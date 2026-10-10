# PCDeck — Website Architecture & Web Context

> [!IMPORTANT]
> **MANDATORY REFERENCE FOR WEBSITE & LANDING PAGE WORK**:
> This document details the complete architecture, design tokens, routing rules, SEO standards, conversion mechanics, and verification protocols for the PCDeck public website hosted on Vercel (`https://pcdeck.vercel.app/`).

---

## 1. Hosting, Deployment & Mirror Architecture

- **Hosting Platform**: Vercel Serverless / Static Hosting.
- **Repository Structure & Production Mirror**:
  - Root directory contains deployment files (`index.html`, `guide.css`, `va.js`, `/es/`, `/pt/`, guides).
  - `website/` contains the mirror and build artifacts (`website/index.html`, `website/guide.css`, `website/PROJECT_CONTEXT.md`, etc.).
  - **Synchronization Invariant**: Changes made to web pages must be reflected across both deployment root and the `website/` directory.
- **Total Monitored Pages**: **62 HTML documents** covering:
  - Homepage (`/`, `/index.html`).
  - Multilingual portals (`/es/`, `/pt/`).
  - Dedicated OS & architecture download pages (`/download/`, `/download/windows/`, `/download/android/`, `/download/linux/`).
  - High-traffic technical guides (`/use-pc-without-mouse/`, `/connect-pc-to-pc-wifi/`, `/browser-pc-remote/`, `/control-linux-pc-from-phone/`, `/guides/`, etc.).
  - Diagnostics & tooling (`/analytics-console/`, `/connect`).
- **Routing Configuration (`vercel.json`)**:
  - `"trailingSlash": true`: Prevents 308 redirect loops between slash and non-slash canonical URLs.
  - Custom headers configured for MIME types, caching headers, and direct binary downloads (`.exe`, `.apk`, `.msix`).

---

## 2. Design System & Cyber-Neon Glassmorphism

- **Core Color Tokens (CSS Variables)**:
  - Background Canvas: `--bg: #07090e;` (Deep obsidian dark background).
  - Panel / Cards: `--paper: #0c1017;` / `--panel: #111722;` (Subtle elevated surfaces).
  - Primary Accent / Glow: `--signal: #1b44d8;` / `--accent: #00f0ff;` (Electric cyan & cobalt).
  - Foreground Text: `--fg: #e2e8f0;` / `--ink: #f8fafc;` (Crisp readable high-contrast typography).
  - Muted Text: `--muted: #94a3b8;` (Secondary metadata, instructions, and timestamps).
  - Grid Lines & Borders: `--grid: rgba(255, 255, 255, 0.08);` / `--line: #1e293b;`.
- **Typography**:
  - Headings: `var(--font-display)` (`Outfit`, sans-serif, 700/800 weight).
  - Code & Checksums: `var(--font-mono)` (`JetBrains Mono`, monospace).
  - Body: `var(--font-body)` (`Inter`, system-ui, sans-serif).
- **Responsive Grid Invariant**:
  - Card grids (`repeat(auto-fit, minmax(..., 1fr))`) must **never** hardcode `minmax` minimum width greater than `280px`.
  - Ensures clean rendering without horizontal overflow on narrow mobile screens (320px–360px).

---

## 3. Navigation Architecture & DOM Isolation Standards

- **Top Navigation Bar (`header.top`)**:
  - Sticky/fixed header with backdrop blur: `backdrop-filter: blur(12px)`.
  - Mobile Menu Toggle: `#nav-toggle` button with `#mobile-menu` slide-out drawer. Every page containing `header.top` must implement the toggle listener script.
- **DOM Isolation Invariant (No Nesting Inside Modals)**:
  - Modal backdrops with `position: fixed; inset: 0; opacity: 0; pointer-events: none;` (such as `#emergency-guide-modal`) must **never** encapsulate sibling sections.
  - Active page sections (such as `#download`, `#community`, `#faq`) must reside as direct children of `<main>`.
  - Modals must be placed outside `<main>` directly above `<footer>` or `</body>`.
- **Smooth-Scroll Navigation Handler (`scrollToTarget`)**:
  - Navigation anchors (`a[href="#download"]`, `a[href="#download-cards"]`, `a[href="#community"]`) use smooth scrolling.
  - Dynamically offsets fixed navbar height: `target.getBoundingClientRect().top + window.pageYOffset - navH - 8`.
  - Automatically handles deep-links on page load via `window.location.hash`.

