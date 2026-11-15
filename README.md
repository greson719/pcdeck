# PCDeck - Mobile Touch Display, Trackpad & Remote Control for PC

Turn any smartphone (Android or iOS) into an ultra-low latency **Wireless Touchscreen Monitor**, **Multi-Touch Trackpad**, **Virtual Webcam/Microphone**, and **Gamepad/Keyboard Controller** for your Windows PC over local Wi-Fi.

[![Website](https://img.shields.io/badge/Official_Website-getpcdeck.com-00f0ff?style=flat&logo=vercel)](https://getpcdeck.com/)
[![Download](https://img.shields.io/badge/Download_Center-PCDeck-1b44d8?style=flat)](https://getpcdeck.com/download/)
[![Pricing](https://img.shields.io/badge/Pricing-%243.99_Lifetime_Pro-7c3aed?style=flat)](https://getpcdeck.com/pricing/)
[![iPhone Webcam](https://img.shields.io/badge/Guide-iPhone_as_PC_Webcam-0ea5e9?style=flat)](https://getpcdeck.com/use-iphone-as-webcam-windows/)
[![Linux & Steam Deck](https://img.shields.io/badge/Guide-Linux_%26_Steam_Deck-f97316?style=flat)](https://getpcdeck.com/control-linux-pc-from-phone/)
[![Microsoft Store](https://img.shields.io/badge/Microsoft_Store-PCDeck-0078D4?style=flat&logo=windows)](https://apps.microsoft.com/detail/9P4BK16LBGLS?cid=github_readme)

---

## Quick Start in 3 Easy Steps

### 1. Run the PC Server (Windows or Linux)
Choose either:
- **Option 1 (Recommended — Microsoft Store)**:
  
  <a href="https://apps.microsoft.com/detail/9P4BK16LBGLS?cid=github_readme" target="_blank">
    <img src="https://get.microsoft.com/images/en-us%20dark.svg" alt="Get PCDeck from Microsoft Store" width="160"/>
  </a>
  
  *Official verified 1-click install, zero SmartScreen prompt, automatic background updates.*

  > **Find PCDeck useful?** A quick rating on the [Microsoft Store](https://apps.microsoft.com/detail/9P4BK16LBGLS?cid=github_readme) helps an indie developer like me a lot.
- **Option 2 (Standalone Portable)**: Double-click [`PCDeck.exe`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/PCDeck.exe) (or run [`run.bat`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/run.bat)) in this folder.
- **Option 3 (Linux & Steam Deck 1-Line)**: Run `curl -sSL https://getpcdeck.com/install.sh | bash` (see [Linux Guide](https://getpcdeck.com/control-linux-pc-from-phone/)).
- A dashboard will open showing your PC's Wi-Fi IP and an optical **QR Code**. Keep this running in the background.

### 2. Connect Your Phone (.apk or Web Browser)
You have two easy ways to connect:

- **Option A (Instant Browser - Zero Phone Install)**:
  - Scan the QR code with your phone camera, or open your PC's IP address (e.g. `http://[YOUR-PC-IP]:8000`) in Safari or Chrome.
  - Works on iPhone, iPad, Android, Mac, and Chromebook with zero app store downloads.
- **Option B (Android APK)**:
  - Copy [`PCDeck.apk`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/PCDeck.apk) to your Android phone and install it for a permanent home screen icon.

---

## Core Capabilities & Guides

- **iPhone as PC Webcam & Microphone**: Use your iPhone as a 1080p 60 FPS wireless camera for Discord, Zoom, Teams, and OBS ([Read Guide](https://getpcdeck.com/use-iphone-as-webcam-windows/)).
- **Use PC Without a Mouse or Monitor**: Emergency keyboard shortcuts and display streaming to your phone screen ([Without Mouse Guide](https://getpcdeck.com/use-pc-without-mouse/) | [Without Monitor Guide](https://getpcdeck.com/use-pc-without-monitor/)).
- **Linux & Steam Deck Remote**: Full Wayland and X11 terminal input and screen control ([Read Guide](https://getpcdeck.com/control-linux-pc-from-phone/)).
- **Stream PC Audio to Phone**: Lossless 48 kHz stereo audio receiver for private listening ([Read Guide](https://getpcdeck.com/stream-pc-audio-to-phone/)).
- **Compare Alternatives**: [Monect Alternative](https://getpcdeck.com/monect-alternative/) | [Unified Remote Alternative](https://getpcdeck.com/unified-remote-alternative/) | [Remote Mouse Alternative](https://getpcdeck.com/remote-mouse-alternative/).
- **Pricing & Pro**: 100% Free Core, optional $3.99 Lifetime Pro unlock for 120 FPS streaming and custom HUD ([View Pricing](https://getpcdeck.com/pricing/)).

---

## Touch Screen Display Mode (Virtual Touchscreen)

Switch to the **Screen** tab to see your live Windows desktop right on your phone:

| Action | Touch Gesture |
| :--- | :--- |
| **Direct Click** | Tap anywhere on the live PC screen -> clicks that exact button/window on PC |
| **Right Click** | Hold finger down on screen for >350ms (or tap Right Click on toolbar) |
| **Drag & Select** | Switch to Drag Mode on the toolbar -> touch & drag windows or text |
| **Pinch to Zoom** | Pinch with 2 fingers to zoom in up to 4x for clicking small desktop icons |
| **2-Finger Pan** | Drag with 2 fingers while zoomed in to pan across your desktop |
| **On-Screen Keyboard** | Tap Keyboard on the top toolbar to open quick text & shortcuts drawer |
| **Stream Quality** | Choose Balanced (30 FPS), High Res, or Pro Max FPS (60/120 FPS) |

---

## Trackpad Mode Gestures

| Action | Touch Gesture |
| :--- | :--- |
| **Move Cursor** | Glide 1 finger across the trackpad area |
| **Left Click** | Tap once with 1 finger (or use bottom LEFT CLICK button) |
| **Right Click** | Tap with 2 fingers (or use bottom RIGHT CLICK button) |
| **Middle Click** | Tap bottom MIDDLE button (opens links in new tab / closes browser tabs) |
| **Smooth Scroll** | Swipe up / down with 2 fingers, or drag the dedicated side scroll strip |
| **Air Mouse** | Switch to Air Mouse tab, hold button, and wave your phone in the air |

---

## Generated Files & Architecture

- [`PCDeck.exe`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/PCDeck.exe) - Standalone Windows executable server (SHA-256 verified).
- [`PCDeck.apk`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/PCDeck.apk) - Standalone Android application package.
- [`run.bat`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/run.bat) / [`start.ps1`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/start.ps1) - 1-click startup scripts.
- [`server/`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/server) - Python FastAPI, screen streaming & native Win32/Linux input simulator.
- [`static/`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/static) - Web client with live canvas stream and responsive touch surface.
- [`website/`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/website) - Official documentation, guides, and download center.
