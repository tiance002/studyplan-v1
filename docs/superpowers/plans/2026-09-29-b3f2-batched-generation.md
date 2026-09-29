# B3-F2 持久化分批规划 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Native execution in this session; no sub-agent dispatch is required.

**Goal:** 用已有 ai_jobs 驱动单 Worker 的完整路线分批生成，失败立即停止、成功安全重放，保持原确认发布与旧 checkpoint 兼容。

**Architecture:** POST 只原子入队，Worker 顺序执行同一 planning_graph 的逐批节点，GET 返回业务进度。受审核领域包提供确定性基线，模型补充个性化内容；Attempt 账本、checkpoint、业务事实分别保持权威。新协议与旧图独立选择，不重解释旧数据。

**Tech Stack:** 现有 Python 3.11+、FastAPI、LangGraph 1.x、PostgreSQL/psycopg、React 19、TypeScript、pytest/httpx.MockTransport。

**Spec:** `docs/superpowers/specs/2026-09-29-b3f2-batched-generation-design.md`（2026-09-29 七项附条件评审已合入）。

## Global Constraints

- 禁止真实 DeepSeek 付费调用；只允许 Fake/MockTransport 和独立临时 PostgreSQL。
- 禁止迁移、重置、清理现有业务库、Checkpoint 和历史 Attempt；不修改任何既有迁移文件。
- 不引入第二套规划引擎、多 Agent、复杂队列或无关重构。
- 保留九阶段及 27 个必需节点，受审核资源/键/归属/必要关系由领域包提供。
- 新 run 协议 `b3f2-batch-v1`；旧 waiting_user 按原协议执行收尾。
- 涉及破坏旧数据、旧迁移或变更正式发布语义时立即停止并报告。
- 用户明确批准本次设计修订及计划生成，无需再审批这七项修改；本计划未执行，以下测试均 NOT RUN。

## Review Focus

1. 成功 Attempt 落库但 checkpoint 未写时强杀：重放原结果且请求数、计量不翻倍（Task 3/4）。
2. HTTP 入队成功但 Worker 未启动：真实持久化 queued，零模型调用，不能靠内存 background task（Task 2）。
3. 旧版本真实 checkpoint 确认/取消：不按新图解释，不新生成或重复发布（Task 4）。
4. 缺 usage 的成功或失败、未知派发：NULL 不转零，保留费用未知且禁止换键绕过（Task 1/3）。
5. 租约丢失、版本绑定后模型撤销、RLS 下未服务 actor：禁止后续派发或跨项目读取，明确配置/核对状态（Task 2/5）。

## 代码边界与依赖顺序

Task 1 预算/结果 → Task 2 持久化入队/Worker 基础 → Task 3 批次图/局部修复/预算守卫 → Task 4 恢复与旧图 → Task 5 服务装配与业务进度 → Task 6 前端 → Task 7 端到端交付。

只拆分本轮新增职责：`planning_budget.py` 管纯预算，`planning_batches.py` 管领域包/批次数据与校验，`job_repository.py` 管现有队列表的 DML，`planning_worker.py` 管领取与生命周期。LLM 仍走现有端口，发布仍走现有 PlanPublicationService。

所有命令从 `D:/studyplan` 执行；Python 使用 `.venv/Scripts/python.exe`。单里程碑先运行对应新增失败测试，再实现并复测。不要在本轮重新跑 `verify_b3_live` 或任何 `*-live-browser.cjs`。

## Task 1：purpose 预算、诊断和 NULL 计量（M1/M5）

**Files:**
- Create: `backend/app/application/planning_budget.py`
- Modify: `backend/app/core/config.py`, `backend/app/ports/llm.py`
- Modify: `.env.example`（只更新示例默认预算与能力配置，不修改本机含凭据的 `.env`）
- Modify: `backend/app/infrastructure/providers/openai_compatible.py`, `runtime_factory.py`, `__init__.py`, `attempt_ledger.py`
- Test: `backend/tests/unit/test_batched_budget.py`, `backend/tests/unit/test_b3_provider.py`

