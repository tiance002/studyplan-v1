# v6.13 Contract Closure — BLOCKED / STOP

## 用户现在新增能做什么

审阅F1–F4修复和真实checkpoint/应用保存反例证据，以及[来源明确的Agent7新Fake/ownedPG Plan与实际教学消费](v6-13-plan-and-teaching-2026-10-04.md)。保存路径已有独立冻结来源防护；普通学习页面的GR候选绑定新缺口仍需评审。没有新增真实provider Plan。

| 层 | 最终结论 | 边界 |
|---|---|---|
| 合同源码与F1–F4保护 | PASS | 四RED→GREEN、共享链只读复核PASS、真实checkpoint和应用入口反例PASS |
| 合同整体收口 | BLOCKED | 不报告CONTRACT_CLOSURE_READY；Goal要求的实际消费门禁未闭合 |
| 教学非收费验收 | BLOCKED | 实际GR候选卡FAIL，剩余Edge/旧版本livePG仍NOT RUN；不报告PEDAGOGY_AND_UNITS_READY |
| 真实代表 | NOT RUN | 新paidAcceptance/Run未创建，provider请求0；freepreflight脚本仅准备 |
| 整体产品 | STAGING_BLOCKED / NOT_READY | 未进入正式库/入口/Worker/RAG/部署或用户接受 |

## 基线、来源与保护

分支feat/n1-resource-discovery，起始/停止HEAD均`1a3262e85296c95d3dfb4349d0d4ef83438f17da`。当前工作树包括继承v6.11/v6.12未提交候选及本轮修复，**尚未提交**。38个相关候选文件、tracked/staged binary patch与425历史证据已保存本机受限ignored副本，不能可靠分离两旧批次，明确采用组合基线，不以HEAD代替候选。原335历史清单扩为最新425，全部hash一致；.env、旧45对账、失败/unknown和旧Plan证据不改。Agent7/AI4/Cloud4及MainWorkspace/CSS字节与本轮候选基线相同。

授权Goal逐字节归档[02_CODEX_GOAL](../implementation/v613-handoff/02_CODEX_GOAL_v6.13.md)。[27项/原31项续接矩阵](v6-13-acceptance-cases-2026-10-04.md)不覆盖v6.12历史记录。N0读取已有证据，不reset/整树restore/切分支/merge/push。

## F1–F4本轮局部修复

F1复用已有ai_run_events独立planning_submission以及ai_provider_attempts成功原响应；Fake显式记录到已有审计事件，不把checkpoint自填raw/hash当可信来源。新增共享纯重建比对函数，用原提交pack/manifest与本Run/阶段/attempt/schema绑定响应重建normalized batches，再执行既有merge。比较将落库的完整nodes/units/rubric/relations/practice与outline顺序、资源身份/refs/roles、guidance/extensions。executor和实际PlanService保存/物化前共用此函数，差异拒绝，同一deepcopy才交给原事务。真实PG反例差异路径落到units[0].rubric.canonical_knowledge...scope；Draft/Plan/catalog污染0、恢复新增Fake0。合法编辑仍按已有draft/revision/hash流程，不被生成快照覆盖。

F2只从所选focus投影有界正向实践映射，分开解释/比较与排除。W6否定Kubernetes不能授权部署；CloudS5合法实践保留；EN/ZH比较与未选ref、付款/额外强制任务、明确GoalSpec排除以及不相关负约束正例均覆盖。自然语言检查仅声明这些覆盖案例，不能证明通用教学语义安全；所有正式任务/完成/来源门禁仍独立保护。

F3普通输入、完整输出对象和repair消息分别限制字符/UTF8字节，JSON转义后计量，并在个别field maxima之外使用有限整体对象上界。原A2反例normal14034chars、output21000chars/84000bytes、repair41087chars/155589bytes；11058chars原失败对象能完整进入MockTransport。ASCII和转义Unicode近边界合法与超界反例PASS。超大对象在Fake/provider/SQL预约前返回dispatched=false，HTTP/账本连接0且实际repair_count0；实际已发失败/unknown继续计量，repair≤2不变。cap/model/temperature/prompt_version未全局修改。

F4从独立原提交核对outer/focus/perbatch marker、manifest/pack hash、eligibility和身份；残留/全部删除新标记、null/未知/不一致均不能降为legacy。直接structure、repair、恢复及保存入口覆盖。兼容表如下。

| 原冻结合同 | 处理 |
|---|---|
| 真正无structure/focus/perbatch新标记legacy | 原KnowledgeStructureV1 wire/fingerprint/恢复语义，旧manifest不回填 |
| stage_skeleton_v1 outline + 旧structure | 保持旧structure；真实ownedPG生成确认/原输入不变PASS |
| reviewed_structure_v1无focus历史候选 | 原三字段units语义；完整canonical eligibility及独立原提交/原响应，缺可信基准拒绝 |
| reviewed_structure_v1+stage_focus_v1 | 四字段units、本阶段精确focus、完整标记/hash/来源核对 |
| mixed/no-canonical/search_only | 仅按冻结eligibility选择旧/new批次；空/未知perbatch标记拒绝 |
| 删除或篡改checkpoint全部新标记 | 对独立Run原manifest比对拒绝，provider/Fake0 |

