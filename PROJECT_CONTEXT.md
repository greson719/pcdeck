# PCDeck — Project Context & Engineering Standards

> [!IMPORTANT]
> **MANDATORY DIRECTIVE FOR ALL AI AGENTS & NEW INSTANCES**:
> Every new AI assistant, coding agent, or subagent working on this repository **MUST READ THIS ENTIRE FILE FIRST** before designing, writing, modifying, or executing code. All architecture, protocols, UX standards, and design invariants defined here must be preserved at all times.

---

## 1. Core Identity & Architectural Invariants
- **Product Name**: **PCDeck** (written as **PCDeck** or **PC Deck** in SEO contexts).
- **Core Value Proposition**: 100% Offline, ultra-low latency local Wi-Fi utility suite for Windows 10/11 & Android (Multi-Touch Trackpad, Full Virtual Mechanical Keyboard + Numpad, Real-Time Low-Latency PC Screen Streaming, Live Stereo PC Audio Streaming, and Cable-Free Local File Transfer).
- **Privacy Standard**: Zero cloud accounts, zero telemetry, zero analytics, zero external dependencies. All communication is strictly local network (LAN / Mobile Hotspot).
- **Monetization & Pro Plan Model**:
  - The core application is completely free and fully functional.
  - **Pro** is an optional **one-time $3.99 in-app lifetime unlock** inside the main PCDeck app (enables 60/120 FPS high-refresh desktop mirroring, unthrottled gigabit file transfers, neon chroma themes, and the pro keymapper).
  - **Rule**: Never create or distribute a separate "PCDeck Pro" binary. PCDeck is a single unified app with in-app activation.

---

## 2. Input Controller & Touch Architecture (Strict Physical Standards)

### A. Screen Streaming Direct Touch & 1:1 Scrolling Physics
When the user streams the PC screen to their Android phone (`tab-screen`):
1. **1:1 Direct Physical Tracking (Phone Level)**:
   - The user expects dragging content on the phone screen to feel identical to scrolling on a native mobile app.
   - Content on the PC must move at the **exact same physical speed** as the user's finger on the phone display.
   - Dynamic scaling formula:
     - `scaleY = (canvas.height / rect.height) / effectiveZoom`
     - `scaleX = (canvas.width / rect.width) / effectiveZoom`
     - `wheelDy = dy * scaleY * scrollSpeed * scrollFactor`
     - `wheelDx = dx * scaleX * scrollSpeed * scrollFactor`
   - **Never** add arbitrary fixed multipliers (such as `24x` or `50x`) to the wheel delta.

2. **Mobile Kinetic Momentum (Fling Inertia)**:
   - Tracks finger release velocity over the last 80ms (`vx`, `vy` in px/ms).
   - If release velocity `|v| > 0.35 px/ms`, engage a `requestAnimationFrame` momentum loop with exponential friction decay (`0.92^(dt / 16.67)`).
   - **Tap-to-Stop**: Any subsequent `touchstart` immediately cancels active momentum animation, matching iOS and Android touch behavior.

3. **Targeted Sub-Pixel Win32 Accumulators**:
   - `WindowsInputController` in `server/input_controller.py` maintains dedicated float sub-pixel accumulators (`_accum_scroll_y` and `_accum_scroll_x`).
   - Dispatches `user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, step_y, None)` for vertical scrolling and `user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, step_x, None)` for horizontal scrolling with signed `ctypes.c_long` parameters.
   - `scroll_at(norm_x, norm_y, dx, dy)` automatically positions the Windows cursor over the target window before emitting wheel deltas so Windows delivers scroll events to the exact control under the user's finger.

### B. Trackpad Gesture Engine (`tab-trackpad`)
- **1-Finger Drag**: Ballistic cursor acceleration with adaptive tremor filtering (`alpha` smoothing) and sub-pixel accumulation (`_accum_x`, `_accum_y`).
- **1-Finger Tap (< 220ms, < 8px moved)**: Left Click (`c,left`).
- **2-Finger Tap**: Right Click (`c,right`).
- **1-Finger Long Press (350ms, < 14px moved)**: Drag & Drop lock (`td` down, `tm` move, `tu` up).
- **Dedicated Scroll Strip**: Calibrated vertical scrollbar thumb strip sending smooth `s,0,dy` wheel steps.

