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

### Zero-Latency Screen Streaming Pipeline (v2.7.0):
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
7. **Wi-Fi Latency Management System (`wifi_latency_manager.py`)**:
   - **Streaming Mode Sleeping**: Automatically puts `WiFiWatchdog` (0 netsh/ipconfig subprocesses) and `CameraStreamer` standby workers to sleep when screen streaming is active.
   - **WLAN Roaming Scan Suppression**: Safely suspends Windows WLAN AutoConfig periodic background scans (`netsh wlan set autoconfig enabled=no`) on the active Wi-Fi interface, eliminating 100ms–300ms ping spikes.
   - **Zero-Bufferbloat Transport Pacing**: Enables `TCP_NODELAY = 1` on all sockets to eliminate 40ms delayed-ACK latency. Enforces dynamic ACK flow control with transport write buffer inspection (`>32KB` backpressure).
   - **Sub-Millisecond Dirty-Frame Skipping**: Uses fast NumPy stride sampling (`[::8, ::8, 0]`) and Win32 cursor tracking to skip JPEG compression and frame dispatch when desktop is static, reducing bandwidth to 0.001 Mbps and keeping ping at <15ms.
   - **Dynamic Auto-ABR FPS Scaling**: Client scales FPS (60 $\rightarrow$ 30 $\rightarrow$ 24 $\rightarrow$ 18 $\rightarrow$ 15 FPS) during network congestion to immediately free up 2.4GHz / 5GHz Wi-Fi spectrum.
   - **Android Hardware Low-Latency Lock**: Native Android layer holds `WifiManager.WIFI_MODE_FULL_LOW_LATENCY` (API 29+) while on `tab-screen` to disable mobile 802.11 power-save sleep jitter.

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
    "versionCode": 270,
    "versionName": "2.7.0",
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

## 7. Lemon Squeezy Pro Licensing & Anti-Tamper Security Architecture

### Live Store & Checkout Details
- **Store Domain**: `pcdeck.lemonsqueezy.com`
- **Product Name**: `PCDeck Pro — Lifetime License` ($3.99 one-time)
- **Live Checkout URL**: `https://pcdeck.lemonsqueezy.com/checkout/buy/5231b162-7c25-44f2-bcc3-f384839344c3`

### Official Lemon Squeezy License API Endpoints
Direct, public client-safe endpoints that require zero private API keys or custom cloud infrastructure:
- **Activation**: `POST https://api.lemonsqueezy.com/v1/licenses/activate` (`license_key`, `instance_name`).
- **Validation**: `POST https://api.lemonsqueezy.com/v1/licenses/validate` (`license_key`, `instance_id`).
- **Deactivation**: `POST https://api.lemonsqueezy.com/v1/licenses/deactivate` (`license_key`, `instance_id`).

### Cryptographic Hardware Binding & Anti-Tamper Engine (`server/license_manager.py`)
- **Hardware Fingerprint (HWID)**:
  - Windows client generates a unique machine ID combining the Windows `MachineGuid` registry key (`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography`) and hardware identifiers via SHA-256.
  - Prevents license sharing or copying `license.dat` across machines.
- **HMAC-SHA256 Tamper Protection**:
  - Valid licenses are saved as cryptographically signed base64 records in `~/.pcdeck/license.dat` (replaces legacy plaintext `.json`).
  - Payload signature: `sig = HMAC_SHA256(machine_hwid + license_key + instance_id + salt)`.
  - If a user edits `license.dat` or copies it to another machine, the HMAC verification fails instantly and the client reverts to the Free edition.
- **Zero Cloud Server Requirement**:
  - PCDeck relies entirely on Lemon Squeezy's hosted licensing API for activation, and internal HMAC cryptography for offline persistence. No external servers or monthly hosting costs required.

### Zero-Trust Local Server Enforcement (`server/main.py`)
- **Command Verification**: Replaced arbitrary `pro_status` client booleans with `pro_auth,{license_key},{instance_id}`.
- **Strict Server Caps**: The Python desktop server independently clamps screen streaming to **30 FPS maximum** for non-pro connections, regardless of what framerate the phone UI requests.
- **Seamless Local Network License Sharing**: If the host PC is activated as Pro, connected phones automatically receive `pro_unlocked,1` over WebSocket, unlocking 60 FPS and Pro features across devices on the local Wi-Fi.

### Android Anti-Tamper & Keystore Verification (`MainActivity.java`)
- **Signature Integrity Check**: `verifyApkIntegrity()` computes the SHA-256 fingerprint of the running APK's certificate at runtime.
- **Official Release Keystore Fingerprint**:
  - `AC496FA0DEE511959D0F686FCEEB681A334224D6453B43F5CF19855E368A74ED`
- **Cracking & Repackaging Defense**: If an attacker decompiles the APK, modifies JavaScript/Java code, and re-signs with tools like Lucky Patcher or MT Manager, `isProUser()` detects the certificate mismatch and locks all Pro features.

### Automated Code Obfuscation Pipeline (`tools/obfuscate_assets.py`)
- Automated AST-level obfuscation using `javascript-obfuscator` with RC4 string array encryption and control flow flattening.
- Integrated into the Android build pipeline via `python build_apk.py --obfuscate`.
- Keeps clean, readable source in `android_app/assets/app.js` while generating hardened, scrambled code inside distribution APKs.

### Developer Pro Testing Workflow (Zero Backdoors Standard)
- **Standard**: Hardcoded backdoor keys (e.g. `PCDECK-DEV-TEST-KEY-2026`) are strictly forbidden in production code.
- **Developer Commands**:
  - Generate HWID-bound local dev license: `python server/license_manager.py --activate-local-dev`
  - Check current license status: `python server/license_manager.py --status`
  - Revert to Free tier for testing: `python server/license_manager.py --deactivate`
  - Source-code run flag (dev only): `$env:PCDECK_DEV_PRO="1"` (strictly disabled in compiled `.exe`).

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
5. **Regenerate Checksums**: Run `python tools/update_checksums.py` to calculate exact SHA-256 digests and update the download table in `website/index.html` and `index.html`.
6. **Verify Website Structure & Integrity**: Run `python tools/verify_website.py` to confirm viewport tags, mobile menu scripts, header/main/footer tag balance, CSS variables, and layout bounds across all 62 website HTML files.
7. **Keep Context Synchronized**: Update `PROJECT_CONTEXT.md` and `WEBSITE_CONTEXT.md` in root and `website/` to reflect every architecture change.
8. **Commit & Push to GitHub**: Commit verified changes and push to `origin main` on `greson719/pcdeck`.

---

## 12. Wireless Debugging & Persistent Device Profile

- **Primary Test Devices**:
  - **Realme Narzo 50i (`RMX3231`)**:
    - **OS / API**: Android 11 (API 30, Realme UI R Edition).
    - **Screen**: 720×1600 (360 dpi), Landscape 1600×720.
    - **RF Band**: 2.4 GHz (Channel 3, 2422 MHz, 65 Mbps link speed).
    - **Pairing Architecture**: Android 11+ dual-port wireless security (ephemeral pairing port for `adb pair <ip>:<pair_port> <code>`, followed by connect on active wireless debugging port via `adb connect <ip>:<connect_port>`).
    - **Persistent Endpoint Cache**: Cached in `last_wireless_adb.txt` with sub-second auto-reconnect on daemon restarts.
  - **Motorola moto g35 5G (`manila_g` / `manila`)**:
    - **Device LAN IP**: `10.23.32.178` (Subnet `10.23.32.0/24`)
    - **Pairing Key / GUID**: `adb-ZD222QY2JF-Cnk1ww`
    - **Active Wireless ADB Port**: `36589`
- **Standard One-Click Wireless Deploy Command**:
  ```powershell
  adb connect <ip>:<port>; adb push PCDeck.apk /data/local/tmp/PCDeck.apk; adb shell pm install -r -d /data/local/tmp/PCDeck.apk; adb shell am start -n com.pcdeck.app/.MainActivity
  ```

---

## 13. Production Release v2.7.2 Specifications