---

## 4. Above-the-Fold Download Conversion Standard

- **Direct Anchor to Action Cards (`#download-cards`)**:
  - Hero and top navigation "Download" buttons point directly to `#download-cards`.
  - Action buttons (`Download PCDeck.exe` and `Download PCDeck.apk`) are centered above the fold upon arrival.
- **Compact Header Spacing**:
  - The `#download` section header maintains tight vertical padding (`padding: 36px 0 20px`).
  - Eliminates excessive dead space so users on laptops, monitors, tablets, and phones immediately see the download buttons.
- **Instant Golden 3-Step Flow**:
  1. Download & launch `PCDeck.exe` on Windows (zero drivers or setup).
  2. Scan the QR code with phone camera.
  3. Instant control over local Wi-Fi.
- **Strict 3-Card Layout Invariant (`#download-cards`)**:
  - The download cards grid must **strictly** contain exactly 3 primary action cards:
    1. **Windows Card (`#card-exe`)**: Primary glowing standalone executable (`PCDeck.exe`).
    2. **Android Card (`#card-apk`)**: Direct APK download (`PCDeck.apk`).
    3. **Linux Card (`#card-linux`)**: 1-line curl launcher script (`run_linux.sh`).
  - **Absolute Prohibition on 4th Offline ZIP Bundle (`PCDeck_Package.zip`)**:
    - `PCDeck.exe` already embeds `PCDeck.apk` directly and serves it to mobile devices over local LAN at `GET /PCDeck.apk` upon scanning the pairing QR code.
    - Never add `PCDeck_Package.zip` back to `#download-cards` or subpages. It caused confusion, layout clutter, and release bloat.
  - **Windows 2-Option Distribution Model & Prohibition on Setup Installers**:
    - Windows distribution is strictly governed by a 2-option model:
      1. **Microsoft Store (`PCDeck.msix` / Store Direct Web Installer)**: Default for installed usage. Auto-updating, signed with verified Microsoft publisher trust, and zero SmartScreen friction.
      2. **Standalone Portable (`PCDeck.exe`)**: For users seeking a zero-install binary that runs immediately from anywhere.
    - **Permanent Discontinuation of `PCDeck-Setup.exe`**: Inno Setup (`ISCC.exe` / `PCDeck_Setup.iss`) is permanently retired. Never add `PCDeck-Setup.exe` or traditional Win32 installer downloads back to the website.

---

## 5. Community, Suggestions & Direct Feedback Section (`#community`)

- **Location**: Direct child of `<main>` preceding `</main>`, styled with `scroll-margin-top: 74px;`.
- **Direct Support Channels**:
  - **Official Reddit Feedback Thread**: Community bug tracking, questions, and feature requests.
  - **1-Click Clipboard Email Copy**:
    - Copies `dogonews67@gmail.com` via `navigator.clipboard.writeText()`.
    - Shows dynamic visual confirmation toast (`✔ Copied to Clipboard!`).
    - Graceful fallback opens `mailto:dogonews67@gmail.com?subject=[PCDeck]%20Feedback`.
  - **Web Gmail Link**: Direct web compose URL for users without desktop mail clients.
- **Android WebView Compatibility**:
  - Native `MainActivity.java` intercepts `mailto:` and `reddit.com` URLs to open native device apps instead of throwing WebView navigation errors.

---

## 6. Technical Guides & Readability (Anti-Wall-of-Text Standard)

- **Scannable Visuals Invariant**:
  - Guides must never present unbroken walls of continuous prose.
  - Every technical guide must embed high-resolution product screenshots and diagrams:
    - `hero-suite.png`: Complete PCDeck ecosystem overview.
    - `qr-pairing.png`: Local Wi-Fi pairing and QR code scan demonstration.
    - `trackpad-phone.png`: Phone trackpad with multi-touch gestures and buttons.
    - `screen-stream.png`: Real-time PC screen streaming with floating toolbar.
    - `file-transfer.png`: High-speed local LAN file transfer interface.
  - Formatted using semantic `<figure class="guide-figure">` with dark borders, rounded corners (`border-radius: 10px`), and descriptive `<figcaption>`.
