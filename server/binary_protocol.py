"""
PCDeck Pro - Ultra-Low-Latency Binary Wire Protocol
High-performance packed binary structs for sub-millisecond input dispatch.
Eliminates JSON/CSV string parsing overhead, GC pauses, and memory churn on both client and host.
"""

import struct
from typing import Optional, Tuple, Any

# Protocol Constants
PROTOCOL_VERSION = 1

# Opcodes (1 byte uint8)
OP_MOVE_REL    = 0x01  # Relative mouse move: dx, dy
OP_MOVE_ABS    = 0x02  # Absolute cursor move: normX, normY
OP_TOUCH_DOWN  = 0x03  # Touch down / button press at normX, normY
OP_TOUCH_UP    = 0x04  # Touch up / button release at normX, normY
OP_CLICK       = 0x05  # Instant click button
OP_SCROLL_REL  = 0x06  # Relative scroll: dx, dy
OP_SCROLL_ABS  = 0x07  # Targeted scroll at normX, normY: dx, dy
OP_PING        = 0x08  # Microsecond latency ping / heartbeat
OP_GAMEPAD     = 0x09  # Full packed gamepad state (axes + buttons + triggers)
OP_TOUCH_MOVE  = 0x0A  # Touch drag move at normX, normY

# Button ID mappings
BTN_LEFT   = 0
BTN_RIGHT  = 1
BTN_MIDDLE = 2
BTN_DOUBLE = 3

BTN_MAP = {
    0: "left",
    1: "right",
    2: "middle",
    3: "double",
}

BTN_REV_MAP = {
    "left": 0,
    "right": 1,
    "middle": 2,
    "double": 3,
}

# Pre-compiled Struct Formats (Little-Endian '<')
# 8-byte structs
STRUCT_MOVE_REL   = struct.Struct("<BBhhH")   # op, flags, dx*10, dy*10, reserved
STRUCT_MOVE_ABS   = struct.Struct("<BBHHBB")  # op, flags, normX*65535, normY*65535, pressure, reserved
STRUCT_TOUCH_DOWN = struct.Struct("<BBHHBB")  # op, btn, normX*65535, normY*65535, pressure, reserved
STRUCT_TOUCH_MOVE = struct.Struct("<BBHHBB")  # op, flags, normX*65535, normY*65535, pressure, reserved
STRUCT_TOUCH_UP   = struct.Struct("<BBHHH")   # op, btn, normX*65535, normY*65535, reserved
STRUCT_CLICK      = struct.Struct("<BB6x")    # op, btn, 6 bytes padding
STRUCT_SCROLL_REL = struct.Struct("<BBhhH")   # op, flags, dx*10, dy*10, reserved
STRUCT_PING       = struct.Struct("<BBIH")    # op, flags, timestamp_ms, reserved

# 12-byte struct
STRUCT_SCROLL_ABS = struct.Struct("<BBHHhh")  # op, flags, normX*65535, normY*65535, dx*10, dy*10

# 16-byte struct
STRUCT_GAMEPAD    = struct.Struct("<BHhhhhBB3x") # op, buttons(uint16), lx, ly, rx, ry, lt, rt, 3x reserved

COORD_SCALE = 65535.0
DELTA_SCALE = 10.0


def unpack_binary_message(data: bytes) -> Optional[Tuple[str, Tuple[Any, ...]]]:
    """
    Decodes raw binary packet into a command tuple in < 0.001 ms (sub-microsecond).
    Returns (cmd_name, args) or None if invalid.
    """
    n = len(data)
    if n < 8:
        return None

    op = data[0]

    if op == OP_MOVE_REL:
        # dx, dy in units of 0.1 px
        _, flags, raw_dx, raw_dy, _ = STRUCT_MOVE_REL.unpack_from(data)
        return ("m", (raw_dx / DELTA_SCALE, raw_dy / DELTA_SCALE))

    elif op == OP_MOVE_ABS:
        _, flags, raw_x, raw_y, pressure, _ = STRUCT_MOVE_ABS.unpack_from(data)
        return ("a", (raw_x / COORD_SCALE, raw_y / COORD_SCALE))

    elif op == OP_TOUCH_DOWN:
        _, btn_id, raw_x, raw_y, pressure, _ = STRUCT_TOUCH_DOWN.unpack_from(data)
        btn = BTN_MAP.get(btn_id, "left")
        return ("td", (raw_x / COORD_SCALE, raw_y / COORD_SCALE, btn))

    elif op == OP_TOUCH_MOVE:
        _, flags, raw_x, raw_y, pressure, _ = STRUCT_TOUCH_MOVE.unpack_from(data)
        return ("tm", (raw_x / COORD_SCALE, raw_y / COORD_SCALE))

    elif op == OP_TOUCH_UP:
        _, btn_id, raw_x, raw_y, _ = STRUCT_TOUCH_UP.unpack_from(data)
        btn = BTN_MAP.get(btn_id, "left")
        return ("tu", (raw_x / COORD_SCALE, raw_y / COORD_SCALE, btn))

    elif op == OP_CLICK:
        _, btn_id = STRUCT_CLICK.unpack_from(data)
        btn = BTN_MAP.get(btn_id, "left")
        return ("c", (btn,))

    elif op == OP_SCROLL_REL:
        _, flags, raw_dx, raw_dy, _ = STRUCT_SCROLL_REL.unpack_from(data)
        return ("s", (raw_dx / DELTA_SCALE, raw_dy / DELTA_SCALE))

    elif op == OP_SCROLL_ABS and n >= 12:
        _, flags, raw_x, raw_y, raw_dx, raw_dy = STRUCT_SCROLL_ABS.unpack_from(data)
        return ("ts", (raw_x / COORD_SCALE, raw_y / COORD_SCALE, raw_dx / DELTA_SCALE, raw_dy / DELTA_SCALE))

    elif op == OP_PING:
        _, flags, ts_ms, _ = STRUCT_PING.unpack_from(data)
        return ("ping", (ts_ms, flags))

    elif op == OP_GAMEPAD and n >= 16:
        _, buttons, lx, ly, rx, ry, lt, rt = STRUCT_GAMEPAD.unpack_from(data)
        return ("gp_state", (buttons, lx, ly, rx, ry, lt, rt))

    return None


