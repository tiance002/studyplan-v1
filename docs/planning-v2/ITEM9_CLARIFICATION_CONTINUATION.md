# Item 9 — Initial Clarification Continuation

日期：2026-10-09。**C0–C2 PASS；React U1–U3 正在实施。** 本报告保留真实与合成验证边界，不代表真实产品模型或教材语义验收。

## 基线与范围

Start HEAD：`9be82b98c714e378812b8e17728c452f93951496`，branch：`feat/n1-resource-discovery`。后端阶段源码验收基于该 HEAD 加本报告列出的工作树差异；阶段提交 SHA 在统一交付记录中记录。

原 U0 报告与进度保留；原型 SHA256：`dc1dd08b40520f76c1fece10858dd2c8e38843e4b2400fed0ea8b9ef2915df7b`，本轮未修改。开始时只有两份预期文档变化；`.workbuddy/`、`design-preview/` 不操作。证据目录：`var/planning-v2-item9-clarification-20261009/`，其中 baseline 保存 tracked hashes、U0/进度原文与私有配置 hash，无配置内容或认证头。

## C0：无需 migration 的持久化

`0001` 的 `ai_run_events` 已有 `event_id bigserial`、Run 外键、`status text` 和 `detail JSONB`；实际新 owned PG 的 information_schema 读回保存在 `owned-databases.json`。现有 `PgPlanningJobRepository.in_transaction` 支持同连接 Run / Event / Job 入队，复用规划 fence 与项目锁。没有新增表、migration、Worker、Receipt 或预算平台。

内部 Receipt 已可能保留 Provider response payload；本轮增加经过 Item 1 Validator 校验的规范化问题事件，并通过受信 DTO 读取，未直接公开原始响应。

## 生命周期与来源

原 Run 保持 `failed + none / goal_clarification_required`，原 Attempt/Receipt 和原 Run 行不修改。保存问题成功后才终结为可答复状态。问题事件冻结 actor/project、Run/root、原 GoalSpec/输入 hash、Profile hash、问题稳定身份及版本、Receipt/manifest 绑定。

用户主动提交新答案时，服务端从父 Run 取得实际问题，校验所有绑定后，在同一预算根下创建新的 Run/Job。父事件仅追加已确认续接引用，不将父 Run 重新排队。最多两轮用户答案、每轮三个问题、单答案最多 2000 字符；第三版问题可读但不可再次提交。

Item 1 消费未改写的原 GoalSpec，以及绑定 actual question ID/version/source 的新用户事实；先前硬约束与 learner claims 必须保留，project_context 仍来自原 GoalSpec。`clarification.answers[0..5]` 是最多两轮答案的有界来源。实际索引成员资格由 Item 1 和冻结 event/Receipt/context 证明；Item 2 仅兼容这些来源语法，不把白名单当作来源证据，不重新解析 raw goal。

Semantic Replanning 保持 Item 8 原流程。该窄接口只续接 initial 澄清，不将 semantic 失败自动变成可回答 initial 问题。

## 预算、并发与恢复

续接 manifest 绑定澄清 context；Runtime 在 Item 1 前检查 marker/context 对称及 durable consent。context 输入指纹从 parent/version/规范化本轮答案重新计算。冻结提交、根及所有同家族 Run 的 reservation、actual excess 和 unknown 共同受原预算限制，无新预算根、cap 增量或新凭据。

普通第二次 initial 仍被 `v2_initial_run_exists` 拒绝。原 unknown/reconciliation/cancelled/其他 failed 无法使用澄清接口；子 Run unknown 不自动换身份或重派。项目锁与同连接事务保证并发创建唯一续接；同键同答案返回原子 Run，同键异答案冲突。

问题或未完成诊断写入的 PostgreSQL 故障使用既有 `ReviewPersistenceInterrupted`，不产生假的可答复终态。新 Worker 接管仍校验 fence，成功 Receipt 被复用，恢复新增外部派发为 0。

## API / DTO

