# Planning V2 Token 与现金门禁最小闭包

任务：`PLANNING_V2_TOKEN_CASH_GATE_CLOSURE_V1`，2026-10-09。

**结论：`BLOCKED_WITH_EXACT_MISSING_AUTHORITY`。** 官方 V4.1 Tokenizer/Prompt Encoding 路径已定位；当前读到的资料尚不能证明本地计数是 API 计费输入的保守上界。官方上下文长度限制是另一条可用的宽上界候选，但尚缺覆盖超限/拒绝请求计费范围的权威说明。按本轮 T0 条件停止 T1/T2 现金代码实施，不把估算、样例或内部费用预约伪装成现金保护。独立审查及最小缺口见下文。

## 1. 基线、范围与复用

- Start/source HEAD：`2edc467a236df3e0c73cc95f46a5226c1b212f93`；实际分支 `feat/n1-resource-discovery`，与参考一致。tracked tree 开始 clean；预存 `.workbuddy/`、`design-preview/` 未访问/修改。
- 复用[上一轮派发门禁](PLANNING_V2_REAL_ACCEPTANCE_DISPATCH_GATE.md)和[产品验收准备](PLANNING_V2_PRODUCT_ACCEPTANCE_PREP.md)的 owned 预算、Worker/恢复、Semantic、历史保护与 React 证据；不重跑 Item1–9、Backend/PG/浏览器矩阵。[冻结架构](PLANNING_V2_ARCHITECTURE_CONTRACT.md)、Scenario A/B/C、Policy、审核资格与业务语义不变。
- 新 acceptance 的内部一期候选预算仍是：7 模型（含 4 Reader）、4 搜索、4 body 操作/8 HTTP、16384 output tokens、19 durable 请求、8 candidates、262144 body bytes、144000 **内部** cost_micros。既有 owned 工厂能装配；不改 default、旧 root 或正式配置。本轮没有创建或派发新 acceptance。
- 实际本地账本与上一轮集合 hash 相同：模型 requests/results 各183、cap 证据280、unknown2（177/183）；搜索各6、cap 证据1000。97/994 只是算术余量，不是授权。原 `.env` hash 与历史证据保持，未访问账户或正式数据库。
- tracked 修改只有本报告与 `docs/implementation/progress.md`；本轮 ignored 证据在 `var/planning-v2-token-cash-closure-20261009/`。本地 checkpoint 的最终 SHA 由该目录 `delivery-receipt.json` 与 annotated tag `checkpoint-planning-v2-token-cash-20261009` 记录，不用报告自身构造循环 hash。
- 独审请求 `gpt-6.1-sol/xhigh`，实际模型/档位解析 `NOT OBSERVABLE`。主会话没有切换模型的工具，不宣称已切换，不改全局配置。

## 2. T0 官方计量证据

### 2.1 官方路径与实际读取情况

