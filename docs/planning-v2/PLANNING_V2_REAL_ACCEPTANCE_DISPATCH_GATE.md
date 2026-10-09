# Planning V2 真实产品验收执行门禁

任务：`PLANNING_V2_REAL_ACCEPTANCE_DISPATCH_GATE_V1`，2026-10-09。

**结论：BLOCKED。** 新 acceptance 的内部预算可通过既有 owned 装配合法冻结；不需要新增两模型暂停平台。但当前没有可信的派发前输入 Token 上界、绑定人民币价格的累计现金预约/拒绝机制，以及费用不可确定时禁止下一身份派发的保护。本轮不把内部费用或 Mock 数字当现金证明，不开始真实 preflight 或收费验收。

## 1. G0 基线及复用

- 实际 Start/source HEAD：`d19f0b7a51e4b48bcd2f5b4073edf675d8016b91`，分支 `feat/n1-resource-discovery`，与参考一致。tracked tree clean；预存 `.workbuddy/`、`design-preview/` 未访问或修改。
- 直接复用 [前置收口报告](PLANNING_V2_PRODUCT_ACCEPTANCE_PREP.md)、C0–U3、成功 Semantic owned PG/HTTP/Edge 及原 unknown/CAS/fence/预算/历史保护证据，不重跑 Item1–9 或完整 Backend/PG/UI 矩阵。[架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)与 Scenario A/B/C 原输入、教材资格、Policy 不改。
- 当前 `.env` hash、模型/搜索账本集合 hash 与上一轮相同。实际本机模型 requests/results各183，累计cap证据280，unknown2（177/183）；搜索requests/results各6。剩余97/994仅算术，**本轮外部授权0**；账户余额、实时价格和凭据有效性 NOT RUN。
- 本轮修改仅本报告与 progress；owned 测试脚本/JSON/原始输出存 ignored `var/planning-v2-dispatch-gate-20261009/`，未修改生产代码、正式配置、默认预算、ledger算法、正式数据库、旧 Run/Receipt 或 migration。
- 路由：有界 owned 检查请求Sol6.1 medium；输入、费用、来源与执行逻辑独审请求Sol6.1 xhigh；实际解析 `NOT OBSERVABLE`，不改全局模型配置。主协调工具不提供模型切换，不宣称已切换。

## 2. G1 合法一期 owned 预算

`OwnedV2PlanningRuntimeFactory` 已支持服务器依赖传入 `ResearchBudget`，只接受 loopback、`studyplan_test_` 前缀且业务/checkpoint分离的数据库。HTTP请求不能提供budget或model。`build_submission` 调用既有 `build_v2_manifest`，预算纳入manifest hash；`PgV2Calls._lock` 对照持久化唯一submission，`budget_family`及预约锁沿原root累计。

仅为**全新 acceptance/root**冻结以下候选预算是合法已有能力，不必改全局default：

| 指标 | 一期冻结值 | 单位/作用 |
|---|---:|---|
| max_searches | 4 | GitHub/Web共享搜索上限 |
| max_reader_requests | 4 | Reader模型请求，包含在模型7次内 |
| max_candidates | 8 | 候选准入，不自动授予8次正文/Reader |
| max_body_bytes | 262144 | 4次永久65536-byte最坏预约 |
| max_output_tokens | 16384 | 当前3基础模型×4096 + 4Reader×1024 |
| max_total_requests | 19 | 7模型 + 4搜索 + 8正文HTTP |
| max_cost_micros | 144000 | 7模型×20000 + 4搜索×1000；内部单位，不是人民币 |
| search_cost_micros / reader_cost_micros | 1000 / 20000 | 沿现有预约算法，不重新定义币种 |

三个上限层次必须分开：

1. 现有manifest允许：Goal/Capability/Curriculum各8192、Reader1024。
2. 当前真实Provider有效 `request_options`：前三者各4096、Reader1024，由practice4096/deployment8192/model cap取min得到，thinking disabled。
3. 新一期ResearchBudget累计：output16384、total19、内部cost144000。

