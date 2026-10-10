# Scenario A SourceFacts 冻结与冷进程恢复修复

任务：`PLANNING_V2_SOURCE_FACTS_COLD_PROCESS_FIX_V1`。

## 基线与原失败现场

Start HEAD：`b999ff9056b601e9dea313fbfc244e2f74d5caea`；分支 `feat/n1-resource-discovery`，开始时tracked tree clean。既有 `.workbuddy/`、`design-preview/` 未操作。

最终结论：`SOURCE_FACTS_COLD_PROCESS_FREEZE_PASS`。最终本地checkpoint SHA记录于本轮ignored `final-delivery.json`及交付消息，不在提交内自引用SHA。

原失败 Run `run_65b8443b2e6b45ddb38a21c11b687603` 保持 `reconciliation_required / v2_recovery_blocked`。新任务开始时对原业务库和checkpoint库使用只读事务，保留全量Run/Job/events/attempts/Draft/Revision/checkpoint查询结果的状态hash：`c58e821b2aed95a3bb8c2324c8f8e04cadbccae95239cdf48e304f12d662f351`。仅1条submission事件，Provider attempts、Draft、Revision、checkpoint均0。原完整来源快照没有保留，不估算旧时间、不恢复、不改manifest。

根因：[原验收报告](PLANNING_V2_SCENARIO_A_REAL_PRODUCT_ACCEPTANCE.md)记录的 ignored `acceptance.py::source_facts()` 每次构造 `PublicResourceSource` 时省略 `created_at`，触发当前时间默认值。生产manifest及Runtime均正确使用 `content_hash(wire(asdict(SourceFacts)))`；不同进程来源身份因此不同。本轮不修改生产校验、hash算法或来源资格。

## owned 完整快照与实际读取路径

新增 `scripts/planning_v2_owned_source_facts.py`，仅为同机owned验收入口：

1. `freeze_reviewed_source_facts` 装配当前合法审核索引、实际目录来源及访问证明。`freeze_source_facts` 在manifest创建前以exclusive write写入完整canonical UTF-8快照，flush/fsync，拒绝覆写。
2. 快照版本 `owned-source-facts-v1`；保存 `source_facts` 全文、原算法 `source_facts_hash`、`source_identity`、envelope `snapshot_hash`。独立 `FrozenSourceFactsRef` 保存绝对路径、文件SHA-256及来源hash，必须作为可信提交收据保留。
3. SourceFacts全文包括Reviewed Index的sections/mappings/evidence/policy版本、Catalog Sources所有字段（含created_at/checked_at/visibility/来源版本和状态）、Access Proof及Project Cases。没有凭据、认证头或教材正文。
4. `read_source_facts` 读取同一文件字节，先核对可信文件SHA，再校验canonical/envelope/版本/固定类型全部字段/来源身份，恢复datetime、Enum及tuple。恢复后的 `wire(asdict(facts))` 必须与原全文完全一致；禁止缺省字段重新生成时间，禁止来源重建fallback。
5. `FrozenOwnedV2PlanningRuntimeFactory.build_submission` 从冻结文件恢复后调用原manifest创建方法。Worker的同一工厂 `__call__` 用durable manifest校验文件及恢复对象，在Provider resolver之前拒绝错误；原Runtime的来源检查继续保留。
6. `assemble_owned_planning` 提供未来owned脚本可用的实际Service/Job/Worker装配，使用冻结工厂。旧ignored验收脚本及其STOP目录不修改，旧授权不用于创建收费Run。

本地文件只保障同一机器、同一受控绝对路径下的owned运行。可信收据与目录必须由Owner/服务账户控制；hash提供完整性，不提供加密或攻击者可替换全部收据时的身份认证。本轮不更改全局ACL、不建设多机器快照存储，不宣称正式多机部署通过。

## 验证与独立审查

| 验证 | 最终状态 | 实际证据与范围 |
|---|---|---|
| 原问题RED | FAIL（预期） | `red-unit.log`：两个独立进程重建相同输入得到不同hash，1项；保留原始失败 |
| 完整来源codec/引用/篡改unit | PASS | 48项，`green-targeted-review-03.log`；该次组合的PG fixture失败另列，不冒称整次命令通过 |
| 实际A退出 → B冷启动 → 本地Worker | PASS | `green-port-pg-04.log`：受影响port unit及PG共2PASS、47deselected、exit0 |
| 独立unit复核 | PASS | 独立审查执行原45项unit，再执行identity两例及port一例3PASS/45deselected；各exit0 |
| 严格身份类型RED | FAIL（预期）→ PASS | `review-red-identity.log`：True/1及1.0/1两项；修为canonical identity比较，最终反例PASS |
| 原失败现场与文件保护 | PASS | `protection-final.json`：849文件hash无变化，旧Run/Job/events/attempts/Draft/Revision/checkpoint全量状态hash保持 |
| Ruff / git diff --check | PASS | 四个新增代码/测试文件；不扩大到全量回归 |
| 真实模型/搜索/Reader/正文/官方预检 | NOT RUN | 每项实际0；只有本地Mock调用与本机PG |

48项unit包含所有Catalog缺省字段保护、嵌套完整字段、真实ReviewedIndex/Catalog/AccessProof及标为synthetic的ProjectCase非空roundtrip、独立子进程恢复、缺失文件/字节/版本/hash/类型/重复JSON键/非canonical编码/错误manifest及工厂解析前拒绝。合成项目案例只证明序列化机制，不升级任何真实案例审核资格。

