# Scenario A 真实课程与产品闭环验收

任务：`PLANNING_V2_SCENARIO_A_REAL_PRODUCT_ACCEPTANCE_V1`。

## 基线、授权与执行状态

Start HEAD：`2706fd531b7d4caa25127c588c0e2c97b1a1fd86`；分支 `feat/n1-resource-discovery`，与本轮参考一致。开始时 tracked tree clean；既有 `.workbuddy/` 和 `design-preview/` 未操作。

Owner 单独确认最多 9 次产品模型（Goal 1、Capability 1、Reader 6、Curriculum 1）、6 次搜索、6 次正文操作/12 次 HTTP、官方价格与余额合计 2 次，并接受没有严格人民币数学现金上限的残余风险。随后批准先实施最小 owned 门禁、离线验证，再执行本批。无充值、重试、repair、换模型、扩额、正式数据库写入或公开生成授权。

最终结果：**BLOCKED — 新 owned Run 在首次模型预约前因 SourceFacts 冻结不一致被拒绝。** 本批真实教学语义、教材及课程产品闭环均为 **NOT RUN**，不是模型语义 FAIL。最小受控门禁离线验证 PASS；这不能替代本批真实产品验收。

门禁与执行 HEAD：`a7060181b7861e02b80810fa3c3b8e91476bcff4`。最终报告 checkpoint 的 SHA 记录于 ignored `final-delivery.json` 和交付消息，避免文档自引用提交 SHA。执行后只更新本报告及 progress，无进一步生产代码修改。

## 最小受控门禁

新 owned assembly 显式选择 `scenario-a-review-v1`，冻结 `planning-v2-product-v2`。旧 manifest、旧 Run 和无标记装配继续原行为；未改架构业务语义、Policy、Prompt、Schema、历史快照或 migration。

- 四模型 purpose 独立上限 1/1/6/1；搜索/正文各6；其他 purpose 在 invoke 前拒绝。
- Provider 实际基础输出4096、Reader1024；manifest 相同冻结上限，总最坏输出18432。
- 新 owned `ResearchBudget`：search6、candidate8、body393216bytes、Reader6、total27、internal cost186000。27=9模型+6搜索+12正文HTTP；internal cost不是人民币。
- Goal、Capability、Curriculum 真实 checkpoint 后，受当前 fence 保护保存绑定审查事件，Run进入 `waiting_user`、`result_ref=NULL`，原 Job 完成并撤销租约。
- 独立审核决定绑定 actor/project、同 Run/root、manifest、stage、checkpoint hash、Run version、审核证据hash和幂等key。批准原 Job 续接、保留 attempts 与累计预算；拒绝、unknown、过期/篡改来源不续发。
- 三次审核加最终持久化最多4次 bounded claim；不通过异常或崩溃模拟暂停，不创建公共审核API或通用暂停平台。

源码：`plan_service.py`、`v2_runtime.py`、`v2_planning_runtime.py`、`runtime_factory.py`、`v2_attempts.py`，新增 `v2_owned_reviews.py`；定向 unit/owned PG 两个测试文件。

## 离线验证与独立审查

| 验证 | 状态 | 证据/范围 |
|---|---|---|
| 新门禁及相邻定向 unit | PASS | 46项，`var/planning-v2-scenario-a-20261010/owned-gate/final-unit.log`，exit0 |
| 新 owned PG / 真实 PostgresSaver | PASS | 8项，`final-owned-pg.log`，exit0；三暂停、同Run恢复、CAS/幂等、旧fence/unknown/篡改拒绝、全最坏累计和逐purpose超额0invoke |
| Wire harness 反例 | PASS | 9项 MockTransport；可信usage、缺usage、截断、超大输入、purpose耗尽，以及Reader正文/usage额外值/usage错误类型/finishReason回显 |
| 相邻旧 runtime PG | PASS | 先6PASS/1FAIL（旧V1 fixture没有显式选择legacy）；仅为fixture补`product_semantics=None`后原失败单项PASS，保留原始失败日志 |
| Ruff / diff | PASS | 本轮相关文件；不重跑283项旧回归 |
| 真实模型、搜索、Reader、正文 | NOT RUN | 首次模型预约前来源绑定拒绝；各项实际请求0 |
| 官方价格及余额预检 | PASS | 两次授权 GET，各 HTTP200；本批 metadata 上限已用完 |