真实执行前必须冻结并复核同一binding与实际options；允许上限8192不是批准将4096升为8192。若参数变化，本期16384算式失效，不能自动扩大预算。本轮Mock实际serializer复现了上述有效参数；没有真正调用官方API。

literal default output4096/total16/cost100000可预约首个4096 Goal，但下一4096 Capability累计超额；完整最坏批次的19/144000也超出16/100000。owned依赖注入解决新root的内部预算装配问题，不“修正”默认或正式装配。

**不能复用/改写上一轮P1 root。** 它已预约output22528、内部cost162000，超过新一期16384/144000；不能替换旧manifest、归零或借新身份绕过同家族。后续真实一期须新专用用户/项目/acceptance/root，不派发历史177/183。

计数成立还需冻结外部scope：无新领域来源验证、无ProjectCase搜索端口、无自动澄清续接、无第二场景/Semantic再生成。需要这些分支时停止；不能因为total尚有余量就认为该purpose获授权。required outcomes和教材资格仍保留，必要资料不足则incomplete。

## 3. G2 输入 Token 与现金门禁：BLOCKED

### 3.1 已证明的接缝

`OpenAICompatibleLLM.generate_structured` 实际发送的messages由专用system prompt和user JSON组成；user含purpose/schema/field_shape/context。构造body后运行endpoint guard，然后一次HTTP POST。输出有max_tokens；输入未做可信Token计数/上界核对。

`provider-seam-check.py` 使用真实序列化代码和 `httpx.MockTransport`，Scenario A输入未经重写：system/user分别4150/1365 UTF-8 bytes，仅作载荷观察，**不是Token上界**。Mock响应无usage仍返回 `LLMResult(input_tokens=None, output_tokens=None, cost_micros=None)`。这不是实际官方Token/价格验收，也不是cash门禁PASS。

`ResearchBudget.METRICS` 只有searches/candidates/body_bytes/reader_requests/output_tokens/total_requests/cost_micros，无input-token、币种、价格版本、tokenizer或framing绑定。`PgV2Calls._generate_structured`只预约output和内部cost；Provider在响应后读取usage，实际cash一直返回None。既有endpoint/隐私/Schema保护不能替代财务保护。

### 3.2 最小阻塞

| 阻塞 | 具体缺失 | 影响/最小解除条件 |
|---|---|---|
| INPUT_BOUND_UNPROVEN | 未发现绑定当前`api.deepseek.com/deepseek-flash`的可信tokenizer/vocab及chat framing上界；本机tokenizers/transformers/tiktoken/sentencepiece未安装，已有Whisper tokenizer不适用 | 无法从完整actual wire messages证明输入账单tokens上界。需要官方可核实的模型/encoder/framing对应关系或官方可信计量/总上下文上界及适用条款；不是安装通用tokenizer就解决 |
| CASH_DISPATCH_GUARD_MISSING | 无绑定货币、价格权威、现金总cap的dispatch前预约/累计拒绝路径 | 有限output/请求数无法约束当前无界input的现金。需先证明Token上界，才评审小owned-only派发适配：核同一最终body/options、价格/币种、每次最坏费用、持久保留/恢复和预算拒绝 |
| COST_UNCERTAIN_CONTINUE | 成功receipt缺usage/costNone保留内部预约，但不自动阻下一身份 | 同新owned Run反例实际允许第二Mock调用，不能宣称“费用不确定停止”已实现。适配须明确未知、缺usage、取消、迟到结果的现金预约与阻断，不释放不可信预约 |

本地缺少当前模型所需证据，不能凭很小wrapper凭空建立权威。现价未实查是后续preflight事项，**不是单独据此判技术BLOCKED**；即使Owner提供余额/现价，前两项技术门禁仍需被证明。

不使用chars/4、未经证明byte→token比例、事后usage、旧CNY1.97余额、历史价格快照或393216输出软件常量冒充输入/现金硬上限。历史CNY0.50只是条件候选，本轮批准现金为0。内部144000不兑换成人民币。

