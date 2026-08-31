"""
PCDeck - Smart Wi-Fi / Hotspot Manager for Windows.

Design goals (in order):
  1. Never trust English netsh strings alone. Windows is localized; the previous
     implementation silently reported "disconnected" on every non-English system
     because it matched the literal word "connected".
  2. Decide "am I actually reachable by the phone?" from routable IPv4 facts, not
     from driver text. A link that says "connected" but only holds a 169.254.x.x
     APIPA address is useless for serving the client.
  3. Assume the radio is cheap. Budget USB dongles and low-end laptop cards
     return empty scan lists on the first poll, drop the link under load, and
     get stuck needing a DHCP renew or an adapter power-cycle. Retry, then heal.
  4. Persist state somewhere that survives a PyInstaller onefile run.

Public API kept backwards compatible with the previous module:
    load_wifi_config, save_wifi_config, get_current_wifi_status,
    get_saved_profiles, scan_visible_networks, connect_to_profile,
    auto_reconnect_known_networks
"""

import os
import re
import sys
import json
import time
import shutil
import socket
import tempfile
import subprocess
import threading
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Persistent config location
# ---------------------------------------------------------------------------
# A PyInstaller onefile build unpacks to a temp dir that is deleted on exit, so
# anything written next to __file__ is lost every single launch. That is why
# "auto-connect on launch" never remembered the last SSID in the shipped .exe.


def _config_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or ""
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".pcdeck")
    path = os.path.join(base, "PCDeck")
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        return os.path.dirname(os.path.abspath(__file__))


CONFIG_DIR = _config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "wifi_config.json")
LEGACY_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifi_config.json")

_CONFIG_LOCK = threading.Lock()

DEFAULT_CONFIG: Dict[str, Any] = {
    "auto_reconnect_on_launch": False,
    "auto_heal": False,            # Passive mode: never drop active connection
    "allow_adapter_reset": False,  # Never reset adapter in background
    "allow_dhcp_renew": False,
    "poll_interval": 10,           # seconds between status queries
    "last_connected_ssid": "",
    "last_good_ip": "",
    "preferred_hotspots": [],      # SSIDs to try first, in order
    "known_good": {},              # ssid -> {"ok": int, "fail": int, "last": epoch}
}


def load_wifi_config() -> Dict[str, Any]:
    """Load persistent Wi-Fi manager configuration (migrating any legacy file)."""
    config = dict(DEFAULT_CONFIG)
    config["preferred_hotspots"] = []
    config["known_good"] = {}

    for candidate in (CONFIG_FILE, LEGACY_CONFIG_FILE):
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                config.update(data)
            break
        except Exception:
            continue

    # Normalise types so a hand-edited file cannot crash the watchdog.
    if not isinstance(config.get("preferred_hotspots"), list):
        config["preferred_hotspots"] = []
    if not isinstance(config.get("known_good"), dict):
        config["known_good"] = {}
    try:
        config["poll_interval"] = max(3, int(config.get("poll_interval", 6)))
    except Exception:
        config["poll_interval"] = 6
    return config


def save_wifi_config(config: Dict[str, Any]) -> None:
    """Atomically persist the Wi-Fi manager configuration."""
    with _CONFIG_LOCK:
        try:
            tmp = CONFIG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2)
            os.replace(tmp, CONFIG_FILE)
        except Exception:
            pass


def update_wifi_config(**changes: Any) -> Dict[str, Any]:
    """Read-modify-write a few keys without clobbering the rest of the file."""
    config = load_wifi_config()
    config.update(changes)
    save_wifi_config(config)
    return config


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------

_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


def _startup_info():
    if sys.platform != "win32":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return info


def _console_codepages() -> List[str]:
    """Codepages to try when decoding console output, best guess first.

    netsh writes in the console OEM codepage, not the ANSI one. Decoding with
    Python's locale default (cp1252 here) turns every non-ASCII SSID into '?',
    which is why phone hotspots with emoji or non-Latin names were unusable:
    the mangled name can never be passed back to `netsh wlan connect`.
    """
    pages = ["utf-8"]
    if sys.platform == "win32":
        try:
            import ctypes

            for fn in ("GetConsoleOutputCP", "GetOEMCP", "GetACP"):
                try:
                    cp = int(getattr(ctypes.windll.kernel32, fn)())
                except Exception:
                    continue
                if cp and f"cp{cp}" not in pages:
                    pages.append(f"cp{cp}")
        except Exception:
            pass
    for fallback in ("cp850", "cp437", "cp1252"):
        if fallback not in pages:
            pages.append(fallback)
    return pages


_CODEPAGES = _console_codepages()


def _decode(raw: bytes) -> str:
    """Decode console bytes, preferring a codepage that round-trips cleanly."""
    if not raw:
        return ""
    for encoding in _CODEPAGES:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode(_CODEPAGES[-1], errors="replace")


def _run(argv: List[str], timeout: int = 8) -> Tuple[int, str]:
    """Run a console tool with no visible window. Returns (returncode, stdout)."""
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            startupinfo=_startup_info(),
            creationflags=_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return proc.returncode, _decode(proc.stdout or b"").strip()
    except subprocess.TimeoutExpired:
        return -1, ""
    except Exception:
        return -1, ""


