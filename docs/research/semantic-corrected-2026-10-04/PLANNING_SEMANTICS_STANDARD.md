# StudyPlan 规划语义标准

任务日期：2026-10-03；收口日期：2026-10-04。状态：人工审核草案，未映射实际数据库、未发布Seed。本轮沿用原审读证据，不新增大范围研究。

## 对象定义与边界

| 对象 | 定义 | 选择/替换规则 | 禁止的误解 |
|---|---|---|---|
| Direction | 用户希望形成的能力领域，如Agent应用、AI全栈、云工程 | 可跨方向组合；不是职业归属字段 | 一人只能属于一个方向 |
| Capability Module | 可解释的能力问题及其输入输出、前置、实践与证据 | 开放标签与资源引用；即使没有Recipe也可编排 | 必须先有一个固定分支枚举 |
| Common Core | 各目标常需的最小应用心智模型与安全/错误/评价入口 | 按起点诊断和目标裁剪深度，保留必要依赖 | Hello 1–12每章都要同深度完成 |
| Reviewed Specialization Recipe | 已审核的章级参考骨架，含why now/JIT/章节/Exposure/练习/增量/exit | planner可选择、组合、裁剪、重排并补用户特有能力 | 路由闭集、职业分支或唯一课程 |
| Cross-cutting Capability Path | 跨Common Core与专项贯穿的能力路径；当前Evaluation | 同时挂到多个阶段，按评价对象深化 | 独立职业分支或等到最后才评价 |
| Optional Training Specialization | 训练目标驱动的可选深度；当前Agentic RL | 有训练目标、环境/reward/eval与资源条件才展开 | 应用开发必须先训练模型 |
| Default Starter Project | 没有合适用户项目时降低启动成本的默认候选 | fallback；可拒绝、替换、裁成纵切面 | 强制capstone或方向定义 |
| Continuous Outcome Carrier | 连续保存学习问题和验证成果的载体 | 用户项目、默认starter、必要的micro exercise；实现可换 | 永远同一份代码、所有能力必须迁入 |
| Reviewed Project Candidate | 身份/适用学习范围已有原包审读依据的可选项目案例 | 按目标选择；binding=optional；审读深度独立记录 | 必学repo、运行已验收或全仓已深审 |
| Personal/User Project | 用户指定/已有的项目及学习纵切面 | 合适时优先；大时缩小，不强迫换starter | 未公共审核就自动加入公共Seed |
| Optional Career Overlay | interview/project_showcase目标触发的表达与展示任务 | 在已有理解证据上加演练 | 所有人必须应对面试 |

## Continuous Outcome Carrier 选择规则

1. 先理解目标、起点和现有项目；不因默认模板存在就重置用户项目。
2. 已有合适项目：以当前项目为持续成果载体，用用户故事/实体/接口替换教材示例的业务名字。
3. 已有项目过大：缩成学习期可维护纵切面，例如“旅行输入→方案草稿→用户确认”，保留与整体项目的接口和未学范围。
4. 没有项目：推荐一个Default Starter Project并解释适配理由，可选其他方案。
5. 当前能力不适合自然加入项目：用独立Micro Exercise或sandbox exercise学会。保留输入、测试与设计取舍；需要时再迁回，不能强造功能。
6. 允许重构、换库、换仓库或替换实现；持续性由问题、测试、数据、接口、决策和验证证据保持。已选阶段的能力exit仍有效，不因换载体取消验证。

## 规划算法（runtime语义，不是数据库方案）

```text
用户目标 + 起点 + 现有项目
→ 识别目标能力
→ 裁剪Common Core与JIT缺口
→ 选择/组合0..N个Reviewed Specialization Recipes
→ 补用户目标特有能力
→ 选择Continuous Outcome Carrier
→ 匹配教程、Exposure与可选Project Case
→ 按实际依赖生成阶段顺序
→ 学习中依据用户提交/确认的证据局部调整
```

Recipe匹配失败不是规划失败。未命中时从capability/prerequisite/resource pool组合局部主线；选择有足够审读依据且免费可得的资料。缺少可审核资源时明确`needs_research_or_review`：说明哪项能力缺资料、已有证据到哪里，暂不编造章节或退出条件。需要新增研究时另行开展有范围的审核，不静默把新提案变成公共已审核Seed。

组合时合并共同前置，保持优秀Spine的局部连续性；将已会内容标REVIEW、同问题不同实现标COMPARE、新工程边界标DEEPEN、API变更标VERSION_CONTEXT、未教能力标NEW。必要顺序由依赖决定，不能为Recipe名称机械复制课程。正常/失败小实践和已选能力exit gate保留。

`primary_focus`表达当前阶段优先问题；`supporting_capabilities`可有多个。一个阶段少量聚焦用于降低认知负荷，不限制总体目标或用户归属。以下只是规划输出示例，不要求新增列：

```yaml
primary_focus: rag
supporting_capabilities: [workflow, browser, evaluation]
recipe_refs: [rag, browser, workflow]
carrier: user_project
carrier_slice: one_user_story
career_overlay: none
```

## Common Core与专项

Common Core含应用/LLM心智模型、loop、tool/structured action、permission/error边界、Eval-Lite、简单知识检索的位置、基础context、framework/workflow位置、protocol/MCP位置与系统评价入口。它只提供目标所需的基础深度：纯工具目标不必构建生产RAG；不需要MCP的目标只了解位置或略过实现；简单应用不硬上持久workflow。

首批深审Recipe：RAG、Coding、Workflow、Browser。Evaluation横切；Agentic RL是可选训练专项。允许未来扩展Multi-Agent、Memory/Personalization、Voice、Multimodal、MCP/Tool Ecosystem、Data Analysis、Customer Support和Domain Agents等，本轮未新增其研究或公共已审核内容。

## 项目和资源选取

用户指定项目可直接成为私有学习载体；公共已审核候选优先供无偏好用户参考，但不能覆盖用户目标。规划Agent可提出更合适的新候选，注明`user_private_candidate`与来源/未审范围。公共Seed提升需要人工审核身份、可访问性、教学范围、前置、失败练习及适配；这不是自动审批或自动评分。

公共项目案例只保存repo URL、why now、learning focus、prerequisites、desired depth、avoid scope、important questions、expected outputs和migration candidates，以及必要的候选状态/溯源说明。known knowledge/study mode可在planner输出组装，不固定源码路径、commit或用户分支。用户实际开发的版本记录、依赖锁与回滚标签是其运行证据，不是公共路线的源码定位约束。

文档中业务名称、数据库示例、main/staging触发条件都只是教学情景。替换时保留相同能力问题与验证方式。local-cloud routing仅是可选成本/质量主题；面试仅是career overlay。阶段证据需用户确认，不自动mastery/scoring。