| Target Binary | File Size | Version / Build | Verification Status |
| :--- | :--- | :--- | :--- |
| `PCDeck.exe` | **36.3 MB** | v2.7.2 (2.7.2.0 Win32 meta) | Passed · Standalone PyInstaller with auto-ping & update prompt |
| `PCDeck-Setup.exe` | **37.68 MB** | v2.7.2 | Passed · Inno Setup full installer with auto-upgrade |
| `PCDeck.apk` | **690.8 KB** | v2.7.2 (Code 272) | Passed · v1/v2/v3 aligned & signed with OTA update check |
| `PCDeck.aab` | **666 KB** | v2.7.2 (Code 272) | Passed · Google Play Bundletool signed |
| `PCDeck.msix` | **45.7 MB** | v2.7.2.0 | Passed · Store manifest validated |

- **Version Consistency Invariant**: All components (`pyproject.toml`, `MainActivity.java`, `app.js` `CURRENT_APP_VERSION_NAME`, `version_info.txt`, `version.json`, and website download cards) must strictly reflect the exact same version string and integer code.
- **Deprecation of `PCDeck_Package.zip` & Strict 3-Card Download Layout Invariant**:
  - `PCDeck.exe` bundles `PCDeck.apk` directly inside its PyInstaller asset payload and automatically serves it over the local Wi-Fi network at `GET /PCDeck.apk`.
  - Phone users scan the QR code and download `http://{LOCAL_IP}:8000/PCDeck.apk` directly from the PC host with zero internet needed.
  - `PCDeck_Package.zip` is completely deprecated, removed, and prohibited. Future agents and sessions must NEVER recreate or distribute `PCDeck_Package.zip`, nor add a 4th "ZIP" card to `#download-cards`. The download grid must strictly retain 3 cards: Windows (`.exe`), Android (`.apk`), and Linux (`.sh`).

---

## 14. Website Conversion Standard: Zero-Install "Scan & Control" Flow

- **Core User Friction Insight**: 95% of users looking for emergency mouse control do not want to download multiple apps or figure out whether they need an APK, ZIP, or EXE first.
- **The Golden 3-Step Flow**:
  1. **Run on PC**: Download & open `PCDeck.exe` on Windows (no install wizard or drivers required).
  2. **Scan the QR Code**: Point phone camera (iPhone or Android) at the screen's QR code.
  3. **Instant Control**: Trackpad & keyboard open immediately in Safari, Chrome, or any browser over local Wi-Fi.
- **Hierarchy of Download CTA (Strict 3-Card Layout)**:
  - **Primary**: Bold, glowing `Download PCDeck for Windows (.exe)`.
  - **Secondary**: Clean cards for Android APK (`691 KB`) and Linux 1-line script (`.sh`).
  - **Prohibition on ZIPs**: Never add a 4th ZIP card or ZIP bundle link. Never clutter the hero or download section with competing ZIP buttons.
- **Language & Tone Standard**: Zero technical jargon, zero AI buzzwords ("paradigm shifting", "AI-powered", "revolutionary"), and zero complex networking terms. Write for everyday humans whose physical mouse just broke.
- **QR Code Density & Scan Invariant**:
  - **Version 3 Grid Standard (29×29 Matrix = 841 Dots)**: The pairing URL must never exceed 48–52 characters (`http://{LOCAL_IP}:{SERVER_PORT}/connect?t={12_HEX_TOKEN}`).
  - **Zero Moiré Blur**: Under no circumstances allow the QR code to inflate into a dense Version 5+ matrix (37×37 = 1,369 micro-dots). Chunky Version 3 dots eliminate LCD/OLED monitor subpixel interference (Moiré) and scan in <20ms on budget phone cameras.
  - **Pure Optical Contrast**: QR codes must strictly render with pure solid black (`#000000`) on pure white (`#ffffff`) with a minimum `border=3` quiet zone. Never use inverted or colored (e.g. cyan-on-navy) modules for pairing QRs.

---

## 15. Brand Identity & Anti-AI-Slop Standard

- **Official Icon Design**: The authentic 3D mechanical mouse (Option A from `playstore_assets/App_Icon_512x512.png` / `natural_master.png`) is the permanent brand visual across all assets (`icon.png`, `icon-512.png`, `PCDeck.ico`, `app_icon.ico`, `favicon.ico`, `favicon.png`, `og-image.png`, and app mipmaps).
- **Icon Integrity & Multi-Resolution Invariant**:
  - **No Dark Flattening**: The authentic reflective silver/charcoal body highlights (`rgb_mean ~44`, body `[62, 71, 80]`) and electric cyan neon strip (`[62, 255, 255]`) must be strictly preserved. Never apply destructive threshold darkening that collapses the mouse body into an opaque, murky black blob (`rgb_mean ~15`).
  - **9-Frame Windows Multi-Res ICO**: All `.ico` files must bundle all 9 pre-rendered MIP frames: `[16x16, 20x20, 24x24, 32x32, 40x40, 48x48, 64x64, 128x128, 256x256]`. Micro frames ($\le 32\text{px}$) must include contrast enhancement so Windows File Explorer details view and taskbar shortcuts never render as dark boxes.
- **Installer Poster Banner Invariant**:
  - `WizardImageFile=WizardImage.bmp` (164×314) must always be a full-bleed, professional cyber-neon vertical banner poster featuring gradient background, soft radial neon back-glow, bold typography ("PCDECK"), tagline, and feature badges. Never leave it as an isolated small square floating in an empty black column.
  - Setup shortcuts must point to `{app}\PCDeck.ico` and call shell refresh (`ie4uinit.exe -show`) to invalidate stale Windows icon caches immediately upon installation.
- **Anti-AI-Slop Policy**:
  - Under no circumstances should AI-generated logos, abstract blobs, or non-mouse vector art replace the authentic mouse icon.
  - Option B was permanently disqualified following independent community feedback identifying loss of mouse silhouette and inappropriate shapes.
  - All copy must remain plainspoken, credible, and instrument-grade.

---

## 16. Web Analytics & SEO Performance

- **Universal Analytics Injection (`/va.js`)**:
  - Integrated via deferred script `<script defer src="/va.js"></script>` across all 62 static website HTML documents.
  - Tracks live visitors, page views, referring countries, and OS/device breakdown with standard Vercel Web Analytics (`/_vercel/insights/script.js`).
  - **Crawler & Search Bot Preservation**: Standard web traffic and search engine bots (Googlebot, Bingbot, Seobility, etc.) are allowed normal tracking to ensure crawlability signals and indexing metrics remain uninterrupted.
- **Owner Self-Visit Exclusion System**:
  - Automatically filters out developer/owner testing traffic so dashboard analytics reflect genuine visitor metrics.
  - **Exclusion Mechanisms**:
    1. **10-Year Persistent Cookie**: `pcdeck_analytics_optout=1` (stored with `path=/; max-age=315360000; SameSite=Lax`).
    2. **LocalStorage Key**: `localStorage.getItem('pcdeck_analytics_optout') === '1'`.
    3. **Query Parameter Bypass**: Visiting any URL with `?admin=1` immediately sets the opt-out cookie/localStorage and disables tracking.
    4. **Dedicated Console Page**: `/analytics-console/` allows 1-click toggling between "Tracking Disabled (Excluded)" and "Tracking Enabled".
    5. **Footer Diagnostic Button**: Live footer button (`#btn-analytics-toggle`) displays real-time status (`🛡️ Analytics: Excluded` or `Active`) and allows instant toggling.
- **Server File & Active User Tracking**:
  - Download metrics: Monitored in Vercel Dashboard Logs via requests to `/PCDeck.exe` and `/PCDeck.apk`.
  - Daily Active Users (DAU): Monitored via launch update pings to `/version.json`.
- **Search Console & Organic Ranking**:
  - High-traffic ranking assets: `/use-pc-without-mouse/`, `/connect-pc-to-pc-wifi/`, `/browser-pc-remote/`, `/control-linux-pc-from-phone/`, `/guides/`.
  - Schema.org rich results: Configured with `TechArticle`, `HowTo`, and `FAQPage` structured data with verified hash anchors.

---

## 17. Dual-Mode Gamepad & Driverless Input Architecture (Store & Anti-Cheat Standard)