def run_netsh_cmd(args: List[str], timeout: int = 8) -> str:
    """Backwards-compatible netsh wrapper (returns stdout only)."""
    return _run(["netsh"] + args, timeout=timeout)[1]


def is_admin() -> bool:
    """True when the process can enable/disable network adapters."""
    if sys.platform != "win32":
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Locale-independent netsh parsing
# ---------------------------------------------------------------------------

_KV_RE = re.compile(r"^\s*([^:]{2,40}?)\s*:\s*(.*?)\s*$")
_PERCENT_RE = re.compile(r"^\d{1,3}\s*%$")


def _parse_records(text: str) -> List[Dict[str, str]]:
    """Split `key : value` output into one dict per device.

    A new record starts whenever a key repeats, which works on any Windows
    display language - we never compare against a translated word to find the
    record boundary.
    """
    records: List[Dict[str, str]] = []
    current: Dict[str, str] = {}
    for line in (text or "").splitlines():
        match = _KV_RE.match(line)
        if not match:
            continue
        key, value = match.group(1).strip(), match.group(2).strip()
        if not key:
            continue
        low = key.lower()
        if low in current:
            records.append(current)
            current = {}
        current[low] = value
    if current:
        records.append(current)
    # The first record is usually the "There is 1 interface on the system:"
    # preamble, which parses into nothing useful; drop anything tiny.
    return [r for r in records if len(r) >= 3]


def _pick(record: Dict[str, str], *names: str) -> str:
    for name in names:
        if name in record and record[name]:
            return record[name]
    return ""


def _ssid_of(record: Dict[str, str]) -> str:
    """Extract the SSID, ignoring the BSSID line that also contains 'ssid'."""
    if "ssid" in record:
        return record["ssid"]
    for key, value in record.items():
        if "ssid" in key and "bssid" not in key:
            return value
    return ""


def _signal_of(record: Dict[str, str]) -> str:
    value = _pick(record, "signal")
    if value:
        return value
    for key, val in record.items():
        if _PERCENT_RE.match(val or "") and "utilization" not in key:
            return val
    return "0%"


def signal_percent(signal: str) -> int:
    try:
        return int(str(signal).replace("%", "").strip())
    except Exception:
        return 0


def _looks_connected(record: Dict[str, str]) -> bool:
    """Decide link state without matching a translated status word.

    netsh only prints SSID/BSSID/Signal/Channel rows for an associated radio,
    so their presence is the language-neutral tell. The English check stays as
    a fast path and as a guard against odd driver output.
    """
    state = _pick(record, "state").lower()
    if state:
        if any(word in state for word in ("connected", "verbunden", "conectado", "connecte", "connessa", "подключено")):
            if "disconnected" not in state and "not connected" not in state:
                return bool(_ssid_of(record))
        if any(word in state for word in ("disconnected", "not connected", "getrennt", "desconectado")):
            return False
    return bool(_ssid_of(record)) and bool(_pick(record, "bssid"))


# ---------------------------------------------------------------------------
# Adapters & addresses
# ---------------------------------------------------------------------------

HOTSPOT_PREFIXES = ("192.168.43.", "192.168.42.", "172.20.10.", "192.168.137.")


def is_usable_ipv4(ip: str) -> bool:
    """A phone on the same LAN can only reach a real private address."""
    if not ip or ":" in ip:
        return False
    if ip.startswith(("127.", "169.254.", "0.")):
        return False
    return True


def get_wireless_interfaces() -> List[Dict[str, Any]]:
    """Every wireless adapter netsh knows about, with its live association."""
    out = run_netsh_cmd(["wlan", "show", "interfaces"], timeout=8)
    interfaces: List[Dict[str, Any]] = []
    for record in _parse_records(out):
        name = _pick(record, "name")
        if not name:
            continue
        interfaces.append({
            "interface": name,
            "description": _pick(record, "description"),
            "ssid": _ssid_of(record),
            "bssid": _pick(record, "bssid"),
            "signal": _signal_of(record),
            "radio": _pick(record, "radio type", "radio"),
            "channel": _pick(record, "channel"),
            "rx_mbps": _pick(record, "receive rate (mbps)"),
            "tx_mbps": _pick(record, "transmit rate (mbps)"),
            "profile": _pick(record, "profile"),
            "connected": _looks_connected(record),
            "raw_state": _pick(record, "state"),
        })
    return interfaces


def get_admin_states() -> Dict[str, str]:
    """Map interface name -> 'enabled' / 'disabled' from `netsh interface show`."""
    out = run_netsh_cmd(["interface", "show", "interface"], timeout=6)
    states: Dict[str, str] = {}
    for line in (out or "").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        admin = parts[0].lower()
        if admin in ("enabled", "disabled", "aktiviert", "deaktiviert", "habilitado", "deshabilitado"):
            name = " ".join(parts[3:]).strip()
            if name:
                states[name] = "disabled" if admin.startswith(("dis", "deak", "desh")) else "enabled"
    return states


