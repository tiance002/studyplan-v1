"""Synthetic official registry and MockTransport; no online technical acceptance."""
import base64
import hashlib
import json
from dataclasses import asdict, replace

import httpx
import pytest
from app.application.capability_planning import CapabilityPlanner
from app.application.domain_verification import DomainVerifier
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.capabilities import (
    CapabilityPlanValidator,
    DomainVerificationEvidence,
    verification_input_hash,
)
from app.domain.planning.capability_policy import CapabilityDefinition, LearningOutcome
from app.domain.planning.domain_verification import (
    DomainApproval,
    TrustedDomainSource,
    bind_domain_approval,
    public_outcomes,
    reader_authority,
    verification_session_hash,
)
from app.domain.planning.research_reader import (
    READER_PURPOSE,
    READER_SCHEMA,
    validate_reader_input,
    validate_reader_output,
)
from app.domain.planning.resource_research import ResearchBudget, ResearchSession
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.infrastructure.resources.teaching_body import GitHubTeachingBody
from app.ports.llm import LLMFailure, LLMResult

from backend.tests.unit.test_capability_planning import Port, cap, profile, wire
from backend.tests.unit.test_research_reader_provider import reader_output, reader_payload
from backend.tests.unit.test_resource_research import SCOPE

TEXT = "Public synthetic ROS2 action lifecycle example, cancellation and result handling."
SHA = hashlib.sha256(TEXT.encode()).hexdigest()


def source(*, public=True):
    definitions = (CapabilityDefinition("ros2.action", "ROS2 Action", (
        LearningOutcome("ros2.action.lifecycle", "解释ROS2 Action目标、反馈、取消与结果的公开生命周期"),), (), "applied", ()),
        CapabilityDefinition("ros2.topic", "ROS2 Topic", (
        LearningOutcome("ros2.topic.exchange", "解释ROS2 Topic的公开发布订阅行为"),), (), "applied", ()))
    return TrustedDomainSource("ros2_official", "fixture-v1", "https://github.com/ros2/design", "c" * 40,
        "docs/actions.md", "b" * 40, SHA, definitions,
        tuple(o.outcome_id for d in definitions for o in d.learning_outcomes) if public else (),
        ("Synthetic official response; no live validation or runtime execution",))


def domain_inputs(*, public=True, fixture=False):
    """Shared frozen Item2 fixture; approval is explicitly server-injected synthetic authority."""
    p = profile("学习ROS2 Action；PRIVATE_PROJECT must not enter public queries")
    s = source(public=public)
    digest = content_hash(asdict(s))
    ev = DomainVerificationEvidence("domain_" + content_hash({"input_hash": verification_input_hash(p), "source_hash": digest}),
        verification_input_hash(p), ("domain-source:" + s.source_id + "@" + s.version + "#" + digest,), s.limitations,
        "fixture" if fixture else "source_verification", s.capabilities)
    if fixture:
        approval = None
    else:
        reader, _ = pinned_reader()
        result = DomainVerifier(reader, sources=(s,)).verify(p, source_id=s.source_id,
            session=verification_session(p, s), scope=SCOPE, project_id="project")
        approval = result.approval
        assert approval is not None and result.evidence == ev
    frozen = CapabilityPlanValidator().validate(wire(p, cap(p, "ros2.action")), profile=p, verification_evidence=(ev,))
    if approval is not None:
        approval = bind_domain_approval(approval, frozen)
    return p, frozen, approval, s


def payload_for(plan, approval):
    payload = reader_payload()
    payload["must_teach"] = [asdict(o) for o in plan.learning_outcomes]
    payload["learner_context"]["accepted_known"] = []
    authority = reader_authority(plan, domain_approvals=(approval,) if approval else ())
    if authority is not None:
        payload["domain_authority"] = authority
    return payload


