# 🪟 PCDeck — Microsoft Store Master Release Kit & Submission Guide

This single master document contains **everything** required to publish **PCDeck** to the **Microsoft Store (Windows 10/11)** via Microsoft Partner Center, fill out every submission questionnaire, pass certification review on the first attempt, and package future updates.

---

## 📁 1. Master Asset Directory (Quick File Index)

All required release binaries, store artwork, and high-DPI manifest assets are located in:
📂 c:\Users\GRESON\Documents\mobile_tracpad_for_pc\msstore_assets\

| Asset Type | Exact File Path | Specs |
|---|---|:---:|
| **Production MSIX Package** | [msstore_assets/PCDeck.msix](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/PCDeck.msix) | Windows App Package (x64, v1.0.0.0) |
| **Store 1:1 App Box Art / Logo** | [msstore_assets/StoreLogo_300x300.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StoreLogo_300x300.png) | 300 × 300 (32-bit PNG) |
| **Spotlight Hero Banner (Featured)** | [msstore_assets/StoreHero_2400x1200.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StoreHero_2400x1200.png) | 2400 × 1200 (2:1 Hero Graphic) |
| **Store Hero Banner (16:9)** | [msstore_assets/StoreHero_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StoreHero_1920x1080.png) | 1920 × 1080 (16:9 Hero Graphic) |
| **Store Promotional Poster** | [msstore_assets/StorePoster_1240x600.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StorePoster_1240x600.png) | 1240 × 600 (Poster Graphic) |
| **Desktop Screenshot 1** | [msstore_assets/1_Hero_Desktop_Suite_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/1_Hero_Desktop_Suite_1920x1080.png) | 1920 × 1080 (Hero Suite & Pairing) |
| **Desktop Screenshot 2** | [msstore_assets/2_MultiTouch_Trackpad_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/2_MultiTouch_Trackpad_1920x1080.png) | 1920 × 1080 (Multi-Touch Trackpad) |
| **Desktop Screenshot 3** | [msstore_assets/3_Desktop_Screen_Mirroring_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/3_Desktop_Screen_Mirroring_1920x1080.png) | 1920 × 1080 (Screen Mirroring 60 FPS) |
| **Desktop Screenshot 4** | [msstore_assets/4_Live_Keyboard_Typing_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/4_Live_Keyboard_Typing_1920x1080.png) | 1920 × 1080 (Live Keyboard & Shortcuts) |
| **Desktop Screenshot 5** | [msstore_assets/5_Local_File_Sharing_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/5_Local_File_Sharing_1920x1080.png) | 1920 × 1080 (Local Wi-Fi File Transfers) |
| **Desktop Screenshot 6** | [msstore_assets/6_PC_Audio_Loopback_Streaming_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/6_PC_Audio_Loopback_Streaming_1920x1080.png) | 1920 × 1080 (PC Audio Loopback Stream) |
| **Desktop Screenshot 7** | [msstore_assets/7_Instant_QR_Code_Pairing_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/7_Instant_QR_Code_Pairing_1920x1080.png) | 1920 × 1080 (3-Second QR Code Pairing) |
| **High-DPI Manifest Icons** | [msstore_assets/Manifest_Assets/](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/Manifest_Assets) | 46 Scaled Tiles (scale-100 to 400, targetsize) |

---

## 🎯 2. High-Converting ASO Store Listing Copy

Copy and paste these directly into the **Store listings** section in Microsoft Partner Center.

### 🏷️ Product Title
`	ext
PCDeck: Wireless Trackpad, Screen Mirror & Remote
`

### 📝 Short Description (Under 100 characters)
`	ext
Turn your phone into a multi-touch trackpad, screen mirror & PC remote over local Wi-Fi.
`

### 📄 Full Description (Formatted for Microsoft Store)
`	ext
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
`

### ⚡ Key Features (Bullet Points for Store Listing)
`	ext
• Wireless multi-touch trackpad with ballistic cursor acceleration and gesture clicks
• Low-latency desktop screen mirroring with 30 FPS and 60 FPS streaming modes
• 1:1 direct physical touch tracking and kinetic momentum scrolling
• Full virtual mechanical keyboard layout, Numpad cluster, and Windows hotkeys
• Cable-free high-speed local Wi-Fi file sharing and batch transfer queues
• Real-time WASAPI stereo PC audio loopback streaming to phone earphones
• Media control deck with volume slider and live audio visualizer
• Instant 3-second QR code network pairing with zero configuration
• 100% offline local network communication with zero cloud accounts or telemetry
`

### 🔍 Search Terms / Keywords (7 Exact Phrases)
`	ext
1. remote mouse
2. wireless trackpad
3. screen mirroring
4. pc remote control
5. wifi file transfer
6. wireless keyboard
7. audio streamer
`

---

## 📋 3. Step-by-Step Microsoft Partner Center Submission Guide

