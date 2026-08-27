# PCDeck — Project Context & Engineering Standards

## 1. Core Identity & Architecture
- **Product Name**: **PCDeck** (written as **PCDeck** or **PC Deck** in SEO contexts).
- **Core Value Proposition**: 100% Offline, local Wi-Fi utility suite for Windows 10/11 & Android (Trackpad, Keyboard, Emergency Screen Streaming, Live PC Audio, and Cable-free File Transfer).
- **Privacy Standard**: Zero cloud accounts, zero telemetry, zero analytics. All communication is strictly local network (LAN / Hotspot).
- **Monetization & Pro Plan Model**:
  - The core application is completely free.
  - **Pro** is an optional **one-time $3.99 in-app lifetime unlock** inside the main PCDeck app (enables 60/120 FPS streaming and faster transfers).
  - **Rule**: Never create or distribute a separate "PCDeck Pro" binary. PCDeck is a single unified app.

---

## 2. Design & Content Standards (Strict Anti-AI Slop Rules)
Any future agent or developer working on this repository must adhere to the following rules:

1. **No AI Cliché Emojis or Slop**:
   - Strictly forbidden: `⚡`, `🚀`, `🔥`, `↓`, `🤖`, `✨`, or generic marketing emojis.
   - Strictly forbidden: Fluffy marketing hype ("revolutionary", "cutting-edge", "game-changing").
   - Use clean, honest, technical, and human-friendly editorial prose.

2. **No Cheap or Generic UI**:
   - Maintain the bespoke design aesthetic: typography (`Archivo`, `Instrument Sans`, `IBM Plex Mono`), clean borders (`var(--grid)`), subtle tint washes (`var(--signal-wash)`), and responsive step lists.
   - Every guide must be genuinely useful first (documenting built-in Windows tools and shortcuts accurately) with natural `.quick-card` and in-line PCDeck product placement.

---

## 3. Active SEO & AEO (AI Engine) Infrastructure
The website (`website/`) is deployed on Vercel at `https://pcdeck.vercel.app/` with 7 canonical routes:
- `/` — Homepage (Turn phone into mouse, keyboard, and emergency display for Windows).
- `/security/` — Security & Privacy Architecture (LAN isolation, zero telemetry, SHA-256 verification, SmartScreen reputation context).
- `/use-pc-without-mouse/` — Mouse failure, focus navigation, Mouse Keys numpad.
- `/use-pc-without-keyboard/` — Keyboard failure, sign-in screen on-screen keyboard, voice typing.
- `/use-pc-without-monitor/` — Broken laptop screen, blind shortcuts, emergency phone screen streaming.
- `/use-pc-without-internet/` — Controlling Windows offline over local Wi-Fi or phone hotspot.
- `/stream-pc-audio-to-phone/` — Broken 3.5mm jack, wireless 48 kHz stereo PC audio to phone.
- `/transfer-files-pc-to-android/` — Cable-free local Wi-Fi file transfers with auto-resume.

**Files to maintain on updates:**
- `sitemap.xml`: Canonical URLs only (no `#` hash fragments).
- `llms.txt`: Structured query reference for AI search engines (Perplexity, ChatGPT Search, Claude, Gemini).
- `robots.txt`: Explicitly allow major AI and search crawlers while disallowing `.exe`, `.apk`, and `.zip` binaries.

---

---

## 4. File Transfer Architecture (High-Speed Streaming Engine)
The local file transfer system is designed for high reliability across small batches (KBs) up to massive archives (5GB - TB+):

### 4. File Transfer & MediaStore Storage Architecture
- **Bidirectional Streaming**:
  - `POST /api/fs/upload-stream`: Unbuffered chunk streaming with 2MB disk buffer.
  - `GET /api/fs/download`: Chunked HTTP streaming with `Accept-Ranges: bytes` support for resume and multi-gigabyte files.
- **Android Scoped Storage & MediaStore (API 29+)**:
  - Downloads are saved to `Downloads/PCDeck/`.
  - Android Q+ `MediaStore.Downloads.EXTERNAL_CONTENT_URI` handles scoped storage with `IS_PENDING = 1` during active streaming and `IS_PENDING = 0` upon full completion.
  - Automatic `MediaScannerConnection.scanFile()` indexes direct file writes immediately so downloaded files appear in the phone's gallery and file managers.
  - Phone File Browser queries `MediaStore.Downloads.EXTERNAL_CONTENT_URI` to list all downloaded files seamlessly without permission lockouts.

2. **Network Resilience & Android Power Management**:
   - **Infinite Socket Timeout**: `conn.setReadTimeout(0)` during active data streams, preventing socket dropouts on long-running multi-gigabyte transfers.
   - **WakeLock & WifiLock**: Automatically acquires Android `PowerManager.PARTIAL_WAKE_LOCK` and `WifiManager.WIFI_MODE_FULL_HIGH_PERF` during transfers to prevent OS Doze throttling and Wi-Fi radio sleep.
   - **Ongoing Status Bar Notifications**: Dispatches sticky Android notifications on channel `pcdeck_transfers_channel` with live percentage, throughput speed (MB/s), and real-time ETA countdown. Transfers proceed uninterrupted even if the app is minimized.

