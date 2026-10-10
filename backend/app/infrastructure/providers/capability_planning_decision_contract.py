"""Short V2 decision wire: semantic choices only; frozen definitions stay server-owned."""

CAPABILITY_DECISION_SHAPE = {
    "decision_version": 2,
    "source_goal_profile_hash": "复制profile.profile_hash",
    "policy_version": "复制policy.policy_version",
    "route_kind": "systematic_agent_route 或 narrow_goal 或 other 或 uncertain",
    "status": "ready 或 needs_clarification 或 needs_verification",
    "learning_decisions": [{
        "capability_id": "本次Policy定义或验证输入中的稳定ID",
        "learning_requirement": "required 或 recommended",
        "project_usage": "required 或 optional 或 excluded",
        "desired_depth": "foundation 或 applied 或 deep",
        "requirement_refs": ["语义相关的真实requirement_id"],
        "learning_target_refs": ["仅explicit技术学习目标的requirement_id"],
        "project_usage_rationale": "说明本能力对主项目的使用选择及依据",
        "selection_rationale": "说明用户目标或真实前置为何需要学习此能力",
    }],
    "claim_decisions": [{
        "capability_id": "冻结Policy中被该声明支持的能力ID；无可信映射时为null",
        "claim_mappings": [{"claim_ref": "profile claim_id", "mapping_rationale": "该声明支持此能力的依据"}],
        "project_usage": "required / optional / excluded；capability_id=null时为null",
        "project_usage_rationale": "说明主项目使用选择；capability_id=null时为null",
        "requirement_refs": ["与已知能力有关的真实requirement_id；未映射时[]"],
    }],
    "constraint_effects": [{"constraint_ref": "profile constraint_id", "capability_id": "受影响能力ID或null",
                            "exclusion": "learning 或 project 或 not_applicable"}],
    "clarification_questions": [],
}

CAPABILITY_DECISION_SYSTEM = (
    "你仅为 Item 2 产生 CapabilityDecisionV2：只输出能力决策，不输出标准 CapabilityPlan。"
    "profile 是唯一学习者事实来源，policy.definitions 是已知能力、outcomes和真实前置的唯一权威；"
    "不要重分析GoalSpec，不使用固定路线、Seed或Recipe，也不要生成课程、教材、Practice或工具调用。"
    "严格按field_shape输出 decision_version=2、来源hash和Policy版本；不得多字段、漏字段或Markdown。"
    "learning_decisions只列真正要学习的能力及必要性依据、重要性、深度、项目使用选择和来源引用；"
    "不列title、outcomes、policy_refs、prerequisite_refs、disposition或accepted_known行。"
    "服务端按capability_id从冻结Policy生成title、outcomes、Policy引用和真实前置；"
    "缺少真实前置时仍须选择该前置的学习能力，已由声明支持的前置由claim_decisions承接。"
    "每个learning decision必须含selection_rationale、project_usage_rationale、真实requirement_refs；"
    "learning_target_refs仅含explicit且确为技术学习目标的需求，不能包括深度、用途、项目背景。"
    "claim_decisions是已知能力的唯一声明映射：按能力分组列出支撑它的claim_mappings，"
    "并给出项目使用选择、选择依据和相关需求来源。一个声明可以支持多个能力，同一能力可由多个声明支持。"
    "每条声明必须在至少一个映射组中出现；若没有可信的Policy能力映射，单独放入capability_id=null组。"
    "null组的project_usage和project_usage_rationale必须为null、requirement_refs必须为空；"
    "null表示未映射，不表示服务端已认定用户掌握任何能力。"
    "对已映射能力，服务端只在存在冻结Policy或已受信验证定义时生成accepted_known；不生成学习任务。"
    "不要同时输出claim_bindings或已知能力清单；服务端从claim_decisions规范化出它们，避免重复声明同一事实。"
    "learning能力与已知能力不得重叠；项目已存在不表示用户已掌握其全部技术，也不自动形成学习目标。"
    "每个profile.required_requirement都须由语义相关的learning或known能力通过requirement_refs覆盖；"
    "技术目标、项目应用、深度/用途条件和项目背景应分别绑定到实际承担这些事实的能力。"
    "项目应用由相关的learning能力引用；规划条件可以引用到实际受其约束的学习能力；"
    "不能为覆盖率把需求复制到无关能力或新加能力。若无法合理映射就返回needs_clarification。"
    "route_kind必须按真实目标范围选择；只提到Agent或某个窄技术不自动成为系统性路线。"
    "只有systematic_agent_route要求MCP能力学习required，这是StudyPlan课程政策，不代表MCP是用户技术目标。"
    "MCP project_usage独立判断；没有明确排除或必用依据时保持optional。MCP学习和最终项目集成分开。"
    "学习深度按profile和Policy默认值，不因术语多而扩大outcomes；窄概念目标不扩成整套专题。"
    "constraint_effects必须逐条覆盖profile.hard_constraints。learning是真正排除学习，project是真正排除项目使用；"
    "仅限制实现方式、保留现有载体或工具权限范围时用not_applicable/null，不是能力排除，也不代表约束已满足。"
    "保留现有CLI/JSON不是排除json.cli；限制工具操作范围不是排除tool.calling；"
    "不在最终项目使用MCP才是project排除，不是限制MCP操作范围。真实权限仍由后续业务环节验证。"
    "无可信定义的目标能力必须保持needs_verification；不得编造Policy、outcome、前置或来源。"
    "未知能力的learning_decisions只能作为待验证候选，不能生成ready标准Plan。"
    "Python等已有基础须依据claim映射保留，不能因宽泛基础删除目标明确要求的更具体能力。"
    "ready时clarification_questions为空；needs_clarification最多提出3个直接影响能力选择的问题。"
    "model rationale只用于解释可审查的语义选择，不替代服务端引用校验或独立语义审查。"
    "禁止学习者自述变成mastery评估；禁止增加无目标或Policy依据的能力。"
)

