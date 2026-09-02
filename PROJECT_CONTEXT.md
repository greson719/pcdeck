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
| `/ws` | Text JSON/CSV commands | Mouse moves (`m`), clicks (`c`), keypresses (`k`), hotkeys (`h`), unicode text (`t`), media keys (`media`), and low-latency touch commands (`a`, `td`, `tm`, `tu`). |
| `/ws/screen` | Binary JPEG frames (Server -> Client) + Heartbeat keepalives | Zero-lag adaptive binary screen streaming (30/60 FPS, quality 20-90, scale 0.3-1.0, 4:4:4 lossless chroma), 1-byte keepalive ping (`h`), and stream configuration (`cfg`). |
| `/ws/audio` | Binary PCM 16-bit 48kHz stereo frames | Real-time loopback PC audio streaming to phone earbuds. |

### Command Reference Table:
- `ts,normX,normY,dx,dy` — Targeted scroll at normalized coordinate `(normX, normY)` with `dx` horizontal and `dy` vertical delta.
- `s,dx,dy` — Relative mouse wheel scroll (`dx` horizontal, `dy` vertical).
- `a,normX,normY` — Absolute mouse cursor repositioning across virtual desktop with precision edge snapping.
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

### Zero-Latency Screen Streaming Pipeline (v2.6.6):
1. **100% Native 1.0x Resolution & 4:4:4 Lossless Chroma**:
   - `subsampling=0` (4:4:4 RGB chroma preservation) eliminates YUV color loss on font outlines.
   - 1.0x native scale delivers un-interpolated desktop pixels for readable text and code.
2. **Dedicated Low-Latency Command Bus**:
   - All touch, click, drag, and scroll commands are routed upstream over `/ws` (`mainWs`), bypassing the heavy downstream binary video traffic for instantaneous <1ms touch responsiveness.
3. **Hardware-Accelerated Frame Coalescing Pipeline**:
   - Client uses a `requestAnimationFrame` zero-backlog queue: if a new frame arrives while the previous frame is decoding, stale frames are discarded in 0ms, keeping the video feed synchronized in real time.
4. **Lightweight Heartbeat (`h`)**:
   - Idle keepalive sends a 1-byte ping instead of re-sending full JPEG frames, eliminating network congestion when the desktop is static.
5. **Precision Edge Snapping & Full Viewport Touch**:
   - Touch listeners cover 100% of the viewport (`screenViewport`), and coordinate normalization snaps near-edge taps (<0.015 or >0.985) to `(width - 1, 0)` for Windows Close (X), Minimize, and Taskbar buttons.
6. **Screen Floating Toolbar**:
   - Built-in `1.0x / 1.5x / 2.0x / 3.0x` Quick Zoom, Landscape Rotation, and Direct Touch / Virtual Cursor mode toggle.

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

## 5. In-App OTA Auto-Updater Architecture

- **Endpoint**: `https://pcdeck.vercel.app/version.json` (polled 4s after app launch and on manual check).
- **Payload Schema**:
  ```json
  {
    "versionCode": 266,
    "versionName": "2.6.6",
    "apkUrl": "https://pcdeck.vercel.app/PCDeck.apk",
    "websiteUrl": "https://pcdeck.vercel.app",
    "playStoreUrl": "",
    "releaseNotes": "• 100% Full Native 1.0x Resolution for razor-sharp, crystal-clear desktop text\n• Hardware-accelerated zero-backlog streaming pipeline (instant 60 FPS)\n• Screen quick toolbar: 1x/1.5x/2x/3x Quick Zoom & Landscape Rotation\n• Ultra-fast 1ms direct touch response",
    "minVersionCode": 1,
    "publishedAt": "2026-09-01"
  }
  ```
- **Redirection Logic**:
  - If `playStoreUrl` is set $\implies$ opens Google Play Store directly via `market://details?id=com.neontrack.mouse` or HTTPS fallback.
  - If `playStoreUrl` is empty $\implies$ opens official website (`https://pcdeck.vercel.app` / `apkUrl`) in browser for a clean 1-tap update download.

---

## 6. Design & Content Standards (Strict Anti-AI Slop Rules)

1. **No AI Cliché Emojis or Marketing Slop**:
   - Strictly forbidden: `⚡`, `🚀`, `🔥`, `🤖`, `✨` or cheesy emojis in technical UI and documentation.
   - Strictly forbidden: Empty buzzwords ("revolutionary", "cutting-edge", "game-changing", "next-gen").
   - Use clean, honest, technical, and human-friendly editorial prose.

2. **Cyber-Neon Glassmorphism Design Aesthetic**:
   - Deep obsidian background (`#0a0e17`), elevated surfaces (`#131926`), typography (`Outfit`, `JetBrains Mono`, `Archivo`), vibrant cyan (`#00f0ff`), lime (`#00ff66`), and yellow (`#ffe600`) accents with micro-animations and tactile haptics.

---

## 7. Lemon Squeezy Pro Licensing Architecture

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

## 8. Universal Linux Support (`run_linux.sh`)

- **Universal 1-Line Setup**: `curl -sSL https://pcdeck.vercel.app/run_linux.sh | bash`
- **Capabilities**:
  - Automatically detects and installs Python 3, `pip`, `venv`, `xdotool`, and `wmctrl`.
  - Configures isolated `.venv` environment and installs dependencies from `pyproject.toml`.
  - Runs headless or GUI server with full input injection, MSS screen capture, audio streaming, and high-speed file transfer across Ubuntu, Debian, Fedora, Arch, and Mint.

