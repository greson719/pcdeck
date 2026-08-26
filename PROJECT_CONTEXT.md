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
The website (`website/`) is deployed on Vercel at `https://pcdeck.vercel.app/` with 5 pillar problem-solving guides:
- `/use-pc-without-mouse/` — Mouse failure, focus navigation, Mouse Keys numpad.
- `/use-pc-without-keyboard/` — Keyboard failure, sign-in screen on-screen keyboard, voice typing.
- `/use-pc-without-monitor/` — Broken laptop screen, blind shortcuts, emergency phone screen streaming.
- `/stream-pc-audio-to-phone/` — Broken 3.5mm jack, wireless 48 kHz stereo PC audio to phone.
- `/transfer-files-pc-to-android/` — Cable-free local Wi-Fi file transfers with auto-resume.

**Files to maintain on updates:**
- `sitemap.xml`: Canonical URLs only (no `#` hash fragments).
- `llms.txt`: Structured query reference for AI search engines (Perplexity, ChatGPT Search, Claude, Gemini).
- `robots.txt`: Explicitly allow major AI and search crawlers while disallowing `.exe`, `.apk`, and `.zip` binaries.

---

## 4. Upcoming Roadmap & Planned Features

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

## 5. Continuous Context Synchronization Rule (Living Document)
- **Mandatory Agent Directive**: This file is a living document. Whenever any change, feature addition, bug fix, UI enhancement, pricing update, or new guide is created:
  1. The developer or AI agent **MUST update this `PROJECT_CONTEXT.md` file immediately** in the same commit.
  2. If new public URLs or guides are added, also update `sitemap.xml` and `llms.txt`.
  3. Never leave context, architecture, or roadmap documentation stale or outdated.