---

## 3. Real-Time WebSocket Communication Protocols

The server runs on FastAPI / Uvicorn (default port `8000`) with dedicated WebSocket endpoints:

| Endpoint | Protocol / Format | Purpose |
| :--- | :--- | :--- |
| `/ws` | Text JSON/CSV commands | Mouse moves (`m`), clicks (`c`), keypresses (`k`), hotkeys (`h`), unicode text (`t`), media keys (`media`). |
| `/ws/screen` | Binary JPEG frames (Server -> Client) + Text commands (Client -> Server) | Zero-lag adaptive binary screen streaming (30/60 FPS, quality 20-90, scale 0.3-1.0), touch move (`a`, `tm`), touch drag (`td`, `tu`), touch scroll (`ts`). |
| `/ws/audio` | Binary PCM 16-bit 48kHz stereo frames | Real-time loopback PC audio streaming to phone earbuds. |

### Command Reference Table:
- `ts,normX,normY,dx,dy` — Targeted scroll at normalized coordinate `(normX, normY)` with `dx` horizontal and `dy` vertical delta.
- `s,dx,dy` — Relative mouse wheel scroll (`dx` horizontal, `dy` vertical).
- `a,normX,normY` — Absolute mouse cursor repositioning across virtual desktop.
- `m,dx,dy` — Relative mouse cursor move with ballistic acceleration.
- `c,btn` — Click button (`left`, `right`, `middle`, `double`).
- `td,normX,normY,btn` — Touch down (press mouse button at coordinate).
- `tm,normX,normY` — Touch move (drag cursor to coordinate).
- `tu,normX,normY,btn` — Touch up (release mouse button at coordinate).
- `k,key` — Press key (`enter`, `backspace`, `f1`-`f12`, `esc`, `ctrl`, `alt`, `win`, etc.).
- `h,key1+key2` — Hotkey combination (e.g. `ctrl+c`, `win+d`, `alt+tab`).
- `t,text` — High-speed Unicode typing synchronization.
- `media,action` — Media control (`play_pause`, `next`, `prev`, `vol_up`, `vol_down`, `mute`).
- `cfg,quality,scale,fps` — Dynamically reconfigure screen stream encoder parameters on the fly.

### Universal Smart QR & Gateway Routing:
- The PC companion app displays a single unified QR code encoding:
  `https://pcdeck.vercel.app/connect?ip={LOCAL_IP}:{SERVER_PORT}`
- **Scanned inside PCDeck App**: In-app scanner parses `?ip=` parameter and connects immediately over local LAN.
- **Scanned by Phone Camera (New User)**: Opens the `/connect` gateway offering 1-tap APK download (`/PCDeck.apk`) or instant zero-install Web Remote (`http://{LOCAL_IP}:{SERVER_PORT}`).
- **Android App Links**: `AndroidManifest.xml` registers `<intent-filter>` for `https://pcdeck.vercel.app/connect` to launch the native companion directly from system camera scans.

---

## 4. File Transfer Architecture (High-Speed Local Streaming)

- **Standard Directory Naming**:
  - Phone Side: `Downloads/PCDeck/` (`📥 Received from PC`).
  - PC Side: `Downloads/PCDeck_Transfers/` (`📥 Received from Phone`).
- **Android All Files Access (`MANAGE_EXTERNAL_STORAGE`)**:
  - Android 11+ (API 30+) `MANAGE_EXTERNAL_STORAGE` and Android 13+ `READ_MEDIA_*` permissions declared in `AndroidManifest.xml`.
  - Permission status checked via `Environment.isExternalStorageManager()` with an in-app 1-tap grant banner.
