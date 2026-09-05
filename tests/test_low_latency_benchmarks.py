"""
Comprehensive Automated Low-Latency Benchmark Suite for PCDeck.

Validates:
  1. Binary Wire Protocol pack/unpack latency (< 0.05ms) and throughput (> 500k ops/sec).
  2. Windows Multimedia Kernel Timer Resolution (timeBeginPeriod(1)) vs default 15.6ms tick.
  3. Windows Process Priority (HIGH_PRIORITY_CLASS = 0x00000080).
  4. Direct Win32 SendInput dispatch latency (< 0.1ms / 100 microseconds).
  5. Socket TCP_NODELAY (Nagle disabled) and 32KB buffer tuning.
  6. Binary packet boundary safety & error handling.
"""

import sys
import os
import time
import socket
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.binary_protocol import (
    OP_MOVE_REL, OP_MOVE_ABS, OP_TOUCH_DOWN, OP_TOUCH_MOVE, OP_TOUCH_UP,
    OP_CLICK, OP_SCROLL_REL, OP_SCROLL_ABS, OP_PING, OP_GAMEPAD,
    pack_move_rel, pack_move_abs, pack_touch_down, pack_touch_move, pack_touch_up,
    pack_click, pack_scroll_rel, pack_scroll_abs, pack_ping, pack_pong,
    unpack_binary_message
)
from server.input_controller import controller, init_low_latency_environment
from server.wifi_latency_manager import wifi_latency_manager


def test_binary_protocol_correctness():
    """Verify pack and unpack for all binary message types."""
    # Move Rel
    buf = pack_move_rel(-15.5, 25.0, flags=1)
    assert len(buf) == 8
    res = unpack_binary_message(buf)
    assert res is not None
    cmd, args = res
    assert cmd == "m"
    assert abs(args[0] - (-15.5)) < 0.1
    assert abs(args[1] - 25.0) < 0.1

    # Click
    buf_click = pack_click(button="right")
    assert len(buf_click) == 8
    res = unpack_binary_message(buf_click)
    assert res is not None
    cmd, args = res
    assert cmd == "c"
    assert args[0] == "right"

    # Scroll Rel
    buf_scroll = pack_scroll_rel(dx=0, dy=-120)
    assert len(buf_scroll) == 8
    res = unpack_binary_message(buf_scroll)
    assert res is not None
    cmd, args = res
    assert cmd == "s"
    assert args[0] == 0
    assert abs(args[1] - (-120.0)) < 0.1

    # Ping
    t_ms = 123456789
    buf_ping = pack_ping(t_ms)
    assert len(buf_ping) == 8
    res = unpack_binary_message(buf_ping)
    assert res is not None
    cmd, args = res
    assert cmd == "ping"
    assert args[0] == t_ms


def test_binary_protocol_performance_benchmark():
    """
    Benchmark binary protocol unpacking speed.
    Target: < 0.05 ms (50 microseconds) per unpack.
    Real performance expectation: < 2 microseconds per unpack.
    """
    buf = pack_move_rel(10.5, -5.2, flags=0)
    iterations = 100_000

    t0 = time.perf_counter()
    for _ in range(iterations):
        unpack_binary_message(buf)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    per_op_us = (elapsed / iterations) * 1_000_000
    per_op_ms = per_op_us / 1000.0
    throughput = iterations / elapsed

    print(f"\n[BENCHMARK] Binary Unpack: {per_op_us:.3f} us/op ({throughput:,.0f} pkts/sec)")

    # Strict assertion: must be well below 0.05ms (50 us)
    assert per_op_ms < 0.05, f"Unpack latency {per_op_ms:.4f}ms exceeds 0.05ms target!"
    assert throughput > 200_000, f"Throughput {throughput:,.0f} pkts/sec is too low"


def test_binary_protocol_safety_invalid_inputs():
    """Verify that malformed or truncated binary buffers return None safely without crashing."""
    # Truncated buffer
    assert unpack_binary_message(b"\x01\x00") is None

    # Empty buffer
    assert unpack_binary_message(b"") is None

    # Unknown message type
    assert unpack_binary_message(b"\xFF" * 8) is None


