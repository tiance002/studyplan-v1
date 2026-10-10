# W5：受控真实适配器与 owned Worker 执行链路收口

本轮完成此前 W5 缺失的实际 Provider、调用账本、元数据预检、Worker 驱动及独立阶段审查续接装配。验收方式是实际 HTTP Provider/资源适配器配合 MockTransport，以及新建隔离 owned PostgreSQL。**本轮未进行任何新的真实外部请求，不构成真实教材或课程语义验收。**

## 基线与修改边界

- Start HEAD：`b17d7a7308caa6f5b1136d587ca3fce8d56d9619`，分支 `feat/n1-resource-discovery`。该基线已上传 GitHub；本轮仅本地 checkpoint，不 push。
- 最终代码由本报告同批本地提交标识；测试期间 HEAD 保持上述基线，提交后未来 acceptance 必须重新 prepare，不能沿用测试 packet。
- 开始时 tracked tree clean；既有未跟踪 `.workbuddy/`、`design-preview/` 不读取、不修改、不暂存。
- 原报告 `STUDYPLAN_DELIVERY_SEAMS_FIX.md` 中 W5 PARTIAL 保持原文，作为历史状态；本报告记录其后续收口。
- 只修改 owned 脚本、定向测试、本报告与 progress。未修改生产 Domain/Runtime、Policy、Schema、hash 算法、预算算法、API、UI、迁移、正式配置及历史 Run/Receipt。

修改文件：

| 文件 | 职责 |
|---|---|
| `scripts/planning_v2_scenario_a.py` | 冻结准备、受控提交、精确 Run Worker tick、审查读取/决定、CLI |
| `scripts/planning_v2_acceptance_external.py` | 独立外部授权、真实 Provider/资源适配器、全局账本、元数据/价格、外部 STOP |
| `backend/tests/unit/test_scenario_a_preparation.py` | 保留默认拒绝及冻结准备检查，更新受控 CLI 检查 |
| `backend/tests/unit/test_w5_review_evidence.py` | 审查内容、checkpoint、身份、版本及非模型自评反例 |
| `backend/tests/unit/test_w5_acceptance_external.py` | 实际序列化/HTTP 适配器的 Mock 边界、账本、用量、元数据与并发锁 |
| `backend/tests/integration/test_w5_owned_runner_pg.py` | 原生 Worker/PG 预约/回执/审查续接/Draft 与资源子请求接线 |
| 本报告及 `docs/implementation/progress.md` | 当前状态及证据索引，保留历史原文 |

开发路由：关键预算、来源及派发问题请求 `gpt-6.1-sol/xhigh`；独立审查子代理采用独立上下文。工具实际模型解析为 `NOT OBSERVABLE`，未更改全局配置或宣称解析身份。

## 实际接线

```text
完整 SourceFacts 快照 → prepared packet / frozen manifest / code SHA
  → 分离的 Owner submit/execute/review 授权与 external 授权
  → 官方元数据 GET 收据 → 独立价格审查绑定
  → 新 owned 提交 → 单一 Run/Job/root
  → 精确 Run PlanningWorker.tick / lease heartbeat / fence
  → 原生 PgV2Calls 预约与 active_dispatch
  → 真实 OpenAICompatibleLLM / GitHub / Tavily / GitHubTeachingBody
  → 全局 request intent → HTTP → append-only result / 原生 PG receipt
  → Goal / Capability / Curriculum 原生审查暂停
  → 独立证据 + 原生 CAS 决定 → 同 Run 冷装配续接
  → Compiler → owned Draft（不自动批准 Revision）
```

`PreparedScenarioAFactory` 在原生工厂创建后绑定实际 `PgV2Calls`。Helper 每笔请求记录对应 `parent_attempt_id`、原生 reservation hash；资源 HTTP 子请求另记录 `pg_child_ordinal`，与原生 `v2_nested_dispatch/result` 对应。不能仅有文件账本而绕过 durable 预约。

Worker 在 SQL 领取前限定被冻结 Run、actor、project、graph、可领取状态及 unknown 保护，保持原生事务、锁、lease、heartbeat 与 finish 行为。不会先领取别的 Job 再拒绝。无关 Job 反例采用同项目但不同 graph，避免人为构造第二个初始 V2 root；原始多 root 来源保护保持有效。

