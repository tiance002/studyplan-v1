"""W5 actual Provider/MockTransport decoding boundary; no external requests."""
import gzip
import hashlib
import json
import os
import zlib
from pathlib import Path

import httpx
import pytest
import zstandard
from app.core.errors import ValidationAppError
from app.ports.llm import LLMFailure, LLMResult

from backend.tests.unit.test_research_reader_provider import reader_output, reader_payload
from backend.tests.unit.test_w5_acceptance_external import (
    invoke,
    model_response,
    ready,
)
from backend.tests.unit.test_w5_acceptance_external import (
    no_network as no_network,
)
from backend.tests.unit.test_w5_acceptance_external import (
    owned as owned,
)
from scripts import planning_v2_acceptance_external as ext


def compressed(raw, coding):
    if coding == "gzip":
        return gzip.compress(raw)
    if coding == "deflate":
        return zlib.compress(raw)
    if coding == "raw-deflate":
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        return compressor.compress(raw) + compressor.flush()
    if coding in {"zstd", "zstd-unknown"}:
        return zstandard.ZstdCompressor(write_content_size=coding == "zstd").compress(raw)
    return raw


def wire_response(raw, coding, status=200):
    # Supplying content would make the constructor decode before the transport.
    header = "deflate" if coding == "raw-deflate" else "zstd" if coding == "zstd-unknown" else coding
    return httpx.Response(status, headers={"content-encoding": header} if header else {},
                          stream=httpx.ByteStream(raw))


@pytest.mark.parametrize("coding", [None, "identity", "gzip", "deflate", "raw-deflate", "zstd", "zstd-unknown"])
def test_provider_and_audit_share_one_decoded_response(owned, coding):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    decoded = model_response().content
    wire = compressed(decoded, coding)
    sent = []
    result = invoke(external, settings, lambda r: (sent.append(r), wire_response(wire, coding))[1])
    assert isinstance(result, LLMResult) and len(sent) == 1
    assert result.payload == json.loads(json.loads(decoded)["choices"][0]["message"]["content"])
    request, receipt = ext.ledger_snapshot(options["model_ledger"])[0]
    assert receipt["status"] == "succeeded" and receipt["unknown"] is False
    assert receipt["usage"] == {"prompt_tokens": 17, "completion_tokens": 29, "total_tokens": 46}
    capture = json.loads((options["evidence_dir"] / "external-model-01-response.json").read_bytes())
    assert capture["response_sha256"] == hashlib.sha256(wire).hexdigest()
    assert capture["decoded_sha256"] == hashlib.sha256(decoded).hexdigest()
    assert capture["decoded_bytes"] == len(decoded)
    assert capture["request_sha256"] == hashlib.sha256(ext._encoded(request)).hexdigest()
    assert receipt["decoded_sha256"] == capture["decoded_sha256"]
    assert (options["evidence_dir"] / "external-model-01-response.body").read_bytes() == wire
    external.close()


def test_saved_scenario_a_offline_replay_only(owned):
    """Local opt-in evidence; never copy private responses into test fixtures."""
    configured = os.environ.get("W5_OFFLINE_SAVED_ACCEPTANCE")
    if not configured:
        pytest.skip("NOT RUN: private saved response packet not supplied")
    source = Path(configured).resolve()
    assert source.is_relative_to(Path(__file__).resolve().parents[3] / "var")
    from app.application.capability_planning import CapabilityPlanner
    from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
    from app.domain.planning.capabilities import CapabilityPlan
    from app.domain.planning.intent import goal_spec_from_payload

    originals = {p.name: p.read_bytes() for p in (
        source / "external-model-190-response.body", source / "external-model-191-response.body",
        source / "review-packet-goal_analysis.json", source / "prepared.json", source / "STOP.json")}
    goal = goal_spec_from_payload(json.loads(originals["prepared.json"])["goal_spec"])
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sent = []

    def respond(request):
        sent.append(request)
        purpose = json.loads(request.content)["messages"][1]["content"]
        if "planning.goal_requirement_analysis" in purpose:
            return wire_response(originals["external-model-190-response.body"], None)
        # Original encoding header was not saved. This explicit mock declaration
        # is an offline fixture, not a reconstruction of the historical receipt.
        return wire_response(originals["external-model-191-response.body"], "zstd")

    provider = external.provider(settings, "synthetic-new-run", transport=httpx.MockTransport(respond))
    external._calls.active_dispatch["attempt_id"] = "offline-goal"
    profile = GoalRequirementAnalyzer(provider).analyze(goal, run_id="synthetic-new-run", attempt_id="offline-goal")
    assert profile.to_payload() == json.loads(originals["review-packet-goal_analysis.json"])["state"]["profile"]
    external._calls.active_dispatch["attempt_id"] = "offline-capability"
    plan = CapabilityPlanner(provider).plan(profile, run_id="synthetic-new-run", attempt_id="offline-capability")
    assert isinstance(plan, CapabilityPlan) and len(sent) == 2
    rows = ext.ledger_snapshot(options["model_ledger"])
    assert rows[1][1]["usage"] == {"prompt_tokens": 4620, "completion_tokens": 1312, "total_tokens": 5932}
    assert rows[1][1]["status"] == "succeeded"  # Synthetic temp ledger ONLY.
    assert originals == {name: (source / name).read_bytes() for name in originals}
    evidence = {"result": "OFFLINE_REPLAY_FIXTURE_PASS", "business_run_created": False, "real_requests": 0,
        "original_bytes_unchanged": True, "profile_hash": profile.profile_hash,
        "candidate_plan_hash": plan.plan_hash, "header_is_mock_declaration": True}
    (options["evidence_dir"] / "offline-replay-result.json").write_text(json.dumps(evidence), encoding="utf-8")
    external.close()


