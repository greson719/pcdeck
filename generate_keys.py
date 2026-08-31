"""
PCDeck Pro - Single Standard 4-Block Cryptographic License Key Generator
Standard Format: PCDK-XXXX-YYYY-ZZZZ (4 Blocks, 16 characters)

Usage:
    python generate_keys.py          # Generate 5 fresh Pro license keys
    python generate_keys.py 20       # Generate 20 fresh Pro license keys
"""

import sys
import os
import hashlib
import secrets

# Master Secret Salt for PCDeck Pro
SECRET_SALT = "PCDECK_PRO_MASTER_SEC_2026_KEYGEN"

def compute_checksum(block_a: str, block_b: str) -> str:
    """Compute 4-character deterministic hex checksum for the 4-block key."""
    raw = f"{block_a}-{block_b}-{SECRET_SALT}".encode("utf-8")
    h = hashlib.sha256(raw).hexdigest().upper()
    return h[0:4]

def generate_key() -> str:
    """Generate a clean 4-block PCDeck Pro License Key (PCDK-XXXX-YYYY-ZZZZ)."""
    block_a = secrets.token_hex(2).upper()
    block_b = secrets.token_hex(2).upper()
    checksum = compute_checksum(block_a, block_b)
    return f"PCDK-{block_a}-{block_b}-{checksum}"

def verify_key(key: str) -> bool:
    """Verify if a 4-block license key is valid."""
    cleaned = key.strip().upper().replace(" ", "")
    parts = cleaned.split("-")
    if len(parts) == 4 and parts[0] == "PCDK":
        block_a, block_b, check = parts[1], parts[2], parts[3]
        expected = compute_checksum(block_a, block_b)
        return check == expected
    
    # Also support unbroken 16-char string PCDKXXXXXXXXXXXX
    raw_clean = "".join(c for c in cleaned if c.isalnum())
    if len(raw_clean) == 16 and raw_clean.startswith("PCDK"):
        block_a = raw_clean[4:8]
        block_b = raw_clean[8:12]
        check = raw_clean[12:16]
        expected = compute_checksum(block_a, block_b)
        return check == expected
        
    return False

if __name__ == "__main__":
    count = 5
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            count = 5

    print("=" * 60)
    print(">> PCDECK PRO -- OFFICIAL 4-BLOCK LICENSE KEY GENERATOR")
    print(">> Format: PCDK-XXXX-YYYY-ZZZZ (4 Blocks)")
    print("=" * 60)
    print(f"Generating {count} valid lifetime license key(s):\n")

    keys = [generate_key() for _ in range(count)]
    for i, k in enumerate(keys, 1):
        is_valid = verify_key(k)
        print(f"  {i:02d}. {k}   [Valid: {is_valid}]")

    print("\n" + "=" * 60)
    print("These keys work 100% offline in PCDeck on Android, PC & Web!")
    print("=" * 60)