- **Two Distinct Gamepad Interfaces & Their Strategic Purposes**:
  1. **On-Screen Streaming Gamepad HUD (`#screen-gamepad-overlay`)**:
     - **Use Case**: Remote Play / Handheld PC Gaming.
     - Designed for users streaming the PC screen directly to their phone display who want on-screen controls floating over the live 60 FPS video (similar to Steam Link or mobile cloud gaming).
     - **HUD Scale-Invariant Dragging Engine**:
       - Eliminates visual coordinate jumping and drift caused by `getBoundingClientRect()` scale compounding on scaled elements (`transform: scale(s)`).
       - Tracks element center in container space: `curCenterX = (rect.left + rect.width / 2) - containerRect.left`.
       - Calculates unscaled DOM placement: `domLeft = curCenterX - (offsetWidth / 2)`, storing normalized percentages.
       - Disables CSS transitions during drag (`.hud-elem.is-dragging { transition: none !important; }`).
       - New buttons spawn precisely at viewport dead-center without jumping.
     - **Add Key Modal Overhaul (`#hud-add-btn-modal`)**:
       - Replaced cramped, shrunken 1-column layout with a 4-column auto-fill responsive grid (`repeat(auto-fill, minmax(96px, 1fr))`) constrained by `width: 100% !important`.
       - Tactical 2-line badges (`.hud-key-pick-btn`): Top line bold primary PC key (`FIRE`, `AIM`, `SPACE`), bottom line neon-cyan controller/mouse mapping (`M-LEFT / RT`, `JUMP / A`).
  2. **Dedicated Wireless Gamepad (`#gamepad-container.modern-gamepad-deck`)**:
     - **Use Case**: Couch Controller for PC Monitor or TV.
     - **1-to-1 Ergonomic Layout Alignment (User Specification)**:
       - **Left Pod (`.gp-deck-left`)**:
         - Top: Primary Analog Stick (dark navy disc, `#ffd700` gold glowing border, `#0284c7` blue thumb with center dot).
         - Bottom: D-Pad diamond (4 circular buttons, gold borders, cyan directional arrows).
         - Bottom-Left Corner: Notched `LT` trigger block (angled top-right chamfer, blue fill, gold border, vertically stacked white "L" over "T").
       - **Center Pod (`.gp-deck-center`)**:
         - Top: `LSHLDR` & `RSHLDR` pill buttons (blue gradient, gold border, bold white text).
         - Mid: Circular View `[⧉]` & Menu `[≡]` buttons (gold borders, cyan icons).
       - **Right Pod (`.gp-deck-right`)**:
         - Top: `ABXY` diamond (gold borders; `Y` olive/yellow, `X` navy/blue, `B` burgundy/red, `A` forest/green).
         - Bottom: Secondary Analog Stick shifted inward (gold border, blue thumb).
         - Bottom-Right Corner: Notched `RT` trigger block (angled top-left chamfer, blue fill, gold border, vertically stacked white "R" over "T").
     - **Console Menu & Options Modal (`#gp-console-menu-modal`)**:
       - Cleans screen clutter by tucking all secondary controls into a dedicated modal opened by tapping Menu `[≡]`.
       - Houses: Layout Presets (Xbox 360, PlayStation, Racing, WASD/FPS), Gyro Motion Sensor (1-Tap Center, Active toggle, Settings), Hardware Controls (Sensitivity `1.0x`/`1.5x`/`2.0x`, Haptics toggle, Edit Layout), and Return to Trackpad.
- **Driverless SendInput Input Architecture (Store & Anti-Cheat Safe)**:
  - **Zero-Driver Requirement**: To ensure 100% compliance with Microsoft Store MSIX guidelines (Policy 10.2.9) and prevent bans from PC game anti-cheats (Easy Anti-Cheat, BattlEye, Ricochet, VAC), PCDeck does not require kernel-mode drivers (`ViGEmBus.sys`).
  - **Input Emulation Standard**:
    - **Movement (Left Stick)**: Direct vector-to-key translation to `W`, `A`, `S`, `D` with diagonal support.
    - **Camera Aim (Right Stick / Aim Pad)**: Ballistic mouse cursor deltas (`move_relative`) for fluid first-person / third-person looking.
    - **Triggers**: `RT` (Left Mouse Button / Primary Fire) & `LT` (Right Mouse Button / Aim Down Sights).
    - **Action Buttons**: `A` (`Space` / Jump), `B` (`Shift` / Sprint), `X` (`Ctrl` / Crouch), `Y` (`R` / Reload), `RB` (`E` / Interact), `LB` (`Q` / Skill).
  - **Anti-Cheat Immunity**: Standard Windows `SendInput()` scancodes are natively accepted by 99% of PC games without triggering anti-cheat kernel driver blocklists.
  - **Complete Driver Logic Purge (Mobile Assets & PC Client)**: All legacy driver installation code, prompts, warning banners, and UAC elevation logic (`#gamepad-driver-banner`, `#hud-driver-banner`, `#mic-driver-banner`, `#cam-driver-banner`, `#driver-trust-modal`, and `server/main.py` installer tasks) have been purged. Both client and host operate 100% driverless out of the box with zero setup warnings or admin prompts.
  - **Optional ViGEm Mode**: If the user already has ViGEmBus installed on their PC independently, PCDeck seamlessly connects to it; otherwise, it automatically operates in driverless Game Deck mode.

---

## 18. Jitter-Free & Anti-Gating Real-Time Microphone Architecture

- **Root Cause of Audio Jitter & Gating Resolved**:
  1. **Dual Transport Elimination**: In previous builds, the Android app concurrently transmitted audio over *both* TCP and UDP on port 8002. Interleaved dual-arrival created phase cancellation, comb-filtering, and queue overflow discards that manifested as rapid "gating" / stutter. Transport is now strictly managed: TCP is the primary low-latency stream; UDP functions exclusively as an inactive fallback.
  2. **Adaptive Jitter Buffer & Anti-Gating (40ms Watermark)**: `MicrophoneSink` implements an adaptive pre-buffering jitter buffer. Audio playback maintains a ~40ms buffer cushion before dispatching frames to the output stream, completely absorbing Wi-Fi packet arrival variance and preventing buffer starvation / driver underruns.
  3. **High-Precision WASAPI Device Selection**: `MicrophoneSink` prioritizes Windows WASAPI 2-channel virtual cable inputs (e.g. `CABLE Input (VB-Audio Virtual Cable) WASAPI`) over legacy MME 16-channel drivers, providing sub-10ms driver latency and zero frame jitter.
  4. **Natural Speech Processing (`VOICE_RECOGNITION`)**: `MainActivity.java` captures via `AudioSource.VOICE_RECOGNITION` instead of `VOICE_COMMUNICATION`. This avoids aggressive OEM hardware noise-gate DSPs that chop off the beginning and end of spoken words. WebAudio fallback similarly disables browser noise gates (`noiseSuppression: false`).
  5. **Throttled VU Meter IPC**: Android UI thread bridge updates are throttled from 100 FPS (every 10ms) to ~19 FPS (~53ms), eliminating thread contention between the audio capture loop and WebView UI.

---

## 19. PC-to-Phone Ultra-Low Latency Audio Streaming (Moonlight / AudioRelay Standard)

