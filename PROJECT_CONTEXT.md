# PROJECT_CONTEXT.md — PCDeck Live System Architecture (v2.8.0.0)

> **State-Only Specification**: This document describes the active production architecture, hardware pipelines, network protocols, and operational invariants as of version **2.8.0.0**. For historical release notes, chronological milestones, and resolved bug post-mortems, see [`docs/HISTORY.md`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/docs/HISTORY.md).

---

## 1. System Identity & Distribution Model
- **Product Name**: PCDeck (formerly Mobile Trackpad for PC)
- **Developer**: Greson Parichha | **Canonical Domain**: `https://getpcdeck.com`
- **Current Production Version**: `2.7.9` | **Version Code**: `279` | **MSIX Version**: `2.8.0.0`
- **Distribution Channels (Strict 3-Card Architecture)**:
  1. **Windows**:
     - *Microsoft Store*: Containerized, test-signed (`dist/PCDeck.msix`) and store upload (`dist/PCDeck_Store_Upload.msix`, Store ID: `9P4BK16LBGLS`).
     - *Standalone Portable*: Self-contained single-file binary (`PCDeck.exe`, ~37.5 MB) serving embedded `/PCDeck.apk` over LAN.
     - *Legacy Retirement*: Inno Setup (`PCDeck-Setup.exe`) and `PCDeck_Package.zip` are permanently discontinued.
  2. **Android**:
     - Standalone signed APK (`PCDeck.apk`, ~983 KB) with `minSdkVersion=21`, `targetSdkVersion=34`, zero native `.so` bloat, signed with v1/v2/v3 signatures.
  3. **Linux**:
     - Headless / GUI launcher script (`run_linux.sh` via `curl -sSL https://getpcdeck.com/run_linux.sh | bash`).

---

## 2. Network Topology & Port Mapping
The server runs on FastAPI / Uvicorn (default port `8000`) with dedicated WebSocket and TCP endpoints:

| Port / Endpoint | Protocol / Format | Architecture & Mechanics |
| :--- | :--- | :--- |
| **`8000 /ws`** | WebSocket (Text & Binary) | Core control bus: mouse moves (`m`), clicks (`c`), keypresses (`k`), hotkeys (`h`), unicode text (`t`), and targeted sub-pixel scroll (`ts`, `s`). |
| **`8000 /ws/screen`** | WebSocket (Binary JPEG) | Adaptive screen stream: client-paced in-flight ACK (`a`), 30 FPS cap for Free, 60/120 FPS for Pro, dirty-frame skip, 1-byte keepalive (`h`). |
| **`8000 /ws/audio`** | WebSocket (Binary PCM) | Browser Web Remote PC loopback audio (16-bit 48kHz stereo, WebAudio `AudioWorklet`). |
| **`8000 /ws/cam`** | WebSocket (Binary JPEG) | Mobile-to-PC webcam feed fed into DirectShow virtual camera filter (`drivers/UnityCaptureFilter64.dll`). |
| **`8000 /api/fs/*`** | HTTP REST & Streams | High-speed file transfers with `Accept-Ranges: bytes` (HTTP 206 Partial Content) and active XHR abort. |
| **`8002`** | Raw TCP / UDP Socket | Real-time wireless microphone (Android `AudioSource.VOICE_RECOGNITION` $\to$ Windows WASAPI 2-ch virtual cable). 40ms adaptive jitter cushion. |
| **`8003`** | Raw TCP Socket | Native Android high-fidelity audio stream directly fed into native `AudioTrack` with sub-40ms latency. |

---

## 3. Streaming Engines & DSP Parameters

### A. Screen Capture & Compression Engine (`server/screen_streamer.py`)
- **Capture**: Persistent Win32 GDI `BitBlt` with `CAPTUREBLT` and direct memory bitmap (`GetDIBits`). Overhead is ~1.4ms per frame.
- **Adaptive Dual-Chroma Subsampling**:
  - High Quality ($q \ge 88$) & Native Scale: `subsampling = 0` (`'444'`) for razor-sharp text and code readability.
  - Motion / Bandwidth-Saving ($q < 88$): `subsampling = 1` (`'420'`) for lightweight 12–18 KB frames.
- **Pacing & In-Flight Flow Control**: Server dispatches next frame only after client returns receipt ACK (`a`), maintaining TCP queue depth at 1 frame and preventing bufferbloat.
- **Dirty Frame Detection**: Fast NumPy 2D stride sampling (`raw_np[::8, ::8, 0]`) skips static frames, dropping idle CPU to <0.5%.

### B. Audio Loopback & Worklet PLL (`static/audio-worklet-processor.js`)
- **Server Audio Buffer**: Queue capacity is 32 chunks (~340ms cushion), write-buffer ceiling is 64 KB.
- **WebAudio Phase-Locked Loop (PLL)**:
  - `TARGET_BUFFER_MS = 100`
  - `DEADBAND_LOW_MS = 75` (slows playback rate gently to accumulate cushion when buffer < 75ms)
  - `DEADBAND_HIGH_MS = 135` (accelerates playback rate up to 1.012x to drain backlog when buffer > 135ms)
  - `PREBUFFER_THRESHOLD_MS = 90`, `REBUFFER_THRESHOLD_MS = 60`
  - `MAX_CEILING_MS = 240` (fast-forwards stale audio if tab sleeps)

