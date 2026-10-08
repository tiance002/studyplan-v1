# Planning V2 Item7 P3 — V2 Runtime 与可靠恢复

日期：2026-10-08。P3 独立审查 PASS；ITEM7_IMPLEMENTATION_COMPLETE。

## 基线、权限与验证边界

Item7 Start HEAD：`f1f3d139d197c29e8d76a0d5d0ce87a045278f4f`。P1 checkpoint：`52a326bf5d11d297fd47623cea346d4f6b55ff0e`；P2 checkpoint / 本阶段 Start：`f7eeab33eeb59d6824b2bc23d3e1a355c3a83340`。分支 `feat/n1-resource-discovery`。

用户授权连续 P1～P3 实施和各阶段独立审查修复、本地 checkpoint。真实产品模型、搜索、Reader 请求保持 0，公开 generate 关闭，不操作正式数据或历史 Run/Receipt/unknown，不新增 migration，不 push/merge/deploy，不进入 Item8。请求实施/独审 Sol6.1 xhigh，实际解析 NOT OBSERVABLE，不修改全局配置。

## 实际链与装配

`owned POST → PlanService.submit_owned_v2 → 现有 Run/Job → PlanningWorker claim → V2PlanningRuntime → Item1 Analyzer → Item2 CapabilityPlanner → Item3 Coverage → Item4 Gap → Item5 Research → Item6 Composer → P1 Compiler → P2 单事务 Draft → Run succeeded + none`。

用户明确确认当前 Draft hash 后才走既有 publication/CAS 事务形成正式 Revision；Worker 不自动批准。未知能力走实际 Pending→受信 registry 对应 DomainVerifier→冻结验证证据路径，不由 Runtime 自创能力。没有旧 outline/structure/practice 模型链或第二个课程决策者。

`planning-v2-execution-v1` 与旧 Run 协议隔离。manifest 绑定 goal hash、来源事实 hash、registry hash、模型/输出参数、预算、checked_at、expected_version 与自身 hash。派发前再与业务库原始提交核对，一致重算更高预算 hash 不能替换原授权。后续阶段只消费各自上游冻结事实，不重新解释 raw goal。

`OwnedV2PlanningRuntimeFactory` 需要显式服务端装配，并限制 loopback、`studyplan_test_*`、业务/checkpoint 两库不同。默认产品 composition 未启用该工厂，受控入口也 fail-closed。正式 `/plans/generate` 仍503。新增 `/plans/v2/owned/generate` 复用现有请求/响应 DTO、鉴权/CSRF/project scope，返回202；OpenAPI、生成TS及实际PG示例同步。未修改 Planning 页面。

## 回执、预算、正文与恢复

复用既有 `ai_provider_attempts`、`ai_run_events`、Run/Job 与 PostgresSaver，无业务 migration、全局角色修改或新审核平台。`PgV2Calls` 派发前持久预留并冻结 identity/input/config/source；成功回执不可变，核查 digest 后复用。pending/dispatched/unknown 阻断同一及变换身份的新派发；取消/租约丢失保留外部不确定性，旧 token 不能继续写 Draft。

共享 Run 预算按各阶段最坏预留单调累计，局部结算不退回可重复消费额度、重启不重置。请求/token/搜索/正文HTTP及bytes/Reader/Domain Verification/候选准入共同受限；observed 超额保留实测额并阻断继续。候选准入是现有事件表内的幂等本地事件，不伪造 Provider Attempt。guarded transport 对每次嵌套HTTP记录身份/hash/状态/bytes，不保存认证头和正文。

`PgV2Checkpoints` 使用独立 namespace 并绑定实际 Run.thread_id/manifest。成功 receipt 已落而 checkpoint 缺失时重建进度；删除所有V2 checkpoint后恢复同一 Draft/hash，新增外部派发0。Draft 已写、Run终态前中断，实际新 Worker claim 新 token 后恢复 succeeded+none，旧 fence 拒绝。

Reader 原始输出在正文仍可用时经既有 Validator 校验，只保留合法 outcome/chunk/source/version/hash/限制/usage，再释放正文；外围 model/finish/诊断同样清理，恶意回显不进入 receipt/checkpoint。纯 body 成功但没有 Reader 成功回执的中断，不能仅凭 hash 重建 Reader：阻断等待 reconciliation，不自动重读。Reader 成功回执缺 checkpoint 则可无正文恢复。没有宣称所有中断都自动完成。

## 实际执行证据

ignored 证据目录 `var/planning-v2-item7-p3-20261008/`。只在新 owned `studyplan_test_v2p3_*` 及独立 checkpoint 库写入，身份存 `owned-database-*.json`，roles_created=[]，库保留。使用现有业务 migration0025 和已有 PostgresSaver 初始化；正式库未写。

