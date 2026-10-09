# Planning V2 真实课程验收前的定向收口

任务：`PLANNING_V2_POST_ITEM2_PRODUCT_CLOSURE_V2`。日期：2026-10-10。

**真实184/187输入的Item3–4离线计算PASS。课程权限约束需要Owner语义决策；当前教材候选遍历不能证明“质量与覆盖优先、相当时中文优先”，旧4Reader范围也不能闭合六组真实缺口。真实教材与课程验收NOT RUN。**这些结论分别记录，不将尚需决策的课程阻塞误报为Coverage/Gap失败。

## 1. 基线、范围与来源

- Start HEAD：`e727fc9dda9be7f69daa2b234cc961385bbd9f66`，分支 `feat/n1-resource-discovery`，与参考一致。开始tracked tree clean，既存 `.workbuddy/`、`design-preview/` 未访问或修改。
- 权威为 [冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)，复用 [187真实验收](ITEM2_REQUIREMENT_BINDING_REAL_RETEST.md)、[产品验收准备](PLANNING_V2_PRODUCT_ACCEPTANCE_PREP.md)、[派发门禁](PLANNING_V2_REAL_ACCEPTANCE_DISPATCH_GATE.md) 和 [Token/现金阻塞报告](PLANNING_V2_TOKEN_CASH_GATE_CLOSURE.md)。既有Provider、React、PG、Worker与历史保护验收不重跑。
- 本轮真实模型、搜索、Reader、教材正文及账户预检均为 **0**。仅原有本地文件只读核查、Domain计算和Mock反例。没有新业务Run、Job、Receipt、Draft/Revision或数据库写入；真实PG行计数NOT RUN。
- tracked改动只有本报告和progress；不修改Prompt、Schema、Validator、Policy、生产代码、审核资格或正式配置。原184–187记录与unknown177/183不重派、不改写。
- 原始证据放ignored `var/planning-v2-post-item2-closure-20261010/`，不含凭据、认证头或教材全文。Final HEAD由本地tag `checkpoint-planning-v2-post-item2-closure-20261010^{commit}` 和delivery-receipt.json记录，避免报告自引用。
- 路由：研究边界Sol6.1 medium、课程合同及独立审查Sol6.1 xhigh；主协调沿用户偏好。实际解析均 **NOT OBSERVABLE**，不修改全局配置。

原184的 `item1.response.body` 提取原模型JSON，以原GoalSpec和 `GoalRequirementProfileValidator` 重建；原187同样从 `item2.response.body` 提取，调用原 `CapabilityPlanValidator`。两者全文与历史应用输出、Provider payload和独审绑定一致，没有使用synthetic witness。

| 冻结事实 | 实际hash |
|---|---|
| 184原响应SHA256 | `5df5001e08e9bdc6d57ebdbc3876b264e95780d67049e5351029a7afd7a69a76` |
| GoalRequirementProfile | `b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348` |
| 187原响应SHA256 | `8d5281dfb1264bbac3806b39930716adf3279263009c6217a6f16d6ab0828f66` |
| CapabilityPlan（Policy v2） | `e14f5f95c01570784d4b8387e842202a2f6a464ee7f6d06eb5bf71066e38b837` |
| reviewed_index（planning-v2-reviewed-v1） | `0e0ca1a7fffc0d3b4d5cdcadfbb55ec7434d7a4dfa1b805e73fd80f985434fe6` |
| CoverageResult | `07030b56e26433e518b34f812cccce9de71a7dcb63c44929c1b0cb180a25d183` |
| ResourceGapSet | `141b925fd307e98996b6f34280b24fcc8be17f31d3ab78fdd7e679686ad80315` |

本机模型账本连续187对，unknown仍177/183；搜索账本不变。旧总额度只是历史授权记录，本轮可用外部授权为0，不能沿用余额或剩余次数消费。

## 2. P1：真实Plan → 正式Reviewed Index → Coverage → Gap