独立审查发现 Reader 原始响应可能在拒绝前回显并持久化教材正文；usage和finishReason也有相同元数据旁路。采集已修为只保留 Reader 原始响应的 hash/status/bytes；仅严格校验通过的有界事实可保留，拒绝时不保存 payload。usage仅投影可信三个计量整数，finishReason仅枚举/None，其他值仅hash。四个哨兵反例证明这些回显不出现在任何保留文件。Reader原始响应不因验收日志要求而越过正文保护。

独审还要求门禁源码本地提交后再冻结执行文件，防止新未tracked模块未纳入hash保护。执行freeze拒绝dirty tracked tree，并确认新模块已tracked。

开发审查请求 Sol6.1 xhigh，实际模型解析 **NOT OBSERVABLE**。独立 critical 审查 **PASS**：独立以内存方式再运行9项Mock矩阵，读取8项owned PG/46项unit证据并核对源码顺序；没有剩余confirmed blocker。旧runtime相关7项最终PASS，原fixture失败日志保留。审批接口返回原Run身份，不改变历史事实。

## 实际执行边界

沿用原 Scenario A GoalSpec；新 acceptance、Run/Job/root 和 append-only 请求身份。独立语义审查 PASS 后才能继续各阶段。实际消息序列化检查、严格模型/finishReason/usage核对，任何 unknown、截断、不可托信usage、Validator或关键语义失败即停止。费用只按实时官方峰值未命中价格估算，不冒充实际扣款或数学现金硬上限。

原始证据目录：`var/planning-v2-scenario-a-product-acceptance-20261010/`。不保存凭据或认证头；教材正文保持瞬态。历史账本unknown177/183与184–187原证据受hash保护。

仅真实 Curriculum 完整且双层审核通过才执行 Compiler/owned PG/Draft/确认/Revision/React。否则这些产品闭环项目记录 NOT RUN。任何结果都不开放公开 `/plans/generate`，不 push、merge、deploy。

## 官方预检、实际调用与费用

2026-10-10 北京时间，实际读取官方价格页及 `/user/balance`，合计2次请求，均HTTP200。已保存脱敏响应和价格来源hash；不再读取余额或价格。