每个阶段分别读取实际 checkpoint 和冻结输入/输出。独立证据必须绑定 acceptance、packet、actor/project、Run、阶段、Run version、review digest 和实际 checkpoint hash，提供明确 PASS/FAIL、审查者、依据与引用。服务端调用原生 `PgOwnedV2Reviews.decide`，不是另造暂停平台。相同决定可幂等读取；FAIL 保持原生业务拒绝并写不可变 STOP，不自动进入下一阶段。

审查文件及其 SHA 必须由可信独立审查渠道提供。Hash 只保护完整性，不能认证审查者是谁；没有自动审查 PASS、模型自评批准或自动签署 Owner 授权。独立语义判断仍是后续执行者职责。

## 外部准入与预算

准备格式为 `owned-scenario-a-preparation-v2`，新增 owned helper 的 SHA 冻结，不重新解释旧 v1 packet。外部授权格式 `owned-external-acceptance-v1`；价格审查格式 `owned-price-review-v1`。旧 Run、旧 manifest、旧账本及旧授权不补造或迁移。

Helper 构造为零网络、零请求入账；没有独立新授权时拒绝外部动作。Owner 授权文件通过同一次读取的原始字节 SHA 验证，冻结当前 HEAD、脚本、SourceFacts、manifest、Provider 配置/密钥修订身份、账本路径与限额。提交绑定单一 Run/root，不允许本目录生成第二个 Run。

实际 Provider 仍是 `OpenAICompatibleLLM → DeepSeek deepseek-flash`，text-only system/user JSON，thinking disabled，基础输出 cap 4096，Reader cap 1024。在实际序列化后、全局模型 request intent 和 HTTP 之前验证完整 messages UTF-8 不超过 32 KiB。它是开发期大小保护，**不是 tokenizer 或现金数学保证**。

新 acceptance 请求计划上界：

| 项目 | 上界 |
|---|---:|
| Goal / Capability / Curriculum | 各 1 |
| Reader | 6，包含在产品模型总数中 |
| 产品模型合计 | 9 |
| 搜索 | 6 |
| 正文操作 / HTTP | 6 / 12 |
| 价格与余额元数据 | 合计 2，独立于 ResearchBudget |
| 输出预约 | 18,432 tokens |
| 正文预约 | 393,216 bytes |
| durable 外部请求预约 | 27（9 + 6 + 12）|
| 内部 cost_micros 预约 | 186,000，保留既有单位，非人民币 |

这些值来自既有合法 owned policy 和最坏预约，不修改正式默认预算。全局模型/搜索 cap 必须在新的可信 Owner 授权中明确；读取当前 append-only request/result 配对后累计，不能把历史额度当成本轮授权。成功、失败与 unknown 历史均占用历史身份；pending、不完整或同 acceptance unknown 阻断后续。跨进程锁、独占 intent/result 文件与 fsync 防止同号竞争，不提供重试或 repair。

官方预检只使用固定价格页和 balance 端点、最多两个独立 GET，不自动重取或跟随重定向。保留价格来源 hash、余额安全字段、元数据请求/响应收据；需要独立价格审查确认模型、币种、缓存未命中高峰价和时间。Provider 配置、授权或来源变更、过期/不可用余额、价格审查不一致均拒绝。模型费用使用可信 usage 和独立审查价作估算；Tavily credits 单独记录，内部 cost_micros 不转换成人民币。

价格和余额本轮均使用 Mock，不声称实时账户可用。严格输入 Token / 人民币现金硬上限仍未证明，后续真实调用须另行明确接受残余风险。没有默认 CNY0.50 授权。

## 响应与证据保留

使用原 Provider/Validator；不得补齐或改写模型响应。响应模型身份、可信整数 usage、总量一致性、输出 cap、finishReason 和 HTTP 状态在受控边界检查。truncation、不可确认用量、unknown 或账本不完整均停止，不换身份、不退款或重派。

明确本地未派发拒绝使用 `LLMNotDispatchedError` / 原生资源 not_dispatched 结果，避免被 PgV2Calls 通用异常处理误判为 unknown。已经产生 wire intent 的不确定结果保持保守 reconciliation。Worker 后置 guard 遇到 unknown STOP 时转回原生 `V2RecoveryBlocked`，防止把已经持久化 unknown 错记为普通业务失败。