实际入口为 `load_reviewed_content_index()` → `CoverageEvaluator().evaluate(plan,index)` → `CoverageResultValidator.validate` → `extract(plan,coverage)`。loader直接核查冻结pack、review文件、版本、section/review对象hash，没有临时合成索引。计算由 `compute.py` 执行，native exit0；输入对象未改变，重复冻结输入得到同样结果及hash。

| B类能力 | outcomes | covered | missing | coverage | 缺口重要性 |
|---|---:|---:|---:|---|---|
| llm.api | 3 | 0 | 3 | none | required |
| structured.output | 2 | 0 | 2 | none | required |
| tool.calling | 2 | 0 | 2 | none | required |
| mcp | 3 | 2 | 1 | partial | required |
| error.permission | 1 | 0 | 1 | none | recommended |
| eval.lite | 1 | 0 | 1 | none | recommended |
| 合计 | **12** | **2** | **10** | 1 partial / 5 none | **8 required / 2 recommended** |

`python.core=accepted_known`保持，只读六项learning_capabilities；没有Python复习、测试或资料缺口。所有Gap深度applied；importance、requirement_refs及Outcome ID/文本精确继承187Plan。covered/missing不交叉且完整划分输入outcomes，没有将已覆盖MCP理论再加入研究。

| 稳定missing outcome ID | 冻结文本 |
|---|---|
| llm.api.exchange | 组织模型API请求并读取模型响应 |
| llm.api.failure_boundary | 识别模型请求失败、截断与结果未知的边界 |
| llm.api.usage_cost | 读取模型请求usage并理解费用边界 |
| structured.output.contract_definition | 定义模型结构化输出合同 |
| structured.output.response_validation | 按输出合同校验模型JSON响应 |
| tool.calling.input_validation | 按工具输入合同校验调用参数 |
| tool.calling.invoke_result | 派发有效工具请求并处理调用结果 |
| mcp.minimal_connection | 完成有界的MCP最小接入并验证一次工具调用结果 |
| error.permission.denial | 区分输入错误、权限拒绝、执行失败与未知结果 |
| eval.lite.cases | 用可检查案例验证目标行为和失败分支 |

完整结构化对象在ignored `profile.json`、`capability-plan.json`、`reviewed-index.json`、`coverage.json`、`gaps.json`、`summary.json`，保留六条Requirement的完整稳定ID与真实对应关系。

### MCP已有审核依据

`agent.application` v8 / `src_mcp101_a7ca881ee83ac722491299cd` source v2 / `sec_mcp101_09e62ff389cb388eb744e738`，审核范围 `selected_sections_read`。唯一内容引用支持 `mcp.roles`、`mcp.interfaces`，不支持minimal_connection。

- [pack v8](../../backend/app/infrastructure/content/agent-application-v8.json) 的 `/resources/13/sections/1` 及 `/resources/13/review_evidence/chapter_review`。
- [保留语义审核](../research/semantic-corrected-2026-10-04/AGENT_APPLICATION_DEEP_REVIEW.md) 第197–205行。
- pack SHA256 `6171e7bbed660d3f1d81d0c65b7b102eef0c2ec8dd7a3c40e54d4e3093985d0b`；review文档SHA256 `3349acbc6b407d48560a48a9c7891ac20856aaa8dddf8702faf9823797bab55c`。
- section对象hash `8278e9f8bae2291a5446080f771f0080381b02ce9c5734e0cc994f9ef74e9b38`；chapter_review对象hash `2be64ad62fee6b73832ff08fd404bed705ba9a4b8b47120bdc46c4b9bd3cbd07`。

这些是pack/审核记录hash，不冒充原教程正文hash。保留审核明确示例未运行、传输示范部分为注释/片段、SDK版本及server权限有限制。本轮只核对已有审核事实，不重新审整套Seed或读取公开教程。

## 3. P2：课程义务与未来运行权限混淆

当前确定链路：

