# Planning V2 — Item 7 P0 上游最小修复

日期：2026-10-08。

状态：`ITEM7_P0_CONSTRAINT_BLOCKERS_RESOLVED`、`ITEM7_P0_UNKNOWN_DOMAIN_STRUCTURAL_PATH_RESOLVED`、`DOMAIN_VERIFICATION_LIVE_PENDING`、`ITEM7_P1_P3_NOT_STARTED`、`STOP`。

## 1. 基线与保留事实

- Start HEAD：`5ca50020864bae52475fd0318a35677bb7ef203f`；分支 `feat/n1-resource-discovery`。
- Final HEAD：本报告随 `fix(planning): unblock v2 constraint and domain research` 本地提交；精确 SHA 见最终答复及 ignored `var/planning-v2-upstream-unblock-20261008/final.json`，不在报告内制造自引用提交 hash。
- 开始时仅有预期的 `docs/implementation/progress.md` 修改及未跟踪 `docs/planning-v2/ITEM7_PLANNING_EXECUTION.md`；逐项核对，原 P0 报告字节/hash 不改，旧失败和 STOP 结论保留。`.workbuddy/`、`design-preview/` 未访问、修改或提交。
- 以架构合同为上位权威；本轮只修用户批准的 Item2 验证接入、Item5/Reader 约束与扩展定义消费、Item6 约束消费。没有修改 GoalProfile 冻结语义、Policy v2 的 12 个能力/27 个 outcomes、Item3 映射、Item4 语义、Seed/审核资格或架构合同。
- 不实施 Compiler、Manifest、数据库持久化、Worker、公开生成或 Item8；不 push、merge、deploy。

## 2. 原始 RED 与新增反例

原始 P0 的两个确定性条件：

1. Item5 `profile.hard_constraints` 非空即每个 gap 返回 `constraints_pending`，在已有 reviewed/free 资料复用之前阻断。
2. Item6 `unresolved or unfilled or payload["constraints"]` 非空即强制 incomplete，无法区分已满足限制。
3. 未知领域虽有 Item2 证据结构，但没有受信来源 producer；Item5/Reader/Item6 公开查询仅允许固定 Policy，合法扩展不能安全贯通。

本轮保留的离线日志：

| 验证 | RED | 修正范围 |
|---|---|---|
| 约束/真实本地 MCP 代表 | 7 FAIL / 11 PASS | 免费证明复用、全覆盖可 complete、已有 carrier、只读/联网的步骤边界 |
| 课程禁止联网反例 | 1 FAIL | Composer 在模型和案例派发、预算预留前拒绝 |
| 领域来源与 Reader/Provider 初始合同 | 22 FAIL | 受信源 pin、审批、公开投影、Provider 本地审批注入 |
| 直接 Provider 绕过约束 | 4 FAIL / 36 PASS | 复用同一确定性 dispatch guard，不能只在上层阻止 |
| 独立审查：失败来源重复核验 | 已派发 2 → 4 HTTP，同 session 未封停 | 一次验证派发标记、失败/成功均不再次派发 |
| 独立审查：整份 Plan 一致替换 | action → 同来源未选 topic，重算 hash/同步 must_teach 后仍获准 | 服务端批准绑定真正当前 frozen Plan hash，不能只核对 JSON 自算 hash |

日志和完整合成证据位于 ignored `var/planning-v2-upstream-unblock-20261008/` 与 `var/planning-v2-item7-p0-unblock-20261008/`。它们不包含真实秘密，也没有修改旧 P0 或历史付费证据。测试脚本字段断言曾误用 `LLMFailure.code/error_code`，修正为既有 `error_class` 后通过；不把此测试脚本问题当生产缺陷。

## 3. A：有限约束适配

新增 `backend/app/domain/planning/constraint_adaptation.py`。它是版本化的**完整表达闭集**与确定性事实检查，非自然语言分类器：只对列明的完整短句选择检查；不进行 substring/宽泛关键词匹配，不使用模型判定 satisfied。组合、陌生或歧义文本继续 pending，用户原文和 source_refs 不改。

例如“免费教材”“只使用免费教材”“教程免费”选择访问证明检查；不是见到“免费”两字就认定满足。`ConstraintAssessment` 保留 constraint_ref、原 source_refs、业务 scope、satisfied/not_applicable/pending/violated、evidence_refs、reason、policy_ref。

