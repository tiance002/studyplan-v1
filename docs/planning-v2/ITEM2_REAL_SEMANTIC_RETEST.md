# Item 2 单次真实语义复测

任务：PLANNING_V2_ITEM2_REAL_RETEST_V1。日期：2026-10-10。

**Provider PASS；程序合同 FAIL；独立真实语义 FAIL。不是合法 pending。**

Owner 在明确的“1次Item2模型、最多2次官方元数据、4096输出、关闭thinking、32KiB消息、接受非严格现金硬上限残余风险”范围之后回复“执行”，本轮按该范围执行。唯一模型请求已完成并STOP，没有重试、repair或后续模型调用。原始JSON没有修改或补齐；未形成合法CapabilityPlan或plan_hash。

## 1. 基线、授权与范围

- 参考/source HEAD：f214f729ec05322c8e179adc2deadc94a90fc731。
- R0准备报告提交及真实执行Start HEAD：9bd56be638ae4db39609b1d8b4402cdad320691b。与参考之间只有本任务报告/进度，无新增源码变化。
- Branch：feat/n1-resource-discovery。执行前tracked tree clean，仅既存 .workbuddy/、design-preview/ untracked，未操作。
- Final HEAD为本报告所属tag checkpoint-planning-v2-item2-real-retest-20261010^{commit}；准确SHA保存ignored delivery receipt，避免文档自引用。
- 复用 [原Scenario A真实验收](PLANNING_V2_SCENARIO_A_REAL_SEMANTIC.md)、[约束作用域修复](ITEM2_CONSTRAINT_SCOPE_FIX.md)、[Item2离线修复](ITEM2_REAL_FAILURE_FIX.md)。原117项回归/20项修复测试/Ruff/独审在源码未变时复用，不重跑Item1或完整矩阵。
- tracked修改仅本报告和进度。harness、响应和审查证据在ignored var/planning-v2-item2-real-retest-20261010/。架构、Policy v2、Schema、Validator、历史Profile、生产代码和正式配置未修改。
- 独立审查请求gpt-6.1-sol/xhigh；实际解析NOT OBSERVABLE。主会话实际解析同样NOT OBSERVABLE，未修改全局模型配置。
- 本轮授权只消费新scope；原184/185授权已使用，不沿用旧额度。允许不严格现金硬上限的开发验收，不构成现金门禁PASS。

## 2. R0：原真实Profile与请求冻结

从第184次原始HTTP响应 var/planning-v2-scenario-a-real-20261009/item1.response.body 提取模型JSON，再以原GoalSpec和原GoalRequirementProfileValidator重建。全文与历史item1.json.output、原Provider payload完全相同，source_refs、constraint_id和确定性hash均保留。

- 原响应SHA256：5df5001e08e9bdc6d57ebdbc3876b264e95780d67049e5351029a7afd7a69a76。
- 实际输入Profile hash：b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348，status=ready。
- 原独立Item1语义PASS的响应/Profile绑定一致，本轮Item1请求0。未使用合成Profile替代。
- 最新Item2 Prompt文件SHA256：b38c2a292577fc3ebcaabeee8f9e463924cc9ed3b41488ac3cc30b634bfd6d8e；实际system消息与当前CAPABILITY_SYSTEM一致。

冻结Scenario A：已会Python；系统学习Agent结构化输出与受限工具调用；applied深度、learn用途；现有Python待办CLI、JSON任务文件。三条约束原文：“保留现有 CLI 和 JSON 任务文件作为持续实践载体”“不重新创建演示项目”“工具仅操作用户明确允许的本地任务范围”。完整Goal/Profile在goal.json、profile.json，原184/185响应不改。

调用链仅 CapabilityPlanner → OpenAICompatibleLLM → DeepSeek chat/completions。无完整Worker、Coverage、Research、Reader或Curriculum。

实际参数：deepseek-flash、max_tokens=4096、thinking.type=disabled、JSON响应模式。完整system/user messages canonical UTF-8为 **17,775 bytes**，≤32,768；真实入账前检查，body与R0捕获相等。messages SHA256：b911f9af9ef682cea4e82e1c89ba3422d39ff7e5f805f1a4dd964eeb988743aa；body SHA256：630d99817623e3744fa3ca50c319556511c567a11a1181e8210b77aec6c785e1。同一wire先绑定identity并fsync追加请求账本，再发送HTTP；没有认证头/API Key日志。

