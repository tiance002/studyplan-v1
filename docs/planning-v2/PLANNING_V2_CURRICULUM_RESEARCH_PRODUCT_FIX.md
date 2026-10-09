# Planning V2 课程语义与教材研究策略定向修复

任务：`PLANNING_V2_CURRICULUM_RESEARCH_PRODUCT_FIX_V1`。日期：2026-10-10。

结论：`CURRICULUM_PRODUCT_SEMANTICS_PASS`、`RESEARCH_POLICY_OFFLINE_PASS`。这是版本化实现、合成材料和真实 owned PG/HTTP 的定向技术验收；`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`。真实教材与生成课程的教学质量未验收，不能由 Mock 资格或结构校验代替。

## 1. 基线、授权和范围

Start HEAD：`d41435038798efead87a8ccc7610d89d745a6e73`；分支 `feat/n1-resource-discovery`。开始时 tracked tree clean，既有 `.workbuddy/`、`design-preview/` untracked 保留、不读取、不操作、不提交。Final HEAD 在提交后完成回执和答复记录，避免报告自引用自己的提交 SHA。

复用已通过的184真实 Profile、187真实 Plan及既有 Item 3/4 检查，不重新调用 Item 1/2，不改 Profile、Policy、能力定义、Gap、coverage、正式配置或预算默认值。允许的上位合同最小修订已先写入架构合同第13节，再实施对应代码。没有新 Agent 产品角色、权限系统、评分引擎、教材数据库或 migration。

外部模型、Tavily、GitHub网络、Reader、教材正文、价格余额 preflight **均0**。本文的 Reader/search/body 次数全部来自本地 Mock。正式数据库写入0；仅创建全新 owned 测试数据库。无 push/merge/deploy，公共 generate 仍503。

## 2. 最小版本差异与历史保护

新 owned 提交由服务端冻结 `product_semantics=planning-v2-product-v2`，参与 manifest hash；Provider schema 根据冻结 manifest 选择，恢复不升级旧标记。无标记保留旧路径。新研究为 `research_comparison_v2` / `ResearchReaderV2`；新课程为 `CurriculumPlanV2` / `semantics_version=2`；编译及执行快照分别为 `CompiledCurriculumV2`、`V2ExecutionSnapshotV2`。Schema/Policy v2的既有能力定义及其引用不改。

旧默认新增字段在 legacy序列化时省略，研究输入/hash与旧编译内容保持原值。新 Curriculum允许消费冻结 legacy Research，但比较状态仍legacy，不授予新的质量资格，不改其hash；新 owned Runtime只生产新研究规则。未知版本、派发/恢复绑定不符仍拒绝。

同一冻结合成输入分别经过 d414350源码和当前 legacy路径，六个hash完全一致：研究、课程上下文、课程结果、编译、执行快照、研究checkpoint。另独立审查直接加载旧研究类，结果序列化、结果hash、快照字段hash也一致。范围是这些代表性冻结事实，不是穷举全部历史Run。

## 3. P1：教学义务与运行权限

`permission_obligations[]` 保存原 `constraint_ref/source_refs`、原 `project_context_hash`、实际 `task_ref/outcome_refs/acceptance_refs`；要求 `authorization_before_execution/default_deny/input_validation=true`、范围 `user_authorized_local_tasks`，以及六种不同案例的实际验收索引和产物。`practice_artifact` 保存授权记录、输入输出和JSON差异等具体交付要求。

服务器校验闭字段、唯一合法引用、项目绑定、六种案例完整性、不同验收与产物；独立语义审核判断这些内容是否真的承担教学义务。仅“安全承诺”、伪造项目/task/ref、缺案例、任意本地文件范围、将运行状态写成verified均拒绝。

正向合成示例使用实际 `tool.calling` Task，在现有待办CLI/JSON文件中安排：用户先列允许任务ID和操作；未授权默认拒绝；授权A不能访问B；非法参数不invoke/不写文件；执行失败不产生部分写入；逐例检查JSON字节或授权字段差异。保留原项目，不创建新的演示项目。