- **Root Cause of Audio Glitches & Stutter in PC-to-Phone Streaming Resolved**:
  1. **False Silence Injection Bug in AudioStreamer**: Previously, `AudioStreamer._run_capture()` checked `if now - self._last_audio_time >= (chunk_duration * 1.25)`. With 48kHz and 1024 frames, this timeout was 26.6ms. Normal Windows thread scheduling variance (±6–10ms) repeatedly triggered this condition ~25 times per second during active music and gaming audio, falsely injecting 21ms blocks of pure zero-silence into the stream. Replaced with a genuine 250ms silence detection threshold that only fires when the host PC is genuinely idle.
  2. **HALved Audio Chunk Size (512 Frames / 10.6ms)**: Reduced PyAudio/WASAPI capture chunk size from 1024 frames (21.3ms) to 512 frames (10.6ms), matching Sunshine/Moonlight industry low-latency standards and halving server capture latency.
  3. **Dedicated Low-Latency TCP Audio Stream Server (Port 8003)**:
     - `AudioStreamer.start_tcp_server(8003)` runs a dedicated non-blocking TCP broadcast socket on port 8003.
     - Sockets configured with `TCP_NODELAY=1` (disabling Nagle packet batching) and `SO_SNDBUF=65536` for instantaneous delivery of raw 16-bit 48kHz stereo PCM frames directly to connected mobile clients.
  4. **Direct Native Android `AudioTrack` Playback**:
     - `MainActivity.java` features `startNativeAudioStream(host, port)` and `stopNativeAudioStream()` powered by native Android `AudioTrack` configured with `USAGE_GAME`, `CONTENT_TYPE_MUSIC`, and `PERFORMANCE_MODE_LOW_LATENCY`.
     - Operates on a dedicated background thread with `THREAD_PRIORITY_URGENT_AUDIO`.
     - Bypasses WebView DOM and browser WebAudio rendering pipelines entirely, eliminating garbage collection pauses and continuing seamless playback even when the phone screen is turned off.
  5. **WebAudio Browser Fallback with Competitive PLL Jitter Buffer (35ms)**:
     - Prebuffer threshold tuned to 35ms (down from 65ms) to achieve instant response to PC game sounds and actions.
     - Phase-Locked Loop (PLL) drift tracking window set to 20ms - 55ms with gentle ±1.5% linear-interpolated fractional resampling, completely eliminating clicks, pops, or noticeable pitch distortion.

---

## 20. Screen Streaming Architecture & Competitor Analysis

- **Architectural Benchmark vs Competitors (Moonlight, Sunshine, Parsec, Monect, Unified Remote)**:
  - **Capture Engine**:
    - **PCDeck**: Persistent Win32 GDI `BitBlt` / `StretchBlt` with `CAPTUREBLT` and direct memory bitmap (`GetDIBits`). Steady-state capture overhead is **~1.4ms per frame** on Windows 11.
    - **Competitors (Sunshine / Parsec)**: DirectX DXGI Desktop Duplication API (DDA) or NVFBC in VRAM (<1-2ms).
    - **PCDeck Advantage**: Operates 100% driverless without requiring discrete gaming GPUs (NVIDIA/AMD/Intel QSV) or proprietary display hook drivers. Runs smoothly on every Windows PC, including budget laptops, Intel UHD/Iris Xe graphics, virtual machines, and office workstations.
  - **Compression & Encoding Pipeline**:
    - **PCDeck**: Ultra-fast SIMD Motion JPEG via `simplejpeg` (C extension wrapping libjpeg-turbo with Fast DCT and 4:2:0 subsampling). Encoding takes **~3.3ms per frame** (~12 KB - 18 KB per scaled frame). Sub-sampled NumPy dirty-frame detection (`raw_np[::8, ::8, 0]`) skips identical frames, reducing idle CPU usage to <0.5%.
    - **Competitors**: Hardware H.264/HEVC encoding. Lower bandwidth (5-15 Mbps vs 15-30 Mbps), but requires dedicated NVENC/AMF hardware encoder chips and external video codec binaries.
  - **Dynamic In-Flight Flow Control & Bufferbloat Prevention**:
    - **Frame Pacing**: The server streams frames over WebSocket (`/ws/screen`) paced by client in-flight receipt ACKs (`'a'`). If the client or Wi-Fi link slows down, `send_frames()` waits on `client_ready_event` (with a 35ms safety timeout) before dispatching the next frame. This strictly caps TCP socket queue depth to **1 frame**, completely eliminating multi-frame bufferbloat and latency buildup.
    - **Zero Background Load**: When the mobile client switches away from the screen tab, it dispatches `pause`. PCDeck immediately puts the desktop capture thread to sleep, reducing Wi-Fi load to **0.00 Mbps** and CPU usage to **0%**, dedicating 100% of network bandwidth to real-time trackpad and audio.

---

## 21. Natural Touch Scrolling & Screen Zoom Stability Architecture

- **Root Causes of Screen Zoom-Out & Low-Quality Glitch Resolved**:
  1. **Canvas Dynamic Box Jumps Eliminated**: Previously, `#screen-canvas` lacked explicit CSS sizing, sizing itself based on intrinsic image dimensions. When Auto-ABR adapted resolution during minor Wi-Fi jitter, the canvas box shrunk abruptly, creating a sudden visual "zoom out" accompanied by blocky pixels due to `image-rendering: pixelated;`.
     - **Fix**: Styled `#screen-canvas` with `width: 100%; height: 100%; object-fit: contain;` and smooth bilinear filtering (`image-rendering: auto;`). Changing internal stream resolution never alters the visual layout box or creates jagged pixel blocks.
  2. **Minimum Zoom Clamped to 1.0 (Fit-to-Screen)**: Pinch-to-zoom minimum scale was previously set to `0.70`, allowing accidental inward pinches or two-finger touches to zoom out into an undersized viewport with black borders. Clamped minimum zoom strictly to `1.0` so the desktop always fills the display frame perfectly.
  3. **Protected Auto-ABR Quality Floor**: Raised Auto-ABR thresholds so native 1080p scale (`scale = 1.0`) is preserved for all RTTs up to 110ms. When network load increases, Auto-ABR throttles framerate from 60 to 30 FPS first (saving 50% bandwidth without any loss of visual sharpness), maintaining a strict quality floor ($\ge 60$) and scale floor ($\ge 0.75\times$).

- **Root Causes of Unnatural / Jerky Touch Scrolling Resolved**:
  1. **Server-Side 120-Unit Notch Stall Eliminated**: Previously, `WindowsInputController.scroll()` held back touch movements until incoming deltas accumulated to a full legacy `WHEEL_DELTA` (120 units = ~100 PC pixels). Small or gentle finger drags were swallowed across 5–8 frames (~100ms lag), followed by a sudden jarring 100-pixel jump.
     - **Fix**: Upgraded to modern Windows high-precision sub-tick dispatch (`SMOOTH_WHEEL_STEP = 24`, exactly 1/5th of a 120 notch). Dispatches smooth, responsive micro-deltas to Chrome, Edge, and Windows 11 apps every frame with zero stall.
  2. **1:1 Natural Finger-Tracking Sensitivity**: The client scroll multiplier was previously `scaleY * 1.25` (~3.75x hypersensitive), sending content flying 4x faster than the finger swipe. Tuned multiplier to `scaleY * 0.45`, achieving exact 1:1 physical finger-to-content tracking.
  3. **Tactile Kinetic Momentum Deceleration**: Tuned momentum deceleration friction from `0.93` (overly slippery 3-second glide) to `0.88`, providing a crisp, natural kinetic flick that smoothly glides and settles in ~600ms matching iOS/Android native swipe behavior.

---

## 22. Web Control PC Audio Streaming & Anti-Jitter Architecture

- **Context & Diagnosis**:
  - Direct Android native audio streaming (`AudioTrack` over TCP port 8003) works smoothly without dropouts because raw bytes are pushed directly over TCP without intermediate queue capping.
  - In contrast, the browser/Web Remote client (`/ws/audio` + WebAudio `AudioWorklet`) experienced periodic audio stuttering, fluttering, and micro-gaps.
- **Root Causes Diagnosed & Fixed**:
  1. **Server-Side Audio Queue Choke (`qsize() > 4`)**:
     - `AudioStreamer._broadcast_chunk()` capped subscriber queues to max 4 chunks (only 42.6ms of buffer headroom).
     - When the asyncio event loop had minor bursts (screen capture, JPEG encoding, or network tasks), `queue.qsize()` exceeded 4, and the server actively threw away audio chunks (`queue.get_nowait()`).
     - **Fix**: Raised queue capacity from 4 to 32 chunks (~340ms) and queue maxsize to 64, providing generous cushion against event-loop scheduling variance. Raised write buffer drop threshold in `server/main.py` from 32KB to 64KB.
  2. **Cascading Re-Prebuffering Silence Lockout**:
     - On the client side (`static/audio-worklet-processor.js`, `static/app.js`, and `android_app/assets/`), whenever a Wi-Fi packet arrived 10ms late and `available <= 2`, the processor set `isPrebuffering = true`.
     - In subsequent `process()` calls, it muted output (`outL.fill(0)`) until a full prebuffer threshold accumulated. A momentary 5ms Wi-Fi delay was artificially magnified into a 35ms silence blackout.
     - **Fix**: Eliminated `isPrebuffering = true` from buffer underrun starvation handling. Prebuffering is strictly restricted to initial stream startup or explicit reset. Incoming packets are played **immediately** without silence penalties.
  3. **Adaptive Phase-Locked Loop (PLL) Retuning (50ms - 90ms Cushion)**:
     - The previous 20ms - 55ms target window was too thin for browser WebSockets over Wi-Fi, leaving only 2 chunks of cushion before hitting starvation.
     - Upgraded initial prebuffer to 60ms and retuned PLL tracking to maintain a 50ms - 90ms cushion (centered at ~70ms). If `bufferedMs < 50`, it gently resamples at 98.5% to accumulate cushion; if `bufferedMs > 85`, it resamples at 101.5% to smoothly drain backlog.
  4. **Zero-Discontinuity Micro-Ramps**:
     - Added an exponential micro-fade ramp if `available <= 1` mid-quantum, preventing any step discontinuities or audible clicks.
     - Added a 220ms hard safety ceiling to fast-forward stale backlogs if the browser tab sleeps or pauses.

