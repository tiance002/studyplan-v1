# Planning V2 Item 1 — 最终定向复测（Case 7）

日期：2026-10-08（Asia/Shanghai）。最终：**ITEM1_SEMANTIC_REVIEW_REQUIRED / ITEM2_NOT_STARTED / STOP**。

唯一获准的新请求已尝试，返回 `provider_transport_unknown / ConnectError`，没有收到模型输出。Case 7 的语义结论为 **AMBIGUOUS**，来源、Validator、Profile 和 hash 真实验收均 **NOT RUN**。这不是已观察到新的语义错误，也不能证明修复后的 Prompt 已通过。已立即停止，不 retry/repair、不换身份补发。

## 1. 基线、授权与修改文件

- Start HEAD：`27d58eb1036dddc23c65cfc8730350fa402ccd3a`；branch：`feat/n1-resource-discovery`，符合用户指定基线。
- 开始 tracked tree 干净；既有 `.workbuddy/`、`design-preview/` 未操作、未提交。
- Final HEAD：本报告所属本地提交；精确 SHA 保存于最终答复及 ignored `var/planning-v2-item1-case7-final-20261008/final-audit.json`，不自嵌自身提交 SHA。
- 唯一新增 tracked 文件：本报告 `docs/planning-v2/ITEM1_CASE7_FINAL_SEMANTIC_RETEST.md`。生产代码、Prompt、Schema、Validator、ID/hash、架构合同、progress、frontend、数据库、migration 均未改。不 push、merge、deploy。
- 权威：[Architecture Contract](PLANNING_V2_ARCHITECTURE_CONTRACT.md)；修复：[Project Context Reference Fix](ITEM1_PROJECT_CONTEXT_REFERENCE_FIX.md)；历史：[首轮烟测](ITEM1_REAL_SEMANTIC_SMOKE.md)、[五案真实复测](ITEM1_REAL_SEMANTIC_RETEST.md)。原失败和 unknown 记录保持。
- 用户本轮只授权最多 1 次新的真实产品请求，仅 Case 7；该授权已使用 1 次，剩余 0。累计 cap280 不变，旧五次授权没有复用。

## 2. Provider / 账户 / 账本预检

