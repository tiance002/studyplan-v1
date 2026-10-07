"""Test-only retained generation fixtures for content and reliability assertions.

Not registered by application composition, never a planner fallback.
"""

from copy import deepcopy

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
        {"planning.outline": selected_output, "planning.structure": selected_output,
         "planning.practice": selected_output, "planning.repair": selected_output}
    )


def _stage_resources(payload, stage_key, node_keys, goal):
    pack = payload.get("domain_pack") or {}
    for stage in pack.get("stage_blueprints") or []:
        if stage.get("stable_key") == stage_key:
            resources = deepcopy(stage.get("resources") or [])
            for resource in resources:
                resource.setdefault("node_keys", list(node_keys))
            return resources
    return [{"role": "primary", "source_ref": "", "section_refs": [], "source_version": 0,
             "order_index": 0, "node_keys": list(node_keys),
             "fallback_search_terms": [goal + " 资料待核验"]}]


def _skeleton_output(payload):
    manifest = payload.get("manifest") or {}
    goal = str(payload.get("goal", "学习目标"))
    sections = []
    for index, spec in enumerate(manifest.get("stages") or []):
        node_keys = list(spec.get("node_keys") or [])
        sections.append({
            "stable_key": spec["stage_key"],
            "title": spec.get("title") or f"{goal}：阶段 {index + 1}",
            "section_kind": spec.get("section_kind") or "general",
            "objective": spec.get("objective") or f"围绕“{goal}”完成阶段 {index + 1}",
            "resources": _stage_resources(payload, spec["stage_key"], node_keys, goal),
            "extensions": [],
        })
    return {"outline_ref": "fake-reviewed-skeleton", "sections": sections}


def _structure_output(payload):
    if payload.get('_structure_input_format') == 'reviewed_structure_v1':
        stage = payload['stage']
        focus = payload.get('allowed_teaching_focus')
        if focus is not None:
            if stage['stage_key'].endswith('.a2'):
                titles = ('工具契约与注册派发', '权限拒绝与职责边界', '未知工具与执行失败证据')
                objectives = ('解释工具定义、参数校验与按名称派发；比较 Tool 与 registry 职责',
                              '解释执行前权限检查与拒绝以后不能继续动作的原因',
                              '区分未知工具和执行失败，指出支持结论的记录')
                return {'units': [{'title': title, 'node_keys': list(payload['allowed_node_keys']),
                                  'focus_refs': [focus[index % len(focus)]['ref']], 'objectives': [objectives[index]]}
                                 for index, title in enumerate(titles)]}
            return {'units': [{'title': stage['title'], 'node_keys': list(payload['allowed_node_keys']),
                               'focus_refs': [f['ref'] for f in focus if not f['ref'].startswith('source:')][:2],
                               'objectives': [stage['objective'] or '解释阶段能力与失败边界']}]}
        return {'units': [{'title': stage['title'], 'node_keys': list(payload['allowed_node_keys']),
                           'objectives': [stage['objective'] or '解释阶段能力与失败边界']}]}
    stage = payload["stage"]
    blueprints = payload.get("node_blueprints") or []
    nodes, relations = [], []
    if blueprints:
        for blueprint in blueprints:
            nodes.append({"stable_key": blueprint["stable_key"], "title": blueprint.get("title", ""),
                          "node_type": blueprint.get("node_type", "concept"),
                          "objectives": list(blueprint.get("objectives") or [])})
            if blueprint.get("parent_key"):
                relations.append({"from_stable_key": blueprint["parent_key"],
                                  "to_stable_key": blueprint["stable_key"], "relation_type": "contains"})
            for dependency in blueprint.get("prerequisite_keys") or []:
                relations.append({"from_stable_key": dependency,
                                  "to_stable_key": blueprint["stable_key"], "relation_type": "prerequisite"})
    else:
        for index in range(2):
            nodes.append({"stable_key": f"{stage['stable_key']}.node.{index}",
                          "title": f"{stage.get('title', '')}要点 {index + 1}", "node_type": "concept",
                          "objectives": [f"理解{stage.get('title', '')}要点 {index + 1}"]})
    unit = {"stable_key": "unit." + stage["stable_key"], "title": stage.get("title") or stage["stable_key"],
            "section_key": stage["stable_key"], "order_index": 0,
            "node_keys": [node["stable_key"] for node in nodes],
            "objectives": [stage.get("objective") or "阶段目标"]}
    return {"nodes": nodes, "units": [unit], "relations": relations}


def _practice_output(payload):
    stage = payload["stage"]
    structure = payload.get("structure") or {}
    blueprint = payload.get("practice_blueprint") or {}
    nodes = [node["stable_key"] for node in structure.get("nodes") or []]
    linked = [key for key in (blueprint.get("node_keys") or nodes[:1]) if key in nodes] or nodes[:1]
    task_key = blueprint.get("stable_key") or ("task." + stage["stable_key"])
    task = {
        "stable_key": task_key,
        "title": blueprint.get("title") or (stage.get("title") or "") + "阶段练习",
        "section_key": stage["stable_key"], "order_index": 0,
        "goal": blueprint.get("goal") or stage.get("objective") or "完成阶段练习",
        "in_scope": list(blueprint.get("in_scope") or ["阶段要点"]),
        "out_scope": list(blueprint.get("out_scope") or []),
        "acceptance": list(blueprint.get("acceptance") or ["展示练习结果并说明验证步骤"]),
        "knowledge_links": [{"node_stable_key": key, "role": "core"} for key in linked],
    }
    return {"stable_key": "practice." + stage["stable_key"], "title": stage.get("title") or "",
            "idea": stage.get("title") or "", "tasks": [task],
            "task_knowledge_links": [{"task_stable_key": task_key, "node_stable_key": key, "role": "core"}
                                     for key in linked]}


