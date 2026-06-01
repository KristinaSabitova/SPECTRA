import pytest
from fastapi import HTTPException
from unittest.mock import patch

from app.core.ssrf_protection import validate_target_url, _is_private


# ── _is_private unit tests ────────────────────────────────────────────────────

def test_loopback_is_private():
    assert _is_private("127.0.0.1") is True
    assert _is_private("127.0.0.2") is True


def test_rfc1918_are_private():
    assert _is_private("10.0.0.1") is True
    assert _is_private("172.16.0.1") is True
    assert _is_private("172.31.255.255") is True
    assert _is_private("192.168.1.1") is True


def test_link_local_is_private():
    assert _is_private("169.254.0.1") is True


def test_ipv6_loopback_is_private():
    assert _is_private("::1") is True


def test_public_ips_not_private():
    assert _is_private("1.1.1.1") is False
    assert _is_private("8.8.8.8") is False
    assert _is_private("104.16.0.0") is False


# ── validate_target_url integration tests ────────────────────────────────────

def test_invalid_scheme_raises():
    with pytest.raises(HTTPException) as exc:
        validate_target_url("ftp://example.com")
    assert exc.value.status_code == 400


def test_no_hostname_raises():
    with pytest.raises(HTTPException) as exc:
        validate_target_url("http://")
    assert exc.value.status_code == 400


def test_bare_private_ip_raises():
    with pytest.raises(HTTPException) as exc:
        validate_target_url("http://192.168.1.1/api")
    assert exc.value.status_code == 400


def test_bare_loopback_raises():
    with pytest.raises(HTTPException) as exc:
        validate_target_url("http://127.0.0.1:8080/api")
    assert exc.value.status_code == 400


def test_public_url_resolving_to_private_raises():
    # Simulate DNS resolution returning a private IP
    with patch("app.core.ssrf_protection.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 80))]
        with pytest.raises(HTTPException) as exc:
            validate_target_url("http://totally-public.example.com/api")
        assert exc.value.status_code == 400


def test_public_url_resolving_to_public_passes():
    with patch("app.core.ssrf_protection.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(None, None, None, None, ("1.1.1.1", 443))]
        # Should not raise
        validate_target_url("https://example.com/api")