---

## 23. UI/UX Standards, Gateway Routing & Layout Ergonomics

- **Zero-Popup Gateway QR Standard (`/connect`)**:
  - Scanning the pairing QR code or opening `/connect` must never trigger automatic popups, download dialogs, or unsolicited modal overlays.
  - The gateway displays balanced 50/50 split cards:
    - **Web Remote**: 3 bullet points + 1 primary button (`Launch Web Remote`).
    - **Android App**: 3 bullet points + 1 secondary button (`Download APK`).
  - Both cards maintain identical structural height, typography, and clean visual parity.

- **Single Floating On-Screen HUD FAB Invariant**:
  - The in-display gaming HUD toggle is strictly located on the floating on-screen FAB (`#btn-screen-hud-fab`) over the screen streaming viewport.
  - Redundant or duplicate HUD toggle buttons on the top titlebar/header (`#btn-screen-gamepad-hud`) are permanently removed to keep the titlebar uncluttered.

- **Inline SVG Dock Navigation Standard**:
  - All 7 dock navigation tabs (`Screen`, `Trackpad`, `Gamepad`, `Keys`, `Files`, `Media`, `Settings`) must use direct inline SVG paths (`<path>`, `<rect>`, `<circle>`) with single `viewBox="0 0 24 24"`.
  - Never use external `<svg><use href="#..."></use></svg>` references for core navigation icons, preventing Chrome/WebKit double-viewBox cutoff bugs in both vertical dock (landscape) and horizontal nav (portrait).

- **Responsive 2-Column Landscape Control Layout (`#tab-keyboard`)**:
  - On landscape mobile screens, control pages such as the virtual keyboard arrange content in a 2-column side-by-side grid (`1.05fr 0.95fr` for Live Typing and Full Numpad).
  - Keeps all interactive controls within the viewport height without requiring vertical scrolling or overflowing beyond the bottom edge of the screen.

- **File Transfer Cancellation & X Button Invariant**:
  - Closing the file transfer progress card via the X button (`.transfer-close-btn` / `#btn-transfer-close`) must actively abort the live `XMLHttpRequest` (`activeUploadXhr.abort()`), set `activeUploadCancelled = true` to halt the remaining queue, cancel download batches, and show a confirmation toast.
  - Never allow transfer progress modals to hide while transfers continue running invisibly in the background.

- **File Manager Long-Press Selection Mode Standard**:
  - File browser items (both PC files and Phone files) hide selection checkboxes and multi-select bars by default to prevent visual clutter.
  - A long-press (480ms hold + haptic vibration) enters selection mode, selects the target file/folder, reveals checkboxes, hides individual per-item action rows, and opens the batch action bar.
  - While in selection mode, single taps toggle item selection.
  - Tapping the batch bar X or clearing all selections automatically exits selection mode and restores standard tap-to-open and per-item action buttons.

- **Browser File Download Direct Stream Invariant (No `target="_blank"`)**:
  - Direct browser downloads via `<a download="..." href="...">` must never use `target="_blank"`. On Android Chrome / mobile browsers, `target="_blank"` spawns an orphaned blank tab that Android freezes after the initial 10 TCP packets (14.48 KB = TCP `initcwnd`), stalling the download indefinitely.
  - Server endpoint `/api/fs/download` uses Starlette `FileResponse` for native non-blocking async chunk streaming, automatic RFC 6266 `Content-Disposition`, and standard HTTP 206 `Range` resume.
  - `SmartGZipMiddleware` and `track_client_and_set_token` middleware bypass streaming routes (`/api/fs/download`, `/api/fs/upload`) to avoid response buffering or cookie header mutation during binary transfers.

- **Agent Communication Standard (Caveman Mode)**:
  - Keep all agent communication terse, direct, and high-signal with zero fluff or conversational filler.

- **IndexNow SEO & Search Engine Indexing Standard**:
  - **Protocol Key**: `2b967b3e45cd4a0cafab08e647e1fc47`
  - **Verification File URL**: `https://pcdeck.vercel.app/2b967b3e45cd4a0cafab08e647e1fc47.txt`
  - **Key File Locations in Repo**:
    - Root: `2b967b3e45cd4a0cafab08e647e1fc47.txt`
    - Mirror: `website/2b967b3e45cd4a0cafab08e647e1fc47.txt`
  - **Automated Workflow**: `.github/workflows/indexnow.yml` parses `website/sitemap.xml` and dispatches immediate batch indexing pings to Bing/IndexNow on every push touching HTML, site guides, or `sitemap.xml`.
  - **Environment Storage**: `.env` and `.env.example` store `INDEXNOW_KEY`, `INDEXNOW_KEY_LOCATION`, and `INDEXNOW_HOST`.

---

## 24. Search Engine Optimization (SEO) & Webmaster Invariants

- **Google Search Console (GSC) Production State & Protocol**:
  - **Property**: `https://pcdeck.vercel.app/`
  - **Sitemap Submission**: `/sitemap.xml` verified as **Success** (Green) on Sep 14, 2026 with exactly **23 discovered pages**.
  - **GSC Indexing Lifecycle & Queue Dynamics**:
    - Status *"Discovered - currently not indexed"* represents normal crawl backlog for young domains with low initial authority, NOT an error, duplicate flag, or penalty.
    - GSC Overview / Page Indexing charts update with a 3–10 day aggregation lag; the dashboard is not a real-time monitor.
    - Manual "Request Indexing" has a hard daily quota (~10–12 requests/day per property). Never attempt bulk manual submission; allow the active sitemap discovery to ingest pages automatically.
    - Automated alerts for traffic dips (e.g., "-79% impressions on `/use-pc-without-mouse/`") trigger routinely on low baseline sample sizes (<10 clicks) and do not represent technical regressions.

- **Microsoft Bing Webmaster Tools Production State & Protocol**:
  - **Property**: `https://pcdeck.vercel.app/`
  - **Sitemap Status**: Resubmitted Sep 14, 2026; actively in **Processing** state covering all 23 URLs.
  - **IndexNow Protocol**:
    - Active API Key: `2b967b3e45cd4a0cafab08e647e1fc47`
    - Key Verification URL: `https://pcdeck.vercel.app/2b967b3e45cd4a0cafab08e647e1fc47.txt` (HTTP 200)
    - All 23 URLs submitted to `https://www.bing.com/indexnow` returning `HTTP 202 Accepted`.
    - Automated CI/CD ping pipeline configured in `.github/workflows/indexnow.yml` on pushes modifying `website/**`, HTML, or `sitemap.xml`.
  - **Bing Dashboard Cache Invariant**:
    - Home dashboard recommendation banners (*"Important new pages are missing from your sitemaps"*, *"Set up IndexNow"*) are batch-computed on a 24–48 hour crawl/scan cycle.
    - Do not re-edit code or re-upload keys when these banners persist immediately after deployment; verify live status directly under the **Sitemaps** and **IndexNow** sidebar tabs.

