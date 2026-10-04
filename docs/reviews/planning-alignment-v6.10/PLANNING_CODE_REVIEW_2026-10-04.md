# StudyPlan 规划思想—内容—代码一致性审查

日期：2026-10-04  
仓库：tiance002/studyplan-v1  
已核对远端分支：feat/n1-resource-discovery  
审查提交：ff3b6c42c16b0ec2b634b45441251cb8dc1e3249（v6.8 收费代表验收记录）  
性质：只读源码与文档审查；不是本轮产品运行验收。

## 0. 核心结论与证据边界

主体工程不应推倒重写。短 outline、冻结 manifest、分阶段生成、确定性保护、确认后发布、历史保护和现有项目学习卡都应保留。

当前最需要修的是：**把已经写进研究文档的学习编排语义，落实到冻结前的路线选择、内容映射和最终页面消费**。不是继续给模型更多上下文，也不是只在前端补一个名叫 A8 的按钮。

本轮已经通过 GitHub 连接器检查工作分支与关键源码。主要结论来自代码条件和数据映射；下文的复现输入是应交给 Codex 执行的回归用例，不冒充本轮运行结果。没有运行用户本机应用、PG、Edge 或完整测试套件；没有执行收费模型、修改仓库或推送。v6.7/v6.8 的 PASS 仅按其报告边界引用，不外推为全面教学质量通过。

远端当前是 v6.8 提交，不能假定上一条 v6.9 建议已经实施。Codex 开工先核对本机新改动，已实现的内容直接复用。

本文分清三类：
- 【源码事实】在固定审查提交中明确可见。
- 【影响推断】由源码分支或数据流推导，需加入产品测试。
- 【本轮建议】为满足用户最新目标作出的规则校正，不伪称旧代码原本就这样。

## 1. 重新对齐的产品思想

### 1.1 平台负责什么

StudyPlan 负责让学习者知道：为什么现在学、应该学到什么程度、读哪一段免费材料、需要补哪一点前置、哪些内容与前面重复、怎么比较、做哪个小实践，以及如何进入真实工程学习。

StudyPlan 不替代外部 Coding Agent，不建设仓库 clone 服务、源码索引、AST/call graph、Repo RAG 或永久逐函数教材。它提供项目地址、学习问题、边界、深度和可复制提示词；外部 AI 在用户允许的环境中读取当前源码并动态安排阅读。

### 1.2 稳定能力、当前教材、用户目标要分开

三条首批方向是 Agent 应用、AI 全栈、云服务工程，不是用户职业闭集。RAG/Coding/Workflow/Browser 是可组合的已审参考方案；Eval 横切；真正参数训练的 Agentic RL 是可选训练专项。

Hello-Agents、LCC、Pi 等是当前候选，不是方向定义。教程正文免费；实践可能发生 API、云计算等费用，两者不能混为一谈。同等质量优先中文或高质量中文版，英文文字可以补充，不默认依赖英文视频。

### 1.3 两种项目不能混为一谈

**持续实践载体**：用户逐步开发的东西。已有项目优先；没有项目才建议 Starter；不能自然承载某能力时允许独立小实验。

**参考学习项目**：用来观察真实成熟实现的外部项目。它承担与教程/自己实现对比的作用。初学者刚写的小 Demo 不能自动替代成熟实现学习；用户已有成熟项目且确实覆盖目标时，可以兼任两种角色。

“Pi 可以替换”表示可选别的合适案例；不等于“完整路线可以静默省掉真实项目学习”。“用户项目优先”主要约束实践载体，不是让所有参考项目都消失。

### 1.4 宏观顺序

必要的即时前置 → 连续教程与小实践 → 同一成果载体增量 → 规模可控的真实项目/核心整体认识 → 按目标选专项教程与深化 → 大型成熟项目的目标相关切片 → 迁移与验证。

这是教学逻辑，不是每个用户都要走完的死板课表。窄专题可以只展开必要闭包。完整方向路线应该交代后续路径；用户说“先做一个最小应用”不等于“永远只学基础”。目标不清楚时使用现有澄清交互或在草案中明确当前范围，不把预算裁剪伪装成学习目标裁剪。

### 1.5 前置与重复

外部前置必须满足：当前不会、主教程不会在首次使用前教、不会就无法继续。已安排在前面的材料不等于已掌握；用户自述熟悉不等于平台 VERIFIED，但也不意味着必须强迫完整重学。

