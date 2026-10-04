"""Authorized, section-scoped body review in a new immutable Agent pack.

No network, original pack writes, runtime claim or curriculum redesign. The
single chapter receives new catalog identities because catalog rows and author
section order are immutable; all inherited teaching and qualification stays.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from app.domain.domain_packs.validation import validate_seed
from app.infrastructure.domain_pack import load_pack

OUTPUT = "agent-application-v8.json"
OLD_SOURCE = "src_v612_1f6742530460b0908234a6d3"
OLD_SECTION = "sec_v612_d79f6a54976fb31d5159ac60"
BODY_REVIEW = {
    "date": "2026-10-05",
    "authorization": "User explicitly authorized10.1 body review and next immutable version",
    "method": "static_text_and_code_read; no execution or external links/images read",
    "source_url": "https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter10",
    "body_url": "https://raw.githubusercontent.com/datawhalechina/hello-agents/main/docs/chapter10/Chapter10-Agent-Communication-Protocols.md",
    "observed_git_blob": "98b0700c4adf3259efc1842a307c9b2c2238fc9b",
    "repository_commit": "NOT OBSERVABLE; main file blob observed, not a pinned repository commit",
    "body_sha256": "e68e510739fc08527f994eac7ab4104b5abc38f4b51c3e788d2fa9ef2111a60d",
    "section_sha256": "97ff3dbbab2119cb15c85d072cbe534b58f8abcb60d69fc63eaf8dbc68220e4d",
    "section_normalization": "CRLF_to_LF; hash covers extracted UTF-8 section, not the captured Windows file",
    "section_utf8_bytes": 13346,
    "captured_section_file_sha256": "ddbb8acb2a13eca2ac1293138e393c15809d45c7c01251018f7853837d9201e4",
    "captured_section_file_utf8_bytes": 13551,
    "body_language": "en",
    "section_header": "10.1 Agent Communication Protocol Fundamentals",
    "reviewed_scope": ["10.1.1", "10.1.2", "10.1.3", "10.1.4"],
    "review_depth": "selected_sections_read",
    "findings": [
        "10.1.1解释重复Tool适配、能力发现和协作的限制；MCPTool代码为静态示例。",
        "10.1.2比较MCP工具/资源连接、A2A协作和ANP概念发现；不要求实现全部协议。",
        "10.1.3说明protocol实现、Tool封装、Agent集成三层；不代替host/client/server深入章节。",
        "10.1.4列包路径和固定版本安装/调用示例，已读未安装或执行。",
    ],
    "limitations": [
        "没有抓取图像/外链，图表内容不作为本次审读依据。",
        "仅新增10.1正文审读；其他章节保留原审读记录，未在本次重新审读。",
        "教程接口/版本描述不是当前SDK互通、安全、transport或部署成功证据。",
        "不新增多Agent、ANP、付款、生产服务或高级OAuth必做任务。",
    ],
    "runtime_validation": "not_run",
}


def reviewed_identity_map(pack):
    source = next(s for s in pack["resources"] if s["source_id"] == OLD_SOURCE)
    new_source = "src_mcp101_" + hashlib.sha256(
        (OLD_SOURCE + BODY_REVIEW["section_sha256"]).encode()).hexdigest()[:24]
    return {OLD_SOURCE: new_source, **{
        s["section_id"]: "sec_mcp101_" + hashlib.sha256(
            (s["section_id"] + new_source).encode()).hexdigest()[:24]
        for s in source["sections"]}}


def _replace_identities(value, mapping):
    if isinstance(value, dict):
        return {k: _replace_identities(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_identities(v, mapping) for v in value]
    return mapping.get(value, value) if isinstance(value, str) else value


def build_mcp101_reviewed_pack():
    base = load_pack("agent-application-v7.json")
    mapping = reviewed_identity_map(base)
    pack = _replace_identities(deepcopy(base), mapping)
    pack["version"] = 8
    source = next(s for s in pack["resources"] if s["source_id"] == mapping[OLD_SOURCE])
    source["source_version"] = 2
    source["checked_at"] = "2026-10-05T00:00:00+08:00"
    source["review_note"] += "；2026-10-05额外定向审读10.1英文正文；其余章节为继承证据，运行未验证。"
    source["review_evidence"]["additional_section_review"] = deepcopy(BODY_REVIEW)
    source["metadata"]["additional_section_review"] = deepcopy(BODY_REVIEW)
    section = next(s for s in source["sections"] if s["section_id"] == mapping[OLD_SECTION])
    section.update(verification_status="reviewed", review_depth="selected_sections_read",
        checked_at="2026-10-05T00:00:00+08:00",
        review_note="2026-10-05实际审读10.1.1–10.1.4英文正文：协议集成问题、MCP/A2A/ANP职责比较、三层Tool封装与静态示例。图像、外链未读；示例未运行；其他章节资格继承；不扩大必做任务。",
        body_review=deepcopy(BODY_REVIEW))
    for stage in pack["stage_blueprints"]:
        for assignment in stage.get("resources", []):
            if assignment["source_ref"] == mapping[OLD_SOURCE]:
                assignment["source_version"] = 2
    # Catalog provenance is immutable per source ID. Retain the original base
    # provenance for unchanged sources and append the new authority in payload.
    pack["publication_evidence"]["mcp101_scoped_review"] = {
        "base_pack": "agent.application/7", "base_provenance": base["provenance"],
        "identity_map": mapping, "new_chapter_source_version": 2,
        "review": deepcopy(BODY_REVIEW),
        "scope": "Only10.1 gains dated body-reading evidence. All other teaching and qualification inherited unchanged.",
    }
    return validate_seed(pack)


def main():
    target = Path(__file__).resolve().parents[1] / "infrastructure/content" / OUTPUT
    text = json.dumps(build_mcp101_reviewed_pack(), ensure_ascii=False, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != text:
            raise ValueError("Published successor differs; do not overwrite")
    else:
        with target.open("x", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