def get_interface_addresses() -> Dict[str, List[str]]:
    """Map interface name -> list of IPv4 addresses currently bound to it."""
    result: Dict[str, List[str]] = {}
    try:
        code, out = _run(["ipconfig"], timeout=3)
        if out:
            current_adapter = None
            for line in out.splitlines():
                line_str = line.strip()
                if "adapter" in line.lower() and ":" in line:
                    parts = line.split("adapter", 1)[1].split(":", 1)[0].strip()
                    current_adapter = parts
                elif ("ipv4" in line.lower() or "adresse ipv4" in line.lower() or "direcci" in line.lower()) and ":" in line:
                    ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                    if ip_match and current_adapter:
                        ip = ip_match.group(1)
                        if not ip.startswith("127."):
                            result.setdefault(current_adapter, []).append(ip)
    except Exception:
        pass

    if not result:
        try:
            ips = socket.gethostbyname_ex(socket.gethostname())[2]
            usable = [ip for ip in ips if not ip.startswith("127.") and not ip.startswith("169.254.")]
            if usable:
                result["Wi-Fi"] = usable
        except Exception:
            pass
    return result


def get_link_health() -> Dict[str, Any]:
    """The single source of truth for "can the phone reach this PC right now?".

    Combines the radio association with the bound IPv4 address so we can tell
    the three failure modes apart:
      * no_radio      - no wireless adapter present or the driver is gone
      * radio_off     - adapter disabled in Windows / hardware switch off
      * disconnected  - adapter up but not associated with any network
      * no_lease      - associated but stuck on APIPA (DHCP failed)
      * ok            - associated with a routable private address
    """
    interfaces = get_wireless_interfaces()
    addresses = get_interface_addresses()
    admin_states = get_admin_states()

    if not interfaces:
        wired_ip = ""
        for name, ips in addresses.items():
            for ip in ips:
                if is_usable_ipv4(ip):
                    wired_ip = ip
                    break
            if wired_ip:
                break
        return {
            "status": "ok" if wired_ip else "no_radio",
            "wireless": False,
            "ip": wired_ip,
            "ssid": "",
            "signal": "0%",
            "interface": "Ethernet" if wired_ip else "",
            "interfaces": [],
            "is_hotspot": False,
        }

    best: Optional[Dict[str, Any]] = None
    for iface in interfaces:
        ips = addresses.get(iface["interface"], [])
        if not ips:
            # Fallback: search partial or case-insensitive match
            for k, v in addresses.items():
                if k.lower() in iface["interface"].lower() or iface["interface"].lower() in k.lower() or "wi-fi" in k.lower() or "wireless" in k.lower():
                    ips = v
                    break
        if not ips and iface.get("connected"):
            # Fallback: any usable IP on the system
            ips = [ip for addrs in addresses.values() for ip in addrs if is_usable_ipv4(ip)]

        iface["ips"] = ips
        iface["ip"] = next((ip for ip in ips if is_usable_ipv4(ip)), "")
        iface["apipa"] = any(ip.startswith("169.254.") for ip in ips)
        iface["admin_state"] = admin_states.get(iface["interface"], "enabled")
        # Rank: routable IP > associated > enabled, tie-break on signal.
        iface["_score"] = (
            (400 if iface["ip"] else 0)
            + (200 if iface["connected"] else 0)
            + (100 if iface["admin_state"] == "enabled" else 0)
            + signal_percent(iface["signal"])
        )
        if best is None or iface["_score"] > best["_score"]:
            best = iface

    assert best is not None
    if not best["ip"] and best.get("connected"):
        for name, ips in addresses.items():
            for ip in ips:
                if is_usable_ipv4(ip):
                    best["ip"] = ip
                    break
            if best["ip"]:
                break

    if best["ip"] or (best.get("connected") and best.get("ssid")):
        status = "ok"
    elif best["admin_state"] == "disabled":
        status = "radio_off"
    elif best["connected"]:
        status = "no_lease"
    else:
        status = "disconnected"

    return {
        "status": status,
        "wireless": True,
        "ip": best["ip"],
        "ssid": best["ssid"],
        "signal": best["signal"],
        "signal_pct": signal_percent(best["signal"]),
        "interface": best["interface"],
        "description": best.get("description", ""),
        "profile": best.get("profile", ""),
        "admin_state": best.get("admin_state", "enabled"),
        "interfaces": interfaces,
        "is_hotspot": best["ip"].startswith(HOTSPOT_PREFIXES) if best["ip"] else False,
        "weak": bool(best["ip"]) and signal_percent(best["signal"]) < 30,
    }


def get_current_wifi_status() -> Dict[str, Any]:
    """Backwards-compatible status dict used by the GUI badge.

    Unlike the old version, "connected" here means *usable*: associated AND
    holding a routable IPv4. A radio sitting on an APIPA address is reported as
    disconnected because the phone genuinely cannot reach it.
    """
    health = get_link_health()
    connected = health["status"] == "ok"
    return {
        "state": "connected" if connected else ("unavailable" if health["status"] == "no_radio" else "disconnected"),
        "ssid": health.get("ssid", ""),
        "signal": health.get("signal", "0%") if connected else "0%",
        "interface": health.get("interface", "Wi-Fi") or "Wi-Fi",
        "profile": health.get("profile", ""),
        "ip": health.get("ip", ""),
        "raw_state": health["status"],
        "health": health,
    }


