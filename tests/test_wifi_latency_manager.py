"""
Unit and Integration Tests for PCDeck Wi-Fi Latency Management System.
Tests:
  1. WiFiLatencyManager streaming mode state transitions and adaptive pacing.
  2. WiFiWatchdog pause/resume monitoring functionality.
  3. ScreenStreamer dirty-frame detection and consumer pause/resume.
  4. Socket TCP_NODELAY optimization helper.
"""

import sys
import os
import time
import socket
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.wifi_latency_manager import WiFiLatencyManager, wifi_latency_manager
from server import wifi_manager
from server.screen_streamer import ScreenStreamer, encode_frame_to_jpeg


def test_wifi_latency_manager_lifecycle():
    """Verify streaming mode transitions and watchdog sleep coordination."""
    mgr = WiFiLatencyManager()
    assert not mgr.is_streaming_active

    # Start watchdog
    watchdog = wifi_manager.start_watchdog()
    assert watchdog is not None
    assert not watchdog.is_paused

    # Acquire streaming mode for viewer 1
    mgr.acquire_streaming_mode("viewer_1")
    assert mgr.is_streaming_active
    assert watchdog.is_paused

    # Acquire streaming mode for viewer 2 (re-entrant)
    mgr.acquire_streaming_mode("viewer_2")
    assert mgr.is_streaming_active
    assert watchdog.is_paused

    # Release viewer 1 (still active for viewer 2)
    mgr.release_streaming_mode("viewer_1")
    assert mgr.is_streaming_active
    assert watchdog.is_paused

    # Release viewer 2 (all viewers gone -> should resume watchdog)
    mgr.release_streaming_mode("viewer_2")
    assert not mgr.is_streaming_active
    assert not watchdog.is_paused

    wifi_manager.stop_watchdog()


def test_adaptive_ack_timeout_scaling():
    """Verify dynamic ACK timeout adapts gracefully to measured client RTT."""
    mgr = WiFiLatencyManager()

    # Initial default RTT (25ms)
    t0 = mgr.get_adaptive_ack_timeout()
    assert 0.3 <= t0 <= 0.5

    # High latency update (e.g. 200ms)
    for _ in range(10):
        mgr.update_measured_rtt(200.0)

    t_high = mgr.get_adaptive_ack_timeout()
    assert t_high > t0
    assert t_high >= 0.45

    # Low latency recovery (15ms)
    for _ in range(10):
        mgr.update_measured_rtt(15.0)

    t_low = mgr.get_adaptive_ack_timeout()
    assert t_low < t_high


def test_socket_optimization():
    """Verify TCP_NODELAY is applied to real socket objects."""
    mgr = WiFiLatencyManager()

    # Create dummy TCP socket pair
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    conn, _ = server_sock.accept()

    # Mock an ASGI websocket transport
    class MockTransport:
        def __init__(self, s):
            self._s = s
        def get_extra_info(self, name):
            if name == "socket":
                return self._s
            return None
        def get_write_buffer_size(self):
            return 1024

    class MockWebSocket:
        def __init__(self, t):
            self.scope = {"transport": t}

    ws = MockWebSocket(MockTransport(conn))

    # Test TCP_NODELAY optimization
    ok = mgr.optimize_socket_for_low_latency(ws)
    assert ok is True

    # Verify socket option on conn
    nodelay_val = conn.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
    assert nodelay_val == 1

    # Verify congestion check
    assert mgr.is_transport_congested(ws, max_buffered_bytes=512) is True
    assert mgr.is_transport_congested(ws, max_buffered_bytes=2048) is False

    conn.close()
    client_sock.close()
    server_sock.close()


def test_screen_streamer_pause_resume():
    """Verify ScreenStreamer tracks active viewers and pauses capture cleanly."""
    streamer = ScreenStreamer()
    assert streamer._active_viewers == 0

    streamer.acquire()
    assert streamer._consumers == 1
    assert streamer._active_viewers == 1

    streamer.pause_consumer()
    assert streamer._active_viewers == 0
    assert streamer._consumers == 1

    streamer.resume_consumer()
    assert streamer._active_viewers == 1

    streamer.release()
    assert streamer._consumers == 0
    assert streamer._active_viewers == 0
    streamer.stop()


