#!/usr/bin/env python3
"""
tools/apply_seo_phase2.py
Applies audited Phase 2 SEO optimizations to website/ files:
- use-phone-as-keyboard title/description
- monect-alternative title/description
- control-linux-pc-from-phone Wayland/Hyprland section
- pt/index.html title/description
- es/index.html title/description + #como-lo-uso block (with corrected links)
- de/index.html title/description
- browser-pc-remote competitor comparison table
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT / "website"

def update_file(path: Path, old: str, new: str, desc: str):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"[-] FAILED to find target chunk in {path.name}: {desc}")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[+] Updated {path.name}: {desc}")
    return True

def apply_keyboard_guide():
    p = WEBSITE / "use-phone-as-keyboard" / "index.html"
    text = p.read_text(encoding="utf-8")
    # Replace title
    text = re.sub(
        r'<title>.*?</title>',
        '<title>Use Phone as Wireless PC Keyboard (Free, No App) | PCDeck</title>',
        text, count=1
    )
    # Replace description
    text = re.sub(
        r'<meta name="description" content=".*?">',
        '<meta name="description" content="Use your Android or iPhone as a wireless keyboard and numpad for Windows or Linux over local Wi-Fi. Type from any mobile browser on port 8000 with no app.">',
        text, count=1
    )
    # Replace og:title
    text = re.sub(
        r'<meta property="og:title" content=".*?">',
        '<meta property="og:title" content="Use Phone as Wireless PC Keyboard (Free, No App) | PCDeck">',
        text, count=1
    )
    # Replace og:description
    text = re.sub(
        r'<meta property="og:description" content=".*?">',
        '<meta property="og:description" content="Use your Android or iPhone as a wireless keyboard and numpad for Windows or Linux over local Wi-Fi. Type from any mobile browser on port 8000 with no app.">',
        text, count=1
    )
    # Replace twitter:title
    text = re.sub(
        r'<meta name="twitter:title" content=".*?">',
        '<meta name="twitter:title" content="Use Phone as Wireless PC Keyboard (Free, No App) | PCDeck">',
        text, count=1
    )
    # Replace twitter:description
    text = re.sub(
        r'<meta name="twitter:description" content=".*?">',
        '<meta name="twitter:description" content="Use your Android or iPhone as a wireless keyboard and numpad for Windows or Linux over local Wi-Fi. Type from any mobile browser on port 8000 with no app.">',
        text, count=1
    )
    p.write_text(text, encoding="utf-8")
    print(f"[+] Updated {p.name}: use-phone-as-keyboard meta")

def apply_monect_guide():
    p = WEBSITE / "monect-alternative" / "index.html"
    text = p.read_text(encoding="utf-8")
    text = re.sub(
        r'<title>.*?</title>',
        '<title>Best Monect PC Remote Alternative (Free, No App) | PCDeck</title>',
        text, count=1
    )
    text = re.sub(
        r'<meta name="description" content=".*?">',
        '<meta name="description" content="Looking for a lightweight Monect PC Remote alternative? Control Windows or Linux from any phone browser over Wi-Fi with zero virtual drivers or adware.">',
        text, count=1
    )
    text = re.sub(
        r'<meta property="og:title" content=".*?">',
        '<meta property="og:title" content="Best Monect PC Remote Alternative (Free, No App) | PCDeck">',
        text, count=1
    )
    text = re.sub(
        r'<meta property="og:description" content=".*?">',
        '<meta property="og:description" content="Looking for a lightweight Monect PC Remote alternative? Control Windows or Linux from any phone browser over Wi-Fi with zero virtual drivers or adware.">',
        text, count=1
    )
    text = re.sub(
        r'<meta name="twitter:title" content=".*?">',
        '<meta name="twitter:title" content="Best Monect PC Remote Alternative (Free, No App) | PCDeck">',
        text, count=1
    )
    text = re.sub(
        r'<meta name="twitter:description" content=".*?">',
        '<meta name="twitter:description" content="Looking for a lightweight Monect PC Remote alternative? Control Windows or Linux from any phone browser over Wi-Fi with zero virtual drivers or adware.">',
        text, count=1
    )
    p.write_text(text, encoding="utf-8")
    print(f"[+] Updated {p.name}: monect-alternative meta")

def apply_linux_guide():
    p = WEBSITE / "control-linux-pc-from-phone" / "index.html"
    text = p.read_text(encoding="utf-8")
    
    wayland_block = """
    <!-- Task 7: Wayland & Hyprland Deep-Dive Block (Pos 12 -> Top 3) -->
    <section id="wayland-hyprland-uinput-architecture" style="margin: 32px 0;">
      <h2>Why PCDeck Works Natively on Wayland &amp; Hyprland (Kernel <code>/dev/uinput</code> Architecture)</h2>
      <p>
        Most Linux remote control apps fail on modern distributions because they rely on the legacy X11 <code>XTest</code> extension or <code>xdotool</code>. Under Wayland compositors—including <strong>Hyprland</strong>, <strong>Sway</strong>, <strong>GNOME (Mutter)</strong>, and <strong>KDE Plasma 6 (KWin)</strong>—X11 synthetic events are blocked by protocol design to prevent malicious background windows from spoofing input.
      </p>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin: 20px 0;">
        <div style="background: var(--paper); border: 1px solid var(--grid); border-radius: 6px; padding: 16px 18px;">
          <h3 style="font-size: 15px; margin: 0 0 8px; color: var(--ink);">1. Kernel-Level <code>evdev</code> Injection</h3>
          <p style="font-size: 13.5px; line-height: 1.5; color: var(--graphite); margin: 0;">
            PCDeck registers a virtual hardware pointer and keyboard directly with the Linux kernel input subsystem (<code>/dev/uinput</code>). Both <code>libinput</code> and <code>wlroots</code> (Hyprland/Sway) treat PCDeck as a genuine physical input device.
          </p>
        </div>

        <div style="background: var(--paper); border: 1px solid var(--grid); border-radius: 6px; padding: 16px 18px;">
          <h3 style="font-size: 15px; margin: 0 0 8px; color: var(--ink);">2. Rootless <code>udev</code> Permission Rule</h3>
          <p style="font-size: 13.5px; line-height: 1.5; color: var(--graphite); margin: 0;">
            You never need to run the PCDeck server as root. The 1-line <code>install.sh</code> script configures a clean <code>udev</code> rule granting your local user group write access to <code>/dev/uinput</code> safely in userspace.
          </p>
        </div>

        <div style="background: var(--paper); border: 1px solid var(--grid); border-radius: 6px; padding: 16px 18px;">
          <h3 style="font-size: 15px; margin: 0 0 8px; color: var(--ink);">3. Hyprland Keybind &amp; Workspace Ready</h3>
          <p style="font-size: 13.5px; line-height: 1.5; color: var(--graphite); margin: 0;">
            Because PCDeck emits genuine kernel keycodes, your existing <code>hyprland.conf</code> keybinds, workspace switches, and floating window drag modifiers trigger with zero compositor configuration.
          </p>
        </div>
      </div>
    </section>