def test_public_descriptors_are_current_frozen_outcomes_and_need_server_approval():
    p, plan, approval, _ = domain_inputs()
    assert public_outcomes(plan) == {}
    assert public_outcomes(plan, domain_approvals=(approval,)) == {o.outcome_id: o.text for o in plan.learning_outcomes}
    assert "ros2.topic.exchange" not in public_outcomes(plan, domain_approvals=(approval,))
    assert "PRIVATE_PROJECT" not in repr(public_outcomes(plan, domain_approvals=(approval,)))
    assert reader_authority(plan) is None
    assert reader_authority(plan, domain_approvals=(approval,))["plan"]["plan_hash"] == plan.plan_hash


def test_source_verification_label_without_approval_is_rejected_before_capability_dispatch():
    p, plan, approval, _ = domain_inputs()
    port = Port(LLMResult(wire(p, cap(p, "ros2.action")), "test", "fixture"))
    result = CapabilityPlanner(port).plan(p, run_id="run", attempt_id="one", verification_evidence=plan.verification_evidence)
    assert isinstance(result, LLMFailure) and not port.calls
    accepted = CapabilityPlanner(port).plan(p, run_id="run", attempt_id="two", verification_evidence=plan.verification_evidence,
                                           domain_approvals=(approval,))
    assert accepted.plan_hash == plan.plan_hash and len(port.calls) == 1


def test_fixture_is_explicit_offline_only_and_cannot_reach_real_provider_boundary():
    _, plan, _, _ = domain_inputs(fixture=True)
    assert public_outcomes(plan) == {} and reader_authority(plan) is None
    authority = reader_authority(plan, allow_fixture_domains=True)
    payload = reader_payload()
    payload["must_teach"] = [asdict(o) for o in plan.learning_outcomes]
    payload["learner_context"]["accepted_known"] = []
    payload["domain_authority"] = authority
    assert validate_reader_input(payload, READER_SCHEMA, allow_fixture_domains=True)
    assert not validate_reader_input(payload, READER_SCHEMA)
    client = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture")
    assert isinstance(client.preflight(purpose=READER_PURPOSE, payload=payload, schema_name=READER_SCHEMA), LLMFailure)


def test_approved_extension_reader_preserves_exact_output_and_single_provider_request():
    _, plan, approval, _ = domain_inputs()
    payload = payload_for(plan, approval)
    assert validate_reader_input(payload, READER_SCHEMA, domain_approvals=(approval,))
    assert validate_reader_output(reader_output(payload), payload, domain_approvals=(approval,)) == reader_output(payload)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reader_output(payload))},
            "finish_reason": "stop"}], "usage": {"prompt_tokens": 20, "completion_tokens": 30}})
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture",
        client=httpx.Client(transport=httpx.MockTransport(handler)), domain_approvals=(approval,))
    result = provider.generate_structured(purpose=READER_PURPOSE, payload=payload, schema_name=READER_SCHEMA,
        run_id="run", attempt_id="one")
    assert isinstance(result, LLMResult) and len(calls) == 1


@pytest.mark.parametrize("change", ["source", "version", "profile", "input_hash", "id", "text", "plan_hash", "outside_plan", "self_registry"])
def test_reader_rejects_tampered_authority_without_dispatch(change):
    _, plan, approval, _ = domain_inputs()
    payload = payload_for(plan, approval)
    authority = payload["domain_authority"]
    evidence = authority["plan"]["verification_evidence"][0]
    if change == "source":
        evidence["source_refs"] = ["official:self-asserted"]
    elif change == "version":
        authority["approval_hashes"] = [content_hash({"forged_version": "other"})]
    elif change == "profile":
        authority["plan"]["source_goal_profile_hash"] = "f" * 64
    elif change == "input_hash":
        evidence["input_hash"] = "f" * 64
    elif change == "id":
        payload["must_teach"][0]["outcome_id"] = "ros2.action.forged"
    elif change == "text":
        payload["must_teach"][0]["text"] = "PRIVATE_PROJECT"
    elif change == "plan_hash":
        authority["plan"]["plan_hash"] = "f" * 64
    elif change == "outside_plan":
        payload["must_teach"] = [asdict(approval.source.capabilities[1].learning_outcomes[0])]
    else:
        authority["registry"] = [asdict(approval.source)]
    assert not validate_reader_input(payload, READER_SCHEMA, domain_approvals=(approval,))