32KiB只是开发期异常大输入保护，不是Token或现金数学上限。

## 3. 官方预检、请求、usage及费用

官方价格/余额GET恰好2次，均HTTP200，无redirect/retry。预检时间2026-10-10 00:27:41（Asia/Shanghai）：账户is_available=true，CNY余额1.95。此为派发前快照，未追加余额读取或核实实际扣款。

[本轮官方价目](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) 显示deepseek-flash文档版本DeepSeek-V4.1-Flash，高峰缓存未命中输入CNY2/百万tokens、输出CNY8/百万tokens。冻结文本及来源在price.txt、price-source.json、pricing.json。实际响应模型别名为deepseek-flash；不把文档版本当作响应返回的额外身份。

| 项目 | 实际结果 |
|---|---|
| Acceptance / attempt | item2-real-retest-515c82f1b8a6 / item2-real-retest-515c82f1b8a6:item2:1 |
| 原append-only账本编号 | **186**，新identity，无历史重派 |
| 派发时间 | 2026-10-10 00:31:02.879748（Asia/Shanghai） |
| 请求/响应model | deepseek-flash / deepseek-flash |
| HTTP / finishReason | 200 / stop |
| input / output / total tokens | **4474 / 1152 / 5626** |
| reported cache hit / miss | 128 / 4346；估算不采用缓存折扣 |
| Provider latency / 应用wall | **4330 ms / 4430 ms** |
| Provider cost_micros | null，不当作现金金额 |
| 高峰缓存未命中费用估算 | **CNY0.018164**，非实际扣款、非数学现金硬上限 |
| 本轮unknown / retry / repair | 0 / 0 / 0 |

估算：(4474×2 + 1152×8) / 1,000,000 = CNY0.018164。原usage整数、非负、total一致，typed Provider usage相同，output≤4096。没有用历史价格或事后余额推测扣款。

## 4. 程序合同与失败诊断

Provider返回合法JSON及可信usage，原CapabilityPlanValidator仍拒绝未经修改的JSON。首拒details.field为 **required_requirement_coverage**。

| 未覆盖的原requirement | 原来源 | 缺陷 |
|---|---|---|
| req_31f0e2d9e8cedf68a82afaa4d2a24a69caca334d808b1d3e2428501284b89121：“把这些能力加入我现有的待办事项 CLI” | goal.target、project_context | 全部能力requirement_refs均未绑定显式项目整合目标 |
| req_ef9a96e06fdb82a3b722992b257e488669318f9820ae438c433808b60b87491a：“学习成果用途是学习” | goal.outcome_purpose | 冻结合同所需的规划条件覆盖遗漏；不能伪装成技术learning_target补救 |

应用返回LLMFailure(error_class=capability_plan_invalid)。不是CapabilityPlanningPending或unknown；模型声称status=ready不等于合法Plan。plan_hash=null，完整hash重建NOT RUN。没有修改Profile、补字段或生成修正版witness。

局部机械检查通过：五项Policy refs及真实前置精确匹配Policy v2；没有额外requirement_ref；Python claim准确；三条constraint_effects均not_applicable/capability_id=null；systematic路线MCP为required学习、optional项目。Validator到需求覆盖检查后拒绝，完整server-normalized Plan、MCP特殊政策最终绑定及hash没有生成。

原始实际response及模型JSON完整保存在item2.response.body、item2.provider.json；应用失败在item2.json；原样重放与缺失ID/文本/来源在item2.validator-diagnosis.json。原响应SHA256：8b0726363d90fae713d761209c7bdef600e2349ef2b628ca1472247f163af320。

## 5. 独立真实语义审查

独立开发代理对照原Goal、真实184 Profile、原186 response及冻结Policy审查并原样重放Validator。逐项证据在review-item2.json/md、review-summary.md，绑定上述响应hash及真实输入。**10项为9 PASS/1 FAIL，整体FAIL。**程序检查不能代替语义审查。