"""
    if "wayland-hyprland-uinput-architecture" not in text:
        target = '<h2>Ubuntu 24.04 LTS &amp; Modern Wayland Compositors</h2>'
        if target in text:
            text = text.replace(target, wayland_block + "\n    " + target, 1)
            p.write_text(text, encoding="utf-8")
            print(f"[+] Inserted Wayland & Hyprland deep-dive block in {p.name}")
        else:
            print("[-] Could not find target insertion point in control-linux-pc-from-phone")

def apply_international_pages():
    # PT
    pt_p = WEBSITE / "pt" / "index.html"
    text = pt_p.read_text(encoding="utf-8")
    text = re.sub(
        r'<title>.*?</title>',
        '<title>PCDeck: Controle Remoto de PC e Mouse no Celular (Sem App)</title>',
        text, count=1
    )
    text = re.sub(
        r'<meta name="description" content=".*?">',
        '<meta name="description" content="Transforme seu celular Android ou iPhone em mouse, teclado e controle remoto para PC Windows e Linux via Wi-Fi. Use no navegador na porta 8000 ou via APK.">',
        text, count=1
    )
    pt_p.write_text(text, encoding="utf-8")
    print("[+] Updated pt/index.html")

    # ES
    es_p = WEBSITE / "es" / "index.html"
    text = es_p.read_text(encoding="utf-8")
    text = re.sub(
        r'<title>.*?</title>',
        '<title>PCDeck: Control Remoto de PC y Ratón en el Móvil (Sin App)</title>',
        text, count=1
    )
    text = re.sub(
        r'<meta name="description" content=".*?">',
        '<meta name="description" content="Convierte tu móvil Android o iPhone en ratón touchpad, teclado y mando para PC Windows o Linux por Wi-Fi. Úsalo gratis desde el navegador sin aplicaciones.">',
        text, count=1
    )
    
    como_lo_uso_block = """