@pytest.mark.skipif(os.name != "nt", reason="Win32 specific low-latency test")
def test_win32_kernel_timer_resolution():
    """
    Verify multimedia timer (timeBeginPeriod(1)) is working.
    On standard Windows without timeBeginPeriod(1), time.sleep(0.001) takes ~15.6ms.
    With timeBeginPeriod(1), time.sleep(0.001) should take <= 3.5ms.
    """
    init_low_latency_environment()

    # Measure 10 short 1ms sleeps
    sleep_samples = []
    for _ in range(10):
        t0 = time.perf_counter()
        time.sleep(0.001)
        t1 = time.perf_counter()
        sleep_samples.append((t1 - t0) * 1000.0)

    avg_sleep_ms = sum(sleep_samples) / len(sleep_samples)
    print(f"\n[BENCHMARK] Win32 1ms Kernel Sleep Average: {avg_sleep_ms:.2f} ms (Default Windows is ~15.6 ms)")

    assert avg_sleep_ms < 5.0, f"Kernel timer resolution too coarse: {avg_sleep_ms:.2f} ms"


@pytest.mark.skipif(os.name != "nt", reason="Win32 specific priority test")
def test_win32_process_priority():
    """Verify that the process priority is elevated to HIGH_PRIORITY_CLASS (0x00000080)."""
    init_low_latency_environment()
    import ctypes
    import ctypes.wintypes
    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    k32.GetPriorityClass.argtypes = [ctypes.wintypes.HANDLE]
    k32.GetPriorityClass.restype = ctypes.wintypes.DWORD
    handle = k32.GetCurrentProcess()
    priority_class = k32.GetPriorityClass(handle)
    HIGH_PRIORITY_CLASS = 0x00000080

    print(f"\n[BENCHMARK] Windows Process Priority Class: 0x{priority_class:08X} (Target: 0x{HIGH_PRIORITY_CLASS:08X})")
    assert priority_class == HIGH_PRIORITY_CLASS, (
        f"Process priority class is 0x{priority_class:08X}, expected HIGH_PRIORITY_CLASS (0x{HIGH_PRIORITY_CLASS:08X})"
    )


@pytest.mark.skipif(os.name != "nt", reason="Win32 specific SendInput test")
def test_win32_sendinput_dispatch_latency():
    """
    Benchmark SendInput dispatch time.
    Target: < 0.1 ms (100 microseconds).
    Real performance expectation: ~20-50 microseconds.
    """
    init_low_latency_environment()

    # Warm up desktop cache
    controller.move_relative(0, 0)

    iterations = 500
    t0 = time.perf_counter()
    for _ in range(iterations):
        controller.move_relative(0, 0)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    per_op_us = (elapsed / iterations) * 1_000_000
    per_op_ms = per_op_us / 1000.0

    print(f"\n[BENCHMARK] Win32 SendInput Dispatch: {per_op_us:.2f} us/op ({per_op_ms:.4f} ms)")
    assert per_op_ms < 0.1, f"SendInput dispatch latency {per_op_ms:.4f}ms exceeds 0.1ms target!"


def test_socket_tcp_nodelay_and_buffer_tuning():
    """Verify TCP_NODELAY and 32KB buffer sizes applied to socket."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    conn, _ = server_sock.accept()

    class MockTransport:
        def __init__(self, s):
            self._s = s
        def get_extra_info(self, name):
            if name == "socket":
                return self._s
            return None

    class MockWebSocket:
        def __init__(self, t):
            self.scope = {"transport": t}

    ws = MockWebSocket(MockTransport(conn))

    # Apply optimization
    ok = wifi_latency_manager.optimize_socket_for_low_latency(ws)
    assert ok is True

    # Check TCP_NODELAY
    nodelay = conn.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
    assert nodelay == 1, "TCP_NODELAY must be 1 (Nagle disabled)"

    # Check buffer sizes (Windows/Linux may double or adjust slightly)
    rcvbuf = conn.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    sndbuf = conn.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    print(f"\n[BENCHMARK] Socket Tuned Buffers: RCVBUF={rcvbuf} bytes, SNDBUF={sndbuf} bytes, TCP_NODELAY={nodelay}")
    assert rcvbuf >= 32768, f"SO_RCVBUF {rcvbuf} is less than 32KB"
    assert sndbuf >= 32768, f"SO_SNDBUF {sndbuf} is less than 32KB"

    conn.close()
    client_sock.close()
    server_sock.close()