**Interfaces:**
- `BudgetPolicy(outline: int, structure: int, practice: int, repair: int, deployment_cap: int, model_cap: int)`，frozen dataclass。
- `BudgetPolicy.for_purpose(purpose: str) -> int`：有效值；目标高于硬上限直接 ValidationAppError。
- `BudgetPolicy.as_dict() -> dict[str, int]`：冻结目标和两级上限，不含密钥。
- `OpenAICompatibleLLM.request_options(purpose: str) -> dict[str, object]`：返回 model/max_tokens 和适用时的 thinking；调用与 fingerprint 共用该函数。
- `LLMResult.input_tokens/output_tokens/cost_micros: int | None`；新增 `diagnostics: dict[str, object]`；LLMFailure.details 保存相同诊断。旧保存结果缺新增字段时通过默认值兼容。

- [ ] 写预算反例测试：默认任务 4096/8192/4096/8192；deployment=8000 与 structure=8192 报错而不静默压缩；非正整数/布尔拒绝；未知模型无能力配置拒绝；配置必须在模型派发前校验。

```python
def test_structure_cap_conflict():
    import pytest
    from app.application.planning_budget import BudgetPolicy
    from app.core.errors import ValidationAppError
    with pytest.raises(ValidationAppError):
        BudgetPolicy(4096, 8192, 4096, 8192, 8000, 393216).for_purpose("planning.structure")
```

- [ ] `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_batched_budget.py backend/tests/unit/test_b3_provider.py`，确认新增断言先 FAIL。
- [ ] 实现配置默认 deployment=8192；新增四 purpose 预算及兼容模型能力配置；两条工厂统一装配。官方精确 host/model 的能力采用受核对值；其余服务使用显式能力配置。

```python
def for_purpose(self, purpose):
    target = {"planning.outline": self.outline, "planning.structure": self.structure,
              "planning.practice": self.practice, "planning.repair": self.repair}[purpose]
    values = (target, self.deployment_cap, self.model_cap)
    if any(type(v) is not int or v < 1 for v in values) or target > min(values[1:]):
        raise ValidationAppError("模型输出预算配置冲突")
    return target
```

- [ ] 用 MockTransport 捕获实际 HTTP 请求。分别测试官方 Flash、其他模型名、其他 host，只有已确认条件发送 thinking。完整 JSON、非法 JSON、length 含 reasoning、usage 缺失、信封为 list、字段类型错误均有反例。NULL 计量不得 `or 0`。

```python
def test_length_retains_usage():
    import httpx
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.ports.llm import LLMFailure
    def reply(request):
        return httpx.Response(200, json={"model": "deepseek-flash", "usage": {
            "prompt_tokens": 11, "completion_tokens": 23}, "choices": [{
            "finish_reason": "length", "message": {"content": "{", "reasoning_content": "abc"}}]})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="mock", model="deepseek-flash", client=client)
        result = llm.generate_structured(purpose="planning.outline", payload={}, schema_name="OutlineV2", run_id="r", attempt_id="r:o:1")
    assert isinstance(result, LLMFailure)
    assert (result.input_tokens, result.output_tokens) == (11, 23)
    assert result.details["reasoning_chars"] == 3
    assert result.details["max_tokens"] == 4096
```

- [ ] 解析前保存已知用量/耗时；失败/成功均保留 options、finish/count 诊断，不保存正文、思考或凭据。transport_unknown 也保存已知请求参数，usage NULL。
- [ ] 搜索所有 LLMResult 计量读取方并修正 NULL 汇总；Mock Fake 可以明确给 0，缺失真实计量不能推算。预算/思考/协议进入请求指纹，旧 null 结果只安全读取，不回填。
- [ ] 重跑上述命令，保留输出到 `docs/acceptance/b3f2/batched/M1-tests.txt`，PASS 后精确暂存该任务文件并提交。

## Task 2：原子入队和单 Worker 租约（后台执行基础）

**Files:**
- Create: `backend/app/ports/planning_jobs.py`, `backend/app/infrastructure/db/job_repository.py`
- Create: `backend/app/infrastructure/worker/planning_worker.py`, `backend/app/tools/planning_worker.py`
- Modify: `backend/app/application/plan_service.py`, `backend/app/api/v1/routes.py`, `backend/app/composition.py`, `backend/app/core/config.py`
- Test: `backend/tests/integration/test_planning_jobs_pg.py`, `backend/tests/e2e/test_async_generation.py`