3. **Integrity Verification & Auto-Resume**:
   - **Verification Endpoint (`/api/fs/verify` & `/api/fs/stat`)**: Queries exact byte size on receiver disk immediately upon stream close. Only flags `Verified` when written bytes match source file length.
   - **Auto-Resume on Interruption**: Queries remote partial byte size before starting large transfers (>10 MB). Automatically seeks and streams only remaining bytes if a prior transfer was interrupted.
   - **Inactivity Watchdog**: Replaced fixed static timers with an activity monitor that only triggers if zero bytes or progress events are received for 60 consecutive seconds.

---

## 5. Upcoming Roadmap & Planned Features

### A. Gaming Controller & Pro Custom Keymapper
- **Feature Overview**: Turn Android phone into a low-latency virtual gamepad for PC gaming and retro emulators.
- **Latency Design**: Direct local UDP transmission (<5ms latency) for gamepad input when user looks at their PC monitor.
- **Free Tier**: Pre-built Standard Gamepad (D-Pad, Left Stick, A/B/X/Y, Triggers, Bumpers) & Mobile Shooter HUD (Thumbstick + Aim area + Action buttons).
- **Pro Plan Exclusive**: **Drag-and-Drop HUD Editor** allowing users to freely place, resize, and bind buttons/sticks anywhere on screen (similar to mobile FPS layout editors in Free Fire / PUBG).

### B. Auto-Start with Windows (Headless & Emergency Mode)
- **Feature**: Add an in-app toggle / setup prompt in `PCDeck.exe` for **"Start with Windows"** (registered via `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- **Purpose**: Ensures the server launches on system boot/wakeup so users with a broken monitor or headless PC can connect immediately without needing a working display to click anything.

### C. Store Publishing & Warning Elimination
- **Android**: Publish to **Google Play Store** to eliminate "Install unknown apps" / Play Protect prompts.
- **Windows**: Package as **MSIX for Microsoft Store** / apply Code Signing to eliminate SmartScreen ("Windows protected your PC") and antivirus false positives.
- **Website Sync**: Update download buttons with official store badges once published.

### D. Mobile Onboarding & PC Server Sideloading (Offline PC Rescue)
- **Problem Solved**: When a PC has a broken mouse, dead monitor, or no internet, the user cannot easily download `PCDeck.exe` on the PC itself.
- **Feature**:
  1. **In-App Download**: Android onboarding screen includes a *"Download PC Server to Phone"* button that downloads `PCDeck.exe` directly into the phone's `/Downloads` folder.
  2. **Transfer Instructions**: Provides visual steps to transfer the `.exe` to the PC via USB cable, OTG pendrive, or local hotspot.
  3. **Local Wi-Fi Host**: (Optional) Phone hosts a tiny local HTTP server so any PC connected to the phone's hotspot can download `PCDeck.exe` without internet.

### E. Lemon Squeezy Pro Licensing & In-App Upgrade Logic
- **Architecture (Official Lemon Squeezy License API)**:
  - **No Custom Backend Required**: Lemon Squeezy provides public client-safe license endpoints that do not expose private store API keys:
    1. **Activation**: `POST https://api.lemonsqueezy.com/v1/licenses/activate` with `license_key` and `instance_name` (e.g., Device ID/Name).
    2. **Validation**: `POST https://api.lemonsqueezy.com/v1/licenses/validate` with `license_key` and `instance_id`.
    3. **Deactivation**: `POST https://api.lemonsqueezy.com/v1/licenses/deactivate` to unbind a device.
  - **Offline-First Storage**:
    - Upon successful activation (`"activated": true`), save `is_pro = true`, `license_key`, and `instance_id` securely in local storage (Android `SharedPreferences` / Windows config).
    - Pro features remain permanently unlocked offline without blocking users when Wi-Fi has no internet access.
- **Real Pro Functionality**:
  - Unlocks 60/120 FPS streaming pipeline in client/server.
  - Unthrottles Wi-Fi file transfer chunking and queue limits.
  - Enables the Pro Drag-and-Drop HUD Keymapper.
- **Smart Upgrade Prompt (Retention Trigger)**:
  - Track app usage days locally (`first_launch_date` / active usage count).
  - If a user is on the Free tier and has actively used the app for **2 to 3 days**, display a polite, non-intrusive modal highlighting Pro benefits ($3.99 lifetime unlock) with direct Lemon Squeezy checkout link and license entry field.

---

## 6. Verification & Release Protocol
Before committing and pushing any changes to GitHub or production:
1. **Compile & Sign Android APK**: Run `python build_apk.py` (verifies Java compilation, resources, DEX conversion, alignment, and apksigner signature).
2. **Update Distribution Packages**: Update `PCDeck_Package.zip` with fresh binaries and documentation.
3. **Regenerate Checksums**: Run `python tools/update_checksums.py` to calculate exact SHA-256 digests and update the download table in `website/index.html`.
4. **Synchronize Context**: Review and update `PROJECT_CONTEXT.md` in root and `website/` to match all implemented features and technical specs.
5. **Verify Git Tree & Push**: Stage verified files (`git add PCDeck.apk index.html PROJECT_CONTEXT.md`), commit with clear descriptive messages, and push to `origin main`.

---

## 7. Continuous Context Synchronization Rule (Living Document)
- **Mandatory Agent Directive**: This file is a living document. Whenever any change, feature addition, bug fix, UI enhancement, pricing update, or new guide is created:
  1. The developer or AI agent **MUST update this `PROJECT_CONTEXT.md` file immediately** in the same commit.
  2. If new public URLs or guides are added, also update `sitemap.xml` and `llms.txt`.
  3. Never leave context, architecture, or roadmap documentation stale or outdated.