`assess_curriculum(local_tool_scope)` → `pending / runtime_permission_evidence_pending` → `constraints_unresolved=True` → `curriculum._validate_output`要求status=incomplete → `curriculum_compiler._validated_curriculum`拒绝field=incomplete → Runtime报告 `v2_curriculum_incomplete`，不持久化可确认完整Draft。

无论是否已有充分教材，Scenario A的这条约束在当前规则下都不能仅凭课程文档变成complete。它不是“漏跑一项测试”。本轮原保护保持，不能直接把pending改satisfied或将complete强报为合法。

现有Knowledge/Unit/Guidance、PracticeDelta、Task及Acceptance可以保存教学文本、输入输出、产物、验证说明和outcome links。因此能够要求学习者设计允许范围、调用前权限与参数校验、越权拒绝、错误/拒绝路径、保护JSON数据，再以具体任务验证。它们能够表达“将来要做什么”，不能在学习前证明用户代码现在已经正确执行。

当前并无独立的、闭合校验的权限教学义务结构：教学/验收文本存在不等于确定性证明六项义务已齐备；随意安全承诺、关键词出现或模型自报不能作为可信满足证据。当前closed Schema拒绝随意加入permission字段，Compiler也重建服务端constraint_assessments并拒绝伪造快照。

需要明确区分：

| 层次 | 课程确认时能核查 | 不能提前宣称 |
|---|---|---|
| 教学规划义务 | 具体任务、允许范围定义、检查步骤、拒绝与失败案例、JSON保护、产物与可执行验收的绑定及完整性 | 学习者已完成实现、实际文件访问安全 |
| 未来Practice/Outcome事实 | 实践提交后由相应验收证据核实权限执行、越权拒绝、数据不被破坏、失败输出 | 课程文本或模型保证等同已验证结果 |

**首选最小方案（建议，未实施）：** 只对新版本local_tool_scope增加有界结构化“权限教学义务→现有Task/Acceptance/PracticeDelta引用”，由服务端校验义务完整、链接合法和可检查产物；课程complete含义调整为“本次教学安排和可执行验收充分”，实际运行权限保持未验证并交未来Practice/Outcome验收。不能用运行权限satisfied标签表示教学义务已安排，不能凭文字或模型承诺放行。不创建权限Runtime、通用评分或新平台，不改其他unknown/no_network/隐私/只读约束含义。

是否足以采用上述语义、必要最小字段、验证规则及新版本绑定，必须Owner明确批准后再实施。本轮不修改冻结合同、Producer或发布条件。若没有批准，保留现状pending/incomplete。

建议的最小结构至少绑定原constraint/source refs、project_context hash和精确Task/outcome refs；明确“实际执行前须用户显式授权”“范围来自用户允许的本地任务”“默认拒绝”。允许范围、无授权、越界、参数不合法、失败/拒绝路径及原JSON保护的检查义务应引用具体实践与验收。服务端只能证明 `planning=arranged`，未来 `runtime=unverified` 保持，不能生成不存在的运行evidence refs。这是字段与消费职责建议，不是本轮新增Enum/Schema或实现。

既有载体保护继续严格：`carrier.kind==user_project` 且 `carrier.description==原project_context`，并保持原project_context hash。规划义务修订不能放宽此精确保护，不能将原CLI换成Starter。

影响范围至少包括Item6专用输出合同/Producer及Domain closed字段、ConstraintAssessment分层/版本引用、Curriculum Validator、Compiler快照重建与hash、Compiled/V2 snapshot、Draft当前内容校验/确认，以及历史Revision读回/重新校验。当前v1/v2约束记录必须继续按原语义解释，新版本不得反解释历史成功/失败Run。已有JSONB承载可作为候选，但本轮没有证明字段扩展及历史重验的最小实现已完成，不能提前承诺无需任何合同调整或自动 migration。

**CURRICULUM_CONSTRAINT_OWNER_DECISION_REQUIRED**

## 4. P3：真实教材研究范围及语言偏好反例

### 资格分层