- **On-Page SEO & Structured Data Technical Standards**:
  - **Page Length Constraints**:
    - `<title>` tags must strictly remain between **50 and 64 characters** (Bing limit: 15–65 characters).
    - `<meta name="description">` tags must strictly remain between **140 and 155 characters** (Bing limit: 25–160 characters).
  - **Structured Data Standards**:
    - Include `prefix="og: https://ogp.me/ns#"` on `<html>` across all guide templates.
    - All guide pages must supply fully populated JSON-LD schemas (`TechArticle`, `HowTo`, `BreadcrumbList`) with explicit `image`, `publisher.logo`, `author.logo`, `tool`, and step hash-anchors (`#step-1`..`#step-4`).
  - **Seobility & Semantic HTML Audit Invariant**:
    - Strictly forbid empty formatting tags (such as `<b></b>` or `<strong></strong>`) used as visual spacers or structural styling (e.g. monitor stand CSS artwork).
    - All non-semantic visual shapes must use `<span>` or pseudo-elements (`::before`/`::after`) with CSS classes. Empty bold tags trigger Critical Errors in SEO crawlers (Seobility, Ahrefs, SEMrush).
  - **Multilingual SEO & Internationalization Standards**:
    - Primary localized editions deployed: Spanish (`/es/`) and Portuguese (`/pt/`).
    - Every localized page must provide bidirectional `<link rel="alternate" hreflang="..." href="...">` tags covering `en`, `es`, `pt`, and `x-default`.
    - Localized pages maintain native FAQPage JSON-LD schemas and localized download CTA buttons targeting the exact same canonical binaries (`/PCDeck.exe`, `/PCDeck.apk`).
  - **Routing & Crawler Directives**:
    - `robots.txt` disallows raw shell scripts (`/*.sh$`) to prevent search engine bots from expecting non-HTML installation scripts in XML sitemaps.
    - `vercel.json` enforces `"trailingSlash": true` to eliminate 308 redirect loops between slash and non-slash canonical URLs.
    - Full parity is strictly maintained between root files and `website/` distribution mirror.

---

## 25. User-Mode Virtual HD Webcam Architecture & Invariants

- **Zero-Kernel User-Mode DirectShow Pipeline**:
  - **Technology**: `drivers/UnityCaptureFilter64.dll` (157 KB 64-bit DirectShow COM filter) interfaced via `pyvirtualcam`.
  - **User-Space Self-Registration (`HKCU`)**:
    - Registers silently into `HKEY_CURRENT_USER\Software\Classes\CLSID\{5C2CD55C-92AD-4999-8666-912BD3E70010}` and `CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{5C2CD55C-92AD-4999-8666-912BD3E70010}`.
    - **Zero Administrator Rights**: Requires no UAC elevation, no installer hooks, no system reboots, and no kernel `.sys` drivers.
    - **Microsoft Store & MSIX Compliant**: Safe for Microsoft Store certification and sandboxed packaging because no kernel drivers are used.
  - **Compatibility**:
    - Windows DirectShow and Media Foundation instantly recognize the device as **"Unity Video Capture"**.
    - All PC web browsers (Chrome, Edge, Firefox), external testing sites (`webcamtests.com`, `webcammictest.com`), and desktop conferencing software (Zoom, Teams, Discord, Google Meet, OBS) detect the phone camera as a native HD webcam.
  - **Zero Breakage Invariant**:
    - Never delete `drivers/UnityCaptureFilter64.dll` or unbind `pyvirtualcam`.
    - Always bundle `drivers;drivers` in `build_exe.py` and `PCDeck.spec`.
    - Maintain `/ws/cam` streaming, standby frames, and aspect-ratio preserving fit.

---

## 26. Touch Gesture Engine Calibration & Drag State Machine (v2.7.1)

- **Single-Finger Tap (<220ms, <8px movement)**: Dispatches Left Click (`sendBinaryClick('left')`).
- **Single-Finger Long Press (350ms hold, <14px movement)**:
  - Dispatches `sendBinaryMoveAbs(curNorm.x, curNorm.y)` followed by `sendBinaryTouchDown(curNorm.x, curNorm.y, 'left')`.
  - Sets `isLongPressTriggered = true` and `isLongPressDrag = true` with haptic feedback (`vibrate(40)`) and visual indicator ("Drag to Move ✋").
  - Subsequent single-finger dragging dispatches real-time coordinates upstream via `sendBinaryTouchMove(curNorm.x, curNorm.y)`.
  - Releasing finger in `touchend` immediately sends `sendBinaryTouchUp(norm.x, norm.y, 'left')` with drop confirmation haptics (`vibrate(30)`).
- **Two-Finger Tap**: Dispatches Right Click (`sendBinaryClick('right')`) with dual-touch haptic confirmation.
- **Dedicated Scroll Strip / Multi-Touch Pan**: Dispatches calibrated `sendBinaryScroll(0, dy)` wheel steps.

---

## 27. Android SDK & APK Package Invariants (Android 5.0 to 16+ Compatibility)

- **Version Strategy & Build Directives**:
  - `minSdkVersion="21"`: Guarantees installability and runtime execution on **Android 5.0 (Lollipop)** through Android 16+ without deprecation blocks.
  - `targetSdkVersion="34"`: Strictly targets stable **Android 14 LTS**.
    - **Never** set `targetSdkVersion` to unreleased preview SDK levels (such as API 36 during dev previews), which triggers `INSTALL_PARSE_FAILED_NOT_APK` ("Package appears to be invalid") on consumer Android 10–15 devices.
    - Android 15 & 16 use official backward-compatibility shims to run `targetSdkVersion 34` apps seamlessly.
    - Satisfies Android 14+ minimum target SDK sideload security rules (which reject apps with `targetSdkVersion < 24`).
- **Zero Native ELF `.so` Library Invariant**:
  - `PCDeck.apk` contains pure `classes.dex` bytecode, Android XML resources, and HTML5 assets running inside the system Chromium WebView.
  - Contains zero native C/C++ `.so` files in `lib/`.
  - Immune to Android 15/16 16KB page-size memory alignment rejections and CPU architecture incompatibilities (100% universal across ARM64, ARMv7, x86, and x86_64).
  - Do **not** re-add `android:extractNativeLibs="false"` to `AndroidManifest.xml` as it causes package parse errors on several OEM Android variants (Samsung OneUI, Xiaomi HyperOS).
- **Signing & Alignment Pipeline**:
  - 4-byte aligned via `zipalign -v 4`.
  - Multi-scheme signed via `apksigner`: v1 (JAR signing), v2 (APK Signature Scheme v2), and v3 (APK Signature Scheme v3) using SHA-256 with 2048-bit RSA keys (`pcdeck_release.keystore`).
- **Dynamic API Level Branching**:
  - All Android OS features in [MainActivity.java](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/android_app/src/com/pcdeck/app/MainActivity.java) are guarded with explicit `Build.VERSION.SDK_INT` runtime checks:
    - API 21+ (Android 5.0): Hardware-accelerated WebView, basic fullscreen flags, install-time permissions.
    - API 23+ (Android 6.0): Dynamic runtime permission requests (`CAMERA`, `RECORD_AUDIO`, `STORAGE`).
    - API 26+ (Android 8.0): Adaptive notification channels and background priority.
    - API 29+ (Android 10): Scoped storage transitions and Wi-Fi low-latency lock (`WIFI_MODE_FULL_LOW_LATENCY`).
    - API 33+ (Android 13): Granular media permissions (`READ_MEDIA_IMAGES`, `POST_NOTIFICATIONS`).
    - API 34+ (Android 14): Edge-to-edge system bar insets and predictive back gestures.

---

## 28. Universal Multi-Browser & Multi-OS Web Controller Compatibility

- **Direct Web Access (`http://<PC-IP>:8000`)**:
  - Operates purely on standard HTML5, CSS3, Pointer Events, and WebSockets.
  - Requires zero software installation on the remote client device.
- **Cross-Platform Compatibility Matrix**:
  - **Android Browsers (Chrome, Samsung Internet, Firefox, Edge)**: 100% touch, trackpad, screen streaming, audio streaming, macros, gamepad, and haptic feedback.
  - **iOS / iPadOS Safari & Chrome**: 100% trackpad, gestures, macros, gamepad, and screen streaming. PC audio loopback unlocked on first user tap (`AudioContext` autoplay policy). Haptic vibration (`navigator.vibrate`) gracefully skipped per Apple WebKit constraints.
  - **Windows, macOS, Linux Browsers (Chrome, Edge, Firefox, Brave, Safari)**: 100% remote trackpad, keyboard, macros, media controls, screen streaming, and audio streaming.
  - **Smart TVs & Gaming Consoles (PS5, Xbox, Samsung Tizen)**: 100% browser pointer & screen view support.
