# B3 最小闭环进度与验收（2026-09-28）

B2-V 修复提交 `94ad097` 后推进 B3，基础实现提交 `cf467bf`。已接入 OpenAI 兼容 Provider、审核内容包、实际 StateGraph / 独立 PG Checkpointer、最小路线前端。用户填写 DeepSeek 配置后，真实外部模型生成、确认、回读、重放及 checkpoint 验收通过；Fake / MockTransport 测试仍单独标明。

## 实现与边界

- Provider 使用 `/chat/completions` JSON 模式，明确各阶段字段；每次派发前提交 attempt，成功响应留存供同 attempt 精确重放；未知结果不得自动重发。记录 model、prompt/schema、tokens、latency；未配置模型价格，cost 保持未知，不估算实际费用。
- Python 工程入门包只读发布，引用 Python 3.14 官方教程四个章节，保持原章节顺序。已检查来源及结构，不宣称完成全面教学质量评估。
- 实际 StateGraph 通过 PostgresSaver 写独立 checkpoint 数据库。每个 thread 使用 PG session advisory lock；正式业务批准/取消先提交，再恢复图关闭等待点。关闭失败进入 reconciliation_required，同幂等决策可确认已提交结果。生成运行恢复不盲目再次派发。
- 仍为同步 invoke：HTTP 202 在生成结束后返回；没有生产异步 worker、调度器或后台队列。
- 前端包含服务端映射的本地会话、生成/Run 状态、阶段标题/目标/顺序编辑、hash CAS、确认/取消、正式路线回读及官方资源。未保存编辑不能确认，409 加载最新内容，待对账禁止新调用。完整注册登录留待 B6。
- 0006 增加 provider attempt 留存字段；受审资源由安装命令播种，运行请求不做 DDL。运行 checkpoint 角色无建表权限，业务应用角色受 RLS 约束。
- 审查发现的实践 repair 丢失已先复现再修复：输入带当前实践，输出实践回写，1 次 repair 后进入等待确认。HTTP 偏好参数使用 JSON 字符串，避免严格 msgpack 反序列化 enum 警告。

## 实际命令与输出

```powershell
.venv/Scripts/python scripts/b3-setup-local.py
# 新建独立本地业务/CP 库并迁移播种，配置写入 gitignored .env；无外部模型调用。
.venv/Scripts/python -m pytest backend/tests/e2e/test_b3_closed_loop.py -o addopts= -q
# 4 passed in 17.90s：实际 Graph/PG 重建后批准、付费账本重放、图关闭失败对账、本地会话授权。
.venv/Scripts/python -m pytest backend/tests/unit/test_graph_workflows.py -k repair_replaces_invalid -o addopts= -q
# 修复前 1 failed, 31 deselected；修复后 1 passed, 31 deselected in 0.67s。
.venv/Scripts/python -m pytest backend/tests/e2e/test_b3_closed_loop.py backend/tests/unit/test_graph_workflows.py -o addopts= -q
# 36 passed in 15.94s（包含 checkpoint 偏好字符串断言）。
.venv/Scripts/python -m pytest -o addopts= -q
# 最终代码完整重跑：395 passed in 176.84s；原始输出 var/b3-release-full.txt。
.venv/Scripts/python -m ruff check backend
# All checks passed!
.venv/Scripts/python -m mypy backend/app
# Success: no issues found in 70 source files
npm --prefix frontend run build
# tsc -b && vite build；29 modules transformed；built in 583ms。
./scripts/b3-verify-live.ps1
# B3 live verification pending: fill LLM_BASE_URL, LLM_MODEL_ID, LLM_API_KEY in D:\studyplan\.env
```

浏览器使用本机 bundled Playwright + Edge，执行 `node var/b3_browser.cjs`，真实 localhost HTTP、业务 PG、独立 checkpoint，模型明确为 Fake：

```text
PASS: real browser session -> generate -> edit/hash CAS -> approve -> reload; official links; mobile without overflow; no page errors
```

