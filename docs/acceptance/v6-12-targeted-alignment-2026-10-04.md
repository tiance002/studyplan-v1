# v6.12 Targeted Alignment：BLOCKED，STOP

用户现在新增能做什么：审阅[来源明确的完整 Agent+RAG 新 Fake 计划](v6-12-fake-plan-review-2026-10-04.md)、[31项教学验收](v6-12-acceptance-cases-2026-10-04.md)及本机[公共/失败 Run 冻结原文](../../var/v612/FROZEN_SCOPE_REVIEW.md)。四条新 Fake 计划已在隔离 owned PG 完成生成、合成确认、读取；没有本轮真实 provider Plan，也没有开放体验服务器。普通学习主区的多单元呈现通过 Mock API 的真实 Edge renderer 验证；实际持久化 Plan 的 Edge 消费尚未运行。

## 授权、基线与停止依据

用户批准执行交接包 [03 Goal](../implementation/v612-handoff/03_CODEX_GOAL_v6.12.md)，以 [01 产品决定](../implementation/v612-handoff/01_PRODUCT_DECISIONS.md) 为本轮统一教学语义。七份交接文件逐字节归档并核对；附件的执行指令由用户明确批准，未将来源资料当作额外操作授权。

实际分支 `feat/n1-resource-discovery`，起点与停止时 HEAD 都是 `1a3262e85296c95d3dfb4349d0d4ef83438f17da`。`ff3b6c42c16b0ec2b634b45441251cb8dc1e3249` 是祖先：PASS。起点已有 v6.11 units-only formatter、节点/adapter/保存接线、checkpoint guard 及测试的未提交候选；本批复用，没有 reset/切分支/回退或重做旧 Goal。最终业务候选与审计仍未提交，不能当成已接受版本；完整差异保存在本机 `var/v612/stopped-tracked-diff.patch`，新增文件由工作树保留。

Goal §0 明确规定“遇到……新的结构性问题才 STOP”。只读合同复核发现保存前恢复 checkpoint 的顶层 canonical/teaching rubric 可绕过检查，故停止实施、实际 Plan Edge 和收费代表派发。未建立 `PEDAGOGY_AND_UNITS_READY`，最终为 **BLOCKED**。以下四项均未修复，不用已有 PASS 数字覆盖。

## 新结构性阻塞与合同缺口

详细复现、精确代码位置、实际证据和后续最小方案见[合同审查](../../var/v612/contract-review.md)、[机器记录](../../var/v612/contract-review.json)、[纯 Fake 脚本](../../var/v612/review-repro.py)。

| 项目 | 验收 | 已证明事实 / 边界 |
|---|---|---|
| F1 保存前恢复投影 | FAIL | compiled short graph + InMemorySaver，在 `save_draft_projection` 前只改顶层 `units[0].rubric.canonical_knowledge/teaching`；manifest、pack、原响应、structure_batches 不变。实际 executor 恢复后保存回调执行一次且收到篡改 rubric，新增 Fake 请求0。真实 PG 越权持久化/发布 NOT RUN，未宣称已证明真实 Plan 写入。 |
| F2 排除文本误作许可 | FAIL | Agent7 W6 的“课程不默认学 Kubernetes”被全 focus 拼接视作主题许可；合法 node/ref 的 `Must deploy a Kubernetes cluster for this stage.` 返回空校验错误。 |
| F3 repair 原对象预算 | FAIL | A2 ceiling14,034chars，11,058chars的响应只有额外 acceptance 一个字段错误；repair 加上原上下文后在派发前报 structure_payload_too_large，repair_count=1，HTTP0。不是收费请求，也不是真实token计数。 |
| F4 部分 marker 删除 | FAIL | 同时删外层 structure marker 与 hash、保留 focus/outline/batch markers，直接批次节点改走 legacy Fake。正式 executor 的 manifest/outline检查及后续merge仍拒绝；未证明可发布绕过。 |

F1 是本轮停止的结构性问题；F2/F3/F4 一并保留为待修合同缺口。审查脚本 exit0 表示成功复现错误，不是产品安全 PASS。

## 实施候选：完成的职责与真实范围

- **合同**：复用 `reviewed_structure_v1`，新未来提交冻结局部 `stage_focus_v1`；按批次 frozen canonical eligibility 区分 reviewed 与 search_only/generic。新 reviewed 输出只接受完整 units 的 title/node_keys/focus_refs/objectives；服务端生成单元身份，并从本地恢复 canonical nodes/relations。原始 presentation 和规范化 projection 分层保存；保留 teaching namespace、原 schema/canonical/hold/实践完成门禁及整 Run repair2。合同仍因上述缺口未验收。
- **内容**：新 Agent7/AI4/Cloud4 对应有实质职责变化的方向。canonical key 集合继承旧版；旧包未改。资源URL、受审章节、读取深度与 runtime NOT RUN 状态原样继承，重新绑定不升级来源资格。A5 一深多浅的主框架教学；A6 受控只读 server、最小 server 阅读/验证、失败与权限边界。新增副本的 MCP acceptance 体现该教学语义，Agent6/旧冻结原文保留。
- **页面**：`MainWorkspace` 普通主区按现有 `stage.units` 顺序展示单元标题、目标、关联知识按钮；复用 title/objectives/node_ids，无新增公开DTO/API。未增单元完成或知识掌握门禁，原阶段总结/实践完成逻辑保留。

完整 Agent+RAG **实际新 Fake frozen route**：A0→A1→A2→A3→A4→A5 Framework→A6 MCP→A7→A8 Pi 小型核心→G0→G1→G2→G3→G4→G5→G6 详细教程→GR 成熟 RAG 目标切片→GT 迁移与验证。18阶段、16 canonical、18正式任务、A2三单元同canonical/一任务。GR RAGFlow/WeKnora 两张替代卡只形成一个“任选案例证明相同能力”任务；GT 有独立最小改动/不迁移理由及改变前后回归验收，未复制成熟地图验收。没有第三个强制毕业Demo。

