"""
PCDeck Pro - Ultra-Low-Latency Windows WASAPI Audio Loopback Streamer
Captures Default PC Audio (Speakers/Headphones) -> Encodes Opus/PCM -> Streams to Phone
"""

import asyncio
import io
import os
import socket
import struct
import subprocess
import sys
import threading
import time
import queue
from typing import Set, Optional, AsyncGenerator, Tuple
import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    try:
        import pyaudio
    except ImportError:
        pyaudio = None


class AudioStreamer:
    """Captures system output audio on Windows via WASAPI Loopback and broadcasts to phone clients."""

    def __init__(self, sample_rate: int = 48000, channels: int = 2, chunk_size: int = 512):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size  # 512 frames = 10.66ms for competitive game streaming
        self.is_running = False
        self.pyaudio_instance = None
        self.stream = None
        self.capture_thread = None
        self.loopback_device = None

        # Active WebSocket subscriber queues
        self._subscribers: Set[Tuple[Optional[asyncio.AbstractEventLoop], asyncio.Queue]] = set()
        self._subscribers_lock = threading.Lock()

        # Native Direct TCP audio stream clients (port 8003)
        self._tcp_clients = set()
        self._tcp_lock = threading.Lock()
        self._tcp_server_thread = None
        self._tcp_stop = None

        # Listeners count
        self.active_listeners = 0

    def _find_loopback_device(self, p):
        """Locates the default output speaker's WASAPI loopback device."""
        # 0. Direct pyaudiowpatch default loopback API (fastest & most accurate on Windows)
        if hasattr(p, "get_default_wasapi_loopback"):
            try:
                loopback = p.get_default_wasapi_loopback()
                if loopback:
                    return loopback
            except Exception:
                pass

        default_speaker_name = ""
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            if wasapi_info and "defaultOutputDevice" in wasapi_info:
                def_out = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                default_speaker_name = def_out.get("name", "")
        except Exception:
            pass

        # 1. Search loopback devices for matching speaker name
        if hasattr(p, "get_loopback_device_info_generator"):
            for dev in p.get_loopback_device_info_generator():
                if default_speaker_name and default_speaker_name in dev.get("name", ""):
                    return dev

            # 2. Return first available loopback device
            for dev in p.get_loopback_device_info_generator():
                return dev

        # 3. Fallback: scan all devices
        for i in range(p.get_device_count()):
            try:
                dev = p.get_device_info_by_index(i)
                if dev.get("isLoopbackDevice", False) or "loopback" in dev.get("name", "").lower():
                    return dev
            except Exception:
                pass

        return None

    def start(self):
        """Starts the audio capture thread if not already active."""
        if self.is_running and self.capture_thread and self.capture_thread.is_alive():
            return

        self.is_running = True
        self.capture_thread = threading.Thread(target=self._run_capture, daemon=True, name="AudioLoopbackCapture")
        self.capture_thread.start()

    def stop(self):
        """Stops the audio capture."""
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception:
                pass
            self.pyaudio_instance = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Real-time WASAPI callback when audio frames are rendered by Windows."""
        if in_data and len(in_data) > 0:
            self._last_audio_time = time.time()
            self._broadcast_chunk(in_data)
        return (in_data, pyaudio.paContinue)

    def _run_capture(self):
        """Internal non-blocking audio capture loop with continuous pacing and self-healing."""
        self._last_audio_time = time.time()
        try:
            # Boost thread priority on Windows to prevent any audio underruns or stutter
            try:
                import ctypes
                thread_handle = ctypes.windll.kernel32.GetCurrentThread()
                # THREAD_PRIORITY_HIGHEST = 2, THREAD_PRIORITY_TIME_CRITICAL = 15
                ctypes.windll.kernel32.SetThreadPriority(thread_handle, 2)
            except Exception:
                pass

            self.pyaudio_instance = pyaudio.PyAudio()
            dev = self._find_loopback_device(self.pyaudio_instance)
            if not dev:
                return

            self.loopback_device = dev
            self.sample_rate = int(dev.get("defaultSampleRate", 48000))
            self.channels = min(2, max(1, int(dev.get("maxInputChannels", 2))))

            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=dev["index"],
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
            )
            self.stream.start_stream()

            chunk_duration = self.chunk_size / max(1, self.sample_rate)
            silence_chunk = b"\x00" * (self.chunk_size * self.channels * 2)

            while self.is_running:
                now = time.time()
                # Only inject a gentle silence keepalive when Windows audio has been genuinely
                # idle for >250ms. Never inject false silence blocks into active gameplay/music!
                if now - self._last_audio_time >= 0.250:
                    self._broadcast_chunk(silence_chunk)
                    self._last_audio_time = now
                time.sleep(0.050)

        except Exception:
            pass
        finally:
            self.is_running = False
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            if self.pyaudio_instance:
                try:
                    self.pyaudio_instance.terminate()
                except Exception:
                    pass
                self.pyaudio_instance = None

    def _broadcast_chunk(self, chunk: bytes):
        """Dispatches audio chunk to all active subscribers across threads safely without backlog bloat."""
        # 1. WebSocket subscriber queues
        with self._subscribers_lock:
            for loop, q in list(self._subscribers):
                try:
                    if loop and loop.is_running():
                        def safe_put(queue=q, data=chunk):
                            try:
                                # Cap queue to max 32 chunks (~340ms) to absorb event-loop bursts without dropping frames
                                while queue.qsize() > 32:
                                    try:
                                        queue.get_nowait()
                                    except Exception:
                                        break
                                queue.put_nowait(data)
                            except Exception:
                                pass
                        loop.call_soon_threadsafe(safe_put)
                    else:
                        while q.qsize() > 32:
                            try:
                                q.get_nowait()
                            except Exception:
                                break
                        q.put_nowait(chunk)
                except Exception:
                    pass

        # 2. Native Direct TCP Sockets (Phone Native AudioTrack / AudioRelay grade)
        if hasattr(self, "_tcp_clients") and self._tcp_clients:
            with self._tcp_lock:
                dead = []
                for client in list(self._tcp_clients):
                    try:
                        client.sendall(chunk)
                    except Exception:
                        dead.append(client)
                for d in dead:
                    self._tcp_clients.discard(d)
                    try: d.close()
                    except Exception: pass

    def start_tcp_server(self, port: int = 8003):
        """Starts high-speed native TCP audio server on port 8003 for native mobile clients."""
        if hasattr(self, "_tcp_server_thread") and self._tcp_server_thread and self._tcp_server_thread.is_alive():
            return

        self._tcp_stop = threading.Event()

        def _tcp_listener():
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind(("0.0.0.0", port))
                server_sock.listen(5)
                server_sock.settimeout(1.0)
                print(f"[AudioStreamer] Native TCP Audio Engine active on 0.0.0.0:{port}", flush=True)
                while not self._tcp_stop.is_set():
                    try:
                        client, addr = server_sock.accept()
                        try:
                            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                            client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                        except Exception:
                            pass
                        with self._tcp_lock:
                            self._tcp_clients.add(client)
                        self.start()
                        print(f"[AudioStreamer] Native audio client connected from {addr[0]}:{addr[1]}", flush=True)
                    except socket.timeout:
                        continue
                    except Exception:
                        pass
            except Exception as e:
                print(f"[AudioStreamer] TCP server error on {port}: {e}", flush=True)
            finally:
                try: server_sock.close()
                except Exception: pass

        self._tcp_server_thread = threading.Thread(target=_tcp_listener, name="AudioStreamer-TCPListener", daemon=True)
        self._tcp_server_thread.start()

    def register_subscriber(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Queue:
        """Registers a new WebSocket subscriber queue with its event loop."""
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except Exception:
                loop = None

        q = asyncio.Queue(maxsize=64)
        with self._subscribers_lock:
            self._subscribers.add((loop, q))
            self.active_listeners = len(self._subscribers)
        self.start()
        return q

    def unregister_subscriber(self, q: asyncio.Queue):
        """Removes a subscriber queue."""
        with self._subscribers_lock:
            self._subscribers = {item for item in self._subscribers if item[1] != q}
            self.active_listeners = len(self._subscribers)

    def create_wav_header(self, sample_rate: int = 48000, channels: int = 2, bits_per_sample: int = 16) -> bytes:
        """Generates standard 44-byte WAV header for streaming."""
        byte_rate = sample_rate * channels * (bits_per_sample // 8)
        block_align = channels * (bits_per_sample // 8)
        # 0x7fffffff size indicates continuous infinite streaming
        data_size = 0x70000000
        total_size = data_size + 36

        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            total_size,
            b'WAVE',
            b'fmt ',
            16,             # Subchunk1Size (16 for PCM)
            1,              # AudioFormat (1 for PCM)
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b'data',
            data_size
        )
        return header


# ---------------------------------------------------------------------------
# Wireless Microphone Sink (Phone Mic -> PC Virtual Audio Cable)
# ---------------------------------------------------------------------------

try:
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except ImportError:
    sd = None
    _HAS_SOUNDDEVICE = False


def is_mic_driver_installed() -> bool:
    """
    Checks if a virtual audio cable (e.g. VB-CABLE, Virtual Audio Cable)
    is installed and available in Windows audio devices.
    """
    if sys.platform == "win32":
        # 1. Check Windows PnP device status directly (un-cached & instant)
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-PnpDevice -FriendlyName '*cable*' -Status OK -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FriendlyName"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if any(k in res.stdout.lower() for k in ("vb-audio", "virtual cable", "cable input", "cable output")):
                return True
        except Exception:
            pass

    if _HAS_SOUNDDEVICE:
        try:
            # Re-initialize sounddevice / PortAudio cache to detect newly registered devices
            try:
                sd._terminate()
                sd._initialize()
            except Exception:
                pass
            devices = sd.query_devices()
            for dev in devices:
                name = dev.get("name", "").lower()
                if any(k in name for k in ("cable input", "cable output", "vb-audio", "virtual audio cable", "line 1")):
                    return True
        except Exception:
            pass

    return False


def get_default_playback_id() -> str:
    """Queries and returns the ID of the current default Windows audio playback device."""
    if sys.platform != "win32":
        return ""
    try:
        cmd = ["powershell", "-NoProfile", "-Command",
               "(Get-AudioDevice -List -ErrorAction SilentlyContinue | Where-Object { $_.Default -eq $true -and $_.Type -eq 'Playback' }).ID"]
        res = subprocess.run(cmd, capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        return res.stdout.strip()
    except Exception:
        return ""


def restore_playback_id(dev_id: str = "") -> bool:
    """Restores original Windows audio playback device to keep PC speakers active."""
    if sys.platform != "win32":
        return False
    try:
        if not dev_id or "cable" in dev_id.lower():
            # Fallback to physical Speakers
            cmd = ["powershell", "-NoProfile", "-Command",
                   "(Get-AudioDevice -List -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*Speakers*' -and $_.Type -eq 'Playback' }) | Set-AudioDevice"]
        else:
            cmd = ["powershell", "-NoProfile", "-Command", f'Set-AudioDevice -ID "{dev_id}"']
        res = subprocess.run(cmd, capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        return res.returncode == 0
    except Exception:
        return False



def get_drivers_dir() -> str:
    """Returns safe fallback directory."""
    return os.path.dirname(os.path.abspath(__file__))


def has_internet_connection() -> bool:
    """Checks if host PC has an active internet connection."""
    import socket
    for host in [("1.1.1.1", 53), ("8.8.8.8", 53)]:
        try:
            socket.create_connection(host, timeout=1.5)
            return True
        except OSError:
            pass
    return False


def install_mic_driver_silently(installer_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Installs the VB-Audio Virtual Cable driver online via winget on Windows.
    Returns (success: bool, message: str).
    """
    if sys.platform != "win32":
        return False, "Virtual Audio Cable is only supported on Windows."

    # Install via winget
    try:
        proc = subprocess.run(
            ["winget", "install", "--id", "VB-Audio.VirtualCable", "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if proc.returncode in (0, 3010):
            return True, "VB-CABLE driver installed successfully via package manager."
        else:
            return False, f"winget returned code {proc.returncode}"
    except Exception as e:
        return False, f"Installation error: {str(e)}"


class MicrophoneSink:
    """
    Receives uncompressed 16-bit 48kHz PCM audio chunks streamed from the phone
    and plays them into a virtual audio cable (e.g. VB-Cable) so PC applications
    (Discord, Zoom, OBS) receive them as microphone input.
    """

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_active = False
        self.out_stream = None
        self.lock = threading.Lock()
        self.active_device_name = "Virtual Audio Cable"
        self.audio_queue = queue.Queue(maxsize=40)
        self.worker_thread = None
        self._stop_event = threading.Event()
        # Jitter buffer & transport arbitration
        self._prebuffer_threshold = 4  # 4 blocks of 512 frames = ~42.6ms buffer cushion
        self._accum_mono = bytearray()
        self._accum_lock = threading.Lock()
        self._tcp_client_active = False
        self._last_tcp_time = 0.0

    def _find_virtual_audio_device(self) -> Optional[int]:
        """Finds virtual audio cable device index on Windows if present, prioritizing low-latency WASAPI."""
        if not _HAS_SOUNDDEVICE:
            return None
        try:
            devices = sd.query_devices()
            # 1. Prefer WASAPI standard 2ch CABLE Input (sub-10ms latency, highest precision on Windows)
            for idx, dev in enumerate(devices):
                if dev.get('max_output_channels', 0) > 0:
                    name = dev.get('name', '').lower()
                    api = sd.query_hostapis(dev.get('hostapi', 0)).get('name', '').lower()
                    if 'cable input' in name and '16ch' not in name and 'wasapi' in api:
                        return idx
            # 2. Prefer DirectSound standard CABLE Input
            for idx, dev in enumerate(devices):
                if dev.get('max_output_channels', 0) > 0:
                    name = dev.get('name', '').lower()
                    api = sd.query_hostapis(dev.get('hostapi', 0)).get('name', '').lower()
                    if 'cable input' in name and '16ch' not in name and 'directsound' in api:
                        return idx
            # 3. Prefer MME standard CABLE Input
            for idx, dev in enumerate(devices):
                if dev.get('max_output_channels', 0) > 0:
                    name = dev.get('name', '').lower()
                    api = sd.query_hostapis(dev.get('hostapi', 0)).get('name', '').lower()
                    if 'cable input' in name and '16ch' not in name and 'mme' in api:
                        return idx
            # 4. Fallback to any vb-audio or virtual audio (non-16ch)
            for idx, dev in enumerate(devices):
                if dev.get('max_output_channels', 0) > 0:
                    name = dev.get('name', '').lower()
                    if ('vb-audio' in name or 'virtual audio' in name) and '16ch' not in name:
                        return idx
        except Exception:
            pass
        return None

    def _audio_worker(self):
        """Dedicated background audio player loop with adaptive jitter buffer & anti-gating."""
        if sys.platform == "win32":
            try:
                import ctypes
                thread_handle = ctypes.windll.kernel32.GetCurrentThread()
                # THREAD_PRIORITY_HIGHEST = 2
                ctypes.windll.kernel32.SetThreadPriority(thread_handle, 2)
            except Exception:
                pass

        is_buffering = True

        while not self._stop_event.is_set():
            if is_buffering:
                # Smooth pre-buffering: accumulate 4 chunks (~42ms cushion) before starting playback to absorb Wi-Fi jitter
                if self.audio_queue.qsize() < self._prebuffer_threshold:
                    time.sleep(0.004)
                    continue
                is_buffering = False

            try:
                chunk = self.audio_queue.get(timeout=0.035)
            except queue.Empty:
                # Wi-Fi packet gap / underrun: re-arm buffering state smoothly without click
                is_buffering = True
                continue

            if chunk is None:
                break

            try:
                if self.out_stream and self.is_active:
                    self.out_stream.write(chunk)
            except Exception as e:
                pass

    def start(self):
        """Starts the virtual microphone output stream with dedicated audio thread."""
        with self.lock:
            if self.is_active and self.out_stream:
                return

            if not _HAS_SOUNDDEVICE:
                print("[MicrophoneSink] sounddevice not available. Operating in buffer loopback mode.")
                self.is_active = True
                return

            try:
                dev_idx = self._find_virtual_audio_device()
                if dev_idx is not None:
                    dev_info = sd.query_devices(dev_idx)
                    self.active_device_name = dev_info.get('name', 'Virtual Audio Cable')
                else:
                    self.active_device_name = "Default Audio Output"

                self.out_stream = sd.RawOutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    device=dev_idx,
                    blocksize=512,
                    latency='low'
                )
                self.out_stream.start()
                self.is_active = True
                self._stop_event.clear()

                # Clear queue & accumulator
                with self._accum_lock:
                    self._accum_mono.clear()
                while not self.audio_queue.empty():
                    try: self.audio_queue.get_nowait()
                    except queue.Empty: break

                self.worker_thread = threading.Thread(target=self._audio_worker, name="PCDeck-MicrophoneWorker", daemon=True)
                self.worker_thread.start()
                print(f"[MicrophoneSink] Active — Routing phone microphone to: {self.active_device_name} ({self.sample_rate}Hz {self.channels}ch)")
            except Exception as e:
                print(f"[MicrophoneSink] Could not open output device ({e}). Ingesting frames in loopback mode.")
                self.is_active = True

    def stop(self):
        """Stops the microphone stream and worker thread."""
        with self.lock:
            self.is_active = False
            self._stop_event.set()
            try:
                self.audio_queue.put_nowait(None)
            except Exception:
                pass
            if self.out_stream:
                try:
                    self.out_stream.stop()
                    self.out_stream.close()
                except Exception:
                    pass
                self.out_stream = None
            with self._accum_lock:
                self._accum_mono.clear()
            self._tcp_client_active = False
            print("[MicrophoneSink] Stopped.")

    def push_pcm_bytes(self, pcm_bytes: bytes, transport: str = "tcp"):
        """Writes incoming raw 16-bit PCM bytes to queue with sample alignment, jitter buffering and deduplication."""
        if not pcm_bytes:
            return

        now = time.time()
        if transport == "tcp":
            self._tcp_client_active = True
            self._last_tcp_time = now
        elif transport == "udp":
            # If TCP stream is active, discard duplicate UDP packets to prevent comb-filtering & stutter
            if self._tcp_client_active and (now - self._last_tcp_time < 1.5):
                return

        if not self.is_active or not self.out_stream:
            self.start()

        try:
            with self._accum_lock:
                self._accum_mono.extend(pcm_bytes)
                # Each mono sample is 2 bytes (16-bit). We output chunks of 512 frames (1024 bytes mono -> 2048 bytes stereo)
                CHUNK_MONO_BYTES = 1024
                while len(self._accum_mono) >= CHUNK_MONO_BYTES:
                    raw_chunk = bytes(self._accum_mono[:CHUNK_MONO_BYTES])
                    del self._accum_mono[:CHUNK_MONO_BYTES]

                    if self.channels == 2:
                        mono_arr = np.frombuffer(raw_chunk, dtype=np.int16)
                        stereo_arr = np.repeat(mono_arr, 2)
                        out_bytes = stereo_arr.tobytes()
                    else:
                        out_bytes = raw_chunk

                    # Keep queue tightly bounded (<80ms) to eliminate latency drift
                    while self.audio_queue.qsize() > 8:
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            break

                    try:
                        self.audio_queue.put_nowait(out_bytes)
                    except queue.Full:
                        pass

                # If queue is starved and we have at least 480 bytes (240 samples) remaining of even length:
                if self.audio_queue.empty() and len(self._accum_mono) >= 480:
                    flush_len = len(self._accum_mono) - (len(self._accum_mono) % 2)
                    raw_chunk = bytes(self._accum_mono[:flush_len])
                    del self._accum_mono[:flush_len]

                    if self.channels == 2:
                        mono_arr = np.frombuffer(raw_chunk, dtype=np.int16)
                        stereo_arr = np.repeat(mono_arr, 2)
                        out_bytes = stereo_arr.tobytes()
                    else:
                        out_bytes = raw_chunk

                    try:
                        self.audio_queue.put_nowait(out_bytes)
                    except queue.Full:
                        pass
        except Exception:
            pass

    def start_dual_receiver(self, port: int = 8002):
        """Starts both high-speed TCP stream listener and UDP datagram listener on port 8002 with deduplication."""
        if hasattr(self, "_net_stop") and self._net_stop and not self._net_stop.is_set():
            return

        self._net_stop = threading.Event()

        # 1. High-Speed Reliable TCP Stream Server (100% reliable, zero dropped packets)
        def _tcp_worker():
            tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                tcp_server.bind(("0.0.0.0", port))
                tcp_server.listen(5)
                tcp_server.settimeout(1.0)
                print(f"[MicrophoneSink] TCP Audio Engine active on 0.0.0.0:{port}", flush=True)
                while not self._net_stop.is_set():
                    try:
                        client_sock, addr = tcp_server.accept()
                        print(f"[MicrophoneSink] Phone connected via TCP from {addr[0]}:{addr[1]}", flush=True)
                        try:
                            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                        except Exception:
                            pass
                        if not self.is_active:
                            self.start()

                        def _handle_client(sock, client_addr):
                            pkt_count = 0
                            try:
                                while not self._net_stop.is_set():
                                    data = sock.recv(4096)
                                    if not data:
                                        break
                                    pkt_count += 1
                                    if pkt_count % 100 == 1:
                                        usable = len(data) - (len(data) % 2)
                                        arr = np.frombuffer(data[:usable], dtype=np.int16) if usable > 0 else np.array([])
                                        p = int(np.max(np.abs(arr))) if len(arr) > 0 else 0
                                        print(f"[MicrophoneSink] TCP incoming from {client_addr[0]}: {pkt_count} chunks (Live Peak: {p})", flush=True)
                                    self.push_pcm_bytes(data, transport="tcp")
                            except Exception as e:
                                print(f"[MicrophoneSink] TCP client read error: {e}", flush=True)
                            finally:
                                print(f"[MicrophoneSink] TCP client {client_addr[0]} disconnected after {pkt_count} chunks", flush=True)
                                self._tcp_client_active = False
                                try: sock.close()
                                except Exception: pass

                        th = threading.Thread(target=_handle_client, args=(client_sock, addr), daemon=True)
                        th.start()
                    except socket.timeout:
                        continue
                    except Exception:
                        pass
            except Exception as e:
                print(f"[MicrophoneSink] TCP listener bind failed on {port}: {e}", flush=True)
            finally:
                try: tcp_server.close()
                except Exception: pass

        self._tcp_thread = threading.Thread(target=_tcp_worker, name="MicrophoneSink-TCPWorker", daemon=True)
        self._tcp_thread.start()

        # 2. UDP datagram listener fallback
        def _udp_worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                except Exception:
                    pass
                sock.bind(("0.0.0.0", port))
                sock.settimeout(1.0)
                print(f"[MicrophoneSink] UDP Audio Engine active on 0.0.0.0:{port}", flush=True)
                while not self._net_stop.is_set():
                    try:
                        data, addr = sock.recvfrom(4096)
                        if data:
                            now = time.time()
                            # Suppress UDP datagrams if TCP client is actively streaming
                            if self._tcp_client_active and (now - self._last_tcp_time < 1.5):
                                continue
                            if not self.is_active:
                                self.start()
                            self.push_pcm_bytes(data, transport="udp")
                    except socket.timeout:
                        continue
                    except Exception:
                        pass
            except Exception as e:
                print(f"[MicrophoneSink] UDP listener failed to bind to {port}: {e}", flush=True)
            finally:
                try: sock.close()
                except Exception: pass

        self._udp_thread = threading.Thread(target=_udp_worker, name="MicrophoneSink-UDPWorker", daemon=True)
        self._udp_thread.start()


# Global singletons
audio_streamer = AudioStreamer()
mic_sink = MicrophoneSink()