八个required缺口需要真实教学章节证据；两项recommended缺口仍保留，不由本轮删除。当前只有两个MCP理论outcomes的正式reviewed映射，其他Seed、URL、README、章节目录、候选卡都不能自动转为covered。

Coverage reviewed与免费可访问材料是两项事实。pack保留 `content_access=free_public` 可作为本地声明来源；未来装配仍需matching catalog source/version及 `ReviewedAccessProof(source_id,source_version,content_hash,access=free_public)`。`ResourceResearcher._reviewed` 和 `prepare_curriculum` 检查该身份，未装配匹配proof时covered教材不能自动变usable。本轮没有核查实时访问或未来owned source_facts，不将测试proof冒充真实网络确认。

候选发现可优先GitHub教学资源，Web仅候选发现；正文需合法版本/位置/免费访问证据，Reader绑定实际chunk/hash，并证明对应missing outcomes。API费用/失败边界常需官方精确行为补充；结构化输出、工具调用和验证可以由一套连贯教程的不同章节承担，但不能只凭标题推覆盖。MCP概念review不能覆盖最小接入实践。

Project Study由Item6依据教学必要性形成有界requirement，可不存在。不因MCP必学而研究大型MCP源码项目；用户CLI是Continuous Practice载体，不是已审核的他人项目案例。若确需Project Study，新增源码版本/切片/正常失败链/取舍及产物证据和预算必须另行评审，现有目录或候选不足。

### 有界反例：最低资格不等于最佳主教材

实际链路位于 `teaching_resource_research.py::ResourceResearcher.research`：151行先按中文排序，155–158行remaining为空即停止；`_inspect`只把当前缺口交Reader，329–339行教学fit为阈值准入。Item5不决定PRIMARY，Item6才决定教材角色，但Item6不能比较没有接收的候选。

本轮用真实Application加Fake候选/正文/Reader运行以下反例，socket网络入口硬拒绝。反例机制检查 **PASS**；以下教学质量为合成场景设定，不证明真实英文或中文教材实际更好。

| 合成反例 | 实际观察 | 政策/影响判断 |
|---|---|---|
| 搜索英文在前，中文最低合格，英文设定更连贯更优 | 中文先读，填满该组outcomes即resolved，仅1Reader，英文未读 | **FAIL：不能证明质量优先比较；不能称中文最适合Primary** |
| 两候选设定同质量同覆盖 | 中文先读并resolved | 中文偏好结果可实现，但“已比较后相当”未证明 |
| 中文部分覆盖、英文设定更广 | 读两次；英文只收到尚缺outcomes | 覆盖union成立，无法比较英文对已填outcomes的整体教学优势 |
| 中文continuity不足 | 中文拒绝后英文审读解决 | 最低资格保护PASS，不能替代合格资源之间的比较 |
| 中文部分覆盖、Reader额度1 | partial/budget_exhausted；英文未Reader审读 | 预算保护PASS，最佳教材判断NOT RUN |

Reader的continuity/beginner_fit/examples/version_fit为类别阈值，不表达合格候选间更优教学质量。每outcome rationale经过Reader校验但未进入ResearchResource；limitations保留。`curriculum.py::prepare_curriculum` 的researched material投影还不传teaching_fit及language，削弱后续比较证据。本轮没有调用真实Curriculum或观察PRIMARY结果，**不能声称实际已选错主教材**，已证明的是比较前停止风险与必要比较证据不足。

首选后续方向仅作为决策材料：在获准的小候选集合内先比较教学质量/目标覆盖，再以中文作质量相当时的偏好；保留必要比较依据交Item6，Primary职责仍属于Item6。不是要求穷举全部外网候选，也不引入分数模型、通用排名平台或本轮自动策略重构。预算不足不能标为“最佳教材已确定”。

## 5. 旧一期预算为何不能直接沿用为闭合保证

复用旧方案4search/4Reader/4body操作/8body HTTP、候选8、body预约262144、3基础模型+4Reader=7模型、output16384、durable19、内部cost144000；这些是历史候选，不是本轮授权或有效现金上限。