**Interfaces:**
- `JobClaim(job_id: str, run_id: str, project_id: str, actor_id: str, lease_token: str)`。
- `PgPlanningJobRepository.enqueue(run: RunRecord, initial: dict, manifest: dict) -> None`：一个事务写三张现有表。
- `claim(project_id: str, worker_id: str, lease_seconds: int) -> JobClaim | None`；`renew(claim: JobClaim, lease_seconds: int) -> bool`；`finish(claim: JobClaim, status: str) -> bool`：全部 fencing。
- `read_submission(project_id: str, run_id: str) -> dict`：取唯一 submission 事件，缺失/多个矛盾版本失败。
- `PlanService.submit_generation(scope, project_id, goal, prefs_snapshot=None) -> str`；`execute_generation(project_id: str, run_id: str) -> None`：前者只入队，后者 Worker 调用。
- `PlanningWorker.tick() -> bool`：一次处理一个 job，返回是否领取；`run()`：有界轮询、优雅停止。

- [ ] 用独立临时 PG 写入队测试：job_key 重复不产生第二 job，故障注入 events/jobs 插入失败整体回滚，无 run 孤儿；scope 不属于项目拒绝。
- [ ] HTTP 测试在未启动 Worker 时 POST 必须返回 queued/202、Fake call_count=0；然后启动 Worker 才生成。用等待 Event 的 Fake 阻塞模型，POST 仍不等待它（避免仅靠毫秒计时判断）。
- [ ] `.venv/Scripts/python.exe -m pytest backend/tests/integration/test_planning_jobs_pg.py backend/tests/e2e/test_async_generation.py`，新增测试先 FAIL。
- [ ] 实现 enqueue：run queued、submission.detail 保存经服务端验证的 actor/project、goal/prefs、完整领域包快照/哈希、模型配置引用及 manifest；不存 API Key。run/job/event 写入共享连接、同事务，不复用目前三个独立事务调用拼接。
- [ ] claim 只领取 pending 或租约过期的 running 且 Run queued/running 的任务。先设置 project RLS；row lock + SKIP LOCKED，更新新 lease_token、expiry、worker_id 和 attempts；failed/waiting_user/unknown 不领取。

```sql
SELECT j.job_id FROM ai_jobs j JOIN ai_runs r ON r.run_id=j.run_id
WHERE r.project_id=%s AND r.status IN ('queued','running')
AND (j.status='pending' OR (j.status='running' AND j.lease_expires_at < now()))
AND j.available_at <= now()
ORDER BY j.created_at,j.job_id FOR UPDATE OF j SKIP LOCKED LIMIT 1;
```

- [ ] renew/finish 的 WHERE 同时含 job_id、run_id、lease_token、running；不能用旧 claim 覆盖新租约。Worker 持有全局单进程 advisory lock；模型调用期间独立连接每 lease/3 续租，不新增队列服务。
- [ ] Worker actor allowlist 从服务端配置 `PLANNING_WORKER_ACTOR_IDS` 读取；用 app.actor_id 查其 learning_projects，再 app.project_id 领取，重新验证 owner。API 拒绝服务范围未配置 actor；文档说明新增用户需加入范围，首版不自动发现全库。
- [ ] test：两个 Worker 竞争仅一个执行；旧租约 renew/finish 为 False；无上下文看不到别项目；错误 actor 不派发。采用 multiprocessing + sentinel 验证强杀释放锁后可领取过期任务。
- [ ] 重跑相关命令、保留原始输出到 `M2-jobs-tests.txt` 后提交。

## Task 3：冻结批次、逐步图、局部修复与整次预算（M2/M3/M4）

**Files:**
- Create: `backend/app/agent_workflows/planning_batches.py`
- Modify: `backend/app/agent_workflows/state.py`, `nodes.py`, `graphs.py`, `validators.py`
- Modify: `backend/app/infrastructure/providers/planning_demo.py`, `attempt_ledger.py`
- Test: `backend/tests/unit/test_batched_planning.py`, `backend/tests/integration/test_run_budget_pg.py`