def test_unapproved_public_descriptor_keeps_domain_outcomes_private():
    _, plan, approval, _ = domain_inputs(public=False)
    assert public_outcomes(plan, domain_approvals=(approval,)) == {}
    assert reader_authority(plan, domain_approvals=(approval,)) is None


def test_direct_constructed_approval_is_not_a_verified_producer_receipt():
    p, plan, _, _ = domain_inputs(fixture=True)
    with pytest.raises(ValidationAppError):
        DomainApproval(p.profile_hash, source(), replace(plan.verification_evidence[0], evidence_kind="source_verification"))


def pinned_reader(mode="ok"):
    calls = []
    def file(path, text, sha):
        return {"type": "file", "path": path, "sha": sha, "size": len(text.encode()), "encoding": "base64",
                "content": base64.b64encode(text.encode()).decode()}
    def handler(request):
        calls.append(request)
        if mode == "unknown":
            raise httpx.ReadTimeout("PRIVATE exception must not persist")
        if request.url.path.endswith("/readme"):
            data = file("README.md", "[Actions](docs/actions.md)", "a" * 40)
        else:
            data = file("docs/actions.md", TEXT if mode != "hash" else "changed", "b" * 40)
        return httpx.Response(200, headers={"Content-Type": "application/json"}, stream=httpx.ByteStream(json.dumps(data).encode()))
    return GitHubTeachingBody(transport=httpx.MockTransport(handler)), calls


def verification_session(p, source, *, budget=None):
    budget = budget or ResearchBudget()
    return ResearchSession("verify-run", verification_session_hash(p, source, budget=budget,
        actor_id=SCOPE.actor_id, project_id="project"), budget)


def test_actual_safe_adapter_producer_checks_pins_two_http_and_closes_body():
    p, frozen, expected, s = domain_inputs()
    reader, calls = pinned_reader()
    session = verification_session(p, s)
    result = DomainVerifier(reader, sources=(s,)).verify(p, source_id=s.source_id,
        session=session, scope=SCOPE, project_id="project")
    assert result.status == "verified" and result.approval.plan_hash is None
    assert bind_domain_approval(result.approval, frozen) == expected
    assert len(calls) == result.requests == 2 and session.usage["total_requests"] == 2
    assert all(dict(call.url.params) == {"ref": s.commit_sha} for call in calls)
    assert TEXT not in repr(result) and not session.snapshot().pending_count


@pytest.mark.parametrize("mode", ["hash", "unknown", "budget", "binding", "scope", "no_registry"])
def test_producer_failures_remain_bounded_and_do_not_approve(mode):
    p, _, _, s = domain_inputs()
    reader, calls = pinned_reader(mode)
    session = verification_session(p, s, budget=ResearchBudget(max_total_requests=1) if mode == "budget" else None)
    if mode == "binding":
        session.input_hash = "f" * 64
    result = DomainVerifier(reader, sources=() if mode == "no_registry" else (s,)).verify(p, source_id=s.source_id,
        session=session, scope=SCOPE, project_id="unowned" if mode == "scope" else "project")
    assert result.approval is None and result.evidence is None
    assert len(calls) <= 2 and "PRIVATE" not in repr(result)
    if mode in {"budget", "binding", "scope", "no_registry"}:
        assert not calls
        assert not session.config_hash
    if mode == "unknown":
        assert result.status == "unknown" and session.blocked and session.snapshot().pending_count == 1
        assert not DomainVerifier(reader, sources=(s,)).verify(p, source_id=s.source_id,
            session=session, scope=SCOPE, project_id="project").approval
        assert len(calls) == 1
    if mode == "no_registry":
        assert result.reason == "DOMAIN_VERIFICATION_LIVE_PENDING"