重复知识必须注明 REVIEW/COMPARE/DEEPEN/VERSION_CONTEXT。比较应发生在相关概念附近，不能只是后面再列一门完整课程。教程可以指定章节范围；开源项目不要把固定源码路径/历史 commit 作为学习契约。

## 2. 当前真实实现流程

【源码事实】受控包路径大致如下：

```text
用户 goal + GoalSpec(target/scope/desired_depth/starting_point/constraints)
  ↓
domain_pack.runtime_pack_key_for_goal / pack_key_for_goal
  ↓
选取已发布 DomainPack
  ↓
semantic_content.adapt_semantic_pack
  ├─ 默认阶段 + 文本触发条件
  ├─ Recipe 标签组合
  ├─ required_module_closure
  └─ 载体说明/资料缺口说明
  ↓
PlanService._freeze_submission
  ├─ 冻结被选阶段/完整本地权威包
  ├─ manifest hash、模型与用途预算
  └─ stage_skeleton_v1
  ↓
短 outline：阶段键与顺序已冻结，主要个性化标题/目标
  ↓
逐阶段 structure / practice
  ↓
planning_batches.merge_batches
  ├─ 恢复权威知识/资源/章节/指导/任务
  └─ 清除越权模型字段与额外任务
  ↓
draft_projection → 草案持久化 → 明确确认 → 新 PlanRevision
  ↓
MainWorkspace → LearningGuidance / Resources / ProjectStudyCard
```

这意味着：**缺 A8 的主要原因在冻结前，不是模型在 outline 中临时忘了加项目**。增加 outline token 或换更强模型，不能让它合法添加被冻结规则排除的阶段。

确定性方案本身可行，但它把课程选择的正确性责任放到了 selector、内容映射和冻结前适配上。结构测试只证明“按既定选择稳定执行”，不能证明“既定选择符合学习目标”。

来源：S1、S2、S3、S4、S5、S8。

## 3. 发现 F1：A8 缺失是选择规则和内容绑定的双重缺口（P1）

【源码事实】map_semantic_content.selection 对 A8 设置 default=False，仅在“源码 / 真实项目 / 项目学习”等词出现时触发。完整/系统学习这类意图没有对应的完整旅程保障。

同一文件中 `BINDINGS['A8'] = []`；项目卡 targets 将 Pi/OpenHands 放在 C10，RAGFlow/WeKnora 放在 G6，browser-use 放在 B7，没有给 A8 配项目卡。

【影响推断】v6.8 的目标没有这些触发词，所以得到 A0/A1/A2/A3/A4/A7 而没有 A8，符合当前代码行为。即使只把 A8 开关改为默认开启，A8 仍可能没有 CASE_STUDY + 对应项目扩展，现有卡片依然不显示。

【建议】复用已有 A8 表达“规模可控真实项目的整体认识”，为完整路线提供一个合适且可替换的轻量项目候选或明确的待选择状态。专项已有 G6/C10/W5/B7 等再负责更深目标切片。不是在一张 A8 卡里同时塞所有大小项目，也不是把 Pi/RAGFlow 变成必学仓库。

无专项目标的完整路线：先保留轻量真实工程认识，并清楚交代后续专项选择；不能为了填表强行选 RAG 大项目。窄目标不强塞 A8。

教材/候选内容改变时发布下一合法 Pack 版本；不改已发布 Agent5、已有 v6.8 Plan 或历史 manifest。

来源：S3、S9。

## 4. 发现 F2：目标范围仍主要依赖正向关键词；完整/窄目标、排除项与起点未充分进入选择（P1）

【源码事实】

1. `pack_key_for_goal` 只要匹配独立的“AI/人工智能”，就在 Agent 分支之前返回 ai.fullstack。因此“系统学习 AI Agent 应用开发”会先落入全栈判断。
2. `adapt_semantic_pack` 用 target/goal/scope/constraints 拼接的文本识别 Recipe 和 when_any；显式排除处理主要针对 RL/训练，没有同等处理“不学 RAG/不要浏览器”。
3. Agent 默认 A0/A1/A2/A3/A4/A7 会进入，即使用户只明确需要 MCP，也没有窄路线分支来先收缩默认根集合。
4. GoalSpec 有 desired_depth 和 starting_point；但阶段选择主要使用默认值、触发词、skip_when_any。当前映射只有很有限的 skip 条目，AI 全栈没有针对已掌握 React/JS/SQL 的相应选择行为。
5. closure 无条件恢复所选节点的依赖；注释明确写即使起点自述建议跳过也保留。用户起点不等于掌握证据是对的，但“依赖必须保留”与“必须完整再学一遍”不应画等号。