模型现金与Tavily credit/费用分开；教学正文HTTP计数和访问许可也独立。后续当前价/币种/时段、余额、搜索账户额度须授权后才核实；本轮未联网。未新增通用tokenizer/跨Provider计费平台、现金数据库或无实际权威的假门禁。

## 4. G3 单次完整 Run 方案

**程序设计可行；当前收费执行仍BLOCKED。** 不需要新增两模型暂停/恢复平台。

建议在可信派发前上界与现金门禁具备后，一次性冻结Scenario A、Provider/binding/options、现有内容/审核来源、一期budget和外部purpose范围，再运行一条完整owned Run。每步保留现有来源/Schema/manifest、累计预算、receipt、checkpoint、fence和取消保护；最后由独立人员对真实输入/输出与教材正文证据评审，Owner明确确认完整Draft。真实质量失败不自动补调用或换模型。

与“两模型后人工复核”相比：省去暂停协议和中途恢复复杂度，但程序合同合法、语义不佳的前两步可能继续消耗本期全部费用，直到最终独立复核才发现。它不能阻止无Schema错误的误解；此风险必须由Owner接受有限最坏花费，不能用程序PASS代替教学质量PASS。

真实业务失败分类不能混淆：

- Goal非ready、Capability未获可信定义、typed Provider/Reader失败、截断、invalid、unknown、预算/fence拒绝会停止对应续接；unknown家族不再派发。恢复复用成功receipt，不重复请求。
- 合法Reader输出但partial/unsupported或teaching-fit不足是资料不足，可在原上限内继续候选；最终required unresolved由Compiler拒绝完整发布。不是任意一次“没找到合适教材”就保证0后续消费。
- owned DurableBody失败/无效结果按明确失败或unknown停止；不得将standalone的body_unread分支直接称为owned自动继续。
- 如果Owner要求首个语义不适配或资料不足立即全停，而非有限预算内研究，则需另行证明小受控门禁；本轮不为此改Worker生命周期。

## 5. G4 最小离线证据

新owned业务 `studyplan_test_v2p3_3eee3f3a`、checkpoint `studyplan_test_v2p3_checkpoint_0bb2c886`；复用现有roles，新增role0；在新库运行既有alembic head0025和PostgresSaver setup，不新增migration。数据库保留。仅本机PG，未启动HTTP/Edge。

| 代表项 | 结果 | 实际断言 |
|---|---|---|
| G4-R1冻结/dispatch前预约/累计/recovery | PASS（机械） | 既有owned factory冻结上一报告精确A GoalSpec与新budget；4次Mock invoke前独立PG连接可见已提交reservation/dispatched attempt；output13312/total4/internalcost80000；恢复额外invoke0，下一4096在invoke前被累计output拒绝 |
| G4-R2超额拒绝 | PASS（机械） | output4095、total0、内部cost19999三反例，全部invoke0、reservation0；只证明内部cost，不是人民币 |
| G4-R3 unknown/usageNone/cancel | PASS（已有机制限定） | 各1次Mock，原预约4096/1/20000不退；unknown相同身份读原receipt、新身份拒绝；取消后fence拒绝；usageNone恢复零重复，但现金不确定阻断另见反例 |
| 同usageNone Run追加next identity | 观察PASS／现金保护缺失 | 原lease有效，无刷新/新库/新Run。第二Mock被允许；累计8192/2/40000，两attempt succeeded且实测output/costNone；不是拒绝PASS |
| 实际Provider serializer/effective options | PASS（Mock） | 根代理MockTransport1次；真实body/headers未写日志，usage/costNone行为复现；不存在Token/cash证明 |
| 超input Token、现金上限的真实门禁反例 | NOT RUN | 没有可信当前token/cash adapter，不用合成数字虚构其有效性 |

G4使用`PgV2Calls.call`的synthetic mechanical purpose，**不是完整A课程、真实LLMResult/Reader Schema或现金验收**。与实际Provider Mock serializer的观察分别记录。PG Mock invokes初始7、追加反例1，共8；另Mock HTTP1；真实DeepSeek/Tavily/正文/Reader/网络preflight均0。各代表Run无Draft。