**Interfaces:**
- `freeze_manifest(pack: dict, policy: BudgetPolicy, model_ref: str, generic_stage_count: int = 4) -> dict`：immutable JSON；受支持包保留所有 stage/node 键；配置可预拆结构批次。
- `structure_payload(state: dict, batch: dict) -> dict`、`practice_payload(state: dict, stage_key: str) -> dict`：局部上下文。
- `validate_structure_batch(payload: dict, batch: dict, pack: dict) -> list[str]`、`validate_practice_batch(payload: dict, stage_key: str, structure: dict) -> list[str]`。
- `merge_batches(outline: dict, structure_batches: list[dict], practice_batches: list[dict], pack: dict) -> dict`：完整旧投影结构，拒绝重复/缺失。
- `attempt_key(run_id: str, purpose: str, stage_key: str, batch_index: int, repair_index: int = 0) -> str`。
- `build_batched_planning_graph(nodes, checkpointer=None)`：同 LangGraph 新协议 builder；旧 build_planning_graph 保留。
- `run_batched_planning_graph(nodes, initial)`：单元机械验证解释器，与真实图逐步路由一致，不是另一业务引擎。

- [ ] 加入清单测试：当前 Agent 为九阶段/27 必需键、structure=9/practice=9/max_requests=21/max_output_budget=131072。修改 pack 要求更多节点后 manifest 必须保留它们，不硬编码 27 作为上限。

```python
def test_manifest_preserves_agent_requirements():
    from app.infrastructure.domain_pack import select_domain_pack
    from app.application.planning_budget import BudgetPolicy
    from app.agent_workflows.planning_batches import freeze_manifest
    pack = select_domain_pack("学习 Agent 开发")
    manifest = freeze_manifest(pack, BudgetPolicy(4096,8192,4096,8192,8192,393216), "mock:1")
    assert manifest["structure_batches_count"] == 9
    assert manifest["practice_batches_count"] == 9
    assert manifest["max_requests"] == 21
    assert manifest["max_output_budget"] == 131072
    assert set(manifest["required_node_keys"]) == set(pack["required_node_keys"])
```

- [ ] 写失败传播测试，Fake 在 outline、第5结构批、第3实践批分别返回 length；调用数分别=1、6、13，没有之后阶段或 repair。空实践也是失败；先前有效批次仍在 state。
- [ ] `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_batched_planning.py backend/tests/integration/test_run_budget_pg.py`，先确认 FAIL。
- [ ] 新 State 加 manifest、structure_batches、practice_batches、current_structure_index/current_practice_index、repair_target、repair_count、protocol；每个模型节点只执行一个 Attempt。图增加 conditional edges，在每个生成失败处直接 record_failure/END。
- [ ] 领域包作为不可改基线：由应用确定 keys/stages/required edges/resources；模型输出只填写可个性化字段及补充节点。矛盾键、资源替换、越阶段归属在局部校验时失败，不通过静默重新分配让测试绿。
- [ ] 结构批次验证 node/unit 非空、objective 非空、稳定键、unit 关联、已声明外部前置键；实践只接收该阶段结构、任务 acceptance/in_scope/out_scope/core 关联。阶段依赖及含子关系从审核蓝图合并，全局检测模型新增循环或未知引用。
- [ ] merge 按骨架顺序重排全局 order_index，缺阶段/缺 required_node/重复键拒绝；调用现有 validate_plan_structure + validate_route_structure 并补 resource/version 真伪、学习顺序验证，完整通过才调用原 save_draft。
- [ ] repair 只用当前 invalid 批次和局部错误（purpose 仍 planning.repair，但 schema 明确结构或实践）。整次两次配额，不重发 length，不全量重建；不能修复资源伪造。无法定位的全局关系错误直接失败。
- [ ] 派发前账本在 run advisory lock 下验证 manifest 完整性、唯一 attempt_key、每 purpose 最大计数和 output budget；先查已存在 Attempt，重放不占新配额。未知仍占额度，禁止不同 key 绕过 frozen 批次目录。超额返回 run_budget_exhausted，零外部调用。
- [ ] 反例：重复调用同一 Attempt、篡改 manifest、repair_count 滞后、恢复重复累计、跨批键冲突、节点全有但阶段单元缺失、循环与伪造来源。MockTransport 的已知 token 合计按唯一 Attempt 求和；缺失使用 usage_complete=False。
- [ ] 跑对应测试输出到 `M3-batches-tests.txt`；新协议不改变旧 builder 的原 generation 路径，提交精确文件。