@pytest.mark.parametrize("constraint", ["禁止联网", "不得调用外部服务", "未知且不能可信分类的限制"])
def test_domain_source_verification_cannot_bypass_user_dispatch_constraints(constraint):
    p = profile("学习ROS2 Action", constraints=(constraint,))
    s = source()
    reader, calls = pinned_reader()
    session = verification_session(p, s)
    result = DomainVerifier(reader, sources=(s,)).verify(p, source_id=s.source_id, session=session, scope=SCOPE, project_id="project")
    assert result.status == "needs_verification" and not calls and result.approval is None
    assert not any(session.usage.values()) and session.snapshot().pending_count == 0


@pytest.mark.parametrize("field", ["profile_hash", "source", "evidence", "consistent_replacement"])
def test_issued_approval_marker_binds_original_content_even_if_replaced_consistently(field):
    p, plan, approval, s = domain_inputs()
    if field == "profile_hash":
        changes = {"profile_hash": "f" * 64}
    elif field == "source":
        changes = {"source": replace(s, body_sha256="f" * 64)}
    elif field == "evidence":
        changes = {"evidence": replace(approval.evidence, input_hash="f" * 64)}
    else:
        modified = replace(s, version="forged-v2")
        ev = replace(approval.evidence, source_refs=(modified.reference,), evidence_id="domain_" + content_hash({
            "input_hash": verification_input_hash(p), "source_hash": modified.source_hash}))
        changes = {"source": modified, "evidence": ev}
    with pytest.raises(ValidationAppError):
        replace(approval, **changes)


def researched_domain(*, approved=True, fixture=False, public=True, reader=None):
    from app.application.teaching_resource_research import ResourceResearcher
    from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
    from app.domain.planning.resource_gaps import extract

    from backend.tests.unit.test_resource_research import Bodies, Reader, Search, run
    p, frozen, approval, _ = domain_inputs(public=public, fixture=fixture)
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    gaps = extract(frozen, coverage)
    github, web, bodies, reader = Search(), Search([]), Bodies(), reader or Reader()
    approvals = (approval,) if approved and approval else ()
    researcher = ResourceResearcher(github=github, web=web, body_reader=bodies, llm=reader, domain_approvals=approvals)
    research, session, *_ = run((p, frozen, coverage, gaps), researcher=researcher)
    return p, frozen, approval, index, coverage, gaps, research, session, github, web, bodies, reader


def test_approved_official_fixture_flows_item2_coverage_gap_reader_curriculum_and_real_provider_mock():
    from app.domain.planning.curriculum import (
        CURRICULUM_PURPOSE,
        CURRICULUM_SCHEMA,
        prepare_curriculum,
        valid_curriculum_input,
        validate_curriculum_output,
    )

    from backend.tests.unit.test_curriculum import output
    p, frozen, approval, index, coverage, gaps, research, session, github, web, bodies, reader = researched_domain()
    assert coverage.entries[0].missing_outcomes == tuple(o.outcome_id for o in gaps.gaps[0].missing_outcomes)
    assert research.entries[0].status == "resolved" and len(reader.calls) == 1
    assert len(github.calls) == 1 and not web.calls and not bodies.produced[0].chunks
    assert "PRIVATE_PROJECT" not in repr(github.calls[0].extra) and "PRIVATE_PROJECT" not in repr(reader.calls[0]["payload"])
    ctx = prepare_curriculum(p, frozen, coverage, research, index, domain_approvals=(approval,))
    assert valid_curriculum_input(ctx.to_payload(), CURRICULUM_SCHEMA, domain_approvals=(approval,))
    assert not valid_curriculum_input(ctx.to_payload(), CURRICULUM_SCHEMA)
    raw = output(ctx)
    curriculum = validate_curriculum_output(raw, ctx.to_payload(), domain_approvals=(approval,))
    assert curriculum.status == "complete" and curriculum.to_payload()["stages"][0]["capability_ids"] == ["ros2.action"]
    assert curriculum.to_payload()["compile_context"]["domain_authority"]["plan"]["plan_hash"] == frozen.plan_hash
    assert "Synthetic official response" in repr(curriculum.to_payload()["compile_context"]["domain_authority"])
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(raw)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 40}})
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture",
        client=httpx.Client(transport=httpx.MockTransport(handler)), domain_approvals=(approval,))
    result = provider.generate_structured(purpose=CURRICULUM_PURPOSE, payload=ctx.to_payload(), schema_name=CURRICULUM_SCHEMA,
        run_id=session.run_id, attempt_id="curriculum")
    assert isinstance(result, LLMResult) and len(calls) == 1