---

## 9. Microsoft Store (MSIX) & Store Distribution Standards

- **Package Identity & Capability Model**:
  - Package Name: `PCDeck`
  - Display Name: `PCDeck: Wireless Trackpad, Screen Mirror & Remote Mouse`
  - Restricted Capability: `runFullTrust` declared in `AppxManifest.xml` for Win32 input simulation (`user32.dll`), WASAPI loopback audio capture, and local WebSocket server binding.
- **Packaging Pipeline**:
  - Automated Terminal Packager: `build_msix.bat` executing `tools/build_msix.py` (assembles layout, high-DPI assets, and invokes Windows SDK `makeappx` or zip container).
  - GUI Fallback Route: Fully compatible with the official Microsoft Store **MSIX Packaging Tool** using `PCDeck.exe` as the source executable.
- **Visual Assets & Store Artwork**:
  - 1:1 App Logo: `msstore_assets/StoreLogo_300x300.png`
  - Spotlight Hero (2:1): `msstore_assets/StoreHero_2400x1200.png`
  - Promotional Hero (16:9): `msstore_assets/StoreHero_1920x1080.png`
  - Promotional Poster: `msstore_assets/StorePoster_1240x600.png`
  - High-DPI Manifest Tiles: 46 scaled assets generated in `msstore_assets/Manifest_Assets/`.
  - 7 Desktop Screenshots (1920x1080): Located in `msstore_assets/`.
- **Multi-Channel Syndication & Discovery**:
  - Windows Package Manager (`winget`): Automatically indexes the store submission for CLI installs (`winget install PCDeck`).
  - Search Engine Crawlers: Google & Bing index Microsoft's high-authority web storefront (`apps.microsoft.com`).

---

## 10. SEO, ASO & Semantic Competitor Positioning Strategy

- **Master ASO Title**: `PCDeck: Wireless Trackpad, Screen Mirror & Remote Mouse`
- **Semantic Keyword Clusters**:
  1. *Input Utility*: `wireless trackpad`, `remote mouse`, `virtual keyboard`, `touchpad replacement`, `gesture control`.
  2. *Low-Latency Display*: `screen mirror`, `desktop streaming`, `low latency screen sharing`, `mobile display`.
  3. *Audio & Media*: `stream pc audio to phone`, `wasapi loopback`, `wireless earphones pc`, `media remote`.
  4. *Local Storage/Data*: `local wifi file transfer`, `cable-free file sharing`, `lan file manager`.
  5. *Situational / Emergency*: `broken mouse alternative`, `offline pc remote`, `couch pc control`, `presentation remote`.
- **Competitor Pain-Point Attack Vectors**:
  - *Vs Remote Mouse / Monect*: Highlight zero in-app ads, zero subscriptions, zero account logins, and zero telemetry.
  - *Vs Unified Remote*: Modern Cyber-Neon UI, integrated 60 FPS screen mirror, real-time WASAPI audio streaming, and 3-second instant QR network pairing.
  - *Zero-Install Advantage*: Instant browser-based Web Remote fallback without requiring mandatory mobile app installation.
- **Product Roadmap & Monetization Alignment**:
  - Free Tier (100% Functional, Zero Ads): Full Trackpad, Mechanical Keyboard, 30/60 FPS Screen Mirror, WASAPI Audio, File Transfer, and Standard Gamepad.
  - Pro Tier ($3.99 One-Time Lifetime): In-Display on-screen HUD Layout Customizer (PUBG-style button drag/resize/opacity), custom game keymapping presets, high-bitrate streaming, and neon chroma themes.

---

## 11. Verification, Build & Release Protocol

Before committing or releasing updates:
1. **Verify Input & Controller Tests**: Run `python test_input.py` to confirm all Win32 cursor, click, and wheel accumulators pass.
2. **Sync Client Assets**: Ensure `static/app.js` and `android_app/assets/app.js` remain bit-for-bit identical.
3. **Compile & Sign Android APK**: Run `python build_apk.py` to compile Java sources, convert to DEX, align, and sign `PCDeck.apk`.
4. **Compile MSIX Package**: Run `.\build_msix.bat` to refresh `PCDeck.msix` and `msstore_assets/PCDeck.msix`.
5. **Regenerate Checksums**: Run `python tools/update_checksums.py` to calculate exact SHA-256 digests and update the download table in `website/index.html`.
6. **Keep Context Synchronized**: Update `PROJECT_CONTEXT.md` in root and `website/` to reflect every architecture change.
7. **Commit & Push to GitHub**: Commit verified changes and push to `origin main` on `greson719/pcdeck`.

---

## 12. Wireless Debugging & Persistent Device Profile

- **Primary Test Device**: `Motorola moto g35 5G` (`manila_g` / `manila`)
- **Paired Hostname**: `greson@surma`
- **Device LAN IP**: `10.23.32.178` (Subnet `10.23.32.0/24`)
- **Pairing Key / GUID**: `adb-ZD222QY2JF-Cnk1ww`
- **Active Wireless ADB Port**: `36589`
- **Persistent Port Target**: `5555`
- **Standard One-Click Wireless Deploy Command**:
  ```powershell
  adb connect 10.23.32.178:36589; adb push PCDeck.apk /data/local/tmp/PCDeck.apk; adb shell pm install -r -d /data/local/tmp/PCDeck.apk; adb shell am start -n com.neontrack.mouse/.MainActivity
  ```

