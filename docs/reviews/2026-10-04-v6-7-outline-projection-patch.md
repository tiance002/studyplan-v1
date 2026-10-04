# v6.7 Outline Projection Patch：OUTLINE_PROJECTION_PATCH_READY，STOP

用户现在新增能做什么：未来新提交具备冻结 outline 骨架投影及 canonical 知识/实践保护，可据本批离线和 owned PG 证据评审下一单一收费代表。正式入口与 Worker 尚未启用，本轮没有真实模型 Plan。全产品仍 **STAGING_BLOCKED / NOT_READY**。

依据：[批准的 v6.7 Goal](../implementation/STUDYPLAN_V6_7_OUTLINE_PROJECTION_PATCH_GOAL_2026-10-04.md)。Downloads 原文逐字节归档，用户明确批准实施 Option1、同时修复两个保护缺口，真实产品模型请求必须为0，完成后STOP。复用 v6.6 归因与既有能力，无重新调查旧G1或课程重做。

## Baseline 与代码范围

- 基线：`feat/n1-resource-discovery` / `df10870add16d658cd706ec26e021d276db0932d`；tracked clean，仅两受保护未跟踪目录。续接该分支，无reset、切分支、push、merge或master操作。
- 新 `planning_outline.py` 是局部 pure projection/短system/shape/结构大小门禁。`nodes.py` 消费冻结格式并严格验证阶段集合、顺序、键、非空标题/目标与越权字段。
- `PlanService._freeze_submission` 仅未来新提交请求 `outline_input_format=stage_skeleton_v1`；`freeze_manifest` 默认无字段，marker进入原manifest_hash。无API/DTO/schema/migration/Seed/预算/模型/cap变更。
- `OpenAICompatibleLLM` 只按 planning.outline 内部marker选择短契约；marker保留在attempt semantic payload指纹中，过滤后不外发。全局 `prompt_version` 仍 `v2-g2-v8-resource-roles`，旧structure/practice/repair模板与purpose预算不变。
- `planning_batches.py` 的新格式merge恢复canonical事实；无marker调用冻结旧merge。新增checkpoint完整性检查位于 `planning_executor.py`。
- Fake demo 与旧生命周期测试Fake适配新骨架，旧Fake分支保留。UI、阶段总结、自动阶段完成规则与RAG未改。

## Legacy 与冻结边界

真正markerless且完整的旧manifest保持原hash/wire/attempt identity与merge语义。旧merge函数从基线只读复制，AST与基线函数体等价；恶意legacy fixture的merge golden SHA为 `bbcda7a40c90468a499b6aef98078e56d4712fe2ada74ff40421c3d04d9a7e21`。这用于证明协议兼容，不声明旧格式两类保护缺口已升级。

独立pre-patch golden固定 legacy messages/payload/fingerprint/HTTP bytes，patch后相等。v6.5实际frozen输入只读重建仍为578108字符/816500bytes，HTTP body SHA `4e38d9b03efd39f5d511497c21faac0d560e1e84b37d76043dafba794073cdb6`，与v6.6本地重建一致。历史原wire没有保存，因此没有“与历史原请求逐字节相同”的声明。

复核发现marker移除/置空会绕过最初的入口条件，RED反例确认后补强：任何已有manifest hash先验证完整性，再选格式；新格式还检查pack_hash；merge选择分支前同样检查。真实checkpoint恢复先核对存储digest、与immutable submission的规范JSON等价、新pack完整性，再返回终态或继续图。规范JSON比较兼容tuple→JSON array，不把序列化表示差异当格式切换。删除/置空marker、篡改pack或切换initial manifest均派发前拒绝。

真实PostgresSaver中途checkpoint证实：新旧格式只派发一次outline；恢复读取冻结格式；旧waiting_user拒绝自动续跑，新short terminal重复读取不派发。未改历史manifest/checkpoint，也未恢复v6.5失败Run或旧unknown。

## 新 outline 输入与大小

仅goal、GoalSpec允许字段、简短prefs、semantic_context允许短字段和frozen_stages进入模型。每阶段含键、标题、短目标、kind、本阶段知识的键/短标题/短objectives/必要parent与prerequisite、外部前置键。canonical全文保持本地，摘要仅影响可见性，不覆盖权威值。

禁止全文字段测试覆盖resources/未选source与section、publication_evidence/review_evidence、完整guide/extensions/practice/project-study、全URL与未选教学Markdown。模型输出只含outline_ref与sections(stable_key/title/objective)，越权字段被拒。

| 六阶段同口径 | legacy离线重建 | 新格式 | 减少 |
| --- | ---: | ---: | ---: |
| messages字符 | 578108 | 4112 | 99.29% |
| HTTP JSON bytes | 816500 | 5239 | 99.36% |
| char/4启发式 | 144527 | 1028 | 99.29% |

原provider实报input209998不与启发式混用；实际DeepSeek tokenizer/收费token验证 **NOT RUN**。六阶段fixture守卫6500字符/14000bytes，给4112证据留模板及有限目标变化余量；runtime上限按goal-context长度、阶段数与capability数缩放，长字符串在投影中有界。超结构大小在transport前拒绝。大路线不可误套六阶段常量：owned PG旅行+初学起点选择27阶段，outline context16712字符，测试上限22600。原structure/practice局部输入与legacy逐项相等，完整大包未转移到下游。

## 内容保护与持久化

