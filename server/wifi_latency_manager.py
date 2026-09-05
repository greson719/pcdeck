"""
PCDeck Pro - Wi-Fi Latency Management System
Coordinates real-time low-latency network optimizations during active screen streaming:
  1. Puts unused background tasks to sleep (WiFiWatchdog netsh subprocesses, standby pump loops).
  2. Suppresses Windows WLAN AutoConfig background scans (eliminates periodic 100ms-300ms ping spikes).
  3. Enforces TCP_NODELAY (disables Nagle's algorithm) across all WebSockets.
  4. Monitors transport write buffer backpressure to eliminate TCP bufferbloat.
  5. Guarantees safe restoration of all OS settings and watchdog monitoring on disconnect or exit.
"""

import atexit
import os
import signal
import socket
import sys
import threading
import time
from typing import Optional, Set, Dict, Any, Tuple

try:
    from server import wifi_manager
except ImportError:
    try:
        import wifi_manager
    except ImportError:
        wifi_manager = None


class WiFiLatencyManager:
    """Coordinates zero-bufferbloat streaming mode and background task sleeping."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_streamers: Set[str] = set()
        self._streaming_mode_active: bool = False
        self._wlan_autoconfig_disabled: bool = False
        self._target_wlan_interface: str = ""
        self._smoothed_rtt_ms: float = 25.0
        self._last_rtt_update: float = time.time()
        self._last_activity_time: float = time.time()

        # Auto-heal on startup: restore any leftover disabled WLAN autoconfig state
        self.startup_auto_heal()

        # Register atexit handler so OS Wi-Fi configuration is guaranteed restored
        atexit.register(self._cleanup_on_exit)

        # Register process termination signal handlers
        self._register_signal_handlers()

        # Launch background watchdog thread for lease/inactivity safety
        self._watchdog_thread = threading.Thread(target=self._autoconfig_safety_watchdog, daemon=True)
        self._watchdog_thread.start()

    @property
    def is_streaming_active(self) -> bool:
        with self._lock:
            return self._streaming_mode_active

    @property
    def smoothed_rtt_ms(self) -> float:
        with self._lock:
            return self._smoothed_rtt_ms

    def update_measured_rtt(self, rtt_ms: float) -> None:
        """Update exponential moving average of client RTT for dynamic pacing."""
        with self._lock:
            self._smoothed_rtt_ms = (self._smoothed_rtt_ms * 0.7) + (max(1.0, float(rtt_ms)) * 0.3)
            self._last_rtt_update = time.time()

    def get_adaptive_ack_timeout(self) -> float:
        """Returns safe timeout before treating an ACK as dropped (scaled with RTT)."""
        with self._lock:
            rtt_sec = self._smoothed_rtt_ms / 1000.0
            # Wait at least 350ms, or 2.5x smoothed RTT (up to 1.5s max)
            return min(1.5, max(0.35, 2.5 * rtt_sec))

    def get_hardware_info(self) -> Dict[str, Any]:
        """Detects current physical Wi-Fi hardware adapter, band (2.4G/5G/6G), and link speed."""
        now = time.time()
        with self._lock:
            if hasattr(self, "_cached_hw") and (now - getattr(self, "_last_hw_time", 0) < 5.0):
                return dict(self._cached_hw)

        info = {
            "band": "2.4GHz",
            "speed_mbps": 0.0,
            "channel": "",
            "radio": "",
            "signal_pct": 70,
            "adapter": "Wi-Fi Adapter",
            "ssid": "",
        }
        try:
            if wifi_manager and hasattr(wifi_manager, "get_current_wifi_status"):
                status_data = wifi_manager.get_current_wifi_status()
                interfaces = status_data.get("health", {}).get("interfaces", [])
                if interfaces:
                    iface = interfaces[0]
                    ch = str(iface.get("channel", "")).strip()
                    rx = str(iface.get("rx_mbps", "0")).strip()
                    sig = str(iface.get("signal", "0%")).replace("%", "").strip()
                    radio = str(iface.get("radio", "")).strip()
                    desc = str(iface.get("description", "")).strip()
                    ssid = str(iface.get("ssid", "")).strip()

                    try:
                        ch_num = int(ch)
                        if ch_num <= 14:
                            band = "2.4GHz"
                        elif ch_num <= 196:
                            band = "5GHz"
                        else:
                            band = "6GHz"
                    except Exception:
                        band = "2.4GHz" if any(k in radio for k in ["802.11n", "802.11b", "802.11g"]) else "5GHz"

                    info = {
                        "band": band,
                        "speed_mbps": float(rx) if rx.replace(".", "").isdigit() else 0.0,
                        "channel": ch,
                        "radio": radio,
                        "signal_pct": int(sig) if sig.isdigit() else 70,
                        "adapter": desc,
                        "ssid": ssid,
                    }
        except Exception:
            pass

        with self._lock:
            self._cached_hw = info
            self._last_hw_time = now
        return dict(info)

    def get_network_health(self) -> Dict[str, Any]:
        """
        Calculates honest, dynamic network health metrics based on live RTT,
        jitter, and connection recency with physical hardware stats.
        """
        hw = self.get_hardware_info()
        with self._lock:
            rtt = self._smoothed_rtt_ms
            age = time.time() - self._last_rtt_update

        # If no RTT measurement received in last 10 seconds, client is not actively pinging
        if age > 10.0:
            return {
                "active": False,
                "rtt_ms": None,
                "score_pct": hw.get("signal_pct", 70),
                "status": "Standby",
                "color": "#94a3b8",
                "description": "No active client traffic",
                "hardware": hw,
            }

        # Dynamic scoring curve based on real-world Wi-Fi RTT
        if rtt <= 16:
            score = 98
            status = "Excellent"
            color = "#22c55e"
            desc = "Sub-16ms ultra-responsive connection"
        elif rtt <= 35:
            score = int(95 - (rtt - 16) * (15 / 19))
            status = "Good"
            color = "#00f0ff"
            desc = "Low-latency LAN connection"
        elif rtt <= 75:
            score = int(80 - (rtt - 35) * (20 / 40))
            status = "Fair"
            color = "#eab308"
            desc = "Moderate latency / slight interference"
        elif rtt <= 150:
            score = int(60 - (rtt - 75) * (25 / 75))
            status = "High Traffic"
            color = "#f97316"
            desc = "Network congestion / frame bufferbloat"
        else:
            score = max(5, int(35 - min(30, (rtt - 150) / 10)))
            status = "Congested"
            color = "#ef4444"
            desc = "Severe interference or Wi-Fi packet drops"

        return {
            "active": True,
            "rtt_ms": round(rtt, 1),
            "score_pct": score,
            "status": status,
            "color": color,
            "description": desc,
            "hardware": hw,
        }

    def optimize_socket_for_low_latency(self, websocket: Any) -> bool:
        """
        Applies TCP_NODELAY and socket-level low-latency options to a FastAPI/Starlette WebSocket
        or raw socket. Disables Nagle's algorithm and minimizes socket buffer bloat.
        """
        try:
            sock = None
            if isinstance(websocket, socket.socket):
                sock = websocket
            else:
                transport = getattr(websocket, "scope", {}).get("transport")
                if transport is None:
                    transport = getattr(websocket, "_transport", None)
                if transport is not None and hasattr(transport, "get_extra_info"):
                    sock = transport.get_extra_info("socket")

            if sock is not None:
                # 1. Disable Nagle's algorithm (TCP_NODELAY) for immediate packet dispatch
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # 2. Enable TCP Keepalive
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # 3. Optimize socket buffer sizes (256KB accommodates 1080p JPEG frames without queuing delay)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False

    def is_transport_congested(self, websocket: Any, max_buffered_bytes: int = 262144) -> bool:
        """
        Inspects the underlying asyncio transport's pending write buffer.
        Returns True if the Wi-Fi link is congested (>256KB un-sent data queued).
        """
        try:
            transport = getattr(websocket, "scope", {}).get("transport")
            if transport is None:
                transport = getattr(websocket, "_transport", None)

            if transport is not None and hasattr(transport, "get_write_buffer_size"):
                buffered = transport.get_write_buffer_size()
                return buffered > max_buffered_bytes
        except Exception:
            pass
        return False

    def touch_stream_activity(self) -> None:
        """Update heartbeat timestamp of active screen/control activity."""
        with self._lock:
            self._last_activity_time = time.time()

    def startup_auto_heal(self) -> int:
        """Heals WLAN autoconfig on startup if it was left disabled by a crash or prior session."""
        if sys.platform != "win32":
            return 0
        try:
            if wifi_manager and hasattr(wifi_manager, "restore_all_wlan_autoconfig"):
                restored = wifi_manager.restore_all_wlan_autoconfig()
                if restored > 0:
                    print(f"[WiFiLatencyManager] Auto-heal: restored WLAN autoconfig on {restored} interface(s)", flush=True)
                return restored
        except Exception as e:
            print(f"[WiFiLatencyManager] Startup auto-heal exception: {e}", flush=True)
        return 0

    def _register_signal_handlers(self) -> None:
        """Trap termination signals to guarantee OS settings are restored on close/Ctrl+C."""
        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            if hasattr(signal, sig_name):
                try:
                    sig = getattr(signal, sig_name)
                    prev_handler = signal.getsignal(sig)
                    def _make_handler(prev):
                        def _handler(signum, frame):
                            try:
                                self._cleanup_on_exit()
                            except Exception:
                                pass
                            if callable(prev):
                                prev(signum, frame)
                            elif prev == signal.SIG_DFL:
                                sys.exit(0)
                        return _handler
                    signal.signal(sig, _make_handler(prev_handler))
                except Exception:
                    pass

    @staticmethod
    def is_autoconfig_suspension_safe(health: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determines whether it is safe to suppress Windows WLAN AutoConfig (netsh wlan set autoconfig enabled=no).

        Background:
        Suppression disables Windows background Wi-Fi roaming scans, completely eliminating periodic
        100ms-300ms ping spikes on internal PCIe / M.2 Wi-Fi cards (e.g., Intel AX200/AX210, Killer).

        However, based on widespread community findings (WLAN Optimizer, Reddit, SuperUser, GitHub):
          1. USB Wi-Fi Adapters: USB dongles (Realtek RTL81xx/88xx, MediaTek MT76xx, Ralink, TP-Link,
             Netgear, Edimax, D-Link, etc.) use miniport drivers that rely on wlansvc scan ticks to maintain
             link power and beacon tracking. Turning off autoconfig causes them to drop the link, freeze,
             or fail DHCP renewals within seconds.
          2. Mobile Hotspots: Android / iOS / portable MiFi hotspots operate as dynamic softAPs.
             If client roaming/probe sweeps stop, phone power management or channel shifting disconnects
             the PC or flags the connection as dead.
          3. Non-Wi-Fi connections: USB Tethering (192.168.42.x) and wired Ethernet do not benefit from
             WLAN tweaks, so messing with WLAN autoconfig while using them is risky and pointless.

        Returns (is_safe: bool, reason: str).
        """
        if not health:
            return False, "No Wi-Fi health data available"

        # Check connection state
        status = health.get("status", "")
        state = health.get("state", "")
        ssid = health.get("ssid", "")
        if not ((status == "ok" or state == "connected") and ssid):
            return False, "Wi-Fi is not actively connected to an SSID"

        # Check adapter description / chipset for USB dongles
        desc = (health.get("description") or "").lower()
        iface_name = (health.get("interface") or "").lower()
        combined_id = f"{desc} {iface_name}"

        usb_indicators = [
            "usb", "dongle", "802.11n", "wireless-n", "wireless n", "nano", "mini",
            "rtl", "realtek", "8188", "8192", "8811", "8812", "8814", "8821",
            "mediatek", "mt7", "ralink", "rt28", "rt53",
            "tp-link", "tplink", "archer t", "tl-wn",
            "edimax", "d-link", "dlink", "netgear", "tenda", "mercusys", "zyxel",
            "broadcom usb", "atheros ar9", "qualcomm atheros ar9",
        ]
        for indicator in usb_indicators:
            if indicator in combined_id:
                return False, f"USB Wi-Fi adapter / dongle detected ('{indicator}' matched in '{desc}')"

        # Check if connected to a mobile hotspot
        ip = str(health.get("ip") or "")
        is_hotspot = bool(health.get("is_hotspot"))
        ssid_lower = ssid.lower()
        hotspot_ssids = [
            "hotspot", "galaxy", "pixel", "iphone", "android", "redmi", "xiaomi",
            "oneplus", "oppo", "vivo", "poco", "huawei", "motorola", "mifi"
        ]

        if is_hotspot:
            return False, "Connected to a mobile hotspot"

        if any(h_name in ssid_lower for h_name in hotspot_ssids):
            return False, f"Mobile hotspot SSID detected ('{ssid}')"

        if ip.startswith(("192.168.43.", "192.168.44.", "10.", "172.20.10.")):
            return False, f"Mobile hotspot / tethered subnet detected ({ip})"

        return True, "Internal Wi-Fi adapter connected to standard AP"

    def _check_safety_watchdog_step(self) -> bool:
        """
        Single evaluation step of the safety watchdog.
        Returns True if restoration was triggered, False otherwise.
        """
        should_restore = False
        reason = ""
        target_iface = ""
        with self._lock:
            if self._wlan_autoconfig_disabled:
                target_iface = self._target_wlan_interface
                inactive = (time.time() - self._last_activity_time) > 15.0
                no_streamers = len(self._active_streamers) == 0 or not self._streaming_mode_active
                if inactive or no_streamers:
                    should_restore = True
                    reason = "inactive/orphaned stream session"
                    self._wlan_autoconfig_disabled = False
                    self._streaming_mode_active = False

        # Check for link-drop if autoconfig is currently disabled
        if not should_restore and target_iface:
            try:
                health = wifi_manager.get_link_health() if (wifi_manager and hasattr(wifi_manager, "get_link_health")) else {}
                status = health.get("status", "")
                # If adapter disconnected, radio turned off, or lease lost
                if status in ("disconnected", "radio_off", "no_lease", "no_radio") or not health.get("ssid"):
                    with self._lock:
                        self._wlan_autoconfig_disabled = False
                    should_restore = True
                    reason = f"Wi-Fi link dropped ({status or 'no ssid'})"
            except Exception:
                pass

        if should_restore:
            print(f"[WiFiLatencyManager] Safety watchdog: {reason} -> automatically restoring WLAN autoconfig", flush=True)
            try:
                if wifi_manager and hasattr(wifi_manager, "set_wlan_autoconfig") and target_iface:
                    wifi_manager.set_wlan_autoconfig(True, interface=target_iface)
                if wifi_manager and hasattr(wifi_manager, "restore_all_wlan_autoconfig"):
                    wifi_manager.restore_all_wlan_autoconfig()
            except Exception as e:
                print(f"[WiFiLatencyManager] Safety watchdog restore error: {e}", flush=True)
            return True
        return False

    def _autoconfig_safety_watchdog(self) -> None:
        """
        Background safety thread: runs every 2 seconds.
        If autoconfig was suppressed, immediately restores it if:
          - The Wi-Fi adapter disconnects or loses signal/SSID (instant self-healing)
          - Streaming activity stops or is orphaned (>15s without activity or 0 streamers)
        Ensures users NEVER get stranded with disabled Wi-Fi scanning.
        """
        while True:
            time.sleep(2.0)
            try:
                self._check_safety_watchdog_step()
            except Exception:
                pass

    def acquire_streaming_mode(self, client_id: str) -> None:
        """
        Engages Ultra-Low Latency Wi-Fi Mode when a client starts viewing the screen:
          - Suspends WiFiWatchdog netsh/ipconfig background subprocess polling.
          - Disables Windows WLAN background roaming scans if elevated AND Wi-Fi is safe (internal PCIe on standard router).
          - Optimizes system responsiveness profile.
        """
        with self._lock:
            self._active_streamers.add(client_id)
            self._last_activity_time = time.time()
            if self._streaming_mode_active:
                return
            self._streaming_mode_active = True

        print(f"[WiFiLatencyManager] Ultra-Low Latency Streaming Mode ENGAGED (viewer: {client_id})", flush=True)

        # 1. Put WiFiWatchdog to sleep (stops netsh & ipconfig subprocess calls)
        try:
            if wifi_manager and hasattr(wifi_manager, "pause_watchdog"):
                wifi_manager.pause_watchdog(reason="Active Screen Streaming")
        except Exception as e:
            print(f"[WiFiLatencyManager] Error pausing watchdog: {e}", flush=True)

        # 2. Suppress Windows WLAN AutoConfig Background Scanning (eliminates ping spikes)
        # CRITICAL SAFETY: Only suppress if running elevated AND Wi-Fi adapter is safe.
        # If Wi-Fi is a USB dongle, mobile hotspot, or disconnected, NEVER disable autoconfig!
        if sys.platform == "win32":
            try:
                if wifi_manager and hasattr(wifi_manager, "is_admin") and wifi_manager.is_admin():
                    health = wifi_manager.get_link_health() if hasattr(wifi_manager, "get_link_health") else {}
                    if not health or not health.get("ssid"):
                        try:
                            st = wifi_manager.get_current_wifi_status() if hasattr(wifi_manager, "get_current_wifi_status") else {}
                            if st:
                                health.setdefault("status", "ok" if st.get("state") == "connected" else "disconnected")
                                health.setdefault("ssid", st.get("ssid", ""))
                                health.setdefault("interface", st.get("interface", "Wi-Fi"))
                                health.setdefault("ip", st.get("ip", ""))
                        except Exception:
                            pass

                    is_safe, reason = self.is_autoconfig_suspension_safe(health)
                    if not is_safe:
                        print(f"[WiFiLatencyManager] Autoconfig suspension skipped: {reason} -> preserving link stability", flush=True)
                    else:
                        iface = self._target_wlan_interface
                        if not iface:
                            iface = health.get("interface") or "Wi-Fi"
                            self._target_wlan_interface = iface

                        ok, msg = wifi_manager.set_wlan_autoconfig(False, interface=iface)
                        if ok:
                            with self._lock:
                                self._wlan_autoconfig_disabled = True
                            print(f"[WiFiLatencyManager] WLAN background roaming scans SUSPENDED on '{iface}'", flush=True)
                        else:
                            print(f"[WiFiLatencyManager] WLAN autoconfig suspend failed: {msg}", flush=True)
            except Exception as e:
                print(f"[WiFiLatencyManager] WLAN autoconfig suspend check: {e}", flush=True)

            # 3. Optimize Windows Multimedia Network Throttling
            try:
                if wifi_manager and hasattr(wifi_manager, "optimize_multimedia_network_profile"):
                    wifi_manager.optimize_multimedia_network_profile()
            except Exception:
                pass

    def release_streaming_mode(self, client_id: str) -> None:
        """
        Disengages Ultra-Low Latency Mode when all viewers stop or pause streaming:
          - Resumes WiFiWatchdog health monitoring.
          - Restores Windows WLAN AutoConfig background roaming scans.
        """
        with self._lock:
            self._active_streamers.discard(client_id)
            if len(self._active_streamers) > 0 or not self._streaming_mode_active:
                return
            self._streaming_mode_active = False
            was_autoconfig_disabled = self._wlan_autoconfig_disabled
            self._wlan_autoconfig_disabled = False
            target_iface = self._target_wlan_interface

        print(f"[WiFiLatencyManager] Streaming Mode DISENGAGED (released by {client_id})", flush=True)

        # 1. Resume WiFiWatchdog
        try:
            if wifi_manager and hasattr(wifi_manager, "resume_watchdog"):
                wifi_manager.resume_watchdog()
        except Exception as e:
            print(f"[WiFiLatencyManager] Error resuming watchdog: {e}", flush=True)

        # 2. Restore Windows WLAN AutoConfig
        if sys.platform == "win32" and was_autoconfig_disabled:
            try:
                if wifi_manager and hasattr(wifi_manager, "set_wlan_autoconfig") and target_iface:
                    wifi_manager.set_wlan_autoconfig(True, interface=target_iface)
                    print(f"[WiFiLatencyManager] WLAN background roaming scans RESTORED on '{target_iface}'", flush=True)
                if wifi_manager and hasattr(wifi_manager, "restore_all_wlan_autoconfig"):
                    wifi_manager.restore_all_wlan_autoconfig()
            except Exception as e:
                print(f"[WiFiLatencyManager] Error restoring WLAN autoconfig: {e}", flush=True)

    def release_all_streaming_modes(self) -> None:
        """Disengages all active streamers and restores OS network settings."""
        with self._lock:
            self._active_streamers.clear()
            self._streaming_mode_active = False
            was_disabled = self._wlan_autoconfig_disabled
            self._wlan_autoconfig_disabled = False
            target_iface = self._target_wlan_interface

        if sys.platform == "win32" and was_disabled:
            try:
                if wifi_manager and hasattr(wifi_manager, "set_wlan_autoconfig") and target_iface:
                    wifi_manager.set_wlan_autoconfig(True, interface=target_iface)
                if wifi_manager and hasattr(wifi_manager, "restore_all_wlan_autoconfig"):
                    wifi_manager.restore_all_wlan_autoconfig()
            except Exception:
                pass

    def _cleanup_on_exit(self) -> None:
        """Atexit / termination handler: guarantees normal Wi-Fi state is restored upon exit."""
        with self._lock:
            was_disabled = self._wlan_autoconfig_disabled
            target_iface = self._target_wlan_interface
            self._wlan_autoconfig_disabled = False
            self._streaming_mode_active = False

        if sys.platform == "win32":
            try:
                if wifi_manager and hasattr(wifi_manager, "set_wlan_autoconfig") and target_iface:
                    wifi_manager.set_wlan_autoconfig(True, interface=target_iface)
                if wifi_manager and hasattr(wifi_manager, "restore_all_wlan_autoconfig"):
                    wifi_manager.restore_all_wlan_autoconfig()
            except Exception:
                pass


# Global singleton instance
wifi_latency_manager = WiFiLatencyManager()
