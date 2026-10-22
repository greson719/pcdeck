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
    - Copies `gresonparichha719@gmail.com` via `navigator.clipboard.writeText()`.
    - Shows dynamic visual confirmation toast (`✔ Copied to Clipboard!`).
    - Graceful fallback opens `mailto:gresonparichha719@gmail.com?subject=[PCDeck]%20Feedback`.
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

### B. Google Search Console (Organic Web Performance — Aug 25 – Oct 16, 2026)
- **Consolidated Telemetry**: **90 total clicks**, **2,140 impressions**, **4.21% average CTR**.
- **Sandbox Graduation & Traffic Scaling**: Average position surged from Page 6 (Pos 55–63) in August to consistent **Page 1 (Pos 4.2–8.5)** by mid-October. Daily velocity climbed from 0–1 clicks/day in August to sustained **4–9 clicks/day** in October (peak: 9 clicks, 80 impressions at Pos 4.2 on Oct 15).
- **Mobile Rank Super-Weapon**: Mobile searchers rank at **Position 6.33 with 5.66% CTR** (636 impressions, 36 clicks), outperforming Desktop (Pos 33.92, 1,479 impressions, 54 clicks) due to high mobile-intent queries ("control PC from phone").
- **Star Landing Page (`/browser-pc-remote/`)**: Primary traffic generator driving **58 clicks (64.4% of site traffic)**, 415 impressions, **13.98% CTR**, and Position 6.90. Confirms dominant product-market fit for zero-install browser remote queries.
- **Top Converting Queries**: `pcdeck` (brand: 6 clicks, Pos 5.08), `from browser` (Pos 1.0, 100% CTR), `online` (Pos 2.0), `without any software` (Pos 2.0), `free` (Pos 3.0).
- **High-Volume Search Clusters**:
  - `/control-linux-pc-from-phone/`: 513 impressions at **Position 7.08** (Page 1). Title and meta description streamlined to 57/148 chars with Steam Deck desktop mode targeting.
  - `/use-pc-without-mouse/`: 851 impressions (highest impression footprint on site) indexing over 100+ broken mouse / emergency keyboard navigation queries.
- **Top Click Geographies**: India (12 clicks, 216 imp), United States (10 clicks, 539 imp), Brazil (6 clicks, 12.8% CTR), Indonesia (5 clicks, 9.8% CTR).

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

## 13. Production Release v2.7.6 & Store Update Management

- **Release Highlights (v2.7.6.0)**:
  - **Multi-PC Switcher**: Instant switching between multiple computers from Settings in 1 tap with zero UI clutter on single-PC setups.
  - **MachineGuid Licensing**: 100% immune to Wi-Fi/MAC randomization, VPN toggles, and network churn.
  - **Offline Migration Engine**: Migrates legacy v2.7.5 activations in 0.001s without server pings.
  - **Download Stream Resiliency**: Eliminated 1.14 KB chunked truncation on first-time APK downloads via middleware streaming exemption.
  - **Desktop Window Version Label**: Added version indicator (`self.version_lbl`) at the bottom-right of the desktop server control panel.
  - **Active Binary Checksums (v2.7.6.0)**:
    - `PCDeck.exe`: `38,655,319 bytes` | SHA256: `42552AABE95BA5D278849F461B37727378F52B072A221DF4A93F0A6E9BE9AC8C`
    - `PCDeck.apk`: `998,228 bytes` | SHA256: `CE5280580976A0CB3A98CD9A596902398C1141BAB6C23F1E0076AF1AFFF1A7EC`
    - `PCDeck_Store_Upload.msix`: `40,738,378 bytes` | SHA256: `A0B95D731B744C186701D19383603BA52A7F5DFBB1A022189842B7A7C4136EC9`

---

## 14. Commercial & Conversion Telemetry (Updated October 20, 2026)
- **Microsoft Store**: 155 acquisitions, 375 page views, 41.33% conversion, 100% install success rate.
- **Vercel Analytics**: 158 weekly unique visitors (+84% WoW), 234 page views (+77% WoW), peak 34 daily visitors.
- **Search Console & Bing**: >4,000 combined impressions, 143 organic search clicks.
- **Dodo Payments Revenue**: 8 Pro license keys sold ($31.92 Gross Volume), $18.74 available payout balance (threshold: $50 USD).

---

## 15. Custom Domain Launch: getpcdeck.com (October 22, 2026)