| 条件 | Item5 行为 | Item6 最终行为 |
|---|---|---|
| 已知明确免费要求 | 允许进入原 reviewed/catalog/free-proof 与正文检查；缺证明/付费不能 resolved | 最终所有选中教材必须 usable 且 confirmed；检查后才 satisfied；未选材料的证明不借给选中对象 |
| 不重新创建演示项目 | 对教材发现不适用，不阻断；仍保留原约束 | 必须实际 user_project、description 精确保留 project_context；Starter 违反/缺项目证据保持 incomplete |
| 只读/禁止自动修改代码 | 不必阻断教材发现 | 当前 Task 文本不能机械证明只读行为，仍 pending，不能 complete；未添加文本关键词过滤伪造满足 |
| 禁止联网/外部调用 | 仅本地 reviewed 复用；有剩余缺口时 network_forbidden，不派搜索/正文/Reader | 外部 Composer/Provider 在预留与派发前拒绝；下游运行限制未验证仍 pending |
| 强制中文教材 | 缺少可信语言证明时 pending，不以标题或 Reader 自报语言放行 | 保持 incomplete；未新增语言判别模型或平台 |
| 中文优先偏好 | 原有中文候选优先顺序保留；不误升为必需技术能力或 mandatory access 条件 | 明确记录为非强制资格条件，不冒称已证明所有教材为中文 |
| 其他/真正冲突的表达 | constraints_pending，零外发 | pending，不删除或自动解释冲突 |

范围限制是明确的：本轮支持有限常见表达，不宣称任意自然语言硬约束已经可安全自动适配。只读行为、强制语言等缺少结构事实时保守 pending 符合本轮授权，未修改 Item1 Schema。未来需要扩充表达或事实时应有界评审，不能放宽成“未知约束默认满足”。

Research 原有“教材免费”产品政策及受信来源检查保持；即使用户没显式写免费，付费或访问未知材料也不会成为合法 resolved 教材。

## 4. B：Item6 消费实际检查结果

`prepare_curriculum` 继续消费实际 Coverage、精确 Gap/Research 绑定、catalog、review records 和 free proofs。Validator 根据**实际被 assignments/knowledge 选中的材料**与实际 carrier 计算约束结果。

完整性判定改为：未解决 outcomes、未选择必要案例、pending/violated 约束才要求 incomplete；不再仅看硬约束列表是否非空。结果由服务器写入 `compile_context.constraint_assessments`，模型的输出 shape 没有该字段，模型新增 satisfied/删除 constraint_refs/修改来源均拒绝。

没有把某步 not_applicable 当全局通行证：已有项目限制仍检查实际 carrier；只读、联网限制仍等待其对应事实。额外 ProjectStudy case 的 bounded behavior review 本身没有免费访问证明，不能借普通教程 free proof 放行，存在此类 case 时免费适配保持 pending。未因此修改 ProjectCase Schema 或降低教学资格。

Item6 专用 Prompt 仅补充与服务器消费一致的说明：约束非空不必然 incomplete，免费材料和原项目必须有实际证据；无法证明的只读/联网/强制语言仍 incomplete。required outcome、prerequisites、Practice、ProjectStudy、来源/版本保护保留。

## 5. Free / Existing Project 正反结果

使用实际 `load_reviewed_content_index()`、MCP v8 已审核 roles/interfaces、真实 `source:2` 身份及与现有文件 hash 绑定的 `free_public` proof。仍以 `review_record` 为 hash_scope，不伪造新正文审核资格，不覆盖 minimal_connection。

| 代表 | Research / Coverage | 合成 Curriculum Validator |
|---|---|---|
| 无免费限制 | 原合法 reviewed/free 复用保持 | 原路径保持 |
| 明确免费要求 + 可信本地 review/free proof | resolved；零外部派发 | complete；原教材及约束/ref 保留，satisfied 引用实际选中 material IDs |
| 已有 MCP 概念 full Coverage + 免费 | Gap 空、Research entries 空；不重研已覆盖 outcomes | complete；不因免费限制强制 incomplete |
| 免费证明缺失/unknown/paid | 不 resolved | incomplete，不能删除 unresolved 或虚构免费 |
| 不新建演示项目 + 已有待办 CLI | reviewed 教材研究不阻断 | user_project，原 description 保留；MCP project_usage=excluded 使用 micro_exercise；可 complete |
| 不新建演示项目但没有已有项目事实 | 不因该约束阻断教材发现 | Starter 无法满足，保持 incomplete |
| 只读/无可信语言/歧义冲突 | 保留对应范围限制 | pending；模型自报满足不能放行 |
| 免费教程 + 另一个缺访问证明的 ProjectStudy case | 教程原证明不改 | incomplete，不把教程证明借给案例 |

这些是实际程序接口与真实本地审核索引的机械验证。课程文本、能力选择、外部候选与 Reader 语义仍为合成 fixture，不等于真实教学质量通过，也不宣称完整 Case A/B 路线已验收。

## 6. C：同一受信扩展定义贯通

### 6.1 实际来源 producer 与两阶段批准

新增 `backend/app/application/domain_verification.py::DomainVerifier`，复用实际 `GitHubTeachingBody` 及其安全传输，不新建搜索或 Reader 平台。

