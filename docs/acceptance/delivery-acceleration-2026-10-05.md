# 2026-10-05 A6 来源与交付收口：最终记录

## 用户现在新增能做什么

未来新 Agent 路线可保留获得正文审读依据的 MCP 10.1 来源；合法冻结资源若在保存前再次丢失，会明确拒绝保存。新 owned 合成 Plan 已通过真实 Edge 的学习单元、源码候选、Prompt、总结、成果、完成推导、变更与历史闭环。正式入口尚未开放。

**局部修复、保留响应回放、owned PG/Edge：PASS。新收费代表完整生成与独立合同/来源审计：PASS。整体：STAGING_BLOCKED / NOT_READY。**

用户后续授权覆盖本文件下方原中间 STOP：仅同一教程10.1正文审读及下一不可变版本；模型累计上限100→200。原 STOP、原45/46 FAIL和旧账本保留，不倒改旧事实。剩余额度不触发再次生成。

## 1. 实际代码、冻结范围与来源依据

- 分支 `feat/n1-resource-discovery`，进入本批本地/已核实远端均为 `9fef887af21dd5ff2a60aef306a6b9b02d176f5f`；保留后继 `c0237d2415e1e77bc216e6f087da5ab53158cf9c`。实现提交 `859db09f4d154b0397ad763146d34561e5af404a`；最终文档提交及实际HEAD见 `var/delivery-20261005/final-invariants-complete.json`。未 reset、切分支、push 或 merge。
- 改动：`plan_resources.assert_frozen_resource_projection`；`PlanService._persist_draft` 的 normalize后/save前调用；CURRENT_PACKS Agent8；新 `map_mcp101_review.py` 和不可变 `agent-application-v8.json`；一个新同因测试文件及旧 current-pack 断言7→8。无 DTO/API/schema/migration/UI/prompt/cap/model 改动。
- 首次丢失在 `restrict_pack_resources`：旧10.1仅 `legacy_index/toc_checked`，不是正文审核；原行为对旧资格正确。用户随后批准实际正文审读，形成 **agent.application/8**。只有第十章 source和四section身份替换、source_version=2；仅10.1新增审读依据，其他三节和其他来源资格继承。canonical、任务、路线、guidance、GR binding不变。
- 新source `src_mcp101_a7ca881ee83ac722491299cd`；10.1新section `sec_mcp101_18e647c993d34f4e0eb316e5`。新ID由既有ID与精确审读摘要生成，不按标题或URL模糊合并。旧source/section及immutable历史保持。
- 10.1实际审读范围：10.1.1–10.1.4，工具集成问题、MCP/A2A/ANP职责比较、protocol/Tool/Agent三层封装和静态示例。实际正文为英文；图片/外链未读，代码未执行，SDK互通/高级认证/transport运行验证 **NOT RUN**，不扩大必做任务。
- 来源：[原仓库第十章](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter10)，[实际采集正文](https://raw.githubusercontent.com/datawhalechina/hello-agents/main/docs/chapter10/Chapter10-Agent-Communication-Protocols.md)。观察Git blob `98b0700c4adf3259efc1842a307c9b2c2238fc9b`，未声称repository commit pin。原正文98277bytes，SHA256 `e68e510739fc08527f994eac7ab4104b5abc38f4b51c3e788d2fa9ef2111a60d`。抽取10.1的LF口径13346bytes/SHA `97ff3dbbab2119cb15c85d072cbe534b58f8abcb60d69fc63eaf8dbc68220e4d`；Windows捕获文件13551bytes/SHA `ddbb8acb2a13eca2ac1293138e393c15809d45c7c01251018f7853837d9201e4`。两个frame明确记录，原采集记录未改。

冻结代表范围为 A0–A8、G0–G6、GR、GT，共18阶段；16 canonical、18正式任务、37 extensions、46资源安排、25个实际选中source identity、74有序章节refs。完整Agent主线保留Framework/MCP，Pi小型源码、专项RAG教程、成熟目标切片和迁移验证分开。

| 教学验收 | 当前证据 | 状态 |
|---|---|---|
| A0–A4基础、工具/RAG/上下文 | canonical全字段、适用知识、原教学标题/目标/focus精确落库，普通学习页可见多单元 | PASS |
| A5 Framework | 完整有状态/恢复学习指导与正式任务；没有回退成可省略阶段 | PASS |
| A6 MCP | 10.1来源version2、ordered section/role/order/nodeIDs保持且非fallback；同域错版本/跨来源/跨知识等仍拒绝或合法降级 | PASS |
| A7系统评价与A8 Pi | 原canonical/任务与小型源码指导保持，不使用万能A8或额外强制小项目 | PASS |
| G0–G6详细RAG | 完整长guidance、阶段任务和Prompt上下文；不接入或修改外部RAG服务 | PASS |
| GR成熟切片 | RAGFlow、WeKnora各一张稳定来源绑定卡/链接/指导/Prompt，metadata-only合法空章节，两仓库不合并；仍一项任选任务 | PASS |
| GT迁移验证 | 既有指导/任务/验收保持，未新增教学平台或知识键 | PASS |
| 合法教学细分 | 回放原58单元、A2原5单元完整保持；新模型原生53单元（A2为2个），逐标题/目标/ref读回，无代码截短或固定数量回填 | PASS |

## 2. RED→GREEN与受影响验证

- 原冻结资格反例 **FAIL / exit1** 保留；actual `_persist_draft` guard进程内no-op反例 **FAIL / exit1**，证明后置normalize丢失能被检测。未回退源码作RED。
- 新35个不同案例 **PASS**：34项组合＋1已有用户修订兼容；合法资源source/version/refs/role/order/nodeIDs、missing/duplicate、hold/未审核/错版本/错归属/不适用、真实legacy/pending、metadata-only repo，以及实际save入口都覆盖。已有用户编辑Draft重用先返回，未覆盖合法修订。
- 原同次执行的197项 F1–F4/F2/语义/内容保护用例 **PASS**，复用执行结果；从原XML提取有明确 provenance 的PASS子集，**不是重跑**。首轮新测试错误读取异常 `.reason` 的11项 **FAIL** 原XML保留，修正新测试使用 `.details['reason']` 后35项组合通过；不把测试错误称业务RED。
- budget/contract31例 **PASS**；独立费用AST/mock7项 **PASS**；前端GR/Prompt16例 **PASS**；`npm run build` **PASS / exit0**。不累加重复运行，不用总数替代逐项教学验收。
- 命令与XML：`pytest ...test_mcp101_reviewed_successor.py` → `mcp101/root-guard.xml`（34PASS/exit0）；兼容单例 → `existing-user-edit-compatibility.xml`（1PASS/exit0）；`pytest ...test_batched_budget.py ...test_reviewed_structure_contract.py` → `budget-contract.xml`（31PASS/exit0）。原组合命令/FAIL及197个实际PASS归因见 `affected-first.xml` / `affected-preserved-provenance.json`。

| 证据层 | 状态 | 具体结论 |
|---|---|---|
| 原F2真实response/receipt | FAIL | 原45/46来源审计结论保持；未重派、恢复或确认旧Draft |
| 当前离线编译图/Fake replay | PASS | 保留51–88共38份原body/content，原normal58→repair59；仅测试包装6处exact来源alias，新身份差异逐path记录，无live fallback |
| 当前真实owned PG/checkpoint | PASS | 新正常API/受控图保存，38个新fake receipts未复制旧真实receipt；46slots74refs、canonical/practice/17关系边、完整guidance，旧Agent7/8 rows保持；新Draft普通synthetic confirm与fresh读回 |
| 当前真实Edge/API/PG | PASS | 23组合checks；Prompt原文两版/指定raw+实施export/未保存保护；真实summary409恢复；synthetic external补充/USER决定；阶段完成推导、一次非收费资源diff/confirm/revision2/旧历史、refresh/logout/relogin；无Knowledge VERIFIED |
| 新鲜真实模型代表 | PASS | 一个全新Acceptance/Run/owned业务及CP库；37normal/0repair/unknown0，独立CP/PG/receipt/原body/冻结来源与public service view精确一致 |
| 新收费Draft confirm / published Plan /其Edge | NOT RUN | 当前仅回放Draft获synthetic confirm许可；新收费Draft保留awaiting_approval，Plan0，不扩大额度授权 |
| 原用户非空Plan内容/体验接受 | NOT RUN | 合成USER接受不替代负责人或原用户接受 |

## 3. 新计划、费用与历史

- 回放Run `run_fc8ca606ec0d446f805541901c7149ee`，初版Plan `pln_e77d2d89bedb41348b27b1c3bca4bc2f`；Edge显式非收费资源调整后当前Plan `pln_8397681c34e5415a9524886ed7cbe3f5`（revision2），初版superseded及Prompt/总结/成果历史仍可读。该合法用户修订不要求回写原冻结资源。
- 唯一新收费Acceptance `delivery-agent8-rag-synthetic-3c602f0ab1bc` / Run `run_96778f62c994478bb68f9df1ad5a67d3` / Draft `drf_08160109502b5c978d4f772ce0dd4aff`。Run succeeded+none；Draft awaiting_approval、Plan0。实际53单元，模型侧原样保存；不强行与旧回放58相等。
- v6.5 outline input **209998** → 本轮真实 **3673**（下降 **98.25093572319736%**），output **1400**，finish_reason **stop**；JSON/18stage keys/PG账本门禁先于structure通过，无length/truncation。
- 单次actual manifest上界：37normal＋最多2repair＝39，output上界241664tokens；本次实际37normal、0repair。总provider input81562、output37412、total118974。请求数与美元费用分开，未编造货币金额。
- 用户追加授权事实已在同一账本append-only记录一次：previous_cap=100、additional_authorization=100、new_cumulative_cap=200、used_before_authorization=88、remaining_after_authorization=112。实际37次新request/result/原body/receipt/usage append-only，累计 **125/200**、剩 **75**；达到第一份代表PASS即停止收费，不因余额重复生成。
- 当前产品搜索/Tavily/GitHub discovery **0**，外部RAG **0**；授权正文采集仅同章directory1/body1，非搜索/模型调用。历史搜索6/1000保持；unknown本批0，历史failed/unknown不重派。
- 921个旧保护文件（含.env、旧账本/response/evidence）哈希保持。旧F2库再次scoped read-only核对：旧Draft awaiting_approval、Plan0、原source audit45/46 FAIL保持。原Run技术投影succeeded与来源FAIL分别记录，未倒改结论。
- 首轮free脚本未加载provider环境而使用默认Fake，门禁 **FAIL** 且派发0；用新独立launcher只加载现有LLM/SESSION安全配置、清除产品DSN后free binding/DNS/TLS **PASS**。未改模型/密钥/全局配置。原库首次默认配置探测失败不是其可用性证据；随后实际.env只读事务核对 **PASS**：schema0023、仅Agent1/Python1发布版本，写入0。

## 4. 证据、归属和回滚

主要证据均在 `var/delivery-20261005/`：`replay/result.json`、`pg/pg-result.json`、`pg/46-source-slots.json`、`mcp101/combined-review-new.json`、`edge/checks-final.json`、`edge/execution-report.json`、`nonpaid-gate.json`、`free-preflight.json`、`paid/independent-draft-result.json`、`paid/independent-slots-readback.json`、`paid/reconciliation-final.json`、`old-f2-readonly.json`、`original-configured-readonly.json`。费用grant和completion在原 `.git/v2-paid-quota-20261001/`。秘密仅private文件，不写tracked文档。

本轮回放业务/CP两库及新收费业务/CP两库全部保留；名称与身份见证据，DSN不公开。受控API PID16356/UI42484及Edge已关闭，8033/5193释放；正式Worker/入口、原库写入、部署、RAG、push/merge **NOT RUN**。API relay实际指向owned8033；清理期间一次默认Vite8000尾随GET被拒绝连接，未触达原库，已登记并限定未来启动target8033。

回滚仅撤销本轮白名单差异/提交，不reset或整树restore。旧Run/Plan继续按原快照；新Agent8源/section身份的已生成owned历史不得删除。回退CURRENT_PACKS时保留已使用版本读取能力；原/本轮证据、失败、unknown和账本始终保留。

开发路由：有界实现/PG/Edge请求Sol6.1 medium，来源/预算关键复核请求Sol6.1 xhigh，机械提取Luna medium。实际解析无法核实均 **NOT OBSERVABLE**。不修改全局配置；单一业务authority负责人，子任务文件独立，没有重复全仓调查。

## 5. 正式交付短差异表与一次授权包

| 承诺 | 当前组合证据 | 真正剩余阻断 / 下一准确动作 |
|---|---|---|
| 生成、草案、确认、完整来源 | 当前回放Plan/真实模型Draft/46slot/费用PG PASS | 原用户非空Draft由本人确认、体验接受；新收费Draft没有扩大确认许可 |
| AI/Agent/Cloud/Python与专项范围 | 原有效证据复用，Agent8当前完整路线PASS，未缩范围 | 原库尚未导入当前AI4/Agent8/Cloud4；最新真实副本restore/import演练后才评审写入 |
| 学习、Prompt、总结、成果、完成、历史 | 当前新Plan真实Edge23checks PASS | 用户主观教学/体验接受仍独立，不以synthetic USER替代 |
| 非收费资源/实践变更、旧历史 | 当前resource revision2与不可变旧历史PASS；未改路径沿用有效测试 | 正式数据/入口演练与用户接受；无需新变更平台 |
| 身份隔离、取消、unknown与恢复 | 现有保护/实际CP/read-only旧Run/current scoped PG PASS | 正式Worker开启前明确allowlist/admission和expired/unknown不claim；不恢复旧失败 |
| 来源发现、审读身份 | 当前10.1正文/immutable/hold/metadata-only边界PASS | 产品GitHub私有OAuth未接线等维持原状态，不以手动URL替代 |
| 构建、正常启动、备份恢复 | 当前build/owned服务PASS；历史native restore证据复用范围有限 | 原库0023而owned0024；当前新内容不同于旧演练，需要fresh native backup→new owned restore→forward0024→AI4/Agent8/Cloud4演练 |
| 日常模型预算 | 本轮wrapper累计200及durable perRun manifest绑定PASS | 常规PlanningRuntimeFactory仍构造PgAttemptLLM时未绑定manifest，且wrapper200不是日常全局预算；需限定非收费运行验证/必要局部修复后才能开启正式Worker |
| 独立RAG及私有OAuth | 保留原合同/边界，未操作 | RAG实例/auth/tenant/dataset/纯检索/citation合同缺口未解除F17；不改成可选、不宣称READY |

**下一授权需一次明确覆盖：**先限定日常Worker预算/admission非收费收口和当前副本native备份恢复/0024＋AI4/Agent8/Cloud4导入演练；演练成功后，若批准正式操作，明确原库forward/seed、实际服务实例/端口/运行账号/启动动作及关闭回滚脚本、仅允许actor范围与旧failed/unknown排除策略、是否需要push/merge/部署分别授权。原用户Plan确认与内容接受仍由用户作出；独立RAG实例及合同另提供明确外部条件。原库写入/正式入口/正式Worker/部署/push/merge没有执行。本轮收费代表已PASS，不再请求重复收费，也不消费剩75。

**STOP于上述正式操作边界，整体保持 STAGING_BLOCKED / NOT_READY。**

---

## 以下为保留的授权续接前中间记录（历史，不覆盖上方最终结论）

# 2026-10-05 Delivery Acceleration：A6 冻结资格矛盾，BLOCKED / STOP

## 后续额度授权追加（2026-10-05）

用户在本批证据收口后明确增加100次产品模型授权，覆盖原Goal模型请求0的额度限制。已向同一 `.git/v2-paid-quota-20261001/` 追加 `authorization-delivery-20261005-cap-200.json`，并在progress顶部记录：previous_cap=100、additional_authorization=100、new_cumulative_cap=200、used_before_authorization=88、remaining_after_authorization=112。重复发送是同一次授权，只追加一次；旧授权和88对request/result/receipt不改。本次新增实际请求0，最新状态88/200、剩余112；下文88/100是扩额前审计时点。

仅在A6、46-slot身份、canonical/practice、Draft/Plan/Edge非收费门禁全部PASS后，才可创建全新Acceptance/Run及新owned业务/checkpoint两库的完整paid代表，仍37normal+最多2repair=39，unknown立即停止、首份完整PASS停止继续收费、新独立FAIL先停收费并离线定位/修复后再决定第二份。当前A6资格门禁FAIL，因此本次授权尚未派发真实请求；额度扩展没有解除来源资格/原库/正式入口/Worker/部署/历史保护边界。此前“未来如收费须扩至至少127”的预算说明已被本条200上限覆盖，不再申请该差额。

## 用户现在新增能做什么

可以核对 A6 首次降级的精确位置、全部保留响应的离线回放及交付剩余门槛。本轮没有开放新体验入口，也没有生成或确认新 Draft/Plan。A6 非 fallback 目标 **FAIL**：原冻结 10.1 只有目录审读资格，现有 Agent 教学消费合同要求降级。活动 Goal §4.2 禁止通过改冻结内容或升资格修复，因此停止该修复及依赖的 owned PG、Edge 阶段。整体仍 **STAGING_BLOCKED / NOT_READY**。

执行授权来自用户交付的 `STUDYPLAN_DELIVERY_ACCELERATION_2026-10-05.zip`，活动 Goal 为 `02_CODEX_ACTIVE_GOAL.md`；01 为优先级说明、03 为同 Goal 验收附录。五个输入文件的 SHA256SUMS 核对 PASS，ignored 副本位于 `var/delivery-20261005/input/`。本报告不改变旧 F2 FAIL。

## 1. Git、预检与保全

- 分支：`feat/n1-resource-discovery`。进入及业务候选 HEAD：`9fef887af21dd5ff2a60aef306a6b9b02d176f5f`。
- `git ls-remote origin refs/heads/feat/n1-resource-discovery` 核对远端相同 SHA；`1a3262e85296c95d3dfb4349d0d4ef83438f17da` 是其祖先（exit 0）。没有回退、切分支、reset、restore、push 或 merge。
- 进入时受跟踪文件干净；只见 `.workbuddy/`、`design-preview/` 两个受保护未跟踪目录，未操作。业务代码、内容包、API/DTO、迁移、provider prompt、模型参数和全局配置修改为 0。本轮 tracked 差异仅本报告及 progress 顶部；文档提交 SHA 另见最终 Git 核对。
- `var/delivery-20261005/` 小文件写入读回、venv、PG 只读角色安全预检 PASS；Edge 可执行文件与现有 playwright-core harness 存在。这里只证明可用性，浏览器消费 NOT RUN。
- 复用旧保护 manifest 的 692 个唯一文件，并加入已完成 F2 批次和当前账本，形成 921 文件保护集。进入核对 PASS；结束核对见 `final-invariants.json`。10 个相关源码/记录白名单存于 `baseline-code.zip`；没有复制或提交秘密。
- 本轮没有创建 owned 业务/检查点库或启动 API、Vite、Worker。核对的业务端口无监听；5432 仍为原本 PG PID7316，未关闭或修改。

## 2. 已复现的唯一 A6 原因与裁决

原独立冻结文件：`var/f2-negative-extra-task-20261004/paid/frozen-submission.json`。

| 字段 | 原冻结事实 |
|---|---|
| stage / role / order | `stage.v62.agent.application.a6` / `reference` / 0 |
| source | `src_v612_1f6742530460b0908234a6d3`，version 1，reviewed，checked_at 存在 |
| section | `sec_v612_d79f6a54976fb31d5159ac60`，10.1 协议角色，legacy_index / toc_checked |
| 原审读依据 | 明确正文审读为 10.2.1–10.2.5、10.5.1；chapter structure/summary/exercises 有检查，10.1 没有正文审读声明 |
| applicability | `node.v62.agent.application.a6`，与阶段 canonical 一致 |
| pack | Agent application v7；curriculum_review.status = chapter_mapping_reviewed，不是 review_status = selected_scope_pending |

身份、版本、章节归属及适用键均正确。首次变化是 [plan_resources.py](../../backend/app/application/plan_resources.py) 的 `restrict_pack_resources`：Agent 非 repo-case、非真正 pending 索引入口要求 source 与所选 section 均 reviewed；此处 section 条件为 false，因而清空 source_ref/section_refs，version 变 0，保留 role/order/node_keys 并添加搜索 fallback。此前 `presentation_entry`、`merge_batches`、独立 `checked_projection(final=True)` 均未丢失该 slot。当前没有执行 materialize/project_draft/normalize/repository.save 或 fresh PG 消费；旧只读 PG 证据已显示相同空引用，不能把它称为本轮新 PG 验收。

**为什么不能把它当普通映射修复：** `validate_seed` 允许目录级 reference 候选进入包，通用 resolver 也能解析 legacy 索引；这不等于获准作为 Agent 已审核教学章节消费。既有 `test_v62_semantic_pg.py:186–198`、`test_v67_outline_projection_pg.py:127–140` 及 [v6.2 验收](v6-2-semantic-content-2026-10-04.md) 明确接受“未审核参考章节剥离引用、保留 role、显示 fallback”。v6.12 继承资格规则，当前 Goal §3.2/§4.2 再次禁止升资格。单次独立组合复核 PASS，未发现无需改权威合同即可修复的身份错误。

所以原“已冻结选择了 10.1”与“10.1 可作为已审核教学章节保留”的前提不一致。没有修改 Agent7、原 manifest/pack/source/section、审核等级或 UI 链接来追绿；落库前新增保留断言也没有实施，因为该 slot 尚未满足“冻结合法资源必须保留”的前提。

## 3. 回放、RED 与边界证据

| 检查 | 状态 | 精确范围 / 命令与退出码 |
|---|---|---|
| 最小预检和历史保护 | PASS | `.venv/Scripts/python.exe var/delivery-20261005/preflight.py`，修正本轮 checkpoint 输出路径后 exit 0；初轮路径接线失败保留工具记录，未越界写文件 |
| 全部原响应离线 compiled graph | PASS | `.venv/Scripts/python.exe var/delivery-20261005/replay_diagnosis.py`，exit 0；38 个原响应，memory checkpoint，停在 save_draft_projection 前，无 DB/socket/provider |
| A6 非 fallback 门禁 RED | FAIL | `.venv/Scripts/python.exe var/delivery-20261005/run_diagnostics.py identity-red`，exit 1，1 项 FAIL；原冻结身份保留期望未满足，未转为 GREEN |
| 首轮资格诊断接线 | FAIL | `run_diagnostics.py qualification-contract`，exit 1，7 PASS / 1 FAIL；把已裁剪 canonical 的 submission 当完整 Seed 校验，触发未选 applicable key 校验；保留首轮 JSON/XML |
| 修正诊断 seam 后资格边界 | PASS | `run_diagnostics.py qualification-contract-final`，exit 0，8 个不同用例 PASS；仅 ignored 测试改为校验完整已发布 Agent7，再精确比较原 section；未改冻结事实或生产逻辑 |
| 一次组合关键复核 | PASS | `qualification-review.json/md`；只读核对，不重复 graph 回放或重跑测试 |
| 新 owned PG 业务/真实 checkpoint/确认 | NOT RUN | 资格前置 FAIL，无新数据库、Draft、Plan 或合成确认 |
| 当前新 Plan 真实 Edge / Prompt / 总结 / 成果 / 变更闭环 | NOT RUN | 依赖同一来源门禁；没有用旧 Plan、Mock 页面或测试数量代替 |
| 新鲜真实模型 / 搜索 / 外部 RAG | NOT RUN | 本 Goal 明确为 0，未创建新付费 Acceptance |
| 最终构建 | NOT RUN | 业务/前端/依赖未改且前置失败；未重复已有构建或宣布新候选可发布 |

8 个资格诊断覆盖：完整 Seed 入包与正文资格不同；原 TOC reference 正确降级且保留 role/order/适用性；A6 邻接已审核来源精确保留；GR 两个不同 repo、空章节和 legacy_index 资格保留；未知来源、错误版本、外来章节均不能提升资格；restrict 不修改冻结 pack 或输入。首轮与最终重复用例不相加。

回放严格使用原序列 51–88，A6 normal58 顶层 shape 失败后进入原 known repair59。每个原 body、JSON envelope、UTF-8 content SHA，以及原 Run/attempt 到新 fake/replay 测试 attempt 的 provenance 均 **38/38 PASS**。未知 purpose/attempt、fixture 耗尽直接失败，无 live fallback；没有改绑旧真实 receipt 或复制为新数据库收费回执。新测试身份仅存在于 memory，未建立正式 Run 行。

独立原 blueprint 与合并状态的全部 **46 slots 精确一致**；restrict 后 **45 身份保留、A6 1 降级**。这里 1 项仍是本 Goal 非 fallback 要求的 FAIL；现合同不允许把它改成已审核章节。原冻结 slot 共有 74 个 section 引用（含 1 个目录级 10.1），降级后为 73，不能把所有冻结引用都称正文已审。

18 阶段、16 canonical、58 教学单元、18 正式任务、37 extensions 保持；独立 raw→hydration→merge→最终投影校验 PASS，未用数量代替内容比对。A2 五单元仍单 canonical/单正式任务；GR 两个不同来源候选仍一项正式任选任务。F1–F4、F2 文字门禁和 GR consumer 未改；此前 173 不同 unit/contract、28 wrapper 安全反例、4 owned PG 与 GR 五场景 Edge 是保留的历史证据，不计为本轮新 PASS，不能代替当前新 Plan 消费。

## 4. 用量、证据与风险

- 产品真实模型新增 **0**，权威累计 **88/100**、剩余12保持；原88 request/result对及授权记录字节保持。搜索新增 **0**，旧6/1000保持；外部正文/RAG调用 **0**。本轮 unknown0，旧 failed/unknown 不重派、不清除。
- 原 F2 Run `run_9f6db411f8d1415a818e7d3f69e14ab8`、Draft `drf_aa6f1f8b3478527185cdb1f2c009fb22` 不连接业务写入、不确认、不修改结论。其 awaiting_approval/0 publication 为保留的旧 PG 读证，本轮未重新查询该库。
- `.env`、旧响应/receipt/审计及保护文件不变；没有写原产品库、启动正式入口或 Worker、修改 RAG、push/merge。
- 路由请求：来源权威与关键复核 Sol6.1/xhigh；独立机械交付提取 Luna/medium；实际解析均 **NOT OBSERVABLE**，未宣称主会话切换成功或修改全局配置。
- 独立复核登记了真正 pending 索引分支遇未知 section 的静态 KeyError 风险；未复现、与 A6 无因果，未扩大为本轮修复。正式 daily Worker 预算绑定亦仅作静态检查，不能声称运行验收 PASS。

重点 ignored 证据：`baseline.json`、`protection.json`、`source-diagnosis.json`、`46-source-slots.json`、`replay-provenance.json`、`offline-merged-state.json`、`offline-restricted-state.json`、`identity-red.{json,xml}`、首轮及最终 `qualification-contract*.{json,xml}`、`qualification-review.json/md`、`operations-readonly.json`、`final-invariants.json`，均在 `var/delivery-20261005/`。原证据目录未改。

## 5. 正式交付剩余短表

| 当前承诺结果 | 可复用证据与本轮新增 | 真正剩余阻断 / 下一动作 |
|---|---|---|
| 生成、草案、确认与完整来源 | v6.8 已完成其旧代表；本轮38原响应完整离线、F1投影和46slot定位 | 10.1目录资格与非fallback教学目标冲突；先解决新冻结依据，再恢复当前 Goal 所需 owned PG/Plan/Edge，不确认旧F2 |
| AI/Agent/Cloud、Python与既有专项 | v6.2/12/13教学证据及当前版本保留，本轮内容修改0 | 受影响新的来源合同尚未确定；不能删MCP/专项或用完整RAG代替所有方向验收 |
| 指导/任务/Prompt/总结/成果/历史 | 已有PG/浏览器闭环与GR五场景证据；本轮58单元/原canonical/任务保持 | 当前新Plan实际闭环NOT RUN；待上游通过后同一owned账号一次走查 |
| 重规划、资源/实践替换和历史 | 既有v6.2真实差异→确认→新版本与历史保留 | 新候选同Plan非收费变更消费NOT RUN；不引入新变更类型 |
| 隔离、取消、unknown与恢复 | 既有auth/lease/恢复PG证据，原失败/unknown保留 | 正式实例实际claim/admission/预算需复核；旧unknown不能领用，恢复不能重发 |
| 公共发现/免费正文/身份 | F08实际Tavily及手动GitHub URL历史证据 | 本轮禁止外部读；GitHub账号OAuth未接线，手动URL不代表私有账号授权 |
| 构建、启动、备份恢复 | v6.3 native dump→新owned restore/forward/旧行保全 | 本轮没有业务差异；正式操作前需新鲜原库快照/备份和现schema核对，不能拿2026-10-04快照当今日状态 |
| 原用户非空Plan与完整接受 | 用户原登录/空状态已接受；旧合成Plan可读证据 | 原用户非空Plan与本人内容/体验接受未完成；合成确认不能替代 |
| 独立RAG / GitHub私有OAuth边界 | F17与v6.3 RAG合同状态保留 | 实例选择、auth/scope/纯检索/citation/故障合同和私有OAuth仍有缺口；不自行改为可选以宣布READY |

## 6. 一次下一授权与正式操作包

**当前准确下一步是来源权威裁决，不是部署。** 若要继续非 fallback 10.1，需明确授权在保留 Agent7 与所有旧 Run/Plan 的前提下，对同一 10.1 建立真实正文审读依据并发布下一不可变内容版本；或者明确评审受资格限制的 TOC reference 消费合同。需要的最小事实是“10.1 的批准阅读深度/范围”；身份字段已经足够，无需新 schema/API/图谱。没有此决定不能只放宽 restrict、改审核 enum 或让UI补链接。新版本/合同成立后，仍需说明原响应复用与新冻结 authority 的差异，恢复非收费PG/Edge支线。

下列正式操作只列需要准备的精确边界，**本轮不请求立即执行，也未执行**：

1. **代码/内容/数据库：** 业务候选9fef887a，源码和迁移差异0；本轮没有导入新版本。将来新包版本/digest须裁定后给出。沿 [既有staging方案](../reviews/2026-10-04-v6-3-staging-plan.md) 重新读原库实际revision与增量，READ ONLY一致快照 native pg_dump(custom)→全新owned库 pg_restore→行/ID/ACL/RLS/来源摘要核对，再决定forward migration和正式immutable导入；不复用旧archive覆盖新原文，不做destructive downgrade。
2. **服务/Worker：** 本轮原产品及测试入口均未启动，无本轮PID要关闭。已有方案的copy API8024/UI5179、正式API8022/UI5175均为历史端口，须在正式授权时重新核对配置与所有权，不能据此自动启用。正式Worker脚本为 `python -m app.tools.planning_worker`，实际默认admission是 trusted_server，不是验收wrapper。其claim函数可更新过期任务的reconciliation状态并持续轮询；必须先核对精确现存job/attempt、排除failed/unknown及运行账号，批准端口/profile/PID归属、停止与回滚步骤后才能启动。
3. **日常费用保护：** 已有每purpose cap、冻结37normal+2repair=39/output241664与SQL per-run预算规则。静态追踪发现 `PlanningRuntimeFactory.__call__` 构造 `PgAttemptLLM(dsn, provider)` 未传 manifest，所检查生产链未给该ledger赋manifest；constructor为None时不能宣称SQL正在执行冻结请求数/总输出守卫。需下一有界非收费runtime证明/裁决，再开放日常生成；未证明实际付费超额，未在本轮扩大修复。历史100次验收wrapper不保护全部日常请求。
4. **新鲜收费代表：** 本轮不申请重复完整生成。没有prompt/provider或生产代码变更；v6.7要求的下一代表已由v6.8完成，不能仅用这条历史下一动作重复索取39次，也不能把本轮回放报新鲜实时报PASS。若后续新合同或有效发布门槛确要求真实复验，届时按实际manifest一次给预算；保持18阶段时88+39=127，差额至少27，不是现在授权，也不估算未知金额。
5. **用户接受及恢复：** 原用户自己的非空Draft由本人确认。正式入口/原库写入/Worker启用/用户体验接受分别授权和验收；不得用合成操作代替。回滚只撤本轮白名单文档差异；没有业务patch或新格式读取依赖。后续数据回滚按native备份恢复到另一个owned recovery库、核对后批准入口切换，保留所有历史。

**结果：A6_SOURCE_QUALIFICATION_BLOCKED / BLOCKED，STOP。** 已完成安全预检、首次降级定位、完整保留响应离线回放、资格边界与单次复核、独立交付差异汇总；依赖的修复、真实ownedPG/Edge闭环与正式操作没有跨越门禁。原真实代表仍FAIL，整体NOT_READY。
