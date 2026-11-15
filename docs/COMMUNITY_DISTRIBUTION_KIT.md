# PCDeck — Community Distribution & Backlink Kit

This kit provides ready-to-use listing descriptions, community forum posts, and launch copy for PCDeck (`https://getpcdeck.com`).

---

## 1. AlternativeTo.net Listing Kit

- **Name:** PCDeck
- **URL:** `https://getpcdeck.com/`
- **License:** Free / Freemium ($3.99 Lifetime Pro)
- **Platforms:** Windows (10/11), Linux, Android, Web / Browser (iOS Safari, Android Chrome)
- **Tagline:** Free browser-based PC remote, wireless trackpad, 1080p webcam, and audio streamer.
- **Competitors to tag against:**
  - Unified Remote (`https://getpcdeck.com/unified-remote-alternative/`)
  - Monect PC Remote (`https://getpcdeck.com/monect-alternative/`)
  - Remote Mouse (`https://getpcdeck.com/remote-mouse-alternative/`)
  - WiFi Mouse (`https://getpcdeck.com/wifi-mouse-alternative/`)
  - Reincubate Camo (`https://getpcdeck.com/use-iphone-as-webcam-windows/`)
  - iVCam
  - Spacedesk (`https://getpcdeck.com/use-phone-as-second-monitor/`)
- **Key Features:**
  - Zero mobile app install required (connects over LAN via phone browser)
  - 100% offline local WebSocket architecture (no cloud, no telemetry)
  - Turn phone into virtual webcam for Zoom, Discord, OBS (720p Free, 1080p 60 FPS Pro)
  - Ultra-low latency touchpad with multi-touch gestures and edge scrolling
  - Screen mirroring and desktop touch control
  - Native Linux & Steam Deck Desktop Mode support via uinput

---

## 2. Product Hunt / Slant / Hacker News (Show HN)

### Hacker News Show HN:
- **Title:** Show HN: PCDeck – Control your PC from your phone browser without installing an app
- **Text:**
```text
Hey HN,

I built PCDeck (https://getpcdeck.com) because existing phone-as-mouse and remote control tools (Unified Remote, Monect, Remote Mouse) were bloated with ad networks, required installing companion apps from mobile app stores, or demanded cloud accounts for simple local LAN control.

PCDeck takes a zero-install browser approach:
1. Run the lightweight executable on your PC (or a one-line bash script on Linux/Steam Deck).
2. Scan the on-screen QR code with your iPhone (Safari) or Android (Chrome).
3. Your mobile browser immediately connects via local WebSockets (port 8000) and serves an ultra-low latency canvas trackpad with multi-touch, keyboard input, audio loopback, and webcam streaming.

No cloud relay, no external telemetry, and no account required. It operates 100% offline on your local Wi-Fi or mobile hotspot.

Source code and Windows/Linux builds: https://github.com/greson719/pcdeck
Webcam guide: https://getpcdeck.com/use-iphone-as-webcam-windows/
Linux guide: https://getpcdeck.com/control-linux-pc-from-phone/

Feedback and questions are welcome.
```

---

## 3. Reddit Community Outreach Posts

### r/windows11 & r/selfhosted (Homelab / Headless Management)
- **Title:** Built a lightweight, zero-install PC remote and webcam tool for Windows 11 (operates 100% offline via local Wi-Fi)
- **Body:**
```text
If your mouse battery ever died mid-game or you needed a quick trackpad/keyboard for a headless mini PC on your desk, you usually had to download an ad-filled app from the App Store.

I built PCDeck to solve this cleanly:
- Runs locally on Windows 10/11 (Microsoft Store verified or standalone .exe).
- When you scan the QR code on your monitor, it opens in Safari or Chrome without installing any mobile app.
- Includes a 1:1 trackpad with two-finger scrolling, hotkey deck, audio streaming, and phone-as-webcam for OBS/Discord.
- 100% local peer-to-peer. Works completely offline without internet access.

Website: https://getpcdeck.com
Headless setup guide: https://getpcdeck.com/use-pc-without-monitor/
```

### r/SteamDeck (Desktop Mode Remote)
- **Title:** Control Steam Deck Desktop Mode from your phone browser without Bluetooth pairing
- **Body:**
```text
Typing terminal commands or navigating Desktop Mode without a physical mouse/keyboard is awkward on the Deck.

PCDeck runs via a single curl command on SteamOS and exposes a local web trackpad and keyboard:
curl -sSL https://getpcdeck.com/install.sh | bash

Scan the QR code with your phone camera and you have an instant touchpad in Safari/Chrome.
Guide: https://getpcdeck.com/control-linux-pc-from-phone/
```