来源与每阶段 exact key/objective/章节/任务/参考项目 Prompt 见[新计划](v6-12-fake-plan-review-2026-10-04.md)，原机器结果 `var/v612/content-route-samples.json` 为离线选择，`var/v612/pg/manifest-rag.json` 与 Plan/workspace JSON 为 Fake owned PG 实际持久化结果，两层不能混称模型输出。

其他实际新 Fake/owned PG：专项待选Agent A0–A8；窄 MCP A0/A1/A2/A6；Node自有API 11阶段，包括 S2 Compose教程→SC小服务源码、S8可观测教程→SR成熟Telemetry切片，载体仍为自己的Node服务。Browser Playwright/async入场→browser-use A8、已知框架REVIEW及Workflow深化有定向UNIT/内容证据，完整Browser新PG NOT RUN。Coding缺独立已审TypeScript课程，Pi SDK Promise/events只提供局部阅读检查，不足时 needs_research_or_review；不借新命名提升证据。

## N0：原失败证据与历史兼容

公共 Agent6 61阶段与 v6.10 私有冻结7阶段分别导出，含 canonical全文/前置/章节/任务/项目角色。旧 `run_9c00403807ee4ccb817529611e44efa6` 只在 owned PG 以 READ ONLY 查询：failed，三次 parsed response 与已存本机原文一致。历史 HTTP wire 未存；不以 parsed JSON 冒充 wire。

A2六个新增键：tool-contract/registry/permission/error-evidence/responsibility-separation 是现有受审能力的可教学细分，不作为新canonical接纳；timeout-audit 完整实现策略/审计schema证据不足，不可自动加必修。原响应逐字节复制为 `backend/tests/fixtures/v610_a2/`，旧校验仍失败，三次错误数1/9/1。未改旧 Acceptance/Run/manifest/checkpoint/Plan，也没有 failed/unknown 重派。

## 验证与用量

| 验证层 | 状态 | 实际范围 |
|---|---|---|
| unit/contract | PASS | 最终951 PASS、2 NOT RUN（Windows symlink权限）；XML953项、failures/errors0，exit0。包含原A2 fixture、units字段/跨stage/陌生key/简易越界、原semantic/legacy golden。四个审查反例未被此测试集覆盖。 |
| 内容定向 | PASS | 最终69项，含原v6.10/v6.2语义及三方向受审事实继承、实际新增阶段职责；中途失败保留。 |
| owned PG / Fake | PASS | 最终10项；4条新Fake生成→合成确认→PG实体/rubric/依赖/任务门槛读回、checkpoint重启/规范化批次marker及知识篡改拒绝。未覆盖F1最终顶层projection反例。 |
| frontend / build | PASS | 16 tests及TS/Vite build。 |
| Edge / Mock API | PASS | 真实msedge renderer，Mock workspace三A2单元一canonical、排序/按钮/390px/refresh/无新增门禁；既有项目卡多候选/长续片回归。 |
| Edge / 实际owned Plan | NOT RUN | 在开始前因结构性STOP取消；没有新只读API/Vite服务或账号消费流程。 |
| 真实 provider / paid representative | NOT RUN | 无本轮paid Acceptance/Run，无真实outline/structure/practice/repair、真实合成confirm或paid Plan。 |
| 正式库/入口/Worker、RAG、外部搜索 | NOT RUN | 未操作。owned Fake测试使用自己的隔离库/测试Worker，不能称正式Worker已验证。 |

测试XML/log在 `var/v612/unit-contract-final.*`、`owned-pg-final.*`；frontend证据 `var/v612/frontend/checks.md`，所有中途 FAIL、objective修正前结果与快照保留。原31项所需层逐项见[验收表](v6-12-acceptance-cases-2026-10-04.md)，不把UNIT/Mock当PG/真实服务/实际Plan Edge。

账本实际 **45/100**，45 intents/45 receipts/该scope unknown0，剩余55；本轮真实模型请求0、产品搜索0，原搜索6/1000不变。现有授权未撤销，也未因剩余额度自动派发。Fake新18阶段 manifest：37normal+2repair=39、输出上界241664；45+39=84≤100，只是冻结Fake binding算术。真实provider binding/free preflight、首次outline账本门禁全部 NOT RUN。

保护复核：[final-invariants](../../var/v612/final-invariants.json) PASS，335历史文件hash保持，包括原45对账/授权审计、原.env、v6.5/v6.8/v6.10证据、旧公开包；未覆盖/删除旧记录。模型开发请求root Sol6.1/high、内容及页面Sol6.1/medium、只读合同复核Sol6.1/high；实际解析均 NOT OBSERVABLE；未改全局模型配置/服务模式。

## 回滚、未提交状态与下一动作

没有正式数据迁移/Seed/部署/API/DTO变更或push/merge，未收费用，旧Plan保持。4条新Fake样本所在的owned库、合成账号及快照保留；DSN/合成密码仅在本机private目录，不进入Git/报告。候选源码尚未提交；回滚应定向撤回本轮候选，先保留起点已存在的v6.11未提交工作，不能整体git restore/reset删除已有成果。保留 stopped diff、hash与新文件供后续对比。

整体仍 **STAGING_BLOCKED / NOT_READY**，本轮 **BLOCKED，STOP**。下一唯一最小动作：评审 F1 保存前按冻结权威事实重建/比对投影的有界防护方案，再决定是否独立修复这四项；本轮不执行下一开发阶段、不自动开启真实代表。
