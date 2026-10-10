"""Actual acceptance adapters, synthetic private grants and MockTransport only."""
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.domain.enums import MediaType, PreferenceScope, ResourceProvenance, ResourceVerificationStatus
from app.domain.planning.intent import GoalSpec
from app.domain.resources.models import ResourcePreference, ResourceRecord
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult
from app.ports.resource_index import ResourceQuery

from scripts import planning_v2_acceptance_external as ext
from scripts import planning_v2_scenario_a as runner
from scripts.planning_v2_owned_source_facts import freeze_reviewed_source_facts, read_source_facts


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return sha(path)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("W5 unit tests must never resolve DNS or open a socket")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(ext.ModelEndpointPolicy, "validate", lambda self, value: value
        if httpx.URL(value).host in self.allowed_hosts else forbidden())


@pytest.fixture
def owned(tmp_path, monkeypatch):
    settings = replace(get_settings(), llm_provider="openai_compatible", llm_base_url="https://api.deepseek.com",
        llm_api_key="synthetic-api-secret-not-real", llm_model_id="deepseek-flash",
        llm_max_output_tokens=8192, llm_practice_output_tokens=4096,
        tavily_api_key="synthetic-web-secret-not-real")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("var/\n", encoding="utf-8")
    monkeypatch.setattr(runner, "_head", lambda _root: "a" * 40)
    ref = freeze_reviewed_source_facts(tmp_path / "facts.json", root=runner.ROOT)
    evidence = tmp_path / "var" / "fresh-owned"
    packet = runner.prepare(evidence, root=tmp_path, goal=GoalSpec("学习代码审查 Agent"),
        model_ref=ext.model_configuration_ref(settings), request_options=ext.actual_request_options(settings),
        facts=read_source_facts(ref))
    model, search = tmp_path / "model-ledger", tmp_path / "search-ledger"
    model.mkdir()
    search.mkdir()
    grant = ext.external_authorization_request(packet, evidence_dir=evidence, model_ledger=model,
        search_ledger=search, global_model_cap=280, global_search_cap=1000)
    grant.update(owner_approved=True, residual_cash_risk_accepted=True,
        owner_evidence="Synthetic unit fixture only; no real Owner authorization", issued_at=datetime.now(timezone.utc).isoformat(),
        actions=["preflight", "execute"])
    path = evidence / "synthetic-external-owner.json"
    digest = save(path, grant)
    options = dict(packet=packet, evidence_dir=evidence, model_ledger=model, search_ledger=search,
        authorization=path, authorization_sha256=digest)
    return settings, options, grant


def metadata(calls):
    def respond(request):
        calls.append(request)
        if str(request.url) == ext.PRICE_URL:
            return httpx.Response(200, text="<html><p>Fresh official fixture DeepSeek Flash CNY input 1 output 2</p><script>ignore</script></html>")
        assert str(request.url) == ext.BALANCE_URL
        return httpx.Response(200, json={"is_available": True, "balance_infos": [{"currency": "CNY",
            "total_balance": "20.50", "granted_balance": "0.00", "topped_up_balance": "20.50"}]})
    return httpx.MockTransport(respond)


def ready(owned, **kwargs):
    settings, options, _grant = owned
    calls = []
    external = ext.AcceptanceExternal(**options, **kwargs)
    external.preflight(settings, transport=metadata(calls))
    review = external.price_review_request()
    review.update(approved=True, input_peak_per_million="1", output_peak_per_million="2",
        reviewed_at=datetime.now(timezone.utc).isoformat())
    path = options["evidence_dir"] / "independent-synthetic-price.json"
    external.approve_price(path, sha256=save(path, review))
    external.bind_run("synthetic-new-run", "synthetic-project", "synthetic-actor")
    from app.infrastructure.providers.v2_attempts import PgV2Calls
    parent = object.__new__(PgV2Calls)  # Explicit synthetic parent, no PG connection.
    parent.run_id, parent.project_id = "synthetic-new-run", "synthetic-project"
    parent.scope = SimpleNamespace(actor_id="synthetic-actor")
    parent.manifest, parent.guard = options["packet"]["manifest"], lambda: None
    parent.provider = SimpleNamespace(configuration_ref=parent.manifest["model_ref"])
    parent.active_dispatch = {"attempt_id": "synthetic-parent", "reserved": {"total_requests": 2,
        "output_tokens": 4096, "searches": 1, "body_bytes": 65536}, "children": 0}
    external.bind_calls(parent)
    return external, calls


