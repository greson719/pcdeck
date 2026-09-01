# PCDeck — Microsoft Partner Center Copy-Paste Listing Kit

Use the exact text below when filling out the Microsoft Store submission form in Microsoft Partner Center.

---

### 1. PRODUCT TITLE (Name)
PCDeck: Wireless Trackpad, Screen Mirror & Remote Mouse

---

### 2. SHORT DESCRIPTION (Under 100 characters)
Turn your phone into a precision trackpad, 60 FPS screen mirror & PC remote over local Wi-Fi.

---

### 3. FULL DESCRIPTION
PCDeck transforms your smartphone into a high-precision multi-touch trackpad, low-latency desktop screen mirror, full mechanical keyboard, virtual gaming controller, stereo audio streamer, and high-speed local file manager for Windows 10 and Windows 11.

Engineered with a 100% offline, peer-to-peer architecture, PCDeck connects directly over your local Wi-Fi network or mobile hotspot. It requires zero cloud accounts, zero sign-ups, zero internet access, and collects zero telemetry.

Pair your devices in three seconds by scanning the desktop QR code, and take instant control of your PC from across the room.

============================================================
CORE MODULES & CAPABILITIES
============================================================

PRECISION MULTI-TOUCH TRACKPAD
• Ballistic cursor acceleration with tremor dampening and sub-pixel Win32 accumulation.
• Hardware gesture support: 1-finger tap for Left Click, 2-finger tap for Right Click.
• 350ms long-press for drag-and-drop file and window movement.
• Dedicated edge scrolling strip for fluid navigation through long documents and code.

LOW-LATENCY DESKTOP SCREEN MIRRORING & IN-DISPLAY HUD
• Real-time desktop streaming directly to your phone screen in 30 FPS and 60 FPS modes.
• Lossless 4:4:4 chroma preservation for sharp, readable font outlines and editor text.
• 1:1 direct physical touch mapping: tap, double-click, drag, and pinch-to-zoom.
• Mobile kinetic inertia fling physics for natural document and browser scrolling.
• In-Display Touch HUD: Position custom touch controls directly over your live desktop screen.

VIRTUAL GAMEPAD & KEYMAPPER
• Console-style virtual gamepad with dual analog sticks, directional pad, and shoulder triggers.
• Low-latency input transmission mapped directly to Windows input drivers.
• Customizable on-screen button layouts and hotkey assignments for PC games and emulators.

VIRTUAL MECHANICAL KEYBOARD & NUMPAD
• Full mechanical keyboard layout including dedicated Function keys (F1–F12), Esc, and Numpad cluster.
• Slide-up mobile typing bar for rapid Unicode text synchronization into active Windows applications.
• One-tap Windows system shortcuts: Win+D, Alt+Tab, Task View, and Snipping Tool.

LOCAL WI-FI FILE MANAGER
• Transfer large files, photos, videos, and archives between PC and phone at maximum local network speeds.
• Unbuffered chunked streaming architecture with a 2MB disk buffer for high throughput.
• Direct folder quick-access to PC Desktop and Downloads folders.

WASAPI STEREO PC AUDIO STREAMING
• Stream real-time PC audio directly to your phone earphones over local Wi-Fi with low latency.
• Complete media playback controller: Play/Pause, Next/Previous Track, and master volume slider.
• Live real-time audio visualizer waveform display.

============================================================
COMMON USE CASES
============================================================
• Emergency Backup: Control your PC when your physical mouse or keyboard runs out of battery or malfunctions.
• Living Room & Media Control: Manage movie playback, volume, and browsing from your couch or bed.
• Presentations & Meetings: Advance slides, navigate windows, and mirror presentations wirelessly.
• Quiet Nighttime Listening: Stream game or movie audio directly to your phone earphones without long headphone cables.
• Quick Cable-Free Sharing: Send screenshots, documents, and videos between devices without USB cables or cloud storage.

============================================================
PRIVACY & SECURITY SPECIFICATION
============================================================
• 100% Offline: All communication is restricted to your local area network (LAN).
• Zero External Servers: Keystrokes, screen frames, and files never leave your local devices.
• Zero Telemetry: No analytics, tracking SDKs, or background profiling.

---

### 4. KEY FEATURES (Bullet Points)
• Ultra-responsive wireless trackpad with ballistic acceleration and multi-touch gestures
• Low-latency desktop screen mirroring with 30/60 FPS modes and 4:4:4 lossless chroma
• 1:1 physical touch tracking with kinetic momentum scrolling
• Full virtual mechanical keyboard layout, Numpad cluster, and Windows hotkey shortcuts
• Cable-free local Wi-Fi file sharing with unbuffered chunked streaming
• Real-time WASAPI stereo PC audio loopback streaming to phone earphones
• Media deck with Windows master volume slider and real-time audio visualizer
• 3-second instant QR code network pairing with zero manual IP setup
• 100% offline local network communication with zero cloud accounts or telemetry

---

### 5. SEARCH TERMS / KEYWORDS (7 Exact Partner Center Tags)
1. wireless trackpad
2. remote mouse
3. screen mirroring
4. pc remote control
5. wifi file transfer
6. wireless keyboard
7. audio streamer

---

### 6. NOTES FOR CERTIFICATION (For Microsoft Reviewers)
PCDeck is a 100% offline local Wi-Fi utility that enables users to control their Windows PC from their smartphone (acting as a wireless multi-touch trackpad, virtual keyboard, low-latency screen mirror, audio loopback streamer, and local file manager).

Why runFullTrust is required:
1. Win32 Input Injection: Uses user32.dll (mouse_event / SendInput) to simulate mouse cursor moves, left/right clicks, wheel scrolls, and keyboard hotkeys sent from the user's paired mobile device over local WebSocket.
2. WASAPI Loopback Audio: Uses Windows Core Audio APIs (WASAPI loopback capture) to stream desktop audio to the user's phone earphones.
3. Local HTTP / WebSocket Server: Hosts a lightweight local server on 127.0.0.1 / local LAN IP (port 8000) strictly for peer-to-peer communication between the user's PC and phone.

All communication occurs 100% locally over LAN. Zero external cloud servers, zero internet requirements, and zero user data collection.

---

### 7. CONTACT & SUPPORT
- Support Email: gresonparichha719@gmail.com
- Privacy Policy: https://pcdeck.vercel.app/privacy_policy.html
- Website: https://pcdeck.vercel.app
