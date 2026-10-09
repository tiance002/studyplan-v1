# Item 2 需求引用修复后的单次真实语义复测

任务：PLANNING_V2_ITEM2_REQUIREMENT_BINDING_REAL_RETEST_V1。日期：2026-10-10。

**Provider PASS；程序合同 PASS；独立真实语义 PASS。**本轮是一次新的 Scenario A Item 2 验收，未重派历史请求、未修改模型输出；不代表完整课程或全产品验收。

## 1. 基线、授权及修改范围

- Start/source HEAD：`c422ebe97536ed580e218fa20a4b1c195046f5cf`；分支 `feat/n1-resource-discovery`。这是 [离线需求引用修复](ITEM2_REQUIREMENT_BINDING_FIX.md) 的已提交基线。
- Owner 在一次新的真实 Item 2 复测建议后回复“允许”。本轮沿用明确的单模型、价格/余额各一次、4096输出、关闭thinking、32KiB消息及此前接受非严格现金硬上限残余风险的受控流程；不追加额度。
- Final HEAD 为本报告所属本地 tag `checkpoint-planning-v2-item2-binding-real-retest-20261010^{commit}`，准确SHA记录在 ignored delivery-receipt.json，避免提交文档自引用。
- 开始时 tracked tree clean，仅既存 `.workbuddy/`、`design-preview/` untracked，未操作。tracked 修改只有本报告和 `docs/implementation/progress.md`。生产代码、Prompt、Policy、Schema、Validator、架构及正式配置未改。
- 本地单次入口复用186已审派发逻辑，只更新HEAD、一次性grant/acceptance身份及186→187计数。独立 delta 审查 PASS，无发现项。harness SHA256：`28886950f0425764c38c24e7a2a4f295ebbff018518a0154c8963c3d3ce27a16`。
- 主协调及独审实际模型解析为 NOT OBSERVABLE；独审请求 `gpt-6.1-sol/xhigh`，未改全局配置。既有离线38项定向测试、Ruff与独审直接复用，没有重复全量回归。

## 2. 冻结实际输入与派发前保护

原184真实响应经原 GoalRequirementProfileValidator 重建，全量Profile、六条需求、source_refs、learner claim及三条constraint_id与历史输出一致。Profile hash：

`b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348`

原184响应SHA256：`5df5001e08e9bdc6d57ebdbc3876b264e95780d67049e5351029a7afd7a69a76`。本轮 Item 1 请求为0，没有使用合成Profile替代。

冻结目标原文：“我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。”scope为结构化输出、受限工具调用、系统性Agent应用学习；desired_depth=applied、outcome_purpose=learn、starting_point=已经会Python。project_context：“我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。”

三条硬约束原文保持：

1. 保留现有 CLI 和 JSON 任务文件作为持续实践载体
2. 不重新创建演示项目
3. 工具仅操作用户明确允许的本地任务范围

实际入口只有 `CapabilityPlanner → OpenAICompatibleLLM → DeepSeek chat/completions`。不启动完整Worker，不进入Coverage、Research、Reader或Curriculum。

最新专用Prompt文件SHA256：`030d3d4e4c9dfb199adbdff5fff76498a18a30d59d844be824aaae21aeffce78`。实际请求model=`deepseek-flash`、`max_tokens=4096`、`thinking.type=disabled`，JSON响应模式。实际序列化的完整system/user messages为 **18,933 bytes ≤ 32,768**。

- messages SHA256：`7c6c8d095149c20393387beb8110e9e4d0a5a3819b45c5125584f3c0eacf4489`
- body SHA256：`94c4d2ed7869bcfc18209adbd9aeefcab96f33d42353d4f6d2996645e19e06cb`

实际wire与本地预检body相等；在入账和HTTP派发前检查大小、身份与保护hash。identity与request追加记录fsync后才发送同一冻结wire。没有API Key或认证头日志。32KiB为异常大输入保护，不能证明Token或现金数学上限。

## 3. 实际外部请求、usage与费用估算

官方元数据共 **2/2** 次：价格与余额各一次，HTTP200、无redirect/retry。预检时间2026-10-10 01:07:52（Asia/Shanghai），账户可用，CNY余额快照 **1.94**。本轮未再次查询余额，未核实实际扣款。

[本轮官方价目](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) 的 `deepseek-flash` 文档版本为 DeepSeek-V4.1-Flash，高峰缓存未命中输入 **CNY2/百万tokens**，输出 **CNY8/百万tokens**。本轮授权读取的文本、HTTP来源与价格绑定在 ignored price.txt、price-source.json、pricing.json；不把文档版本伪装成响应的额外模型身份。

