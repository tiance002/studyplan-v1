"""One pinned official-source read, no search/model/automatic retry."""
import hashlib
from dataclasses import asdict
from urllib.parse import quote, urlsplit

from app.core.errors import AppError
from app.core.ids import content_hash
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.planning.constraint_adaptation import composition_dispatch_allowed
from app.domain.planning.domain_verification import (
    DomainVerificationResult,
    _issue_approval,
    _profile,
    _source,
    verification_session_hash,
)
from app.domain.planning.research_reader import TransientBody
from app.domain.planning.resource_research import ResearchSession
from app.domain.resources.models import ResourceRecord
from app.domain.workspace.models import AuthContext


class DomainVerifier:
    def __init__(self, body_reader, *, sources=()):
        self._body_reader, self._sources = body_reader, tuple(sources)
        if len(self._sources) > 20 or len({s.source_id for s in self._sources}) != len(self._sources):
            raise ValueError("Domain source registry rejected")
        for source in self._sources:
            _source(source)

    def verify(self, profile, *, source_id, session, scope, project_id):
        body = text = chunk = None
        def result(reason, *, unknown=False, **metadata):
            return DomainVerificationResult("unknown" if unknown else "needs_verification", reason=reason, **metadata)
        try:
            _profile(profile)
            if type(scope) is not AuthContext or type(session) is not ResearchSession:
                return result("verification_input_rejected")
            scope.require_project(project_id)
            if session.config_hash:
                return result("verification_stopped")
            source = next((s for s in self._sources if s.source_id == source_id), None)
            if source is None:
                return result("DOMAIN_VERIFICATION_LIVE_PENDING")
            expected = verification_session_hash(profile, source, budget=session.budget,
                actor_id=scope.actor_id, project_id=project_id)
            if session.input_hash != expected:
                return result("verification_input_rejected")
            if not composition_dispatch_allowed([asdict(c) for c in profile.hard_constraints]):
                return result("verification_constraints_pending")
            if session.blocked:
                return result("verification_stopped")
            reservation = session.reserve("domain_verification", total_requests=2, body_bytes=65536)
            if reservation is None:
                return result("verification_budget_exhausted")
            # One dispatch per verification session, including known failures.
            # Snapshot retains this marker; later runtime consumes the Receipt.
            session.config_hash = content_hash({"domain_verification_dispatch": expected, "source_hash": source.source_hash})
            owner, name = urlsplit(source.repo_url).path.strip("/").split("/")
            candidate = ResourceRecord("domain_source_" + source.source_id, source.repo_url, source.source_id,
                MediaType.REPO, "unknown", ResourceProvenance.SEARCH_CANDIDATE,
                ResourceVerificationStatus.UNVERIFIED, project_id, discovery={"source": "github", "repo": {
                    "owner": owner, "name": name, "default_branch": source.commit_sha}})
            try:
                body = self._body_reader.read(candidate, paths=(source.path,), max_bytes=65536, timeout_seconds=15)
            except Exception:
                session.mark_unknown()
                session.unknown_measurement = True
                return result("verification_unknown", unknown=True)
            if (type(body) is not TransientBody or type(body.requests) is not int or type(body.bytes_read) is not int
                or not 0 <= body.requests <= 10**12 or not 0 <= body.bytes_read <= 10**12):
                session.mark_unknown()
                session.unknown_measurement = True
                return result("verification_unknown", unknown=True)
            receipt = {"requests": body.requests, "bytes_read": body.bytes_read}
            if body.status == "unknown":
                # Keep pending/worst and raise only observed lower bounds.
                session.usage["total_requests"] += max(0, body.requests - 2)
                session.usage["body_bytes"] += max(0, body.bytes_read - 65536)
                session.mark_unknown()
                session.unknown_measurement = True
                return result("verification_unknown", unknown=True, **receipt)
            try:
                session.settle(reservation, total_requests=body.requests, body_bytes=body.bytes_read)
            except AppError:
                session.blocked = True
                return result("verification_budget_exceeded", **receipt)
            if body.status != "succeeded":
                return result("verification_source_unavailable", **receipt)
            url = source.repo_url + "/blob/" + source.commit_sha + "/" + quote(source.path, safe="/")
            resource_id = "resource_" + content_hash({"url": url})
            if (body.requests != 2 or body.resource_id != resource_id or body.url != url
                or body.version != "git-blob:" + source.blob_sha or type(body.chunks) is not list or len(body.chunks) != 1):
                return result("verification_pin_mismatch", **receipt)
            chunk = body.chunks[0]
            if type(chunk) is not dict or set(chunk) != {"resource_id", "version", "content_hash", "location", "chunk_id", "text"}:
                return result("verification_pin_mismatch", **receipt)
            text = chunk["text"]
            if not isinstance(text, str) or not 0 < len(text.encode("utf-8")) <= 16384:
                return result("verification_pin_mismatch", **receipt)
            meta = {"resource_id": resource_id, "version": body.version, "content_hash": source.body_sha256,
                "location": source.path + "#L1-L" + str(max(1, len(text.splitlines())))}
            if (hashlib.sha256(text.encode("utf-8")).hexdigest() != source.body_sha256 or chunk != meta | {
                "chunk_id": "chunk_" + content_hash(meta), "text": text}):
                return result("verification_pin_mismatch", **receipt)
            approval = _issue_approval(profile, source)
            return DomainVerificationResult("verified", approval.evidence, approval, requests=body.requests, bytes_read=body.bytes_read)
        except (AppError, TypeError, ValueError, KeyError, AttributeError, UnicodeError):
            return result("verification_input_rejected")
        finally:
            if type(body) is TransientBody:
                body.close()
            text = chunk = None
