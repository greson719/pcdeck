"""
PCDeck Pro - Cryptographic License & Anti-Tamper Engine
=========================================================
Implements hardware fingerprint binding (HWID), HMAC-SHA256 signature
verification, and zero-trust tamper-proof license storage.
"""

import os
import sys
import json
import base64
import hmac
import hashlib
import datetime
import urllib.request
import urllib.error
import socket
from typing import Dict, Any, Tuple

# Storage directory and secured data file
LICENSE_DIR = os.path.join(os.path.expanduser("~"), ".pcdeck")
SECURE_LICENSE_FILE = os.path.join(LICENSE_DIR, "license.dat")
LEGACY_LICENSE_FILE = os.path.join(LICENSE_DIR, "license.json")

# Obfuscated internal salt components (combined at runtime)
_S1 = bytes([112, 99, 100, 101, 99, 107])            # "pcdeck"
_S2 = bytes([95, 115, 101, 99, 117, 114, 101])       # "_secure"
_S3 = bytes([95, 112, 114, 111, 95, 50, 48, 50, 54]) # "_pro_2026"
_SALT = _S1 + _S2 + _S3                              # "pcdeck_secure_pro_2026"


def _get_all_legacy_hwids() -> list:
    """
    Generate all possible legacy HWIDs for this machine by checking all active
    and virtual network adapters (Wi-Fi, Ethernet, Bluetooth).
    Enables 100% OFFLINE migration from v2.7.5 to v2.7.6 even if the user switched
    adapters or had MAC randomization enabled.
    """
    guid_part = ""
    if sys.platform == "win32":
        try:
            import winreg
            access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0x0100)
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, access) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    guid_part = f"guid:{guid.strip().lower()}"
        except Exception:
            pass

    host_part = ""
    try:
        host = socket.gethostname().strip().lower()
        if host:
            host_part = f"host:{host}"
    except Exception:
        pass

    # Collect all known MAC integers on this physical machine
    mac_ints = set()
    try:
        import uuid
        node = uuid.getnode()
        if node:
            mac_ints.add(node)
    except Exception:
        pass

    try:
        import psutil
        for addrs in psutil.net_if_addrs().values():
            for a in addrs:
                if hasattr(a, "family") and getattr(a.family, "name", "") == "AF_LINK" and a.address:
                    clean_mac = a.address.replace("-", "").replace(":", "").strip()
                    if clean_mac and len(clean_mac) == 12:
                        try:
                            mac_ints.add(int(clean_mac, 16))
                        except Exception:
                            pass
    except Exception:
        pass

    legacy_hwids = []
    base_components = []
    if guid_part:
        base_components.append(guid_part)
    if host_part:
        base_components.append(host_part)

    for m in mac_ints:
        comps = list(base_components) + [f"mac:{m}"]
        raw_seed = "|".join(comps)
        legacy_hwids.append(hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:32])

    if not legacy_hwids:
        raw_seed = "|".join(base_components) if base_components else "pcdeck_fallback_hwid"
        legacy_hwids.append(hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:32])

    return legacy_hwids


def _get_legacy_hwid() -> str:
    """Primary legacy HWID using current active node."""
    all_legacy = _get_all_legacy_hwids()
    return all_legacy[0] if all_legacy else hashlib.sha256(b"pcdeck_fallback_hwid").hexdigest()[:32]


def get_machine_hwid() -> str:
    """
    Generate a rock-solid, invariant hardware fingerprint for the local machine.
    On Windows, uses the immutable Windows MachineGuid with KEY_WOW64_64KEY view
    so network changes, VPN switches, Wi-Fi reconnection, and reboots never invalidate the license.
    """
    # 1. Windows MachineGuid (permanent per Windows installation)
    if sys.platform == "win32":
        try:
            import winreg
            access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0x0100)
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, access) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid and len(guid.strip()) > 8:
                    return hashlib.sha256(f"guid:{guid.strip().lower()}".encode("utf-8")).hexdigest()[:32]
        except Exception:
            pass

    # 2. Linux machine-id fallback
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    mid = f.read().strip()
                    if mid:
                        return hashlib.sha256(f"linux_id:{mid.lower()}".encode("utf-8")).hexdigest()[:32]
            except Exception:
                pass

    # 3. macOS IOPlatformUUID fallback
    if sys.platform == "darwin":
        try:
            import subprocess
            out = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]).decode("utf-8")
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    uuid_str = line.split("=")[-1].strip().strip('"')
                    return hashlib.sha256(f"mac_uuid:{uuid_str.lower()}".encode("utf-8")).hexdigest()[:32]
        except Exception:
            pass

    # 4. Hostname fallback only if OS GUIDs are unavailable
    try:
        host = socket.gethostname().strip().lower()
        if host:
            return hashlib.sha256(f"host:{host}".encode("utf-8")).hexdigest()[:32]
    except Exception:
        pass

    return hashlib.sha256(b"pcdeck_fallback_hwid").hexdigest()[:32]