服务端 assessment只把 `local_tool_scope` 的 **planning_status** 记为arranged；**runtime_status始终unverified**。它没有授权任何工具调用。其他readonly/no_network/privacy/unknown保护及existing_carrier原文要求保持。未来真实Practice/Outcome证据仍需后续审核；本轮不实现运行权限验证。

## 4. P2：必学完整性与推荐缺口

服务端 `required_curriculum_outcomes` 统一承担必学、明确学习选择和真实先修闭包；Validator与Compiler通过同一上下文验证结果。

- required缺材料或安排，或其真实先修缺失：incomplete。
- 已选教学阶段中的未解决内容：incomplete，不能以recommended标签冒充材料已充分。
- 明确 `learning_target_refs` 对应的推荐能力不可被整段静默省略，即使教材已经可用。
- 未纳入教学、非必学先修、非用户明确选择的recommended缺口：可与完整必学课程并存，但保留原importance、missing原因及来源。

新合同的 `unresolved[]` 原样进入编译、Draft、Revision和HTTP `v2_content`。没有改变CapabilityPlan的重要性。旧课程仍采用原完整性规则。独审发现的“教材可用时省略明确推荐目标仍complete”反例已修复，新增定向测试保留。

## 5. P3：派发、比较与跨能力复用

**必学优先。** 只改变内部工作顺序：required缺口先于recommended；最终ResearchResult仍按冻结Gap的canonical顺序，原Gap hash、requirement refs、深度、重要性均不变。required无法闭合时保留具体missing及预算原因，不追加额度或删目标。

**有限比较。** 保留Reviewed→GitHub教程→Web教程的既有发现层级及既有精确补充职责；新路径在共享预算内审读已发现、获准且可比的有限候选，不因第一个中文候选达到准入阈值立即跳过后面的候选。四维质量意见（连贯教学、起点适配、示例、版本）必须有短rationale和正文chunk/hash引用。`insufficient/unknown`不构成合格资源，正常保留missing。

通过实际outcome覆盖与四维质量的支配关系形成有限偏序，没有分数；仅覆盖和各维类别相当时中文优先。互不支配、单一候选、缺质量证据或预算截断均明确比较不足。`comparison_status/order/reasons`和带来源的意见传入Item6；Item5不输出PRIMARY，也不声称全局最佳。最终教材角色仍由Item6决定，模型语义意见不是独立质量认证。

**跨能力。** 最多六个获准、依赖相邻、相同desired_depth且仍缺失的outcomes联合审读；不合并整张Plan，不重审Coverage已经支持的MCP理论。同URL并不意味着所有能力已审核。成功范围可以复用；同候选/版本/深度的新增范围先扣除已审范围，只审新的outcomes，不重复旧成功。更深要求不能使用浅层资格。合并同来源的质量意见保守保留较弱类别，避免早先strong掩盖新增范围adequate。

内存缓存绑定候选发现身份、URL、深度和已审范围；正文结果携带实际来源版本。Durable Reader恢复再匹配schema、rules、candidate_identity（发现信息+深度）和exact scope。Body请求也绑定review_scope与review_identity；新范围/版本/深度使用新预算身份，已有成功Reader在正文获取之前复用。孤立body metadata回执无正文时继续阻断，不能重派旧身份。所有正文finally清除，持久化仅短意见、来源、范围及hash。

## 6. 六组真实Gap的离线预算测算

原Profile：`b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348`；原Plan：`e14f5f95c01570784d4b8387e842202a2f6a464ee7f6d06eb5bf71066e38b837`；Coverage：`07030b56e26433e518b34f812cccce9de71a7dcb63c44929c1b0cb180a25d183`；Gap：`141b925fd307e98996b6f34280b24fcc8be17f31d3ab78fdd7e679686ad80315`。原Validator重建并核对全文/hash。12待学outcomes中2MCP理论已有审核覆盖，10missing=8required+2recommended；Python不进入研究。