- 六阶段精确回填：18资源安排、35章节refs、13extensions及全部frozen guidance相等。保留source/version/role/章节范围、hold排除、why-now/exposure、项目候选optional语义。
- 新格式所有reviewed知识（唯一及重复曝光）恢复canonical title/node_type/objectives/scope/acceptance/parent/prerequisites；incoming parent/prerequisite边重建。模型不能覆写知识正文或依赖事实。
- 新格式reviewed practice按blueprint身份与数量恢复goal、范围、deliverable、acceptance、required/optional及知识links。删除模型次级任务/额外Starter及关联，不union任意模型验收；仅保留已有final GoalSpec明确成果增量。
- 本批不开放supplemental task。模型额外任务移除后不进入现有completion gate。现有PlanTaskLink没有optional-task表达，因此新格式对显式 `optional=True` / `required=False` canonical practice在freeze前拒绝，避免错误变成必修；当前三个发布包无该不支持声明，Starter/Project Candidate仍走已有optional extensions。这是有界fail-closed决定，没有扩DTO或阶段完成规则。
- 现有knowledge实体无scope/acceptance列，使用现有 `learning_units.rubric` JSONB保存 `canonical_knowledge`（完整本地blueprint）及 `canonical_practice`（恢复后权威任务快照），取代模型rubric。模型description/hints不进入rubric权威。owned PG查询证实scope/acceptance/parent/prerequisites及practice事实持久化；source_status保留ai_draft，不伪造verified。
- 五语义场景：旅行Agent、无项目Agent、Voice无Recipe、Node Cloud、AI Fullstack既有项目均PASS，保留用户项目优先、Starter fallback、开放Recipe/补审、Evaluation横切与RL optional。

## Tests 与证据

| 层 | 结果 | 证据与范围 |
| --- | --- | --- |
| 新unit/Fake contracts | PASS38 | `var/v67/new-unit.xml`；legacy golden、格式/大小、恶意回填、五场景、精确18/35/13、删除/置空marker与pack篡改 |
| unit + contract | PASS878 / NOT RUN2 | `var/v67/unit-contract-final.xml`；880总，已有symlink权限项未运行；exit0 |
| owned业务PG +真实checkpoint | PASS7 | `var/v67/pg-final.xml`；普通Auth/CSRF、新提交持久化/容器重建、Fake、Draft/显式synthetic confirm/Plan回读、markerless历史fixture、失败不重派、实际checkpoint中途恢复/篡改拒绝 |
| 相邻恢复/生命周期PG | PASS21；单项复核PASS1 | `recovery-adjacent-final.xml`原1FAIL保留，`kill-recovery-retry.xml`复核exit0；详见下段 |
| Ruff / diff检查 | PASS | 白名单源/test文件；无API/DTO/migration变更 |
| Chrome / frontend build | NOT RUN | 前端未改，v6.2/v6.3既有UI证据保留，本批只改内部契约 |
| 真实provider / tokenizer /正式发布 | NOT RUN | 产品模型请求0；未切正式入口/Worker |

TDD保留各RED XML；最初root缺marker、Fake缺新形状/generic空目标、内容保护与rubric缺口、review marker移除漏洞均有先FAIL后PASS。PG首轮1PASS/2FAIL是27阶段误用15k阈值及failed Run对应job completed的断言错误；新增checkpoint fixture有ID前缀/state键/JSON数组/rehydrated outline断言错误，均保留文件后修正。相邻PG首轮19FAIL包含tuple/array真实比较缺陷和旧Fake未识别新输入，规范JSON比较与Fake局部适配后通过21项；force-kill检查有一次未读到resumable next的FAIL，新owned库单项复核PASS，未修改该测试或宣称时序现象根因已完全定位。该偶发检查风险保留，不把多轮结果累加冒充一次全绿。

普通owned PG较大场景实际27阶段/62安排/100reviewed refs/61extensions/27知识/27practice，scope/acceptance JSONB与实体readback相等。旧markerlessfixture是本轮新建的合成历史，未使用真实历史Run。所有测试库由既有安全harness创建并精确清理；专用实例opt-in为False，既有角色复用、无全局角色改动。真实PG不是Fake规则测试的替代，Chrome本轮明确NOT RUN。

本机证据：`var/v67/payload-evidence.json`、`baseline-invariants.json`、各XML、`pg-*.json`、`final-invariants.json`；checkpoint为 `var/codex-goals/studyplan-v67.json`。不提交密钥/DSN/私人正文或本机证据。

## 用量、风险与回滚

模型quota仍24/50，48份request/result哈希、26份历史Acceptance文件、9份v6.5证据与正式.env哈希保持。模型/搜索本批新增0；搜索最新记录6/1000。真实产品库读写0、正式入口/Worker0、RAG修改0、无push/merge。此处产品模型用量不等同开发子代理用量。

root偏好请求Sol6.1/high；独立content与PG请求Sol6.1/medium，review请求Sol6.1/high；解析值均NOT OBSERVABLE。无Astra/Sol max或全局配置/服务模式修改；最多两名业务writer，各文件有单一所有者。

风险：真实provider输出质量/成功率与实际token下降尚未验证；checkpoint force-kill偶发检查保留上述原FAIL；显式optional canonical task格式目前拒绝，后续扩充必须先提供不影响阶段完成的现有契约。全产品非空原账号历史/RAG/完整用户接受等门禁未完成。

本轮没有正式数据或配置回滚事项。代码可普通revert局部提交；若未来已创建新格式正式Run，应先停止新提交并保留两格式读取/保护，不能重写其manifest或执行中降级。不能重用v6.5 Acceptance、清零quota或删除历史evidence。

最终 **OUTLINE_PROJECTION_PATCH_READY**；全产品 **STAGING_BLOCKED / NOT_READY**；完成后 **STOP**。唯一下一最小动作：另行明确授权一个全新、单一Agent5 synthetic收费代表验证；本轮不执行。最终本地SHA在交付时动态读取，不声称已在GitHub。