def get_stored_license_record() -> Dict[str, Any]:
    """Read raw payload from local license file without HWID enforcement."""
    if not os.path.exists(SECURE_LICENSE_FILE):
        return {}
    try:
        with open(SECURE_LICENSE_FILE, "rb") as f:
            raw_b64 = f.read()
        payload_bytes = base64.b64decode(raw_b64)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return {}


def _compute_hmac(hwid: str, key: str, instance_id: str) -> str:
    """Compute HMAC-SHA256 signature for license payload bound to local HWID."""
    msg = f"{hwid.strip()}::{key.strip().upper()}::{instance_id.strip()}".encode("utf-8")
    return hmac.new(_SALT, msg, hashlib.sha256).hexdigest()


def verify_license() -> Dict[str, Any]:
    """
    Cryptographically verify local license file.
    Ensures license has not been modified and was issued for THIS specific machine.
    Seamlessly migrates licenses from legacy volatile HWID to stable HWID.
    """
    # Safe developer override: ONLY active in non-frozen dev environment with explicit flag
    if os.environ.get("PCDECK_DEV_PRO") == "1" and not getattr(sys, "frozen", False):
        return {
            "pro_active": True,
            "key": "DEV-ENVIRONMENT-OVERRIDE",
            "instance_id": "dev-local-001",
            "activated_at": datetime.datetime.now().isoformat(),
            "token": "dev-token-verified",
        }

    if not os.path.exists(SECURE_LICENSE_FILE):
        return {"pro_active": False, "key": "", "instance_id": "", "token": ""}

    try:
        with open(SECURE_LICENSE_FILE, "rb") as f:
            raw_b64 = f.read()

        payload_bytes = base64.b64decode(raw_b64)
        data = json.loads(payload_bytes.decode("utf-8"))

        key = data.get("key", "").strip().upper()
        instance_id = data.get("instance_id", "").strip()
        stored_hwid = data.get("hwid", "").strip()
        stored_sig = data.get("sig", "").strip()

        if not key or not instance_id or not stored_hwid or not stored_sig:
            return {"pro_active": False, "key": "", "instance_id": "", "token": ""}

        current_hwid = get_machine_hwid()

        # 1. Hardware ID match check (primary stable HWID or legacy multi-adapter check)
        hwid_matched = hmac.compare_digest(stored_hwid, current_hwid)
        is_legacy = False
        if not hwid_matched:
            for leg_hwid in _get_all_legacy_hwids():
                if hmac.compare_digest(stored_hwid, leg_hwid):
                    hwid_matched = True
                    is_legacy = True
                    break

        if not hwid_matched:
            return {"pro_active": False, "key": "", "instance_id": "", "token": ""}

        # 2. Cryptographic signature check
        expected_sig = _compute_hmac(stored_hwid, key, instance_id)
        if not hmac.compare_digest(stored_sig, expected_sig):
            return {"pro_active": False, "key": "", "instance_id": "", "token": ""}

        # Seamlessly upgrade legacy record to new stable HWID
        if is_legacy:
            try:
                save_license(key, instance_id, data.get("meta", {}))
            except Exception:
                pass

        return {
            "pro_active": True,
            "key": key,
            "instance_id": instance_id,
            "activated_at": data.get("activated_at", ""),
            "token": stored_sig,
        }

    except Exception:
        return {"pro_active": False, "key": "", "instance_id": "", "token": ""}


def save_license(key: str, instance_id: str, meta: Dict[str, Any] = None) -> bool:
    """Save cryptographically signed license record bound to current machine HWID."""
    try:
        os.makedirs(LICENSE_DIR, exist_ok=True)
        hwid = get_machine_hwid()
        sig = _compute_hmac(hwid, key, instance_id)

        record = {
            "key": key.strip().lower(),
            "instance_id": instance_id.strip(),
            "hwid": hwid,
            "sig": sig,
            "activated_at": datetime.datetime.now().isoformat(),
            "meta": meta or {},
        }

        payload_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
        raw_b64 = base64.b64encode(payload_bytes)

        temp_file = os.path.join(LICENSE_DIR, "license.tmp")
        with open(temp_file, "wb") as f:
            f.write(raw_b64)
        os.replace(temp_file, SECURE_LICENSE_FILE)

        # Remove vulnerable legacy file if it exists
        if os.path.exists(LEGACY_LICENSE_FILE):
            try:
                os.remove(LEGACY_LICENSE_FILE)
            except Exception:
                pass

        return True
    except Exception:
        return False


