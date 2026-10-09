# Planning V2 真实语义小规模验收

任务：`PLANNING_V2_REAL_SEMANTIC_SMOKE_V1`，2026-10-09。

**本轮仅完成本地准备，真实语义验收 NOT RUN。** Owner尚未授权任何外部请求，没有执行模型或价格/余额预检。冻结 Scenario A 另发现可在本地证明的 Item2 Provider preflight 阻塞；不消耗收费请求验证已知拒绝，不删除约束或绕过保护。本轮没有获得正式现金硬门禁，也不把开发期大小检查冒充费用上限。

## 1. 基线与复用

- 实际 Start/source HEAD：`b87b15660a1080c242a0935c44c597c95eb537a9`，分支 `feat/n1-resource-discovery`。开始tracked tree clean，仅预存 `.workbuddy/`、`design-preview/` 未跟踪目录，未访问/修改。
- 复用[冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)、[准备报告](PLANNING_V2_PRODUCT_ACCEPTANCE_PREP.md)的Scenario A及C0–U3/Semantic/历史保护证据；[上一轮Token现金结论](PLANNING_V2_TOKEN_CASH_GATE_CLOSURE.md)保留。用户本轮允许后续**另行授权**开发期有界风险测试，不要求先获得正式现金硬上界，但本轮外部授权仍为0。
- 本机最新账本重新核对：模型 request/result各183且连续1–183，unknown177/183原样保留；模型/搜索所有JSON集合hash、`.env` hash与上一轮相同。累计cap280、搜索6/1000证据复用；算术余量97/994不是本轮额度。没有新增授权账、请求身份或账本写入。
- 本地白名单配置：`openai_compatible`、`https://api.deepseek.com`、`deepseek-flash`、deployment输出8192、practice默认4096。实际本地Provider options为每次4096、`thinking.type=disabled`、`response_format.type=json_object`。没有读取凭据值到证据，凭据有效性、账户余额、实时价格及实际服务端模型身份NOT RUN。
- tracked修改仅本报告及progress；本地证据存 `var/planning-v2-real-semantic-smoke-20261009/`。不改架构、Prompt、Policy、Schema、配置、数据库、Worker或正式入口。本地终点SHA见该目录 `delivery-receipt.json`；旧历史保留。

## 2. 沿用冻结 Scenario A

```json
{
  "target": "我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。",
  "starting_point": "已经会 Python。",
  "scope": ["结构化输出", "受限工具调用", "系统性 Agent 应用学习"],
  "desired_depth": "applied",
  "outcome_purpose": "learn",
  "constraints": ["保留现有 CLI 和 JSON 任务文件作为持续实践载体", "不重新创建演示项目", "工具仅操作用户明确允许的本地任务范围"],
  "project_context": "我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。"
}
```

`GoalSpec`规范化后的JSON与前置报告首个冻结输入逐字段一致，未将它换成历史Case7。准备标识仅`offline-preparation-only/offline-item1/offline-item2`，没有进入账本，不是收费Run/attempt。若将来获授权，必须新建专用acceptance和一次性请求身份；177/183及旧Case7身份永不重派。

## 3. 本地入口与大小检查

只复用独立应用入口：

1. `GoalRequirementAnalyzer.analyze → OpenAICompatibleLLM.generate_structured → GoalRequirementProfileValidator`。
2. 明确有效ready Profile后，`CapabilityPlanner.plan → OpenAICompatibleLLM.generate_structured → CapabilityPlanValidator`；不调用Coverage、Research、Reader、Composer或Worker。

`prepare.py`只注入一个没有任何真实HTTP delegate的`CaptureOnlyClient`：在Provider完成实际body构造后捕获，不返回Fake模型输出，而是明确结束本地捕获。Item1调用通过实际Analyzer/Provider序列化，完整system/user messages的紧凑UTF-8 JSON表示为 **5692 bytes**，纯content合计 **5515 bytes**，model/output/thinking与预期一致。完整合成请求在 `item1.offline-wire.json`，不含认证头。