测试bootstrap仅在新owned库派发前构造submission fixture（旧helper的占位输入由本例A冻结输入替换）；没有改历史Run/receipt/预约。初次tuple/list直接比较在建库前FAIL，改为canonical wire比较后exit0；原失败log保留。补充反例只跑原usageNone场景，没有重跑其他矩阵。

主要证据：`g4/checks.py`、`g4/packet.json`、`g4/execution.json`、`g4/raw-output.txt`、`g4/usage-none-counter.json`、`provider-seam.json`；均ignored。完整Backend、正式PG行数、真实外部接口、真实教材审核及UI本轮NOT RUN。public503复用上一轮明确storage-denied/in-memory单项PASS，源码hash未改变。

## 6. 独立审查与最小后续范围

独审请求Sol6.1 xhigh，只看实际Provider/预算/恢复接缝、合同、G4源码/PG保存证据及本报告，不重复PG/UI执行。具体发现和关闭记录见ignored `independent-review.json`、`independent-review-packet.md`。审查PASS表示BLOCKED判断和证据范围可信，不表示财务保护或真实产品接受。

独审核对：owned预算可注入且旧P1预算绝不可改写；请求cap/manifest/累计三层区分；不存在可信current-token绑定；内部预约不等于人民币；unknown/取消保留原debts；usageNone下一身份可继续是实际缺口；单Run替代暂停符合本轮允许方式，partial研究仍可能消耗至上限。没有为追READY修改合同或费用字段。

### 下一轮 Owner 授权建议

**当前不建议授权收费Run。** 最小下一步只申请有界官方元数据preflight，以解除权威信息缺口；技术现金门禁仍须随后经离线反例验证：

- DeepSeek模型0、Tavily搜索0、教学正文0、Reader0；模型现金上限0、搜索计费上限0，不充值。
- 如Owner另行批准，最多4次元数据HTTPS GET，分别用于当前官方模型/计量绑定、官方价格/币种、账户余额、Tavily账户quota/credit。只用核实的官方端点；若端点/权限/计费不明、需额外tokenizer资产请求或不能获得证明，即停止，不能自行增次或搜索。
- 此“4次元数据GET”是拟议额度，不是已获授权，不包括教学正文或产品搜索。需要准确Token资产/framing权威而这4次无法满足时，先报告最小增量，不能带着假设开始收费。
- 只有Token/现金门禁最终可信，并且实时价/余额/搜索资格满足时，才另申请新Scenario A一期：最多7模型含4Reader、4搜索、4body操作/8HTTP，16384 output、19durable、8候选、262144 body bytes；无域/案例/澄清额外范围。
- 收费一期现金上限此时**未定且授权0**。须用未来权威input上界 `I_j`、output cap `O_j`、核实的CNY每百万单价 `p_in/p_out`，对每次最坏未命中缓存费向上取整累计：`Σ ceil_currency((I_j*p_in + O_j*p_out)/1e6)`。搜索计费单独给上限。不能把CNY0.50默认填入或用内部144000替代。

## 7. 最终状态与保护

| 工作项 | 状态 |
|---|---|
| G0基线/账本/来源核对 | PASS |
| G1新owned内部预算冻结 | PASS；不授予真实费用 |
| G2可信输入Token、现金hard gate | BLOCKED |
| G3单次Run替代暂停的程序方案 | PASS；收费安全执行仍受G2阻断 |
| G4机械预算/恢复保护 | PASS限定范围；input/cash门禁NOT RUN，费用未知续派发缺口已证实 |
| 真实外部preflight与产品验收 | NOT RUN／授权0 |

本地checkpoint只提交本报告及progress，精确Final HEAD由checkpoint及ignored delivery receipt定位。旧939 tracked基线中除progress外全部保持，progress历史保留；`.env`及模型/搜索账本保持。没有生产代码、Prompt/Policy/Schema、正式数据库、旧Receipt、migration或受保护目录变更，不push、merge、deploy；正式 `/plans/generate`保持关闭。

`BLOCKED`

`REAL_EXTERNAL_REQUESTS_NOT_RUN`

`PUBLIC_GENERATE_NOT_ENABLED`

`STOP`
