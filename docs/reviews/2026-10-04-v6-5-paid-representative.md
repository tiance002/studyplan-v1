# v6.5 单一收费代表：PAID_REPRESENTATIVE_FAIL，STOP

用户现在新增能做什么：本轮没有产生可供学习的真实模型 Plan；现有副本体验保持。新增证据确认当前 DeepSeek 实际网络/响应契约可用，但 Agent5 Common Core 的首个 outline 在 4096 输出配置下被截断，当前收费生成代表未通过。执行已停止，不重发、不创建第二个 Run，不进入下一门禁。

本轮依据[用户批准的 v6.5 Goal](../implementation/STUDYPLAN_V6_5_PAID_REPRESENTATIVE_GOAL_2026-10-04.md)。归档与下载原文 SHA256 相同，以本机哈希核对为证；不是新增规划。业务源码、测试、provider 参数及正式 `.env` 未修改；本提交仅保存 Goal/审计/当前入口/唯一 progress。

## Baseline 与独立作用域

- 分支：`feat/n1-resource-discovery`，起始 HEAD：`a2c9435785687ce7d908fd5b13b9980d542a7bca`。
- tracked clean；已有 `.workbuddy/`、`design-preview/` 未操作。无 reset、master/develop 合并、push。
- AcceptanceId：`v65-agent5-synthetic-7a1040c10f15`，新唯一 ID，已绑定且终结，不能复用。
- 唯一 Run：`run_cecd033d2fed4a3190a77df32a3cb382`。
- 全新 owned 业务库：`studyplan_test_v65_business_b6a8ba0f`；全新独立 checkpoint 库：`studyplan_test_v65_checkpoint_6959d5a8`。
- 仅新库 forward 迁移到既有 `0024`、导入公共 reviewed Agent5、新合成账号和默认偏好；原产品库未连接、未读取、未写入。既有角色只读复用，未改全局角色。
- 合成目标严格为“零基础系统学习 Agent 应用开发，先做一个最小应用。”；未包含用户真实项目、Summary、Prompt、Outcome 或私人资料。
- 使用实际正式配置 provider `openai_compatible`、端点 `api.deepseek.com`、模型 `deepseek-flash`，真实返回 model 同名；key 存在但未打印/写入报告。
- 开发路由请求主协调 Sol 6.1/high；实际主会话 model/effort 解析 NOT OBSERVABLE。未创建子代理、未使用 Astra、未改全局设置或服务模式。

## 免费预检

17 项硬预检在首个收费派发前 PASS。证据为 `var/v65/free-preflight.json`、`preflight-complete.json`、`frozen-submission.json`。

| 检查 | 结果 | 实际值/依据 |
| --- | --- | --- |
| HEAD / tracked clean | PASS | 上述基线；禁止目录仅保留 untracked |
| 正式 `.env` 实际加载链 | PASS | 提取 `scripts/b3f1-dev.ps1` 的唯一 foreach 加载语句执行，再读取 `get_settings()`；正式 API 未启动 |
| runtime DNS / endpoint guard | PASS | `119.188.175.46`、`123.125.246.121`，公网；现有 guard 保留并在真实派发前再核对 |
| 实际传输 TLS / 证书 | PASS | 额外免费直接 TLS1.3，certifi 证书链和 hostname 校验；无 Authorization/模型 HTTP |
| 代理配置与旧网络证据完整性 | PASS | v6.4 实际 merge/generated/basic runtime hashes 未漂移 |
| cap / purpose / binding | PASS | runtime8192；outline/practice4096、structure/repair8192；真实部署 binding 未变 |
| 旧受控账本 | PASS | 精确23/50、23对 request/result；旧文件逐字节 hash 保持；受控账本未决0 |
| 唯一 ID / 全新 owned 两库 / synthetic | PASS | 上述独立 ID/库；普通注册与服务端 actor/project scope，精确 allowlist |
| publication / frozen manifest | PASS | Agent5 digest `eeff800d60e332772045d32db8ff143a254b24d72d32462b35e7620842be0565`；实际提交 manifest 与预检完全相等，6阶段 |
| 预算 | PASS | normal13、repair2、total15、输出上界94208；不扩大50总额度 |

传输说明：v6.4 TLS 证据经 HTTPX 默认 Windows 代理探测；本轮源码核对确认产品适配器实际新建 client 使用 `trust_env=False`。因此没有仅凭旧代理 TLS 证据代替产品真实路径，而是在收费前补做直接 TLS，成功后才派发；未注入代理 client、未改变安全策略。

预检首轮脚本把 `result-XX.json` 拼为 `request-XX-result.json`，脚本 FAIL，尚无 Run/收费；修正文件匹配后实际账本 PASS。最终只读汇总首轮用了不存在的 `plans` 表，检查 FAIL；改为现有 `plan_revisions` 后 PASS。两项均为 ignored 验收脚本错误，保留早期失败文件/执行输出，未重放收费 Run、未改变产品来掩盖结果。

## 唯一真实请求与计量

仅领取这个 Run 的一个 fenced claim，执行现有 Worker `_process`，有既有 lease heartbeat；未运行 daemon/轮询/第二 tick。provider 和 PgAttemptLLM/Graph 原路径保留；验收 wrapper 在派发前独占追加受控 quota intent，收响应后追加 receipt；核对 scope、允许 attempt catalog、参数、前序 PG/账本回执和预算。实际 HTTP post 只观测响应元数据，没有重试或替换响应。