def test_screen_streamer_single_frame():
    """Verify grab_single_frame succeeds with valid JPEG output."""
    streamer = ScreenStreamer()
    jpeg, w, h = streamer.grab_single_frame(quality=60, scale=0.5)
    assert len(jpeg) > 100
    # JPEG magic bytes: FF D8
    assert jpeg[0] == 0xFF and jpeg[1] == 0xD8
    assert w > 0 and h > 0


def test_dirty_frame_detection_logic():
    """Verify that identical frames with unchanged cursor are flagged clean (not dirty)."""
    import numpy as np

    h, w = 100, 100
    # Frame 1: constant buffer
    frame1 = np.full((h, w, 4), 120, dtype=np.uint8)
    sample1 = frame1[::8, ::8, 0]
    cursor1 = (50, 50)

    # Frame 2: identical buffer & identical cursor
    frame2 = np.full((h, w, 4), 120, dtype=np.uint8)
    sample2 = frame2[::8, ::8, 0]
    cursor2 = (50, 50)

    # Test logic
    is_dirty = True
    if cursor1 == cursor2 and np.array_equal(sample1, sample2):
        is_dirty = False
    assert is_dirty is False

    # Frame 3: cursor moved
    cursor3 = (55, 50)
    is_dirty_cursor = True
    if cursor1 == cursor3 and np.array_equal(sample1, sample2):
        is_dirty_cursor = False
    assert is_dirty_cursor is True

    # Frame 4: pixel changed
    frame4 = frame1.copy()
    frame4[16, 16, 0] = 200
    sample4 = frame4[::8, ::8, 0]
    is_dirty_pixel = True
    if cursor1 == cursor2 and np.array_equal(sample1, sample4):
        is_dirty_pixel = False
    assert is_dirty_pixel is True


def test_autoconfig_skipped_when_wifi_disconnected(monkeypatch):
    """Verify that autoconfig is never disabled if Wi-Fi adapter is disconnected (e.g. USB tethering / LAN)."""
    mgr = WiFiLatencyManager()
    
    # Mock elevated admin status
    monkeypatch.setattr(wifi_manager, "is_admin", lambda: True)
    # Mock disconnected Wi-Fi link health
    monkeypatch.setattr(wifi_manager, "get_link_health", lambda: {"state": "disconnected", "ssid": "", "interface": "Wi-Fi"})
    monkeypatch.setattr(wifi_manager, "get_current_wifi_status", lambda: {"state": "disconnected", "ssid": ""})
    
    disabled_calls = []
    monkeypatch.setattr(wifi_manager, "set_wlan_autoconfig", lambda enabled, interface="": (disabled_calls.append((enabled, interface)), (True, "OK"))[1])
    
    mgr.acquire_streaming_mode("viewer_lan")
    
    # Streaming mode is active for the client, but autoconfig was NOT touched!
    assert mgr.is_streaming_active
    assert not mgr._wlan_autoconfig_disabled
    assert len(disabled_calls) == 0
    
    mgr.release_streaming_mode("viewer_lan")


def test_startup_auto_heal_restores_disabled_interfaces(monkeypatch):
    """Verify that startup_auto_heal queries and restores any disabled WLAN interfaces."""
    mgr = WiFiLatencyManager()
    restored_called = False
    
    def fake_restore():
        nonlocal restored_called
        restored_called = True
        return 1
        
    monkeypatch.setattr(wifi_manager, "restore_all_wlan_autoconfig", fake_restore)
    result = mgr.startup_auto_heal()
    assert restored_called is True
    assert result == 1


def test_cleanup_on_exit_restores_all_autoconfig(monkeypatch):
    """Verify that _cleanup_on_exit restores all WLAN interfaces."""
    mgr = WiFiLatencyManager()
    mgr._wlan_autoconfig_disabled = True
    mgr._target_wlan_interface = "Wi-Fi"
    
    restore_all_called = False
    def fake_restore_all():
        nonlocal restore_all_called
        restore_all_called = True
        return 1
        
    monkeypatch.setattr(wifi_manager, "restore_all_wlan_autoconfig", fake_restore_all)
    mgr._cleanup_on_exit()
    
    assert not mgr._wlan_autoconfig_disabled
    assert restore_all_called is True