开发期limit为 **32768 bytes**，检查完整messages JSON表示（包括role/content键及转义），不是仅测goal.target。相同检查函数的32768边界通过、32769拒绝，均无外部invoke。它只防意外大载荷，不证明输入Token数、账户费用或API计费上界。当前脚本**没有live模式**；将来真正受控入口必须在同一次POST的body构造后、append-only请求预约/外部HTTP前复用此检查，并绑定实际body hash，不能仅拿本轮离线尺寸放行实际请求。

Item2使用一个**人工合成、仅用于结构/序列化检查**的Profile；不是模型真实输出，也不是语义PASS。它通过现有Profile Validator、保留所有三条structured constraints和项目背景；Capability输入结构及领域证据准入均合法。但实际Provider在preflight拒绝，未构造Item2消息。因此Item2完整wire尺寸检查为 **NOT RUN**，不得假称小于32KiB。以后若解决接缝，必须以实际返回Profile重新校验、计量，超限即停止，不裁剪Policy或约束追求通过。

## 4. 新发现的精确本地阻塞

`OpenAICompatibleLLM.preflight`对Capability调用同时要求合法input、合法领域证据及`composition_dispatch_allowed(profile.hard_constraints)`。`constraint_adaptation.constraint_kind`采用已有精确短语表；`composition_dispatch_allowed`拒绝`no_network`或`unclassified`。

| 冻结约束 | 当前分类 |
|---|---|
| 保留现有 CLI 和 JSON 任务文件作为持续实践载体 | unclassified |
| 不重新创建演示项目 | existing_carrier |
| 工具仅操作用户明确允许的本地任务范围 | unclassified |

本地实际结果：`LLMFailure(error_class=capability_planning_input_invalid, details.dispatched=false)`，Item2外部invoke0。诊断逐项证明input/schema/domain证据通过，拒绝来自composition约束保护，而非领域验证或模型输出。

`GoalRequirementProfileValidator.validate`要求每条`goal.constraints[i]`原文及相应source_ref出现在hard_constraints；因此任何通过当前Validator的Scenario A Profile都必须带上上述两条unclassified约束，Item2会在当前Provider门禁被拒绝。该推论不依赖合成Profile中requirements的具体写法，也不依赖模型质量。第一笔真实Item1可单独执行，但当前不能完成目标中的真实Item1–2两笔链。

首次本地harness假设两个入口均能到达序列化，因Item2既有preflight返回failure而断言失败；随后只修正ignored harness来保留并诊断该阻塞，未改生产保护，也没有重试真实请求。诊断文件为`offline-serialization-blocker.json`与`item2.preflight-diagnosis.json`。

最小下一步是单独评审Capability派发准入与本批明确外发授权的适配范围：区分项目实践范围约束与外部模型许可，并保留真正no-network、未知隐私限制及完整约束来源的fail-closed行为。当前不实施修复、不扩大短语表、不删除约束、不重写Scenario A、不增加Provider旁路。直接用授权开关跳过所有unclassified保护也不能视为已批准的修复。

## 5. 外部门禁与未来顺序

以下四项**均待Owner明确追加授权**：

- 最多2次新的官方`deepseek-flash`调用；非思考，单次output最多4096，两个purpose限定Item1和Item2。
- 最多2次官方元数据读取，用于价格与余额预检；不足或无法核实就停止，不自动增加GET。
- 明确接受本批现金费用没有严格数学硬上限的残余风险；32KiB大小限制不是现金授权金额，也不是CNY0.50保证。
- 不充值、不换模型、不repair/retry；Tavily、GitHub资料搜索、Reader和正文请求均0。

授权之外还存在第4节Item2接缝阻塞，必须另行处理或由Owner明确收缩为仅Item1；不能收到两次调用授权后仍消耗请求去验证已知无法进入第二笔的路径。