def goal_payload():
    return {"goal": {"target": "做只读 Code Review Agent", "scope": ["PR review"], "desired_depth": "applied",
        "starting_point": "我会 Python", "outcome_purpose": "interview", "constraints": ["只读"],
        "project_context": "已有旅行 Agent"}}


def goal_output():
    return {"schema_version": 1, "target_summary": "代码审查", "required_requirements": [
        {"text": "结论关联代码依据", "origin": "inferred_required", "source_refs": ["goal.target"], "rationale": "Review 需有依据"}],
        "hard_constraints": [{"text": "只读", "source_refs": ["goal.constraints[0]"]}],
        "learner_claims": [{"text": "会 Python", "source_refs": ["goal.starting_point"]}],
        "clarification_questions": [], "status": "ready"}


def model_response(*, finish="stop", usage=True, model="deepseek-flash"):
    value = {"model": model, "choices": [{"message": {"content": json.dumps(goal_output(), ensure_ascii=False)},
        "finish_reason": finish}]}
    if usage:
        value["usage"] = {"prompt_tokens": 17, "completion_tokens": 29, "total_tokens": 46}
    return httpx.Response(200, json=value)


def invoke(external, settings, handler, attempt="synthetic-attempt"):
    external._calls.active_dispatch["attempt_id"] = attempt
    provider = external.provider(settings, "synthetic-new-run", transport=httpx.MockTransport(handler))
    return provider.generate_structured(purpose="planning.goal_requirement_analysis", payload=goal_payload(),
        schema_name="GoalRequirementProfileV1", run_id="synthetic-new-run", attempt_id=attempt)


def test_unsigned_template_never_authorizes_and_construction_is_zero_dispatch(owned):
    _settings, options, grant = owned
    assert not list(options["model_ledger"].glob("*.json"))
    unsigned = deepcopy(grant)
    unsigned["owner_approved"] = False
    path = options["authorization"]
    with pytest.raises(ValidationAppError):
        ext.AcceptanceExternal(**(options | {"authorization_sha256": save(path, unsigned)}))
    assert not list(options["model_ledger"].glob("*.json"))
    assert not (options["evidence_dir"] / "external-metadata").exists()