【建议】在现有 GoalSpec/selector 内做薄规则，不增加分类模型：明确目标优先于泛词；显式范围/排除优先于正向提及；完整路线和窄专题先决定根集合，再展开必要依赖。起点采用“已声明基础 / 需补 / 未知”的规划语义，不写成 VERIFIED。

依赖处理先做最小可行：必要知识关系继续保留；已经具备的内容可作为简短复习/进入检查，不复制整门课程。若现有数据不支持真正省略一个阶段而保留其已满足前置，不要删除依赖边骗校验，应明确限制并给出最薄适配方案。

必须以成对用例检查：同一目标只改变“只学/系统学”“已有基础/零基础”“需要/不需要”，路线应该有可解释差异。

来源：S1、S2、S4。

## 5. 发现 F3：实践载体已经能识别，但具体任务仍可能只是“用户项目说明 + 原默认练习”（P1）

【源码事实】`adapt_semantic_pack` 会替换部分阶段标题/目标/guide 中的 Starter 字符串；对 practice 则主要把 carrier_note 加在原 `practice['goal']` 前。

v6.7 新 merge 按受审 blueprint 恢复任务身份、数量、目标、范围与验收，仅保留模型的 description/hints 等有限字段。这个保护解决了额外强制任务问题，但也意味着模型不能在下游修正不适配的默认练习。

【影响推断】已有电商、旅行、Node API 的用户，可能在总标题看到了自己的项目，但具体练习仍沿研究助手/某默认服务的场景。是否每条路线已经发生这种不一致，需要对具体任务文本逐项检查；不能仅凭 carrier_title 正确宣布个性化完成。

【建议】保护“来源与能力要求”而不是冻结所有默认业务名。优先在 freeze 前形成经过规则校验的私人任务适配，然后 freeze 后继续严格保护。可先采用受控占位映射/现有指导字段，不另加模型预处理调用。

某项能力不适合用户项目时，标成独立 Micro Exercise 并说清用途，不能一边说“必须用你的项目”，一边保留不相关任务。知识键、章节、权限、费用、required/optional、验收最低要求不能被随意改写。

参考学习项目与实践载体分别表述。用户拥有一份刚写的 Demo，不自动证明已经完成“成熟工程对比学习”。

来源：S1、S5、S8、S9。

## 6. 发现 F4：项目卡已经有前端实现，但目前只消费一张卡，长文本续片也有丢失风险（P1）

【源码事实】
- `MainWorkspace` 已调用 ProjectStudyCard，所以不是从零缺这个组件。
- ProjectStudyCard 先看有没有 case_study/repo，再用 `extensions.find(...)` 取首个“项目学习：”扩展；没有逐个项目建立资源 URL 与扩展的精确配对。
- G6 有 RAGFlow、WeKnora，C10 有 Pi、OpenHands；如果均已入同一 Plan，该组件只会形成一张卡。
- mapper 的 `bounded_extensions` 把 guidance 每 850 字符切片，后续 topic 仍以“项目学习：”开头。
- MainWorkspace 的普通扩展区域排除所有“项目学习：”；ProjectStudyCard 又只取第一个。续片与后续项目有被隐藏的明确消费路径。
- 当前 Prompt 同时描述小项目整体和大项目切片，但输入结构没有独立 study_mode 字段。它不是“完全没有大小项目方法”，而是方法通用、项目级选择不够明确。

【建议】复用组件，按资源身份/规范化 repo root 精确配对，逐项展示已选卡，保证每个项目的片段完整可读，不跨项目拼接。用轻量内容约定标清 whole_core / targeted_deep_dive 等学习方式，不按 Star/文件数自动分类。

每张卡展示 why/focus/depth/avoid/questions/expected outputs/transfer。平台不预先生成当前源码地图；外部 AI 根据提示词动态分析。没有 repo 时可展示“参考项目待选择”及学习目标，但不能伪造链接。

保留已有优点：Prompt 已明确“此前介绍不代表掌握”、源码指令不覆盖学习范围、事实/解释/推断分开、复制本身不调用模型。不要把这些已正确的功能重写掉。