- **30-Second Rapid Connection Checklist**:
  - Every guide features a prominent boxed checklist (`.guide-quickstart-card`):
    1. **Download & Launch**: Run `PCDeck.exe` on Windows or 1-line script on Linux.
    2. **Same Local Wi-Fi**: Connect PC and phone to the same router or hotspot.
    3. **Scan QR Code**: Open phone camera to scan screen QR code.
    4. **Instant Control**: Immediate trackpad, keyboard, and screen mirror.

---

## 7. Search Engine Optimization (SEO) & Semantic Quality

- **Seobility Critical Error Prevention**:
  - Strictly avoid empty bold/strong tags (`<b></b>`, `<strong></strong>`) for layout shapes or monitor stand graphics.
  - All visual elements must use semantic `<span>` with CSS classes or pseudo-elements.
- **Meta Title & Description Bounds**:
  - Titles: Strictly **50–64 characters** (Bing & Google compliant).
  - Descriptions: Strictly **140–155 characters**.
- **Structured Data Standards**:
  - Guide templates include JSON-LD schemas (`TechArticle`, `HowTo`, `BreadcrumbList`, `FAQPage`).
  - Hash anchors (`#step-1`..`#step-4`) must match actual DOM IDs.
- **Multilingual Standards**:
  - Localized hubs: Spanish (`/es/`) and Portuguese (`/pt/`).
  - Bidirectional `<link rel="alternate" hreflang="..." href="...">` tags covering `en`, `es`, `pt`, and `x-default`.
- **Search Engine Indexing & IndexNow**:
  - Key: `2b967b3e45cd4a0cafab08e647e1fc47` (accessible at `/2b967b3e45cd4a0cafab08e647e1fc47.txt`).
  - Automated CI/CD ping pipeline via `.github/workflows/indexnow.yml` on HTML/sitemap changes.

---

## 8. Web Analytics & Conversion Event Tracking Pipeline (`va.js`)

- **Universal Script**: Included on all 62 HTML documents via `<script defer src="/va.js"></script>`.
- **Search Engine Bot & Crawler Preservation**:
  - Automated bot & headless scraper detection (`isBotEnvironment()`) excludes automated crawlers from analytics without interfering with SEO indexing.
- **Owner Self-Visit Exclusion**:
  - Multi-tier exclusion preventing testing traffic from skewing analytics:
    1. 10-Year Cookie: `pcdeck_analytics_optout=1`.
    2. LocalStorage: `pcdeck_analytics_optout = '1'`.
    3. URL Param: `?admin=1`, `?dev=1`, `?owner=1`, `?notrack=1` registers exclusion automatically.
    4. Management Console: `/analytics-console/` or `/ignore-my-visit/`.
    5. Footer Toggle: `#btn-analytics-toggle` displaying real-time status (`🛡️ Analytics: Excluded` or `Active`).
- **Automated Custom Event Dispatching (`window.va('event', ...)`)**:
  - Automatically intercepts interactive clicks across all pages and dispatches custom events to Vercel Web Analytics:
    1. `download_windows_msstore`: Primary Windows channel. Intercepts `get.microsoft.com`, `apps.microsoft.com`, `9p4bk16lbgls`, `ms-windows-store:`, and text containing `"MS Store"` / `"Microsoft Store"`.
    2. `download_windows_exe`: Secondary standalone `.exe` channel. Intercepts `pcdeck.exe`, `/download/windows`, and `"standalone .exe"`.
    3. `download_windows`: Universal aggregate event fired whenever either Windows channel is triggered.
    4. `download_android`: Intercepts `pcdeck.apk`, `/download/android`, and `"download apk"`.
    5. `download_linux`: Intercepts `run_linux.sh`, `install.sh`, `/download/linux`, and `"linux setup"`.
    6. `open_web_remote`: Intercepts `/connect/`, `/browser-pc-remote/`, and `"web remote"`.
    7. `mobile_bridge_email`: Intercepts `mailto:` links pre-filling PC download URLs for mobile visitors.
    8. `mobile_bridge_copy`: Intercepts 1-click clipboard copy of desktop download links on mobile.
    9. `guide_click`: Tracks technical guide readership and category engagement.
- **Direct Download Page Handlers**:
  - `/download/windows/index.html` and `/download/android/index.html` use `window.va('event', { name: ... })` (strictly avoiding deprecated/unsupported `va('track', ...)`).

---

## 9. Verification & Automated Quality Assurance

