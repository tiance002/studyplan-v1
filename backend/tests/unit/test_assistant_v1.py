import pytest
from app.domain.assistant import build_input, validate_reply, validate_message, assistant_manifest, manifest_intact
from app.application.model_binding import SubmissionBinding
from app.application.planning_budget import BudgetPolicy
from app.core.errors import ValidationAppError


def test_work_draft_and_question_exact_and_bounded():
    raw = " \n原文🙂\t "
    assert validate_message("work_draft", raw) == raw
    for intent, text in [("other", raw), ("question", " "), ("work_draft", "x"*20001), ("question", "\x00")]:
        with pytest.raises(ValidationAppError): validate_message(intent,text)


def test_question_binds_draft_without_replacing_it_and_deduplicates():
    draft = {"message_id":"d1", "content":"我的原稿"}
    trigger = {"message_id":"q1", "intent":"question", "content":"请解释目标"}
    history = [{"role":"user","content":"我的原稿","message_id":"d1"},
               {"role":"assistant","content":"已评价","message_id":"a1"}]
    result = build_input("summary", {"objectives":["目标"]}, draft, trigger, history)
    assert result["current_message"]["content"] == "请解释目标"
    assert result["work_draft"]["content"] == "我的原稿"
    assert all(m["message_id"] != "d1" for m in result["history"])


def test_input_overflow_fails_before_dispatch_and_never_truncates_latest():
    with pytest.raises(ValidationAppError):
        build_input("practice", {"acceptance":["x"*44000]}, None,
                    {"message_id":"m","intent":"question","content":"exact"}, [])


@pytest.mark.parametrize("value", [{}, {"reply":""}, {"reply":" \n"}, {"reply":"x"*16001}, {"reply":"ok","status":"VERIFIED"}, {"reply":False}])
def test_invalid_reply_fails_without_planning_repair(value):
    assert validate_reply(value)


def test_markdown_reply_is_feedback_only():
    assert validate_reply({"reply":"## 解释\n请结合任务要求补充边界。"}) == []


def test_frozen_single_request_manifest_integrity():
    binding=SubmissionBinding("fixture:assistant", BudgetPolicy(100,100,100,100,100,100))
    manifest=assistant_manifest(binding)
    assert manifest_intact(manifest) and manifest["max_requests"]==1
    assert manifest["output_cap"]==100
    assert not manifest_intact(dict(manifest,max_requests=2))
    assert not manifest_intact(dict(manifest,protocol="summary-review-v1"))


def test_retained_paid_extra_message_identity_is_non_authoritative_without_mutating_fixture():
    import json
    from pathlib import Path
    raw = (Path(__file__).parents[1]/"fixtures/assistant_v1/known_extra_message_id.json").read_bytes()
    fixture = json.loads(raw)
    value = json.loads(fixture["content"])
    assert fixture["finish_reason"] == "stop"
    assert set(value) == {"reply", "message_id"}
    assert validate_reply(value) == []
    from app.domain.assistant import project_reply
    assert project_reply(value)==dict(reply=value['reply'],status='continue',proposal=None)
    assert json.loads(fixture["content"]) == value  # Original receipt/failed Run unchanged.


def test_coaching_wire_explicitly_forbids_output_id_fields_without_other_purpose_changes():
    import json, httpx
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.domain.assistant import ASSISTANT_PROTOCOL, ASSISTANT_PURPOSE
    observed=[]
    def reply(request):
        observed.append(json.loads(request.content))
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":'{"reply":"只读评价"}'}}],"usage":{"prompt_tokens":1,"completion_tokens":1}})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        p=OpenAICompatibleLLM(base_url="https://fixture.invalid/v1",api_key="synthetic",model="synthetic",client=client)
        p.prompt_version=ASSISTANT_PROTOCOL
        payload=build_input("summary", {"objectives":["输入边界"]},{"message_id":"draft","content":"稿"},{"message_id":"q","intent":"question","content":"问"},[])
        p.generate_structured(purpose=ASSISTANT_PURPOSE,payload=payload,schema_name="AssistantReplyV1",run_id="r",attempt_id="a")
    assert len(observed)==1
    system=observed[0]["messages"][0]["content"]
    assert "唯一字段 reply" in system and "不能包含 message_id" in system and "所有解释只写在 reply" in system