@pytest.mark.parametrize("coding,over", [(None, False), (None, True), ("zstd-unknown", False), ("zstd-unknown", True)])
def test_exact_wire_or_decoded_capacity_boundary(owned, coding, over):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    decoded = model_response().content
    decoded += b" " * (524288 + int(over) - len(decoded))
    raw = compressed(decoded, coding)
    result = invoke(external, settings, lambda _r: wire_response(raw, coding))
    receipt = ext.ledger_snapshot(options["model_ledger"])[0][1]
    if over:
        assert isinstance(result, LLMFailure) and not result.dispatch_unknown
        assert receipt["status"] == "failed" and not receipt["unknown"]
    else:
        assert isinstance(result, LLMResult) and receipt["decoded_bytes"] == 524288
        assert receipt["status"] == "succeeded"
    external.close()


@pytest.mark.parametrize("change,reason", [("model", "model_identity_invalid"), ("length", "provider_output_truncated"),
    ("missing-encoding", "provider_invalid_envelope")])
def test_compressed_identity_and_finish_checks_remain_strict(owned, change, reason):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    raw = compressed(model_response(model="different" if change == "model" else "deepseek-flash",
        finish="length" if change == "length" else "stop").content, "zstd")
    result = invoke(external, settings, lambda _r: wire_response(raw, None if change == "missing-encoding" else "zstd"))
    assert isinstance(result, LLMFailure) and result.error_class == reason and not result.dispatch_unknown
    assert ext.ledger_snapshot(options["model_ledger"])[0][1]["status"] == "failed"
    external.close()


def test_transport_loss_after_partial_encoded_bytes_remains_unknown(owned):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    sent = []

    class Lost(httpx.SyncByteStream):
        def __iter__(self):
            yield compressed(model_response().content, "zstd")[:8]
            raise httpx.ReadError("synthetic transient transport loss")

    result = invoke(external, settings, lambda r: (sent.append(r), httpx.Response(200,
        headers={"content-encoding": "zstd"}, stream=Lost()))[1])
    assert isinstance(result, LLMFailure) and result.dispatch_unknown and len(sent) == 1
    receipt = ext.ledger_snapshot(options["model_ledger"])[0][1]
    assert receipt["status"] == "reconciliation_required" and receipt["usage"] is None and receipt["unknown"]
    with pytest.raises(ValidationAppError):
        invoke(external, settings, lambda _r: pytest.fail("unknown must not redispatch"), attempt="other")
    external.close()


@pytest.mark.parametrize("kind", ["truncated-gzip", "truncated-deflate", "truncated-zstd", "corrupt-zstd",
    "unsupported", "wrong-declaration", "multiple-codings", "zstd-extra-frame", "gzip-trailing",
    "known-size-bomb", "unknown-size-bomb", "gzip-bomb", "deflate-bomb",
    "empty-zstd", "empty-truncated-zstd", "empty-trailing-zstd", "empty-concat-zstd"])