所有原始证据在 ignored `var/`，不进入报告或正式数据库。Goal/Capability/Curriculum 保留原始响应与 Provider 结果；Reader 原始内容不落盘，保留响应 hash、用量及投影事实，原生 Reader 检查仍负责合法可持久化结果。教材正文始终 transient；本次 sentinel 反例检查没有将正文写入 JSON。授权、DSN/session 仅使用本地受控文件及环境，不打印凭据或认证头。

## 定向验证与独立审查

证据目录：`var/codex-goals/w5-runner-closure-20261010/`。测试和 helper 装配都只允许 Mock HTTP 与 loopback 新 owned PG；不能以测试内的合成价格、授权、教学材料或人工 PASS 证据代替真实产品验收。

| 验证 | 实际结果与证据 |
|---|---|
| 准备 + 审查单元测试 | PASS，最终新增 DSN 保护后 48 passed / exit 0 / 12.19s；`dsn-green.log/.exit`（先前 42 passed 保留） |
| DSN 最终拒绝边界 | PASS，port 规范化后 6 passed / 27 deselected / exit 0；`dsn-final.log/.exit` |
| 外部适配器单元测试 | PASS，37 passed / exit 0 / 73.84s；独立实施代理实际工具输出及 `external-unit-final.json` |
| 新隔离 owned PG | PASS，6 passed / exit 0 / 230.01s；`owned-pg-fourth.log/.exit` |
| Ruff（六个 Python 文件） | PASS，exit 0；`ruff-final.exit` |
| git diff --check | PASS，exit 0 |
| 历史保护 | PASS，459 原文件 hash 零差异；模型 request 仍 189，搜索仍 6；`history-final.json` |
| 真实外部/实时预检/正式库/React | NOT RUN |

单元测试命令：`.venv/Scripts/python.exe -m pytest backend/tests/unit/test_scenario_a_preparation.py backend/tests/unit/test_w5_review_evidence.py -q -o addopts='' --basetemp var/codex-goals/w5-runner-closure-20261010/root-final-temp`。

外部适配器命令：`.venv/Scripts/python.exe -m pytest backend/tests/unit/test_w5_acceptance_external.py --basetemp=var/w5-external-unit-20261010-05 --tb=short --maxfail=4 -o addopts='' -q`。

PG 命令：`.venv/Scripts/python.exe -m pytest backend/tests/integration/test_w5_owned_runner_pg.py -q -o addopts='' --basetemp var/codex-goals/w5-runner-closure-20261010/pg-fourth-temp`。

DSN 补丁后准备/审查命令同前，basetemp 改为 `dsn-green-temp`。最后只复测 `test_scenario_a_preparation.py -k 'effective_owned_dsn or owned_pair_and_environment'`，basetemp `dsn-final-temp`。唯一案例总计 85 项 unit 与 6 项 owned PG，不把复跑累加为新的测试数量。

六个 PG 案例分别证明：三次实际原生审查后同 Run 续接到 Draft、unknown 进入 reconciliation 且冷装配不重派、实际 GitHub/Tavily/body Mock HTTP 对应 PG 父预约/子请求、审查 checkpoint 篡改拒绝、全局 cap 已耗尽时 HTTP 为 0 且不产生 false unknown、精确领取与独立 FAIL 不影响无关 Job。完整路线使用合成教材 fixture；单独资源 seam 使用真实资源适配器的 Mock HTTP。它们共同证明接线，不证明真实教材质量。

既有 374 项接缝回归、SourceFacts 两个独立进程冷启动证据、fence/CAS/取消、历史保护及公开 generate 503 证据直接复用，不重复完整 Backend/React/浏览器矩阵。本轮 Worker 冷装配测试重建依赖对象；不同 Python PID 的完整来源一致性复用已经通过的 SourceFacts 冷进程报告，不扩大本轮证明范围。

独审主动发现并关闭：

1. 本地 review state 被替换但复用旧 digest：增加实际封印及 checkpoint hash 校验。
2. 审查者等于本次冻结模型：按实际模型集合拒绝，不能仅屏蔽一个固定模型名称。
3. unknown 已入 PG 后的外部 guard 误转普通失败：保持原生 reconciliation。
4. 本地额度/授权等未派发拒绝误分类 unknown：保留 known not-dispatched，并以 PG cap exhausted 反例证明外部 0。
5. Reader 原始 payload/诊断可能落盘：helper 只保留 hash/计量，交由原生投影核查。
6. 价格来源被替换：独立审查绑定元数据实际 GET 收据及原始来源 hash。
7. 已知正文 404/搜索错误被误判批次 unknown：沿用原生 known/unknown 分类。
8. 文件账本与 PG 子请求接线：实际资源适配器反例核对 parent attempt 与 nested ordinal。
9. 继承的 owned DSN URL guard 只检查表面 host/path：W5 入口现拒绝 URL query/fragment 覆盖及 `PGHOSTADDR/PGSERVICE/PGSERVICEFILE`，使用 libpq conninfo 核验有效 host/dbname，按规范化 port/dbname 拒绝不同用户、loopback 别名或 `05432` 隐藏的同库配置；在 session 读取与工厂构造之前拒绝。本次仅修 W5 入口，不改旧正式模块。