| 独审项目 | 状态 | 原始输出依据 |
|---|---|---|
| 原Profile及来源身份 | PASS | 原184全文、来源hash与实际请求一致，没有改写目标 |
| Python已知且不复习测试 | PASS | accepted_known、原claim绑定，无基础学习/掌握测试 |
| structured.output学习目标 | PASS | required/applied，绑定真实结构化输出技术目标 |
| tool.calling学习目标 | PASS | required/applied，绑定真实受限工具调用技术目标 |
| llm.api及能力范围 | PASS | 实际先修正确，没有无依据辅助能力或固定路线 |
| MCP课程政策与项目采用 | PASS | required学习、optional项目；自身Policy来源，不把learn当MCP明确技术目标 |
| 三条实践约束效果 | PASS | not_applicable，不变成能力排除或权限已满足 |
| 原CLI/JSON不强制完整json.cli | PASS | 没有新增json.cli或完整掌握断言，也不要求重建项目 |
| depth/purpose与技术目标区分 | PASS | applied作为条件引用；learn不伪装技术目标（其引用缺失另由完整覆盖项拒绝） |
| 完整目标归因与ready成立 | **FAIL** | 原CLI整合及learn条件未覆盖，局部背景保留不足以宣布ready |

不存在已确认的硬约束冲突，不能把失败包装成合法pending。局部正确及一次结果不能证明所有用户目标可靠通过。仍未验证教材、课程或Draft语义。

## 6. 与第185次真实失败的差异

| 185缺陷 | 本次186 |
|---|---|
| 七个已知能力缺Policy refs，首拒definition_refs | 五项定义和前置引用均正确，首拒已变化 |
| CLI载体误作json.cli项目排除 | not_applicable，没有机械增加json.cli |
| 工具范围误作tool.calling项目排除 | not_applicable，与实际能力使用不冲突 |
| MCP以learn用途伪装明确学习目标 | MCP技术目标refs为空，自身Policy refs正确，项目optional |
| applied条件遗漏 | 本次两项能力引用applied；但项目整合和learn条件遗漏 |

这些只是本次原输出的局部改善，不能宣称Prompt对任意目标已稳定有效。185原失败和原响应保持原样。

## 7. 派发门禁审查及历史保护

派发前独审发现两项ignored harness记录bug：未预约也可能标unknown；不可信usage也可能给数字费用估算。仅修本地入口，unknown依赖已预约且结果不明，估算依赖可信Provider usage/model/finish门禁。5个unknown表达式和2个cash条件反例PASS。初审FAIL保留review-harness-initial.json/md；最终review-harness.json/md PASS，harness SHA256：1e030972bbe2b7c276b509ab281febb2cb0ef3a046399cd68821f2dccc593e1a。没有修改生产代码或模型输出。

最终账本保护PASS：旧1–185请求/result及历史响应hash不变；只追加authorization-item2-real-retest-20261010.json、request-186.json、result-186.json。连续配对至186；186为failed/unknown=false；历史unknown177、183保留；搜索账本不变。identity、R0 body及实际wire hash相同。STOP.json明确scope已消费且禁止继续派发。

本轮模型 **1/1**、官方元数据 **2/2**；Item1、搜索、Reader、正文、其他模型 **0**。无retry/repair、旧identity重派、正式数据库、产品Worker/Run/Draft/Revision写入。此处acceptance/run_id只是应用调用身份，不代表创建产品Run。

公开generate保护、正式配置及全部生产源码hash未变，沿用原503证据；本轮HTTP门禁探测NOT RUN，未启用正式生成。仅报告/进度文档更新，原历史进度字节保留；未push/merge/deploy。final-audit.json及delivery-receipt.json记录交付保护。

## 8. 未验证事项和下一步

全量Backend/PG/Worker、React/浏览器、Item3–7、真实教材及完整课程/Draft质量均NOT RUN。实际扣款读回及严格数学现金硬门禁NOT RUN。

existing_carrier/local_tool_scope被识别、不构成能力排除，不表示项目载体或实际权限已满足；下游缺可信证据时Curriculum继续pending/incomplete。本次没有进入那些环节。

最小下一步建议为有界离线定位：强化冻结requirement_refs完整覆盖核对，明确原项目应用目标以及用途/深度条件的真实引用，同时learning_target_refs只指技术目标。禁止删除原Profile需求、任意关联能力、放宽Validator或修正旧响应。本轮不实施建议、不申请或消费第二次请求；任何再次真实复测须单独授权。

**ITEM2_REAL_SEMANTIC_RETEST_FAIL**

**ITEM2_SEMANTIC_REVIEW_REQUIRED**

**ITEM3_7_NOT_STARTED_THIS_RUN**

**STOP。**
