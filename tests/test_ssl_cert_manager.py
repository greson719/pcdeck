"""
Unit Tests for PCDeck SSL/TLS Certificate Manager and HTTPS configuration.
Verifies self-signed SAN certificate generation, non-crashing fallbacks,
MSIX container storage paths, and dual-port metadata exposed via API.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.cert_manager import get_or_create_ssl_cert, get_ssl_storage_dir, get_all_local_ips
from server.main import app, SERVER_PORT, SERVER_SSL_PORT


@pytest.fixture
def client():
    return TestClient(app)


def test_cert_generation_creates_valid_pem_files():
    """Verify that get_or_create_ssl_cert creates non-empty cert.pem and key.pem."""
    cert_path, key_path = get_or_create_ssl_cert(primary_ip="192.168.1.100")
    assert cert_path is not None
    assert key_path is not None
    assert os.path.isfile(cert_path)
    assert os.path.isfile(key_path)
    assert os.path.getsize(cert_path) > 300
    assert os.path.getsize(key_path) > 300

    # Ensure certificate contents start with standard PEM headers
    with open(cert_path, "r", encoding="utf-8") as f:
        cert_content = f.read()
    with open(key_path, "r", encoding="utf-8") as f:
        key_content = f.read()

    assert "-----BEGIN CERTIFICATE-----" in cert_content
    assert "-----BEGIN " in key_content


def test_cert_storage_preserves_msix_isolation():
    """Verify certificate storage path is inside LocalAppData or ~/.pcdeck."""
    ssl_dir = get_ssl_storage_dir()
    assert os.path.isdir(ssl_dir)
    lower = ssl_dir.lower()
    assert "pcdeck" in lower or "temp" in lower


def test_get_all_local_ips_returns_loopback():
    """Verify local IP enumeration discovers 127.0.0.1 and ::1."""
    ips = get_all_local_ips()
    assert "127.0.0.1" in ips
    assert "::1" in ips


def test_api_ping_exposes_ssl_port(client):
    """Verify /api/ping returns both primary HTTP and secondary HTTPS port numbers."""
    response = client.get("/api/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["port"] == SERVER_PORT
    assert data["ssl_port"] == SERVER_SSL_PORT
    assert data["ssl_port"] == 8443


def test_api_info_exposes_ssl_metadata(client):
    """Verify /api/info returns valid HTTPS URL and SSL port for browser clients."""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["ssl_port"] == SERVER_SSL_PORT
    assert "ssl_url" in data
    assert data["ssl_url"].startswith("https://")
    assert ":8443" in data["ssl_url"]