def _profile_names_from_xml() -> List[str]:
    """Recover exact profile names by exporting profiles as XML.

    `netsh wlan show profiles` prints names through the console codepage, which
    replaces every character it cannot represent with a literal '?'. Those names
    are unusable for connecting. The XML export keeps the real Unicode name, so
    we treat it as the authoritative source and only fall back to text parsing.

    Exported without key=clear on purpose: we need names, not saved passwords,
    and writing cleartext PSKs to disk would be a needless risk.
    """
    if sys.platform != "win32":
        return []
    folder = tempfile.mkdtemp(prefix="pcdeck-wlan-")
    try:
        code, _ = _run(["netsh", "wlan", "export", "profile", f"folder={folder}"], timeout=20)
        names: List[str] = []
        if code != 0 and not os.listdir(folder):
            return []
        for entry in sorted(os.listdir(folder)):
            if not entry.lower().endswith(".xml"):
                continue
            path = os.path.join(folder, entry)
            try:
                root = ET.parse(path).getroot()
            except Exception:
                continue
            # Namespaced element: match on the local tag name.
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] == "name" and (element.text or "").strip():
                    name = element.text.strip()
                    if name not in names:
                        names.append(name)
                    break
        return names
    except Exception:
        return []
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _saved_profiles_from_text() -> List[str]:
    """Profile names scraped from netsh output (locale-independent parsing)."""
    out = run_netsh_cmd(["wlan", "show", "profiles"], timeout=8)
    if not out:
        return []
    profiles: List[str] = []
    for line in out.splitlines():
        # Matches "All User Profile : Name" and every localized variant, while
        # skipping the "Profiles on interface X:" heading which has no colon
        # value or ends with a colon.
        match = _KV_RE.match(line)
        if not match:
            continue
        key, value = match.group(1).strip().lower(), match.group(2).strip()
        if not value or "profile" not in key:
            continue
        if value.endswith(":") or "interface" in key:
            continue
        if value not in profiles:
            profiles.append(value)
    if profiles:
        return profiles

    # Fallback for display languages whose label does not contain "profile"
    # (e.g. Spanish "Perfil de todos los usuarios"): every indented key:value
    # row in this command's output is a profile name.
    for line in out.splitlines():
        if not line.startswith(("    ", "\t")):
            continue
        match = _KV_RE.match(line)
        if not match:
            continue
        value = match.group(2).strip()
        if value and value not in profiles and not value.startswith("<"):
            profiles.append(value)
    return profiles


_PROFILE_CACHE: Dict[str, Any] = {"names": [], "at": 0.0}
_PROFILE_TTL = 30.0


def get_saved_profiles(refresh: bool = False) -> List[str]:
    """All Wi-Fi profiles saved on this machine, with exact Unicode names.

    Cached briefly: the XML export spawns netsh and touches disk, and the scan
    path asks for this list on every poll.
    """
    now = time.time()
    if not refresh and _PROFILE_CACHE["names"] and now - _PROFILE_CACHE["at"] < _PROFILE_TTL:
        return list(_PROFILE_CACHE["names"])

    names = _profile_names_from_xml()
    text_names = _saved_profiles_from_text()

    if names:
        # Union, preferring XML spelling but keeping anything export missed
        # (profiles on an interface that is currently down, for instance).
        lowered = {n.lower() for n in names}
        placeholder = {n.lower().replace("?", "") for n in names}
        for candidate in text_names:
            key = candidate.lower()
            if key in lowered:
                continue
            # Skip mangled duplicates of a name we already have from XML.
            if "?" in candidate and key.replace("?", "") in placeholder:
                continue
            names.append(candidate)
    else:
        names = text_names

    _PROFILE_CACHE["names"] = list(names)
    _PROFILE_CACHE["at"] = now
    return list(names)


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

_SSID_LINE_RE = re.compile(r"(?:^|\n)\s*[^\r\n:]*?SSID\s*(\d+)\s*:\s*([^\r\n]*)", re.I)


def _scan_once(timeout: int = 10) -> List[Dict[str, Any]]:
    out = run_netsh_cmd(["wlan", "show", "networks", "mode=bssid"], timeout=timeout)
    if not out or "SSID" not in out.upper():
        out = run_netsh_cmd(["wlan", "show", "networks"], timeout=timeout)
    if not out:
        return []

    found: List[Dict[str, Any]] = []
    matches = list(_SSID_LINE_RE.finditer(out))
    for index, match in enumerate(matches):
        ssid = match.group(2).strip()
        if not ssid:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(out)
        block = out[start:end]

        signals = [signal_percent(s) for s in re.findall(r"(\d{1,3})\s*%", block)]
        auth_match = re.search(r"^\s*[^\r\n:]*?(?:Authentication|Authentifizierung|Autenticaci)[^\r\n:]*:\s*([^\r\n]+)", block, re.I | re.M)
        band = "5 GHz" if re.search(r"Channel\s*:\s*(3[6-9]|[4-9]\d|1[0-7]\d)\b", block, re.I) else "2.4 GHz"

        found.append({
            "ssid": ssid,
            "signal": f"{max(signals)}%" if signals else "0%",
            "signal_pct": max(signals) if signals else 0,
            "auth": auth_match.group(1).strip() if auth_match else "",
            "band": band,
            "bssid_count": len(re.findall(r"BSSID\s*\d+", block, re.I)) or 1,
        })
    return found


