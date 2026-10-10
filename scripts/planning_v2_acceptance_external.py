"""Owned-only external acceptance ports; construction never dispatches.

Private owner grants, their SHA receipts, the prepared packet and all supplied
paths must be controlled by the caller. Hashes bind integrity, not authority.
This helper neither creates approval nor changes the product budget. Global
request/result journals remain append-only, including historical unknowns.
Cash figures are estimates from a newly fetched, independently reviewed price;
they are never a hard cash ceiling. There is no retry or repair path.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import zlib
from contextlib import contextmanager
from copy import copy, deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import httpx
from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.research_reader import TransientBody
from app.domain.planning.v2_runtime import PURPOSE_SCHEMAS, manifest_intact, purpose_schema
from app.domain.resources.models import SourceSearchUnavailable
from app.infrastructure.providers import build_llm
from app.infrastructure.providers.endpoint_policy import ModelEndpointPolicy
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.infrastructure.resources.github import GitHubResourceIndex
from app.infrastructure.resources.github_transport import (
    GitHubNotDispatchedError,
    PinnedPublicTransport,
    validate_github_url,
)
from app.infrastructure.resources.tavily import TavilyResourceIndex
from app.infrastructure.resources.teaching_body import GitHubTeachingBody
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult

GRANT_VERSION = "owned-external-acceptance-v1"
PRICE_REVIEW_VERSION = "owned-price-review-v1"
PRICE_URL = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
BALANCE_URL = "https://api.deepseek.com/user/balance"
READER = "planning.research_reader"
MODEL_RESPONSE_LIMIT = 524288
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _encoded(value):
    return canonical_json(value).encode("utf-8")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _reject(field):
    raise ValidationAppError("Owned external acceptance rejected", field=field)


def _path(value):
    path = Path(value)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        _reject("trusted_absolute_path")
    return path.resolve()


def _decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _reject("duplicate_json_key")
            result[key] = value
        return result
    if len(raw) > 4 * 1024 * 1024:
        _reject("evidence_size")
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        _reject("evidence_json")


def _read(path):
    return _decode(_path(path).read_bytes())


def _exclusive(path, value):
    with _path(path).open("xb") as stream:
        stream.write(_encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def _fresh(value, *, after):
    try:
        issued, oldest = datetime.fromisoformat(value), datetime.fromisoformat(after)
        current = datetime.now(timezone.utc)
        if issued.tzinfo is None or oldest.tzinfo is None or not oldest <= issued <= current:
            _reject("fresh_timestamp")
        if (current - issued).total_seconds() > 86400:
            _reject("stale_authorization_or_preflight")
    except (ValueError, TypeError):
        _reject("fresh_timestamp")


def _packet(packet):
    if (type(packet) is not dict or not manifest_intact(packet.get("manifest"))
        or packet.get("packet_hash") != content_hash({k: v for k, v in packet.items() if k != "packet_hash"})
        or not re.fullmatch(r"scenario-a-[0-9a-f]{32}", packet.get("acceptance_id", ""))):
        _reject("prepared_packet")
    # Reuse the root runner's entire deterministic budget/owned policy check.
    from scripts.planning_v2_scenario_a import request_plan
    if packet.get("request_plan") != request_plan(packet["manifest"]):
        _reject("prepared_request_plan")
    expected = {p: {"model": "deepseek-flash", "max_tokens": 1024 if p == READER else 4096,
        "thinking": {"type": "disabled"}} for p in PURPOSE_SCHEMAS}
    if packet.get("request_options") != expected:
        _reject("prepared_request_options")


def external_authorization_request(packet, *, evidence_dir, model_ledger, search_ledger,
                                   global_model_cap, global_search_cap):
    """Unsigned template only; the owner supplies a separate fresh approval."""
    _packet(packet)
    root = _path(packet["repository_root"])
    evidence = _path(evidence_dir)
    model, search = _path(model_ledger), _path(search_ledger)
    if not evidence.is_relative_to(root / "var") or len({evidence, model, search}) != 3:
        _reject("external_paths")
    if (any(type(v) is not int or v <= 0 for v in (global_model_cap, global_search_cap))
        or not model.is_dir() or not search.is_dir() or not evidence.is_dir()):
        _reject("existing_ledgers_and_caps")
    return {"version": GRANT_VERSION, "acceptance_id": packet["acceptance_id"],
        "packet_hash": packet["packet_hash"], "repository_root": str(root),
        "helper_sha256": _sha(Path(__file__).read_bytes()), "owner_approved": False,
        "owner_evidence": "", "issued_at": "", "actions": [], "evidence_dir": str(evidence),
        "model_ledger": str(model), "search_ledger": str(search),
        "global_model_cap": global_model_cap, "global_search_cap": global_search_cap,
        "request_plan": packet["request_plan"] | {"metadata_requests": 2},
        "request_options": deepcopy(packet["request_options"]), "residual_cash_risk_accepted": False}


def model_configuration_ref(settings):
    """Pure local deployment binding; no credential plaintext is returned."""
    values = {name: getattr(settings, name) for name in ("llm_provider", "llm_base_url", "llm_model_id",
        "llm_timeout_seconds", "llm_max_output_tokens", "llm_outline_output_tokens", "llm_structure_output_tokens",
        "llm_practice_output_tokens", "llm_repair_output_tokens", "llm_model_max_output_tokens")}
    values["allowed_hosts"] = list(settings.llm_allowed_hosts)
    values["secret_revision_sha256"] = _sha(settings.llm_api_key.encode())
    return "acceptance-deployment:" + content_hash(values)


def actual_request_options(settings):
    """Build the existing provider and read its options without DNS/HTTP."""
    port = build_llm(settings)
    if type(port) is not OpenAICompatibleLLM:
        _reject("real_provider_type")
    return {purpose: port.request_options(purpose) for purpose in PURPOSE_SCHEMAS}


@contextmanager
def _ledger_lock(folder):
    """OS advisory lock plus same-process lock. No lock deletion/recovery retry."""
    key = str(_path(folder))
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        _reject("global_ledger_busy")
    stream = None
    acquired = False
    try:
        lock_path = _path(folder) / ".owned-acceptance.lock"
        try:
            with lock_path.open("xb") as initial:
                initial.write(b"0")
                initial.flush()
                os.fsync(initial.fileno())
        except FileExistsError:
            pass
        stream = _path(lock_path).open("r+b")
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        yield
    except OSError:
        _reject("global_ledger_busy_or_unwritable")
    finally:
        if stream is not None:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            stream.close()
        lock.release()


def ledger_snapshot(folder):
    """Strict existing contiguous pairs; unknown pairs remain consumed."""
    folder = _path(folder)
    def files(prefix):
        result = {}
        for path in folder.glob(prefix + "-*.json"):
            match = re.fullmatch(prefix + r"-([0-9]+)\.json", path.name)
            if not match or int(match[1]) in result:
                _reject("ledger_identity")
            result[int(match[1])] = path
        return result
    requests, results = files("request"), files("result")
    if set(requests) != set(results) or sorted(requests) != list(range(1, len(requests) + 1)):
        _reject("unresolved_append_only_journal")
    rows = []
    for number in sorted(requests):
        request, result = _read(requests[number]), _read(results[number])
        if type(request) is not dict or type(result) is not dict:
            _reject("ledger_record")
        # Legacy paired receipts remain intact. Enforce all fields for new rows.
        if request.get("external_version") == GRANT_VERSION:
            if any(result.get(k) != v for k, v in request.items()):
                _reject("ledger_result_binding")
        rows.append((request, result))
    return rows


class AcceptanceExternal:
    """Explicit private dependency for the tracked owned runner.

    Transport injection is a Python test seam; CLI callers use the existing
    production HTTP adapters. guard rechecks the caller's frozen root evidence.
    """
    def __init__(self, packet, *, evidence_dir, model_ledger, search_ledger,
                 authorization, authorization_sha256, guard=None, model_transport=None,
                 github_transport=None, web_transport=None, metadata_transport=None):
        _packet(packet)
        self.packet = deepcopy(packet)
        self.evidence_dir = _path(evidence_dir)
        self.model_ledger, self.search_ledger = _path(model_ledger), _path(search_ledger)
        self.authorization, self.authorization_sha256 = _path(authorization), authorization_sha256
        self.guard = guard or (lambda: None)
        self.model_transport, self.github_transport = model_transport, github_transport
        self.web_transport, self.metadata_transport = web_transport, metadata_transport
        self._clients, self._secrets = [], []
        self._calls = None
        self._wire_reservations = 0
        self._grant()  # No approval defaults and no ledger writes in construction.

    def _grant(self):
        raw = self.authorization.read_bytes()
        if type(self.authorization_sha256) is not str or _sha(raw) != self.authorization_sha256:
            _reject("external_owner_evidence_hash")
        grant = _decode(raw)
        if type(grant) is not dict:
            _reject("external_owner_evidence")
        expected = external_authorization_request(self.packet, evidence_dir=self.evidence_dir,
            model_ledger=self.model_ledger, search_ledger=self.search_ledger,
            global_model_cap=grant.get("global_model_cap"), global_search_cap=grant.get("global_search_cap"))
        dynamic = {"owner_approved", "owner_evidence", "issued_at", "actions", "residual_cash_risk_accepted"}
        if (set(grant) != set(expected) or any(grant[k] != v for k, v in expected.items() if k not in dynamic)
            or grant["owner_approved"] is not True or grant["residual_cash_risk_accepted"] is not True
            or type(grant["owner_evidence"]) is not str or not 1 <= len(grant["owner_evidence"].strip()) <= 2000
            or type(grant["actions"]) is not list or not grant["actions"]
            or any(type(a) is not str for a in grant["actions"])
            or len(set(grant["actions"])) != len(grant["actions"])
            or set(grant["actions"]) - {"preflight", "execute"}):
            _reject("external_owner_authorization")
        _fresh(grant["issued_at"], after=self.packet["manifest"]["checked_at"])
        return grant

    def _stop(self, phase, reason, *, unknown=False):
        path = self.evidence_dir / "STOP.json"
        try:
            _exclusive(path, {"acceptance_id": self.packet["acceptance_id"], "packet_hash": self.packet["packet_hash"],
                "phase": phase, "error_class": reason, "unknown": unknown, "retry": False, "time": _now()})
        except FileExistsError:
            pass

    def check(self, action="execute"):
        """Revalidate trusted owner bytes and frozen root before each action."""
        self.guard()
        from scripts.planning_v2_scenario_a import load_prepared
        if load_prepared(self.evidence_dir / "prepared.json", root=self.packet["repository_root"]) != self.packet:
            _reject("frozen_root_packet_changed")
        _packet(self.packet)
        if (self.evidence_dir / "STOP.json").exists():
            _reject("batch_stopped")
        grant = self._grant()
        permission = "execute" if action == "submit" else action
        if permission not in grant["actions"]:
            _reject("external_action_not_authorized")
        for folder in (self.model_ledger, self.search_ledger):
            with _ledger_lock(folder):
                rows = ledger_snapshot(folder)
                if any(result.get("unknown") is True for request, result in rows
                    if request.get("acceptance_id") == self.packet["acceptance_id"]):
                    _reject("batch_reconciliation_required")
        if action == "execute":
            self._pricing()
            self._binding()
        return grant

    def bind_calls(self, calls):
        """Bind the existing owned durable PG ledger; this performs no DB I/O."""
        from app.infrastructure.providers.v2_attempts import PgV2Calls
        binding = self._binding()
        if (not isinstance(calls, PgV2Calls) or calls.run_id != binding["run_id"]
            or calls.project_id != binding["project_id"] or calls.scope.actor_id != binding["actor_id"]
            or calls.manifest != self.packet["manifest"]
            or getattr(calls.provider, "configuration_ref", None) != self.packet["manifest"]["model_ref"]):
            _reject("durable_owned_calls_binding")
        self._calls = calls

    def _parent(self, kind, *, attempt_id=None):
        calls = self._calls
        if calls is None:
            _reject("durable_parent_required")
        self.bind_calls(calls)  # Check mutable runtime fields before admission.
        calls.guard()
        parent = getattr(calls, "active_dispatch", None)
        if (type(parent) is not dict or type(parent.get("attempt_id")) is not str or not parent["attempt_id"]
            or type(parent.get("reserved")) is not dict or type(parent.get("children")) is not int
            or parent["children"] < 0 or (attempt_id is not None and parent["attempt_id"] != attempt_id)):
            _reject("durable_parent_not_active")
        metric, minimum = ("searches", 1) if kind == "search" else ("body_bytes", 65536) if kind in {"body_operation", "body_http"} else ("output_tokens", 1)
        if (type(parent["reserved"].get(metric)) is not int or parent["reserved"][metric] < minimum
            or type(parent["reserved"].get("total_requests")) is not int or parent["reserved"]["total_requests"] < 1):
            _reject("durable_parent_reservation")
        return {"parent_attempt_id": parent["attempt_id"], "pg_child_ordinal": parent["children"],
            "parent_reserved_hash": content_hash(parent["reserved"])}

    def bind_run(self, run_id, project_id, actor_id):
        self.check("submit")
        if any(type(v) is not str or not 1 <= len(v) <= 200 for v in (run_id, project_id, actor_id)):
            _reject("owned_run_binding")
        binding = {"acceptance_id": self.packet["acceptance_id"], "packet_hash": self.packet["packet_hash"],
            "manifest_hash": self.packet["manifest"]["manifest_hash"], "run_id": run_id,
            "project_id": project_id, "actor_id": actor_id}
        path = self.evidence_dir / "external-run-binding.json"
        if path.exists():
            if _read(path) != binding:
                _reject("second_or_mismatched_run")
        else:
            # A missing local binding can never adopt/replay an old global ID.
            for folder in (self.model_ledger, self.search_ledger):
                with _ledger_lock(folder):
                    if any(r.get("acceptance_id") == self.packet["acceptance_id"] for r, _ in ledger_snapshot(folder)):
                        _reject("acceptance_identity_already_used")
            _exclusive(path, binding)
        return binding

    def _binding(self):
        binding = _read(self.evidence_dir / "external-run-binding.json")
        expected = {"acceptance_id", "packet_hash", "manifest_hash", "run_id", "project_id", "actor_id"}
        if (type(binding) is not dict or set(binding) != expected
            or binding["acceptance_id"] != self.packet["acceptance_id"]
            or binding["packet_hash"] != self.packet["packet_hash"]
            or binding["manifest_hash"] != self.packet["manifest"]["manifest_hash"]):
            _reject("owned_run_binding")
        return binding

    def _identity(self, *, run=False):
        result = {"external_version": GRANT_VERSION, "acceptance_id": self.packet["acceptance_id"],
            "packet_hash": self.packet["packet_hash"], "manifest_hash": self.packet["manifest"]["manifest_hash"],
            "repository_root": self.packet["repository_root"], "head": self.packet["head"],
            "model_ref": self.packet["manifest"]["model_ref"], "authorization_sha256": self.authorization_sha256}
        return result | (self._binding() if run else {})

    def _reserve(self, folder, *, kind, limit, global_cap, detail, purpose=None):
        folder = _path(folder)
        with _ledger_lock(folder):
            rows = ledger_snapshot(folder)
            fresh = [r for r, _ in rows if r.get("acceptance_id") == self.packet["acceptance_id"]]
            if len(rows) >= global_cap or len(fresh) >= limit:
                _reject("external_budget_exhausted")
            if purpose is not None and sum(r.get("purpose") == purpose for r in fresh) >= self.packet["request_plan"]["purpose_limits"][purpose]:
                _reject("external_purpose_budget_exhausted")
            if detail.get("attempt_id") and any(r.get("attempt_id") == detail["attempt_id"] for r, _ in rows):
                _reject("attempt_already_dispatched")
            if any(s.get("unknown") is True for r, s in rows if r.get("acceptance_id") == self.packet["acceptance_id"]):
                _reject("batch_reconciliation_required")
            authority = folder / ("authorization-" + self.packet["acceptance_id"] + ".json")
            grant = self._grant()
            if authority.exists():
                if _read(authority) != grant:
                    _reject("global_authority_changed")
            else:
                _exclusive(authority, grant)
            number = len(rows) + 1
            record = self._identity(run=kind != "metadata") | {"kind": kind, "number": number,
                "time": _now()} | detail
            _exclusive(folder / f"request-{number:02}.json", record)
        return record

    def _result(self, folder, record, **detail):
        with _ledger_lock(folder):
            _exclusive(folder / f"result-{record['number']:02}.json", record | detail)

    def _local_ledger(self, name):
        folder = self.evidence_dir / name
        folder.mkdir(exist_ok=True)
        return _path(folder)

    def _settings(self, settings):
        if (settings.llm_provider != "openai_compatible" or settings.use_fake_llm
            or settings.llm_model_id != "deepseek-flash" or settings.llm_base_url.rstrip("/") != "https://api.deepseek.com"
            or not settings.llm_api_key or model_configuration_ref(settings) != self.packet["manifest"]["model_ref"]):
            _reject("real_provider_configuration")
        self._secrets = [value for value in (settings.llm_api_key, settings.tavily_api_key) if value]

    def _secret_free(self, raw):
        if any(value.encode() in raw for value in self._secrets):
            _reject("response_secret_echo")

    def preflight(self, settings, *, transport=None):
        """At most two official GETs; a crash/pending intent permanently blocks."""
        self.check("preflight")
        self._settings(settings)
        folder = self._local_ledger("external-metadata")
        with _ledger_lock(folder):
            if ledger_snapshot(folder):
                _reject("metadata_preflight_already_used")
        inner = transport or self.metadata_transport or httpx.HTTPTransport(retries=0, trust_env=False)
        with httpx.Client(transport=inner, timeout=25, trust_env=False, follow_redirects=False) as client:
            for kind, url in (("price", PRICE_URL), ("balance", BALANCE_URL)):
                record = None
                try:
                    self.check("preflight")
                    ModelEndpointPolicy(("api-docs.deepseek.com", "api.deepseek.com")).validate(url)
                    record = self._reserve(folder, kind="metadata", limit=2, global_cap=2,
                        detail={"metadata_kind": kind, "method": "GET", "url": url})
                    with client.stream("GET", url, headers={"Authorization": "Bearer " + settings.llm_api_key}
                        if kind == "balance" else {}) as response:
                        raw = bytearray()
                        for chunk in response.iter_bytes():
                            if len(raw) + len(chunk) > 262144:
                                raise ValueError("metadata_response_size")
                            raw.extend(chunk)
                        self._secret_free(raw)
                        if response.status_code != 200:
                            raise ValueError("metadata_http_rejected")
                    if kind == "price":
                        parser = _PriceText()
                        parser.feed(bytes(raw).decode("utf-8"))
                        artifact = {"acceptance_id": self.packet["acceptance_id"], "packet_hash": self.packet["packet_hash"],
                            "url": url, "time": _now(), "http_status": 200, "body_sha256": _sha(raw),
                            "text": "\n".join(parser.parts)}
                    else:
                        data = _decode(bytes(raw))
                        rows = data.get("balance_infos") if type(data) is dict else None
                        if data.get("is_available") is not True or type(rows) is not list:
                            raise ValueError("balance_unavailable")
                        safe = [{key: row[key] for key in ("currency", "total_balance", "granted_balance", "topped_up_balance")} for row in rows]
                        if not any(row["currency"] == "CNY" and _decimal(row["total_balance"]) > 0 for row in safe):
                            raise ValueError("balance_unavailable")
                        artifact = {"acceptance_id": self.packet["acceptance_id"], "packet_hash": self.packet["packet_hash"],
                            "time": _now(), "http_status": 200, "body_sha256": _sha(raw),
                            "is_available": True, "balance_infos": safe}
                    artifact_path = self.evidence_dir / ("external-price-source.json" if kind == "price" else "external-balance.json")
                    _exclusive(artifact_path, artifact)
                    self._result(folder, record, status="succeeded", unknown=False, http_status=200,
                        response_sha256=_sha(raw), response_bytes=len(raw), artifact_sha256=_sha(artifact_path.read_bytes()))
                except Exception as error:
                    if record is not None:
                        self._result(folder, record, status="reconciliation_required", unknown=True, error_class=type(error).__name__)
                    self._stop("metadata", type(error).__name__, unknown=record is not None)
                    raise
        return self.price_review_request()

    def price_review_request(self):
        price, balance = self.evidence_dir / "external-price-source.json", self.evidence_dir / "external-balance.json"
        return {"version": PRICE_REVIEW_VERSION, "acceptance_id": self.packet["acceptance_id"],
            "packet_hash": self.packet["packet_hash"], "price_source_sha256": _sha(price.read_bytes()),
            "balance_sha256": _sha(balance.read_bytes()), "model": "deepseek-flash", "currency": "CNY",
            "input_peak_per_million": "", "output_peak_per_million": "", "estimate_only": True,
            "approved": False, "reviewed_at": ""}

    def approve_price(self, review_path, *, sha256):
        """Only independently reviewed, caller-trusted price evidence is accepted."""
        self.check("preflight")
        raw = _path(review_path).read_bytes()
        if _sha(raw) != sha256:
            _reject("price_review_hash")
        review = _decode(raw)
        self._validate_price(review)
        receipt = {"review": review, "review_sha256": sha256, "review_path": str(_path(review_path))}
        _exclusive(self.evidence_dir / "external-pricing.json", receipt)
        return receipt

    def _validate_price(self, review):
        template = self.price_review_request()
        dynamic = {"input_peak_per_million", "output_peak_per_million", "approved", "reviewed_at"}
        if (type(review) is not dict or set(review) != set(template)
            or any(review[k] != v for k, v in template.items() if k not in dynamic)
            or review["approved"] is not True
            or any(type(review[k]) is not str or _decimal(review[k]) <= 0
                for k in ("input_peak_per_million", "output_peak_per_million"))):
            _reject("independent_price_review")
        price, balance = _read(self.evidence_dir / "external-price-source.json"), _read(self.evidence_dir / "external-balance.json")
        for artifact in (price, balance):
            if artifact.get("acceptance_id") != self.packet["acceptance_id"] or artifact.get("packet_hash") != self.packet["packet_hash"]:
                _reject("fresh_metadata_binding")
            _fresh(artifact["time"], after=self._grant()["issued_at"])
        _fresh(review["reviewed_at"], after=max(price["time"], balance["time"]))
        rows = ledger_snapshot(self.evidence_dir / "external-metadata")
        if len(rows) != 2 or any(result.get("status") != "succeeded" or result.get("unknown") is not False for _, result in rows):
            _reject("fresh_metadata_receipts")
        for (record, result), kind, url, artifact, name in zip(rows, ("price", "balance"), (PRICE_URL, BALANCE_URL),
            (price, balance), ("external-price-source.json", "external-balance.json"), strict=True):
            if (any(record.get(k) != v for k, v in self._identity().items())
                or record.get("metadata_kind") != kind or record.get("url") != url or record.get("method") != "GET"
                or result.get("artifact_sha256") != _sha((self.evidence_dir / name).read_bytes())
                or result.get("response_sha256") != artifact.get("body_sha256")):
                _reject("official_metadata_artifact_binding")

    def _pricing(self):
        receipt = _read(self.evidence_dir / "external-pricing.json")
        raw = _path(receipt["review_path"]).read_bytes()
        if _sha(raw) != receipt["review_sha256"] or _decode(raw) != receipt["review"]:
            _reject("price_review_integrity")
        self._validate_price(receipt["review"])
        return receipt["review"]

    def provider(self, settings, run_id, *, transport=None):
        self.check("submit")
        self._settings(settings)
        port = build_llm(settings)
        if type(port) is not OpenAICompatibleLLM:
            _reject("real_provider_type")
        for purpose, options in self.packet["request_options"].items():
            if port.request_options(purpose) != options:
                _reject("deployment_options_mismatch")
        port.endpoint_guard = ModelEndpointPolicy(settings.llm_allowed_hosts).validate
        port.configuration_ref = self.packet["manifest"]["model_ref"]
        return _ModelBatch(self, port, run_id, transport or self.model_transport)

    def resource_ports(self, settings, run_id=None, *, github_transport=None, web_transport=None):
        self.check("submit")
        self._settings(settings)
        github = github_transport or self.github_transport
        web = web_transport or self.web_transport
        return SimpleNamespace(github=_BoundedIndex(self, GitHubResourceIndex(transport=_ExternalWire(self, "search", github or PinnedPublicTransport(), run_id))),
            web=_BoundedIndex(self, TavilyResourceIndex(settings.tavily_api_key, transport=_ExternalWire(self, "search",
                web or httpx.HTTPTransport(retries=0, trust_env=False), run_id))) if settings.tavily_api_key else None,
            body_reader=_BoundedBody(self, GitHubTeachingBody(transport=_ExternalWire(self, "body_http",
                github or PinnedPublicTransport(), run_id))))

    def close(self):
        for client in self._clients:
            client.close()
        self._clients.clear()


ExternalAcceptance = AcceptanceExternal


def _decimal(value):
    try:
        result = Decimal(value)
        if not result.is_finite():
            _reject("finite_decimal")
        return result
    except (InvalidOperation, ValueError, TypeError):
        _reject("finite_decimal")


class _PriceText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, value):
        if not self.skip and value.strip():
            self.parts.append(value.strip())


class _ModelResponseRejected(Exception):
    """A received response was locally rejected; never a dispatch retry."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _decode_model_response(raw, encoding):
    """Bound output allocation, using the same codec backends as local HTTPX.

    This owned text-only boundary accepts a single complete encoded frame.
    Multiple codings/frames and trailing bytes are rejected rather than silently
    ignored. HTTPX's streaming chunk_size alone does not bound decompression.
    """
    if encoding == "identity":
        return bytes(raw)
    try:
        if encoding in {"gzip", "deflate"}:
            decoder = zlib.decompressobj(31 if encoding == "gzip" else zlib.MAX_WBITS)
            try:
                decoded = decoder.decompress(raw, MODEL_RESPONSE_LIMIT + 1)
            except zlib.error:
                if encoding != "deflate":
                    raise
                # HTTPX accepts both zlib-wrapped and raw deflate.
                decoder = zlib.decompressobj(-zlib.MAX_WBITS)
                decoded = decoder.decompress(raw, MODEL_RESPONSE_LIMIT + 1)
            if len(decoded) > MODEL_RESPONSE_LIMIT or decoder.unconsumed_tail:
                raise _ModelResponseRejected("model_response_decoded_size")
            if not decoder.eof or decoder.unused_data:
                raise _ModelResponseRejected("model_response_decoding_failed")
        elif encoding == "zstd":
            import zstandard
            # max_output_size is ignored by this backend for declared-size
            # frames. Check the declared length BEFORE any output allocation.
            params = zstandard.get_frame_parameters(raw)
            # This backend returns early for a declared empty frame, skipping
            # completeness/trailing checks. Empty content cannot be model JSON.
            if params.content_size == 0:
                raise _ModelResponseRejected("model_response_decoding_failed")
            if params.content_size != zstandard.CONTENTSIZE_UNKNOWN and params.content_size > MODEL_RESPONSE_LIMIT:
                raise _ModelResponseRejected("model_response_decoded_size")
            if params.window_size > 8 * 1024 * 1024:
                raise _ModelResponseRejected("model_response_decoding_failed")
            decoded = zstandard.ZstdDecompressor(max_window_size=8 * 1024 * 1024).decompress(
                raw, max_output_size=MODEL_RESPONSE_LIMIT + 1, allow_extra_data=False)
        else:
            raise _ModelResponseRejected("model_response_encoding_unsupported")
    except (ImportError, zlib.error) as error:
        raise _ModelResponseRejected("model_response_decoding_failed") from error
    except _ModelResponseRejected:
        raise
    except Exception as error:
        # Codec exceptions carry no response text into receipts or diagnostics.
        raise _ModelResponseRejected("model_response_decoding_failed") from error
    if len(decoded) > MODEL_RESPONSE_LIMIT:
        raise _ModelResponseRejected("model_response_decoded_size")
    return decoded