来源：S6、S7、S8、S10。

## 7. 发现 F5：能力节点与阶段、阅读范围绑得过紧；重复编排更多是文字而非统一能力身份（P2）

【源码事实】mapper 对每一阶段生成一个 `node.v62.<direction>.<code>`；节点标题来自阶段标题，objectives 来自 primary_chapters，scope 同样是阅读内容。A1 与 C1 等重复机制使用不同阶段节点键。

因此当前页面中的“学习目标”可能更像“读这些章”，不是“能解释/实现什么”；跨阶段重复大多靠 guide 的 REVIEW/COMPARE 等文字表达，而非共享细粒度能力标识。

【建议】本轮不迁移旧节点、不重建全知识图谱。先在下一版本内容中改正关键节点的可观察能力目标，阅读范围仍放资源章节；为关键重叠增加少量显式对照问题/已有能力引用。全面细粒度能力拆分可后置。

避免另一极端：为了去重把同知识的不同 Exposure 直接删除。默认基础和专项深化仍应保留各自的学习目的。

来源：S3、S9。

## 8. 发现 F6：核心云部署/恢复阶段仍有“详细说明但资料待补”的内容缺口（P1 内容验收项）

【源码事实】mapper 给 S3、S6、S7、S13 增加 `needs_research_or_review` 扩展，说明目标云厂商部署、Kubernetes 细项、语言对应 OpenTelemetry、数据库恢复等未形成独立审读切片。其保守标注是正确的，不能把它们当作已经完整深审和可直接照做的主线。

当前 Cloud 条件选择已经把 K8s、平台/IaC 等按目标触发，这一点不应重新说成所有云用户都被强制学 Kubernetes。

【建议】只补当前即将给用户验收的必经内容，不重新研究全部资料。完整云部署路线首次遇到未选云商时，应明确选择一个云平台或使用通用本地演练与待选说明。不能用“自行搜索当前官方资料”取代已承诺的连续入门教学。

Coding/RAG 等数据的已有 hold 继续保留；不得为了章节覆盖率把目录级审读升级为正文级。

来源：S3。

## 9. 发现 F7：技术预算、完整学习路线与本次生成范围需要分开（P1 验收/展示项；更深优化后置）

当前逐阶段生成安排为 outline 1 次 + 每阶段 structure/practice 各 1 次 + 有界 repair。按这个安排，六阶段正常 13 次、上限 15；增加一个阶段会变成正常 15、上限 17。这里是当前流程的算术推导，不是新的费用授权。

当前受控验收账本已到39/50，剩余11次，不能直接沿用之前“最多15次”的许可重跑，更不能借换 AcceptanceId 重新获得额度。该受控跨库账本也不能冒充普通用户的全局自动预算系统。

【建议】完整学习地图和当前详细执行范围要在草案说明中清楚。不能为了测试预算删掉完整路线关键环节，也不能一说“系统学习”就自动生成全部61阶段。

本轮用本地预置内容+Fake+隔离PG+Edge展示修正路线，不再付费生成。下一收费方案先由代码重算阶段数、用途请求、repair与真实账本，再单独批准。

另外，practice 中相当多模型输出最后被 blueprint 覆盖；之后值得核对哪些调用真正带来个性化增量。但现在不建议为此取消整套生成阶段、重写协议或扩大修复范围。

来源：S5、S11，及本轮用户提供的 v6.8 用量。

## 10. 与上一条 v6.9 建议相比，必须校正的地方

1. 不能只把 A8 设为 broad 默认：还要补对应项目绑定，否则前端仍无项目卡。
2. 不要只用更多关键词补丁解决 complete/narrow/first step；首先明确本次学习范围。
3. 不要把实践 carrier 自动当作成熟源码对比案例。
4. 不要平台维护每个项目的永久“文件阅读地图”；地图仍由外部 AI 学习时生成。
5. 不是现在必须重写整个 UI；已有组件只做配对、多候选、续片消费等薄修。
6. 两类项目学习按目标分层，不要求每条窄路线固定凑一小一大两个仓库。
7. 旧真实生成 Plan 不原位改；修正后的新样本明确标记 Fake 生成或确定性新内容样本，不冒充 v6.8 原始真实输出。

## 11. 建议实施顺序

第一批：修目标选择与项目学习路径（F1/F2），补完整路线与窄目标对照，生成零费用新样本。