- 当前 Provider=`openai_compatible`，官方 endpoint=`https://api.deepseek.com`，请求模型=`deepseek-flash`。本次无响应模型字段，实际响应模型 **未知**，不把配置模型冒充 Provider 已自报模型。
- 参数保持原有 `max_tokens=4096`、`thinking.type=disabled`、timeout120 秒；既有预算及 endpoint public-DNS/origin guard 有效，没有换模型/Provider或新增凭据。
- 免费账户余额 GET 返回 HTTP200、`is_available=true`，可用余额 1.96 CNY；这确认预检时账户接口可用，不能保证随后的模型连接成功。认证头/API Key 未进入日志，没有充值。
- 调用前账本 182/280，历史 unknown 只有177。新增 append-only 授权以及 request/result183；结束 **183/280、余97、unknown=[177,183]**。unknown183 仍占用该笔授权，不以未知结果退回次数。原账本375文件全部 hash 保持，unknown177未覆盖、删除或重派。
- 调用前费用估算复用同日已核对的[DeepSeek官方价快照](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：CNY/百万 tokens，闲时 hit0.02/miss1/output4，高峰翻倍。按估计6000输入及既有4096输出cap、高峰价估计一案 **0.044768 CNY**，低于余额；这是调用前估计，非精确 tokenizer、账单或新增产品预算。
- 独立 ignored 入口由上轮已使用的单次记录入口有界派生，仅允许 labels=[7]、scope_limit=1；HTTPTransport retries=0、禁止redirect，派发前 exclusive 写入 request183。STOP标记和已有输入/账本阻止再次派发。
- 实际链路：`GoalRequirementAnalyzer → RecordingPort（只记录）→ build_llm / OpenAICompatibleLLM → DeepSeek HTTP 尝试`。没有 Fake 内容或旧 Graph，没有 Worker/业务持久化；run_id只是验收请求身份，不是新建业务 Planning Run。

## 3. Case 7 输入与新身份

与上一轮 Case 7 规范化 GoalSpec 完全相等，以下文本全部为合成数据，未发送真实私有项目资料。

```json
{
  "target": "我想学习 Agent 的结构化输出和受限工具调用，并将它应用到我现有的小型待办事项管理程序中。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": [],
  "project_context": "我已经有一个本地待办事项管理 CLI，使用 JSON 文件保存任务，希望直接在现有程序上增加 Agent 能力，而不是重新创建演示项目。"
}
```

- Acceptance：`planning-v2-item1-case7-final-synthetic-cfd3179be093`
- run_id：`planning-v2-item1-case7-final-synthetic-cfd3179be093:case-7`
- attempt_id：`planning-v2-item1-case7-final-synthetic-cfd3179be093:case-7:goal_requirements:1`
- 账本编号：183；新身份与历史 Case7、unknown177 均不同。
- 实际请求体保存在 ignored `case-7.request.json`，包括修复后的专用 Prompt 和上述输入；SHA256：`e77c5b549362640d0b8f1f4b270596e407606654fc8dd57ddf4be3036e283ed3`。认证头不在该文件。

## 4. 实际结果与计量

北京时间2026-10-08 14:13:35开始；唯一入口耗时 **5448 ms**，Provider计时 **5349 ms**。没有 HTTP response，原始响应正文不存在；以下是实际 Provider/Analyzer 返回的失败对象，两者完全一致：

```json
{
  "error_class": "provider_transport_unknown",
  "message": "Provider outcome unknown",
  "retryable": false,
  "dispatch_unknown": true,
  "details": {
    "requested_model": "deepseek-flash",
    "max_tokens": 4096,
    "thinking": {
      "type": "disabled"
    },
    "purpose": "planning.goal_requirement_analysis",
    "schema": "GoalRequirementProfileV1",
    "finish_reason": null,
    "content_chars": null,
    "reasoning_chars": null,
    "transport_exception_type": "ConnectError"
  },
  "input_tokens": null,
  "output_tokens": null,
  "latency_ms": 5349
}
```

| 项目 | 结果 |
|---|---|
| 请求尝试 / 明确响应 | 1 / 0 |
| Provider类型 | LLMFailure |
| HTTP状态 / finishReason | 未知 / 未知 |
| input / output tokens | 未知 / 未知，不能记0 |
| cache hit / miss tokens | 未知 / 未知 |
| 实际费用 / 基于usage的费用估算 | 未知 / 无法计算 |
| 原始模型content / 最终Profile | 未收到 / 无 |
| 合法project_context输出 / 其他refs | NOT RUN / NOT RUN |
| Schema / Validator / Profile ID/hash | NOT RUN / NOT RUN / NOT RUN |
| unknown传播及不重试 | PASS：dispatch_unknown=true，retryable=false，一次调用后STOP |

ConnectError只能证明客户端记录了连接异常，不能据此断言远端没有接收、没有执行或不会计费。没有进一步网络诊断、余额复查、模型重试或 repair。历史修改副本没有用来填补本次输出；先前离线 ID/hash PASS 仍只属于其对应 fixture。

## 5. 独立语义审查与历史结果复用

独立开发审查代理对照新输入、已构造请求、实际失败对象、STOP和上轮标准；不是被测DeepSeek自评。审查请求 `gpt-6.1-sol / medium`，主协调请求 `gpt-6.1-sol / high`；实际解析均 **NOT OBSERVABLE**。审查证据保存为 ignored `independent-review.md`。

独立结论：**Case7 AMBIGUOUS**。没有真实模型内容，无法判断规范 `project_context` 是否生成、项目背景是否完整保留、是否误扩展专项/数据库/Web/云、是否误认为已会全部Agent能力、是否要求重建项目。程序合同相关项为 **NOT RUN**，不能由请求Prompt包含正确指导或历史修订副本代替。失败传播和单次尝试边界 **PASS**。

历史已通过真实案例仅复用，不重新请求：

| Case | 有效证据 | 历史程序 / 独立语义 | 本轮重测 |
|---|---|---|---|
| 1 Python已有基础 | 首轮烟测 | PASS / PASS | NOT RUN |
| 2 只读CodeReview/interview | hard_constraints修复后的五案复测 | PASS / PASS | NOT RUN |
| 4 PR分析与审查依据 | 五案复测 | PASS / PASS | NOT RUN |
| 5 离线与云端实时冲突 | 五案复测 | PASS / PASS | NOT RUN |
| 6 窄目标/免费教程 | 五案复测 | PASS / PASS | NOT RUN |
| 7 已有项目背景 | 本次唯一新请求 | NOT RUN / AMBIGUOUS | 尝试1次，unknown |

历史 Case7 的非法引用 FAIL仍保留；本次unknown没有替换该历史结论。当前专项仍缺一份修复后的明确真实响应，不能汇总标记 `ITEM1_REAL_SEMANTIC_ACCEPTED`。按用户本轮最终状态的两选一规则，标记 **ITEM1_SEMANTIC_REVIEW_REQUIRED**；该整体状态不把 unknown 误称为已发现语义FAIL。

## 6. 必要边界与结束核对

- 必要边界测试 **9 PASS**，XML errors/failures/skipped均0：规范引用指导/严格拒绝/合法通过5，project_context公共generate关闭1，真实API层fail-closed模拟1，Provider unknown不泄露/不重试1，Analyzer unknown原样传播1。
- 命令使用 `.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit`，只选上述节点；完整参数及XML保存在 ignored `boundary.log/xml`。全量回归/collection **NOT RUN**，没有重复33项或198项回归。
- 802个既有tracked文件及配置hash保持，412个旧账本/上轮原始证据文件hash保持，架构合同/Prompt/Schema/Validator/hash/占位页无改动；新增migration0。
- public `/plans/generate`仍在身份/项目scope后503；依赖spy证明拒绝发生在Run/Job/Provider/Plan访问前。未恢复旧Planning，未启动Worker。
- 本轮产品搜索0、Reader0、其他产品模型0；没有数据库写入。新业务Run0、Job0、Draft/Plan mutation0依据独立入口不接DB和fail-closed spy，**真实PG行计数 NOT RUN**，不冒充数据库计数。
- 真实PG/checkpoint、浏览器、前端build、大规模语义质量/稳定性、不同采样重复试验 **NOT RUN**。精确账单、Token及新模型响应均不可得。没有证明Prompt修订的真实效果，也没有因unknown自动修改修复。
- 完整证据：ignored `var/planning-v2-item1-case7-final-20261008/`，含preflight、输入/新身份、实际请求、Provider失败、Analyzer失败、STOP、独立审查、9项边界和本轮audit。凭据/认证信息不入证据。恢复检查点：`var/codex-goals/planning-v2-item1-case7-final.json`。
- 本轮一次授权已用尽；unknown177与unknown183均不可重派。不申请或启动补发，不进入Item2；后续任何工作需新的明确指令。

**ITEM1_SEMANTIC_REVIEW_REQUIRED**

**ITEM2_NOT_STARTED**

**STOP**