## Task 4：新图恢复和真实旧图收尾（M3/旧图兼容）

**Files:**
- Modify: `backend/app/infrastructure/checkpointer/planning_executor.py`, `backend/app/ports/graph_runner.py`
- Modify: `backend/app/application/plan_service.py`
- Create Test: `backend/tests/integration/test_batched_recovery_pg.py`, `backend/tests/integration/test_legacy_checkpoint_compatibility.py`
- Create test helper: `backend/tests/helpers/legacy_planning_checkpoint.py`

**Interfaces:**
- `builder_for_version(graph_version: str)`：`b3f2-batch-v1` 返回新 builder；已知旧版返回旧 builder；unknown 拒绝。
- `PgPlanningExecutor.execute_or_resume(nodes, initial, thread_id, graph_version, guard) -> PlanningTrace`；guard 是零参数可调用，在每个步骤/派发前验证有效 claim 和 Run 状态。
- 既有 `finish(thread_id, graph_version, decision, result_id, draft_hash)` 签名不变，按保存版本选择图。
- `legacy_planning_checkpoint.py` 从 Git 基线 39e79ad 导出实际 graph/nodes/state/validators 到临时测试源码目录，仅用于生成旧数据；测试保存其 source hash 和版本。

- [ ] 新 PG 恢复测试先 FAIL：子进程 Fake成功并通过账本写入，在 checkpoint 前 sentinel 阻塞，父进程 kill；另一个进程恢复后相同 attempt_key 无第二次网络请求。另测 checkpoint 完成后 kill，应从下批开始。
- [ ] unknown 故障：外部响应后账本 UPDATE 注入异常，账本保持 dispatched；恢复只核对不派发。明确 length 成功写入失败对象但投影来不及更新，恢复补 failed 而不继续。
- [ ] 用真实旧版代码在临时 PG 创建两份 waiting_user：一份批准、一份取消，禁止先把生产库转储进测试。随后新程序 subprocess 启动，调用原决定接口并断言：旧 thread/版本不变、旧 hash 不变、模型0新增、重复 approve 返回同 plan_id、一份publication、cancel 无publication。
- [ ] `.venv/Scripts/python.exe -m pytest backend/tests/integration/test_batched_recovery_pg.py backend/tests/integration/test_legacy_checkpoint_compatibility.py`，先 FAIL。
- [ ] executor 在同 thread advisory lock 下读 Run/lease/checkpoint/Attempt。checkpoint 无值才 initial invoke；有新协议非终态用 graph.invoke(None, config) 恢复；待确认/终态/unknown 不生成。不是通过新 run_id/thread_id 强制重跑。
- [ ] 向真实 Graph 配置足够 recursion_limit（按 frozen 最大批次和每批节点数推导）避免旧默认 25 步限制使19请求流程中途失败。显式计算步数上限，不设无限。
- [ ] finish 使用旧builder原 awaiting节点路径；PlanService 仍先通过现有 publication/cancel 事务，再 acknowledge checkpoint。重复收尾只确认已有业务结果。无法解释旧版本报安全错误，不更新旧 checkpoint。
- [ ] 测模型设置撤销、Worker 强杀续租失效、新 claim 与旧进程同时返回、未知版本拒绝、旧发布计划读取。重复恢复不重复保存草案、计量、事件计数或发布。
- [ ] 原始输出与旧源码 hashes 到 `M4-recovery-tests.txt`；相关测试 PASS 后提交。

## Task 5：Worker 服务装配、冻结模型和业务进度

