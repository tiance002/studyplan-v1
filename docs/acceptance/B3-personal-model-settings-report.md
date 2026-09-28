# B3 个人模型设置验收（2026-09-28）

范围：只支持 OpenAI 兼容 `/chat/completions`。用户在界面填写 Base URL、模型名称、API Key；服务器按已认证 actor 隔离，用独立 Fernet 主密钥加密 API Key。GET 只返回公开元数据和 `has_api_key`，PUT 使用 version CAS，DELETE 撤销历史密钥但保留运行修订绑定。部署默认模型在没有个人配置时明确显示，不会静默回退 Fake。

迁移 `0007` 在本地专用 B3 业务库执行 `alembic upgrade head`，输出 `Running upgrade 0006 -> 0007`。加密主密钥只存本机忽略的 `.env`，未打印、未提交。管理员批准的 HTTPS 主机默认 `api.openai.com` 与 `api.deepseek.com`；保存和派发前均校验 URL、公开 DNS 地址，生产出口网络仍必须阻断私网与 metadata 以覆盖 DNS 变化窗口。

真实 PG/HTTP 测试覆盖：加密后无明文、两个 actor 隔离、双窗口 CAS、旧绑定固定模型、清除后不能复用旧密钥、无部署默认凭据时个人模型仍能选择、并发不同 actor 不串 provider、恶意 URL 和无 DNS 拒绝、错误响应不回显异常格式的 Key、实际 HTTP + PG + StateGraph 使用个人模型。旧部署默认模型账本指纹可重放，绝不再次派发。服务端请求路径不接受客户端自报 actor。清除会撤销历史密钥，但保留配置版本和 Run 绑定供审计与结果回读。

浏览器（Edge/Playwright）执行本地会话 → 保存设置 → 刷新回读 → 清除：GET、输入框、localStorage 均不含 Key，390px 无横向溢出、无脚本异常；结果：

```text
PASS: settings save/reload/clear; secret absent from GET/input/localStorage; current deployment fallback explicit; desktop/mobile; no LLM dispatch
```

截图 `var/model-settings-desktop.png`、`var/model-settings-mobile.png` 已目视核验。该浏览器流程没有发起付费模型调用。

真实个人设置链路：

```powershell
./scripts/b3-verify-live.ps1 --personal
# verified: real_provider_HTTP_PG_StateGraph_checkpoint_publish_replay
# project: prj_d9a09c9e3cf74779815cc545016dba4e
# run: run_92afe02d089248549dd9732369c4abe5
# plan: pln_045fd4ae602344ccbbce938196b45d19, revision 1
# model_source: personal, settings_version: 1
# deepseek-flash OutlineV1: 1013 input / 1207 output tokens
# KnowledgeStructureV1: 1284 / 5147
# PracticeProposalV1: 1387 / 2491
```

独立 PG 回查：Run `succeeded` 指向上述 plan，3 个成功 attempt 共 3684 输入、8845 输出 tokens，`ai_run_model_settings` 绑定修订 1。验收专用 actor 的密钥随后撤销，绑定和发布记录保留。首次脚本包装层没有转发 `--personal`，因此留下另一条部署默认模型成功记录；包装层已修正，实际个人链路通过。原始输出 `var/b3-personal-live-actual.txt` 和 `var/b3-personal-live.txt`。

最终代码验证：

```powershell
.venv/Scripts/python -m pytest -o addopts= -q
# 406 passed in 191.94s；输出 var/model-settings-final-release.txt
.venv/Scripts/python -m ruff check backend
# All checks passed!
.venv/Scripts/python -m mypy backend/app
# Success: no issues found in 76 source files
npm --prefix frontend run build
# 30 modules transformed；built in 772ms
```

运行仍是同步 StateGraph/PG Checkpointer，不宣称生产异步队列。正式云端多用户认证尚未实现，本地进程内会话只供开发；公开部署需要可信登录/会话服务及网络出口限制，不能直接公开本地会话令牌。Anthropic `/messages` 不在本次范围。