第二批：修实践/参考项目角色、具体任务适配和项目卡消费（F3/F4）；与第一批可在不同文件并行，合并前验收数据契约。

同批内容修正：只改本次触及的学习目标措辞与必要入口缺口（F5/F6），不要重做三方向研究；证据不足的项保持待审并明确影响。

最终：无付费的端到端语义验收（F7），保留 v6.7/v6.8 真实证据，不宣称新选择规则已通过真实模型。

不新增表、另一个 planner、模型预摘要、clone worker、mastery系统或新的 RAG。若现有模型确实不能承载一项要求，先拿具体冲突与最小替代方案报告，不悄悄扩架构。

## 12. 不应回退的现有实现

- stage_skeleton_v1 与短 outline 的内部白名单。
- old/new manifest、hash/fingerprint、checkpoint 兼容和不可变历史。
- canonical 资源、章节、依赖与验收保护；修的是冻结前适配，不是放宽冻结后篡改。
- 用户明确确认计划和变更；旧 Plan/总结/成果不被新内容版本覆盖。
- RLS/归属/CSRF/请求账本/unknown 不重派。
- ProjectStudy Prompt 的本地当前源码工作流与只复制不调用。
- 正文免费与实践费用分离、中文优先、hold 不误发布。
- 不把源码大项目全仓掌握作为普通学习者硬门槛。

## 13. 验收的正确层级

技术生成：模型返回、解析、持久化、恢复与计量。

规划语义：目标范围、前置、重复、实践/参考项目、可选边界。

内容质量：章节与能力匹配、例子可理解、教程可达、练习可执行。

实际用户接受：用户愿意照着学，能看到完整路径并理解下一动作。

v6.8 已通过其有界技术代表，不能因本次语义问题否认该事实；也不能因 v6.8 PASS 跳过后三项。本轮目的是补齐后者，不是再刷一次模型成功。

## 14. 关键来源索引

以下链接都固定到本次审查提交，仅用于**实现审计取证**；这不改变“用户学开源项目不锁源码版本”的产品原则。

- **S1** [backend/app/domain/planning/semantic_content.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/domain/planning/semantic_content.py) — adapt_semantic_pack：默认/触发/排除/闭包/载体适配
- **S2** [backend/app/infrastructure/domain_pack.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/infrastructure/domain_pack.py) — pack_key_for_goal、runtime_pack_key_for_goal、CURRENT_PACKS
- **S3** [backend/app/tools/map_semantic_content.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/tools/map_semantic_content.py) — BINDINGS、selection、依赖/节点/项目targets与章节资格
- **S4** [backend/app/domain/planning/intent.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/domain/planning/intent.py) — GoalSpec、required_module_closure
- **S5** [backend/app/agent_workflows/planning_batches.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/agent_workflows/planning_batches.py) — freeze_manifest、merge_batches、canonical practice/knowledge
- **S6** [frontend/src/features/learning/ProjectStudyCard.tsx](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/frontend/src/features/learning/ProjectStudyCard.tsx) — 单一find、卡片显示与Prompt上下文
- **S7** [frontend/src/content/projectStudyPrompt.ts](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/frontend/src/content/projectStudyPrompt.ts) — 外部AI学习提示词与URL规范化
- **S8** [frontend/src/features/learning/MainWorkspace.tsx](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/frontend/src/features/learning/MainWorkspace.tsx) — 项目卡挂载与普通扩展过滤
- **S9** [docs/research/semantic-corrected-2026-10-04/AGENT_APPLICATION_TEMPLATE_PRODUCTIZED.md](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/docs/research/semantic-corrected-2026-10-04/AGENT_APPLICATION_TEMPLATE_PRODUCTIZED.md) — A0–A8、专项与项目/载体语义
- **S10** [backend/app/application/draft_projection.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/application/draft_projection.py) — 扩展投影与草案实体字段边界
- **S11** [backend/app/application/plan_service.py](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/application/plan_service.py) — _freeze_submission 与新Run冻结顺序
- **S12** [docs/research/semantic-corrected-2026-10-04/PLANNING_SEMANTICS_STANDARD.md](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/docs/research/semantic-corrected-2026-10-04/PLANNING_SEMANTICS_STANDARD.md) — 开放Recipe、Continuous Outcome Carrier、候选项目定义
- **S13** [docs/implementation/progress.md](https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/docs/implementation/progress.md) — v6.8及先前实现验收范围