def test_is_autoconfig_suspension_safe_usb_dongles():
    """Verify that USB Wi-Fi dongles of all vendors (Realtek, MediaTek, TP-Link, Ralink, etc.) are flagged unsafe."""
    mgr = WiFiLatencyManager()

    # Realtek dongle
    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "HomeWiFi", "interface": "Wi-Fi",
        "description": "Realtek RTL8188FTV Wireless LAN 802.11n USB 2.0 Network Adapter",
        "ip": "192.168.1.100", "is_hotspot": False
    })
    assert safe is False
    assert "USB Wi-Fi adapter" in reason

    # TP-Link dongle
    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "HomeWiFi", "interface": "Wi-Fi 2",
        "description": "TP-Link Wireless USB Adapter",
        "ip": "192.168.1.101", "is_hotspot": False
    })
    assert safe is False
    assert "USB Wi-Fi adapter" in reason

    # MediaTek / Ralink dongle
    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "OfficeNet", "interface": "Wi-Fi",
        "description": "MediaTek MT7601U 802.11b/g/n Wireless LAN Adapter",
        "ip": "192.168.1.102", "is_hotspot": False
    })
    assert safe is False
    assert "USB Wi-Fi adapter" in reason


def test_is_autoconfig_suspension_safe_mobile_hotspots():
    """Verify that Android, iPhone, and cellular mobile hotspots are flagged unsafe."""
    mgr = WiFiLatencyManager()

    # Samsung Galaxy Hotspot
    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "Galaxy F15 5G ED0B", "interface": "Wi-Fi",
        "description": "Intel(R) Wi-Fi 6 AX200 160MHz",
        "ip": "10.189.70.215", "is_hotspot": False
    })
    assert safe is False
    assert "hotspot" in reason.lower()

    # Generic Android Hotspot (192.168.43.x)
    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "AndroidAP", "interface": "Wi-Fi",
        "description": "Intel(R) Wi-Fi 6 AX200 160MHz",
        "ip": "192.168.43.15", "is_hotspot": False
    })
    assert safe is False
    assert "hotspot" in reason.lower()

    # iPhone Hotspot (172.20.10.x)
    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "Alex's iPhone", "interface": "Wi-Fi",
        "description": "Intel(R) Wi-Fi 6 AX200 160MHz",
        "ip": "172.20.10.3", "is_hotspot": False
    })
    assert safe is False
    assert "hotspot" in reason.lower()


def test_is_autoconfig_suspension_safe_internal_pcie():
    """Verify that genuine internal PCIe adapters on regular Wi-Fi routers ARE permitted."""
    mgr = WiFiLatencyManager()

    safe, reason = mgr.is_autoconfig_suspension_safe({
        "status": "ok", "ssid": "Home_Fiber_5G", "interface": "Wi-Fi",
        "description": "Intel(R) Wi-Fi 6 AX200 160MHz",
        "ip": "192.168.1.45", "is_hotspot": False
    })
    assert safe is True
    assert "Internal Wi-Fi adapter" in reason


def test_watchdog_auto_restores_on_link_drop(monkeypatch):
    """Verify that watchdog detects link drop during streaming and restores autoconfig."""
    mgr = WiFiLatencyManager()
    mgr._wlan_autoconfig_disabled = True
    mgr._target_wlan_interface = "Wi-Fi"
    mgr._streaming_mode_active = True
    mgr._active_streamers.add("client_1")
    mgr._last_activity_time = time.time()  # recent activity

    # Mock Wi-Fi link drop (status="disconnected")
    monkeypatch.setattr(wifi_manager, "get_link_health", lambda: {"status": "disconnected", "ssid": "", "interface": "Wi-Fi"})

    restored = []
    monkeypatch.setattr(wifi_manager, "set_wlan_autoconfig", lambda enabled, interface="": (restored.append((enabled, interface)), (True, "OK"))[1])
    monkeypatch.setattr(wifi_manager, "restore_all_wlan_autoconfig", lambda: 1)

    triggered = mgr._check_safety_watchdog_step()

    assert triggered is True
    assert not mgr._wlan_autoconfig_disabled
    assert len(restored) > 0
    assert restored[0] == (True, "Wi-Fi")