- 官方价格页对应 `deepseek-flash` / `DeepSeek-V4.1-Flash`；CNY计价，峰值缓存未命中输入每百万tokens 2元，输出每百万tokens 8元。来源：[DeepSeek官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。本报告引用本批授权GET保存的当时快照，没有追加访问。
- 返回账户可用，余额 CNY3.92（预检时点值，非最终扣款核对）；未充值。
- 新请求输入预定使用冻结Scenario A、thinking disabled，基础输出4096、Reader1024。门禁/真实Provider序列化的Mock验证PASS；本批没有实际派发消息，因此实际模型响应身份、finishReason、usage、延迟、Profile/Plan/Curriculum均 **NOT RUN**。
- 新模型请求0/9，搜索0/6，正文操作0/6、正文HTTP0/12，Reader0/6；官方metadata2/2。产品模型输入/输出usage增量0，按无模型请求估算模型费用CNY0，不声称核对了实际扣款，也不声称现金数学硬门禁通过。
- 模型账本仍187，搜索账本仍6；仅追加本批授权记录，无请求188或搜索请求7。历史unknown177/183不改写、不重派。本批没有transport unknown。

## 首次 Worker 拒绝与准确根因

新 owned Run：`run_65b8443b2e6b45ddb38a21c11b687603`。服务端冻结的 manifest hash：`34df89b58fdf9c018b834b523cc43308b8afb9adc914512a88bd1ef6c2fa2329`，SourceFacts hash：`fac825c862e881155805506a8a5d61f975cb6291738fb5703c093cd39a8724cb`。GoalSpec全文及三条原约束未改。

第一次Worker claim后，Run及Job进入 `reconciliation_required`；`next_action=reconcile`、`error_class=v2_recovery_blocked`、Run version3、`result_ref=NULL`。两个新 owned 库的只读核对：provider_attempts=0、reservations=0、checkpoint=0、Draft=0、Revision=0；仅保留原submission事件。正式库未操作。

准确失败分支是 `V2PlanningRuntime.execute` 在加载checkpoint/调用模型之前执行的 frozen input/source versions 校验。manifest完整性、Goal与DomainRegistry绑定均PASS，SourceFacts绑定FAIL。`reconciliation_required` 是既有应用层对 `V2RecoveryBlocked` 的映射；它不证明外部派发结果未知，此处没有任何Provider请求。

**这是本轮验收脚本的装配遗漏。** ignored `acceptance.py::source_facts()` 每次重建 `PublicResourceSource` 时没有指定 `created_at`，触发其当前时间默认值；manifest对完整 `wire(asdict(SourceFacts))` 哈希。提交进程和Worker进程因此得到不同来源身份。提交前没有保留完整SourceFacts规范化快照，只保留了其hash。

独立连续重建两份来源事实，唯一差异为 `catalog_sources[0].created_at`；重建hash均不等于原冻结hash，归一该字段后两份hash一致。冻结源码、内容与harness文件hash均保持。不能由当前材料找回原完整来源快照，也不能推测时间、改manifest/hash或制造checkpoint恢复。

原始证据：`submission.json`、`execution-freeze.json`、`tick-1.json`、`exact-block.json`、`STOP.json`；独立只读查询绑定原actor/project，未修改Run、历史或数据库事实。

## 最终验收矩阵及独立判断

| 项目 | 程序/执行状态 | 独立语义状态及原因 |
|---|---|---|
| owned purpose/预算/fence及三个审查续接门禁 | PASS（离线） | 不代表真实模型或课程质量通过 |
| 实际新Run来源冻结装配 | FAIL | 新进程created_at改变，冻结身份不一致 |
| 新Goal / Capability | NOT RUN | 0模型派发，未借用184/187作为新结果 |
| 真实免费教材、候选比较、Reader正文证据 | NOT RUN | 搜索/正文/Reader均0；没有本批真实教材结论 |
| required/recommended缺口解决 | NOT RUN | 未进入Coverage/Research；历史结果仅参照 |
| 课程阶段、连续实践、权限教学及complete/incomplete | NOT RUN | 未生成Curriculum；不能标记complete或教学意义上的incomplete |
| Compiler / 新Draft / 确认 / Revision / current-history / React | NOT RUN | 无完整课程，未进入产品闭环或浏览器 |
| 本批STOP及来源拒绝保护 | PASS | 保留原Run/root，不恢复、不另开身份追绿 |
| 公共generate fail-closed | PASS | 最小定向测试1PASS/exit0；原503保护保持，未开放入口 |
| 旧证据与配置保护 | PASS | 473个旧文件hash保持，含.env/历史账本/真实旧响应；progress旧字节完整保留 |

独立审查子代理读取实际装配代码、runtime拒绝顺序、manifest及两个owned库的只读数据，确认上述根因、0attempt/0reservation/checkpoint及STOP决定。前述离线critical PASS没有覆盖到本轮冷进程来源重建错误；本报告没有将其扩大为成品PASS。开发模型实际解析仍 **NOT OBSERVABLE**。

## 修改清单、剩余最小问题与 STOP

已提交门禁源码：

- `backend/app/application/plan_service.py`
- `backend/app/domain/planning/v2_runtime.py`
- `backend/app/infrastructure/checkpointer/v2_planning_runtime.py`
- `backend/app/infrastructure/providers/runtime_factory.py`
- `backend/app/infrastructure/providers/v2_attempts.py`
- `backend/app/infrastructure/db/v2_owned_reviews.py`
- `backend/tests/unit/test_owned_v2_acceptance_gate.py`
- `backend/tests/integration/test_owned_v2_acceptance_gate_pg.py`
- `backend/tests/integration/test_v2_planning_runtime_pg.py`（仅legacy fixture适配）
- 本报告与 `docs/implementation/progress.md`。

下一处实际阻塞是 **owned验收入口没有冻结完整来源事实**。未来最小路径：在新的提交之前持久化实际完整canonical SourceFacts快照及hash；各进程从相同字节恢复包括时间、版本及证据在内的来源身份，冻结前与claim前均校验；先用无外部调用的冷进程测试证明一致。可复用现有领域解码方式，无需改hash算法、放宽Validator或增加migration。

这只是后续建议，本批未实施恢复补丁。原完整packet不存在，不能无损续接原Root。本批保留failed owned两库、Run/Job、manifest、授权和STOP证据，不改写、不删除、不恢复，也不自动另开第二Run。未使用的模型/搜索/正文额度不自动转为新的验收身份授权；metadata额度已用完，未来批次及其预检边界由Owner另行决定。

最终：`REAL_PRODUCT_ACCEPTANCE_BLOCKED_BY_SOURCE_FREEZE`；`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`；**STOP**。无push、merge、deploy、正式库/正式配置改动；不开放公开生成，不宣称大规模语义可靠性或完整产品通过。