没有改变原ResearchBudget：4搜索、8candidate预约、4Reader、4096累计Reader输出、16研究请求、262144正文bytes、内部cost_micros100000。两个Mock测算都用原六Gap，保留正文/输出最坏预约，不假装实际usage。

| 合成发现方案 | 搜索/正文操作/Reader | 派发顺序与结果 | 比较事实 |
|---|---|---|---|
| 同一候选可教多个范围 | 4/4/4 | llm.api联合structured及tool输入→MCP→仅tool.invoke_result新增范围→error.permission；8必学missing闭合，eval.lite仍缺 | 全部单一候选，比较不足 |
| 两语言候选有限比较 | 4/4/4 | 两次llm联合范围、两次MCP；tool.invoke_result仍缺，两项recommended缺 | llm/MCP/structured有限比较充分，tool部分覆盖，不能生成完整必学课程 |

两方案Mock累计预约计量都是16请求、4096输出、内部84000（4×20000+4×1000），实际短合成body280bytes。每次正文仍在派发前预约65536bytes/最多2HTTP；4操作最坏262144bytes/8HTTP。候选数为4或8。内部cost_micros不是人民币，不是现金硬门禁。

若将每个新增required范围都做两候选比较，此代表至少6Reader（LLM联合2、MCP实践2、tool新增2），超出原4Reader；不含推荐范围，也不保证真实教材足够。对应候选测算为6144Reader输出、393216正文bytes/12HTTP、最多6搜索/24研究请求、内部126000；整链3基础模型再加6Reader的条件测算是9模型/18432输出/27外部请求、内部186000。这仅是Owner未来评估的参数，不写入默认预算、不授权调用，也不承诺搜索分布或教材质量。原一期7模型/4Reader条件没有因本修复自动增大。

以上100000是独立研究测算用的现有默认上限，不是整链Root预算充足证明。未来新Run若包含3基础模型+4Reader+4搜索，并且三笔基础模型每笔冻结4096输出，最坏须同时容纳16384输出、19请求、内部144000；默认100000本身不足。前述六Reader整链数字也以三笔基础请求各4096为条件，实际配置若更高须重新计算，不把候选数字冒充派发许可。只能在Owner明确的候选额度与既有owned冻结准入内检查，不能将独立研究测算误当整链已可派发。本轮复用原184/187，不重发两笔来获取新预算根。

ReaderV2仍1024输出，六outcomes+四维意见在真实模型中能否完整生成未验证；遇到截断不能repair追绿。真实教材资格、免费正文、来源版本及实际章节适配仍需下一轮单独授权后核查。缺资源时正确incomplete不属于本轮算法FAIL。

## 7. 实际改动及消费者

| 文件 | 关键职责 |
|---|---|
| `domain/planning/constraint_adaptation.py` | local_tool_scope新规划assessment，旧约束策略版本不变 |
| `domain/planning/curriculum.py` | prepare版本、比较投影/身份校验、义务Validator、共享必学闭包与complete规则 |
| `domain/planning/curriculum_compiler.py`、`v2_execution.py` | 同规则编译、原事实保全、版本快照、user_content读回 |
| `application/curriculum_composition.py`、`providers/curriculum_contract.py` | 选择冻结schema、专用新课程shape/说明 |
| `application/teaching_resource_research.py` | required派发、有限比较、新范围/深度复用、保守合并 |
| `domain/planning/resource_research.py`、`research_reader.py` | 小型版本化元数据、legacy省略、Reader短证据合同 |
| `providers/research_reader_contract.py`、`openai_compatible.py` | 专用ReaderV2/课程V2序列化；原preflight保护保持 |
| `domain/planning/v2_runtime.py`、`providers/runtime_factory.py` | owned冻结标记、schema选择、旧恢复不升级 |
| `checkpointer/v2_planning_runtime.py`、`providers/v2_attempts.py` | 版本化快照/receipt、exact范围/版本/深度身份、原durable预约/fence复用 |

