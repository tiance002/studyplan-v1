# Planning V2 产品验收前置收口

任务：`PLANNING_V2_PRODUCT_ACCEPTANCE_PREP_V1`。日期：2026-10-09。本文准备后续真实验收授权，本轮真实产品模型、网络搜索和 Reader 请求均为 0。正式 `/plans/generate` 不开放。

## 1. 基线、范围和证据复用

- Start/source HEAD：`dc3d60372502a43caf544558ade46cba945aaf0f`，分支 `feat/n1-resource-discovery`。开始 tracked tree clean；只有预先存在的 `.workbuddy/`、`design-preview/` 未跟踪目录，两者未访问或修改。
- 唯一上位合同：[Planning V2 Architecture Contract](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。本轮不改变合同、Item1–9 核心业务、Policy、Prompt、Schema、正式装配、迁移或历史数据。
- 已存在 `checkpoint-item9-clarification-20261009`、`checkpoint-item9-final-20261009`。[澄清续接报告](ITEM9_CLARIFICATION_CONTINUATION.md)、[React 报告](ITEM9_REACT_IMPLEMENTATION.md)及 [progress](../implementation/progress.md)直接复用。当前 19 个 C0–C2 后端证据文件 SHA-256 与原 packet 全部相同。
- 复用既有 119 unit/contract、38 个独立 owned PG case、最终 35 前端测试/build、8 个拦截边界与原 Edge UI 证据；本轮没有重跑这些矩阵。Item8 的预算拒绝、unknown、CAS、取消、fence 及历史保护测试同样复用，不能把复用写成新执行。
- 新证据仅存 ignored `var/planning-v2-product-acceptance-prep-20261009/`：`baseline.json`、`ledger-inventory.json`、`content-evidence.json`、`content-packet.md`、P1 harness/JSON/截图、独立审查和最终保护检查。报告不保存凭据、认证头或教材正文。版本终点由本地 checkpoint/最终交付 SHA 定位，避免文档自引用提交 hash。
- 路由请求：机械账本 Luna medium；有界浏览器及教材分析 Sol6.1 medium；预算/来源/历史独审 Sol6.1 xhigh；主协调按用户 Sol6.1 high 偏好。实际解析均 `NOT OBSERVABLE`，未改全局设置。

### 实际本机账本

| 检查 | 本轮事实 | 状态和限制 |
|---|---|---|
| 本机产品模型 quota | `.git/v2-paid-quota-20261001` 连续 request 1–183，183 results；178 succeeded、5 failed，其中 2 个 `unknown=true` | PASS：文件盘点，不是账户余额 |
| 累计 cap | 最新授权文件为 280，算术剩余 `280−183=97` | PASS：算术；本 Goal 授权仍为 0，不能消费余量 |
| unknown | 第177次 Case3 和第183次最终 Case7，均 `provider_transport_unknown` | 保留，不重派；Case7 不能称为真实语义通过 |
| 搜索 quota | 6 request/6 result；配置 cap1000，算术剩余994 | PASS：文件盘点，非搜索账户余额/资格实查 |
| 其他历史数 | v610 `45/100` 是同一目录旧快照，不与183相加；19个 Run summary 的265 request_count 是另一统计层 | PASS：计数语义区分，不覆盖历史 |
| 配置白名单 | `openai_compatible`，主机 `api.deepseek.com`，模型 `deepseek-flash`，部署输出8192；Tavily；两种 key 仅记录 SET | PASS：本地配置读取，凭据有效性未验证 |
| 账户余额、实时价格、网络权限、正式 PG attempts | 本轮禁止真实外部调用/正式库访问 | NOT RUN；不能由 SET、quota 或旧余额替代 |

完整请求身份、授权文件、来源路径及 hash 见 ignored ledger packet。本次不修改其任何历史文件。

## 2. P1 Semantic Replanning 成功补证

真实 owned PG/Worker/HTTP/Edge 成功链 PASS；独立复核见第6节。只完成一个初始root和一个合法Semantic后继，没有生成第三个业务Run。

场景仅验证集成：用户已会 Python，已有本地 JSON 待办 CLI；Revision1 学习可靠的 JSON 文件处理，Revision2 真正改变为 asyncio 取消与并发。两轮的 B 类能力分别为 `json.cli` 与 `python.async`；相同 `python.core` 保持 accepted_known。保留同一已有项目、免费教材、既有接口及数据限制。

外部端口全部显式 Mock，资格为合成测试证据，界面实际标明合成资料。本例不证明真实教材或模型语义。使用真实 owned PostgreSQL、Postgres checkpoint、既有 Worker、实际 HTTP Cookie/CSRF 和 Edge，不用拦截响应替代业务链。

预算装配原样复用已经验证的 Item9/C2 owned harness：`max_output_tokens=131072`、`max_total_requests=50`、`max_cost_micros=1000000`；searches4、readers4、candidates8、body262144 保持。这是原受控测试装配，不是改 `ResearchBudget` 字面默认、不提高 cap、不修改数据库预算值。新 Semantic Run 必须继承原冻结 budget root 和已用额度。它不能证明尚未装配的正式 V2 预算充足。

| 实际步骤 | 证据结果 |
|---|---|
| 新用户、新owned两库、初始完整Draft→浏览器明确确认Revision1 | PASS；初始root `run_8e3acecf908f4fbab36db2040baa31cb` succeeded |
| 目标改变、补充事实保留、同root新Run→新完整Draft→明确确认Revision2 | PASS；Semantic Run `run_b7a6ad41555153ac8e077aa35d959e5b` succeeded，B类实际由json.cli变为python.async |
| 刷新、退出/重新登录、current/history | PASS；current v2，history v1；Edge截图01–07及完整HTTP响应/断言 |
| 原Plan/source/version内容 | PASS；旧Plan合法approved→superseded，其他公开字段完整相等；两次manifest/budget冻结并存，不覆盖旧版本 |
| 旧学习事实/成果 | PASS限定范围：通过真实公开API建立的in_progress exposure、保存的summary原文及rubric/source snapshot，重规划后完整不变；新版本exposure未记录，不继承旧掌握 |
| Practice成果及summary模型评审 | NOT RUN；saved summary不是已审核成果，也没有冒称Practice artifact |
| shared root实际累计预约 | search2、Reader2、candidate2、body131072、output22528、total14、cost162000（内部单位）；全部≤原受控cap，已用额度不归零 |
| Fresh PG及服务停止 | PASS；`pg_readback.py`、`final-readback.cjs` exit0；8059/5199 ECONNREFUSED |

新业务库 `studyplan_test_prep_p1_904c982d`、checkpoint库 `studyplan_test_prep_p1cp_799d146e` 保留。另保留启动失败产生的空owned两库，不删失败痕迹；未使用正式库或旧Item9测试库。`p1/pg-readback.json`包含实际Run、submission、attempt、reservation、Plan、summary、exposure和checkpoint读回。

本例两轮source_id/URL/material_id不同，但合成source_version字符串相同。证明的是原json.cli来源快照及plan/revision1保全、新python.async来源独立且不继承学习事实；不证明同一真实教材的版本升级、正文变化或审核失效，这些边界只复用Item8既有保护。

原启动/脚本失败：sandbox 服务不可达、启动时多产生一对无 Run 的 owned 库、浏览器登录前失败、SessionView 键引用错误、locator错误、PG读回列名错误，以及历史状态 approved→superseded 的不当全对象比较。只调整 ignored harness；不新增业务重派来追 PASS。locator/status失败完整JSON保留；最初project-key失败完整JSON被一次harness重试覆盖，确切错误只留工具回执及明确标记的转录 `harness-failures.json`，不能称全部早期失败原始JSON均保留。初始Draft/确认截图与实际PG/receipt仍在，不影响成功链的事实证据。

## 3. P2 固定代表输入与验收矩阵

以下为后续真实验收的固定合成 GoalSpec；不得把期望输出写成 Fake 金标准再宣称语义通过。调用时必须冻结原输入、request identity、模型参数及所有来源。不同场景不复用 historical unknown 的身份。

### Scenario A：优先的真实 Agent 语义代表

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

MCP 的系统性学习要求是课程政策，由 Policy 注入而非预先伪造用户需求；不把它强制加入用户 CLI。研究 query 不含私有项目上下文。

### Scenario B：复杂专项

```json
{
  "target": "我想学习并开发一个个人多模态 RAG 知识库，支持检索自己的文字资料和图片，并给出可检查的回答依据。",
  "starting_point": "会 Python 基础；没有系统学过 RAG 或多模态检索。",
  "scope": ["文字与图片资料的个人知识检索", "回答依据", "有界成熟项目源码切片学习"],
  "desired_depth": "applied",
  "outcome_purpose": "learn",
  "constraints": ["只使用合成资料进行本次验收", "项目源码学习限定必要切片，不要求通读或运行整个仓库"],
  "project_context": "准备逐步实现个人知识库，希望各阶段在同一项目上持续增加能力。"
}
```

### Scenario C：窄基础应用

```json
{
  "target": "我只想用 Python 完成 JSON 文件读写、异常处理及本地数据统计 CLI，学习资料正文必须免费。",
  "starting_point": "已能使用 Python 函数和基本容器；JSON 文件读写和异常处理仍需学习。",
  "scope": ["本地 JSON 文件读写", "异常处理", "统计结果与 CLI 失败出口"],
  "desired_depth": "applied",
  "outcome_purpose": "learn",
  "constraints": ["学习资料正文免费公开可读", "仅使用本地文件与 CLI", "不扩展到 Agent、RAG、MCP 或云服务"],
  "project_context": "一个读取 JSON、计算字段统计并写出结果的本地 CLI。"
}
```

| 场景 | 必要行为 | FAIL 判据 | 当前真实质量 |
|---|---|---|---|
| A | Python accepted_known 不进新学习集合；自己的 CLI 从 Profile→Capability→Curriculum→Draft/Revision 保留；结构化/工具能力按实际目标及先修选择；systematic MCP required 和 project_usage 分离；连续实践有增量/产物/验收 | Python复习或测试、强制新项目、强制CLI接MCP、漏硬限制、凭标题覆盖、缺教材仍 complete | NOT RUN |
| B | 未知领域必须经现有可信定义/先修门禁；教材章节证明所需 outcomes；Project Study 有界源码行为证据；用户项目持续增量 | Fixture RAG ID冒充真实审批、固定职业模板、README冒充源码审核、编造文件调用链、孤立练习冒充连续实践 | NOT RUN |
| C | 保留读/写/异常/统计及免费正文；已有函数/容器不机械复习；教材章节与实践可执行，资格不足 incomplete | 只读课程替代写入/统计；把部分Python声明当全部掌握；引入Agent/MCP/RAG/云；免费URL代替免费正文；缺资格仍确认 | NOT RUN |

三场景输入结构离线验证 PASS，尚未运行真实 Analyzer/Planner/Reader/Composer。本轮没有构造全套人工课程。真正冲突沿用 Item1 Case5 的真实响应及既有离线保护，不重新收费。

## 4. P3 当前真实教材资格与缺口

只读检查受控覆盖索引、保留审核报告和研究消费者，未重审整套 Seed、读新公开教程或建立内容库。结果是本机冻结证据，不是当前正式 PG catalog 状态。

真实受控索引 `planning-v2-reviewed-v1`，hash `0e0ca1a7fffc0d3b4d5cdcadfbb55ec7434d7a4dfa1b805e73fd80f985434fe6`：`agent.application` v8 → source `src_mcp101_a7ca881ee83ac722491299cd` v2 → section `sec_mcp101_09e62ff389cb388eb744e738`（MCP10.2）。保留审核范围为 `selected_sections_read`。只有 `mcp.roles`、`mcp.interfaces` 有明确对应正文审核，不能扩展到 `mcp.minimal_connection`。文档/pack hash 不冒充教材正文 hash；未执行教程示例也不冒充已运行。

| 场景/能力 | 已有真实支持 | 尚缺的证据与边界 |
|---|---|---|
| A systematic MCP | roles/interfaces covered；第三项 missing，因此 partial | 最小接入实践须有单独章节正文/Reader范围证据，不能由MCP标题继承 |
| A structured.output/tool.calling/llm.api 等实际选中B | 当前受控 mapping 无对应覆盖 | 免费或合法访问的教学源→精确正文→Reader outcomes证据；不能从已有CLI推断工具能力已掌握 |
| B RAG/多模态 | 当前12项Policy无对应核心定义；未核实真实可信领域批准 | 先补可信领域定义/先修授权证据，再研究章节；Item6 RAG代表是合成，不能搬其身份 |
| C json.cli/python.core 的实际B | 当前受控 mapping 无覆盖 | GitHub免费正文/Reader可能是最小资料链；json.cli目前只有读/校验/CLI错误，写入及统计需求是否有合法表达需定向判断 |
| 成熟项目 Project Study | 现有目录/候选卡不能单独证明 bounded_reviewed | 精确版本、源码切片、输入输出、正常/失败路径、取舍和可检查产物；本轮此语义审核NOT RUN |

资格等级必须分开：

1. 真实已审核的限定正文，只支持其实际 outcomes。
2. Seed、发布标识、来源/章节目录、README 审核仅证明各自范围。
3. GitHub/Web 搜索结果是候选，不能自动当教学章节；Tavily/Web 当前仅发现能力，不自动提供可读正文。
4. 历史教材/旧包保留其版本和原审核范围；TOC/index 不能继承新版正文资格。

`ResourceResearcher._reviewed` 还要求 source/version、content hash 和 `ReviewedAccessProof` 免费访问身份匹配；Coverage 的 reviewed 不等于本次免费/可访问要求已满足。该真实索引的 loader 和 `_qualified_mappings` 离线核查 PASS；实际 runtime catalog、免费访问 proof 实时状态、正文 Reader 与项目源码审核 NOT RUN。

优先 **A 作真实语义代表**；它可能超过四次 Reader 能够闭合的资料范围，必须先冻结真实 CapabilityPlan/gaps 后判断预算。**C 是最短资料链候选**，但不能偷偷删掉写入/统计、扩充Policy或忽略部分已知能力来让它通过。C 是否存在合同级阻塞目前仅为风险，未实际执行Planner，不预判必须改架构。B 暂不纳入最小外部调用批次。

合法 incomplete 反例采用 **A + 当前真实受控索引 + 禁止新增资料资格**。预期 MCP partial、其他实际选中B none，required missing保留，不能确认为完整课程。这是可执行的未来反例方案，不是本轮真实模型输出。

## 5. P4 最小真实调用方案（待 Owner 单独授权）

### 5.1 装配与预算前置风险

`OwnedV2PlanningRuntimeFactory` 仅允许 loopback `studyplan_test_` 两库，预算/Provider/来源由服务器依赖冻结，HTTP 用户不能指定。正式 V2 装配仍关闭；旧 `PersonalPlanningRuntimeFactory` 的 outline/structure/practice 不是可复活的替代链。

`ResearchBudget()` 字面默认 output4096、total16、search4、Reader4、candidates8、body262144、cost100000。独立本机有效参数核实：practice默认4096、deployment8192、官方模型软件cap393216；`OpenAICompatibleLLM.request_options`取各上限的min，Goal/Capability/Curriculum实际均4096，Reader1024。manifest默认允许上限8192不等于每次Provider实际4096。literal budget可预约首个Goal4096，但第二个Capability累计预约会超额拒绝；最坏资料批次还需19外部请求及内部cost144000，均超过literal的16/100000。不能通过改 cap 或自动减少必要能力追求 PASS。

后续必须核实并由 Owner 冻结已有合法受控装配与产品预算绑定。本轮 P1 原 owned131072/50/1m预算只证明那个测试装配，没有把 literal default 修正为正式预算。本轮未更改任何配置或 cap。

### 5.2 最小一期：只运行 A 的一个新 acceptance/root

先进行授权内的免费 preflight：有效凭据、官方模型/请求参数、endpoint guard、余额、现价、最新账本、真实资料端口、来源资格和预算绑定。它也属于外部请求，本轮 NOT RUN。不得要求用户贴 key。

| 阶段 | purpose/端口 | 最大新增请求 | 继续门禁 |
|---|---|---:|---|
| 先判目标/能力 | `planning.goal_requirement_analysis`、`planning.capability_planning` | 2模型；当前各output≤4096 | Profile合法、Python/项目/硬约束保留；无澄清、无未批准领域；冻结B与gaps |
| 教材研究 | GitHub优先、Web只作候选发现 | 搜索合计≤4；≤8候选 | 真实查询只含获准公共教学描述；不得外发私有项目 |
| 正文取证 | Github body read | ≤4次body操作，每次最多2HTTP/65536 bytes；总HTTP≤8/body≤262144 | 身份/版本/许可/可读正文合法；读取正文短暂使用，不进报告/receipt全文 |
| 正文语义审读 | `planning.research_reader` | ≤4模型，每次output≤1024 | 精确正文chunk/source绑定、outcome范围、限制说明；Reader已含在模型总数 |
| 组织课程 | `planning.curriculum_composition` | 1模型，当前output≤4096 | unresolved required不能伪造 complete；输出可依法持久化完整性状态 |
| 编译/确认/回读 | deterministic Compiler、owned PG/HTTP/浏览器 | 0模型/搜索/Reader | 完整Draft才可人工明确确认；freshreadback/history和学习事实版本隔离 |

**本期提议总上限：7产品模型（含4Reader），4搜索，8正文HTTP。** 三个基础模型加搜索、正文、Reader最多19个 durable外部请求；不把7+4Reader算成11，也不把正文2HTTP算成一次。当前有效配置最坏输出 `3×4096+4×1024=16384` tokens。内部cost预约上界 `7×20000+4×1000=144000`，不是人民币。候选上限8仍受原预算保护。当前owned durable路径每次body永久累计至少65536 bytes预约，不因实际正文较短而退回，body262144因此最多4次body操作/8HTTP；不能用standalone ResearchSession实际结算回退的逻辑替代这个durable证明。

先2模型后门禁不意味着重开root、重置预算或向新请求身份转移剩余额度。若 actual gaps 在原合法额度内无法闭合，只记录 incomplete；不得自动追加本期额度。现有研究器可能对明确未读/不适合候选继续尝试；若 Owner 要求首个失败即停止，须在受控执行前证明该停机门禁可实现，不能把计划文字当成已实现的通用开关。

执行前另有待证明门禁：当前 `V2PlanningRuntime.execute` 在Goal/Capability后自动进入Research，没有证据表明可在这个位置安全暂停以等待人工/独立语义review，再保持原身份/root继续。本表的“两模型后复核”是拟议验收分段，不是已实现接口。若既有受控装配不能安全提供该暂停或dispatch前门禁，不能按表直接开始收费；须报告精确缺口、另行评审最小受控执行适配，不能靠改budget、制造failed再重派或重置root实现。

**不在本期额度中：** B 的领域正文验证（每次正文操作预约2HTTP/65536 bytes，批准后额外一次 `capability-verified` 模型调用；B全场景总上限未规划）、后续澄清轮、第二个Scenario、Semantic二次真实生成、ProjectCase搜索/inspect（另有最多3HTTP预约）。遇到这些需求应停止并报告新范围，不删课程所需事实，也不绕过原Validator。域正文验证本身不是另一个LLM Reviewer。

C 如被选择为一期代表，替换 A 的本期额度而非额外叠加；必须先有合法表达其完整目标的证据。现有受信领域扩展可以原则上提供distinct窄能力/outcomes（不覆盖旧身份，必须有服务器受信source、正文和issued approval），因此C不被证明绝对无法表达；但若为C使用该机制，其额外验证不在本期额度。python.core现有A/B按整体能力，标B会包含函数/容器/异常全部outcomes，标A又可能藏异常缺口，需要真实结果逐项判断，不由Validator自动证明语义正确。B 在可信定义与源码审核资格未准备好前不提议收费执行。A incomplete反例优先用同一冻结输入/真实索引的离线/已保存响应消费，若要另发模型就须另列额度。

### 5.3 Token 与费用：可证明边界和条件估算分开

程序可以证明上述 output预约上限；**现有 ResearchBudget 没有 input-token cap，Provider返回 cost_micros=None，内部 cost_micros预约也不等于账户人民币费用**。因此当前无法证明一次完整真实批次的现金最坏上限。Reader正文最多16384 UTF-8 bytes不等于完整请求tokens（另有prompt/目标/Schema）；Curriculum完整上游payload不可用 chars/4估计冒称token硬上限。

本地保存的2026-10-08官方价格快照：高峰未命中缓存input CNY2/百万、output CNY8/百万；低峰分别1/4。本轮没有查询当前价格；旧余额CNY1.97不是当前余额。以下只是**基于历史高峰价的条件测算**：

- 若未来确证每个实际请求 input≤16384 tokens，7请求最大input114688、output16384，条件费用 `114688×2/1e6 + 16384×8/1e6 = CNY0.360448`。
- 两个前置模型条件input32768、output8192，条件费用 CNY0.131072。
- 对任意实际总input `I`，历史高峰条件式为 `2I/1e6 + 0.131072`。缓存优惠不计；更高现价、额外调用和搜索服务计费不包含。

可供 Owner 评审的**候选模型现金限额 CNY0.50**，仅在当前官方价格、余额、准确token计数及每dispatch的input≤16384门禁全部得到证明后才可采纳；不是已生效cap、不是当前可信现金保证。若无法在既有接口和授权范围内证明入站token/费用停机保护，停止收费验收并报告，不自行开发通用费用平台或修改正式预算。Tavily本期最多4请求的账户费用/credit、免费preflight的真实请求数及GitHub访问配额当前 NOT RUN，须单独查明并纳入 Owner 授权；模型CNY0.50不能包含未知搜索费用。

### 5.4 停止条件与独立两层验收

unknown、timeout后结果不确定、truncation、Provider状态不明立即停止整个批次；保留身份/最坏预约，不retry/repair、不换收费模型、不新root绕过。预算不足、正文不可读、来源/许可/版本不合格、领域资格缺失或required资料不能闭合时，按真实分类保留 incomplete/拒绝；不伪造确认。正文不可读/资格失败能否首个即停须在执行门禁预检中核实。Owner批准之前任何余额/价格/网络验证也不执行。

| 层次 | 独立审查内容 | 证据和判定 |
|---|---|---|
| 程序正确性 | Schema/Enum、refs/hash/source版本绑定、冻结预算预约/结算、未知不重派、required完整分区、Draft完整性、事务/CAS/freshreadback | 原始真实响应、Validator、预算/receipt、PG实际读回；PASS/FAIL/NOT RUN，Mock不能代真实Provider |
| 教学质量 | 目标与已有基础、教材实际内容/章节范围、能力先修/顺序、自己项目连续增量、源码研究切片与最终产物验收 | 独立开发审查代理读输入/真实输出与必要正文证据；Owner实际阅读评审；PASS/PARTIAL/FAIL/NOT RUN，不让被测模型自己裁决 |

关键硬约束/已知基础/必要Outcome遗漏、虚构覆盖或不合格资料为FAIL；有正确可用部分但缺关键资料为PARTIAL并拒绝完整确认；真实阶段没执行为NOT RUN。没有新评分模型或评测平台。

## 6. 收口、独立审查及待授权事项

独立Sol6.1 xhigh代理从源码、冻结合同、实际PG/HTTP JSON、manifest重算和截图复核，不采纳实施者自报PASS。P1两个合法Run/共同root/预算原样保留、summary原文hash、source/rubric版本及exposure隔离均通过；真实Practice artifact和模型summary review保持NOT RUN。

独审发现并关闭的报告问题：B/C purpose非法值改为learn并重新构造三份最终GoalSpec；Reader purpose纠正为planning.research_reader；区分manifest8192与当前有效Provider4096并收紧token/条件费用；C未显式write/stat outcomes不夸大为绝对合同阻塞。另对body次数审查：standalone session可退回actual，owned durable却保留每笔最坏65536；根据后者源码和PG预约证据确认最多4次body/19total，未放宽预算。只修改报告/ignored证据，无生产Bug修复。

| 前置工作 | 最终判定 | 实际证据/限制 |
|---|---|---|
| P0基线/本机账本/既有成果复用 | PASS | HEAD一致、19后端来源hash一致、938原tracked基线；账户/正式PG NOT RUN |
| P1单条成功集成 | PASS | 真实owned PG/Worker/HTTP/Edge；仅显式Mock，真实教学质量不在PASS范围 |
| P2代表场景设计 | PASS | A/B/C最终GoalSpec合法、预期及关键失败判据明确；实际真实输出NOT RUN |
| P3真实教材准备度 | PARTIAL | MCP两项可信覆盖；三场景资料均未闭合，catalog实时资格/新正文审核NOT RUN |
| P4请求/token范围设计 | PASS | 7模型含4Reader/4搜索/8bodyHTTP/19durable/output16384，限定无领域/项目案例额外请求的owned路径；分段语义暂停/停机实现仍是执行前条件 |
| P4现金/搜索费用硬边界 | PARTIAL | 历史价条件算式明确；input硬cap、现价/余额/搜索credit NOT RUN，执行前阻断 |
| 最小public generate保护 | PASS | 现有storage-denied/in-memory API用例新执行1 passed，HTTP503且storage调用0 |
| 正式产品/真实教学质量验收 | NOT RUN | 本轮未授权外部请求，不能把前置收口当产品接受 |

准备报告完成，真实产品验收仍 NOT RUN，不宣称Planning V2已可用。

Owner 后续需明确决定：

1. 一期代表是否采用优先A；是否同意新acceptance/root、最多7模型（含4Reader）、4搜索、8正文HTTP，并明确免费preflight和搜索计费范围。旧177/183绝不重派。
2. 哪个现有合法受控预算装配可用于真实一期，input/现金保护是否可证明；在价格/余额/费用单位/搜索额度未实查前，不将条件CNY0.50当无条件硬保证。不增加累计cap280、不充值。
3. C目标粒度/部分Python已知是否需后续有界核实，B可信领域/源码审核另行准备；本轮不提前修改核心Policy。
4. 真实响应经独立两层审查，Owner完成教学内容与体验验收后，再决定正式入口授权。此准备任务不授权启用 `/plans/generate`。

本地提交仅报告及progress，源码修改0。最终保护检查PASS：原938 tracked中的937文件逐字节hash保持，progress旧历史bytes完整保留，`.env` hash及378模型/12搜索账本文件集合hash保持；证据JSON无凭据/认证字段，文档链接合法。`git diff --check`结果随本地checkpoint回执保存。不push、merge、deploy。完整Backend、原正式PG、真实外部接口、真实教材正文、真实产品语义和全套浏览器矩阵本轮 NOT RUN。

`REAL_PRODUCT_ACCEPTANCE_NOT_RUN`

`PUBLIC_GENERATE_NOT_ENABLED`

`WAITING_OWNER_EXTERNAL_CALL_AUTHORIZATION`

`STOP`
