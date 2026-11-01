# Privacy Policy for PCDeck

**Last Updated:** August 29, 2026  
**Effective Date:** August 29, 2026  

PCDeck ("we," "our," or "the application") is committed to protecting your privacy. This Privacy Policy explains how PCDeck handles information when you use our Android application and desktop companion server.

---

## 1. Core Principles: 100% Offline & Local-First

PCDeck is built from the ground up as a **100% offline, local peer-to-peer utility**. 
- **No Cloud Accounts:** You do not need to create an account, log in, or provide an email address.
- **No Telemetry or Tracking:** We do not collect, track, or transmit analytics, crash logs, diagnostic data, or personal information to any external server or third party.
- **No Advertising:** PCDeck contains no third-party advertisements or ad-tracking SDKs.
- **Local Network Only:** All communication (mouse input, keyboard strokes, screen mirroring, audio streaming, and file transfers) takes place exclusively within your private local Wi-Fi or mobile hotspot network between your phone and your PC.

---

## 2. Device Permissions and How They Are Used

PCDeck requests only the minimum permissions necessary to deliver its core wireless utility features:

### A. Camera (`CAMERA`)
- **Purpose:** Used exclusively to scan the QR code displayed on the PC Companion Server window for instant pairing.
- **Data Handling:** Camera frames are analyzed entirely in real-time in your device's memory. No photos, videos, or visual recordings are ever saved, stored on disk, or transmitted over any network.

### B. Network & Wi-Fi (`INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE`, `CHANGE_WIFI_MULTICAST_STATE`)
- **Purpose:** Used to discover your PC companion server on the local Wi-Fi/Hotspot network and establish direct peer-to-peer WebSocket and HTTP connections for touch trackpad input, screen stream reception, audio stream playback, and file transfers.
- **Data Handling:** All network packets remain strictly inside your local private subnet (e.g., `192.168.x.x`). No internet connection is required or used to transmit data to the outside world.

### C. Storage & Files (`READ_EXTERNAL_STORAGE`, `WRITE_EXTERNAL_STORAGE`, Scoped Storage)
- **Purpose:** Used solely when you explicitly choose to transfer files between your phone and your PC using the in-app File Transfer tool.
- **Data Handling:** Only files you explicitly select for upload or download are accessed and transferred directly between your phone and PC over the local network. We never index, read, or catalog your personal files without direct user action.

### D. Audio Playback
- **Purpose:** Plays the real-time audio PCM stream relayed from your PC over the local Wi-Fi connection.
- **Data Handling:** Audio data is buffered temporarily in volatile memory for live playback through your device speakers or headphones and is immediately discarded.

---

## 3. Data Collection, Storage, and Sharing

- **Personal Data Collected:** **None.**
- **Third-Party Data Sharing:** **None.** We do not sell, rent, trade, or share any user data with any third party, analytics provider, or advertiser.
- **Cloud Storage:** None. PCDeck operates without any cloud backend or remote database.

---

## 4. Children’s Privacy (COPPA Compliance)

PCDeck does not collect any personal information from any user, including children under the age of 13. The application is completely safe for general audiences.

---

## 5. Security

Because all communications occur strictly over your private local Wi-Fi or encrypted mobile hotspot without traversing the public internet or external proxy servers, your interactions remain confined to your private local network environment.

---

## 6. Changes to This Privacy Policy

We may update this Privacy Policy from time to time to reflect changes in functionality or legal requirements. Any updates will be posted with a revised "Last Updated" date.

---

## 7. Contact Us

If you have any questions, concerns, or requests regarding this Privacy Policy or PCDeck, please contact the developer directly:
- **Developer:** Greshon Parichha
- **Email:** [gresonparichha719@gmail.com](mailto:gresonparichha719@gmail.com)