Follow these steps in the [Microsoft Partner Center](https://partner.microsoft.com/dashboard):

### Step 1: Reserve Product Name
1. Log in to your Microsoft Partner Center account.
2. Go to **Apps and games > Overview > New product > MSIX or PWA app**.
3. Enter product name: PCDeck: Wireless Trackpad, Screen Mirror & Remote (or PCDeck).
4. Click **Check availability** and **Reserve product name**.

---

### Step 2: Pricing and Availability
1. **Markets**: Select **All possible markets** (Worldwide).
2. **Pricing**: Select **Free**.
3. **Discoverability**: Select **Make this product available in the Microsoft Store**.
4. **Publish date**: Select **Publish this submission immediately after certification**.
5. Click **Save**.

---

### Step 3: Product Properties
1. **Category**:
   - Primary: **Utilities & tools**
   - Secondary: **Productivity**
2. **Support Contact Info**:
   - Support email: gresonparichha719@gmail.com
   - Privacy Policy URL: https://pcdeck.vercel.app/privacy (or hosted privacy_policy.html)
   - Website: https://pcdeck.vercel.app
3. **Hardware Requirements**:
   - Keyboard: **Required**
   - Mouse: **Required**
   - Touch: **Recommended**
   - Wi-Fi / Local Area Network adapter: **Required**
4. Click **Save**.

---

### Step 4: Age Ratings (IARC Questionnaire)
1. Enter email address: gresonparichha719@gmail.com
2. App category: Select **Utility, Productivity, Communication, or Other**.
3. Violence, Sexual Content, Language, Controlled Substances, Gambling: Select **No** to all.
4. Miscellaneous:
   - Does the app share user location? **No**
   - Does the app collect personal data? **No**
   - Does the app allow users to purchase digital goods? **No** (Base app is free)
5. Click **Save and generate rating**. Result: **All Ages / Everyone / PEGI 3**.

---

### Step 5: App Declarations & Notes for Certification (Crucial)

#### Declarations:
- Check **This product has been tested to meet the accessibility guidelines**.
- Check **This product uses restricted capabilities** (unFullTrust).

#### Notes for Certification (Copy & Paste for Reviewers):
`	ext
PCDeck is a 100% offline local Wi-Fi utility that enables users to control their Windows PC from their smartphone (acting as a wireless multi-touch trackpad, virtual keyboard, low-latency screen mirror, audio loopback streamer, and local file manager).

Why runFullTrust is required:
1. Win32 Input Injection: Uses user32.dll (mouse_event / SendInput) to simulate mouse cursor moves, left/right clicks, wheel scrolls, and keyboard hotkeys sent from the user's paired mobile device over local WebSocket.
2. WASAPI Loopback Audio: Uses Windows Core Audio APIs (WASAPI loopback capture) to stream desktop audio to the user's phone earphones.
3. Local HTTP / WebSocket Server: Hosts a lightweight local server on 127.0.0.1 / local LAN IP (port 8000) strictly for peer-to-peer communication between the user's PC and phone.

All communication occurs 100% locally over LAN. Zero external cloud servers, zero internet requirements, and zero user data collection.
`

---

### Step 6: Store Listings & Visual Artwork Upload
Navigate to **Store listings > English (United States)**:

1. **Text**:
   - Paste **Description**, **Short Description**, **Features**, and **Search Terms** from Section 2 above.
2. **Logos & Artwork**:
   - **App tile icon (300 × 300)**: Upload [msstore_assets/StoreLogo_300x300.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StoreLogo_300x300.png)
   - **Spotlight / Featured Hero (2400 × 1200)**: Upload [msstore_assets/StoreHero_2400x1200.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StoreHero_2400x1200.png)
   - **Promotional Hero (1920 × 1080)**: Upload [msstore_assets/StoreHero_1920x1080.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StoreHero_1920x1080.png)
   - **Poster Art (1240 × 600)**: Upload [msstore_assets/StorePoster_1240x600.png](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/StorePoster_1240x600.png)
3. **Desktop Screenshots**: Upload all 7 screenshots from msstore_assets/:
   - 1_Hero_Desktop_Suite_1920x1080.png
   - 2_MultiTouch_Trackpad_1920x1080.png
   - 3_Desktop_Screen_Mirroring_1920x1080.png
   - 4_Live_Keyboard_Typing_1920x1080.png
   - 5_Local_File_Sharing_1920x1080.png
   - 6_PC_Audio_Loopback_Streaming_1920x1080.png
   - 7_Instant_QR_Code_Pairing_1920x1080.png
4. Click **Save**.

---

### Step 7: Packages Upload
1. Navigate to the **Packages** page.
2. Drag and drop:
   📂 c:\Users\GRESON\Documents\mobile_tracpad_for_pc\msstore_assets\PCDeck.msix
3. Partner Center will validate the package identity, target architecture (x64), and capabilities (unFullTrust).
4. Click **Save**.

---

### Step 8: Submit to the Store
1. Review the submission summary page.
2. Click **Submit to the Store**.
3. Certification typically completes within 24–48 hours.

---

## 🔄 4. How to Build & Publish Future MSIX Updates

Whenever you update PCDeck features or fix bugs:

1. **Increment Version in 	ools/build_msix.py**:
   Update Version="1.0.1.0" in APPX_MANIFEST.
2. **Rebuild MSIX Package**:
   Run the 1-click batch script in PowerShell:
   `powershell
   .\build_msix.bat
   `
3. **Upload New Package in Partner Center**:
   - Go to Partner Center > PCDeck > **Update**.
   - Upload the new msstore_assets/PCDeck.msix.
   - Update the release notes.
   - Click **Submit to the Store**.

---

## 📞 Developer Contact & Support Details

- **Developer Name:** Greshon Parichha
- **Support Email:** gresonparichha719@gmail.com
- **Application Name:** PCDeck
- **Official Website:** https://pcdeck.vercel.app
- **Distribution Model:** 100% Offline Local Wi-Fi Utility (Free, Zero Ads)