当前Research以Gap capability逐项处理，Reader的must_teach只包含当前entry remaining，已inspect URL缓存只复用原scope证据。不重新审不存在的outcome refs，也不会自动跨能力扩大覆盖。因此当前六组disjoint缺口在空session/无额外qualified映射下，理想也需要至少 **6次scope-specific Reader判定**。这不等于需要6本教材，也不是证明必须6次搜索。

使用真实187Profile/Plan及正式Coverage/Gap、Fake每组理想全覆盖资源及原默认ResearchBudget，实际发生4search+4Reader+4body，顺序为 `error.permission → eval.lite → llm.api → mcp`。前两组recommended先消费额度，structured.output及tool.calling的 **4个required outcomes仍unresolved**。这是旧范围的综合预算反例，不是隔离Reader-only实验；至少6次scope-specific Reader的结论另由当前must_teach限定本cap、六组互不重合且无新增qualified映射证明。Gap规范化字典序保证确定性，Research直接按此顺序处理，没有required预算优先保护。

同URL反例仅1body/1Reader，只解决首组；之后缓存对新能力缺matching refs直接continue。重复发现同一综合教程不能在现有实现中自动闭合跨能力缺口，不能据“一个资源教多个outcomes”宣称4次Reader足够。4search/4body最坏预约同时限制后续能力发现及读取，单次短正文的standalone settle不能替代durable永久最坏预约规则。

### 最小下一步范围

优先仍保留原Scenario A及真实187Plan，不替换为窄场景、不删除required或recommended。不为预算缩小用户真实目标。本轮建议先完成Owner对权限教学义务的合同决定，并单独评审有界候选比较、required先保障与同URL新outcome补审；任何实现都须另开明确范围，不能自动应用。

后续外部授权至少应区分：八个required缺口的教材及正文审读、两recommended缺口的保留/预算决策、两个covered MCP理论的访问proof装配、候选比较成本，以及最后Curriculum教学质量/完整性验收。仅四个required gap理想各一次审读也会用完4Reader，未留失败候选、比较或recommended余量，不能称完整Scenario A闭合计划。

未来若使用合法owned业务Run，184/187独立应用响应只能作本轮离线来源；不能伪装成新Run已预约/已消费Receipt。合法身份与原root预算必须按现有冻结/dispatch规则确认。若设计仅资料链有界验收而不跑完整Worker，应明确其验证范围，不将结果扩展成端到端Draft/Plan验收。

### 费用范围与风险

本轮费用及外部请求均0。此前第187的CNY0.029378是已核价单次估算，不能预测未来Research现金支出；最近价目/余额不是新的账户授权，也不证明严格现金门禁。

未来模型现金只能以授权时官方价格和实际usage作估算，公式 `input_tokens×核实输入价 + output_tokens×核实输出价`。内部cost_micros不等于人民币；Tavily搜索额度/价格单列，正文请求/Reader/项目检查单列。本轮无法证明未来input token或现金严格上限，旧CNY0.50条件候选不生效。

若沿现有每能力scope、不含比较且理想一次成功，六Reader输出cap合计6144；加新合法完整Run的3基础模型4096上限，output预约至少18432，已高于旧16384。它只是成功下界示意，**不是经过授权或足够比较的最坏预算**。比较/不合格/正文不可读将增加消耗，不能自动将cap调大或拿历史余额保证成功。未来预算须以最终受控执行范围重新核算并由Owner授权；unknown、截断、来源/usage不可信、预算不足保持原STOP/incomplete保护。

## 6. 验证、独立审查及未运行项