Run before committing any web changes:
```powershell
python tools/verify_website.py
```
**Verification Checklist**:
- [x] All 62 HTML files contain `<meta name="viewport">`.
- [x] Headers contain mobile menu toggles and script handlers.
- [x] Exact balance of `<header>`, `<main>`, and `<footer>` tags across all files.
- [x] `guide.css` and `index.html` define all required CSS design tokens.
- [x] Zero CSS grid minmax definitions with hardcoded widths exceeding 280px.
- [x] Root deployment files and `website/` mirror remain in 100% bit-for-bit parity.

---

## 10. Ground-Truth Acquisition & Funnel Performance (First 16 Days: Sep 23 – Oct 08, 2026)

To avoid erroneous optimization assumptions, all web decisions must align with verified telemetry across all 3 primary consoles:

### A. Microsoft Partner Center (Windows Store & MSIX Direct Installer — Published Sep 23, 2026)
- **First 16 Days Installs**: **86 successful installations** (15 complete telemetry days, ~5.73/day average; recent velocity **6.8–7.0 installs/day**).
- **Store Page Views**: **205 views**.
- **Store Conversion Rate**: **41.95%** (Industry standard for desktop utilities is 15–20%).
- **Install Success Rate**: **100.0%** (zero package deployment failures across all 86 installs).
- **Runtime Engagement**: **50 Monthly Active Devices (MAD - Opt-in)** across **77 active sessions** (~1.54 sessions/device).
- **User-Initiated Uninstalls**: **Only 2 uninstalls** out of 86 (**97.7% retention rate**).
- **Stickiness (DAD / MAD)**: **16.69%** (exceeds 8–12% standard desktop utility benchmark).
- **Technical Stability**: Crash-free stability patch prepared in v2.7.4.0.
- **Top Geographic Distribution**: India (19 active devices, 38%), France (7, 14%), United States (4, 8%), Japan (2, 4%), Sierra Leone (3), Qatar (1), Dominican Republic (2).

### B. Google Search Console (Organic Web Performance)
- **Sandbox Graduation**: Average position surged from Page 6 (Pos 55–63) in August to consistent **Page 1 (Pos 5.5–10)** starting mid-September.
- **Mobile Rank Super-Weapon**: Mobile devices rank at **Position 6.98 with 7.46% CTR** (vs. Desktop at Pos 45.11). Confirms necessity of Mobile Bridge ("Email to PC" / "Copy Link") above the fold.
- **Star Landing Page**: `/browser-pc-remote/` achieved **20 clicks, 164 impressions, 12.2% CTR, Position 8.18**.
- **Topical Clustering**: Google indexes PCDeck across 100+ "No Mouse / Broken Mouse" long-tail queries (`/use-pc-without-mouse/` has 707 impressions on Google).

### C. Bing Webmaster Tools (Windows Edge Searchers)
- **Desktop Search Growth**: Sustained volume of **50 to 71 impressions/day** with steady daily clicks (up to 10% CTR).
- **High Intent**: 100% desktop Windows users using default Microsoft Edge / Windows Search, directly driving primary MSIX Web Installer downloads.

---

## 11. Pro Monetization, Aesthetic Themes & Payment Strategy

### A. Value Proposition & Transparent Pricing
- **Model**: Single lifetime purchase ($3.99 one-time). No subscriptions, no ads, no cloud lock-in.
- **Payment Provider**: Dodo Payments (`dodopayments.com`) providing merchant-of-record compliance, localized currency checkout, and automatic coupon support.
- **Regional Purchasing Power Parity (PPP)**: The app intelligently detects non-Western markets via native Win32 GeoID checks to display fair regional pricing at checkout while preserving standard $3.99 baseline in top Western markets (US, UK, DE, FR, JP).

### B. Aesthetic Themes as Viral Conversion Driver
- Themes serve as a visual status symbol and emotional hook for power users, converting casual users to Pro without paywalling core hardware trackpad/mouse utility.
- 8 Pure CSS Themes: Cyber Cyan (Free Default), Frutiger Aero (Pro), Y2K Chrome (Pro), CRT Phosphor (Pro), Synthwave (Pro), Solar Gold (Pro), Matrix Lime (Pro), OLED Pure Dark (Pro).
- Zero external image assets or tacky emojis: 100% responsive, high-performance CSS glassmorphism, hardware scanlines, and tactile styling.