| 检查 | 结果 | 证据 |
|---|---|---|
| 初始恢复矩阵 | FAIL（16 PASS / 1 FAIL） | `runtime-matrix.xml`，保留实际Worker接管失败 |
| 接管/全checkpoint缺失/Domain精确预算修复 | PASS（3） | `recovery-fix-targeted.xml` |
| P3真实PG主矩阵 | PASS（20） | `runtime-matrix-final.xml`，实际整链、未知专项自动触发、接管、unknown/cancel/fence/正文保护 |
| 预算/初始化终态 | PASS（5） | `budget-terminal-targeted.xml`，复用了主矩阵一个overrun，不能累加为全新25项 |
| Composer预算传播 RED/GREEN | FAIL（预期1）→ PASS（3） | `composer-budget-red.xml` / `composer-budget-green.xml`；实际Worker的10500-token反例，已知失败、0composition派发；含2项复测 |
| 真实HTTP | PASS（1） | `http-runtime-final.xml` / `http-runtime-readback.json`，真实Cookie/CSRF/scope、202/status、实际Worker、Draft、明确确认/current/history、public503 |
| DTO/生成契约 | PASS（9） | `dto-final.xml`，实际PG示例 |
| 部署模型/RC预算/旧Planning去接线 | PASS（23） | `affected-offline.xml`，仅3个直接受影响文件 |
| Import/collection | PASS（26） | 25 PG + 1 HTTP；collection不等于执行 |
| 相关Ruff / git diff --check | PASS | `runtime-closure.json`及交付回执 |

HTTP 外部返回为合成 fixture：4LLM、1search、1body方法调用（底层fixture申报2HTTP），真实产品调用0；完成后查询、确认、再次 Worker tick 的派发增量0。真实PG不是外部Provider/教学语义验收，suite间有重叠，不累加冒称不同测试。

## 独立审查与修复

fresh-context 独审读取实际源码、diff、冻结合同、XML和PG/HTTP回读，自行执行反例，不使用实施者自报PASS代替结论。发现并修复：

1. Reader envelope可回显正文；固定外围metadata并清理诊断，独立反例GREEN；Reader receipt按原reservation/settlement保留body/Reader用量，避免恢复改变ResearchResult/hash。
2. 已知Reader truncation被改成普通失败/unknown；保留原分类和dispatch_unknown=False。
3. 成功receipt早返回绕过observed-overrun重启阻断；重放仍核查总额。
4. checkpoint thread可与实际Run不一致；增加业务Run和先前checkpoint绑定；DomainVerifier扣除已有durable reservation，精确剩余额度及registry/receipt恢复实证。
5. 候选准入未持久计费；现有事件中幂等计数，不创建虚假外部Attempt。
6. Application内PG Runtime反向依赖infrastructure；具体适配归infrastructure，纯协议归Domain。
7. incomplete/初始化拒绝只使Job失败而Run残留running；当前fence内统一合法终态。
8. 实际Worker恢复把含服务器compile_*字段的checkpoint当模型输出；复用原Compiler受控规范化校验，不放宽Item6 Validator。
9. 本地预算拒绝误记unknown；区分派发前已知失败与真实不确定性，Composer在V2 LLM适配层收到typed known LLMFailure，保留Item6原合同；实际Worker反例RED→GREEN。

最终 fresh-context 独审 PASS：独立核读最终源码、实际RED/GREEN与PG/HTTP证据，并逐项核查11个源码/测试SHA256与冻结包相符，差异0。主矩阵20项、预算5项、传播3项去重后共25个不同PG用例，不将三批相加冒称28项。没有修改Item1～6核心语义、Policy/Prompt/Schema/审核映射/Seed、架构或migration。

## 修改与未运行项

新增Domain `v2_runtime`；infrastructure `v2_planning_runtime`、`v2_planning_executor`、`v2_attempts`、`v2_transport`；修改PlanService/routes/runtime_factory/job_repository/planning_worker；新增PG和HTTP测试；更新3份契约产物、本报告、统一交付、progress。最终逐文件和SHA256见 `runtime-closure.json` / checkpoint diff。P1/P2已验收细节分别见 `ITEM7_P1_COMPILER.md`、`ITEM7_P2_PERSISTENCE.md`。

产品模型/搜索/Reader0，历史unknown177/183不重派。真实官方领域证据、真实教材语义/课程质量、浏览器和完整用户E2E均NOT RUN。P2真实PG核对学习/实践/Prompt/Summary/Exposure；Assistant共享上下文继承/投影经代码及PG helper核对，完整Assistant会话/Provider NOT RUN。全量历史Backend回归NOT RUN。

Final HEAD在提交后交付回执中记录，避免自身hash循环。仅证明Item7实现及隔离可靠性边界，整个产品仍NOT_READY；Item8未开始，本地checkpoint后STOP。
