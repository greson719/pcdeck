# AGENTS.md — PCDeck Agent Directives

## 1. Mandatory Caveman Mode (Token Efficiency & Max Speed)
- Zero pleasantries, zero filler ("Sure!", "I'd be happy to", "As requested").
- Minimum words, maximum density. State exact actions, diffs, results, exit codes.
- Auto-run safe reads, edits, builds, tests without asking.

## 2. Ponytail Code Ladder (MANDATORY — run before writing ANY code)

Before writing code, stop at the **first rung that holds**:

```
1. Does this need to exist?         → no: skip it (YAGNI)
2. Already in this codebase?        → reuse it, don't rewrite
3. Stdlib / built-in does it?       → use it
4. Native platform feature?         → use it (e.g. <input type="date"> not flatpickr)
5. Already-installed dependency?    → use it
6. One line?                        → one line
7. Only then: write the minimum that works
```

**Never skip**: trust-boundary validation, error handling, security, accessibility.
Lazy about the solution — never lazy about reading the existing code first.

## 3. Project Invariants
- Follow all architectural rules defined in `PROJECT_CONTEXT.md` and `WEBSITE_CONTEXT.md`.
- **PCDeck_Package.zip Deprecation**: NEVER build, package, or re-add `PCDeck_Package.zip` to releases, download cards, or websites. `PCDeck.exe` already embeds `PCDeck.apk` and serves it locally over Wi-Fi at `GET /PCDeck.apk`. Keep download cards strictly to 3: Windows (`.exe`), Android (`.apk`), Linux (`.sh`).
- **PCDeck-Setup.exe Discontinuation (Strict 2-Option Windows Model)**: NEVER build, package, or re-add `PCDeck-Setup.exe` (Inno Setup installer). Windows distribution is strictly a 2-option model:
  1. **Microsoft Store (`.msix` / Store Web Installer)**: For regular users desiring an installed, auto-updating app with verified publisher trust and zero SmartScreen friction.
  2. **Standalone Portable (`PCDeck.exe`)**: For users wanting a portable, zero-install binary that runs immediately from anywhere.
  The Inno Setup (`ISCC.exe` / `PCDeck_Setup.iss`) pipeline is permanently retired.
- Never use `cd` in PowerShell; use absolute paths or `Cwd`.
- Sync assets (`static/` <-> `android_app/assets/`) and rebuild binaries when UI/core code changes.
- Run `python build_apk.py` after any HTML/JS/CSS/Java changes.
- Run `python build_exe.py` after any Python server changes.

## 4. Hardware & Streaming Mechanics Non-Regression Invariant (CRITICAL)
- **Zero Breakage Policy**: Never break, disable, delete, or regress any active streaming or hardware mechanics during refactors, cleanups, or optimizations:
  1. **Webcam**: Maintain `/ws/cam` streaming, phone camera grabber, preview video, aspect ratio scaling, and format conversion.
  2. **Microphone**: Maintain phone mic capture, audio worklets, and server receiver sink (port 8002).
  3. **Speaker / PC Audio**: Maintain WASAPI loopback capture, TCP audio streaming (port 8003), and client player worklet.
  4. **Screen Streaming & Touch**: Maintain low-latency screen capture/render, touch click, pan/zoom, kinetic momentum, and high-speed natural scrolling.
  5. **Gamepad & Controls**: Maintain virtual controller emulation (vgamepad/ViGEmBus), key injection, and file transfer pipelines.
- **Verification Requirement**: Before completing any task touching server, client, or audio/video code, verify that all underlying protocols, sockets, and mechanics remain intact.

## 5. Anti-AI-Slop & Premium UI Invariant (STRICT MANDATE)
- **Zero AI Slop / Zero Generic Emojis**: NEVER inject generic AI slop, tacky cartoon emojis (e.g. 🚀, 💻, 🤖, ✨, 🔥, ⚡, 🎧, 🎮, 📱, 🎉, 🫧, 💿, 📟, 🌌, 👑, etc.), or gimmicky AI copy into the application UI, buttons, tabs, headers, modal dialogues, or cards.
- **Eliminate Cheap Amateur Look**: Emojis make professional desktop and mobile software look cheap, low-effort, and AI-generated.
- **Strict Visual Authority**: Use clean, bespoke SVG vector icons (`<svg class="deck-icon">`), crisp typography (Inter/Outfit), authentic design system micro-interactions, and genuine glassmorphic/cyber aesthetics only. Real software is built with high-fidelity vector icons and typography, never emoji spam.

## 6. Customer Email & Support Communication Directives (STRICT)
- **First-Person Voice Only**: Always write from Greson personally (**"I" / "my" / "me"**). NEVER use corporate "we", "our team", or "us".
- **Zero AI Clichés & Zero Exaggeration**: NEVER use bot clichés like "Great catch!", "Thanks for reaching out!", or overly dramatic praise. Be grounded, direct, and human.
- **Do Not State the Obvious**: Never announce "as an independent developer" or "solo creator" unless explicitly asked; customers already know.
- **Plain, Non-Jargon Explanations**: Explain technical fixes simply in plain English without dropping internal code jargon, polling loops, or low-level APIs.
- **Never Pressure for Reviews**: When a customer volunteers a review, acknowledge it with a humble thank you ("thank you for offering to leave a review on the Store as well"). Never say "if you get time this weekend" or pressure paying customers.
- **Proactive UX Guidance**: Explicitly mention any initial-state UI conditions (e.g., "this list only appears once 2+ PCs are connected to keep the screen clean") to prevent first-time confusion.
- **Short, Compact & Punchy**: Keep emails brief, bulleted, and immediately scannable on mobile screens.