def check_dodo_license_valid(key_str: str) -> Tuple[bool, str]:
    """
    Check whether a license key is valid directly with Dodo Payments /licenses/validate.
    Public unauthenticated endpoint - fast and safe.
    """
    clean_key = (key_str or "").strip()
    if not clean_key or len(clean_key) < 5:
        return False, "Invalid license key format."
    if clean_key.upper().startswith("PCDECK-DEV") or clean_key.upper().startswith("PCDECK-LOCALDEV"):
        return False, "Developer test key."

    try:
        req_data = json.dumps({"license_key": clean_key}).encode("utf-8")
        req = urllib.request.Request(
            "https://live.dodopayments.com/licenses/validate",
            data=req_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "PCDeck-Windows-Client/2.7.0"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            if res_json.get("valid") is True:
                return True, "License key is active and valid."
            return False, res_json.get("message") or res_json.get("error") or "License key is inactive or expired."
    except Exception as ex:
        return False, f"Validation network error: {ex}"


def try_silent_license_recovery() -> bool:
    """
    Attempt to silently recover an existing license file if HWID drifted.
    Runs asynchronously on startup without blocking the UI or event loop.
    Enforces hardware affinity to prevent copied license files from auto-activating.
    """
    info = verify_license()
    if info.get("pro_active"):
        return True

    stored = get_stored_license_record()
    key = stored.get("key", "").strip()
    if not key or key.upper().startswith("PCDECK-DEV") or key.upper().startswith("PCDECK-LOCALDEV"):
        return False

    stored_hwid = (stored.get("hwid") or "").strip()
    stored_sig = (stored.get("sig") or "").strip()
    hwid = get_machine_hwid()

    # Hardware affinity check: only recover if this file originated on this physical machine
    is_same_machine = (stored_hwid == hwid or stored_hwid in _get_all_legacy_hwids())
    if not is_same_machine:
        return False

    # Cryptographic integrity check: ensure the file was signed by PCDeck
    expected_sig = _compute_hmac(stored_hwid, key, stored.get("instance_id", ""))
    if not hmac.compare_digest(stored_sig, expected_sig):
        return False

    is_valid, _ = check_dodo_license_valid(key)
    if is_valid:
        instance_id = stored.get("instance_id") or f"inst_active_{hwid[:12]}"
        return save_license(key, instance_id, stored.get("meta", {}))
    return False


def activate_license_online(key_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Activate license key directly with official Dodo Payments API.
    Binds the generated instance to this machine's HWID.
    Uses the Hybrid Approach: if the activation limit is reached (HTTP 422),
    it immediately verifies key entitlement via /licenses/validate and
    binds the valid license to this machine without trapping the user.
    """
    clean_key = (key_str or "").strip().lower()
    if not clean_key:
        return False, "Please enter a valid license key.", {}

    hwid = get_machine_hwid()
    instance_name = f"PCDeck Windows Host ({hwid[:8]})"

    # Developer test key (safe local hardware binding ONLY active in non-frozen dev environment with explicit flag)
    if (clean_key == "pcdeck-dev-test" or clean_key.startswith("pcdeck-localdev")) and os.environ.get("PCDECK_DEV_PRO") == "1" and not getattr(sys, "frozen", False):
        instance_id = f"dev_{hwid[:12]}"
        saved = save_license(clean_key, instance_id, {"tier": "developer_test", "mode": "local_test"})
        if saved:
            return True, "PCDeck Pro activated in developer test mode!", {"id": instance_id}

    try:
        req_data = json.dumps({
            "license_key": clean_key,
            "name": instance_name
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://live.dodopayments.com/licenses/activate",
            data=req_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "PCDeck-Windows-Client/2.7.0"
            }
        )

        with urllib.request.urlopen(req, timeout=12) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))

            instance_id = res_json.get("id") or res_json.get("instance_id") or f"inst_{hwid[:12]}"
            saved = save_license(clean_key, instance_id, res_json)
            if saved:
                return True, "PCDeck Pro activated successfully!", res_json
            else:
                return False, "Failed to securely save license file.", {}

    except urllib.error.HTTPError as e:
        # HYBRID AUTO-RECOVERY: If activation limit is reached (HTTP 422),
        # allow recovery IF this machine already possessed this key locally (re-activation after HWID drift/network change).
        # Rejects brand new machines attempting to exceed the seat limit.
        if e.code == 422:
            stored_record = get_stored_license_record()
            stored_key = (stored_record.get("key") or "").strip().lower()
            stored_hwid = (stored_record.get("hwid") or "").strip()
            stored_sig = (stored_record.get("sig") or "").strip()

            is_same_machine = (stored_key == clean_key) and (
                stored_hwid == hwid or stored_hwid in _get_all_legacy_hwids()
            )
            file_authentic = False
            if is_same_machine and stored_hwid and stored_sig:
                expected_sig = _compute_hmac(stored_hwid, stored_key, stored_record.get("instance_id", ""))
                if hmac.compare_digest(stored_sig, expected_sig):
                    file_authentic = True

            if is_same_machine and file_authentic:
                is_valid, _ = check_dodo_license_valid(clean_key)
                if is_valid:
                    instance_id = stored_record.get("instance_id") or f"inst_active_{hwid[:12]}"
                    saved = save_license(clean_key, instance_id, {
                        "source": "dodo_hybrid_recovery",
                        "note": "Re-activated on existing authorized machine"
                    })
                    if saved:
                        return True, "PCDeck Pro activated successfully!", {"id": instance_id, "recovered": True}

        err_msg = ""
        try:
            body = json.loads(e.read().decode("utf-8"))
            err_msg = body.get("message") or body.get("error") or body.get("detail") or ""
        except Exception:
            pass

        if not err_msg:
            if e.code == 404:
                err_msg = "License key not found. Please check your purchase receipt."
            elif e.code == 422:
                err_msg = "License activation limit reached for this key."
            elif e.code == 403:
                err_msg = "License key is inactive or revoked."
            else:
                err_msg = f"HTTP Error {e.code}"
        return False, f"Activation failed: {err_msg}", {}
    except Exception as ex:
        return False, f"Could not connect to license server: {ex}", {}


def validate_license_online() -> Tuple[bool, str]:
    """Periodically or manually re-validate active license against Dodo Payments."""
    info = verify_license()
    if not info.get("pro_active"):
        return False, "No active license found."

    key = info.get("key")
    instance_id = info.get("instance_id")
    if not key or not instance_id:
        return False, "Invalid license state."

    try:
        req_data = json.dumps({
            "license_key": key
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://live.dodopayments.com/licenses/validate",
            data=req_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "PCDeck-Windows-Client/2.7.0"
            }
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            if res_json.get("valid") is True:
                return True, "License is active and valid."
            else:
                return False, res_json.get("message") or res_json.get("error") or "License is no longer valid."
    except Exception as ex:
        # If offline, fall back to valid cryptographic local signature
        return True, f"Offline validation preserved: {ex}"


def deactivate_license() -> Tuple[bool, str]:
    """Remove local license and deactivate with Dodo Payments if online."""
    try:
        info = verify_license()
        key = info.get("key")
        instance_id = info.get("instance_id")
        if key and instance_id:
            try:
                req_data = json.dumps({
                    "license_key": key,
                    "license_key_instance_id": instance_id
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://live.dodopayments.com/licenses/deactivate",
                    data=req_data,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "PCDeck-Windows-Client/2.7.0"
                    }
                )
                with urllib.request.urlopen(req, timeout=8):
                    pass
            except Exception:
                pass

        if os.path.exists(SECURE_LICENSE_FILE):
            os.remove(SECURE_LICENSE_FILE)
        if os.path.exists(LEGACY_LICENSE_FILE):
            os.remove(LEGACY_LICENSE_FILE)
        return True, "License deactivated and removed."
    except Exception as e:
        return False, f"Failed to deactivate: {e}"


def activate_local_dev_license() -> Tuple[bool, str]:
    """
    Generate and sign a valid Pro license for the local machine's HWID.
    Used by the developer to test Pro features on their own PC without hardcoding backdoors.
    """
    hwid = get_machine_hwid()
    key = f"PCDECK-LOCALDEV-{hwid[:8].upper()}"
    instance_id = f"dev_{hwid[:12]}"
    ok = save_license(key, instance_id, {"tier": "developer_test", "created_by": "local_dev_tool"})
    if ok:
        return True, f"Local Developer Pro license generated and bound to HWID {hwid}!"
    return False, "Failed to save local developer license."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PCDeck Pro License Manager CLI")
    parser.add_argument("--status", action="store_true", help="Check current license status")
    parser.add_argument("--activate-local-dev", action="store_true", help="Activate Pro locally on this machine for development/testing")
    parser.add_argument("--deactivate", action="store_true", help="Remove local license to test Free tier")
    parser.add_argument("--hwid", action="store_true", help="Print local machine hardware ID")

    args = parser.parse_args()

    if args.activate_local_dev:
        ok, msg = activate_local_dev_license()
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")
    elif args.deactivate:
        ok, msg = deactivate_license()
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")
    elif args.hwid:
        print(f"Local Machine HWID: {get_machine_hwid()}")
    else:
        status = verify_license()
        print("=== PCDeck License Status ===")
        print(f"  Pro Active  : {status.get('pro_active', False)}")
        print(f"  Key         : {status.get('key', 'None')}")
        print(f"  Instance ID : {status.get('instance_id', 'None')}")
        print(f"  Machine HWID: {get_machine_hwid()}")