| 项目 | 实际结果 |
|---|---|
| Acceptance / attempt | `item2-binding-retest-0f08ab8c5dbd` / `item2-binding-retest-0f08ab8c5dbd:item2:1` |
| append-only账本编号 | **187**，唯一新请求 |
| 派发时间 | 2026-10-10 01:11:54.698751（Asia/Shanghai） |
| 请求/响应model | deepseek-flash / deepseek-flash |
| HTTP / finishReason | **200 / stop** |
| input / output / total tokens | **4705 / 2496 / 7201** |
| reported cache hit / miss | 384 / 4321；估算不使用缓存折扣 |
| Provider latency / 应用wall | **7756 ms / 7871 ms** |
| Provider cost_micros | null，不解释为人民币 |
| 高峰缓存未命中费用估算 | **CNY0.029378**，非实际扣款、非数学现金硬上限 |
| 本轮unknown / retry / repair | **0 / 0 / 0** |

费用估算：`(4705×2 + 2496×8) / 1,000,000 = CNY0.029378`。原usage为非负整数、total一致，typed Provider相等，output≤4096，finishReason=stop。没有缺失usage、截断或额外领域验证。本批授权不构成现金硬门禁PASS。

## 4. 程序合同与真实CapabilityPlan

原CapabilityPlanValidator直接接受未修改的模型JSON。应用返回 `CapabilityPlan`，模型状态ready，无pending或澄清；确定性hash重建PASS。服务端按既有Policy规范化能力定义/outcomes及MCP特殊政策，不属于修补失败响应或模型repair。

Plan hash：`e14f5f95c01570784d4b8387e842202a2f6a464ee7f6d06eb5bf71066e38b837`

| 实际能力 | 学习处理 | 项目使用 | 技术目标与来源 |
|---|---|---|---|
| python.core | accepted_known / recommended | required | 原Python claim；无learning_target_refs，不进入学习集合 |
| llm.api | needs_learning / required | required | 结构化输出、受限工具调用的技术目标及应用/条件refs |
| structured.output | needs_learning / required | required | 结构化输出技术目标，前置llm.api |
| tool.calling | needs_learning / required | required | 受限工具调用技术目标，前置llm.api |
| mcp | needs_learning / required | optional | 自身Policy与服务端systematic-agent-mcp；技术目标refs为空 |
| error.permission | needs_learning / recommended | required | 受限工具、项目应用及应用条件，不伪装成显式技术目标 |
| eval.lite | needs_learning / recommended | required | 对结构化输出、工具调用及CLI应用的可检查案例 |

七项desired_depth均applied。Python的深度字段不改变accepted_known排除学习的语义。没有json.cli、RAG、多Agent、云部署或固定职业路线。三条constraint_effects均 `not_applicable / capability_id=null`，含义是不构成能力排除，**不代表实际项目载体或工具权限已满足**。

六条原始需求的真实引用矩阵（R编号仅为报告简称，不新增合同字段；完整稳定ID见冻结profile.json及模型JSON）：

| 原requirement文本 | 实际requirement_refs承担能力 | 实际learning_target_refs |
|---|---|---|
| R1：完整既有Python CLI/JSON项目背景 | python.core | 无 |
| R2：系统学习Agent结构化输出 | llm.api、structured.output、eval.lite | llm.api、structured.output |
| R3：系统学习Agent受限工具调用 | llm.api、tool.calling、error.permission、eval.lite | llm.api、tool.calling |
| R4：把这些能力加入现有待办CLI | llm.api、structured.output、tool.calling、error.permission、eval.lite | 无 |
| R5：学习深度为应用级 | python.core、llm.api、structured.output、tool.calling、mcp、error.permission | 无 |
| R6：学习成果用途是学习 | python.core、llm.api、structured.output、tool.calling、mcp、error.permission | 无 |

原186遗漏的R4、R6均被覆盖；不将应用/深度/用途编造为新技术目标，不是all-ID复制到所有能力。MCP上的applied/learn属于规划条件引用，课程required原因仍由systematic路线Policy决定，项目optional不变。

原始response SHA256：`8d5281dfb1264bbac3806b39930716adf3279263009c6217a6f16d6ab0828f66`。完整原始HTTP响应、模型JSON、应用Plan、身份及账本结果引用保存在 ignored `var/planning-v2-item2-binding-real-retest-20261010/` 的 item2.response.body、item2.provider.json、item2.json、item2.identity.json。不会将合成witness作为本次证据。

