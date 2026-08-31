"""
NeonTrack - Ultra-Low-Latency Windows WASAPI Audio Loopback Streamer
Captures real-time PC speaker output and streams PCM / WAV chunks over WebSocket & HTTP.
"""

import asyncio
import io
import struct
import threading
import time
from typing import Set, Optional, AsyncGenerator

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    import pyaudio


class AudioStreamer:
    """Captures system output audio on Windows via WASAPI Loopback and broadcasts to phone clients."""

    def __init__(self, sample_rate: int = 48000, channels: int = 2, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.is_running = False
        self.pyaudio_instance = None
        self.stream = None
        self.capture_thread = None
        self.loopback_device = None

        # Active WebSocket subscriber queues
        self._subscribers: Set[asyncio.Queue] = set()
        self._subscribers_lock = threading.Lock()

        # Listeners count
        self.active_listeners = 0

    def _find_loopback_device(self, p: pyaudio.PyAudio):
        """Locates the default output speaker's WASAPI loopback device."""
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
        """Internal non-blocking audio capture loop with keep-alive silence generator and self-healing."""
        self._last_audio_time = time.time()
        try:
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

            silence_chunk = b"\x00" * (self.chunk_size * self.channels * 2)

            while self.is_running:
                now = time.time()
                # If Windows audio renderer is idle for > 400ms, send keep-alive silence chunk
                if now - self._last_audio_time > 0.40:
                    self._broadcast_chunk(silence_chunk)
                    self._last_audio_time = now
                time.sleep(0.05)

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
        """Dispatches audio chunk to all active subscribers across threads safely."""
        with self._subscribers_lock:
            for loop, q in list(self._subscribers):
                try:
                    if loop and loop.is_running():
                        def safe_put(queue=q, data=chunk):
                            try:
                                if queue.qsize() < 30:
                                    queue.put_nowait(data)
                            except Exception:
                                pass
                        loop.call_soon_threadsafe(safe_put)
                    else:
                        if q.qsize() < 30:
                            q.put_nowait(chunk)
                except Exception:
                    pass

    def register_subscriber(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Queue:
        """Registers a new WebSocket subscriber queue with its event loop."""
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except Exception:
                loop = None

        q = asyncio.Queue(maxsize=50)
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


# Global audio streamer singleton
audio_streamer = AudioStreamer()
