# ⚡ NeonTrack - Mobile Touch Display, Trackpad & Remote Control for PC

Turn any smartphone (Android or iOS) into an ultra-low latency **Wireless Touchscreen Monitor**, **Multi-Touch Trackpad**, and **Keyboard Controller** for your Windows PC over local Wi-Fi.

---

## 🚀 Quick Start in 3 Easy Steps

### 1. Run the PC Server (`.exe`)
Double-click [`NeonTrack.exe`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/NeonTrack.exe) (or run [`run.bat`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/run.bat)) in this folder.
- A terminal window will open showing your PC's Wi-Fi IP and a **QR Code**.
- Keep this window running in the background.

### 2. Connect Your Phone (`.apk` or Web Browser)
You have two easy ways to connect:

- **Option A (Android APK)**:
  - Copy [`NeonTrack.apk`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/NeonTrack.apk) to your Android phone and install it.
  - Open the app, type your PC's IP (e.g. `192.168.1.100:8000`), and tap **Connect**.
- **Option B (Instant Browser - No Install Needed)**:
  - Scan the QR code with your phone camera, or open `http://<your-pc-ip>:8000` in Safari/Chrome on your phone.

---

## 📺 Touch Screen Display Mode (Virtual Touchscreen)

Switch to the **📺 Screen** tab to see your live Windows desktop right on your phone!

| Action | Touch Gesture |
| :--- | :--- |
| **Direct Click** | Tap anywhere on the live PC screen $\to$ clicks that exact button/window on PC |
| **Right Click** | Hold finger down on screen for >350ms (or tap `🖱️ R-Click` on toolbar) |
| **Drag & Select** | Switch to `✋ Drag Mode` on the toolbar $\to$ touch & drag windows or text |
| **Pinch to Zoom** | Pinch with 2 fingers to zoom in up to 4x for clicking small desktop icons |
| **2-Finger Pan** | Drag with 2 fingers while zoomed in to pan across your desktop |
| **On-Screen Keyboard** | Tap `⌨️` on the top toolbar to open the quick text & shortcuts drawer |
| **Stream Quality** | Choose `⚡ Balanced` (30 FPS), `✨ High Res`, or `🚀 Max FPS` (40+ FPS) |

---

## 🖱️ Trackpad Mode Gestures

| Action | Touch Gesture |
| :--- | :--- |
| **Move Cursor** | Glide 1 finger across the trackpad area |
| **Left Click** | Tap once with 1 finger (or use bottom `LEFT CLICK` button) |
| **Right Click** | Tap with 2 fingers (or use bottom `RIGHT CLICK` button) |
| **Middle Click** | Tap bottom `MIDDLE` button (opens links in new tab / closes browser tabs) |
| **Smooth Scroll** | Swipe up / down with 2 fingers, or drag the dedicated side scroll strip |
| **Air Mouse** | Switch to **Air Mouse** tab, hold button, and wave your phone in the air! |

---

## 📁 Generated Files

- [`NeonTrack.exe`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/NeonTrack.exe) - Standalone Windows executable server.
- [`NeonTrack.apk`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/NeonTrack.apk) - Standalone Android application package.
- [`run.bat`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/run.bat) / [`start.ps1`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/start.ps1) - 1-click startup scripts.
- [`server/`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/server) - Python FastAPI, screen streaming & native Win32 input simulator.
- [`static/`](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/static) - Cyber-Neon Glassmorphism web client with live canvas stream.
