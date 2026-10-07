# Planning V2 — Item 1 Goal Requirement Analysis

日期：2026-10-07。上位合同：[PLANNING_V2_ARCHITECTURE_CONTRACT](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。本文件只记录 Item 1 实现与证据，不增加跨模块架构权威。

## 结果与基线

本项实现 GoalSpec / 自然语言 → 单次 Goal Requirement Analysis → validated GoalRequirementProfile。没有 Capability Policy、Item 2、课程、资源研究、Compiler、新图或生产接线。公开生成仍 fail-closed；真实模型语义代表验收和真实 PG 均 NOT RUN。模块完成不表示完整 Planning V2 或全产品 READY。

- branch：`feat/n1-resource-discovery`；start HEAD：`31513e960723414645e4d3332c29718b603c96bd`，与用户预期一致。
- 开始 tracked tree 干净；原 `.workbuddy/`、`design-preview/` 未访问/修改/提交。
- 主协调请求 Sol6.1/high；路径/测试清点 Luna/medium；Provider 实现、实际调用链与独立审查 Sol6.1/medium。实际解析全部 NOT OBSERVABLE；无 HARD 升级、无全局配置修改。
- 本地提交消息：`feat(planning): add v2 goal requirement analysis`。final SHA 在提交后答复，避免自引用；不 push/merge/deploy。
- 可恢复 checkpoint：ignored `var/codex-goals/planning-v2-item1.json`；证据目录：ignored `var/planning-v2-item1-20261007/`。

## 先审计后实现：A～F

| 问题 | 只读结论与接缝 |
|---|---|
| A 六类事实进入 generate | `api/v1/schemas.py::GoalSpec` 嵌套在 `PlanGenerateRequest.goal_spec`；`api/v1/routes.py::generate_plan` 用 `model_dump(mode="json")` → `goal_spec_from_payload` → `PlanService.submit_generation`。target/scope/desired_depth/starting_point/outcome_purpose/constraints 均可表达；服务在 scope 后直接拒绝，不存 Run/Job、不绑定/调用模型 |
| B 序列化/hash/保存 | `domain/planning/intent.py::goal_spec_payload` 被 frozen manifest、`PlanDraft.content_hash`、`PlanRevision.structure_fingerprint` 及 `db/plan_repository.py::_draft_payload / _structure_payload` 使用；DB 读回用 `goal_spec_from_payload`。不是任意新增字段自动落库，必须经过该显式 helper |
| C 最小 project_context | Domain/API 现有 GoalSpec 增加可空 string，最多2000字符。Domain 去首尾空白，空白归 None；helper 对 None 省略键。旧六字段 payload/canonical hash 保持；非空背景进入其独立字段，不混入 target/constraints。现有 Draft/Revision serializer/hash 可显式携带；本轮未执行 DB 保存 |
| D 可复用 transport | 现有 LLMPort/LLMResult/LLMFailure、typed dispatch exceptions、JSON mode、HTTP/endpoint guard、usage、严格 JSON、truncation/unknown，无自动 retry。新 purpose 必须单独绑定 schema/preflight/system/budget 分支 |
| E 禁止复用 | 旧 OUTLINE_SYSTEM/OUTLINE_SHAPE、structure/practice shapes、route selector/Seed、默认完整路线 prompt、旧 repair/manifest/ledger 的业务解释。仅向 SHAPES 加键会继承旧 route prompt，已用专用 system 明确隔离 |
| F migration | Item 1 无持久化接线需求；输入经既有可选 GoalSpec 和 JSON serializer 表达。migration=0，0025及全部既有 migration bytes 保持。Profile 没有新表/Repository；正式 durable Runtime 留给 Item 7 |

## 实现职责与最终合同

| 文件 | 职责 |
|---|---|
| `backend/app/domain/planning/intent.py` | GoalSpec 可空 project_context；空值省略保证旧序列化/hash兼容 |
| `backend/app/api/v1/schemas.py` | 同一现有 GoalSpec 输入字段最小扩展，不新增竞争目标 DTO/endpoint |
| `backend/app/domain/planning/goal_requirements.py` | 冻结 Profile/Requirement/Constraint/Claim；确定性 Validator/identity/hash，不依赖模型/网络/DB |
| `backend/app/application/goal_requirement_analysis.py` | GoalRequirementAnalyzer，只执行一次 LLMPort 调用并返回 Profile 或现有 LLMFailure；typed dispatch exception 原样传播 |
| `backend/app/infrastructure/providers/goal_requirement_contract.py` | Item 1 专用 wire shape/system；exact purpose/schema/input 归属预检 |
| `backend/app/infrastructure/providers/openai_compatible.py` | 复用通用 transport，仅新增目的分支，既有共享 HTTP/JSON/失败处理尾部、global prompt_version、预算配置不改 |
| `backend/tests/unit/test_goal_requirement_analysis.py` | 12类代表/结构场景、policy/raw authority 两组边界、确定性、事实保护及失败传播 |
| `backend/tests/unit/test_goal_requirement_input.py` | optional 输入/hash/serializer兼容与包含项目背景的公开 route 仍拒绝 |
| `backend/tests/unit/test_goal_requirement_provider.py` | 31项 MockTransport 新目的/预检/JSON/usage/truncation/unknown 测试 |
| `backend/tests/unit/test_planning_intent.py` | 两个既有失败用例更新过期 frozen/Fake setup；一处旧结构字段断言对齐实际 learner 投影，补充 manifest/practice 完整事实断言，hash/最终实践保护保留；无生产协议恢复 |
| `contracts/openapi.json` | 重新导出现有 GoalSpec 的 optional 字段 |
| `frontend/src/api/generated/schema.d.ts` | 工具生成的可空类型，仅新增 `project_context?: string \| null`；无页面/组件/CSS修改 |
| 本报告、`docs/implementation/progress.md` | 本项证据、限制、唯一进度入口；上位架构合同原文保持 |

Profile 最终 JSON 字段：`schema_version`、`target_summary`、`scope`、`desired_depth`、`starting_point`、`outcome_purpose`、`required_requirements`、`hard_constraints`、`learner_claims`、`project_context`、`clarification_questions`、`status`、`profile_hash`。

`starting_point` 是上位合同要求保留的事实，不是未来预留字段。scope/depth/starting_point/purpose/project_context 从已校验输入确定性复制，不让模型改写。Requirement 为 requirement_id/text/origin/source_refs/rationale；Constraint/Claim 各为其 ID/text/source_refs。origin 仅 explicit/inferred_required，后者 rationale 必须非空。

模型 wire 只输出七字段：schema_version/target_summary/required_requirements/hard_constraints/learner_claims/clarification_questions/status。模型条目不输出 ID/hash；程序以既有 canonical_json/content_hash 生成确定性 identity，引用排序并拒绝重复 identity；Profile hash 只覆盖 validated payload。时间、tokens、latency、request/run/attempt ID 不进入语义 hash。extra fields 一律拒绝，不静默吞业务字段。

source_refs 仅限当前输入实际存在的字段：goal.target、goal.scope/有效索引、goal.desired_depth、goal.starting_point、goal.outcome_purpose、goal.constraints/有效索引、project_context（解析到 GoalSpec.project_context）。结构化 constraints 每项要求原文保留并引用对应索引；这是可证明的输入事实保护，不是 NLP 解释。ready 必须非空 requirements、无问题；needs_clarification 必须1～3问题。没有分数、技术推荐、能力、Stage/Resource、mastery 或 accepted_known 字段。

Analyzer 接受单一 GoalSpec（target 承载自然语言）或将自然语言 string 规范化为同一 GoalSpec；输出只返回 Profile，不返回 raw GoalSpec/raw target 供下游再次分类。没有实现 Item 2 consumer 或 `raw_goal + profile` 双权威接口。未来 Consumer 只收 Profile。原始输入只用于本项与来源审计。

## Provider / 可靠性边界

新 purpose=`planning.goal_requirement_analysis`；schema=`GoalRequirementProfileV1`。输入只能 `{"goal": goal_spec_payload(spec)}`，拒绝 domain_pack、旧 markers、额外上下文；模型请求使用独立 system/shape，不继承旧路线语义。新输出预算取既有 practice/deployment/model cap 的 min，不追加全局额度/预算字段。

| 情形 | 结果与本项行为 |
|---|---|
| local schema/input reject | LLMFailure，dispatched=False，模拟HTTP0 |
| endpoint guard reject | 既有 LLMNotDispatchedError 原样传播，无调用/重试 |
| HTTP明确拒绝 | provider_http_rejected，known failure |
| timeout / HTTP5xx | provider_transport_unknown / provider_server_unknown，dispatch_unknown=True，无盲重试 |
| malformed/fenced JSON | provider_invalid_json，保留usage，不本地截取/repair/再次调用 |
| length | provider_output_truncated，先于JSON解析；自定义Port返回length也不能成为Profile |
| envelope/非object/缺wire字段 | 既有 invalid_envelope/invalid_shape，不能空成功 |
| wire合法但domain结构无效 | goal_requirement_profile_invalid，保留计量事实，不返回Profile |
| wire和domain结构有效 | 返回冻结Profile；不声称语义一定正确 |

run_id/attempt_id 是必需调用身份，**不代表 durable receipt 已存在**。本项不创建 Worker/ledger/receipt/Run，不接 PersonalPlanningRuntimeFactory，不自动重试/repair/挂起/恢复，不使用旧 known-JSON-failure attestation。正式运行配置、prompt绑定、预算/回执与重启恢复留给 Item 7。

## RED、验收与已知基线失败

所有证据保留在 `var/planning-v2-item1-20261007/`。使用现有 `.venv/Scripts/python.exe`，未安装依赖。最初 PATH pytest 指向缺 psycopg 的另一环境，root RED 同时显示新 Analyzer 模块未实现及该环境缺依赖；原日志未覆盖。仓库 `.venv` 的旧 launcher-location 提示虽存在，实际 imports/tests 可运行，不把提示当产品失败或已修复。

| 检查 | 状态 | 实际证据/范围 |
|---|---|---|
| 实施前 RED | FAIL | root-red.log/xml：新 Analyzer 未实现+PATH缺依赖；provider-red.log/xml：26个 unsupported-purpose 预期失败；均在实现前添加测试 |
| 必需范围去重证据 | PASS | evidence-packet.json：273项最终有效PASS（新增92+既有181）；从实际XML按test identity复用最新结果，不是声称另一次273项完整执行；旧FAIL原XML保留 |
| Item 1 targeted | PASS | root-regression.xml 内61项新 Analyzer/input；provider-final.xml 内31项，共92项最终新增用例全部通过，不把首次56项与后续重复累加 |
| 必需 GoalSpec/intent | PASS | intent-fixture-final.xml：5PASS；首次3PASS2FAIL及中间4PASS1FAIL保留；只修测试setup与过时字段断言，未改生产保护 |
| auth/scope/current read/fail-closed/DTO | PASS | root-regression.xml 其余受影响用例：401/scope优先、503、零依赖访问、session/current空态、组合根无Fake fallback、OpenAPI fresh一致 |
| structured provider/JSON/truncation保护 | PASS | provider-regression.xml 中 b3_provider、b3f2_planning、known_json_repair、assistant_v11、assistant_final_practice 与新provider用例177PASS；没有修改repair资格/次数 |
| 额外旧 partial-content suite | FAIL | 同次provider-regression.xml 的20项：旧markerless bootstrap在_initial_state/provider调用前拒绝；test/batches/nodes blob与31513e9相同，baseline旧provider代表case同FAIL。该HOLD旧suite不作为本轮已通过证据，不修旧语义追绿 |
| backend 全量 collection | PASS | backend-collection-final.log：2049 collected，无collection/import error；不是全量测试运行PASS |
| OpenAPI / TS | PASS | fresh export + gen:api；frontend-types.log：tsc；类型仅optional字段 |
| Ruff | PASS | 新/本项文件完整规则；旧provider仅忽略其既有E701/I001，原两处单行与局部import保持 |
| diff / 不变量 | PASS | git diff --check；28份架构合同/placeholder/.env/migration哈希保持；上位合同无改动 |
| 真实 PG/checkpoint | NOT RUN | 本轮无DB写入/真实PG业务验证；不以TestClient、静态serializer或Fake冒充PG行计数 |
| 产品真实模型/搜索/浏览器视觉 | NOT RUN | provider全为MockTransport/Fake；无页面变化，未重做视觉验收；语义真实代表另需明确授权 |

必需回归命令包含新Analyzer/input、test_planning_intent、test_planning_residual_cleanup、test_planning_legacy_removal、integration/test_app_boot、contract/test_v1_dto_contract；shared provider命令包含上述JSON/assistant保护及额外旧partial suite。使用 `--confcutdir=backend/tests/unit` 避免无关顶层PG自动探测；首次provider RED 的顶层conftest存在只读probe，不是本轮真实PG验收。

两个 intent 基线失败为 `test_frozen_context_reaches_batches_and_is_in_draft_revision_hash`、`test_purpose_requirements_survive_generation_merge_and_only_affect_final_practice`。`intent-baseline-stale-fixtures.xml` 以31513e9的intent/provider内存加载复现2FAIL，test/structure/guided/helper hash一致；两者均在旧输入缺 reviewed_structure marker 时拒绝。迁入现代冻结与test-only Fake后，中间4PASS1FAIL显示另一个旧断言要求当前structure不再消费的完整goal_spec。对齐为当前learner三字段精确投影，并新增manifest/practice实际consumer的完整GoalSpec相等；Draft/Revision hash与最终用途唯一性原断言保留，最终5PASS。没有恢复旧raw goal字段或放宽生产门禁。20项额外partial失败由 `provider-stale-baseline-evidence.json` 与 `provider-baseline-stale-fixture.xml` 记录；旧FAIL保留，不能宣称全部backend regression通过。

## 独立审查、语义限制及最终门禁

独立只读 Item 1 审查按五原则与额外边界检查，结论 PASS：无错误前提、双权威、课程政策提前注入、无消费预留字段或不必要平台；Python/interview/project_context/raw-goal/validator/public generate/旧shape边界均有对应保护。同一审查者仅增量核对intent测试差异，确认完整事实/hash/最终用途保护未削弱，结论PASS；没有重复全仓审计。审查为开发审查，不是产品第二AI Reviewer；没有HARD升级。

特别保留 `SEMANTIC_EVAL_REQUIRED`：Fake故意输出“必须学习MCP”且合法引用goal.target时，结构Validator可以通过；程序没有能力证明该语义来自用户。测试同时证明程序不从selector/Seed/旧Prompt自动加MCP。不能把前者隐藏或建设关键词黑名单假装解决。Python事实是否被真实模型正确抽取、用途是否扩课、推断/歧义是否合理，仍需用户另行授权的真实代表验收。

公开 generate 未注册 Analyzer，仍scope后503；新Run=0、Job=0、产品provider调用=0、Plan mutation=0 是依赖访问前spy/HTTP门禁证据，**不是本轮真实PG行计数**。产品真实模型调用0，搜索0，DB写入0，migration0。没有旧余额消费、历史Run/unknown恢复、Seed/Worker/正式入口/RAG改动。

无 Item 1 实现 BLOCKER；已知旧partial夹具FAIL与真实语义/PG/完整Runtime未验证明确保留。与架构合同无偏差：新增starting_point落实上位事实要求；project_context是其已列明I1门禁的最小实现；正式持久化/课程/能力不提前实施。

回滚用正常 revert 本地 Item 1 提交；无DB回滚需求，不恢复旧Planning。收口后状态为 **PLANNING_V2_ITEM1_GOAL_REQUIREMENT_ANALYSIS_COMPLETE / ITEM2_NOT_STARTED / STOP**，全产品继续 STAGING_BLOCKED / NOT_READY。