def scan_visible_networks(retries: int = 1, settle: float = 0.5) -> List[Dict[str, Any]]:
    """Scan nearby networks safely with single-pass to prevent radio drops."""
    merged: Dict[str, Dict[str, Any]] = {}
    for attempt in range(max(1, retries)):
        for net in _scan_once():
            key = net["ssid"].lower()
            existing = merged.get(key)
            if existing is None or net["signal_pct"] > existing["signal_pct"]:
                merged[key] = net
        if len(merged) >= 2 and attempt >= 1:
            break
        if attempt + 1 < retries:
            time.sleep(settle)

    # `show networks` reports the *associated* SSID with no signal reading on
    # many drivers (this dongle included), so the network we are actually using
    # would rank last. `show interfaces` has the true live RSSI - overlay it.
    live: Dict[str, Dict[str, Any]] = {}
    for iface in get_wireless_interfaces():
        if iface.get("connected") and iface.get("ssid"):
            live[iface["ssid"].lower()] = iface
    for key, iface in live.items():
        pct = signal_percent(iface.get("signal", "0%"))
        net = merged.get(key)
        if net is None:
            merged[key] = {
                "ssid": iface["ssid"],
                "signal": iface.get("signal", "0%"),
                "signal_pct": pct,
                "auth": "",
                "band": "",
                "bssid_count": 1,
            }
        elif pct > net.get("signal_pct", 0):
            net["signal"] = iface.get("signal", net["signal"])
            net["signal_pct"] = pct

    saved = get_saved_profiles()
    saved_lower = {s.lower(): s for s in saved}

    networks: List[Dict[str, Any]] = []
    for key, net in merged.items():
        net["is_saved"] = key in saved_lower
        net["is_connected"] = key in live
        networks.append(net)

    # Saved-but-not-currently-visible profiles still belong in the list: a phone
    # hotspot that is switched off right now is exactly what the user wants to
    # pick before switching it on.
    for key, original in saved_lower.items():
        if key not in merged:
            networks.append({
                "ssid": original,
                "signal": "Saved",
                "signal_pct": -1,
                "auth": "Profile",
                "band": "",
                "bssid_count": 0,
                "is_saved": True,
                "is_connected": False,
            })

    # Connected first, then saved, then by signal - the order a human expects.
    networks.sort(
        key=lambda n: (
            2000 if n.get("is_connected") else 0,
            1000 if n["is_saved"] else 0,
            n["signal_pct"],
        ),
        reverse=True,
    )
    return networks


# ---------------------------------------------------------------------------
# Connecting & healing
# ---------------------------------------------------------------------------


def wait_for_usable_link(timeout: float = 15.0, interval: float = 1.0) -> Dict[str, Any]:
    """Poll until the link is genuinely usable (associated + routable IPv4)."""
    deadline = time.time() + timeout
    health = get_link_health()
    while time.time() < deadline:
        if health["status"] == "ok":
            return health
        time.sleep(interval)
        health = get_link_health()
    return health


def connect_to_profile(ssid: str, interface: str = "", wait: float = 14.0) -> Tuple[bool, str]:
    """Connect to a saved profile and verify it by observing the link, not stdout.

    `netsh wlan connect` prints a localized success string and returns 0 even
    when association later fails, so the old "does stdout contain 'successfully'"
    check both false-negatived on translated Windows and false-positived on a
    dropped handshake. We fire the command and then watch the actual link.
    """
    ssid = (ssid or "").strip()
    if not ssid:
        return False, "SSID cannot be empty"

    argv = ["wlan", "connect", f"name={ssid}", f"ssid={ssid}"]
    if interface:
        argv.append(f"interface={interface}")
    run_netsh_cmd(argv, timeout=12)

    health = wait_for_usable_link(timeout=wait)
    ok = health["status"] == "ok"
    _record_attempt(ssid, ok, health.get("ip", ""))
    if ok:
        return True, f"Connected to {health.get('ssid') or ssid} ({health.get('signal', '')})"
    if health["status"] == "no_lease":
        return False, f"Associated with {ssid} but DHCP gave no address"
    return False, f"Could not connect to {ssid}"


def _record_attempt(ssid: str, ok: bool, ip: str = "") -> None:
    """Track per-SSID reliability so the picker learns which link actually works."""
    if not ssid:
        return
    config = load_wifi_config()
    stats = config.get("known_good", {})
    entry = stats.get(ssid) or {"ok": 0, "fail": 0, "last": 0}
    entry["ok" if ok else "fail"] = int(entry.get("ok" if ok else "fail", 0)) + 1
    entry["last"] = int(time.time())
    stats[ssid] = entry
    config["known_good"] = stats
    if ok:
        config["last_connected_ssid"] = ssid
        if ip:
            config["last_good_ip"] = ip
    save_wifi_config(config)