将来合法执行顺序：核对未变源码/配置/输入/账本→限定最多2个官方元数据预检→冻结所获价格/币种及本批风险授权→Item1派发前校验options与实际messages大小→以现有append-only模型账本的exclusive请求/result方式记录一次性身份和真实原始响应→Analyzer返回ready且来源、约束、hash合法，usage可信，再进入Item2。Item2复用**实际**Profile而非本轮fixture，大小/来源/参数均重新核对。

遇到unknown/timeout不确定、length截断、usage缺失或不可信、Schema/来源失败、needs_clarification、needs_verification或额外领域验证需求，立即停止本批。原始响应、typed Provider结果、Validator结果及语义意见分别保存；失败也追加账本，不改写历史。不根据`cost_micros=None`推断费用0：有可信input/output usage及冻结官方币种/价格时才能做明确标记的费用估算，峰值cache-miss可作保守估算，不宣称数学硬限。结果不明/缺usage则保留费用未知并停止。

## 6. 验收矩阵与证据

| 检查 | 本轮结果 |
|---|---|
| HEAD/branch、冻结Goal一致、账本/.env及源码保护 | PASS：本地核对；无外部查询 |
| Item1真实入口序列化与options检查 | PASS：仅本地Capture，无模型输出 |
| 开发期32KiB边界 | PASS：32768允许，32769拒绝；不是Token/现金证明 |
| Item2结构fixture及准入诊断 | PASS：精确定位preflight拒绝；不等于Capability语义通过 |
| 独立本地机械阻塞复核 | PASS：12项有界检查，覆盖原Profile拒绝、约束遗漏/改写/丢精确引用、增加已识别约束仍拒绝、needs_clarification仅本地pending；HTTP post到达0 |
| Item2真实请求体大小及两个purpose真实服务调用 | NOT RUN |
| Item1真实Profile、source_refs、hard_constraints、learner_claims、profile_hash | NOT RUN |
| Item2真实CapabilityPlan、Python accepted_known、学习集合、MCP policy/project_usage、约束来源及plan_hash | NOT RUN |
| 实际返回模型身份、finishReason、usage、延迟、费用估算 | NOT RUN；数值未知，不填0冒充免费响应 |
| 独立真实语义审查 | NOT RUN；没有真实模型输出可审 |
| 完整教材/CurriculumPlan/Draft/PG/端到端 | NOT RUN；本轮范围外，不复跑旧技术矩阵 |

未来独立语义审查分别核对：Python已有基础不复习/不测；结构化输出与受限工具调用目标保留；现有Python/JSON待办CLI及三条硬限制完整；不强制创建项目；系统性Agent的MCP课程政策与CLI项目集成分离。合法JSON不等于这些语义成立。Item1程序/语义分别判定，未满足ready+Validator+可信usage不进入第二笔；Item2亦单独判定，不替模型自评背书。

本轮独立代理只复核第4节的源码因果链与准备证据，**不是独立真实语义审查**。报告结论及机械阻塞证明PASS；没有发现保留原Goal同时允许Item2派发的既有合法入口。请求Sol6.1 xhigh，实际解析NOT OBSERVABLE。结论及范围记录于`independent-prep-review.md/json`，不修改保护或调用外部端口。

## 7. 实际调用与停止

真实模型 **0**，官方元数据 **0**，Tavily/产品资料搜索 **0**，Reader **0**，教材正文 **0**；没有新Planning Run/Job、Draft/Plan mutation或migration，未访问正式数据库，实际PG行数核验NOT RUN。只有本地Capture入口及结构fixture，未启动Worker、旧Planning或正式generate。原始真实响应列表为空，usage/费用估算/真实语义均NOT RUN。

**LOCAL_PREPARATION_COMPLETE / EXTERNAL_AUTHORIZATION_PENDING / ITEM2_PROVIDER_PREFLIGHT_BLOCKED**

真实Item1–2语义验收尚未通过；等待Owner决定接缝最小修复范围及上述外部授权。无push/merge/deploy。本轮到此STOP。