class _ModelBatch:
    def __init__(self, owner, port, run_id, transport):
        self.owner, self.port, self.run_id = owner, port, run_id
        self.configuration_ref, self.model = port.configuration_ref, port.model
        self.active, self.envelope, self.record = None, None, None
        self.capture = None
        self.dispatch_started = False
        self.lock = threading.Lock()
        port.client = httpx.Client(transport=_ModelWire(self, transport or httpx.HTTPTransport(retries=0, trust_env=False)),
            timeout=port.timeout, trust_env=False, follow_redirects=False)
        owner._clients.append(port.client)

    def request_options(self, purpose):
        return self.port.request_options(purpose)

    def generate_structured(self, **kwargs):
        if not self.lock.acquire(blocking=False):
            raise LLMNotDispatchedError("Owned model dispatch already active")
        try:
            self.record, self.envelope, self.capture, self.dispatch_started = None, None, None, False
            self.owner.check()
            if (kwargs["run_id"] != self.run_id or self.run_id != self.owner._binding()["run_id"]
                or kwargs["purpose"] not in PURPOSE_SCHEMAS
                or kwargs["schema_name"] != purpose_schema(self.owner.packet["manifest"], kwargs["purpose"])):
                raise LLMNotDispatchedError("Owned model identity differs from frozen run")
            self.active, self.envelope, self.record = kwargs, None, None
            self.owner._parent("model", attempt_id=kwargs["attempt_id"])
            try:
                result = self.port.generate_structured(**kwargs)
            except _ModelResponseRejected as error:
                # The wire already stored its one known failure receipt/STOP.
                return LLMFailure(error.reason, "Owned response decoding rejected")
            if self.record is None:
                self.owner._stop(kwargs["purpose"], getattr(result, "error_class", "local_not_dispatched"))
                return result
            envelope, record = self.envelope, self.record
            usage = envelope.get("usage") if type(envelope) is dict else None
            cap = self.request_options(kwargs["purpose"])["max_tokens"]
            valid = (type(usage) is dict and all(type(usage.get(k)) is int and usage[k] >= 0
                for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
                and usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
                and usage["completion_tokens"] <= cap)
            choices = envelope.get("choices") if type(envelope) is dict else None
            finish = choices[0].get("finish_reason") if type(choices) is list and choices and type(choices[0]) is dict else None
            reason = None
            if not valid:
                reason = "usage_untrusted"
            elif (envelope.get("model") != "deepseek-flash"
                    or getattr(result, "model_id", envelope.get("model")) != envelope.get("model")):
                reason = "model_identity_invalid"
            elif type(finish) is not str or finish not in {"stop", "length"}:
                reason = "finish_reason_invalid"
            elif not isinstance(result, LLMResult):
                reason = getattr(result, "error_class", "provider_invalid")
            elif result.finish_reason != "stop" or envelope["choices"][0].get("finish_reason") != "stop":
                reason = "finish_reason_invalid"
            elif result.input_tokens != usage["prompt_tokens"] or result.output_tokens != usage["completion_tokens"]:
                reason = "usage_mismatch"
            pricing = self.owner._pricing()
            cost = str((Decimal(usage["prompt_tokens"]) * Decimal(pricing["input_peak_per_million"])
                + Decimal(usage["completion_tokens"]) * Decimal(pricing["output_peak_per_million"])) / Decimal(1000000)) if valid else None
            unknown = isinstance(result, LLMFailure) and result.dispatch_unknown
            self.owner._result(self.owner.model_ledger, record, status="reconciliation_required" if unknown else "failed" if reason else "succeeded",
                unknown=unknown, usage={k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")} if valid else None,
                usage_sha256=_sha(_encoded(usage)), finish_reason=finish if type(finish) is str and finish in {"stop", "length"} else None,
                estimate_currency="CNY", peak_cash_estimate=cost, estimate_only=True, error_class=reason,
                **(self.capture or {}))
            retained = asdict(result)
            if kwargs["purpose"] == READER:
                # PgV2Calls still owns the final Reader projection/echo checks.
                # Even adapter-valid content stays transient at this boundary.
                retained = {"error_class": reason, "input_tokens": getattr(result, "input_tokens", None),
                    "output_tokens": getattr(result, "output_tokens", None), "payload_retained": False,
                    "payload_sha256": content_hash(result.payload) if isinstance(result, LLMResult) else None,
                    "model_id": envelope.get("model") if envelope.get("model") == "deepseek-flash" else None,
                    "finish_reason": finish if type(finish) is str and finish in {"stop", "length"} else None}
            self.owner._secret_free(_encoded(retained))
            _exclusive(self.owner.evidence_dir / f"external-model-{record['number']:02}-provider.json", retained)
            if reason:
                self.owner._stop(kwargs["purpose"], reason, unknown=unknown)
                if isinstance(result, LLMResult):
                    return LLMFailure(reason, "Owned acceptance response rejected", input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens, latency_ms=result.latency_ms)
            return result
        except Exception as error:
            self.owner._stop("model", type(error).__name__, unknown=self.dispatch_started)
            if isinstance(error, ValidationAppError) and not self.dispatch_started:
                raise LLMNotDispatchedError("Owned model admission rejected before dispatch") from None
            raise
        finally:
            self.active = None
            self.lock.release()


class _ModelWire(httpx.BaseTransport):
    def __init__(self, batch, inner):
        self.batch, self.inner = batch, inner

    def handle_request(self, request):
        batch, owner = self.batch, self.batch.owner
        owner.check()
        kwargs = batch.active
        if kwargs is None or request.method != "POST" or str(request.url) != "https://api.deepseek.com/chat/completions":
            raise LLMNotDispatchedError("Owned model destination rejected")
        body = _decode(request.content)
        options, messages = batch.request_options(kwargs["purpose"]), body.get("messages")
        if (set(body) != {"model", "messages", "max_tokens", "thinking", "response_format"}
            or any(body.get(k) != v for k, v in options.items()) or body["response_format"] != {"type": "json_object"}
            or type(messages) is not list or len(messages) != 2
            or [m.get("role") for m in messages] != ["system", "user"]
            or any(type(m) is not dict or set(m) != {"role", "content"} or type(m["content"]) is not str for m in messages)):
            raise LLMNotDispatchedError("Owned model exact wire options rejected")
        size = len(_encoded(messages))
        if size > 32768:
            raise LLMNotDispatchedError("Owned messages exceed 32768 UTF8 bytes")
        grant = owner._grant()
        record = owner._reserve(owner.model_ledger, kind="model", limit=grant["request_plan"]["model_requests"],
            global_cap=grant["global_model_cap"], purpose=kwargs["purpose"], detail={"purpose": kwargs["purpose"],
                "schema": kwargs["schema_name"], "attempt_id": kwargs["attempt_id"], **options,
                "message_utf8_bytes": size, "messages_sha256": _sha(_encoded(messages)),
                "body_sha256": _sha(request.content), "input_hash": content_hash(kwargs["payload"]),
                "pricing_hash": _sha((owner.evidence_dir / "external-pricing.json").read_bytes()),
                **owner._parent("model", attempt_id=kwargs["attempt_id"])})
        batch.record = record
        batch.dispatch_started = True
        raw = bytearray()
        capture = {"request_sha256": _sha(_encoded(record)), "response_complete": False}
        try:
            response = self.inner.handle_request(request)
            capture["http_status"] = response.status_code
            encodings = response.headers.get_list("content-encoding", split_commas=True)
            capture["content_encoding_sha256"] = _sha(_encoded(encodings))
            encoding = encodings[0].strip().lower() if len(encodings) == 1 else "identity" if not encodings else "unsupported"
            capture["content_encoding"] = encoding if encoding in {"identity", "gzip", "deflate", "zstd"} else "unsupported"
            try:
                for chunk in response.stream:
                    if len(raw) + len(chunk) > MODEL_RESPONSE_LIMIT:
                        raise _ModelResponseRejected("model_response_wire_size")
                    raw.extend(chunk)
            finally:
                response.close()
            capture["response_complete"] = True
            decoded = _decode_model_response(raw, encoding)
            capture.update(response_sha256=_sha(raw), response_bytes=len(raw),
                decoded_sha256=_sha(decoded), decoded_bytes=len(decoded))
            try:
                owner._secret_free(raw)
                owner._secret_free(decoded)
            except ValidationAppError:
                raise _ModelResponseRejected("model_response_secret_echo") from None
            try:
                batch.envelope = _decode(decoded)
            except ValidationAppError:
                batch.envelope = {}
            batch.capture = capture
            # Metadata only: provider text, Reader chunks and secrets stay transient.
            _exclusive(owner.evidence_dir / f"external-model-{record['number']:02}-response.json",
                capture)
            if kwargs["purpose"] != READER:
                with (owner.evidence_dir / f"external-model-{record['number']:02}-response.body").open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            # Provider JSON and usage audit consume exactly this decoded byte
            # string. Strip the encoding to prevent HTTPX decompressing again.
            headers = httpx.Headers(response.headers)
            for field in ("content-encoding", "content-length", "transfer-encoding"):
                headers.pop(field, None)
            headers["content-length"] = str(len(decoded))
            return httpx.Response(response.status_code, headers=headers, content=decoded, request=request)
        except _ModelResponseRejected as error:
            capture.update(response_sha256=_sha(raw), response_bytes=len(raw), error_class=error.reason)
            _exclusive(owner.evidence_dir / f"external-model-{record['number']:02}-response.json", capture)
            owner._result(owner.model_ledger, record, status="failed", unknown=False,
                usage=None, **capture)
            owner._stop(kwargs["purpose"], error.reason, unknown=False)
            batch.record = None
            raise
        except Exception as error:
            owner._result(owner.model_ledger, record, status="reconciliation_required", unknown=True,
                error_class=type(error).__name__, usage=None)
            owner._stop(kwargs["purpose"], type(error).__name__, unknown=True)
            batch.record = None  # Result is already durable; adapter must not duplicate it.
            raise

    def close(self):
        self.inner.close()


class _ExternalWire(httpx.BaseTransport):
    def __init__(self, owner, kind, inner, run_id):
        self.owner, self.kind, self.inner, self.run_id = owner, kind, inner, run_id

    def handle_request(self, request):
        owner = self.owner
        try:
            grant = owner.check()
            if self.run_id is not None and self.run_id != owner._binding()["run_id"]:
                _reject("external_run_binding")
            tavily = request.method == "POST" and str(request.url) == "https://api.tavily.com/search"
            if request.method == "GET" and request.url.host == "api.github.com":
                validate_github_url(str(request.url))
                if (self.kind == "search") != (request.url.path == "/search/repositories"):
                    _reject("external_destination_kind")
            elif tavily and self.kind == "search":
                ModelEndpointPolicy(("api.tavily.com",)).validate("https://api.tavily.com")
                body = _decode(request.content)
                expected = {"search_depth": "basic", "auto_parameters": False, "include_answer": False,
                    "include_raw_content": False, "include_usage": True}
                if (any(body.get(k) != v for k, v in expected.items()) or type(body.get("max_results")) is not int
                    or not 1 <= body["max_results"] <= 5 or set(body) != set(expected) | {"query", "max_results"}):
                    _reject("tavily_wire_options")
            else:
                _reject("external_destination")
            folder = owner.search_ledger if self.kind == "search" else owner._local_ledger("external-body-http")
            limit = grant["request_plan"]["search_requests" if self.kind == "search" else "body_http_requests"]
            record = owner._reserve(folder, kind=self.kind, limit=limit,
                global_cap=grant["global_search_cap"] if self.kind == "search" else limit,
                detail={"method": request.method, "url_sha256": _sha(str(request.url).encode()),
                    "provider": "tavily" if tavily else "github", "body_sha256": _sha(request.content),
                    **owner._parent(self.kind)})
        except Exception as error:
            owner._stop(self.kind, type(error).__name__)
            if isinstance(error, ValidationAppError):
                raise LLMNotDispatchedError("Owned external admission rejected before dispatch") from None
            raise
        owner._wire_reservations += 1
        try:
            response = self.inner.handle_request(request)
        except GitHubNotDispatchedError:
            owner._result(folder, record, status="not_dispatched", unknown=False,
                dispatched=False, error_class="github_destination_rejected")
            owner._stop(self.kind, "github_destination_rejected")
            raise
        except Exception as error:
            owner._result(folder, record, status="reconciliation_required", unknown=True, error_class=type(error).__name__)
            owner._stop(self.kind, type(error).__name__, unknown=True)
            raise
        audit = _AuditStream(owner, response.stream, folder, record, response.status_code, tavily)
        wrapped = httpx.Response(response.status_code, headers=response.headers, request=request,
            extensions=response.extensions,
            stream=audit)
        # HTTPX copies the extensions mapping in Response.__init__. Bind the
        # actual adapter-visible mapping rather than the original transport's.
        audit.extensions = wrapped.extensions
        return wrapped

    def close(self):
        self.inner.close()


class _AuditStream(httpx.SyncByteStream):
    def __init__(self, owner, stream, folder, record, status, tavily, extensions=None):
        self.owner, self.stream, self.folder, self.record, self.status, self.tavily = owner, stream, folder, record, status, tavily
        self.size, self.digest, self.finished, self.closed, self.raw = 0, hashlib.sha256(), False, False, bytearray()
        self.extensions = extensions if extensions is not None else {}

    def __iter__(self):
        for chunk in self.stream:
            self.size += len(chunk)
            self.digest.update(chunk)
            # The body adapter must see and count the over-limit chunk before
            # refusing it against its tighter aggregate 65536-byte reservation.
            # It never appends that chunk to the parsing buffer.
            if self.size > 262144 and self.record["kind"] != "body_http":
                raise httpx.ReadError("Owned external response too large")
            if self.record["kind"] == "search":
                self.raw.extend(chunk)
            yield chunk
        self.finished = True

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stream.close()
        # Known non-200 responses can be classified from their headers without
        # reading error bodies; native adapters deliberately do that.
        unknown, usage, reason = not self.finished and self.status == 200, None, None
        # Only the body adapter can attest to a validated header-only capacity
        # refusal. A partial read, HTTP error or transport interruption cannot
        # acquire this known-unread classification.
        capacity_rejected = (self.record["kind"] == "body_http" and self.status == 200
            and self.size == 0 and not self.finished
            and self.extensions.get("studyplan_body_termination") == "declared_capacity_rejected")
        if capacity_rejected:
            unknown, reason = False, "declared_capacity_rejected"
        elif self.record["kind"] == "body_http" and self.status == 200 and not self.finished:
            termination = self.extensions.get("studyplan_body_termination")
            if termination == "streamed_capacity_rejected" and self.size > 0:
                unknown, reason = False, "streamed_capacity_rejected"
            elif termination == "body_validation_rejected" and self.size == 0:
                unknown, reason = False, "body_validation_rejected"
        if self.finished and self.record["kind"] == "search" and self.status == 200:
            try:
                data = _decode(bytes(self.raw))
                expected = "results" if self.tavily else "items"
                if type(data) is not dict or type(data.get(expected)) is not list:
                    raise ValueError("search_envelope")
                if self.tavily:
                    credits = data.get("usage", {}).get("credits")
                    if type(credits) not in {int, float} or not math.isfinite(credits) or not 0 <= credits <= 10**6:
                        raise ValueError("search_usage_untrusted")
                    usage = {"credits": credits}
            except (ValidationAppError, ValueError, TypeError, AttributeError):
                reason = "search_usage_or_envelope_untrusted"
        self.raw.clear()
        failed = self.status != 200 or reason is not None
        self.owner._result(self.folder, self.record, http_status=self.status, response_bytes=self.size,
            response_sha256=self.digest.hexdigest(), unknown=unknown, usage=usage, error_class=reason,
            status="unread" if capacity_rejected else "reconciliation_required" if unknown else "failed" if failed else "succeeded")
        # Existing port results own the known-HTTP semantic policy (e.g. an
        # unread GitHub chapter is consumed but is not a batch-wide STOP).
        if unknown or (reason is not None and not capacity_rejected):
            self.owner._stop(self.record["kind"], reason or "external_response_failed", unknown=unknown)


class _BoundedIndex:
    def __init__(self, owner, port):
        self.owner, self.port = owner, port
        self._transport = port._transport

    def find(self, query):
        before = self.owner._wire_reservations
        try:
            binding = self.owner._binding()
            if query.scope.actor_id != binding["actor_id"] or query.extra.get("project_id") != binding["project_id"]:
                _reject("external_search_actor_project")
            port = copy(self.port)
            port._transport = self._transport  # Existing guarded_port wraps this per Run.
            result = port.find(query)
        except (LLMNotDispatchedError, ValidationAppError):
            if self.owner._wire_reservations != before:
                raise  # A wire intent exists: native reconciliation keeps authority.
            self.owner._stop("search", "external_admission_not_dispatched")
            return SourceSearchUnavailable(reason="external_admission_not_dispatched", status="not_dispatched",
                requests=0, bytes_read=0, receipts=(), stop_required=True)
        if getattr(result, "stop_required", False):
            self.owner._stop("search", "search_port_stop_required", unknown=getattr(result, "status", None) == "unknown")
        return result


class _BoundedBody:
    supports_outcome_selection = True
    supports_chapter_selection = True

    def __init__(self, owner, port):
        self.owner, self.port = owner, port
        self._transport = port._transport

    def read(self, candidate, **kwargs):
        owner = self.owner
        record = None
        before = owner._wire_reservations
        try:
            grant = owner.check()
            if candidate.project_id != owner._binding()["project_id"]:
                _reject("external_body_project")
            folder = owner._local_ledger("external-body-operations")
            record = owner._reserve(folder, kind="body_operation", limit=grant["request_plan"]["body_operations"],
                global_cap=grant["request_plan"]["body_operations"], detail={"candidate_hash": content_hash({
                    "resource_id": candidate.resource_id, "url": candidate.url, "paths": list(kwargs.get("paths", ())),
                    "must_teach": list(kwargs.get("must_teach", ()))}) , **owner._parent("body_operation")})
            port = copy(self.port)
            port._transport = self._transport
            result = port.read(candidate, **kwargs)
            owner._result(folder, record, status=result.status, unknown=result.status == "unknown")
            if result.status in {"unknown", "failed"}:
                owner._stop("body_operation", "body_read_rejected", unknown=result.status == "unknown")
            return result
        except Exception as error:
            if isinstance(error, (LLMNotDispatchedError, ValidationAppError)) and owner._wire_reservations == before:
                if record is not None:
                    owner._result(folder, record, status="not_dispatched", unknown=False, dispatched=False,
                        error_class="external_admission_not_dispatched")
                owner._stop("body_operation", "external_admission_not_dispatched")
                return TransientBody("failed", reason="external_admission_not_dispatched", requests=0, bytes_read=0)
            if record is not None:
                owner._result(folder, record, status="reconciliation_required", unknown=True, error_class=type(error).__name__)
            owner._stop("body_operation", type(error).__name__, unknown=record is not None)
            raise