---

## 4. Input Injection & Touch Physics

### A. Touch Scrolling & Kinetic Momentum (`static/app.js` & `server/input_controller.py`)
- **Dynamic Touch Scaling**:
  - `scaleY = canvasH / rectH`, `scaleX = canvasW / rectW`
  - `speedMultiplier = 1.08 * (state.scrollSpeed ? (state.scrollSpeed / 1.4) : 1.0)`
  - `wheelDy = scrollDy * scaleY * speedMultiplier * scrollFactor`
  - `wheelDx = scrollDx * scaleX * speedMultiplier * scrollFactor`
- **Windows High-Precision Sub-Tick Dispatch**:
  - Dispatches micro-deltas using `SMOOTH_WHEEL_STEP = 24` (1/5th of legacy 120-unit notch), eliminating notch stall in modern browsers and apps.
- **Kinetic Momentum (Fling)**:
  - Triggered if release velocity $|v| > 0.35\text{ px/ms}$. Capped at `maxVelocity = 2.5` with `0.70` damping.
  - Exponential friction decay: `Math.pow(0.92, dt / 16.67)`.
  - Tap-to-stop cancels momentum animation immediately on `touchstart`.

### B. Driverless Gamepad Architecture (`server/gamepad_manager.py`)
- **Driverless SendInput First**: Microsoft Store Policy 10.2.9 compliant; emulates gamepad inputs directly via Win32 `SendInput` without mandatory third-party kernel drivers.
- **Optional Dual-Emission**: If `ViGEmBus` is detected locally on the host, events dual-emit to standard Xbox 360 controller emulation.
- **HUD Dragging**: Scale-invariant coordinate normalization (`transform: scale(s)`) prevents coordinate drift on mobile displays.

---

## 5. Commercial Licensing & Security Architecture

### A. Dodo Payments Standard (`live.dodopayments.com`)
- **Key Format**: RFC-4122 lowercase UUIDs (`/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/`).
- **Sanitization Invariant**: Always sanitize keys with `.trim().replace(/['"]/g, '').toLowerCase()` in JS and `.strip().lower()` in Python. NEVER use `.toUpperCase()` or `.upper()`.
- **Seat Limit & 422 Anti-Piracy**: Each key allows 3 machine hardware bindings (`activation_limit: 3`). Re-activation upon HTTP 422 is strictly permitted ONLY if the local machine matches signed `license.dat` HWID records.
- **Local Wi-Fi Auto-Unlock**: Connected mobile clients automatically inherit Pro tier at zero cost via WebSocket broadcast (`pro_unlocked, 1`).
- **Direct Mobile Fallback (`activateDirectMobile`)**: If a mobile client pairs with an older PCDeck desktop server that rejects UUIDs, the phone activates directly against Dodo Payments over HTTPS.

### B. Hardware Binding & HMAC Tamper Protection (`server/license_manager.py`)
- **HWID Source**: Strictly bound to `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` (`KEY_READ | KEY_WOW64_64KEY`). Never hash volatile MAC addresses or hostnames.
- **Payload Signature**: `sig = HMAC_SHA256(machine_hwid + license_key + instance_id + salt)` stored in `%LOCALAPPDATA%\PCDeck\license.dat` (or `~/.pcdeck/license.dat`). Tampered files fail verification instantly and revert to Free.

---

## 6. UI/UX Standards & Anti-AI-Slop Mandate
- **Zero Emojis**: Strictly no emojis in HTML, JavaScript, Python GUI, buttons, toasts, or markdown docs.
- **Vector Icons Only**: Inline `<svg viewBox="0 0 24 24">` paths with class `deck-icon`.
- **Verified Themes (6 Active)**:
  1. `default`: Cyber Cyan (obsidian `#0a0e17` with `#00f0ff` neon accents)
  2. `aero`: Frutiger Aero (aquatic glass gradients, `#025480` icons, `aero_bg.webp`)
  3. `y2k`: Y2K Chrome (brushed dark steel `#181d26` with hot pink highlights)
  4. `crt`: CRT Phosphor (pitch black `#030804` with scanlines and phosphor green)
  5. `purple`: Synthwave (violet dusk `#180938` with retro wireframe borders)
  6. `oled`: OLED Pure Dark (0-nit pitch black `#000000` with zero glow)

---

## 7. Mandatory Verification Gates
Before committing code or completing any task:
1. `static/app.js` == `android_app/assets/app.js` (Must be bit-for-bit identical)
2. `static/index.html` == `android_app/assets/index.html`
3. `python tools/sync_website.py`
4. `python tools/verify_website.py` (Must pass all 68 HTML files)
5. `python tools/audit_repo.py` (Must exit 0 with zero invariant violations)
6. `pytest tests/` (All 84 unit tests must pass)