- **PWA Standalone Mode**:
  - Supports "Add to Home Screen" on both iOS and Android for borderless, full-screen native-like operation (`apple-mobile-web-app-capable: yes`, `manifest.json`).
- **Hardware Sink vs. Web Sandbox Invariant**:
  - Direct browser camera/mic requires a Secure Context (HTTPS or localhost) due to browser WebRTC policies.
  - The native Android APK (`PCDeck.apk`) uses direct Android SDK APIs (`android.hardware.camera2`, `AudioRecord`), completely bypassing browser HTTP sandbox restrictions.

---

## 29. 2.4 GHz USB Wi-Fi Dongle Adaptive Latency Engine & RF Hardening

- **Physical Bottlenecks on 2.4 GHz USB Dongles (RTL8188FTV / MT7601U)**:
  - **Co-Channel Interference**: 2.4 GHz spectrum has only 3 non-overlapping channels (1, 6, 11) crowded by neighboring routers and Bluetooth devices.
  - **USB 3.0 Radio Frequency Interference (RFI)**: Unshielded USB 3.0 ports emit broad-spectrum RF noise around 2.4 GHz–2.5 GHz directly into nano-dongle antennas, causing packet drops and sudden latency spikes up to 200ms+.
  - **Dongle Thermal Throttling**: Compact nano-dongles have minimal thermal dissipation, dropping frames under sustained high-throughput transmission.
- **Closed-Loop ACK Drop Timeout Invariant**:
  - In dynamic Wi-Fi QoS scaling (`WiFiLatencyManager`), the ACK drop timeout must **never** exceed the inter-frame capture interval:
    $$\text{timeout} \le 0.85 \times \left(\frac{1000}{\text{target\_fps}}\right)$$
  - Prevents the desktop capture loop from stalling during packet delivery delays, maintaining steady 20–30 FPS flow without visual hitching.
- **Dynamic Auto-ABR RTT-Aware Pacing**:
  - Under high RTT (>80ms) on 2.4 GHz networks, the stream encoder steps down FPS and compression quality progressively (60 -> 30 -> 24 -> 20 -> 15 FPS), immediately relieving airtime pressure and preserving low-latency control responsiveness.

---

## 30. Android 11+ Wireless ADB Pairing & Connection Resilience

- **Dual-Port Pairing Architecture**:
  - Android 11+ separates the dynamic pairing port (used once with a 6-digit code for `adb pair <ip>:<pair_port> <code>`) from the persistent wireless connection port (`adb connect <ip>:<connect_port>`).
  - Desktop pairing dialogs support dual-field entry and two-phase dispatch, eliminating connection failures caused by connecting to the pairing port.
- **Persistent Wireless ADB Endpoint Cache (`last_wireless_adb.txt`)**:
  - Caches the last verified wireless endpoint on the host machine.
  - On ADB daemon restarts or USB unplugs, `adb_preflight()` automatically checks and reconnects to the cached wireless device in <500ms.
- **Unsuppressed Interactive scrcpy Mirroring**:
  - `server/main.py` launches `scrcpy.exe` with standard process flags (`creationflags=0`), ensuring the SDL3 device mirror window renders interactively without silent background suppression.

---

## 31. Universal Web Game Dual-Emission Engine & Minimalist Console Gamepad

- **Web Browser Game Input Mechanics (HTML5 Canvas, WebGL & Native Titles)**:
  - Web browser games execute inside standard browser contexts (Chrome, Edge, Firefox).
  - These games exclusively listen to browser DOM `keydown` / `keyup` events (`ArrowRight`/`D` for Throttle, `ArrowLeft`/`A` for Brake/Reverse, `Space` for Jump/Handbrake).
  - Virtual Xbox 360 controller packets (`XUSB_REPORT`) via ViGEmBus driver are not recognized by HTML5 games lacking explicit HTML5 Gamepad API polling loops.
- **Universal Dual-Emission Architecture (`gamepad_manager.hybrid_mode`)**:
  - Automatically dual-emits both virtual Xbox 360 controller packets (via ViGEmBus) AND Windows SendInput keyboard events:
    - **Right Trigger (RT / Gas)**: Sends `Right Arrow` and `D` keystrokes.
    - **Left Trigger (LT / Brake)**: Sends `Left Arrow` and `A` keystrokes.
    - **D-Pad Right / Left**: Sends `Right Arrow` / `Left Arrow` and `D` / `A`.
    - **D-Pad Up / Down**: Sends `Up Arrow` / `Down Arrow` and `W` / `S`.
    - **A / Cross Button**: Sends `Space` (Jump / Select).
    - **B / Circle Button**: Sends `C` / `Escape`.
    - **Analog Left Stick**: Resolves stick deflection into directional keystrokes in real time.
  - Zero game interference: Held keys are tracked in a dedicated thread-safe set (`_held_fallback_keys`) and reliably cleared on button release or `reset_all()`.
- **Pure Minimalist Console Deck (Exact 1:1 Layout Spec)**:
  - Gamepad interface displays strictly 8 primary control clusters with zero on-screen clutter:
    1. Left Analog Stick (disc)
    2. D-Pad (4 circular diamond buttons)
    3. Inset LT Trigger (bottom-left)
    4. LSHLDR & RSHLDR pill buttons (top center)
    5. Circular View `[⧉]` & Menu `[≡]` buttons (mid center)
    6. ABXY Diamond (top right)
    7. Right Analog Stick (disc)
    8. Inset RT Trigger (bottom-right)
  - All secondary buttons (L3, R3, trackpad strips, header, docks, layout presets, sensitivity, haptics, layout editor, return to trackpad) are completely housed within the Menu `[≡]` modal (`#gp-console-menu-modal`).

---

## 32. Gamepad Standalone Architecture, Zero-Snapping Layout Editor & Ergonomic Corner Insets

- **Dedicated Gamepad Section (`#tab-gamepad`)**:
  - `#gamepad-container` moved completely out of `#tab-trackpad` into its own standalone `<section id="tab-gamepad" class="tab-view">`.
  - `#tab-trackpad` is 100% clean and dedicated to mouse touchpad operations with zero joystick/gamepad options or bleed-through.
  - Dock and header switching triggers `switchTab('tab-gamepad')` and `switchTab('tab-trackpad')` cleanly with auto activation/deactivation.
- **Prominent Close Joystick Actions**:
  - Added full-width, high-contrast `[✕ CLOSE JOYSTICK / EXIT TO TRACKPAD]` button at the very top of `#gp-console-menu-modal`.
  - Added dedicated `[Close Joystick]` button in `#gp-editor-toolbar`.
  - Maintained `[← Return to Trackpad]` in bottom modal footer; all handlers synchronously call `closeGpConsoleMenu()`, `setGamepadMode(false)`, and `switchTab('tab-trackpad')`.
- **Zero-Snapping & Scale-Invariant Drag Engine**:
  - Fixed position context: Changed `.gp-deck-side` and `.gp-deck-center` to `position: static` (with `margin-top: auto` for bottom pods).
  - Adopted proven HUD center-delta dragging algorithm (`elemCenter = (rect.left + rect.width / 2) - containerRect.left; newCenter = elemCenter + (e.clientX - startPointer.x)`).
  - Eliminates DOM offset parent mismatch; eliminates snapping, jumping, and scale-distortion on drag.
- **Ergonomic Corner Insets & Button Spacing**:
  - Inset corner triggers (`.gp-corner-trigger`) away from physical phone corners (`bottom: clamp(10px, 2.2vh, 20px); left/right: clamp(14px, 2.8vw, 26px)`).
  - Removed sharp polygon clip paths and added `border-radius: 14px` for comfortable thumb rest.
  - Increased `.modern-gamepad-deck` padding and pod margins to eliminate bezel-crowding on modern smartphones.
- **Universal Mode Branding**:
  - Completely purged casual/external site mentions ("Poki"); renamed presets and status to `Universal (Web & PC)` and `UNIVERSAL HYBRID (WEB + PC)`.

