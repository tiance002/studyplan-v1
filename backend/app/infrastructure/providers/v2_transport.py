"""Durable identity before each nested HTTP request of a bounded port call.

The parent attempt holds the shared worst budget. Child dispatches consume that
reservation; only identities/status/byte count/hash are retained, never wire
response bodies, request bodies, headers or source text.
"""

import hashlib
from copy import copy

import httpx
from app.core.ids import content_hash
from app.domain.planning.v2_runtime import V2BudgetExceeded, V2RecoveryBlocked
from psycopg.types.json import Jsonb


class V2GuardedTransport(httpx.BaseTransport):
    def __init__(self, ledger, inner):
        self.ledger, self.inner = ledger, inner

    def handle_request(self, request):
        ledger = self.ledger
        ledger.guard()
        parent = getattr(ledger, "active_dispatch", None)
        if parent is None:
            raise V2RecoveryBlocked("Nested HTTP request has no durable parent reservation")
        parent["children"] += 1
        if parent["children"] > parent["reserved"].get("total_requests", 0):
            raise V2BudgetExceeded()
        detail = {
            "manifest_hash": ledger.manifest["manifest_hash"],
            "parent_attempt_id": parent["attempt_id"],
            "ordinal": parent["children"],
            "purpose": "http.transport",
            "schema": "V2WireReceiptV1",
            "input_hash": content_hash(
                {
                    "method": request.method,
                    "url_hash": content_hash(str(request.url)),
                    "body_hash": hashlib.sha256(request.content).hexdigest(),
                }
            ),
            "source_versions_hash": ledger.manifest["source_facts_hash"],
        }
        detail["identity"] = content_hash(detail)
        with ledger.tx() as conn:
            ledger._lock(conn)
            row = conn.execute(
                "SELECT status FROM ai_provider_attempts WHERE run_id=%s AND attempt_id=%s",
                (ledger.run_id, parent["attempt_id"]),
            ).fetchone()
            if row is None or row["status"] != "dispatched":
                raise V2RecoveryBlocked("Nested HTTP parent is no longer dispatched")
            conn.execute(
                "INSERT INTO ai_run_events(run_id,attempt_id,status,detail) VALUES(%s,%s,'v2_nested_dispatch',%s)",
                (ledger.run_id, parent["attempt_id"], Jsonb(detail)),
            )
        response = self.inner.handle_request(request)
        stream = response.stream

        class ContentFreeStream(httpx.SyncByteStream):
            def __init__(self):
                self.digest = hashlib.sha256()
                self.size = 0
                self.recorded = False

            def __iter__(self):
                for chunk in stream:
                    self.digest.update(chunk)
                    self.size += len(chunk)
                    yield chunk

            def close(self):
                stream.close()
                if not self.recorded:
                    self.recorded = True
                    receipt = {
                        "identity": detail["identity"],
                        "manifest_hash": detail["manifest_hash"],
                        "http_status": response.status_code,
                        "bytes": self.size,
                        "content_hash": self.digest.hexdigest(),
                    }
                    with ledger.tx() as conn:
                        conn.execute(
                            "INSERT INTO ai_run_events(run_id,attempt_id,status,detail) VALUES(%s,%s,'v2_nested_result',%s)",
                            (ledger.run_id, parent["attempt_id"], Jsonb(receipt)),
                        )

        response.stream = ContentFreeStream()
        return response


def guarded_port(ledger, port):
    if port is None or not hasattr(port, "_transport"):
        return port
    # Existing transport-capable adapters are copied per Run; no global state or
    # shared factory's port is mutated when claims move between Workers.
    from app.infrastructure.resources.github import GitHubResourceIndex
    from app.infrastructure.resources.github_transport import PinnedPublicTransport

    result = copy(port)
    inner = port._transport or (
        PinnedPublicTransport()
        if isinstance(port, GitHubResourceIndex)
        else httpx.HTTPTransport(trust_env=False)
    )
    result._transport = V2GuardedTransport(ledger, inner)
    return result