@pytest.mark.parametrize("field,value", [
    ("residual_cash_risk_accepted", False), ("helper_sha256", "0" * 64), ("packet_hash", "0" * 64),
    ("global_model_cap", True), ("global_search_cap", 0), ("actions", ["preflight", "execute", "retry"]),
    ("actions", ["execute", "execute"]), ("acceptance_id", "old-historic-identity"),
    ("issued_at", (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()),
    ("request_options", {}), ("request_plan", {"model_requests": 10}),
])
def test_fresh_exact_owner_grant_required(owned, field, value):
    _settings, options, grant = owned
    changed = grant | {field: value}
    with pytest.raises(ValidationAppError):
        ext.AcceptanceExternal(**(options | {"authorization_sha256": save(options["authorization"], changed)}))


def test_official_preflight_is_two_new_bound_gets_and_separately_reviewed_price(owned):
    settings, options, _grant = owned
    external, calls = ready(owned)
    assert len(calls) == 2
    assert calls[0].method == calls[1].method == "GET"
    assert "authorization" not in calls[0].headers
    assert calls[1].headers["authorization"] == "Bearer " + settings.llm_api_key
    rows = ext.ledger_snapshot(options["evidence_dir"] / "external-metadata")
    assert len(rows) == 2 and all(r[1]["status"] == "succeeded" for r in rows)
    assert external._pricing()["estimate_only"] is True
    assert external._pricing()["input_peak_per_million"] == "1"
    with pytest.raises(ValidationAppError):
        external.preflight(settings, transport=metadata(calls))
    assert len(calls) == 2


def test_price_or_balance_hash_replacement_and_config_secret_change_prevent_dispatch(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    with pytest.raises(ValidationAppError):
        external.provider(replace(settings, llm_api_key="changed-key"), "synthetic-new-run")
    (options["evidence_dir"] / "external-price-source.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValidationAppError):
        external.check()


def test_actual_provider_options_exact_bytes_and_append_only_global_unknown_history(owned):
    settings, options, _grant = owned
    for prefix, value in (("request", {"number": 1, "acceptance_id": "historical-unknown", "attempt_id": "old"}),
        ("result", {"number": 1, "unknown": True, "status": "reconciliation_required"})):
        save(options["model_ledger"] / f"{prefix}-01.json", value)
    historic = {p.name: sha(p) for p in options["model_ledger"].glob("*.json")}
    external, _calls = ready(owned)
    sent = []
    def respond(request):
        sent.append(request)
        return model_response()
    result = invoke(external, settings, respond)
    assert isinstance(result, LLMResult) and len(sent) == 1
    wire = json.loads(sent[0].content)
    assert wire["thinking"] == {"type": "disabled"} and wire["model"] == "deepseek-flash" and wire["max_tokens"] == 4096
    row = ext.ledger_snapshot(options["model_ledger"])[1]
    assert row[0]["message_utf8_bytes"] == len(ext._encoded(wire["messages"])) <= 32768
    assert row[0]["body_sha256"] == hashlib.sha256(sent[0].content).hexdigest()
    assert row[0]["actor_id"] == "synthetic-actor" and row[0]["project_id"] == "synthetic-project"
    assert row[0]["manifest_hash"] == options["packet"]["manifest"]["manifest_hash"]
    assert row[1]["usage"] == {"prompt_tokens": 17, "completion_tokens": 29, "total_tokens": 46}
    assert row[1]["peak_cash_estimate"] == "0.000075" and row[1]["estimate_only"] is True
    assert all(sha(options["model_ledger"] / name) == digest for name, digest in historic.items())
    assert settings.llm_api_key not in "".join(p.read_text(encoding="utf-8") for p in options["model_ledger"].glob("*.json"))
    with pytest.raises(LLMNotDispatchedError):
        invoke(external, settings, lambda _r: pytest.fail("purpose count must prevent dispatch"), "new-attempt")
    external.close()


@pytest.mark.parametrize("finish,usage,model,reason", [
    ("stop", False, "deepseek-flash", "usage_untrusted"),
    ("length", True, "deepseek-flash", "provider_output_truncated"),
    ("stop", True, "changed-model", "model_identity_invalid"),
])
def test_no_usage_length_or_changed_model_persists_stop_and_blocks_cold_process(owned, finish, usage, model, reason):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sent = []
    result = invoke(external, settings, lambda request: (sent.append(request), model_response(finish=finish, usage=usage, model=model))[1])
    assert isinstance(result, LLMFailure) and result.error_class == reason and len(sent) == 1
    record = ext.ledger_snapshot(options["model_ledger"])[0][1]
    assert record["status"] == "failed"
    assert record["usage"] is None if not usage else record["usage"]["total_tokens"] == 46
    if finish == "length":
        assert record["finish_reason"] == "length"
    assert (options["evidence_dir"] / "STOP.json").exists()
    cold = ext.AcceptanceExternal(**options)
    with pytest.raises(ValidationAppError):
        cold.check()
    external.close()


def test_transport_timeout_consumed_as_unknown_without_retry(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sent = []
    def lost(request):
        sent.append(request)
        raise httpx.ReadTimeout("synthetic lost reply")
    result = invoke(external, settings, lost)
    assert isinstance(result, LLMFailure) and result.dispatch_unknown and result.retryable is False
    receipt = ext.ledger_snapshot(options["model_ledger"])[0][1]
    assert receipt["unknown"] is True and receipt["status"] == "reconciliation_required" and receipt["usage"] is None
    with pytest.raises(ValidationAppError):
        ext.AcceptanceExternal(**options).check()
    assert len(sent) == 1
    external.close()


@pytest.mark.parametrize("change", ["large", "model", "thinking", "output", "destination"])
def test_exact_wire_guard_before_global_reservation(owned, change):
    settings, options, _grant = owned
    sent = []
    external, _calls = ready(owned)
    batch = external.provider(settings, "synthetic-new-run", transport=httpx.MockTransport(lambda r: sent.append(r)))
    batch.active = {"purpose": "planning.goal_requirement_analysis", "schema_name": "GoalRequirementProfileV1",
        "payload": goal_payload(), "attempt_id": "wire-attempt"}
    external._calls.active_dispatch["attempt_id"] = "wire-attempt"
    body = {"model": "deepseek-flash", "max_tokens": 4096, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]}
    url = "https://api.deepseek.com/chat/completions"
    if change == "large":
        body["messages"][1]["content"] = "汉" * 11000
    elif change == "model":
        body["model"] = "deepseek-other"
    elif change == "thinking":
        body["thinking"] = {"type": "enabled"}
    elif change == "output":
        body["max_tokens"] = 8192
    else:
        url = "https://wrong.example/chat/completions"
    with pytest.raises(LLMNotDispatchedError):
        batch.port.client.post(url, json=body)
    assert not sent and not list(options["model_ledger"].glob("request-*.json"))
    external.close()


def query():
    return ResourceQuery(scope=AuthContext("synthetic-actor", "session", datetime.now(timezone.utc), ("synthetic-project",)),
        node_keys=(), preference=ResourcePreference(PreferenceScope.SYSTEM, "system"), limit=5,
        extra={"project_id": "synthetic-project", "query": "agent guide"})


def candidate():
    return ResourceRecord(resource_id="synthetic-resource", project_id="synthetic-project", url="https://github.com/fixture/course",
        title="Agent guide", media_type=MediaType.TEXT, language="en", provenance=ResourceProvenance.SEARCH_CANDIDATE,
        verification_status=ResourceVerificationStatus.UNVERIFIED, discovery={"source": "github", "repo": {
            "owner": "fixture", "name": "course", "default_branch": "main"}})


def file_response(path, text):
    return httpx.Response(200, headers={"content-type": "application/json"}, json={"type": "file", "path": path,
        "sha": "a" * 40, "size": len(text.encode()), "encoding": "base64", "content": base64.b64encode(text.encode()).decode()})


def test_actual_github_tavily_and_body_adapters_share_bound_quota_without_retaining_body(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sent = []
    text = "Transient body sentinel: learn agent examples, never persist whole source."
    def github(request):
        sent.append(request)
        if request.url.path == "/search/repositories":
            return httpx.Response(200, json={"items": []})
        if request.url.path.endswith("/readme"):
            return file_response("README.md", "[Lesson](lesson.md)")
        assert request.url.path.endswith("/contents/lesson.md")
        return file_response("lesson.md", text)
    def web(request):
        sent.append(request)
        return httpx.Response(200, json={"results": [], "usage": {"credits": 1}})
    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(github), web_transport=httpx.MockTransport(web))
    assert ports.github.find(query()) == []
    assert ports.web.find(query()) == []
    body = ports.body_reader.read(candidate(), paths=("lesson.md",), max_bytes=65536)
    assert body.status == "succeeded" and body.chunks[0]["text"] == text
    body.close()
    assert not body.chunks and len(sent) == 4
    assert len(ext.ledger_snapshot(options["search_ledger"])) == 2
    assert len(ext.ledger_snapshot(options["evidence_dir"] / "external-body-http")) == 2
    assert ext.ledger_snapshot(options["evidence_dir"] / "external-body-operations")[0][1]["status"] == "succeeded"
    retained = "".join(path.read_text(encoding="utf-8") for path in options["evidence_dir"].rglob("*.json"))
    assert text not in retained and settings.tavily_api_key not in retained


def test_tavily_usage_missing_stops_even_when_adapter_returns_candidates(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    ports = external.resource_ports(settings, web_transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={"results": []})))
    ports.web.find(query())
    receipt = ext.ledger_snapshot(options["search_ledger"])[0][1]
    assert receipt["status"] == "failed" and receipt["usage"] is None
    assert (options["evidence_dir"] / "STOP.json").exists()


def test_known_unread_body_and_known_nonstop_search_failures_remain_consumed(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sent = []
    def github(request):
        sent.append(request)
        if request.url.path == "/search/repositories":
            return httpx.Response(404, json={"message": "known missing"})
        if request.url.path.endswith("/readme"):
            return file_response("README.md", "[Lesson](lesson.md)")
        return httpx.Response(404, json={"message": "chapter missing"})
    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(github),
        web_transport=httpx.MockTransport(lambda _r: httpx.Response(400, json={"detail": "known failed"})))
    body = ports.body_reader.read(candidate(), paths=("lesson.md",), max_bytes=65536)
    assert body.status == "unread"
    assert not (options["evidence_dir"] / "STOP.json").exists()
    github_result, web_result = ports.github.find(query()), ports.web.find(query())
    assert not github_result.stop_required and not web_result.stop_required
    assert len(ext.ledger_snapshot(options["search_ledger"])) == 2
    external.check()
    assert len(sent) == 3 and not (options["evidence_dir"] / "STOP.json").exists()


def test_reviewed_replacement_metadata_cannot_claim_original_official_receipts(owned):
    settings, options, _grant = owned
    external = ext.AcceptanceExternal(**options)
    external.preflight(settings, transport=metadata([]))
    balance_path = options["evidence_dir"] / "external-balance.json"
    balance = json.loads(balance_path.read_bytes())
    balance["balance_infos"][0]["total_balance"] = "9000000"
    save(balance_path, balance)
    review = external.price_review_request() | {"approved": True, "input_peak_per_million": "1",
        "output_peak_per_million": "2", "reviewed_at": datetime.now(timezone.utc).isoformat()}
    path = options["evidence_dir"] / "synthetic-replacement-review.json"
    with pytest.raises(ValidationAppError):
        external.approve_price(path, sha256=save(path, review))


def test_missing_global_result_blocks_cold_dispatch_and_keeps_intent(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    intent = options["model_ledger"] / "request-01.json"
    digest = save(intent, {"number": 1, "acceptance_id": options["packet"]["acceptance_id"]})
    with pytest.raises(ValidationAppError):
        ext.AcceptanceExternal(**options).provider(settings, "synthetic-new-run")
    assert sha(intent) == digest and not list(options["model_ledger"].glob("result-*.json"))


def test_ledger_os_lock_excludes_a_second_process(owned):
    _settings, options, _grant = owned
    folder = options["model_ledger"]
    root = Path(__file__).resolve().parents[3]
    code = "from scripts.planning_v2_acceptance_external import _ledger_lock\nimport sys\nwith _ledger_lock(sys.argv[1]): pass\n"
    with ext._ledger_lock(folder):
        child = subprocess.run([sys.executable, "-c", code, str(folder)], cwd=root,
            env=os.environ | {"PYTHONPATH": str(root / "backend") + os.pathsep + str(root)}, capture_output=True, text=True)
    assert child.returncode != 0 and "global_ledger_busy_or_unwritable" in child.stderr


def test_second_run_or_foreign_actor_scope_never_dispatches(owned):
    settings, _options, _grant = owned
    external, _calls = ready(owned)
    with pytest.raises(ValidationAppError):
        external.bind_run("second-run", "synthetic-project", "synthetic-actor")
    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(lambda _r: pytest.fail("foreign actor")))
    wrong = replace(query(), scope=AuthContext("foreign", "session", datetime.now(timezone.utc), ("synthetic-project",)))
    result = ports.github.find(wrong)
    assert result.status == "not_dispatched" and result.requests == 0 and result.stop_required


def test_reader_success_envelope_never_persists_raw_payload_before_native_projection(owned, monkeypatch):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sentinel = "Transient Reader source sentinel must never enter helper artifacts"
    provider = external.provider(settings, "synthetic-new-run", transport=httpx.MockTransport(lambda _r:
        httpx.Response(200, json={"model": "deepseek-flash", "usage": {"prompt_tokens": 17,
            "completion_tokens": 29, "total_tokens": 46}, "choices": [{"message": {
                "content": json.dumps({"untrusted_extra": sentinel})}, "finish_reason": "stop"}]})))
    external._calls.active_dispatch["attempt_id"] = "reader-attempt"
    def adapter_boundary(**_kwargs):
        # Simulate an adapter-valid envelope before the separate native PG
        # projection. This test intentionally does not claim domain validation.
        provider.port.client.post("https://api.deepseek.com/chat/completions", json={
            "model": "deepseek-flash", "max_tokens": 1024, "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "s"},
                {"role": "user", "content": "source: " + sentinel}]})
        return LLMResult({"untrusted_extra": sentinel}, "deepseek-flash", "openai_compatible",
            input_tokens=17, output_tokens=29, finish_reason="stop", diagnostics={"raw": sentinel})
    monkeypatch.setattr(provider.port, "generate_structured", adapter_boundary)
    result = provider.generate_structured(purpose="planning.research_reader", payload={"source": sentinel},
        schema_name="ResearchReaderV2", run_id="synthetic-new-run", attempt_id="reader-attempt")
    assert isinstance(result, LLMResult)
    artifact = json.loads((options["evidence_dir"] / "external-model-01-provider.json").read_bytes())
    assert artifact["payload_retained"] is False and artifact["payload_sha256"]
    assert not (options["evidence_dir"] / "external-model-01-response.body").exists()
    assert sentinel not in "".join(path.read_text(encoding="utf-8") for path in options["evidence_dir"].rglob("*.json"))
    assert ext.ledger_snapshot(options["model_ledger"])[0][0]["max_tokens"] == 1024
    external.close()


def test_global_cap_includes_historical_usage_and_model_dispatch_has_intent_first(owned):
    settings, options, grant = owned
    grant["global_model_cap"] = 1
    options = options | {"authorization_sha256": save(options["authorization"], grant)}
    save(options["model_ledger"] / "request-01.json", {"number": 1, "acceptance_id": "historic"})
    save(options["model_ledger"] / "result-01.json", {"number": 1, "unknown": False})
    external, _calls = ready((settings, options, grant))
    with pytest.raises(LLMNotDispatchedError):
        invoke(external, settings, lambda _r: pytest.fail("global cap must prevent HTTP"))
    assert len(ext.ledger_snapshot(options["model_ledger"])) == 1
    assert json.loads((options["evidence_dir"] / "STOP.json").read_bytes())["unknown"] is False


def test_model_request_is_durable_before_mock_transport_and_parent_binding_required(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    def respond(_request):
        request = options["model_ledger"] / "request-01.json"
        assert request.exists() and not (options["model_ledger"] / "result-01.json").exists()
        value = json.loads(request.read_bytes())
        assert value["parent_attempt_id"] == "synthetic-attempt" and value["parent_reserved_hash"]
        return model_response()
    assert isinstance(invoke(external, settings, respond), LLMResult)
    external.close()


@pytest.mark.parametrize("source", ["github", "tavily"])
def test_resource_global_admission_rejection_is_known_zero_http(owned, source):
    settings, options, grant = owned
    grant["global_search_cap"] = 1
    options = options | {"authorization_sha256": save(options["authorization"], grant)}
    save(options["search_ledger"] / "request-01.json", {"number": 1, "acceptance_id": "historic"})
    save(options["search_ledger"] / "result-01.json", {"number": 1, "unknown": False})
    external, _calls = ready((settings, options, grant))
    forbidden = httpx.MockTransport(lambda _r: pytest.fail("global search admission must make HTTP zero"))
    ports = external.resource_ports(settings, github_transport=forbidden, web_transport=forbidden)
    result = (ports.github if source == "github" else ports.web).find(query())
    assert result.status == "not_dispatched" and result.requests == result.bytes_read == 0
    assert len(ext.ledger_snapshot(options["search_ledger"])) == 1
    assert json.loads((options["evidence_dir"] / "STOP.json").read_bytes())["unknown"] is False


def test_pinned_github_explicit_not_dispatched_receipt_never_becomes_unknown(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    def rejected(_request):
        raise ext.GitHubNotDispatchedError("synthetic rejected public destination")
    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(rejected))
    result = ports.github.find(query())
    assert result.status == "not_dispatched" and result.requests == 0
    receipt = ext.ledger_snapshot(options["search_ledger"])[0][1]
    assert receipt["unknown"] is False and receipt["dispatched"] is False