- **Domain**: `getpcdeck.com` (Official Primary Canonical)
- **Secondary / Redirect**: `www.getpcdeck.com` (`308 Permanent Redirect` -> `https://getpcdeck.com/`)
- **Legacy Fallback**: `pcdeck.vercel.app` (Preserved as active production alias)
- **Registrar & Nameservers**: Hostinger (`apollo.dns-parking.com`, `athena.dns-parking.com`)
- **DNS Records**:
  - `A @ 216.198.79.1` (TTL 300)
  - `CNAME www getpcdeck.com` (TTL 300)
  - `TXT @ google-site-verification=9GdXotk3owSHTyICyxvvEFWIx9WU-XTtAYuBFL6InRc` (TTL 14400)
- **Verification Telemetry**:
  - `https://getpcdeck.com` $\implies$ HTTP 200 OK (Vercel Edge, SSL Active)
  - `http://getpcdeck.com` $\implies$ HTTP 308 Permanent Redirect to HTTPS
  - `https://www.getpcdeck.com` $\implies$ HTTP 308 Permanent Redirect to `https://getpcdeck.com/`
- **Global Codebase & Canonical Migration**:
  - 122 files migrated (all 66 HTML pages, OpenGraph, JSON-LD schemas, breadcrumbs, `sitemap.xml`, `robots.txt`, `llms.txt`, `api/version.js`).
  - Android App Links: `android_app/AndroidManifest.xml` configured with `getpcdeck.com` & `www.getpcdeck.com`.
  - Binaries rebuilt & signed: `PCDeck.apk` (974.8 KB) and standalone `PCDeck.exe` (36.9 MB).
- **Search Engine Discovery**:
  - **IndexNow / Bing**: 32 URLs submitted and accepted (`HTTP 200 OK` / `HTTP 202 Accepted`).
  - **Google Search Console**: Verified domain ownership via DNS TXT. `sitemap.xml` submitted with status **`Success`** (29+ discovered URLs).

---

## 16. Dedicated Transparent Pricing Page (/pricing/)

- **Canonical URL**: `https://getpcdeck.com/pricing/` (HTTP 200 OK live verified).
- **Design Philosophy**:
  - Clean, high-density side-by-side comparison.
  - Zero AI slop, zero generic emojis, built on `guide.css` design tokens.
- **Tiers**:
  - **PCDeck Core ($0 Free Forever)**: Multi-touch trackpad, virtual keyboard & numpad, 30 FPS screen mirroring, PC audio streaming, webcam, mic, file transfer, standard gamepad.
  - **PCDeck Pro ($3.99 One-Time Lifetime)**: 60/120 FPS high-refresh mirroring, custom HUD keymapper, uncapped gigabit Wi-Fi file transfers, neon chroma themes.
- **Checkout Link**: Dodo Payments integration (`https://checkout.dodopayments.com/buy/pdt_0Np7oiRe7Art1gb9IAx8K?quantity=1&redirect_url=https://getpcdeck.com`).
- **Structured Data**: JSON-LD `Product` with multi-tier `Offer` schemas (`Free Software` + `One-time Lifetime License`), `BreadcrumbList`, and `FAQPage`.
- **Sync**: Files present in both `pricing/index.html` and `website/pricing/index.html`.

---

## 17. High-Authority Backlink Pipeline & Directory Status (Domain Authority)

- **Microsoft Partner Center (DA 99)**: Official Store listing submission updated with `Website: https://getpcdeck.com` and `Privacy Policy: https://getpcdeck.com/privacy_policy.html`.
- **GitHub Repository (DA 96)**: `homepageUrl` set to `https://getpcdeck.com`.
- **SaaSHub (DA 75)**:
  - Product listing live and verified: `https://www.saashub.com/pcdeck` (HTTP 200 OK).
  - Backlink to `https://getpcdeck.com` active on page.
  - Categories: `Remote Desktop`, `Utilities`, `OS & Utilities`, `Remote PC Access`, `Remote Control`, `Multi Monitor`, `Productivity`, `Office & Productivity`.
  - Competitor associations: Remote Mouse, Unified Remote, Monect, KDE Connect, AudioRelay, DroidCam, Spacedesk, AnyDesk, Microsoft Remote Desktop, Splashtop, LogMeIn, Macro Deck, TouchPortal, Deckboard, MATRIC.
  - Pricing synced: Freemium ($0 Free Option / $3.99 One-off Pro Option linking to `https://getpcdeck.com/pricing/`).
  - Status: Verification passed, listing live, product in review queue for featured placement.
- **AlternativeTo (DA 80+)**: Submission in review queue (Day 26).
- **Next Directory Targets**: SourceForge (DA 93), Softpedia (DA 88), Product Hunt (DA 90).