---

## 33. Community, Suggestions & Complaints Architecture

- **Direct Creator Support & Community Feedback Channels**:
  - Direct communication channels integrated into desktop app (`static/index.html`), Android native APK (`android_app/assets/index.html`), and public website (`index.html`, `website/index.html`).
  - **Official Reddit Feedback Thread**: Direct link to the official feedback thread on Reddit for public bug reports, feature suggestions, and community discussions.
  - **1-Click Direct Email Copy**:
    - Email: `dogonews67@gmail.com`.
    - Primary action writes email to system clipboard via `navigator.clipboard.writeText()` with visual "✔ Copied to Clipboard!" toast confirmation.
    - Fallback handler for unsupported browsers / sandboxes triggers `mailto:dogonews67@gmail.com?subject=[PCDeck]%20Feedback`.
    - Direct Web Gmail link (`https://mail.google.com/mail/?view=cm&fs=1&to=dogonews67@gmail.com&su=[PCDeck]%20Suggestions%20%26%20Complaints`) for users without a local desktop mail client.
- **Website `#community` Section & DOM Invariant**:
  - The suggestions and complaints section `<section class="feedback-section" id="community">` must **always** reside as a direct child of `<main>`.
  - **Never** nest `#community` inside fixed overlays or modal backdrops (such as `#emergency-guide-modal` with `position: fixed; inset: 0; opacity: 0; pointer-events: none;`).
  - Styled with explicit `scroll-margin-top: 74px;` so fixed top navigation bars never obscure the section heading upon arrival.
- **Smooth-Scroll Navigation Binding (`scrollToTarget`)**:
  - Top navigation bar link `a[href="#community"]`, footer links, and floating feedback pills are bound to `scrollToTarget()`.
  - Calculates dynamic element offset: `target.getBoundingClientRect().top + window.pageYOffset - navH - 8` with smooth animation (`behavior: 'smooth'`).
  - Page-load hash handler automatically scrolls to `#community` if visited directly via `https://pcdeck.vercel.app/#community`.
- **Android Native Intent Dispatch (`MainActivity.java`)**:
  - `WebViewClient.shouldOverrideUrlLoading()` intercepts `mailto:` and `https://www.reddit.com/...` links.
  - Dispatches native Android `Intent.ACTION_VIEW` or `Intent.ACTION_SENDTO` to open external email clients (Gmail, Outlook) or the native Reddit app instead of throwing WebView navigation errors.

---

## 34. Website Download Cards Alignment & Above-The-Fold Conversion Standards

- **Direct Scroll Anchor (`#download-cards`)**:
  - Hero and top navigation "Download" buttons are bound to `#download-cards` instead of the top of `#download`.
  - Keeps the primary executable (`PCDeck.exe`) and Android APK (`PCDeck.apk`) action cards directly visible and centered above the fold upon arrival.
- **Header Padding & Vertical Spacing Invariant**:
  - Section `#download` header maintains compact vertical padding (`padding: 36px 0 20px` or similar) with tight heading margins (`margin-bottom: 8px`).
  - Eliminates unnecessary dead space so users on 1080p, 1440p, laptops, tablets, and phones do not have to scroll past multiple screen heights of marketing headers to find download buttons.
- **Action Parity & Verified Checksums**:
  - Both cards feature real-time SHA-256 verification links (`#verify`) and verified offline capabilities.

---

## 35. Technical Guides Readability & Anti-Wall-of-Text Standards

- **Visual-First Scannability Invariant**:
  - In-depth technical guides (e.g., `/browser-pc-remote/`, `/control-linux-pc-from-phone/`, `/connect-pc-to-pc-wifi/`, `/guides/`) must never present unbroken walls of text.
  - Every technical guide must feature high-resolution interface figures and architecture diagrams:
    - `hero-suite.png`: Complete PCDeck ecosystem overview.
    - `qr-pairing.png`: Local Wi-Fi pairing and QR code scan demonstration.
    - `trackpad-phone.png`: Phone trackpad with multi-touch gestures and buttons.
    - `screen-stream.png`: Real-time PC screen streaming with floating toolbar.
    - `file-transfer.png`: High-speed local LAN file transfer interface.
  - Figures are marked up with semantic `<figure class="guide-figure">`, dark glassmorphic borders, rounded corners (`border-radius: 10px`), and descriptive `<figcaption>`.
- **30-Second Rapid Connection Checklist**:
  - Every technical guide must include a prominent, boxed 4-step checklist (`.guide-quickstart-card`) right below the hero or introduction:
    1. **Download & Launch**: Run `PCDeck.exe` on Windows or 1-line script on Linux.
    2. **Same Local Wi-Fi**: Confirm both devices share the same router or phone hotspot.
    3. **Scan QR Code**: Open phone camera or browser to instant pairing URL.
    4. **Instant Control**: Immediate trackpad, keyboard, and screen streaming access.
  - Solves emergency user queries in under 30 seconds while retaining deep technical analysis underneath for search engine topical authority.

---

## 36. Universal Analytics, Self-Visit Exclusion & Search Engine Bot Standards (`va.js`)

- **Universal Script Architecture (`/va.js`)**:
  - Deployed across all 62 website HTML documents via `<script defer src="/va.js"></script>`.
  - Delegates to Vercel Web Analytics (`/_vercel/insights/script.js`) without external third-party tracking scripts.
- **Owner Self-Visit Exclusion (Zero Data Pollution)**:
  - Developer/owner visits during testing and updates are automatically filtered out.
  - Multi-tier persistent opt-out:
    1. Cookie: `pcdeck_analytics_optout=1` (10-year lifespan).
    2. LocalStorage: `pcdeck_analytics_optout = '1'`.
    3. URL Param: `?admin=1` triggers automatic cookie/localStorage registration.
    4. Dedicated Console: `/analytics-console/` provides real-time toggle status and reset controls.
    5. Footer Status Button: Real-time dynamic button `#btn-analytics-toggle` displaying `🛡️ Analytics: Excluded` or `Active`.
- **Search Engine Crawler Preservation**:
  - Standard HTTP requests and verified search engine crawlers (Googlebot, Bingbot, IndexNow bots, Seobility auditors) are processed with standard headers.
  - Preserves site health monitoring, SERP crawlability, and indexing signals.

---

## 37. Microsoft Store Certification Compliance & Security Invariants (v2.7.2)

- **Strict Enforcement of Policy 10.2.10.1 (Zero Executable Downloads from App)**:
  - **Rejection Root Cause**: Store testers previously flagged `"Download Mobile App"` in `server/gui.py` which invoked `webbrowser.open(".../PCDeck.apk")`. Store policy strictly forbids applications or metadata from initiating downloads of executables (`.apk`, `.exe`, `.msi`, `.bat`).
  - **Resolution**: Permanently replaced with in-app "How to Connect" guidance modal (`open_how_to_connect_dialog`). Displays 4 simple zero-install steps on-screen (phone camera QR scan) with a single outbound hyperlink to the website root (`https://pcdeck.vercel.app/`). Initiates zero file downloads.
- **Native Package Identity Detection (`is_msix_packaged()`)**:
  - In Store installations, `server/gui.py` calls `kernel32.GetCurrentPackageFullName`.
  - When packaged inside an MSIX container, the function returns `ERROR_SUCCESS (0)` rather than `APPMODEL_ERROR_NO_PACKAGE (15700)`.
  - Suppresses background auto-update polling threads (`_silent_update_ping`) because updates for Store packages are managed natively by the Microsoft Store client.
- **Partner Center `runFullTrust` Justification Standard**:
  - MSIX packaged desktop utilities require explicit justification for the `runFullTrust` restricted capability in Partner Center Submission Options:
    1. Desktop screen capture via Windows Desktop Duplication API for low-latency display streaming.
    2. Cursor, scroll, and keyboard simulation via Win32 `SendInput` API.
    3. Virtual Xbox 360 controller emulation via ViGEmBus driver.
    4. Desktop audio stream capture via Windows Core Audio / WASAPI loopback capture.
- **Partner Center Active Lifecycle**:
  - Product ID: `9P4BK16LBGLS`
  - Version: `2.7.2.0` (Code `272`, x64)
  - Submission State: Passed pre-processing, active in certification.