| 资料 | 本轮证据及限度 |
|---|---|
| [官方 Tokenizer 指导](https://github.com/deepseek-ai/deepseek-recipe/blob/main/docs/tokenizer.md) | 已读；要求附加匹配模型的 tokenizer，示例以 `DeepseekV41Encoding` 渲染对话，再关闭自动添加 special tokens 编码。关闭自动添加不等于不识别文本中的 AddedToken 字面量。moving main 未冻结 SHA；未执行示例。 |
| [官方 v41 资产目录](https://github.com/deepseek-ai/deepseek-recipe/tree/main/static/tokenizers/v41) | 页面读取 DisabledError。指导已说明目录存在；不能把访问失败说成资产不存在。tokenizer.json 未下载、未验证版本/hash，未安装依赖。 |
| [Issue #5](https://github.com/deepseek-ai/deepseek-recipe/issues/5) | 已读；第三方 reporter 的公开反例，非官方计费算法承诺。读到的页面为 open，未见维护者解决说明；本轮不运行其 API 复现。 |
| [官方 Token 用量说明](https://api-docs.deepseek.com/quick_start/token_usage/) | 直接打开两次超时；随后从该确切官方页面的搜索索引读到文本。字符转换是近似量，实际每次用量取返回 usage；离线 ZIP 未下载。索引读取不冒充已验证的版本化本地计量实现。 |

Issue 报告的环境是 recipe0.1.1、检查 commit `8cadfede7063c896b944e7bae05daa3549ae97ea`、v41、`deepseek-flash`、单 user 消息、thinking disabled。包含模板的 local/API 计数：空文本4/4，`<｜User｜>`5/9，`<｜begin▁of▁sentence｜>`5/16。`｜DSML｜`连续8次时，recipe12、API21、移除 AddedToken 后的 ordinary-BPE 加模板36。后者在这个样本大于 API，不证明对所有允许文本恒大于 API。[反例来源](https://github.com/deepseek-ai/deepseek-recipe/issues/5)

这些观察足以反对“无条件采用本地示例计数作为 API 上界”，但不证明当前 main 仍有同样错误，也不能把原单 user 的数字移植为本项目 system/user JSON 的真实 usage。官方组织托管 issue 不使 reporter 成为官方计费权威。

### 2.2 对实际输入的适用性

`OpenAICompatibleLLM.generate_structured` 实际发送一个 system 字符串和一个 `json.dumps(message, ensure_ascii=False)` user 字符串；message 含 purpose/schema/field_shape/context。官方 Flash 的实际 options 为 non-thinking、json_object，基础三 purpose 输出各4096、Reader1024。源码在构造 body、endpoint guard 后进行 HTTP POST；没有派发前可信输入 Token 或币种门禁。

一次纯离线序列化核查确认上述三个字面量经过相同 JSON 序列化表达及 wire JSON roundtrip 后仍保留。**PASS 仅表示语法可达**，不表示冻结 Scenario A 实际含这些字符串，也不证明 API 的 Token 数；未调用 Provider、Tokenizer 或 HTTP。后续模型输出及 Reader 外部文本不能仅凭首个合成目标未含特殊字面量就宣称所有请求不存在该问题。没有添加关键词黑名单、改写输入或放宽 Schema。

精确计数需要证明 local count 与服务计数相等；本轮只需要更弱的 `billable_input(actual_request) <= U(actual_request)`。现有材料没有建立这个不等式：固定比例/百分比、字符除4、未核查的 byte/token 比、简单 `max(recipe, ordinary_BPE)` 或几个对照样本均不能代替证明。需要明确消息渲染/特殊字面量/规范化规则，以及本地算法或其保守版本与当前服务计费范围的对应关系；不要求建设通用 tokenizer 平台。

### 2.3 公平评估上下文长度替代路径

官方 Chat Completions 文档明确输入与生成长度受模型 context length 限制，`max_tokens` 是生成上限；因此**被接收的推理输入**存在 context ceiling 上界候选。这条路径不依赖本地精确分词，不应因 Issue 反例就一并否定。[官方 API 说明](https://api-docs.deepseek.com/api/create-chat-completion/)

此次精确 Token 用量查询附带返回了官方 pricing 页面索引：Flash 的模型对应关系及 context length1M；这些是公开索引材料，不是实时价目/账号预检或 Owner 现金报价。[官方模型资料](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)

尚缺有限、明确的计费桥梁：对**超限或拒绝请求**，是否保证不收输入费用，或者其所有计费输入也受同一 context ceiling 限制。当前资料仅明确推理上下文限制，没有证明全部派发结果的账单上限。unknown 本身不是反证：若服务端已接收，仍可受相同上限保护；但本地无法判明结果时，所保留的预约必须涵盖所有可能收费结果。还需冻结 ceiling 的数值含义、当前模型/价格版本及失配即拒绝条件。

这是可进一步核实的最小替代路线，**不是要求猜测无限的服务端行为**。若获得上述收费范围说明，可以用每请求完整 context ceiling 预约作为较宽的保护，代价是现金授权需求较高；不需要先解决精确分词。当前不能将其直接写成已证明的所有派发计费上界，也不自动批准 CNY0.50 或更高金额。

## 3. 三项阻塞与 T1/T2 决策

| 阻塞 | 本轮状态 | 精确原因与最小解除条件 |
|---|---|---|
| INPUT_BOUND_UNPROVEN | 未解决 | 本地计量路径缺与 API 保守不等式的证明；context ceiling 路径缺超限/拒绝请求收费范围及冻结数值说明。二者任选一条可靠证明即可，不要求两条都完成。 |
| CASH_DISPATCH_GUARD_MISSING | 未解决；T1 NOT RUN | T0 前提未成立，按授权停止代码实施。现有 `PgV2Calls` / `ResearchBudget` 的内部 cost_micros 无币种、价格或 input 上界绑定，不能解释为现金。 |
| COST_UNCERTAIN_CONTINUE | 未解决；T2 现金实现 NOT RUN | 已有成功且 usage=None 的 receipt 能在内部预算内继续；没有可信现金预约，所以仍不具备受控真实验收的现金保证。不是要求所有 usage=None 一律停止，正确条件如下。 |

本轮用户的 T2 条件优先于历史报告中概括性的“费用不确定一律停机”表述；旧报告不改写：

1. 已知成功、usage 可信：可按结算规则处理；usage 存在也不能凭空释放未被覆盖的现金费用。
2. 已知成功、usage/cost 缺失：**如已有可信最坏现金预约，保留整笔预约**；下一身份仅在原 root 的累计最坏金额仍在 Owner 授权 cap 内时允许。缺 usage 本身不是必然业务失败。
3. 无法证明最坏现金金额：不能继续真实派发。unknown 继续 reconciliation 锁定，不退款、不重派、不换身份绕过。取消、迟到、Worker 恢复保留原 fence/receipt 保护。

独审实际核对 `PgV2Calls.family_reservations`、`call` 与 `_generate_structured`：内部预约先提交再 invoke；累计保留原 worst 或更大观测值；pending/unknown 阻同 family 续派。机械结构可复用，但目前没有真正的现金 quote/reservation。不能为了显示“修好了”先往旧 Receipt 补字段或增加无权威的金额列。无 migration、无默认现金 cap、无历史数据修改。

未来证明成立后的小 owned-only 实施应冻结：完整序列化 body 的 hash/计量绑定与实际 options、输入上界依据、模型/来源版本、币种、峰值 cache-miss input 价和 output 价、明确整数金额单位、Run/root及授权 cap；沿现有 fingerprint 隐私契约，不持久化 Reader正文或认证头。向上取整 `U_input * peak_input_price + actual_output_cap * peak_output_price`，在 durable dispatch 前同锁事务预约，恢复/取消/unknown不返还无依据的金额。Tavily费用另列，内部 cost_micros 语义不变。本轮没有实现或声称通过这条调用链。

## 4. T3 与独立审查

| 验证 | 状态 | 范围 |
|---|---|---|
| 基线、分支与账本/.env hash 对照 | PASS | 对照上一轮 baseline；183/280/unknown2与search6只复用当前未变账本，不查账户 |
| JSON 特殊字面量可达性 | PASS | 新离线检查；无分词/费用/API真实性声明 |
| 旧 owned 预约、output/total/internal-cost超限0invoke、unknown/取消/恢复保护 | PASS（复用） | 上轮 G4实际 owned PG证据，源码hash不变；本轮未重跑 |
| T0全派发计费上界权威证明评审 | FAIL | 已评审材料，但缺有限计费范围权威；不是执行Tokenizer得到错误计数 |
| Tokenizer执行 / 新现金门禁验收 | NOT RUN | 未执行Tokenizer或真实计费实验，未实施cash |
| T3-1 新可信token/现金额度超限时外部invoke0 | NOT RUN | 不拿本轮禁用外部调用得到的0冒充现金guard拒绝 |
| T3-2 usage=None保留现金预约、下一身份累计拒绝 | NOT RUN | 旧证据只有内部预约，不是现金 |
| T3-3 新现金链的unknown/取消/Worker恢复 | NOT RUN | 复用原内部保护，尚无新现金持久化路径可测 |
| 本报告本地链接、历史progress字节保留、源码/配置/账本保护及git diff --check | PASS | 定向文档和hash核查，原始证据见ignored目录 |
| Backend全量、真实PG、浏览器、Ruff生产代码回归 | NOT RUN | 无生产代码变化；按本轮范围不重跑 |

独立代理在独立上下文读取实际 Provider、PgV2Calls、ResearchBudget 及共享权威材料，主动评估上下文 ceiling 替代路线；owned 装配仅复用旧证据，未独立重读工厂。没有直接采用实施者的 PASS 结论，没有新网络或 PG 调用。**报告结论独审 PASS 仅表示阻断结论和条件语义获得复核；T0权威门禁为FAIL，现金实现与真实产品验收为NOT RUN。** 独审要求已修正未来冻结表述，明确持久化 hash/计量绑定而非 Reader正文/认证头，并区分未闭合证明与未执行测试。复核记录为 `var/planning-v2-token-cash-closure-20261009/independent-review.md/json`；所有本轮 ignored evidence 不含凭据、认证头或教材全文。

## 5. 精确下一步与停止边界

两条最小选择，尚未执行：

- **context ceiling 路线：** 获取官方关于 text-only Chat Completions 超限/拒绝请求的收费范围说明，核实完整计费输入受冻结 ceiling 保护或超限不收费；冻结准确数值、服务模型对应和计费币种/价格。若成立，即可评审 owned-only宽上界现金预约；Owner另行决定可接受金额，不用资产下载或精确计数来替代该缺口。
- **本地上界路线：** Owner另行授权获取版本固定的 v41 tokenizer资产/编码实现及 hash，并取得模型对应、服务端 literal/framing/规范化说明或官方保守界保证，完成限定输入的不等式证明。**仅下载资产仍不足以解除 Issue 暴露的 API 对应关系缺口**；少量收费对照只能校准，不能证明全域上界。

账号元数据 GET 不解决 T0，也不证明现金派发保护；本轮不需要执行它。可信上界与 owned现金代码完成后，才另行申请账号余额、实际模型/价格、币种和 Tavily额度的外部 preflight。本轮没有冻结真实报价、实时价格、人民币授权或转换汇率；不引用旧余额或索引价作为当前现金硬限。

真实 DeepSeek/Tavily/教材正文/Reader请求均0；凭据账户preflight0；新 Tokenizer/ZIP资产下载0。仅执行明确 T0 所需公开资料读取及一次精确官方页面检索，**不写成“全部网络0”**，也不等同产品资料搜索。正式数据库/Run/Receipt/历史unknown无修改；public generate保持关闭；无push/merge/deploy。

当前真实产品验收**不能进入 READY_FOR_EXTERNAL_PREFLIGHT**；先补上述任一有限权威条件并完成现金门禁验证。本轮交付到此 STOP，不自动继续资产下载、账户查询、收费模型或正式发布。

`BLOCKED_WITH_EXACT_MISSING_AUTHORITY`

`STOP`
