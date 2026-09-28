"""Approved public HTTPS model origins; validate again before any credential dispatch."""
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

from app.core.errors import AppError, ErrorCode, ValidationAppError


class ModelEndpointPolicy:
    def __init__(self, allowed_hosts):
        self.allowed_hosts = frozenset(host.strip().lower() for host in allowed_hosts if host.strip())

    def validate(self, value):
        value = value.strip()
        if not value or any(ord(char)<33 for char in value):
            raise ValidationAppError("Invalid model Base URL")
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme == "https" and parsed.hostname in self.allowed_hosts
                     and parsed.port in (None,443) and not parsed.username and not parsed.password
                     and not parsed.query and not parsed.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise ValidationAppError("Use an approved HTTPS model provider on port 443 without URL credentials or query")
        try:
            addresses = socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ValidationAppError("Model provider must resolve only to public addresses")
        except (socket.gaierror, ValueError):
            raise AppError(ErrorCode.DEPENDENCY_UNAVAILABLE,"Model provider DNS unavailable") from None
        return urlunsplit(("https",parsed.netloc.lower(),parsed.path.rstrip("/"),"",""))