@pytest.mark.parametrize("mode", ["unapproved", "private_descriptor", "fixture"])
def test_unapproved_domain_descriptor_makes_zero_search_body_reader_and_no_real_curriculum_dispatch(mode):
    from app.domain.planning.curriculum import CURRICULUM_PURPOSE, CURRICULUM_SCHEMA, prepare_curriculum
    values = researched_domain(approved=mode != "unapproved", public=mode != "private_descriptor", fixture=mode == "fixture")
    p, frozen, _, index, coverage, _, research, _, github, web, bodies, reader = values
    assert research.entries[0].reason_codes == ("public_descriptor_unapproved",)
    assert research.entries[0].unresolved_outcomes == frozen.learning_outcomes
    assert not any((github.calls, web.calls, bodies.calls, reader.calls))
    ctx = prepare_curriculum(p, frozen, coverage, research, index)
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture")
    failure = provider.preflight(purpose=CURRICULUM_PURPOSE, payload=ctx.to_payload(), schema_name=CURRICULUM_SCHEMA)
    assert isinstance(failure, LLMFailure) and failure.details["dispatched"] is False


@pytest.mark.parametrize("fixture", [False, True])
def test_real_capability_provider_does_not_export_unapproved_source_or_fixture(fixture):
    from app.domain.planning.capabilities import CAPABILITY_PURPOSE, CAPABILITY_SCHEMA
    from app.domain.planning.capability_policy import CAPABILITY_POLICY
    p, frozen, _, _ = domain_inputs(fixture=fixture)
    payload = {"profile": p.to_payload(), "policy": CAPABILITY_POLICY.to_payload(),
        "verification_evidence": [e.to_payload() for e in frozen.verification_evidence]}
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture")
    failure = provider.preflight(purpose=CAPABILITY_PURPOSE, payload=payload, schema_name=CAPABILITY_SCHEMA)
    assert isinstance(failure, LLMFailure) and failure.details["dispatched"] is False


@pytest.mark.parametrize("constraint,allowed", [("只使用免费教材", True), ("禁止联网", False),
    ("未知且不能可信分类的限制", False)])
def test_direct_curriculum_provider_respects_dispatch_constraints_with_actual_mcp_fixture(constraint, allowed):
    from app.domain.planning.curriculum import CURRICULUM_PURPOSE, CURRICULUM_SCHEMA

    from backend.tests.unit.test_constraint_adaptation import fixture
    _, _, _, ctx, _ = fixture((constraint,), full=True)
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture")
    failure = provider.preflight(purpose=CURRICULUM_PURPOSE, payload=ctx.to_payload(), schema_name=CURRICULUM_SCHEMA)
    assert (failure is None) == allowed
    if not allowed:
        assert failure.details["dispatched"] is False


@pytest.mark.parametrize("constraint", ["禁止联网", "未知且不能可信分类的限制"])
def test_direct_capability_provider_cannot_bypass_external_dispatch_constraints(constraint):
    from app.domain.planning.capabilities import CAPABILITY_PURPOSE, CAPABILITY_SCHEMA
    from app.domain.planning.capability_policy import CAPABILITY_POLICY
    p = profile("学习MCP", constraints=(constraint,))
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture")
    payload = {"profile": p.to_payload(), "policy": CAPABILITY_POLICY.to_payload(), "verification_evidence": []}
    failure = provider.preflight(purpose=CAPABILITY_PURPOSE, payload=payload, schema_name=CAPABILITY_SCHEMA)
    assert isinstance(failure, LLMFailure) and failure.details["dispatched"] is False