### C. Developer Testing & Promo Protocols
- **Local Dev Testing (100% Free)**: Use `python server/license_manager.py --activate-local-dev` to bind an authentic HMAC-SHA256 license to local HWID for complete offline testing.
- **Full Cloud Gateway Testing**: Use Dodo Payments 100% discount promo codes (e.g. `PCDECK100`) to test the real customer checkout flow, key generation, and cloud license verification without incurring credit card charges.

---

## 12. Strategic Marketing Roadmap, Custom Domain Protocol & Video Funnel Invariants

### A. Custom Domain Prerequisite (Strict Invariant)
- **Invariant**: Secure the custom domain (e.g. `pcdeck.app`, `usepcdeck.com`, `pcdeck.net`) **BEFORE** executing external backlink campaigns or launching YouTube promotion.
- **Rationale**:
  1. *Prevents Google 301 Re-indexing Dip*: Shifting accumulated search volume from `.vercel.app` &rarr; custom domain triggers a 2–4 week ranking and traffic fluctuation.
  2. *Permanent Backlink Equity*: External directory listings permanently anchor the developer URL; securing the custom domain first guarantees 100% of directory backlink authority transfers directly to the owned domain.
  3. *Brand Perception*: Professional custom domains convert significantly higher than free subdomains.

### B. Directory Submission Targets (Post-Domain Priority)
- **Softpedia (DA 85)**: Fast editorial review, verified malware scan, provides the authoritative "100% CLEAN" safety badge.
- **Uptodown (DA 88)**: Massive global audience (strong in Europe and LATAM), zero-fee developer portal, hosts both Windows `.exe` and Android `.apk`.
- **Softonic (DA 92)**: High-authority editorial backlink to boost Google Page 1 ranking.
- **FileHorse / MajorGeeks (DA 75–80)**: Exposure to desktop utility and power-user IT communities.

### C. YouTube Shorts & Mobile Frictionless Funnel Standard
- **Zero Raw Store Links on Mobile**: Never place raw Microsoft Store deep links (`ms-windows-store:...` or `apps.microsoft.com/...`) as the sole link in mobile video descriptions or pinned comments (90%+ of Shorts viewers are on smartphones where Windows Store links trigger OS incompatibility errors and instant drop-offs).
- **Frictionless Bridge Routing**: Video links must route to `https://pcdeck.vercel.app/` (or future custom domain `/download/`), leveraging the native Mobile-to-PC Bridge:
  - *Mobile Viewers*: Immediately access the Android APK or instant browser remote (`/browser-pc-remote/`) plus 1-tap "Email link to PC" / "Copy PC link" for when they reach their desktop.
  - *Desktop Viewers*: Automatically served the official Microsoft Store Direct Web Installer button above the fold.
- **High-Converting Video Formats**:
  - *Problem/Solution Short (30–45s)*: "Mouse broke mid-game / mid-work &rarr; turned phone into 0-lag PC trackpad over Wi-Fi (zero ads, 100% offline)."
  - *Evergreen Search Guide (2–3m)*: "How to stream PC audio to phone headphones over Wi-Fi without Bluetooth or cables."

---

## 13. Production Release v2.7.4 & Store Update Management

- **Release Highlights**:
  - **Android System Share Sheet Integration**: Direct "Share to PCDeck" target allows sharing photos, videos, documents, or text from any Android app directly to the connected Windows PC over local Wi-Fi.
  - **Crash Prevention & AppUserModelID Hardening**: Fixed the Windows Shell MSIX AppUserModelID conflict, session-local mutex fallback, and safe working directory mapping to ensure zero startup crashes.
  - **Port 8000 & Network Endpoint Stability**: Verified 200 OK responses on `/connect`, `/`, and local `/PCDeck.apk` serving.
- **Active Binary Checksums & Checksum Sync**:
  - `PCDeck.exe`: `38,072,930 bytes` | SHA256: `71E4B67A6B2ED0CD784A95E21B41407CEDE135F220B701066514DD3029535574`
  - `PCDeck.apk`: `711,443 bytes` | SHA256: `C5351806A94C182C093189136589D6D657DA58F70F8DFDCEC215E0C4D0FD24D1`
  - `PCDeck_Store_Upload.msix`: `40,151,167 bytes` | SHA256: `50FC6125A1FF47D8D6C249366EC331D6F06C108FF9A173148EA2B0924182D064`



