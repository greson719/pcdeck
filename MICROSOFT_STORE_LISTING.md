# 🪟 PCDeck — Microsoft Partner Center Copy-Paste Listing Kit

Use the exact text below when filling out the Microsoft Store submission form in Microsoft Partner Center.

---

### 1. PRODUCT TITLE (Name)
PCDeck: Wireless Trackpad, Screen Mirror & Remote

---

### 2. SHORT DESCRIPTION (Under 100 characters)
Turn your phone into a multi-touch trackpad, screen mirror & PC remote over local Wi-Fi.

---

### 3. FULL DESCRIPTION
Transform your smartphone into a wireless multi-touch trackpad, desktop screen mirror, mechanical keyboard, stereo audio streamer, and cable-free file manager for Windows 10 and Windows 11.

PCDeck runs 100% offline over your local Wi-Fi network or mobile hotspot. It requires zero cloud accounts, zero sign-ups, zero internet connectivity, and contains zero telemetry.

Connect in 3 seconds by scanning the pairing QR code displayed on your PC screen, and take complete control of your computer from across the room.

========================================
HIGHLIGHT FEATURES
========================================

🖱️ MULTI-TOUCH PRECISION TRACKPAD
• Ultra-responsive mouse cursor movement with ballistic acceleration.
• Physical tap gestures: 1-finger tap for Left Click, 2-finger tap for Right Click.
• 350ms long-press for drag-and-drop file and window locking.
• Dedicated edge scroll strip for vertical scrolling through documents and web pages.

🖥️ LOW-LATENCY DESKTOP SCREEN MIRRORING
• Stream your Windows desktop directly to your mobile display in real time.
• Fluid 30 FPS and 60 FPS streaming modes with adaptive JPEG compression.
• 1:1 direct physical touch interaction: tap, double-click, drag, and pinch-to-zoom.
• Mobile kinetic inertia fling physics for natural document scrolling.

⌨️ LIVE VIRTUAL KEYBOARD & NUMPAD
• Full virtual mechanical keyboard layout with dedicated Function keys (F1-F12) and Numpad cluster.
• Slide-up mobile typing bar for instant Unicode text entry into active Windows apps.
• Instant Windows shortcut hotkeys: Win+D, Alt+Tab, Task View, and Snipping Tool.

📁 CABLE-FREE LOCAL FILE MANAGER
• Transfer multi-gigabyte files, photos, videos, and documents between PC and phone over high-speed local Wi-Fi.
• Unbuffered chunked streaming architecture with strict 1-by-1 FIFO batch queuing.
• Direct access to PC Desktop and Downloads folders.

🎵 STEREO AUDIO STREAMING & MEDIA DECK
• Stream PC audio directly to your phone earphones over local Wi-Fi with low latency.
• Complete media playback deck: Play/Pause, Next/Previous Track, and Windows Volume controls.
• Real-time audio visualizer wave display.

⚡ 3-SECOND INSTANT QR CODE PAIRING
• Launch PCDeck and point your phone camera at the QR code to pair immediately.
• Zero manual IP typing or port configuration required.
• Operates seamlessly across local home Wi-Fi and direct Mobile Hotspots.

🔒 100% PRIVATE & OFFLINE
PCDeck communicates strictly peer-to-peer over your local network. Your keystrokes, screen data, and files never leave your local devices.

---

### 4. KEY FEATURES (Bullet Points)
• Wireless multi-touch trackpad with ballistic cursor acceleration and gesture clicks
• Low-latency desktop screen mirroring with 30 FPS and 60 FPS streaming modes
• 1:1 direct physical touch tracking and kinetic momentum scrolling
• Full virtual mechanical keyboard layout, Numpad cluster, and Windows hotkeys
• Cable-free high-speed local Wi-Fi file sharing and batch transfer queues
• Real-time WASAPI stereo PC audio loopback streaming to phone earphones
• Media control deck with volume slider and live audio visualizer
• Instant 3-second QR code network pairing with zero configuration
• 100% offline local network communication with zero cloud accounts or telemetry

---

### 5. SEARCH TERMS / KEYWORDS
1. remote mouse
2. wireless trackpad
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
- Privacy Policy: https://pcdeck.vercel.app/privacy
- Website: https://pcdeck.vercel.app