def test_complete_response_decode_rejection_is_known_and_never_redispatched(owned, kind):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    decoded = model_response().content
    coding, raw = "zstd", compressed(decoded, "zstd")
    if kind.startswith("truncated-"):
        coding = kind.removeprefix("truncated-")
        raw = compressed(decoded, coding)[:-4]
    elif kind == "corrupt-zstd":
        raw = b"not a zstandard frame"
    elif kind == "unsupported":
        coding, raw = "br", decoded  # Brotli is not installed in this runtime.
    elif kind == "wrong-declaration":
        coding, raw = "gzip", decoded
    elif kind == "multiple-codings":
        coding = "gzip, zstd"
    elif kind == "zstd-extra-frame":
        raw += raw
    elif kind == "gzip-trailing":
        coding, raw = "gzip", compressed(decoded, "gzip") + b"trailing"
    elif kind.endswith("bomb"):
        decoded = b"x" * 2_000_000
        coding = {"known-size-bomb": "zstd", "unknown-size-bomb": "zstd-unknown",
                  "gzip-bomb": "gzip", "deflate-bomb": "deflate"}[kind]
        raw = compressed(decoded, coding)
    elif kind.startswith("empty-"):
        raw = compressed(b"", "zstd")
        if kind == "empty-truncated-zstd":
            raw = raw[:-1]
        elif kind == "empty-trailing-zstd":
            raw += b"junk"
        elif kind == "empty-concat-zstd":
            raw += compressed(decoded, "zstd")
    sent = []
    result = invoke(external, settings, lambda r: (sent.append(r), wire_response(raw, coding))[1])
    assert isinstance(result, LLMFailure) and result.error_class.startswith("model_response_")
    assert not result.dispatch_unknown and len(sent) == 1
    request, receipt = ext.ledger_snapshot(options["model_ledger"])[0]
    assert receipt["status"] == "failed" and receipt["unknown"] is False and receipt["usage"] is None
    assert request["number"] == receipt["number"] == 1
    assert not (options["evidence_dir"] / "external-model-01-response.body").exists()
    assert json.loads((options["evidence_dir"] / "STOP.json").read_bytes())["unknown"] is False
    with pytest.raises(ValidationAppError):
        invoke(external, settings, lambda _r: pytest.fail("STOP must deny another identity"), attempt="another")
    assert len(sent) == len(ext.ledger_snapshot(options["model_ledger"])) == 1
    external.close()


@pytest.mark.parametrize("usage", [None, {"prompt_tokens": True, "completion_tokens": 29, "total_tokens": 30},
    {"prompt_tokens": "17", "completion_tokens": 29, "total_tokens": 46},
    {"prompt_tokens": 17, "completion_tokens": 29, "total_tokens": 45},
    {"prompt_tokens": 17, "completion_tokens": 4097, "total_tokens": 4114}])
def test_compression_does_not_relax_usage_trust(owned, usage):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    envelope = model_response().json()
    envelope["usage"] = usage
    raw = compressed(json.dumps(envelope).encode(), "zstd")
    result = invoke(external, settings, lambda _r: wire_response(raw, "zstd"))
    assert isinstance(result, LLMFailure) and result.error_class == "usage_untrusted"
    receipt = ext.ledger_snapshot(options["model_ledger"])[0][1]
    assert receipt["usage"] is None and receipt["status"] == "failed" and not receipt["unknown"]
    external.close()


@pytest.mark.parametrize("echo_secret", [False, True])
def test_compressed_reader_body_and_secret_stay_transient(owned, echo_secret):
    settings, options, _grant = owned
    external, _calls = ready(owned)
    payload = reader_payload()
    payload["rules_version"] = "research_comparison_v2"
    output = reader_output(payload)
    chunk = payload["chunks"][0]
    output["quality_evidence"] = {dimension: {"category": "adequate", "rationale": "Synthetic bounded example",
        "evidence_refs": [{"chunk_id": chunk["chunk_id"], "content_hash": chunk["content_hash"]}]}
        for dimension in ("continuity", "beginner_fit", "examples", "version_fit")}
    if echo_secret:
        output["outcomes"][0]["rationale"] = settings.llm_api_key
    envelope = {"model": "deepseek-flash", "usage": {"prompt_tokens": 17, "completion_tokens": 29, "total_tokens": 46},
                "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]}
    decoded = json.dumps(envelope).encode()
    raw = compressed(decoded, "zstd")
    external._calls.active_dispatch["attempt_id"] = "reader-attempt"
    provider = external.provider(settings, "synthetic-new-run", transport=httpx.MockTransport(lambda _r:
        wire_response(raw, "zstd")))
    result = provider.generate_structured(purpose=ext.READER, payload=payload,
        schema_name="ResearchReaderV2", run_id="synthetic-new-run", attempt_id="reader-attempt")
    assert isinstance(result, LLMFailure if echo_secret else LLMResult)
    if echo_secret:
        assert result.error_class == "model_response_secret_echo" and not result.dispatch_unknown
    for path in options["evidence_dir"].rglob("*"):
        if path.is_file():
            retained = path.read_bytes()
            assert decoded not in retained and raw not in retained
            assert payload["chunks"][0]["text"].encode() not in retained
            assert settings.llm_api_key.encode() not in retained
    assert not (options["evidence_dir"] / "external-model-01-response.body").exists()
    external.close()
