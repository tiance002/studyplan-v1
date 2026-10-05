# Known Invalid JSON → 有界 Batch Repair

日期：2026-10-05。结果：**KNOWN_INVALID_JSON_BATCH_REPAIR_PASS / STOP**。

## 用户现在新增能做什么

未来新 Run 的 structure/practice batch，在严格 JSON 解析失败、响应已知且非截断、原 attempt 已持久化为 known failed 并记录 usage 的条件下，可以消耗现有 `planning.repair` 通道。修复是新 deterministic attempt；原失败保留，完整业务校验继续执行。本批没有创建新用户 Run，没有收费生成新的本人路线。

授权原文：[本批 Goal](../implementation/STUDYPLAN_KNOWN_INVALID_JSON_REPAIR_GOAL_2026-10-05.md)。执行分支 `feat/n1-resource-discovery`，基线 `88eb3b3492de7dff80ed812011cd09268075e38d`；保留后继成果，不切换、reset、整树 restore、push 或 merge。

## 修复与拒绝边界

1. HTTP adapter 仍只使用严格 `json.loads(content)`。仅增加已实际收到 HTTP 200 的诊断事实；不修改原 body、不补字符、不解 fence、不猜测 substring、不将失败包装成 LLMResult。
2. PgAttemptLLM 在 failed outcome 事务提交后，才返回绑定 Run/attempt 的持久化证明。retained replay 对该失败类型要求实际行 `status=failed`、error/input/output 列与回执一致；冲突返回 `attempt_receipt_conflict`，不派发。
3. 显式 allowlist 仅允许 `provider_invalid_json`、unknown=false、HTTP200、已派发/已返回、finish_reason=stop、非负整数 usage、非空原 content 和匹配的 durable proof。`retryable` 不参与放宽。
4. batch 使用空的、带 `_known_invalid_json_attempt` 的失败占位，通过原 validator 建立 `repair_target`。reviewed structure 占位不回填成功节点；practice 占位不具有有效任务。修复成功替换占位并清除 marker，仍经过原 canonical/task 校验。
5. 独立来源读取将该失败保留为 `failure` 回执，不含 parsed payload 或原坏正文。checkpoint 恢复必须精确重建占位；缺回执、篡改 marker/内容/身份/schema/usage 均拒绝。final 保存不能接受未修复占位。成功内容不得携带包括 null 在内的失败 marker。
6. 沿用整 Run `max_repairs=2`、既有 attempt key、manifest request/output budget、租约与 admission。repair 自身的 JSON 失败继续保守终止；合法 JSON 但业务非法仍可按既有两次上限处理，不能生成 Draft。

未修改 Graph 边、公开 API/DTO/schema/迁移、prompt、模型、temperature/cap、Agent8 内容或 canonical/source/practice 权威规则。上述投影与回执差异仅为这条失败路径提供证据，不改变成功投影的 F1–F4 语义。

## 逐项非收费验收

| 验收项 | 状态 | 实际证据 |
|---|---|---|
| 真实 G6 原 body → 严格 parser → known JSON failure | PASS | 原 7068 bytes，SHA `ffffffa319a2217bd889dca2f4c9416d21fc37d78903cbf4a090ccb3bf8d901c`；实报 2581 input/1534 output、stop；读取前后字节相同 |
| 原 18 阶段冻结合同的 G6 index15 离线副本 → Fake repair1 | PASS | 只在未来离线 fixture ID 下操作；repair_target 指向 G6，repair_count 0→1，完整 practice validator 通过；没有保存 Draft 或改原 Run |
| structure / practice known invalid normal → repair1 → 完整 Draft | PASS | compiled short graph + 真实 PostgresSaver + 应用保存入口；各一个独立 failed normal 与 succeeded repair row，Draft1/Plan0 |
| 新 repair ID、request +1、output reservation、repair2 上限 | PASS | 各完整 owned 场景 normal19+repair1=20 MockTransport 请求；request/output/repair2 独立拒绝矩阵与 restart 保持 |
| repaired JSON 的 canonical/task 保护 | PASS | 非法结构节点、非法任务 links 持续拒绝；合法 JSON 业务非法最多两次修复后失败；repair 坏 JSON 一次后终止；Draft0 |
| unknown、length/truncated、auth、安全、preflight、budget、unsupported/未知错误 | PASS | 显式禁止矩阵，均不进入 JSON repair；现有零派发计量/冻结输入/租约检查继续通过 |
| normal receipt 已提交、checkpoint 未提交 | PASS | 新 owned checkpoint 恢复读取同一 failed normal，无新增 Mock HTTP，不重派 normal |
| repair receipt 已提交、checkpoint 未提交 | PASS | 新 owned checkpoint 恢复读取同一 succeeded repair，无新增 Mock HTTP；repair_count 正确推进 |
| 标准 owned Worker 成功终态 | PASS | `PlanningWorker._process → PlanService.execute_generation`：Run succeeded/none、job completed、Draft1/Plan0、repair1；后续 Worker 不领取、不新增请求 |
| 标准 owned Worker 非法 repair / unknown | PASS | 分别 Run failed/retry、reconciliation_required/reconcile；Draft0；unknown repair0，fresh ledger replay 仍 unknown且零派发；均不能重新领取 |
| 真正 unmarked batch 合同 | PASS | 未来新 unmarked Fake 两种 batch 通过现有 repair；不补格式 marker，不改历史 manifest/fingerprint |
| 原本人失败 Run 与费用记录 | PASS | 实际 RC owned PG 只读：原 Run failed，34 succeeded attempts+1 failed，35 normal/repair0，Draft0/Plan0；历史 1416 文件 SHA 与全部 160 request/result 保持 |

