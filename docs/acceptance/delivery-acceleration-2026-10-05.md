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