def renew_dhcp(interface: str = "") -> bool:
    """Ask Windows for a fresh lease - fixes the 169.254.x.x dongle lockup."""
    if interface:
        code, _ = _run(["ipconfig", "/renew", interface], timeout=25)
    else:
        code, _ = _run(["ipconfig", "/renew"], timeout=30)
    if code != 0:
        _run(["ipconfig", "/release", interface] if interface else ["ipconfig", "/release"], timeout=20)
        code, _ = _run(["ipconfig", "/renew", interface] if interface else ["ipconfig", "/renew"], timeout=30)
    return code == 0


def enable_adapter(interface: str) -> bool:
    """Re-enable an adapter that was switched off in Windows. Requires admin."""
    if not interface:
        return False
    code, _ = _run(["netsh", "interface", "set", "interface", f"name={interface}", "admin=enable"], timeout=20)
    return code == 0


def reset_adapter(interface: str) -> bool:
    """Power-cycle a wedged radio (disable, pause, enable). Requires admin.

    This is the escape hatch for budget USB dongles whose driver stops
    responding to scan/connect requests until the interface is bounced.
    """
    if not interface or not is_admin():
        return False
    _run(["netsh", "interface", "set", "interface", f"name={interface}", "admin=disable"], timeout=25)
    time.sleep(2.5)
    code, _ = _run(["netsh", "interface", "set", "interface", f"name={interface}", "admin=enable"], timeout=25)
    time.sleep(3.0)
    return code == 0


def pick_best_target(networks: Optional[List[Dict[str, Any]]] = None) -> str:
    """Choose which SSID to join, ranked by how well it has worked before.

    Priority: explicit preferred hotspots -> last known good -> visible saved
    networks weighted by past success and signal -> any saved profile at all.
    """
    config = load_wifi_config()
    stats = config.get("known_good", {})
    if networks is None:
        networks = scan_visible_networks()

    visible_saved = [n for n in networks if n.get("is_saved") and n.get("signal_pct", -1) >= 0]
    by_ssid = {n["ssid"].lower(): n for n in visible_saved}

    for preferred in config.get("preferred_hotspots", []):
        if preferred and preferred.lower() in by_ssid:
            return by_ssid[preferred.lower()]["ssid"]

    last = (config.get("last_connected_ssid") or "").lower()
    if last and last in by_ssid:
        return by_ssid[last]["ssid"]

    def rank(net: Dict[str, Any]) -> float:
        entry = stats.get(net["ssid"]) or {}
        ok = int(entry.get("ok", 0))
        fail = int(entry.get("fail", 0))
        # Reliability in [-1, 1], scaled so a proven network beats a slightly
        # stronger but historically flaky one.
        reliability = (ok - fail) / float(max(1, ok + fail))
        return net.get("signal_pct", 0) + reliability * 35.0

    if visible_saved:
        return max(visible_saved, key=rank)["ssid"]

    if last:
        return config.get("last_connected_ssid", "")

    saved = get_saved_profiles()
    return saved[0] if saved else ""


# ---------------------------------------------------------------------------
# Auto-reconnect: escalating repair ladder
# ---------------------------------------------------------------------------


def auto_reconnect(force: bool = False) -> Dict[str, Any]:
    """Get the machine back onto a usable Wi-Fi link, escalating as needed.

    Each rung is cheap before it is expensive, and we stop the moment the link
    is genuinely usable. Returns a report describing what was tried.
    """
    steps: List[str] = []
    config = load_wifi_config()
    health = get_link_health()

    if health["status"] == "ok" and not force:
        return {"ok": True, "action": "none", "steps": ["already connected"], "health": health}

    iface = health.get("interface", "")

    # Rung 1: adapter is administratively down.
    if health["status"] == "adapter_disabled":
        steps.append("enabling disabled adapter")
        if enable_adapter(iface):
            time.sleep(3.0)
            health = wait_for_usable_link(timeout=12.0)
            if health["status"] == "ok":
                return {"ok": True, "action": "enable_adapter", "steps": steps, "health": health}

    # Rung 2: associated but no routable address - almost always DHCP.
    if health["status"] == "no_lease" and config.get("allow_dhcp_renew", True):
        steps.append("renewing DHCP lease")
        renew_dhcp(iface)
        health = wait_for_usable_link(timeout=12.0)
        if health["status"] == "ok":
            return {"ok": True, "action": "renew_dhcp", "steps": steps, "health": health}

    # Rung 3: pick the best known network and join it.
    networks = scan_visible_networks()
    target = pick_best_target(networks)
    if target:
        steps.append(f"connecting to {target}")
        ok, message = connect_to_profile(target, iface)
        steps.append(message)
        if ok:
            return {"ok": True, "action": "connect", "ssid": target, "steps": steps, "health": get_link_health()}
    else:
        steps.append("no saved network is in range")

    # Rung 4: the radio itself is wedged - bounce it and retry once.
    if not config.get("allow_adapter_reset", True):
        steps.append("adapter reset disabled in settings - skipped")
    elif is_admin() and iface:
        steps.append("resetting the wireless adapter")
        if reset_adapter(iface):
            networks = scan_visible_networks()
            target = pick_best_target(networks) or target
            if target:
                ok, message = connect_to_profile(target, iface)
                steps.append(message)
                if ok:
                    return {
                        "ok": True,
                        "action": "reset_adapter",
                        "ssid": target,
                        "steps": steps,
                        "health": get_link_health(),
                    }
    elif iface:
        steps.append("adapter reset needs administrator rights - skipped")

    return {"ok": False, "action": "failed", "steps": steps, "health": get_link_health()}