最终 unit/contract/受影响规则与 compiled Fake 回归：**243 PASS，0 FAIL，0 NOT RUN**，其中本批新定向案例58，contract31。真实 owned PG/checkpoint 定向案例：**16 PASS**。PG 在新 `studyplan_test_known_json_*` 两库运行，复用既有迁移，仅导入当前不可变已审核包；所有新临时库已回收，全局角色变更0。

最终命令：

```text
.venv\Scripts\python.exe -m pytest backend/tests/unit/test_known_json_repair.py backend/tests/unit/test_b3_provider.py backend/tests/unit/test_partial_content_repair.py backend/tests/unit/test_v613_projection.py backend/tests/unit/test_reviewed_structure_contract.py backend/tests/unit/test_rc_runtime_budget.py backend/tests/unit/test_run07_real_graph_repair.py backend/tests/unit/test_batched_planning.py backend/tests/unit/test_v67_outline_projection.py backend/tests/contract -q --junitxml=var/known-json-repair-20261005/verified-final.xml
```

PG 最终16项由初轮7 PASS、纠正两个 `draft_ref` 夹具断言后的2 PASS，以及标准 Worker/receipt mismatch 扩展7 PASS组成；未因文档收口重复跑有效 PG。初始 RED（4 FAIL）、test fixture 字段/语法/tuple 断言 FAIL、PG 初轮2 fixture FAIL全部保留，不能从审计抹去。独立复核一次覆盖完整矩阵，修复实际 failed-row 证明与 null marker 两个同调用链边界后闭合。

## 证据、用量与状态

本机证据目录：`D:\studyplan\var\known-json-repair-20261005\`：

- `baseline.json`、`input-hashes.json`：执行基线、1416保护文件与9份生产/新测试输入 SHA。
- `verified-final.xml`：最终243条 unit/contract/受影响回归。
- `pg/results.json`、`pg/extension-results.json`、`pg/worker-*.json`、`pg/replay-*.json`、`pg/receipt-mismatch-*.json`：真实 owned PG/checkpoint 与标准 Worker 的实际结果。
- `final-invariants.json`：原本人失败 Run 的实际只读核对与160/200账本保留。
- `review.json` / `review.md`：关键边界整批独立复核与输入 SHA。

开发路由：root/关键复核请求 `gpt-6.1-sol/xhigh`，PG有界实现请求 `gpt-6.1-sol/medium`；实际解析均 **NOT OBSERVABLE**，未修改全局配置。

| 验证层 | 状态 |
|---|---|
| 严格原 fixture、unit/contract、Fake/compiled graph | PASS |
| 新 owned PG、真实 checkpoint、标准 owned Worker | PASS |
| 本批真实 provider / DNS/TLS / 收费代表 | NOT RUN |
| 本批浏览器与用户内容/体验验收 | NOT RUN |
| 部署、原产品库写入、正式入口/Worker、push/merge | NOT RUN |

产品模型新增 **0**，搜索/外部 RAG 新增 **0**。累计 **160/200，剩40**，没有新增额度或 repair。原本人 RC 第一次生成仍为 **FAIL**，原 response/receipt/usage/failed Run/checkpoint 保留；本批 PASS只证明该失败类型可以由未来新 Run 的现有有界 repair 处理。

## 风险、回滚与下一安全动作

- 本批尚未进行新的真实模型代表，不能保证服务商下一次输出必然成功。usage 或响应证明缺失、非 stop、unknown、截断等仍拒绝进入 repair；repair 坏 JSON 仍保守终止。
- 本地提交可用普通后继 revert 回滚这批源码，不 reset/修改旧 Run、不迁移数据库、不改历史账本。既有严格 parser、repair2 和终态门禁继续有效。
- **STOP**。不自动新建 Acceptance/Run，不恢复旧本人失败 Run。仅用户下一次明确批准后，才按正常 RC 用户流程创建唯一全新 Acceptance/Run，保持37 normal+最多2 repair≤39；remaining40本身不是本轮收费授权。
- 合同修复与非收费门禁 **PASS**；新真实用户生成与本人接受 **NOT RUN**；整体继续 **STAGING_BLOCKED / NOT_READY**。
