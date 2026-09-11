# PCDeck — Microsoft Store Master Release Kit & Submission Guide

This single master document contains **everything** required to publish **PCDeck** to the **Microsoft Store (Windows 10/11)** via Microsoft Partner Center, fill out every submission questionnaire, pass certification review on the first attempt, and package future updates.

---

## 1. Master Asset Directory (Quick File Index)

All required release binaries, store artwork, and high-DPI manifest assets are located in:
 c:\Users\GRESON\Documents\mobile_tracpad_for_pc\msstore_assets\

| Asset Type | Exact File Path | Specs |
|---|---|:---:|
| **Production Win32 Installer (.exe)** | [msstore_assets/PCDeck-Setup.exe](file:///c:/Users/GRESON/Documents/mobile_tracpad_for_pc/msstore_assets/PCDeck-Setup.exe) | Windows Inno Setup Installer (x64, v2.7.0) |
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

## 2. High-Converting ASO Store Listing Copy

Copy and paste these directly into the **Store listings** section in Microsoft Partner Center (`Apps and games > Store listings > English (United States)`).

### Product Title
```text
PCDeck: Wireless Mouse, Trackpad, Webcam & PC Remote
```

### Short Description (Under 100 characters)
```text
No phone app needed: scan QR code to use your phone as a mouse, webcam & PC remote over local Wi-Fi.
```
*(99 characters — strictly under the 100-character Partner Center limit).*

### Full Description (Formatted for Microsoft Store)
```text
PCDeck turns any smartphone or tablet into a wireless trackpad, mouse, PC screen mirror, HD webcam, microphone, keyboard, and file transfer tool for Windows 10 & 11 — with ZERO mobile app installation required.

Whether your mouse battery died, you need an HD webcam for Zoom, or you want to control PC media from your couch, just scan the QR code on your PC screen with your phone camera. It connects instantly in your mobile browser (Safari, Chrome, Firefox, Edge). 

No app store downloads. No cables. No account creation. No cloud servers. No subscriptions. 
Point, scan, and you have a precision wireless trackpad in under 3 seconds.

============================================================
WHAT YOU CAN DO WITH PCDECK
============================================================

WIRELESS TRACKPAD & MOUSE
• Turn your phone screen into a smooth, responsive laptop-style touchpad.
• Intuitive multi-touch gestures: 1-finger tap to left-click, 2-finger tap to right-click.
• Long-press to drag and drop files or reposition desktop windows.
• Dedicated edge scrolling strip for reading documents, PDFs, and websites.

PHONE AS WIRELESS WEBCAM
• Use your smartphone's camera as an HD virtual webcam on your PC.
• Compatible with Zoom, Microsoft Teams, Discord, OBS Studio, and Google Meet.
• Front and rear camera switching with smooth local video streaming.

DESKTOP SCREEN MIRRORING & TOUCH CONTROL
• Stream your Windows desktop directly to your phone screen in real time.
• Interact with your desktop using direct touch: tap, double-click, and pinch-to-zoom.
• Smooth scrolling with natural kinetic inertia.

WIRELESS MICROPHONE
• Use your phone as an external microphone for your PC.
• Useful for voice calls, gaming chat, meetings, and quick voice recordings.

KEYBOARD & SHORTCUT DECK
• Type text into any Windows application directly from your phone.
• Access Windows hotkeys with a single tap: Task View, Alt+Tab, Win+D, and Snipping Tool.
• Includes dedicated Function keys (F1–F12) and Esc key.

HIGH-SPEED LOCAL FILE TRANSFER
• Send photos, videos, archives, and documents between your phone and PC.
• High-speed local Wi-Fi transfers with zero file size limits and no cloud uploads.
• Direct folder shortcuts to your PC Desktop and Downloads folders.

STEREO AUDIO STREAMING & MEDIA CONTROLS
• Stream audio from your PC directly to your phone earphones.
• Dedicated media remote: Play/Pause, Next/Previous track, and master Windows volume slider.

============================================================
WHY USERS CHOOSE PCDECK
============================================================
• Zero Mobile App Installation: No App Store or Google Play downloads required. Connects instantly via your phone's built-in web browser (or optional companion app).
• 100% Local & Private: Runs entirely on your local Wi-Fi or mobile hotspot. Keystrokes, camera feeds, and files never leave your home network.
• Zero Account Hassle: No email sign-ups, no passwords, and no login screens.
• Lightweight & Fast: Clean background execution without bloated background services or invasive drivers.
• Universal Compatibility: Works with any iPhone, Android, iPad, or tablet and Windows 10/11 PCs.

============================================================
PERFECT FOR
============================================================
• Emergency mouse/keyboard replacement when batteries die or devices disconnect.
• Streaming movies, YouTube, or Netflix on your PC while controlling playback from bed.
• Work and study: using your phone as a high-quality webcam for conferences.
• Navigating presentations in conference rooms or classrooms without a clicker.
• Sending large video files and photos between phone and PC without USB cables.

============================================================
SYSTEM REQUIREMENTS
============================================================
• PC running Windows 10 or Windows 11 (64-bit).
• Phone and PC connected to the same Wi-Fi network (or phone Wi-Fi hotspot).
• Any modern mobile web browser (Safari, Chrome, Edge, Firefox) — no app download required.
```

###  Key Features (Bullet Points for Store Listing)
```text
• Zero phone app install required: scan PC screen QR code to connect instantly in any browser
• Ultra-responsive wireless trackpad with multi-touch gestures and edge scrolling
• Turn your phone into an HD wireless PC webcam for Zoom, Teams, Discord, and OBS
• Real-time desktop screen mirroring with direct touch control and pinch-to-zoom
• Wireless PC microphone using your smartphone mic over local Wi-Fi
• Virtual keyboard with instant Unicode typing and one-tap Windows shortcuts
• High-speed local Wi-Fi file sharing without file size limits or cloud uploads
• Stream PC audio directly to your phone earphones with media controls
• 100% local peer-to-peer connection — no accounts, no cloud, no telemetry
```

###  Search Terms / Keywords (7 Exact Phrases)
```text
1. remote mouse
2. wireless trackpad
3. pc remote
4. phone webcam
5. screen mirror
6. wireless keyboard
7. wifi file transfer
```

---

##  3. Step-by-Step Microsoft Partner Center Submission Guide

Follow these steps in the [Microsoft Partner Center](https://partner.microsoft.com/dashboard):

### Step 1: Reserve Product Name
1. Log in to your Microsoft Partner Center account.
2. Go to **Apps and games > Overview > New product**.
3. Choose **Win32 app** (or **Windows & Xbox** app).
4. Enter product name: `PCDeck: Wireless Trackpad, Screen Mirror & Remote` (or `PCDeck`).
5. Click **Check availability** and **Reserve product name**.

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
- Check **This product uses restricted capabilities** (
unFullTrust).

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

### Step 7: Packages & Installer Configuration

Microsoft Store supports both **Win32 (.exe installers)** and **MSIX packages**.

#### Option A: Win32 Application (.exe Installer) — [RECOMMENDED]
*Why: Allows automatic DirectShow virtual camera registration, firewall configuration, and future virtual mic audio drivers without sandbox restrictions.*

1. Navigate to the **Package setup** or **Installer** page in Partner Center.
2. Fill in the installer properties:
   - **Installer download URL:** `https://pcdeck.vercel.app/PCDeck-Setup.exe` (or direct GitHub Release link `https://github.com/<username>/pcdeck/releases/download/v2.7.0/PCDeck-Setup.exe`)
   - **Installer type:** `.exe`
   - **Silent install parameters:** `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-`
   - **Silent uninstall command:** `"{autopf}\PCDeck\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
   - **Main executable name:** `PCDeck.exe`
   - **Installer binary architecture:** `x64`
   - **Does installer require administrator elevation?**: Check **Yes** (required to register DirectShow filters and firewall rules).
3. Click **Save**.

---

#### Option B: MSIX Package Upload
If you submit via MSIX container instead:
1. Navigate to the **Packages** page.
2. Drag and drop:
    `c:\Users\GRESON\Documents\mobile_tracpad_for_pc\msstore_assets\PCDeck.msix`
3. Click **Save**.

---

### Step 8: Submit to the Store
1. Review the submission summary page.
2. Click **Submit to the Store**.
3. Certification typically completes within 24–48 hours.

---

##  4. How to Build & Publish Future Updates

### For Win32 Installer (.exe):
1. Increment the version in `version.json`, `version_info.txt`, and `PCDeck_Setup.iss` (e.g. `2.7.1`).
2. Rebuild the standalone executable and installer:
   ```cmd
   python build_exe.py
   python tools\build_installer.py
   ```
   *(Or simply run `build_installer.bat`)*
3. Upload the new `PCDeck-Setup.exe` to your website or GitHub Release.
4. In Microsoft Partner Center, click **Update**, update the release notes and installer URL, and submit.

### For MSIX Package:
1. Increment `Version="x.x.x.x"` in `tools\build_msix.py`.
2. Run `build_msix.bat`.
3. Upload `msstore_assets\PCDeck.msix` to Partner Center.

---

##  Developer Contact & Support Details

- **Developer Name:** Greshon Parichha
- **Support Email:** gresonparichha719@gmail.com
- **Application Name:** PCDeck
- **Official Website:** https://pcdeck.vercel.app
- **Distribution Model:** 100% Offline Local Wi-Fi Utility (Free, Zero Ads)
