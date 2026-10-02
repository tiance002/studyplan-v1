"""Fixed GitHub endpoint transport with public DNS pinning and total deadlines.

The checked sockaddr is connected directly; TLS still verifies api.github.com.
No proxy environment, redirect, retry, or second hostname resolution is used.
"""
import ipaddress
import queue
import re
import socket
import ssl
import threading
import time
from contextvars import ContextVar
from urllib.parse import parse_qsl, unquote, urlsplit

import httpcore
import httpx
from httpcore._backends.sync import SyncBackend, SyncStream

_DEADLINE = ContextVar("github_deadline", default=None)
_REPO_COMPONENT = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


class GitHubNotDispatchedError(httpx.TransportError):
    """A proven destination rejection before opening any TCP socket."""


class _DestinationRejected(httpcore.ConnectError):
    pass


def validate_content_path(path):
    if not isinstance(path, str) or not 1 <= len(path) <= 1024:
        raise ValueError("Invalid repository path")
    if path.startswith(("/", "\\")) or any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ValueError("Invalid repository path")
    if any(c in path for c in ("\\", "%", "?", "#", ":")):
        raise ValueError("Invalid repository path")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise ValueError("Invalid repository path")
    path.encode("utf-8")
    return path


def validate_github_url(url):
    parsed = urlsplit(str(url))
    if (parsed.scheme != "https" or parsed.hostname != "api.github.com"
            or parsed.port not in (None, 443) or parsed.username is not None
            or parsed.password is not None or parsed.fragment or "\\" in str(url)
            or any(ord(c) <= 32 or ord(c) == 127 for c in str(url))):
        raise ValueError("GitHub destination rejected")
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if len(params) != len(dict(params)):
        raise ValueError("Duplicate GitHub parameters")
    parameters = dict(params)
    if parsed.path == "/search/repositories":
        if set(parameters) - {"q", "per_page"} or not 1 <= len(parameters.get("q", "")) <= 500:
            raise ValueError("Invalid GitHub search parameters")
        if parameters.get("per_page", "5") not in {"1", "2", "3", "4", "5"}:
            raise ValueError("Invalid GitHub search limit")
        return
    match = re.fullmatch(r"/repos/([^/]+)/([^/]+)(?:/(readme|contents)(?:/(.+))?)?", parsed.path)
    if not match or not all(_REPO_COMPONENT.fullmatch(part) and part not in {".", ".."}
                            for part in match.group(1, 2)):
        raise ValueError("GitHub path rejected")
    if set(parameters) - {"ref"} or any(not 1 <= len(value) <= 255 or any(ord(c) < 32 for c in value)
                                      for value in parameters.values()):
        raise ValueError("Invalid GitHub content parameters")
    if match.group(4):
        raw_parts = match.group(4).split("/")
        decoded = [unquote(part, errors="strict") for part in raw_parts]
        if any("/" in part for part in decoded):
            raise ValueError("Encoded repository separators rejected")
        validate_content_path("/".join(decoded))
    elif match.group(3) == "contents":
        raise ValueError("Unbounded repository index rejected")


def _remaining(deadline, timeout):
    remaining = deadline - time.monotonic() if deadline is not None else timeout
    if remaining is not None and remaining <= 0:
        raise httpcore.ReadTimeout("GitHub operation deadline exceeded")
    return min(remaining, timeout) if remaining is not None and timeout is not None else remaining or timeout


class DeadlineStream(httpcore.NetworkStream):
    def __init__(self, stream, deadline):
        self.stream, self.deadline = stream, deadline

    def read(self, max_bytes, timeout=None):
        result = self.stream.read(max_bytes, timeout=_remaining(self.deadline, timeout))
        _remaining(self.deadline, timeout)
        return result

    def write(self, buffer, timeout=None):
        return self.stream.write(buffer, timeout=_remaining(self.deadline, timeout))

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        if server_hostname != "api.github.com":
            raise httpcore.ConnectError("GitHub TLS hostname rejected")
        return DeadlineStream(self.stream.start_tls(ssl_context, server_hostname,
            timeout=_remaining(self.deadline, timeout)), self.deadline)

    def close(self):
        self.stream.close()

    def get_extra_info(self, info):
        return self.stream.get_extra_info(info)


class PinnedGitHubBackend(SyncBackend):
    def __init__(self, *, resolver=None):
        self.resolver = resolver or socket.getaddrinfo

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host != "api.github.com" or port != 443 or local_address is not None:
            raise httpcore.ConnectError("GitHub destination rejected")
        deadline = _DEADLINE.get() or time.monotonic() + (timeout or 15)
        replies = queue.Queue(maxsize=1)
        def resolve():
            try:
                replies.put((self.resolver(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM), None))
            except Exception:
                replies.put((None, True))
        threading.Thread(target=resolve, daemon=True).start()
        try:
            addresses, error = replies.get(timeout=_remaining(deadline, timeout))
        except queue.Empty as exc:
            raise httpcore.ConnectTimeout("GitHub DNS deadline exceeded") from exc
        if error or not addresses:
            raise httpcore.ConnectError("GitHub DNS failed")
        for family, kind, _protocol, _, sockaddr in addresses:
            address = ipaddress.ip_address(sockaddr[0])
            if (family not in {socket.AF_INET, socket.AF_INET6} or kind != socket.SOCK_STREAM
                    or sockaddr[1] != 443 or not address.is_global or address.is_multicast
                    or (isinstance(address, ipaddress.IPv6Address) and (address.is_site_local
                        or address.ipv4_mapped is not None))):
                raise _DestinationRejected("GitHub DNS address rejected")
        # One address, one connection attempt. Failures remain explicit and
        # cannot produce hidden request amplification or a DNS rebinding gap.
        family, kind, protocol, _, sockaddr = addresses[0]
        sock = socket.socket(family, kind, protocol)
        try:
            sock.settimeout(_remaining(deadline, timeout))
            for option in socket_options or ():
                sock.setsockopt(*option)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.connect(sockaddr)
            return DeadlineStream(SyncStream(sock), deadline)
        except socket.timeout as exc:
            sock.close()
            raise httpcore.ConnectTimeout("GitHub connect timeout") from exc
        except OSError as exc:
            sock.close()
            raise httpcore.ConnectError("GitHub connect failed") from exc


class PinnedPublicTransport(httpx.HTTPTransport):
    def __init__(self, *, resolver=None):
        super().__init__(verify=True, trust_env=False, retries=0)
        self._pool.close()
        self._pool = httpcore.ConnectionPool(ssl_context=ssl.create_default_context(),
            network_backend=PinnedGitHubBackend(resolver=resolver), retries=0,
            max_connections=1, max_keepalive_connections=0)

    def handle_request(self, request):
        validate_github_url(str(request.url))
        if request.method != "GET":
            raise ValueError("GitHub request method rejected")
        deadline = request.extensions.get("n1_deadline") or time.monotonic() + 15
        token = _DEADLINE.set(deadline)
        try:
            return super().handle_request(request)
        except httpx.ConnectError as exc:
            cause = exc
            for _ in range(5):
                if isinstance(cause, _DestinationRejected):
                    raise GitHubNotDispatchedError("GitHub destination rejected before TCP/HTTP dispatch") from exc
                cause = cause.__cause__
                if cause is None:
                    break
            raise
        finally:
            _DEADLINE.reset(token)