- **Bidirectional Streaming**:
  - `POST /api/fs/upload-stream`: Unbuffered chunk streaming with 2MB disk buffer.
  - `GET /api/fs/download`: Chunked HTTP streaming with `Accept-Ranges: bytes` support for auto-resume.
- **Network Resilience & Power Management**:
  - Infinite socket read timeout (`setReadTimeout(0)`) during active transfers.
  - Android `PowerManager.PARTIAL_WAKE_LOCK` and `WifiManager.WIFI_MODE_FULL_HIGH_PERF` held during transfers to prevent OS Doze throttling.
  - Sticky ongoing Android status bar notifications with live percentage, throughput speed (MB/s), and real-time ETA countdown.

---

## 5. Design & Content Standards (Strict Anti-AI Slop Rules)

1. **No AI Cliché Emojis or Marketing Slop**:
   - Strictly forbidden: `⚡`, `🚀`, `🔥`, `🤖`, `✨` or cheesy emojis in technical UI and documentation.
   - Strictly forbidden: Empty buzzwords ("revolutionary", "cutting-edge", "game-changing", "next-gen").
   - Use clean, honest, technical, and human-friendly editorial prose.

2. **Cyber-Neon Glassmorphism Design Aesthetic**:
   - Deep obsidian background (`#0a0e17`), elevated surfaces (`#131926`), typography (`Outfit`, `JetBrains Mono`, `Archivo`), vibrant cyan (`#00f0ff`), lime (`#00ff66`), and yellow (`#ffe600`) accents with micro-animations and tactile haptics.

---

## 6. Lemon Squeezy Pro Licensing Architecture

### Live Store & Checkout Details
- **Store Domain**: `pcdeck.lemonsqueezy.com`
- **Product Name**: `PCDeck Pro — Lifetime License` ($3.99 one-time)
- **Live Checkout URL**: `https://pcdeck.lemonsqueezy.com/checkout/buy/5231b162-7c25-44f2-bcc3-f384839344c3`

### Official Lemon Squeezy License API Endpoints
Direct, public client-safe endpoints that require zero private API keys or custom backend:
- **Activation**: `POST https://api.lemonsqueezy.com/v1/licenses/activate` (`license_key`, `instance_name`).
- **Validation**: `POST https://api.lemonsqueezy.com/v1/licenses/validate` (`license_key`, `instance_id`).
- **Deactivation**: `POST https://api.lemonsqueezy.com/v1/licenses/deactivate` (`license_key`, `instance_id`).

### Activation & Persistence Flow
- User purchases PCDeck Pro ($3.99 one-time lifetime license) on Lemon Squeezy and receives their unique license key.
- Inside PCDeck (Android or Windows), the user enters the key and taps **Activate**.
- The app directly contacts `https://api.lemonsqueezy.com/v1/licenses/activate` with the license key and device instance name.
- On verified activation (`activated: true`), the app saves `pcdeck_pro_active = true`, `pcdeck_pro_license = license_key`, and `pcdeck_pro_instance_id = instance.id` in persistent local storage.
- Once activated, Pro features remain unlocked for the lifetime of the installation.
- Multi-device support: Up to 5 device instances per customer license key.

---

## 7. Verification, Build & Release Protocol

Before committing or releasing updates:
1. **Verify Input & Controller Tests**: Run `uv run python test_input.py` to confirm all Win32 cursor, click, and wheel accumulators pass.
2. **Sync Client Assets**: Ensure `static/app.js` and `android_app/assets/app.js` remain bit-for-bit identical.
3. **Compile & Sign Android APK**: Run `uv run python build_apk.py` to compile Java sources, convert to DEX, align, and sign `PCDeck.apk`.
4. **Regenerate Checksums**: Run `uv run python tools/update_checksums.py` to calculate exact SHA-256 digests and update the download table in `website/index.html`.
5. **Keep Context Synchronized**: Update `PROJECT_CONTEXT.md` in root and `website/` to reflect every architecture change.
6. **Commit & Push to GitHub**: Commit verified changes and push to `origin main` on `greson719/pcdeck-pro`.