以上路径均在 `backend/app/`。另新增四个unit文件（curriculum_product_v2、product_fix_boundaries、product_semantics_manifest、research_comparison_v2）、一个owned PG文件 `backend/tests/integration/test_product_fix_pg.py`，以及明确标注原184/187与合成材料区别的fixture `backend/tests/fixtures/planning_v2/product_fix_184_187.json`。文档为架构第13节、本报告及progress。Provider文件还修正两处既有单行Python语句格式，无行为改变。无前端、正式API、数据库schema、Policy、原审核映射或历史文件改写。

## 8. 定向验证和独立审查

证据目录：ignored `var/planning-v2-product-fix-20261010/`，不含凭据、认证头或真实教材全文。

| 验证 | 实际结果/证据 |
|---|---|
| RED | root-red.log：2FAIL/1PASS，先定位owned版本派发接缝；后续反例随独审补齐 |
| 最终受影响unit/Provider/Validator/Compiler/旧约束回归 | 12文件，283PASS，exit0；final-targeted.log/.exit |
| owned PG +真实HTTP | 3PASS，exit0；final-owned-pg.log、pg/*readback.json：Draft→显式合成确认→Revision→fresh PG→cookie HTTP current/history，完整义务/推荐缺口保留；generate503 |
| durable恢复 | 同scope恢复1调用；新来源版本2；同outcomes新深度3；深度恢复仍3；body均close |
| 旧版本代表hash | 六hash完全相等；baseline/current-legacy-hashes.json及final-audit.json |
| Ruff / git diff --check | PASS / PASS，native exit0 |
| 保护审计 | 514个.env/旧账本/历史真实证据文件hash保持；无新增历史目录文件，无migration差异 |
| 真实收费模型/搜索/正文/Reader/账户及浏览器 | NOT RUN，本轮未授权；全量Backend/React/浏览器矩阵NOT RUN |

初次PG检查1FAIL/1PASS是测试将原wire排序与Validator规范化后的数组直接比较；改为比较validated Curriculum，正式持久化逻辑未为该失败放宽。depth-green中的1FAIL是测试读错learner_context字段路径，已修正；负质量测试的字段名错误也修正。旧失败记录不当作产品PASS，不掩盖真实历史185/186失败。

独立审查使用独立上下文、实际源码/diff/合同及证据，未由实施者自评替代。确认并关闭：可用教材下明确推荐目标静默省略；候选新版本复用旧receipt；浅审跨深度扩张；新深度正文metadata-only身份碰撞；单候选误称比较充分。合成权限任务的教学内容独立检查PASS；真实教材/真实生成课程语义仍NOT RUN。

请求的开发模型路由为Sol6.1 medium有界实现、Sol6.1 xhigh关键引用/安全独审；主会话无法切换或核实模型解析，实际均记 **NOT OBSERVABLE**，不把角色名当实际模型身份。部分实施代理达到usage limit后由主协调完成代码，最终审查由独立closing reviewer完成。没有产品第二Reviewer或通用评测平台。

## 9. 剩余风险和结束

当前技术实现可以准备受控真实资源/课程验收，但不宣布真实课程已合格。必须另获Owner授权：具体研究范围、模型/搜索/正文/Reader次数、预算与无严格现金硬上限风险，以及实时来源/价格/余额预检。有限比较仍可能不足或消耗预算后留下required缺口；返回incomplete并保留原因。已审核内容的身份检查不等于正文教学质量，本轮合成材料不升级为真实审核教材。

未来真实验收还要独立检查章节是否覆盖目标、质量取舍是否合理、权限任务和continuous practice是否连贯、用户现有项目是否完整保留。本轮owned HTTP证明字段保全，React展示和浏览器用户体验未重验。旧历史Run仅做版本代表回放及现有保护复用，没有恢复历史unknown177/183。

最终：`CURRICULUM_PRODUCT_SEMANTICS_PASS` / `RESEARCH_POLICY_OFFLINE_PASS` / `REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`。本地提交后 **STOP**；不自动开始收费教材研究、公开生成或发布。
