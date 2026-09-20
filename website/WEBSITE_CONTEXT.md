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

## 8. Web Analytics & Owner Opt-Out Architecture (`va.js`)

- **Universal Script**: Included on all 62 HTML documents via `<script defer src="/va.js"></script>`.
- **Search Engine Bot & Crawler Preservation**:
  - Standard crawler traffic is preserved to maintain accurate crawlability and search visibility metrics.
- **Owner Self-Visit Exclusion**:
  - Multi-tier exclusion preventing testing traffic from skewing analytics:
    1. 10-Year Cookie: `pcdeck_analytics_optout=1`.
    2. LocalStorage: `pcdeck_analytics_optout = '1'`.
    3. URL Param: `?admin=1` registers exclusion automatically.
    4. Management Console: `/analytics-console/`.
    5. Footer Toggle: `#btn-analytics-toggle` displaying real-time status (`🛡️ Analytics: Excluded` or `Active`).

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