def _repair_output(payload):
    context = payload.get("context") or {}
    if (payload.get("target") or {}).get("kind") == "practice":
        return _practice_output(context)
    return _structure_output(context)


def selected_output(purpose, payload):
    """Exercise the existing graph using reviewed blueprints, with no cloud call."""
    # ---- b3f2-batch-v1 local payloads ----
    if purpose == "planning.outline" and payload.get("_outline_input_format") == "stage_skeleton_v1":
        return {"outline_ref": "fake-skeleton-v1", "sections": [
            {"stable_key": stage["stable_key"], "title": stage["title"],
             "objective": stage["objective"] or f"围绕{payload.get('goal') or '学习目标'}完成{stage['title']}"}
            for stage in payload["frozen_stages"]]}
    if "target" in payload and "context" in payload:
        return _repair_output(payload)
    if payload.get('_structure_input_format') == 'reviewed_structure_v1':
        return _structure_output(payload)
    if "stage" in payload and "structure" in payload:
        return _practice_output(payload)
    if "stage" in payload and "node_blueprints" in payload:
        return _structure_output(payload)
    if "manifest" in payload:
        return _skeleton_output(payload)
    if "domain_pack" not in payload:
        return {"planning.outline": outline, "planning.structure": structure,
                "planning.practice": practice}.get(purpose, structure)(purpose, payload)
    pack = payload["domain_pack"]
    sections = deepcopy(pack.get("stage_blueprints", []))
    goal = str(payload.get("goal", "学习目标"))
    if not sections:
        sections = [
            {"stable_key": f"stage.general.{i}", "title": f"{goal}：{title}", "section_kind": kind,
             "objective": f"围绕“{goal}”完成{objective}", "extensions": [],
             "resources": [{"role": "primary", "source_ref": "", "section_refs": [],
                            "source_version": 0, "order_index": 0,
                            "fallback_search_terms": [goal + " " + title + " 教程"]}]}
            for i, (title, kind, objective) in enumerate([
                ("基础与范围", "foundation", "必要概念与前置条件梳理"),
                ("核心方法", "core", "核心方法的对照练习"),
                ("实践与验证", "practice", "可展示的作品与结果检查"),
            ])
        ]
    nodes = deepcopy(pack.get("knowledge_blueprints", []))
    if not nodes:
        nodes = [{"stable_key": f"node.scope.{i}", "title": s["title"], "node_type": "concept",
                  "objectives": [s["objective"]]} for i, s in enumerate(sections)]
        for i, section in enumerate(sections):
            section["node_keys"] = [f"node.scope.{i}"]
    units = []
    for i, section in enumerate(sections):
        unit_nodes = section["node_keys"]
        units.append({"stable_key": "unit." + section["stable_key"], "title": section["title"],
                      "section_key": section["stable_key"], "order_index": i,
                      "node_keys": unit_nodes, "objectives": [section["objective"]]})
        for resource in section.get("resources", []):
            resource.setdefault("node_keys", unit_nodes)
    relations = []
    for node in nodes:
        for dep in node.get("prerequisite_keys", []):
            relations.append({"from_stable_key": dep, "to_stable_key": node["stable_key"],
                              "relation_type": "prerequisite"})
        if node.get("parent_key"):
            relations.append({"from_stable_key": node["parent_key"], "to_stable_key": node["stable_key"],
                              "relation_type": "contains"})
    if not relations:
        relations = [{"from_stable_key": nodes[i - 1]["stable_key"], "to_stable_key": nodes[i]["stable_key"],
                      "relation_type": "prerequisite"} for i in range(1, len(nodes))]
    templates = {t.get("section_key"): t for t in pack.get("practice_blueprints", [])}
    tasks = []
    task_links = []
    for i, section in enumerate(sections):
        template = templates.get(section["stable_key"], {})
        key = str(template.get("stable_key", "task." + section["stable_key"]))
        linked_nodes = template.get("node_keys", section["node_keys"][:1])
        links = [{"node_stable_key": n, "role": "core"} for n in linked_nodes]
        tasks.append({"stable_key": key, "title": template.get("title", section["title"] + "阶段练习"),
                      "section_key": section["stable_key"], "order_index": i,
                      "goal": template.get("goal", section["objective"]), "knowledge_links": links,
                      "in_scope": template.get("in_scope", [section["objective"]]),
                      "out_scope": template.get("out_scope", []),
                      "acceptance": template.get("acceptance", ["展示练习结果并说明验证步骤和已知限制"]),
                      })
        task_links.extend({"task_stable_key": key, **link} for link in links)
    proposal = {"stable_key": "practice.route", "title": goal + "实践", "idea": goal,
                "tasks": tasks, "task_knowledge_links": task_links}
    outputs = {
        "planning.outline": {"outline_ref": "fake-reviewed-skeleton", "sections": sections},
        "planning.structure": {"nodes": nodes, "units": units, "relations": relations},
        "planning.practice": proposal,
        "planning.repair": {"nodes": nodes, "units": units, "relations": relations, "practice_proposal": proposal},
    }
    return outputs[purpose]