| 项目 | 实际结果 |
| --- | --- |
| 请求数 / normal / repair | 1 / 1 / 0 |
| known failures / 本轮 unknown | 1 / 0 |
| global quota | 23/50 → 24/50；失败计量，不回退计数 |
| purpose | `planning.outline` / `OutlineV1` |
| HTTP / envelope | 200；choices/message/content 实际字段 PASS |
| finish reason / 字符数 | `length` / 12858 |
| requested max_tokens | 4096，thinking.disabled |
| 实际 provider input / output | 209998 / 4097 tokens |
| total_tokens | 214095 |
| cached / cache hit / cache miss | 0 / 0 / 209998 |
| 延迟 | 16222 ms（现有适配器实际记录） |
| provider adapter final | `provider_output_truncated`，failed，明确已知结果 |
| Run final / result_ref | failed / null |

实际 usage 输出4097比请求4096多1，照录 provider 字段，未把实际值改成4096、未声称服务严格遵守输出 cap。整体实际输出4097仍低于已冻结94208；本轮未修改任何预算。输入209998异常偏大是后续离线审查的具体线索，不能仅凭该数字宣称截断根因已完全定位，也不估算美元费用。

现有适配器看到 `finish_reason=length` 在 JSON/schema 成功处理前返回截断失败；既有 Graph 将模型失败终止，因此没有 local repair。不得人为把截断改成可局部修复结果来继续调用。没有 timeout、5xx、缺回执或 billing unknown；历史其他 scope 的 unknown1 原记录保留、不重派，不把本轮 unknown0 写成所有历史 unknown0。

## 门禁结果与持久化

| 门禁 | 状态 | 边界 |
| --- | --- | --- |
| 真实 DNS / guard / binding / TLS | PASS | 此次实际网络 |
| HTTP/envelope/usage 观测 | PASS | 首个 outline 响应字段可观察 |
| 成功可解析 outline | FAIL | 明确输出截断；不是成功长 JSON |
| 截断错误处理 | PASS | failed、无重发、无第二 Run |
| structure / practice / local repair | NOT RUN | 在首个请求失败后停止 |
| 真实输出后的知识/资料/章节/extensions/Starter/项目/Eval/RL保护 | NOT RUN | 无成功合并/草案；不能用冻结输入或 Fake历史替代 |
| 失败 Run / attempt / 双账本回执持久化 | PASS | app角色+actor/project只读精确核对，1Run、1failed attempt、unresolved0 |
| 成功草案/发布/PG Plan回读 | NOT RUN | `plan_drafts=0`、`plan_revisions=0` |
| synthetic explicit confirm | NOT RUN | 无草案可确认 |
| Chrome路线/资料/实践/Project Study/刷新/重登录 | NOT RUN | 没有生成结果，未启动新浏览器 API/前端 |
| 停止后新增收费请求 | PASS | 0，最终账本仍24 |
| 原 `.env` / 旧quota与历史Acceptance hashes | PASS | 最后只读审计逐字节核对保持 |

Fake/业务 unit/既有 PG/历史 Chrome：本批 NOT RUN，没有业务源码改动，不用既往 PASS 抵消当前真实失败。ignored harness 语法编译 PASS；有明确失败不扩大回归或重复收费验证。

## 证据、安全、风险与回滚

本机证据：`var/v65/free-preflight.json`、`preflight-complete.json`、`frozen-submission.json`、`run-report.json`、`execution-state.json`、`stop.json`、`final-audit.json`；受控账本 `.git/v2-paid-quota-20261001/request-24.json`、`result-24.json`；新 Acceptance journal/evidence 位于 `.git/b3f2-controlled-live/v65-agent5-synthetic-7a1040c10f15*.json`。旧记录不修改，新增请求失败也永久占用额度。凭据仅在限制本机用户/SYSTEM/Admin ACL 的 ignored `var/v65/private/`，报告不含 key/密码/DSN。

真实用户数据外发 NO；产品库写入 NO；RAG 修改 NO；GitHub/Tavily 新调用0；正式入口切换 NO；正式 Worker daemon NO；push/merge NO。新 owned 两库仅保留用于失败证据，没有清理/破坏历史数据。

本轮无业务/正式配置需回滚；停用一次性 harness 即已停止。若后续获准清理，只能删除精确两个新 owned 库，先核对名称/无活跃进程，不删除 quota、Acceptance 或 unknown 证据，不退回已消费次数；本轮未执行清理。审计文档可在后续纠正文档提交中更正，不能改写实际收费事实。

最终 `PAID_REPRESENTATIVE_FAIL`，STOP。网络READY保留，全产品 `STAGING_BLOCKED / NOT_READY`。当前新增具体 blocker 是真实 outline 截断，另外非空原用户历史/RAG契约/完整用户接受等既有门禁仍未完成。

唯一最小下一动作：另开有界**离线**审查，核对 outline 输入209998 tokens的组成与最小受保护上下文/输出职责，先提出可回滚修正；本次 Acceptance 不再允许任何收费重发。本报告不自行实施该下一门禁。
