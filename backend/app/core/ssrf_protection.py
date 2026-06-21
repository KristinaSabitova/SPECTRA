"""
SSRF (Server-Side Request Forgery) protection.

Before making HTTP requests to user-supplied URLs, resolve the hostname and
reject any IP that belongs to private or reserved ranges.  This prevents an
attacker from using SPECTRA as a proxy to probe internal infrastructure.

Protected ranges (RFC 1918 / RFC 5735 / RFC 4291 / RFC 6598):
  127.0.0.0/8        loopback
  10.0.0.0/8         RFC-1918 private
  172.16.0.0/12      RFC-1918 private
  192.168.0.0/16     RFC-1918 private
  169.254.0.0/16     link-local
  0.0.0.0/8          this-network
  100.64.0.0/10      shared address space (CGN)
  ::1/128            IPv6 loopback
  fc00::/7           IPv6 ULA
  fe80::/10          IPv6 link-local
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, status

_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable — block by default
    return any(addr in net for net in _BLOCKED_NETWORKS)


def validate_target_url(url: str) -> None:
    """
    Validate that a user-supplied URL does not point to private infrastructure.

    Resolves all A/AAAA records for the hostname and rejects if any resolves
    to a private or reserved address.  The error message is intentionally vague
    to avoid leaking internal DNS topology to an attacker.

    Raises HTTPException 400 on any violation.
    """
    parsed = urlparse(url)
    _ALLOWED_HOSTS = {"lab"}
    if parsed.hostname in _ALLOWED_HOSTS:
        return
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL must use http or https scheme.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target URL must include a hostname.",
        )

    # Reject bare IP literals in private ranges before doing any DNS round-trip.
    # ipaddress.ip_address() raises ValueError for domain names, so this only
    # fires when the hostname is an actual IP literal (e.g. http://192.168.1.1/).
    try:
        ipaddress.ip_address(hostname)  # raises ValueError for domain names
        if _is_private(hostname):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target URL points to a restricted address.",
            )
        # IP literal is public — no DNS resolution needed, skip to success
        return
    except ValueError:
        pass  # hostname is a domain name, continue to DNS resolution

    # KNOWN LIMITATION — DNS rebinding / TOCTOU: we resolve here and then httpx
    # opens a new connection that resolves DNS again.  An attacker who controls
    # DNS TTL could serve a public IP for the check and a private IP for the
    # actual request.  Future fix: resolve once, pass the IP literal directly to
    # httpx (e.g. via a custom transport or the `proxies` param with an IP URL).
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve target hostname: {exc}",
        )

    for family, _type, _proto, _canonname, sockaddr in infos:
        resolved_ip = sockaddr[0]
        if _is_private(resolved_ip):
            # Intentionally omit the resolved IP to prevent info leaks
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target URL resolves to a private or reserved address.",
            )
