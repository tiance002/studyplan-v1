"""Bounded Reader wire authority; external text never grants tool authority."""
import hashlib
import re
from dataclasses import dataclass, field

from app.core.ids import content_hash

READER_PURPOSE = "planning.research_reader"
READER_SCHEMA = "ResearchReaderV1"
READER_OUTPUT_CAP = 1024


@dataclass(slots=True)
class TransientBody:
    status: str
    resource_id: str = ""
    url: str = ""
    version: str = ""
    chunks: list[dict] = field(default_factory=list, repr=False)
    reason: str = ""
    requests: int = 0
    bytes_read: int = 0

    def close(self):
        self.chunks.clear()


def validate_reader_input(payload, schema_name):
    try:
        _fields(payload, {"must_teach", "chunks", "learner_context"})
        if schema_name != READER_SCHEMA:
            return False
        outcomes = _array(payload["must_teach"], 20, nonempty=True)
        from app.domain.planning.capability_policy import CAPABILITY_POLICY
        public_outcomes = {o.outcome_id: o.text for d in CAPABILITY_POLICY.definitions for o in d.learning_outcomes}
        ids = []
        for outcome in outcomes:
            _fields(outcome, {"outcome_id", "text"})
            ids.append(_text(outcome["outcome_id"], 200))
            _text(outcome["text"], 2000)
            if public_outcomes.get(outcome["outcome_id"]) != outcome["text"]:
                raise ValueError("Reader public outcome not approved")
        _unique(ids)
        chunks = _array(payload["chunks"], 2, nonempty=True)
        chunk_ids, resource_versions, total = [], set(), 0
        for chunk in chunks:
            _fields(chunk, {"chunk_id", "resource_id", "version", "content_hash", "location", "text"})
            _text(chunk["resource_id"], 200)
            _text(chunk["version"], 200)
            _text(chunk["location"], 1024)
            text = _text(chunk["text"], 16384)
            total += len(text.encode("utf-8"))
            if (not re.fullmatch(r"[0-9a-f]{64}", chunk["content_hash"])
                    or hashlib.sha256(text.encode("utf-8")).hexdigest() != chunk["content_hash"]):
                raise ValueError("Reader chunk hash")
            metadata = {k: chunk[k] for k in ("resource_id", "version", "content_hash", "location")}
            if chunk["chunk_id"] != "chunk_" + content_hash(metadata):
                raise ValueError("Reader chunk identity")
            chunk_ids.append(chunk["chunk_id"])
            resource_versions.add((chunk["resource_id"], chunk["version"]))
        _unique(chunk_ids)
        if len(resource_versions) != 1 or total > 16384:
            raise ValueError("Reader source range")
        learner = payload["learner_context"]
        _fields(learner, {"accepted_known", "desired_depth"})
        allowed = {d.capability_id for d in CAPABILITY_POLICY.definitions}
        known = _array(learner["accepted_known"], 50)
        _unique(known)
        if set(known) - allowed or learner["desired_depth"] not in {"foundation", "applied", "deep"}:
            raise ValueError("Reader learner context")
        return True
    except (ValueError, TypeError, KeyError, UnicodeError):
        return False


def validate_reader_output(raw, payload):
    if not validate_reader_input(payload, READER_SCHEMA):
        raise ValueError("Reader input rejected")
    try:
        _fields(raw, {"outcomes", "teaching_fit"})
        outcomes = _array(raw["outcomes"], 20, nonempty=True)
        expected = {o["outcome_id"] for o in payload["must_teach"]}
        chunks = {c["chunk_id"]: c for c in payload["chunks"]}
        body_texts = {" ".join(c["text"].lstrip("\ufeff").split()) for c in payload["chunks"]}
        reasons = []

        def short_reason(value, limit):
            _text(value, limit)
            normalized = " ".join(value.lstrip("\ufeff").split())
            if any(text and text in normalized for text in body_texts):
                raise ValueError("Reader complete body echo")
            reasons.append(normalized)

        ids = []
        for outcome in outcomes:
            _fields(outcome, {"outcome_id", "status", "evidence_refs", "limitations", "rationale"})
            ids.append(outcome["outcome_id"])
            if outcome["status"] not in {"supported", "partial", "unsupported"}:
                raise ValueError("Reader status")
            refs = _array(outcome["evidence_refs"], 2)
            if outcome["status"] != "unsupported" and not refs:
                raise ValueError("Reader missing evidence")
            cited = []
            for ref in refs:
                _fields(ref, {"chunk_id", "content_hash"})
                chunk = chunks.get(ref["chunk_id"])
                if chunk is None or ref["content_hash"] != chunk["content_hash"]:
                    raise ValueError("Reader evidence mismatch")
                cited.append(ref["chunk_id"])
            _unique(cited)
            for limitation in _array(outcome["limitations"], 3):
                short_reason(limitation, 160)
            short_reason(outcome["rationale"], 240)
        _unique(ids)
        if set(ids) != expected:
            raise ValueError("Reader outcome range")
        # Check the aggregate retained opinion too: splitting a short body
        # across fields/outcomes must not turn it into persistable metadata.
        for text in body_texts:
            covered = set()
            for reason in reasons:
                start = text.find(reason)
                while start >= 0:
                    covered.update(range(start, start + len(reason)))
                    start = text.find(reason, start + 1)
            if (text in " ".join(reasons)
                    or all(char.isspace() or i in covered for i, char in enumerate(text))):
                raise ValueError("Reader aggregate body echo")
        fit = raw["teaching_fit"]
        choices = {"continuity": {"sufficient", "insufficient", "unknown"},
                   "beginner_fit": {"suitable", "unsuitable", "unknown"},
                   "examples": {"present", "absent", "unknown"},
                   "version_fit": {"compatible", "incompatible", "unknown"},
                   "language": {"zh", "en", "other", "unknown"}}
        _fields(fit, set(choices))
        if any(fit[key] not in values for key, values in choices.items()):
            raise ValueError("Reader teaching fit")
        return raw
    except (TypeError, KeyError):
        raise ValueError("Reader output rejected") from None


def _fields(value, expected):
    if type(value) is not dict or set(value) != expected:
        raise ValueError("Reader fields")


def _array(value, limit, nonempty=False):
    if type(value) is not list or len(value) > limit or nonempty and not value:
        raise ValueError("Reader list bound")
    return value


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Reader text bound")
    return value


def _unique(values):
    if len(values) != len(set(values)):
        raise ValueError("Reader duplicate")