只读复核另定位repair原响应落库先于checkpoint提交的同链时序变体。只在next=repair_batch且无final字段时识别当前kind/stage/index/count+1的精确待重放receipt；仍检查之前的原响应派生状态。PgAttemptLLM复用指纹绑定的已存结果，真实checkpoint/SQL+MockTransport对照恢复HTTP0/Fake0；最终保存不能用此例外。

## 验证及实际消费STOP

- PASS：完整unit/contract1018；2 NOT RUN为Windows symlink条件，exit0。F1/F4独立33扩展案例、32focus/repair、2已知receipt时序对照均在最终全量包含，不能相加当新增独立总数。
- PASS：ownedPG21个独立case，包含compiled PostgresSaver、独立SQL来源、直接应用拒绝、合法恢复/幂等、当前课程路线与旧structure对照。主轮18PASS/1FAIL因PythonSeed夹具缺失（派发前503）；补既有Python2Seed后定向3PASS。原FAIL、初始队列夹具FAIL及RED文件保留，聚合XML不是新执行命令。
- PASS：受影响兼容PG原60PASS/1FAIL（裸PlanService.__new__夹具缺依赖），补显式fixture依赖后单项1PASS；另路线/并发/回滚PG7PASS。合法资源/任务修订、未来前缀、lease/cancel/迟到结果和原fingerprint兼容对应案例详见XML。
- 本轮frontend unit/build NOT RUN，复用v6.12的16PASS/buildPASS；业务UI源字节未改。新Edge harness实际执行，但清理竞态薄修正后NOT RUN。
- FAIL：普通Auth→真实API→ownedPG→Edge初始准确读回/A2三单元/A5A6A8/G0–G6/GRGT/whole_core Prompt先PASS，到GR真实渲染4张重复pending无链接卡。两case_study repo资源ordered_sections=[]，两extensions有rootURL，当前分组无法验证同一来源绑定而添加fallback卡。这是独立新消费结构根因，触发用户“独立新结构根因STOP”与Goal§0/§12；没有改UI/DTO/来源资格、静默合卡或人工写最终Plan追绿。
- NOT RUN：RAG刷新/退出重登录、system/MCP/Node/long普通Edge、旧v68/v610livePG消费、真实binding/DNS/TLS、全新paid代表。freepreflight.py仅准备，不执行。

Edge自有API8031/Vite5191已关闭，已确认Plan保留。记录62HTTP、auth登录POST2、业务写请求0、model/Worker尝试0、外部浏览请求0。失败清理继承的unroute-before-close模式造成pending GET落向Vite默认localhost8000代理，ECONNREFUSED，无实际入口服务/业务HTTP；仅修owned harness清理，修正后NOT RUN，日志保留。

## 用量、风险与回滚

真实normal0/repair0/unknown新增0；权威45/100、45对receipt、该scopeunknown0、余55；搜索新增0、原6/1000保留。Fake RAG实际manifest37normal+2repair=39/output241664，45+39=84≤100只是算术，实际付费binding预检NOT RUN。没有新的paidAcceptance/Run，旧v65/v610 failed或历史unknown不重派。

根协调请求Sol6.1/high，独立测试/PG/Edge及准备Sol6.1/medium，只读reviewSol6.1/high；实际解析均NOT OBSERVABLE，未改全局配置。共享合同由root单一整合，子代理只修改独立测试/新审计harness，不同文件并行；未增调度/签名/数据库平台。

风险：GR真实来源消费绑定未闭合；剩余Edge/旧版本livePG/REAL未验收；语义文本检查非通用证明，课程TypeScript资格缺口仍保留。已通过源码修复不等于全部产品READY或用户接受。

回滚只可比对var/v613/private-baseline保存的组合候选，对本轮指定文件/差异做定向逆向修订并保留v6.11/v6.12成果；禁止整树restore/reset、删除历史或Plan。没有收费需要回滚；新owned样本与证据保留，受控服务已关。

下一安全动作仅为评审这条GR资源/guidance身份绑定的最小修复边界及相应验收，若涉及公开API/资源资格更改须新明确授权。当前BLOCKED并STOP，不继续开发、模型门禁、部署、push/merge或RAG。

证据入口：var/v613/final-invariants.json、case-matrix.json、contract-review.md/json、unit-contract-final.xml、pg/suite-summary.json、edge/checks-attempt1.json、edge/gr-card-diagnosis.json、edge/execution-metadata.json。私有DSN/账号/备份不进入Git或报告正文。