**Files:**
- Modify: `backend/app/composition.py`, `backend/app/application/container.py`, `backend/app/application/plan_service.py`
- Modify: `backend/app/infrastructure/providers/runtime_factory.py`, `backend/app/infrastructure/db/job_repository.py`
- Modify: `backend/app/domain/runs/models.py`, `backend/app/api/v1/schemas.py`, `views.py`
- Modify: `backend/app/infrastructure/db/run_repository.py`, `backend/app/infrastructure/worker/planning_worker.py`
- Modify: `.env.example`、`scripts/b3f1-dev.ps1`（说明并提供显式 Worker 启动，不自动触发真实生成）
- Test: `backend/tests/e2e/test_async_generation.py`, `backend/tests/contract/test_v1_dto_contract.py`

**Interfaces:**
- `RunProgress`：phase、current_stage_index/title、total_stages、completed/total_structure_batches、completed/total_practice_batches、completed_batches、request_count/max_requests、input_tokens/output_tokens nullable、usage_complete、failure_phase/stage；无图字段。
- `get_progress(project_id: str, run_id: str) -> dict | None`：从 checkpoint 完成索引与账本校正后的最新业务事件读取。
- `publish_progress(claim: JobClaim, progress: dict) -> None`：fencing；终态不变更，重复checkpoint版本不重复计数。
- `PersonalPlanningRuntimeFactory.bind_submission(scope, project_id, run_id) -> str` 冻结现有加密配置版本；`for_bound_run(project_id, run_id)` 取相同配置；不静默改用当前模型。

- [ ] 覆盖queued→running→逐批→waiting_user、失败阶段、unknown的 GET 投影。断言 GET 无模型调用；不含 thread_id/checkpoint/node_name；NULL计量保持NULL。旧 Run 无progress返回None。
- [ ] Worker 使用冻结版本/manifest 执行；队列中不得含 key/cookie。绑定后更改设置不影响该Run，撤销被冻结版本明确失败。测试未服务 actor 入队配置错误与跨项目GET拒绝。
- [ ] 去掉新后台Run按旧总时长简单判 run_interrupted 的逻辑。健康续租19批允许持续运行；无租约且unknown按表核对。Run is_terminal 与 job terminal 分别处理，不能仅任务完成就发布。
- [ ] 将进度写入 ai_run_events.detail；只在checkpoint稳定点更新完成索引，恢复重新计算并补投影。模型调用计量由账本汇总唯一attempt，支持known subtotal + usage_complete，不伪造货币cost。
- [ ] 默认新HTTP协议 `b3f2-batch-v1`，旧Run读取不改变graph_version/thread；新run不能被环境旧version误选。测试两种settings入口及生产Fake拒绝仍在。
- [ ] `.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_async_generation.py backend/tests/contract/test_v1_dto_contract.py`，先FAIL后PASS并保存 `M5-service-tests.txt`，提交。

## Task 6：前端逐阶段进度与契约

**Files:**
- Modify: `frontend/src/features/planning/PlanningPage.tsx`
- Modify generated: `contracts/openapi.json`, `frontend/src/api/generated/schema.d.ts`
- Create: `frontend/tests/planning-progress.browser.cjs`
- Modify: `scripts/b3f2-browser.cjs`（已有Fake验收增加后台启动与轮询，不改真实脚本）

**Interfaces:** `RunView.progress` 可选有限业务结构；现有 api.generate/run/draft/decide 签名不变。

- [ ] Playwright Mock HTTP：POST立即202，随后GET依次返回queued、structure第2/9阶段、practice第4/9阶段、waiting_user；断言只有一次POST、显示阶段标题及已完成数、waiting前无确认按钮。
- [ ] 反例：刷新复用storage run_id；运行中禁用提交；轮询失败后保留run_id并可刷新；length失败显示位置；unknown显示需核对；旧run无progress仍正常。
- [ ] 首先运行 `node frontend/tests/planning-progress.browser.cjs` 确認进度断言FAIL。测试脚本仅mock API且断言任何未拦截 generate 被拒绝；不能连当前真实服务。
- [ ] render有progress时用业务文案“正在生成第 x/y 阶段 · 知识结构/实践任务”，不输出LangGraph/线程字段，不以请求次数等于费用。run queued/running时生成按钮禁用；不改V6.3其他布局。
- [ ] 导出DTO契约：使用既有 `scripts/export_openapi.sh` 的Fake/memory环境，接着 `npm --prefix frontend run gen:api`；不可带入真实服务密钥。类型从Pydantic生成，不手工改schema.d.ts。
- [ ] `npm --prefix frontend test`、`npm --prefix frontend run build`、新增浏览器脚本及合同测试通过；保存 `M6-frontend-tests.txt`，检查1366/1440/1920下状态条，无布局回归，再提交。

