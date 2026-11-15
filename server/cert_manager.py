"""
PCDeck SSL/TLS Certificate Manager.
Generates and manages self-signed local LAN TLS certificates for secure HTTPS/WSS browser streaming
(required by Apple Safari / iOS and Chromium for hardware camera and microphone access).
Strictly adheres to MSIX container isolation by storing certificates in %LOCALAPPDATA%\\PCDeck\\ssl.
"""

import os
import sys
import socket
import datetime
import ipaddress
from typing import Tuple, Optional, List

def get_ssl_storage_dir() -> str:
    """Return secure writable storage directory for PCDeck SSL certificates."""
    appdata = os.environ.get("LOCALAPPDATA")
    if appdata and os.path.isdir(appdata):
        ssl_dir = os.path.join(appdata, "PCDeck", "ssl")
    else:
        ssl_dir = os.path.join(os.path.expanduser("~"), ".pcdeck", "ssl")
    try:
        os.makedirs(ssl_dir, exist_ok=True)
    except Exception:
        import tempfile
        ssl_dir = os.path.join(tempfile.gettempdir(), "pcdeck_ssl")
        os.makedirs(ssl_dir, exist_ok=True)
    return ssl_dir


def get_all_local_ips() -> List[str]:
    """Discover all IPv4 and IPv6 addresses on local machine interfaces for Subject Alternative Names."""
    ips = set()
    ips.add("127.0.0.1")
    ips.add("::1")
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None):
            ip_str = item[4][0]
            if "%" in ip_str:
                ip_str = ip_str.split("%")[0]
            ips.add(ip_str)
    except Exception:
        pass
    return list(ips)


def get_or_create_ssl_cert(primary_ip: str = "127.0.0.1") -> Tuple[Optional[str], Optional[str]]:
    """
    Ensure a valid self-signed certificate and private key exist for the PCDeck HTTPS server.
    Returns (cert_file_path, key_file_path) or (None, None) if TLS generation fails.
    """
    ssl_dir = get_ssl_storage_dir()
    cert_path = os.path.join(ssl_dir, "cert.pem")
    key_path = os.path.join(ssl_dir, "key.pem")

    # If both files already exist and have valid non-zero size, reuse them
    if os.path.isfile(cert_path) and os.path.isfile(key_path):
        try:
            if os.path.getsize(cert_path) > 200 and os.path.getsize(key_path) > 200:
                return cert_path, key_path
        except Exception:
            pass

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        # 1. Generate 2048-bit RSA Private Key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 2. Build SAN list with localhost, hostnames, and all local interface IPs
        san_entries = [
            x509.DNSName("localhost"),
            x509.DNSName("pcdeck.local"),
        ]
        try:
            host_dns = socket.gethostname()
            if host_dns:
                san_entries.append(x509.DNSName(host_dns))
        except Exception:
            pass

        all_ips = set(get_all_local_ips())
        if primary_ip:
            all_ips.add(primary_ip)

        for ip_str in all_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                san_entries.append(x509.IPAddress(ip_obj))
            except ValueError:
                pass

        # 3. Create Certificate Subject & Issuer (Self-Signed)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "PCDeck Secure Local Remote"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PCDeck"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))  # 10 years validity
            .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        # 4. Write Private Key to key.pem
        with open(key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # 5. Write Certificate to cert.pem
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        return cert_path, key_path

    except Exception as e:
        print(f"[SSL] Certificate generation failed: {e}", file=sys.stderr)
        return None, None
