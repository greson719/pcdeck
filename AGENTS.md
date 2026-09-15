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
- Follow all architectural rules defined in `PROJECT_CONTEXT.md`.
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