| 验证 | 状态 | 实际证据 |
|---|---|---|
| 原184/187原始JSON重建 | PASS | 原Validator、全文/hash与历史应用输出一致 |
| 正式loader身份/版本/审核hash | PASS | 真实本地pack/review固定校验，不是synthetic index |
| Plan→Coverage→Gap | PASS | 12=2covered+10missing；8required2recommended，已知Python排除 |
| 稳定重复/输入不变 | PASS | 原输入canonical前后相同，重复输出/hash相同 |
| local_tool_scope现有拒绝链 | PASS | 现有保护离线复现；不能表示产品complete通过 |
| 权限结构与伪造结果反例 | PASS | 既有3代表测试+ignored8反例；native exit0，闭Schema和server snapshot保护保持 |
| 候选政策与预算反例 | PASS | 真实Application+Fake ports，5候选反例+2真实Gap/Fake研究反例；native exit0 |
| 质量先比较政策符合性 | FAIL | 中文最低合格后提前停止、后续质量未比较；不是实际教材质量FAIL |
| 研究闭合准备 | PARTIAL | 精确缺口已确定，旧4Reader不能闭合、免费proof/比较预算未冻结 |
| 独立收口审查 | PASS | P1独立16检查、P2/P3实际证据及报告反向复核；不代表政策或课程通过 |
| 真实教材、Reader与Curriculum质量 | NOT RUN | 无任何外部调用，未生成真实课程 |
| PG/Worker/React/浏览器/全量Backend | NOT RUN | 复用既有有效技术证据，不重跑 |

本地compute首次检查误用Policy原outcome顺序与Gap规范化排序比较，断言FAIL；只修ignored检查并保存失败日志，重跑PASS。保护inventory首次将全部ledger文件含lock与json-only集合比较，断言FAIL；只修同范围集合比较后PASS。不是生产错误，没有修改原结果或审核资格。P2反例脚本的初始断言与修正记录单独保留，不能把检查脚本失误包装为生产缺陷。

P2精确证据在 `constraint/evidence-manifest.json`、`probe-result.json`、`pytest-exit.json`；P3在 `research/packet.md`、`counterexamples.json`、`real-gap-budget-counterexamples.json`、`exit.json`。这些课程/正文反例均明确标合成，不是新真实课程或教材。

独立收口审查 **PASS**，没有未关闭报告问题。独审从原184/187raw及账本身份重建，执行16项来源/转换检查，含隔离pack/review损坏及缺失拒绝、覆盖重叠/假full/缺refs拒绝；项目 `.venv/Scripts/python.exe` native exit0。复核P2的8probe+3代表测试及P3的7案例源脚本/产物/exit，未重复运行这些矩阵。统一结果在 `review/final-review.md`、`unified-result.json`、`p1-result.json`、`unified-exit.json`，原生退出均0。

独审主动发现并关闭报告R1：研究反例原措辞错误地声称“只限制4Reader”，已按实际默认综合预算改正，6scope下界另列源码条件；不需要重跑案例。独审首次误用非项目Anaconda3.12时，异常构造出现TypeError，原日志/exit1保留 `review/p1-nonproject-python-initial-fail*`；使用项目环境同一拒绝反例正常PASS，没有扩张为异常处理源码修复。独审PASS只批准证据准确性及本轮边界收口，候选比较政策FAIL、Owner决策required、真实课程NOT RUN均保留。

final-audit保护1465个冻结文件，允许变化只有progress；旧响应、账本、正式配置、源码与上位合同hash保持，账本新增0。公开generate503源码/装配未改，复用原证据；本轮HTTP探测NOT RUN。没有push/merge/deploy。

## 7. Owner待决定事项与STOP

1. 是否批准“课程确认核查结构化教学义务及可执行验收；运行权限结果留待实践验收”的最小新版本合同方向。当前课程complete仍不可放行。
2. 是否另行批准有界候选比较及required/跨能力审读的局部收口；当前策略不能支撑质量优先和旧4Reader闭合保证。本轮不实施检索重构。
3. 上述前置通过后，再单独决定真实研究/正文/Reader/课程的请求数量、身份、预算、现金风险及元数据preflight。当前授权全部为0。

**ITEM3_4_REAL_INPUT_OFFLINE_PASS**

**CURRICULUM_CONSTRAINT_OWNER_DECISION_REQUIRED**

**REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN**

**STOP。**
