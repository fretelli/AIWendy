from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException


BLOCKED_HOSTS = {"metadata.google.internal", "metadata.aws.internal"}


def validate_external_https_url(url: str, *, allow_private: bool = False) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Only credential-free public HTTPS URLs are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host in BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="Restricted network destination")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise HTTPException(status_code=400, detail="Unable to resolve destination") from exc
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        if not allow_private and (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_reserved or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="Private and local network destinations are blocked")
    return url.rstrip("/")