桌面及 390px 移动端截图已目视检查；测试服务已停止。截图位于 `var/b3-confirmed-desktop.png` / `var/b3-confirmed-mobile.png`。旧确认版本与新草案同时出现时，资源链接分别属于各自版本。

## 用户填写与下一验收

本机 `.env` 已设置 `LLM_PROVIDER=openai_compatible`、默认 `LLM_BASE_URL=https://api.openai.com/v1`。填写 `LLM_MODEL_ID` / `LLM_API_KEY`；其他服务商再改兼容 base URL。不要在聊天或提交中发送密钥。

`scripts/b3-verify-live.ps1` 使用真实配置，创建独立验证项目，经监听 socket 生成、批准、回读及发布重放，并检查 final checkpoint、run 和 provider attempt usage。没有凭据时停在预检，不发起付费调用。

## DeepSeek 真实验收

用户配置 `LLM_BASE_URL=https://api.deepseek.com`，模型 `deepseek-flash`；密钥仅保留本机 `.env`。第一次真实运行 `run_99f6dcb405df4001969cad23a3738e4e` 经两次有界修复后失败，5 个 paid attempt 均有已知成功响应，Run 明确 failed。

定位为提示词关系字段未定义：模型返回 `from_node_stable_key` / `to_node_stable_key`，契约校验要求 `from_stable_key` / `to_stable_key`。补全结构/修复提示词中的关系例子，先新增协议反例失败，再修复为通过。提示词版本升级 `b3-v2`，账本 fingerprint 随之更新；不放宽校验，不重写旧结果。

```powershell
.venv/Scripts/python -m pytest backend/tests/unit/test_b3_provider.py -k relation_contract -o addopts= -q
# 修复前 1 failed, 1 deselected in 0.59s
.venv/Scripts/python -m pytest backend/tests/unit/test_b3_provider.py -o addopts= -q
# 修复后 2 passed in 0.36s
./scripts/b3-verify-live.ps1
# verified: real_provider_HTTP_PG_StateGraph_checkpoint_publish_replay
# project_id: prj_6ed0e5199f024ff4b0704bd2b6098e25
# run_id: run_8802895fe92c467ca113002c7c93b812
# plan_id: pln_f79901a42180469993cae7b86e5907a5, revision: 1
# OutlineV1: succeeded, input 1013 / output 403
# KnowledgeStructureV1: succeeded, input 1298 / output 4660
# PracticeProposalV1: succeeded, input 1419 / output 3428
# KnowledgeStructureV1 repair: succeeded, input 2995 / output 7022
```

独立回查 PG：Run `succeeded / none` 指向上述 plan；4 个 attempt 均为 `b3-v2 / succeeded`，输入 6725 / 输出 15513 tokens。已发布 2 个阶段、3 个单元链接、2 个任务链接、7 个任务知识关联、2 个资料分配。checkpoint 为 `approve` 且 result_id 等于 plan_id，structure_errors / generation_errors 为空，repair_count=1。原始证据位于 `var/b3-deepseek-live-v2.txt`、`var/b3-deepseek-audit.txt`；首次失败记录保留在 `var/b3-deepseek-live.txt` 和业务 PG。

```powershell
.venv/Scripts/python -m pytest -o addopts= -q
# 396 passed in 180.42s；输出 var/b3-deepseek-full.txt
.venv/Scripts/python -m ruff check backend
# All checks passed!
.venv/Scripts/python -m mypy backend/app
# Success: no issues found in 70 source files
```

同一前端通过真实配置的服务端会话回读该 DeepSeek 正式计划（测试服务仅将会话学习空间指向验收项目，不替换 Provider）：

```text
PASS: actual DeepSeek-published plan read by frontend; 2 stages, 4 official links; desktop/mobile; no page errors; no new LLM dispatch
```

截图 `var/b3-real-model-desktop.png` / `var/b3-real-model-mobile.png` 已目视核验；测试 API 已停止。

用户另提出云端个人模型设置，限定 OpenAI 兼容 API。方案见 `docs/design-package/B3-user-model-settings-design.md`，尚未实现；它不是现有环境变量配置或完整云端发布的能力。