- `GET /plans/v2/availability`：当前账号 scope 下实际装配/准入的 initial_generation、clarification、semantic_replanning、local_change 与人类说明；无预算、DSN 或内部身份。
- `GET /runs/{id}`：可选 typed `clarification`，包含 question_id/text、clarification_version、can_submit_answers、message、continuation_run_id；另有有界 typed planning_issues。
- `POST /plans/v2/owned/clarifications`：parent_run_id、clarification_version、answers、idempotency_key；响应沿用 202/run_id/status_url。
- `goal_clarification_required` 显示“需要补充信息”，不提示重派。
- OpenAPI 与生成 TypeScript 已同步，无通用 resume API。

未完成课程仍不生成可确认 Draft。恢复时先执行现有 Compiler 的 authority/server snapshot/findings 全部校验，只有已验证的 `field=incomplete` 分支才保存固定人类诊断；不公开 raw Provider 文案。

## 实际验证

| 检查 | 结果与证据 |
|---|---|
| 新增 Item 1 输入绑定与直接回归 | PASS，初次 GREEN 53；最终与直接合同合并为 119 PASS，`unit-contract-final-green.txt`，exit 0。 |
| 新 owned 业务 PG + 独立 checkpoint / Worker / Cookie-CSRF HTTP 矩阵 | PASS，31，`pg-final-green.txt`，exit 0。首次 27 是其子集，未相加冒充独立测试数。 |
| 独审发现的四组边界 | PASS，首组 4、第二组 9 定向结果，`review-targeted-green.txt` / `review-binding-incomplete-green.txt`；保持原 RED。 |
| 两轮指纹、澄清后 local/semantic、旧 ready→semantic | PASS，3，`review-final-direct-green.txt`，exit 0。 |
| 实际本地 TCP HTTP（非 TestClient） | PASS，`socket-http-success.json`：Cookie/CSRF、澄清→新 Run→三阶段 Draft→明确确认→current/history 相等；公开 generate 503。 |
| Ruff / import & 定向 collection / diff | PASS，受影响 119 项实际加载并通过，`review-ruff.txt`，`git diff --check`。未重复完整 Backend/Item 7/8 历史矩阵。 |
| 真实产品 LLM / Search / Reader / 正式库 / 浏览器 React | NOT RUN 于后端阶段。外部端口全部显式合成；React 浏览器在下一阶段独立记录。 |

owned schema/数据库名和 roles_created=[] 保存在独立 receipts；全局角色未创建或修改。多轮定向测试各自使用新 owned 数据库，未写旧 Item 7/8 证据。TCP 浏览器装配只使用本轮新库，未读取正式 DSN。普通沙箱的 loopback 服务启动未成功，服务停止后通过批准的本地进程执行方式复用本轮 owned 库，未重派任何产品请求。

RED 包括缺少 clarification 输入、JSONB list/tuple 比较、下游来源语法，以及独审反例。最早 unit RED 的包装 shell 曾返回 0，而 pytest 输出为 FAIL；报告不以该 shell 值宣称 RED 成功，后续由实际 pytest returncode 记录。没有用 Fake 正确字段宣称真实语义 PASS。

## 独立审查

独立审查从实际源码、diff、冻结合同和证据主动发现四组问题：省略 context、availability actor 准入、答案指纹绑定、可信 incomplete / 持久化中断。修复与同 fixture 定向关闭复核后 **PASS**；未重复完整 PG 矩阵。生命周期、原 Run/Receipt、来源成员、共享预算、普通 root 防护、幂等、unknown、Worker fence 与 Item 8 兼容均核对。请求 Sol 6.1 xhigh，实际解析 `NOT OBSERVABLE`；审查者没有修改文件或运行 PG/外部调用。

修改职责：Item 1 输入/来源最小扩展、澄清 Domain/DB adapter、PlanService/API/Run 投影、Runtime/预算家族/入队的必要适配、测试与派生契约。Goal/Profile/Capability Schema 核心语义、Policy v2、hash 算法、架构合同和教材审核资格不变。

`INITIAL_CLARIFICATION_CONTINUATION_PASS`

`PUBLIC_GENERATE_NOT_ENABLED`

React 正在按用户授权继续；真实产品语义验收仍待另行授权。不 push、merge、deploy。