原 RED 与开发中失败日志保留：审查函数尚未实现；CLI 文本断言；合成 Provider caps 未一致；Mock response streaming；Mock Tavily 端点；人为第二个初始 root；DSN 六个新反例。没有改写历史失败，修正的均为本轮实现或 fixture，不放宽正式校验。PG 六项在最后局部 DSN 保护之前执行；新增保护不改变合法 plain owned DSN 的连接/事务行为，后续以零连接拒绝反例和独立源码审查验证，不宣称整组 PG 在该补丁后重跑。

最终独立审查 PASS，九项 findings 全部关闭，open findings 0。证据：`var/codex-goals/w5-runner-closure-20261010/independent-review.json`，SHA-256 `7499bc4495e437e4346a076e2ff283f373adde0363b03c0a21bcc93f8c9c39ff`。审查者核对实际源码、回执顺序、PG/Mock 结果和剩余信任边界，并未把程序接线 PASS 扩展为真实语义 PASS。

## 使用方式与后续真实调用门禁

运行入口：`.venv/Scripts/python.exe scripts/planning_v2_scenario_a.py --help`。

按顺序使用 `prepare → external-request → preflight → price-review-request → approve-price → submit → tick → review → decide → tick`。三个实际审查阶段是 `goal_analysis`、`capability_planning`、`curriculum_composition`。最后一次 tick 才继续 Compiler/Draft，不自动确认 Revision。

- `prepare` 需要受控 Goal 文件、实际 model_ref 和实际 request_options；来源完整快照先持久化，再创建 manifest。只能使用新 ignored `var/` 目录。
- CLI 读取当前进程的 Settings，不自行加载或改写正式 `.env`。后续 owned 启动进程必须显式装配允许的 Provider，并让 deployment/outline/structure/practice/repair caps 与本批 4096 配置一致；Reader 由原有 purpose cap 限制到 1024。正式默认 8192 不因本报告改变，未匹配配置会在 build_llm/请求绑定阶段拒绝。定向测试使用合成 Settings 完成此装配，未声称当前正式环境可以不加配置直接派发。
- `external-request` 只生成 unsigned 请求，不能批准自己；需要新的独立 Owner 文件与其可信 SHA、当前全局账本路径/上限，以及对本批费用残余风险的明确接受。
- `preflight` 本身是受限网络操作，只有新的授权覆盖官方 GET 才能执行；本轮未执行真实 preflight。
- `approve-price` 使用独立审查文件及 SHA，不能将未审价、历史余额或测试价格当成真实预检。
- `submit/tick/review/decide/status` 使用两个不同的受控 owned DSN 环境变量名、session 环境变量名、project ID，以及 Owner/外部授权文件和 SHA。CLI 先拒绝非 owned DSN，再解析 server session；不创建账号、数据库或环境配置。
- 每次 `review` 只输出 unsigned NOT RUN 模板和实际冻结证据。可信独立审查后才提供 PASS/FAIL 文件及 SHA 给 `decide`，并继续同一 Run 的 `tick`。
- 同机冷进程从原 packet、完整 SourceFacts 和 immutable receipts 重装配，不重新生成 created_at。跨机器部署或未受控共享文件权限不在本轮证明范围。
- 遇到 STOP/pending/unknown/身份或来源不一致，不改文件、删账本或创建新 root 追绿；需要 Owner 决策。

本轮未运行：真实 Provider/搜索/正文/Reader、实时价格及余额、Scenario A 教材与课程独立教学语义、React 浏览器、正式数据库和公开生成。不存在新的真实请求授权消耗，也不宣称完整产品上线或现金硬门禁通过。

最终状态：`W5_OWNED_RUNNER_OFFLINE_PASS`，`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`。本地 checkpoint 后 STOP，等待新的独立真实请求授权。