## Task 7：独立 Fake V1 端到端及最终交付（M6）

**Files:**
- Create: `backend/tests/e2e/test_batched_agent_route.py`, `scripts/b3f2-batched-demo.ps1`
- Create: `docs/acceptance/b3f2/batched/Delivery.md`, `commands-and-status.md`
- Produce: `agent-route.json`, `stage-example.json`, `manifest-example.json`, `run-progress.json`, screenshots及逐任务原始日志。

- [ ] 脚本启动独立临时业务库/Checkpoint，明确Fake模式、独立端口、Worker actor范围；先检查test DB名称和provider，再允许生成。不得复用当前8000服务进行POST，不调用本地业务库迁移。
- [ ] 整条真实HTTP→enqueue→Worker→Graph→账本→草案→原确认/发布事务→读回验证，Fake九阶段且所有27节点、子关系、必要依赖、资源、任务齐全。生成19次无repair，另反例21上限包含两次修复；不把Fake说成云验证。
- [ ] 输出单阶段结构/实践和完整合并JSON、冻结manifest及全过程业务进度；前端显示已发布路线和真实实体ID。旧版计划读取和旧checkpoint结果在报告独立列证据。
- [ ] 每项M0–M6及七项评审建映射表：requirement → 测试名称/原始日志/截图 → PASS/FAIL/NOT RUN。缺少证据的要求不能报告完成；安全测试只运行临时库且核对不触及现有迁移文件。
- [ ] 最后一次完整必要回归，命令分开执行并记录退出码：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m mypy backend/app
npm --prefix frontend test
npm --prefix frontend run build
node frontend/tests/planning-progress.browser.cjs
git diff --check
```

完整PG测试若环境不可用报告NOT RUN，不通过跳过伪造PASS。脚本输出Tee到对应原始日志，记录实际执行命令、exit code、测试数量，失败修复后仅重跑受影响检查；无新改动不反复全量回归。

- [ ] 比较 `backend/alembic/versions` 与39e79ad hash，必须无差异；确认没有业务库迁移/清理调用、历史Attempt变更、密钥和完整敏感prompt进入git。不跟踪原有.workbuddy/design-preview。
- [ ] Delivery写清修改文件、流程图、预算目标/两级上限/最终值、反例结果、两个JSON示例、资源真实性、V1 Worker部署限制与延期项。真实DeepSeek=NOT RUN；建议默认19次、最大21次、默认output预算上限131072，不声称等于实际tokens或账单。
- [ ] 所有授权范围内实现与必要检查通过后，按已有GitHub提交授权提交并推送当前codex分支（不强推、不合并master）。交付commit/HEAD及报告，停止；受控真实验证等待用户另行授权。

## 覆盖与计划自检

| 要求 | 实施/验证责任 |
|---|---|
| M0 历史/当前诊断 | 已有M0报告，不更改历史数据 |
| M1 预算与模型适配 | Task1，Task3整次预算 |
| M2 完整骨架/分批/合并 | Task3，Task7 |
| M3 停止与一致恢复 | Task2/3/4 |
| M4 局部有界修复 | Task3 |
| M5 失败持久化与计量 | Task1/3/4/5 |
| M6 完整Agent与旧计划前端 | Task4/6/7 |
| 评审1后台执行 | Task2/5/7 |
| 评审2预算生效 | Task1 |
| 评审3状态表 | Task3/4/5 |
| 评审4真实旧checkpoint | Task4 |
| 评审5总预算与业务进度 | Task3/5/6 |
| 评审6审核确定事实 | Task3/7 |
| 评审7反例及隔离 | Task1–7 |

自检：七项均映射到具体任务；接口命名与前后责任一致；无第二队列/模型引擎；无迁移变更；请求上限含未知Attempt且重放不双计；没有把真实验证作为本次完成条件。文档修订/计划生成完成，产品实现与所有新增测试仍 NOT RUN。