# ---------------------------------------------------------------------------
# Power management (the usual reason a cheap dongle "randomly" drops)
# ---------------------------------------------------------------------------


def _powershell(script: str, timeout: int = 20) -> Tuple[int, str]:
    """Run a short PowerShell snippet with no window and no profile."""
    return _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout=timeout,
    )


def get_power_saving_state(interface: str = "") -> Dict[str, Any]:
    """Report whether Windows is allowed to power down the wireless adapter.

    Returns {"supported": bool, "power_saving_on": Optional[bool], "detail": str}.
    """
    if sys.platform != "win32":
        return {"supported": False, "power_saving_on": None, "detail": "not Windows"}

    name = interface or (get_link_health().get("interface") or "")
    if not name:
        return {"supported": False, "power_saving_on": None, "detail": "no wireless interface"}

    code, out = _powershell(
        "(Get-NetAdapterPowerManagement -Name '%s' -ErrorAction Stop)."
        "AllowComputerToTurnOffDevice" % name.replace("'", "''")
    )
    if code != 0 or not out.strip():
        return {"supported": False, "power_saving_on": None, "detail": "adapter does not expose power settings"}

    value = out.strip().splitlines()[-1].strip().lower()
    if value.startswith("enabled"):
        return {"supported": True, "power_saving_on": True, "detail": "Windows may power down this adapter"}
    if value.startswith("disabled"):
        return {"supported": True, "power_saving_on": False, "detail": "adapter stays powered"}
    if value.startswith("unsupported"):
        return {"supported": False, "power_saving_on": None, "detail": "adapter does not support power management"}
    return {"supported": False, "power_saving_on": None, "detail": value}


