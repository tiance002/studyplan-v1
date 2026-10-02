"""A rejected DNS destination is known not dispatched, unlike a lost HTTP reply."""
import socket
from datetime import UTC, datetime

from app.domain.resources.models import DEFAULT_SYSTEM_PREFERENCE
from app.domain.workspace.models import AuthContext
from app.infrastructure.resources.github import GitHubResourceIndex
from app.infrastructure.resources.github_transport import PinnedPublicTransport
from app.ports.resource_index import ResourceQuery


def test_fake_ip_dns_rejection_never_opens_socket_and_is_known_not_dispatched(monkeypatch):
    def forbidden_socket(*_args, **_kwargs):
        raise AssertionError("Rejected DNS must not open a TCP socket")
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.19", 443))]
    index = GitHubResourceIndex(transport=PinnedPublicTransport(resolver=lambda *_: answer))
    result = index.find(ResourceQuery(scope=AuthContext(actor_id="owned", session_id="owned", issued_at=datetime.now(UTC), learning_project_scope=("p",)),
        node_keys=(), preference=DEFAULT_SYSTEM_PREFERENCE, limit=5, extra={"project_id":"p", "query":"agent tutorial"}))
    assert result.reason == "github_destination_rejected"