服务器提供 `TrustedDomainSource`：来源 ID/版本、官方仓库、commit、允许文档路径、blob/body hash、经受控审核的 CapabilityDefinition、公开 outcome 许可、检查局限。只有服务器注册的一个固定来源可读；不将用户目标或私人项目拼成 query，不无限搜索或递归研究。

读取上限为 2 HTTP、65536 wire bytes、16384 正文字节、15 秒 aggregate deadline；限定 README 允许的固定文档，验证源身份/commit/blob/body/chunk/location 后才签发。复用 ResearchSession 预算预留/结算，unknown 保留 pending 与预算占用，观测超额只抬高计量下界；临时正文 finally 清除，不进入审批、状态或报告。

批准有两个明确阶段：

1. 来源批准绑定 Profile hash、verification input hash、完整来源/版本/pins、定义和局限，供 Item2 消费。
2. Item2 冻结实际 CapabilityPlan 后，由服务器绑定其精确 plan_hash，形成下游批准。Reader/Research/Curriculum 只接受与该真实 Plan 一致的批准，不能从 JSON 重算一个新 Plan hash 自证范围。

`DomainApproval` 私有进程内 issuer 绑定完整原始 digest；默认直接构造、source_verification 字符串、自改字段或 source/evidence 一致伪造都不能签发/重绑定。不是通用签名或持久化平台。所有批准对象由服务端注入，不从模型 JSON 构造。

同一验证会话派发后有一次性标记；已派发失败、pin 不符、成功以及恢复该标记后的调用都不能再次派发。输入拒绝、无注册项或未获预算时保持零请求。实际持久成功 Receipt 恢复仍由后续 Item7 负责，不能用重新发网请求替代。

### 6.2 共享解析与正式 Provider 门禁

`backend/app/domain/planning/domain_verification.py` 复用 Item2 `_definitions` 和既有 frozen Plan validator，统一提供 `public_outcomes`、`reader_authority`、`public_outcomes_from_authority`；不维护三套不同的未知能力词典。

Item5 仅对当前 frozen B 的获准精确 ID/text 形成公共教学需求；没有公开许可仍 public_descriptor_unapproved、零搜索/正文/Reader。A 不变成新学习缺口。Reader authority 只有冻结 Plan、批准 hash 与必要 fixture 标记，无 raw goal/project_context。

Reader 和 Curriculum 的实际 Provider preflight/输出校验都消费服务器注入的同一批准对象，并检查 Plan/来源/版本/ID/text/当前学习范围。fixture 可用于显式离线结构检查，正式 Provider 默认拒绝；单有 source_verification 标签或自报 authority 也拒绝。源内未选能力不能通过整体替换 Plan + 重算 hash 获准。

`OpenAICompatibleLLM` 只增加批准依赖及上述 preflight/Validator 接线；没有新增 Provider、改模型/endpoint/费用 cap/重试上限。直接 Capability/Curriculum Provider 调用也复用约束 dispatch guard，不能绕开上层禁止联网门禁。

Item6 冻结必要 domain authority 于受保护 compile_context，条件案例查询复用获准公共描述；模型不能新增定义、来源或课程目标。

### 6.3 未知领域正反例与 LIVE_PENDING

合成官方 ROS2 registry/响应经实际 GitHubTeachingBody + MockTransport、来源 producer 与绑定批准，贯通 Item2 → Coverage none → Gap → Item5 → Reader → Item6 complete。真实 Provider adapter 的 Reader/Curriculum 调用也以 MockTransport 验证；公共查询和 Reader 输入没有合成私人标记 `PRIVATE_PROJECT`。

未批准公开描述、fixture-only、未签发或篡改来源/版本/input hash/outcome/Plan/审批对象均拒绝或保持 unresolved，不删 required outcomes。已知 Policy 不被覆盖；accepted_known 和系统性 MCP/项目用途分离的既有回归保留。

**DOMAIN_VERIFICATION_LIVE_PENDING**：没有配置生产官方 registry/pins，未进行真实联网、技术事实审核或模型语义验收。来源字节/hash 与注册表绑定只证明身份一致，不证明注册表的学习结果/前置在技术语义上必然正确；生产 registry 仍须有来源可靠性、版本、范围及语义审核。

后续 Item7 Runtime 还须接通必要未知领域触发、真实来源配置、统一 Run 预算、持久 dispatch/receipt、取消/fence 和从成功 Receipt 重建批准。当前进程内 issuer 不能作为重启恢复事实；不得重派成功或 unknown。这里已有可调用且以实际安全适配器 Mock 验证的 producer，仍不冒称在线官方验证已经完成。

## 7. 验证与独立审查

