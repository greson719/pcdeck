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

## 4. Upcoming Roadmap: Gaming Controller & Pro Custom Keymapper
- **Feature Overview**: Turn Android phone into a low-latency virtual gamepad for PC gaming and retro emulators.
- **Latency Design**:
  - Direct local UDP transmission (<5ms latency) for gamepad input when user looks at their PC monitor.
- **Free Tier**:
  - Pre-built Standard Gamepad (D-Pad, Left Stick, A/B/X/Y, Triggers, Bumpers).
  - Pre-built Mobile Shooter HUD (Thumbstick + Aim area + Action buttons).
- **Pro Plan Exclusive**:
  - **Drag-and-Drop HUD Editor**: Allows users to freely add, resize, and reposition buttons/sticks anywhere on the screen and bind them to any PC keyboard key or mouse click (similar to mobile FPS layout editors in Free Fire / PUBG).