## 5. 独立真实语义审查

独立开发审查代理直接对照冻结Goal、原184 Profile、真实187原始response、当前Policy及Validator进行审查，结论为 **本次Scenario A限定PASS**。没有让被测DeepSeek自行判定通过。审查具体证据在ignored review-item2.json/md，绑定原始response和Profile，区分机械合法与业务合理。

| 独审项目 | 状态 | 依据与限制 |
|---|---|---|
| 已知Python | PASS | accepted_known且绑定原claim；不安排复习或掌握度测试 |
| structured.output | PASS | required/applied，真实结构化输出技术目标及CLI应用引用 |
| tool.calling | PASS | required/applied，真实受限工具技术目标及CLI应用引用 |
| llm.api及前置 | PASS | 实际API请求/响应为两技术目标的必要交互先修；R2/R3技术目的归因有依据，不声称用户单独明确要求学API |
| MCP课程与项目采用 | PASS | 系统性Agent Policy引入required学习；project optional，targets为空。R5/R6仅条件，不伪造MCP明确技术目标 |
| 原CLI/JSON项目保留 | PASS | R4由structured/tool等实际应用能力承担；原背景保留，不要求重建项目 |
| 工具权限范围 | PASS | 三约束not_applicable，不错误排除tool.calling；不声明实际权限已验证 |
| 不机械新增json.cli | PASS | 既有JSON项目未推断为完整掌握或强制重学json.cli |
| 深度/用途分离与六需求覆盖 | PASS | 全部原ID有引用，R4/R5/R6不进入技术target；Python条件refs/applied不改变已知状态 |
| 辅助能力与范围 | PASS | error.permission对应受限工具拒绝/错误边界；eval.lite对应两能力应用CLI后的可检查成功/失败案例，均为recommended学习，有实际目标依据 |

与186比较：R4/R6遗漏已解决并形成合法Plan；能力集合从五项变七项，新error.permission与eval.lite不是为覆盖任意ID新增的无关专项。MCP和Python保留正确区分。本次语义PASS来自实际输出审查，不能用之前的synthetic witness或测试PASS替代；单次通过不证明Prompt普遍稳定改善。

载体原文、JSON文件保留、工具许可边界的实际课程/运行满足仍未验证。本Plan的项目required和约束not_applicable是规划事实，不是后续权限执行或完整Draft合格证明。

## 6. 历史保护与结束边界

final-audit.py原生exit0，保护PASS。旧184/185/186证据目录、历史账本、unknown177/183、`.env`、生产源码及冻结合同hash保持；模型账本仅追加本轮grant、request-187.json、result-187.json，连续配对至187。187为succeeded/unknown=false，账本成功表示本次调用及程序结果成功，不代替教学质量验收。搜索账本完全不变。

本轮模型 **1/1**、官方元数据 **2/2**；Item1、搜索、Tavily、Reader、正文、其他模型 **0**。无重试/repair，无历史identity重派。独立调用入口没有产品Worker、Run、Job、Draft或Revision持久化；本地acceptance/run_id只是调用身份。本轮不连接正式或owned PG，行计数验证 **NOT RUN**。

STOP.json在请求完成后已冻结 `further_dispatch=false`。公开generate仍保持原fail-closed配置和源码，复用既有503证据；本轮HTTP门禁探测NOT RUN。无push、merge、deploy，不开放正式生成。原progress历史字节保留，只追加本轮事实。

## 7. 仍未验证与后续工作

真实教材资格、Coverage/Research/Reader/Curriculum、完整Draft、课程顺序和连续实践、实际工具权限、PG/Worker、React/浏览器及全量Backend均 **NOT RUN**。严格数学现金硬门禁、真实扣款读回仍 **NOT RUN**。

本次只能说明冻结Scenario A的一次真实Item2结果。即使独审通过，也不证明所有用户目标稳定可靠，不扩大为Item3–7或完整产品PASS。existing_carrier/local_tool_scope仍必须在后续课程中有可信满足证据；不足时继续pending/incomplete，不能因本次可派发及Plan合法自动满足。

任何下一阶段资料研究或新的外部调用仍需Owner单独决定；本轮不执行。

**ITEM2_REAL_SEMANTIC_RETEST_PASS**

**ITEM3_7_NOT_STARTED_THIS_RUN**

**REAL_PRODUCT_ACCEPTANCE_PENDING**

**STOP。**