def pack_move_rel(dx: float, dy: float, flags: int = 0) -> bytes:
    """Packs relative cursor move into 8 bytes."""
    idx = max(-32768, min(32767, int(round(dx * DELTA_SCALE))))
    idy = max(-32768, min(32767, int(round(dy * DELTA_SCALE))))
    return STRUCT_MOVE_REL.pack(OP_MOVE_REL, flags, idx, idy, 0)


def pack_move_abs(norm_x: float, norm_y: float, pressure: int = 0, flags: int = 0) -> bytes:
    """Packs absolute cursor move into 8 bytes."""
    ix = max(0, min(65535, int(round(norm_x * COORD_SCALE))))
    iy = max(0, min(65535, int(round(norm_y * COORD_SCALE))))
    return STRUCT_MOVE_ABS.pack(OP_MOVE_ABS, flags, ix, iy, pressure & 0xFF, 0)


def pack_touch_down(norm_x: float, norm_y: float, button: str = "left", pressure: int = 0) -> bytes:
    """Packs touch down event into 8 bytes."""
    btn_id = BTN_REV_MAP.get(button, 0)
    ix = max(0, min(65535, int(round(norm_x * COORD_SCALE))))
    iy = max(0, min(65535, int(round(norm_y * COORD_SCALE))))
    return STRUCT_TOUCH_DOWN.pack(OP_TOUCH_DOWN, btn_id, ix, iy, pressure & 0xFF, 0)


def pack_touch_move(norm_x: float, norm_y: float, pressure: int = 0, flags: int = 0) -> bytes:
    """Packs touch move event into 8 bytes."""
    ix = max(0, min(65535, int(round(norm_x * COORD_SCALE))))
    iy = max(0, min(65535, int(round(norm_y * COORD_SCALE))))
    return STRUCT_TOUCH_MOVE.pack(OP_TOUCH_MOVE, flags, ix, iy, pressure & 0xFF, 0)


def pack_touch_up(norm_x: float, norm_y: float, button: str = "left") -> bytes:
    """Packs touch up event into 8 bytes."""
    btn_id = BTN_REV_MAP.get(button, 0)
    ix = max(0, min(65535, int(round(norm_x * COORD_SCALE))))
    iy = max(0, min(65535, int(round(norm_y * COORD_SCALE))))
    return STRUCT_TOUCH_UP.pack(OP_TOUCH_UP, btn_id, ix, iy, 0)


def pack_click(button: str = "left") -> bytes:
    """Packs instant click into 8 bytes."""
    btn_id = BTN_REV_MAP.get(button, 0)
    return STRUCT_CLICK.pack(OP_CLICK, btn_id)


def pack_scroll_rel(dx: float, dy: float, flags: int = 0) -> bytes:
    """Packs relative scroll into 8 bytes."""
    idx = max(-32768, min(32767, int(round(dx * DELTA_SCALE))))
    idy = max(-32768, min(32767, int(round(dy * DELTA_SCALE))))
    return STRUCT_SCROLL_REL.pack(OP_SCROLL_REL, flags, idx, idy, 0)


def pack_scroll_abs(norm_x: float, norm_y: float, dx: float, dy: float, flags: int = 0) -> bytes:
    """Packs targeted absolute scroll into 12 bytes."""
    ix = max(0, min(65535, int(round(norm_x * COORD_SCALE))))
    iy = max(0, min(65535, int(round(norm_y * COORD_SCALE))))
    idx = max(-32768, min(32767, int(round(dx * DELTA_SCALE))))
    idy = max(-32768, min(32767, int(round(dy * DELTA_SCALE))))
    return STRUCT_SCROLL_ABS.pack(OP_SCROLL_ABS, flags, ix, iy, idx, idy)


def pack_ping(timestamp_ms: int, flags: int = 0) -> bytes:
    """Packs ping heartbeat into 8 bytes."""
    return STRUCT_PING.pack(OP_PING, flags, timestamp_ms & 0xFFFFFFFF, 0)


def pack_pong(timestamp_ms: int) -> bytes:
    """Packs pong reply into 8 bytes."""
    return STRUCT_PING.pack(OP_PING, 1, timestamp_ms & 0xFFFFFFFF, 0)