def disable_power_saving(interface: str = "") -> Tuple[bool, str]:
    """Stop Windows from powering down the radio to save energy.

    Budget USB dongles (Realtek RTL81xx in particular) are frequently put to
    sleep by USB selective suspend and then come back without re-associating.
    The symptom looks exactly like a flaky router: the link drops every few
    minutes for no visible reason. Turning this off is the single most effective
    stability fix on that hardware, so we also raise the wireless power policy
    to Maximum Performance on both AC and battery.

    Requires administrator rights.
    """
    if sys.platform != "win32":
        return False, "Only supported on Windows"
    if not is_admin():
        return False, "Administrator rights are required to change adapter power settings"

    name = interface or (get_link_health().get("interface") or "")
    if not name:
        return False, "No wireless interface found"

    safe = name.replace("'", "''")
    code, out = _powershell(
        "Set-NetAdapterPowerManagement -Name '%s' -AllowComputerToTurnOffDevice Disabled "
        "-ErrorAction Stop; 'done'" % safe
    )
    adapter_ok = code == 0

    # Wireless Adapter Settings -> Power Saving Mode -> Maximum Performance.
    # 0 = Maximum Performance for both the AC and DC value indexes.
    sub = "19cbb8fa-5279-450e-9fac-8a3d5fedd0c1"
    setting = "12bbebe6-58d6-4636-95bb-3217ef867c1a"
    _run(["powercfg", "/setacvalueindex", "SCHEME_CURRENT", sub, setting, "0"], timeout=12)
    _run(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", sub, setting, "0"], timeout=12)
    _run(["powercfg", "/setactive", "SCHEME_CURRENT"], timeout=12)

    if adapter_ok:
        update_wifi_config(power_saving_disabled=True)
        return True, f"Power saving disabled on {name}"
    detail = (out or "").strip().splitlines()[-1] if out.strip() else "adapter refused the change"
    return False, f"Could not change adapter power settings: {detail}"


def disable_usb_selective_suspend() -> bool:
    """Stop Windows suspending USB ports - the killer for USB Wi-Fi dongles.

    Many cheap adapters (including the RTL81xx family) do not implement the NDIS
    power-management OIDs at all, so Get/Set-NetAdapterPowerManagement fails with
    "device is not functioning". On those, USB selective suspend is the actual
    mechanism putting the radio to sleep, and it is set per power scheme rather
    than per adapter - so it is still fixable even when the adapter itself
    exposes nothing.
    """
    if sys.platform != "win32" or not is_admin():
        return False
    sub = "2a737441-1930-4402-8d77-b2bebba308a3"   # USB settings
    setting = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"  # USB selective suspend
    ok = True
    for verb in ("/setacvalueindex", "/setdcvalueindex"):
        code, _ = _run(["powercfg", verb, "SCHEME_CURRENT", sub, setting, "0"], timeout=12)
        ok = ok and code == 0
    _run(["powercfg", "/setactive", "SCHEME_CURRENT"], timeout=12)
    return ok


def ensure_stable_radio(interface: str = "") -> Dict[str, Any]:
    """Apply the one-time stability tweaks a budget adapter needs.

    Safe to call on every launch: it checks first and only writes when Windows
    actually has a power-saving feature switched on.
    """
    actions: List[str] = []
    state = get_power_saving_state(interface)

    if state.get("supported") and state.get("power_saving_on") is True:
        ok, message = disable_power_saving(interface)
        actions.append(message if ok else f"adapter power saving unchanged ({message})")
    elif not state.get("supported"):
        # Adapter exposes no power settings - fall back to the USB-level fix,
        # which is what actually matters for a USB dongle.
        if is_admin() and disable_usb_selective_suspend():
            actions.append("USB selective suspend disabled")
            update_wifi_config(power_saving_disabled=True)

    return {
        "changed": bool(actions),
        "actions": actions,
        "state": get_power_saving_state(interface),
    }


# ---------------------------------------------------------------------------
# Background watchdog
# ---------------------------------------------------------------------------


class WiFiWatchdog:
    """Polls link health on a background thread and repairs drops on its own.

    Backs off after consecutive failures so a machine with no network in range
    does not spend its life running netsh in a tight loop.
    """

    def __init__(self, on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self._on_event = on_event
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last: Dict[str, Any] = {"status": "unknown", "checked_at": 0}
        self._failures = 0
        self._repairs = 0

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="wifi-watchdog", daemon=True)
            self._thread.start()
            return True

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            snapshot = dict(self._last)
        snapshot["watchdog_running"] = self.running
        snapshot["consecutive_failures"] = self._failures
        snapshot["repairs"] = self._repairs
        return snapshot

    # -- internals ---------------------------------------------------------

    def _emit(self, event: Dict[str, Any]) -> None:
        if not self._on_event:
            return
        try:
            self._on_event(event)
        except Exception:
            # A misbehaving UI callback must never kill the watchdog.
            pass

    def _loop(self) -> None:
        # One-time hardware stabilisation. Only does anything when running
        # elevated and when Windows actually has a power-saving knob switched on.
        try:
            report = ensure_stable_radio()
            if report.get("changed"):
                self._emit({"type": "stabilised", "report": report})
        except Exception:
            pass

        while not self._stop.is_set():
            config = load_wifi_config()
            interval = max(5, int(config.get("poll_interval", 6)))

            if not config.get("auto_heal", True):
                self._stop.wait(interval)
                continue

            health = get_link_health()
            with self._lock:
                previous = self._last.get("status")
                self._last = health
            if health["status"] != previous:
                self._emit({"type": "link", "health": health})

            if health["status"] == "ok":
                self._failures = 0
                self._stop.wait(interval)
                continue

            self._emit({"type": "repairing", "health": health})
            report = auto_reconnect()
            if report["ok"]:
                self._failures = 0
                self._repairs += 1
                with self._lock:
                    self._last = report["health"]
                self._emit({"type": "repaired", "report": report})
                self._stop.wait(interval)
                continue

            self._failures += 1
            self._emit({"type": "repair_failed", "report": report, "attempts": self._failures})
            # Exponential backoff capped at ~5 minutes.
            backoff = min(interval * (2 ** min(self._failures, 4)), 300)
            self._stop.wait(backoff)


# ---------------------------------------------------------------------------
# Module-level singleton so the server and the tray UI share one watchdog
# ---------------------------------------------------------------------------

_watchdog: Optional[WiFiWatchdog] = None
_watchdog_lock = threading.Lock()


def start_watchdog(on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> WiFiWatchdog:
    """Start (or return) the shared watchdog. Safe to call more than once."""
    global _watchdog
    with _watchdog_lock:
        if _watchdog is None:
            _watchdog = WiFiWatchdog(on_event=on_event)
        elif on_event is not None:
            _watchdog._on_event = on_event
        _watchdog.start()
        return _watchdog


def stop_watchdog() -> None:
    global _watchdog
    with _watchdog_lock:
        if _watchdog is not None:
            _watchdog.stop()


def get_watchdog() -> Optional[WiFiWatchdog]:
    return _watchdog


def watchdog_status() -> Dict[str, Any]:
    """Health snapshot that is safe to call whether or not the watchdog runs."""
    if _watchdog is not None:
        return _watchdog.status()
    health = get_link_health()
    health["watchdog_running"] = False
    return health


# ---------------------------------------------------------------------------
# Backwards-compatible aliases (gui.py imports these names)
# ---------------------------------------------------------------------------


def auto_reconnect_known_networks() -> Tuple[bool, str]:
    """Legacy signature: returns (ok, human-readable message)."""
    report = auto_reconnect()
    health = report.get("health", {})
    if report["ok"]:
        ssid = report.get("ssid") or health.get("ssid") or "Wi-Fi"
        if report["action"] == "none":
            return True, f"Already connected to {ssid}"
        return True, f"Connected to {ssid} ({health.get('ip', '')})"
    detail = report["steps"][-1] if report.get("steps") else "no saved network in range"
    return False, f"Auto-reconnect failed: {detail}"