@pytest.mark.parametrize("mode", ["hash", "ok"])
def test_independent_review_domain_verification_dispatch_is_once_per_session_and_snapshot(mode):
    p, _, _, s = domain_inputs()
    reader, calls = pinned_reader(mode)
    verifier = DomainVerifier(reader, sources=(s,))
    session = verification_session(p, s)
    first = verifier.verify(p, source_id=s.source_id, session=session, scope=SCOPE, project_id="project")
    usage = dict(session.usage)
    snapshot = session.snapshot()
    second = verifier.verify(p, source_id=s.source_id, session=session, scope=SCOPE, project_id="project")
    assert len(calls) == 2, "Known pin failure or success must not dispatch a second verification"
    assert second.reason == "verification_stopped" and not second.approval
    assert snapshot.config_hash and session.usage == usage
    restored = ResearchSession.restore(snapshot)
    repeated = verifier.verify(p, source_id=s.source_id, session=restored, scope=SCOPE, project_id="project")
    assert repeated.reason == "verification_stopped" and len(calls) == 2 and restored.usage == usage
    assert first.status == ("verified" if mode == "ok" else "needs_verification")


def test_independent_review_reader_cannot_swap_to_another_self_consistent_plan_from_same_source():
    _, frozen, approval, _ = domain_inputs()
    payload = payload_for(frozen, approval)
    plan = payload["domain_authority"]["plan"]
    definition = approval.source.capabilities[1]
    plan["capabilities"][0].update(capability_id=definition.capability_id, title=definition.title,
        learning_outcomes=[asdict(o) for o in definition.learning_outcomes])
    plan["plan_hash"] = content_hash({k: v for k, v in plan.items() if k != "plan_hash"})
    payload["must_teach"] = [asdict(o) for o in definition.learning_outcomes]
    assert not validate_reader_input(payload, READER_SCHEMA, domain_approvals=(approval,))
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="fixture", model="fixture",
        domain_approvals=(approval,))
    failure = provider.preflight(purpose=READER_PURPOSE, payload=payload, schema_name=READER_SCHEMA)
    assert isinstance(failure, LLMFailure) and failure.details["dispatched"] is False


def test_source_approval_must_be_explicitly_bound_after_item2_before_reader_export():
    p, frozen, bound, s = domain_inputs()
    adapter, _ = pinned_reader()
    unbound = DomainVerifier(adapter, sources=(s,)).verify(p, source_id=s.source_id,
        session=verification_session(p, s), scope=SCOPE, project_id="project").approval
    assert unbound.plan_hash is None and public_outcomes(frozen, domain_approvals=(unbound,)) == {}
    assert reader_authority(frozen, domain_approvals=(unbound,)) is None
    port = Port(LLMResult(wire(p, cap(p, "ros2.action")), "test", "fixture"))
    selected = CapabilityPlanner(port).plan(p, run_id="item2", attempt_id="one",
        verification_evidence=(unbound.evidence,), domain_approvals=(unbound,))
    assert selected.plan_hash == frozen.plan_hash and len(port.calls) == 1
    assert bind_domain_approval(unbound, selected) == bound
    assert bind_domain_approval(bound, selected) is bound
    payload = payload_for(frozen, bound)
    payload["domain_authority"]["approval_hashes"] = [unbound.approval_hash]
    assert not validate_reader_input(payload, READER_SCHEMA, domain_approvals=(unbound,))


def test_plan_binding_cannot_be_replaced_or_rebound_to_another_selected_plan():
    p, frozen, approval, _ = domain_inputs()
    other = CapabilityPlanValidator().validate(wire(p, cap(p, "ros2.topic")), profile=p,
        verification_evidence=frozen.verification_evidence)
    with pytest.raises(ValidationAppError):
        replace(approval, plan_hash=other.plan_hash)
    with pytest.raises(ValidationAppError):
        bind_domain_approval(approval, other)
