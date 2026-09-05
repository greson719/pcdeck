# Original User Request

## Initial Request — 2026-09-04T16:33:01Z

Refactor and optimize the PCDeck remote desktop and trackpad platform (PC Python Server, Web Client, and Android App) to eliminate input lag, frame drops, and network jitter, achieving sub-5ms input response times and ultra-smooth 60fps streaming.

Working directory: c:\Users\GRESON\Documents\mobile_tracpad_for_pc
Integrity mode: development

## Requirements

### R1. High-Performance Binary Wire Protocol & Dual-Channel Networking
- Implement a compact, raw binary packed wire protocol for all high-frequency cursor, touch, and scroll input messages (8–12 byte binary structs: `[1B msg_type, 2B delta_x, 2B delta_y, 2B flags, 1B pressure]` / normalized coords) to replace stringified CSV/JSON payloads.
- Enforce `TCP_NODELAY` (disabling Nagle's algorithm) and set optimal small-packet buffer sizes (`SO_RCVBUF` / `SO_SNDBUF`) on all client and server sockets upon connection.
- Isolate high-frequency input channels from bulk data/state syncs (file transfers, HTTP RPCs, and camera setup) so cursor input is never blocked by streaming or transfers.
- Maintain full backward compatibility for control commands (hotkeys, typing, settings) and gracefully fallback if text frames are received.

### R2. 802.11 Wi-Fi Power-Save Mitigation & Active Low-Latency Heartbeat
- Implement an active lightweight heartbeat beacon (every 20–50ms) to prevent 2.4GHz / 5GHz Wi-Fi chips from entering 100–300ms power-save sleep states during active sessions.
- In Android `MainActivity.java`, acquire and hold `WifiManager.WIFI_MODE_FULL_LOW_LATENCY` (API 29+) or `WIFI_MODE_FULL_HIGH_PERF` immediately upon connection to keep the radio PHY layer continuously awake for trackpad, gamepad, and screen sessions (not solely during screen streaming).

### R3. Client-Side Touch Interception & Motion Prediction
- Configure all touch interaction surfaces in `static/app.js` and `android_app/assets/app.js` with `touch-action: none;` and non-passive touch listeners (`{ passive: false }`) to eliminate browser gesture disambiguation delay.
- Extract touch coordinates directly from `event.changedTouches` and route immediately to the binary wire pipeline without intermediate string allocations.
- Implement an Exponential Moving Average (EMA) and linear velocity predictor to smoothly interpolate cursor trajectories across packet jitter.
- Throttle mouse and touch transmission to the display refresh rate via `requestAnimationFrame` (60–120Hz) to prevent socket queue saturation.

### R4. Microsecond Windows OS Input Injection & Kernel Scheduling
- Call `timeBeginPeriod(1)` via `winmm.dll` on PC server startup to force the Windows OS kernel scheduler timer resolution from 15.6ms down to 1ms.
- Ensure all cursor and touch movements use direct Win32 ctypes `SendInput` with `MOUSEINPUT` structs with sub-pixel accumulators and zero blocking overhead.
- Decouple input ingestion into a dedicated asynchronous worker / high-priority ingestion loop to avoid latency spikes during disk I/O, file downloads, or video encoding.

### R5. Low-Latency Video Pipeline & Adaptive Congestion Degradation
- Optimize video streaming configurations (MJPEG / H.264) for baseline profile, zero B-frames, and ultrafast encoding.
- Ensure web clients configure low-latency playback buffers (`playoutDelayHint = 0`, `desynchronized: true` canvas context).
- Monitor live Round-Trip Time (RTT); if smoothed RTT exceeds 25ms on congested networks, dynamically scale down frame resolution/FPS to prioritize input responsiveness.

## Acceptance Criteria

### Protocol & Injection Benchmarking
- [ ] Binary wire protocol parser processes input buffers in < 0.05ms per event with zero memory allocation churn.
- [ ] Windows timer resolution is confirmed at 1.0ms via `timeGetDevCaps` / `winmm` on server initialization.
- [ ] Win32 `SendInput` injection latency benchmarks verify < 0.1ms dispatch time per mouse event.
- [ ] Socket options confirm `TCP_NODELAY = 1` active across all live WebSocket transport sockets.

### Client & Android Runtime
- [ ] Android `MainActivity.java` acquires Wi-Fi low-latency lock upon connection and maintains active radio state.
- [ ] Web client touch surfaces operate with `touch-action: none`, direct binary packing, and `requestAnimationFrame` motion coalescing.
- [ ] RTT monitor dynamically adapts video bitrate and frame rate when measured network latency spikes over 25ms.
- [ ] All automated latency verification benchmarks pass cleanly across server, client, and Android assets.
