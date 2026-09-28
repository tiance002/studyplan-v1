# B2-V 定向修复验收（2026-09-28）

审计起点：`d299e8765fd1f5e19737a550fdbadb6a01a43d43`，工作树干净；已包含既有 B2-V，未重复实现发布事务、取消互斥、资源降级等已有能力。旧工程未修改。

## 修复

1. 发布重放按 PublishResult.revision 回读，并核对 plan_id；不再取当前版本。
2. HTTP edit 必须携带当前 draft_hash；仓储 SQL 同时比较 hash 与可编辑状态，过期窗口返回 409。更新原测试中的无条件草案改写，使其显式携带旧 hash。
3. 实体 ID 对 project/key 使用无损 UTF-8 JSON + URL-safe Base64，不清洗、不截断。不同键不共用 ID。DTO 取消这些实体 ID 的旧 64 字符限制；同步导出 OpenAPI 和 TS 类型。
4. 目录按完整生成内容的 SHA-256 内容版本隔离，实体及关联冲突时 DO NOTHING。0005 只移除逻辑键唯一约束并增加检索索引，不重写任何旧 ID/FK/内容。旧 slug ID 继续可读，不尝试修复过去已经发生的覆盖。新内容产生新 ID；旧总结/实践进度仍属于旧实体，不自动迁移到新内容。降级若存在重复逻辑键，由 UNIQUE 约束安全拒绝。
5. 生成装配、执行或持久化抛异常时写 failed；付费 dispatch_unknown 立即停止后续调用并写 reconciliation_required/reconcile。Run SQL 使用 WHERE version=expected_version，并保护终态。

B2 仍使用同步解释器；HTTP 202 在同步生成完成后返回。这不是生产级异步 Graph/worker。

## 真实命令与输出

```powershell
.venv/Scripts/python -m pytest backend/tests/e2e/test_b2v_http_end_to_end.py -k regression -q -rs
# 修复前：5 failed（历史重放 v2、旧窗口返回 200、并发 [200,200]、键仅 2 个 ID；异常测试 fixture 修正后确认 running）。
.venv/Scripts/python -m pytest backend/tests/e2e/test_b2v_http_end_to_end.py -k regression -o addopts= -q
# 修复后：7 passed, 17 deselected in 14.85s
.venv/Scripts/python -m pytest -o addopts= -q
# 最终完整重跑：385 passed in 124.42s (0:02:04)
# 含领域 EDIT 入口 CAS 与旧 ID/长键反例；输出 var/b2v-commit-full.txt
# 全量收集后新增的旧 ID/长键反例单独执行：1 passed, 23 deselected in 5.41s
.venv/Scripts/python -m ruff check backend
# All checks passed!
.venv/Scripts/python -m mypy backend/app
# Success: no issues found in 62 source files
$env:PYTHONPATH='backend'
.venv/Scripts/python -m app.tools.export_openapi
npm --prefix frontend run gen:api
npm --prefix frontend run build
# tsc -b && vite build；27 modules transformed；built in 1.21s
```

另补监听 localhost 的 Uvicorn + httpx + 真实 PG 反例：

```powershell
.venv/Scripts/python -m pytest backend/tests/e2e/test_b2v_socket_counterexamples.py -o addopts= -q
# 4 passed in 16.26s：历史重放、双窗口/旧内容、并发编辑、生成后取消保留历史。
```

其他 HTTP 反例通过 FastAPI TestClient/ASGI 与真实 PG 仓储执行。PG 反例只使用随机 `studyplan_test_*` 临时库及已有独立迁移/应用角色，测试后删除临时库。无 PG 跳过。原始输出本机保存在 `var/b2v-commit-full.txt`、`var/b2v-counterexamples-final.txt`、`var/b2v-socket.txt`。