<!-- Task 9.2: Spanish 2-Option Clarity Block (#como-lo-uso) -->
<section id="como-lo-uso" class="direct-answer" style="margin: 28px 0; background: var(--panel); border: 1.5px solid var(--grid); border-left: 4px solid var(--signal); border-radius: 8px; padding: 22px 24px;">
  <h2 style="font-size: 20px; color: var(--ink); margin-bottom: 8px;">¿Cómo lo uso? Elige entre 2 Opciones en Windows y 2 Formas en tu Móvil</h2>
  <p style="font-size: 14.5px; color: var(--graphite); line-height: 1.6; margin-bottom: 16px;">
    Con PCDeck no necesitas crear cuentas ni instalar controladores virtuales pesados. Elige la forma que prefieras para conectar tu ordenador y tu teléfono por Wi-Fi local:
  </p>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px;">
    <div style="background: var(--paper); border: 1px solid var(--grid); border-radius: 6px; padding: 14px 16px;">
      <h3 style="font-size: 15px; margin: 0 0 6px; color: var(--ink);">Opción 1: Sin Instalar Nada en el Móvil (Navegador Puerto 8000)</h3>
      <p style="font-size: 13.5px; color: var(--graphite); line-height: 1.5; margin: 0;">
        Instala PCDeck desde la <a href="https://get.microsoft.com/installer/download/9P4BK16LBGLS">Microsoft Store (<code>9P4BK16LBGLS</code>)</a> en Windows (o ejecuta el script en <a href="/control-linux-pc-from-phone/">Linux y Steam Deck</a>). Escanea el código QR con la cámara de tu Android o iPhone para controlar el PC directamente desde tu navegador web.
      </p>
    </div>

    <div style="background: var(--paper); border: 1px solid var(--grid); border-radius: 6px; padding: 14px 16px;">
      <h3 style="font-size: 15px; margin: 0 0 6px; color: var(--ink);">Opción 2: Ejecutable Portátil <code>PCDeck.exe</code> + App Nativa <code>PCDeck.apk</code></h3>
      <p style="font-size: 13.5px; color: var(--graphite); line-height: 1.5; margin: 0;">
        ¿Prefieres otra forma sin pasar por la tienda de Windows? Descarga el ejecutable portátil independiente <a href="/PCDeck.exe"><code>PCDeck.exe</code></a> (sin instalación) y, en Android, usa la aplicación nativa ligera <a href="/PCDeck.apk"><code>PCDeck.apk</code></a>.
      </p>
    </div>
  </div>
</section>
"""
    if "como-lo-uso" not in text:
        target = '</header>'
        if target in text:
            text = text.replace(target, target + "\n" + como_lo_uso_block, 1)
            es_p.write_text(text, encoding="utf-8")
            print("[+] Inserted #como-lo-uso block in es/index.html")
    else:
        es_p.write_text(text, encoding="utf-8")
        print("[+] Updated es/index.html")

    # DE
    de_p = WEBSITE / "de" / "index.html"
    text = de_p.read_text(encoding="utf-8")
    text = re.sub(
        r'<title>.*?</title>',
        '<title>PCDeck: PC-Fernbedienung &amp; Maus auf dem Handy (Ohne App)</title>',
        text, count=1
    )
    text = re.sub(
        r'<meta name="description" content=".*?">',
        '<meta name="description" content="Nutzen Sie Android oder iPhone per WLAN als kabelloses PC-Touchpad, Maus und Tastatur für Windows und Linux. Kostenlos im Browser auf Port 8000 ohne App.">',
        text, count=1
    )
    de_p.write_text(text, encoding="utf-8")
    print("[+] Updated de/index.html")

def apply_browser_remote():
    p = WEBSITE / "browser-pc-remote" / "index.html"
    text = p.read_text(encoding="utf-8")
    
    benchmark_table = """
    <!-- Task 3.3: PC Remote Competitor Comparison Benchmark -->
    <section id="pc-remote-comparison-benchmark" style="margin: 36px 0;">
      <h2>PCDeck vs. Monect, Remote Mouse &amp; Unified Remote (Technical Benchmark)</h2>
      <p>
        Legacy remote control utilities require installing synchronized apps on both devices, frequently inject kernel-level virtual drivers, and lock basic keyboard or screen features behind subscriptions. Compare the architecture:
      </p>

      <table class="keys">
        <thead>
          <tr>
            <th>Capability / Vector</th>
            <th>PCDeck</th>
            <th>Monect PC Remote</th>
            <th>Remote Mouse</th>
            <th>Unified Remote</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Phone App Required?</strong></td>
            <td><strong>No (Port 8000 Web Remote + optional <code>PCDeck.apk</code>)</strong></td>
            <td>Yes (Mandatory App Store / APK install)</td>
            <td>Yes (Mandatory iOS / Android app)</td>
            <td>Yes (Mandatory iOS / Android app)</td>
          </tr>
          <tr>
            <td><strong>Windows Host Footprint</strong></td>
            <td><strong>Portable <code>PCDeck.exe</code> or MS Store (<code>9P4BK16LBGLS</code>)</strong></td>
            <td>Full installer + virtual HID/gamepad drivers</td>
            <td>Background Windows service installer</td>
            <td>Background service + driver installer</td>
          </tr>
          <tr>
            <td><strong>Linux Wayland &amp; Steam Deck</strong></td>
            <td><strong>Native (Kernel <code>/dev/uinput</code> via 1-line <code>install.sh</code>)</strong></td>
            <td>Windows-focused host</td>
            <td>Legacy X11 only</td>
            <td>Breaks on Wayland compositors (Hyprland/GNOME)</td>
          </tr>
          <tr>
            <td><strong>Cloud Accounts &amp; Login</strong></td>
            <td><strong>None (Instant LAN QR pairing)</strong></td>
            <td>Account prompts &amp; ad network SDKs</td>
            <td>In-app account / purchase verification</td>
            <td>Optional cloud account sync</td>
          </tr>
          <tr>
            <td><strong>Privacy &amp; Telemetry</strong></td>
            <td><strong>100% Local Wi-Fi / Zero Telemetry</strong></td>
            <td>Collects usage &amp; advertising identifiers</td>
            <td>Includes analytics &amp; crash telemetry</td>
            <td>Includes app analytics</td>
          </tr>
          <tr>
            <td><strong>Price / Paywalled Features</strong></td>
            <td><strong>100% Free (All core trackpad/mouse features unlocked)</strong></td>
            <td>Ad-supported; VIP subscription for pro features</td>
            <td>Paywalls landscape keyboard &amp; media keys</td>
            <td>Paywalls custom remotes &amp; screen view</td>
          </tr>
        </tbody>
      </table>
      <p style="font-size: 14px; color: var(--muted); margin-top: 10px;">
        Looking for a dedicated breakdown? Read our full <a href="/monect-alternative/">Monect PC Remote Alternative guide</a>.
      </p>
    </section>
"""
    if "pc-remote-comparison-benchmark" not in text:
        target = '<h2>Frequently Asked Questions About Browser PC Remote</h2>'
        if target in text:
            text = text.replace(target, benchmark_table + "\n    " + target, 1)
            p.write_text(text, encoding="utf-8")
            print(f"[+] Inserted competitor benchmark table in {p.name}")
        else:
            print("[-] Target heading not found in browser-pc-remote")

if __name__ == "__main__":
    apply_keyboard_guide()
    apply_monect_guide()
    apply_linux_guide()
    apply_international_pages()
    apply_browser_remote()
    print("\n[OK] Phase 2 SEO modifications applied to website/ directory.")