范围仅新约束/领域反例、受影响 Item2/5/Reader/6/Provider/JSON 与最小 public fail-closed；不跑全 Backend、真实 PG 或浏览器。

| 检查 | 结果 | 范围/限制 |
|---|---|---|
| 新约束定向 | PASS，22 项 | 真实本地 MCP 索引/free proof + 合成课程输出 |
| Research/Curriculum/Provider/JSON/fail-closed 包 | PASS，260 项 | 最小公开 generate 仍 503、零 storage access |
| Domain + Item2 + Provider 包 | PASS，150 项 | 初始 Domain40 + Item2 57 + 受影响 Provider53 |
| 独审修复后 Domain/Provider | PASS，98 项 | 最终 Domain45 + 受影响 Provider53；含原3个 RED 反例和新增未绑定/篡改拒绝 |
| 必要 import / collection | PASS，147 项 | 新约束、领域、CapabilityPlanner/专用Provider；不代表全 Backend collection |
| Ruff：新增/受影响代码 | PASS | 12 文件正常检查；OpenAI Provider 忽略仅基线 E701 后 PASS；导入排序和未用 import 已清理 |
| Ruff：完整 OpenAI Provider | FAIL，基线2处 E701 | `try: validate_expected_kind(payload)` 与 issue-ledger consumed 同行语句在 Start HEAD 已存在；本轮不扩修旧助手逻辑 |
| git diff --check / 保护 hash | PASS | 原 P0 报告、未授权源码、.env、378历史证据未变 |

各回归包存在重叠，不能将上述数量相加声称不同测试总数。独审修复后没有重复运行完整260/150包；只复核受影响领域与Provider，最终 collection 验证导入。测试网络禁用，HTTP fail-closed 用例仅允许 Windows asyncio 本地 self-pipe、禁止外部连接/DNS。

独立只读审查 **PASS**：两项具体反例已关闭，有限约束事实检查、来源/Plan 双阶段批准、fixture 隔离和公开需求边界没有剩余代码阻断。审查明确保留 LIVE_PENDING、进程内 issuer 与后续持久 Receipt/统一预算的限制；没有把自算 plan_hash 单独当作认证，也没有把 Validator PASS 当模型语义通过。

原 P0 报告 hash、Policy/GoalProfile/审核索引/Seed/迁移/数据库与 Runtime 源码、`.env`、378 份历史账本/证据均作保护校验；旧进度正文完整保留。

真实产品模型、真实 GitHub/Web、真实 Reader：**NOT RUN**，实际请求数均 0。真实用户/owned PG、行数比较、Compiler、Draft/Revision 发布、Worker/Receipt/checkpoint/cancel/fence 恢复、浏览器：**NOT RUN**。没有创建 Run/Job/Draft/Plan 或执行 migration，不将“未调用写接口”冒充真实数据库前后行数验证。

## 8. 修改文件与剩余风险

生产代码/协议共 11 个文件：

- 新增 `domain/planning/constraint_adaptation.py`、`domain/planning/domain_verification.py`、`application/domain_verification.py`。
- 修改 `application/capability_planning.py`、`application/teaching_resource_research.py`、`application/curriculum_composition.py`。
- 修改 `domain/planning/curriculum.py`、`domain/planning/research_reader.py`。
- 修改 `infrastructure/providers/openai_compatible.py`、`research_reader_contract.py`、`curriculum_contract.py`。

以上路径均相对 `backend/app/`。新增 `backend/tests/unit/test_constraint_adaptation.py`、`test_domain_verification.py`。文档：新增本报告，保留并纳入原 P0 报告，更新 progress；ignored 脚本/证据不提交。

Hash 算法没有改动；新的服务器约束评估与领域来源/Plan 绑定自然进入相关课程/批准 hash。没有修改 CapabilityPlan/GoalProfile Schema 或增加数据库结构。

本轮确实解除“任何硬约束必卡死研究/课程”的前两项机制阻塞，未知领域完成受信定义下的离线结构贯通。并未证明完整原始 Case A/B/C 真实路线均通过：B 的独立异常处理需求、真实来源语义、前置充分性、语言资格及课程质量仍待有界真实验收。正常资料不足、预算不足或没有合格案例时仍 incomplete，不为了全绿编造素材。

主协调请求 Sol6.1 high；安全/来源实现及独立审查请求 Sol6.1 xhigh。实际解析均 **NOT OBSERVABLE**，未改全局配置，不使用 Sol max/Astra，不为机械整理额外调用开发代理。

`ITEM7_P0_CONSTRAINT_BLOCKERS_RESOLVED`

`ITEM7_P0_UNKNOWN_DOMAIN_STRUCTURAL_PATH_RESOLVED`

`DOMAIN_VERIFICATION_LIVE_PENDING`

`ITEM7_P1_P3_NOT_STARTED`

`STOP`
