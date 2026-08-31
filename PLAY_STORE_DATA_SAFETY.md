# Google Play Console — Data Safety Form Guide

Use this exact guide when filling out the **Data safety** section in the Google Play Console for **PCDeck**.

---

## 1. Data Collection and Security

| Question in Play Console | Answer | Explanation |
|---|:---:|---|
| **Does your app collect or share any of the required user data types?** | **No** | PCDeck does not collect, record, log, or transmit any user data to any external server or third party. |
| **Is all of the user data collected by your app encrypted in transit?** | **Yes** / **N/A** (Select Yes if asked) | Local network peer-to-peer communication. |
| **Do you provide a way for users to request that their data be deleted?** | **Yes** (or N/A since no data is collected) | No user accounts or remote data exist to delete. |

---

## 2. App Permissions Declarations

### Camera (`android.permission.CAMERA`)
- **Category:** Device or other IDs / App Functionality
- **Collected:** **No** (Processed ephemerally in volatile memory on-device only).
- **Shared:** **No**.
- **Purpose:** App Functionality (Scanning the PC companion pairing QR code).

### Photos and Videos / Files (`Storage / Media`)
- **Category:** Files and docs
- **Collected:** **No** (Files are transferred peer-to-peer locally between user's own PC and phone only when user explicitly taps Send / Save).
- **Shared:** **No**.
- **Purpose:** App Functionality (Local Wi-Fi file sharing).

---

## 3. Privacy Policy URL for Play Console

Enter the URL where you host `privacy_policy.html` (e.g., via GitHub Pages):
```
https://<your-username>.github.io/mobile_tracpad_for_pc/privacy_policy.html
```
*(Or upload `privacy_policy.html` to any free static host like Vercel, Netlify, or Google Sites).*

---

## 4. Developer Contact Details

- **Developer Name:** Greshon Parichha
- **Contact Email:** `gresonparichha719@gmail.com`
- **Application Category:** Tools / Productivity / Remote Desktop