保留初始执行中的实际失败：首次GREEN因默认临时目录无权限产生45个setup ERROR，改用本仓库ignored var内新的basetemp；首个组合45unit PASS/1PG FAIL是测试将正常 `owned_acceptance_review` 误写为None；后续48unit PASS/1PG FAIL是测试监控误将 `_transport` 的私有能力探测算为调用。仅修改这些fixture/监控预期，保留日志及测试库；未为追绿修改Runtime或来源校验。

独立审查提出并关闭三项：外部端口先记录实际调用再拒绝，补齐显式content hash和manifest负例，以canonical JSON阻止重复身份字段的bool/float与int等值混淆。私有 `_transport` 的 `hasattr` 探测返回缺失，公共方法仍记录并拒绝。最终独审PASS，没有本任务范围内未关闭的阻塞。请求开发路由Sol6.1/xhigh，实际模型解析 `NOT OBSERVABLE`；未修改全局模型配置。

证据保存到 ignored `var/planning-v2-source-facts-cold-process-20261010/`。复用此前8项owned PG及9项Mock门禁证据，不重复283项旧回归、React或全量Backend。

## 两个真实独立进程与完整内容一致性

最终代表文件：`cold-62b28a053a9f/phase-a.json`、`phase-b.json`、`source-facts.json`及 `source-facts-canonical.json`。

| 项目 | 提交进程A | 冷Worker进程B |
|---|---|---|
| PID / cwd | 27504 / `D:\studyplan` | 24992 / `D:\studyplan\backend` |
| 生命周期 | 写入完整文件、构造manifest、提交后退出0 | `subprocess.run(A)`已返回后新启动，退出0 |
| SourceFacts canonical bytes | 5684 | 5684，逐字节与A持久化全文比较相等 |
| SourceFacts hash | `2d8a5a3f572cba5d99dffc368120d4144413a0c1280c5ce452dbc569884d833a` | 相同，与DB读取的manifest一致 |
| created_at | `2026-10-10T02:38:28.931792+00:00` | 原样恢复，实际类型datetime |
| visibility | ResourceSourceVisibility | 相同实际枚举类型 |
| 实际状态 | queued，0claim/0attempt | waiting_user/review_draft，1claim/1本地Mock attempt，goal_analysis审核暂停 |

两个进程使用同一绝对快照路径：`D:\studyplan\var\planning-v2-source-facts-cold-process-20261010\cold-62b28a053a9f\source-facts.json`，文件SHA-256为 `b9fc7d175863a5265ec0a1e685bd15c91a7eec83e815e2accef888e826679bd9`。文件SHA与SourceFacts hash分别核对，不混用。

实际来源：`src_mcp101_a7ca881ee83ac722491299cd` version2；Reviewed Index hash `0e0ca1a7fffc0d3b4d5cdcadfbb55ec7434d7a4dfa1b805e73fd80f985434fe6`，1 section / 2 mappings / 3 evidence / 1 access proof。实际ProjectCases为空且完整保留；非空ProjectCase由明确synthetic unit验证。上述只证明身份和类型保全，不是重新审核教材语义。

新Run `run_b3eafd85e7a148b18e97ab20c7541b80` 仅为本地Mock测试，DB manifest hash `60634a8146276d9758c1f9942fb26852f1b5609080f16c1b2be4425d3b991e44`；真实Runtime来源检查通过后到首次正常审查点，Draft0。测试未批准该暂停，未进入Capability/Research/Reader/Curriculum。

8项PG负例：missing、bytes、snapshot_version、unknown_field、facts_hash_corruption、manifest_mismatch、corehash_created_at、corehash_source_version。后两项连快照自报hash也重算，仍被可信参考/原durable manifest拒绝；每例Provider resolver、Mock调用、禁止端口调用及外部调用均0。socket/DNS audit guard只允许loopback PG，并以被拦截的connect探测证明外网拒绝；没有实际外网连接。web、project/domain及metadata端口未装配，Reader/search/body均未调用。

最终owned库：`studyplan_test_v2p3_26052806` / `studyplan_test_v2p3_checkpoint_6dcb0e3b`。四次有理由的PG执行产生的测试库对与中间失败证据均保留，回执roles_created为空；没有新增migration文件或正式库操作。

## 修改范围与后续装配条件

新增四个源/测试文件：

- `scripts/planning_v2_owned_source_facts.py`
- `backend/tests/unit/test_owned_source_facts_freeze.py`
- `backend/tests/integration/owned_source_facts_cold_process.py`
- `backend/tests/integration/test_owned_source_facts_cold_process_pg.py`

新增本报告，更新progress并保留全部旧字节。旧验收脚本、失败两库、Run、Job、manifest、授权、checkpoint、来源状态、184–187记录、Policy、Schema、hash算法、预算及生产Runtime全部保持。模型账本187、搜索账本6未增，unknown177/183保持；公开generate原503保护未改变，本轮HTTP/React复测NOT RUN。

下一次新授权owned验收应先为新目录调用 `freeze_reviewed_source_facts(absolute_path)`，保留可信 `FrozenSourceFactsRef`，再用 `assemble_owned_planning(..., snapshot=reference, ...)` 构造提交；独立Worker从持久化收据恢复同一个reference，不再次调用来源构造函数。当前已证明这一装配路径的本机冷启动条件；未来必须继续保持收据/目录受控并使用既有审批、预算、fence及请求身份保护。没有本轮授权去执行真实模型或使用旧授权创建收费Run。

## 最终交付状态

`SOURCE_FACTS_COLD_PROCESS_FREEZE_PASS`

`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`

**STOP。** 本轮真实模型、搜索、正文、Reader及官方价格/账户预检均0。未验证多机器部署、真实教材质量、真实模型语义或完整课程产品闭环；不push、merge、deploy或开放正式生成。
