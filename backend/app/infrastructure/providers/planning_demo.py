"""Explicit local Fake LLM scenario. Never claims a cloud call or verified resource."""

from app.infrastructure.providers.fake import FakeLLM

TOPICS = [
    ("foundation", "开发环境与 Python 基础", "建立可复现的开发环境，理解函数与依赖管理"),
    ("core", "模型调用与提示词", "理解结构化输入输出与模型失败处理"),
    ("core", "工具与 Agent 编排", "使用稳定工具接口组织可观察的任务流程"),
    ("practice", "完成可验收的 Agent 应用", "实现一个小型知识助手并验证错误分支"),
]


def outline(purpose, payload):
    return {
        "outline_ref": "fake-demo",
        "sections": [
            {
                "stable_key": f"stage.{i}",
                "title": title,
                "section_kind": kind,
                "objective": objective,
                "resources": [
                    {
                        "role": "primary",
                        "source_ref": "",
                        "section_refs": [],
                        "source_version": 0,
                        "fallback_search_terms": [title + " 官方文档"],
                        "order_index": 0,
                    }
                ],
                "extensions": [],
            }
            for i, (kind, title, objective) in enumerate(TOPICS)
        ],
    }


def structure(purpose, payload):
    return {
        "nodes": [
            {"stable_key": f"node.{i}", "title": title, "node_type": "skill", "objectives": [objective]}
            for i, (_, title, objective) in enumerate(TOPICS)
        ],
        "units": [
            {
                "stable_key": f"unit.{i}",
                "title": title,
                "section_key": f"stage.{i}",
                "order_index": i,
                "node_keys": [f"node.{i}"],
                "objectives": [objective],
            }
            for i, (_, title, objective) in enumerate(TOPICS)
        ],
        "relations": [
            {
                "from_stable_key": f"node.{i - 1}",
                "to_stable_key": f"node.{i}",
                "relation_type": "prerequisite",
            }
            for i in range(1, len(TOPICS))
        ],
    }


def practice(purpose, payload):
    return {
        "stable_key": "practice.agent",
        "title": "Agent 应用实践",
        "idea": str(payload.get("goal", "Agent 开发")),
        "tasks": [
            {
                "stable_key": "task.agent",
                "title": "构建并验证知识助手",
                "section_key": "stage.3",
                "order_index": 0,
                "goal": "完成一个可运行的 Agent 应用",
                "in_scope": ["工具调用", "失败处理"],
                "out_scope": ["生产部署"],
                "acceptance": ["演示一次成功工具调用和一次受控失败"],
                "knowledge_links": [{"node_stable_key": "node.3", "role": "core"}],
            }
        ],
        "task_knowledge_links": [
            {"task_stable_key": "task.agent", "node_stable_key": "node.3", "role": "core"}
        ],
    }


def build_planning_demo():
    return FakeLLM(
        {"planning.outline": outline, "planning.structure": structure, "planning.practice": practice}
    )
