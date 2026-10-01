# G4 成果原文、人工验收与首批 Outcome 档案

用户现在可以在当前路线的明确实践任务下保存成果说明和有来源类别的证据，回读保存时的项目、任务、知识版本及验收要求；要求补证据后，另存一条关联的补充记录。人工确认必须逐项引用已有证据、填写实际观察，并明确承认平台没有独立运行代码或核验来源。成果档案按实际保存记录归类，空分类显示待补充。

本批技术链路已 Implemented / Tested / Integrated；下述范围有真实 Chrome、HTTP 和 PostgreSQL 证据。负责人实际产品体验 **NOT RUN**。本批不代表 F01–F18、Q01–Q12 全部完成，整体 **NOT_READY**；完整 Outcome Profile、其余受控操作及全路线重规划继续实施。

## 基线、授权和归属

- 工作区 `D:\studyplan`，分支 `feat/v2-g1-user-slice`，起点 `e8faf51d0f9b0111accd25567e5246b7169581e6`。
- 代码提交 [`9cf4cdb94d8db073f98b386da89766d15be66ca8`](https://github.com/tiance002/studyplan-v1/commit/9cf4cdb94d8db073f98b386da89766d15be66ca8) 已正常 push；`git ls-remote origin refs/heads/feat/v2-g1-user-slice` 与本地 SHA 一致。只提交本批 22 个白名单文件，没有 GitHub API 重放，远端 SHA 与本地相同。
- 沿用 V2 连续实施、普通 commit/push 和专用测试环境授权。本批没有模型、搜索、RAG 或 GitHub API 派发，累计仍模型 **23/50**、搜索 **2/1000**、unknown **0**，跨日期不重置。
- 主协调实际 `gpt-6.1-sol/high`；Kuhn 复用 `gpt-6.1-sol/high` 实现事务与迁移；Gauss 复用 `gpt-6.1-sol/medium` 实现前端；Rawls 独立只读复核实际 `gpt-6-luna/max`。模型与 effort 来自本机 JSONL 的会话和 turn metadata，不以提示词或工具请求值代替证据。两位业务实现者均停止编辑后 root 才接共享文件。

## Goal / Constraints / Allowed changes / Non-goals

Goal 是成果原文和归因证据持久化、冻结任务依据、明确人工决定、不可变补充和历史，以及按实际记录归集首批 Outcome。复用既有 `PracticeSubmission`、`AcceptanceReview`、证据等级和两个权威业务表；0022 只作增量扩展及位置头、回执，不重建业务模型、Graph、队列或核验引擎。

保存和决定先验证服务端身份、项目及 active owner，再查原回执，随后重查当前批准 Plan、任务位置和三类版本。原 body/key 可以在新路线发布后核对已提交结果；新的旧位置请求不能绕过当前路线检查。客户端不能指定 actor、reviewer、grade 或 VerificationRecord。

保存原文、证据标题/正文/来源地址不做空白清洗。快照保存实际 plan/stage/task/project 和知识角色、内容版本；旧无依据记录明确 `legacy_unfrozen`，不拿当前任务补造历史。原文、评审和回执不可变；只有实际任务状态变化增加 task.version，位置头则每次新保存递增。已人工 accepted 的任务不会因后来补充的非通过决定而被静默降级。

Allowed changes 为本批 Domain/Port/Application/DB/API、0022、针对测试、共享组合根、OpenAPI/客户端类型和实践页内的独立成果及档案组件。未改既有 EvidenceGrade 或实践领域规则，没有修改已发布迁移、原服务、原库、旧 Run、checkpoint 或付费 journal。

Non-goals 为平台执行外部代码、独立核验报告/来源、模型替人作通过决定、知识 VERIFIED 或 Exposure 完成升级。新保存证据只有 reported/insufficient；note-only 按既有领域规则为 insufficient。可存 HTTP(S) 地址元数据，但不发起访问。完整目标、Outcome Profile、其余 F13 操作及真实外部集成未从 Goal 删除。

## Tests

以下测试各自证明其对应范围，不把 Fake、源码 review 或构建当作真实持久化验收。命令以工作区根为默认，前端命令从 `frontend` 执行；Python 使用 `.venv\Scripts\python.exe`，`PYTHONPATH=D:\studyplan\backend`。实际测试输入为本提交代码。

| 验证 | 命令 / 范围 | 结果 |
|---|---|---|
| 新规则与既有等级 | `python -m pytest backend/tests/unit/test_practice_submissions_v2.py backend/tests/unit/test_evidence_grade.py --tb=short` | **PASS**，exit 0，33 项，1.22s；13 新规则加 20 既有领域性质 |
| 新真实 PG | `python -m pytest backend/tests/integration/test_practice_submissions_pg.py --tb=short` | **PASS**，exit 0，30 项，43.88s |
| Cookie/CSRF、私密错误、跨账号和旧回执 | `python -m pytest backend/tests/integration/test_submission_http_pg.py --tb=short` | **PASS**，exit 0，4 项，17.64s |
| 契约 | `python -m pytest backend/tests/contract --tb=short -q` | **PASS**，exit 0；collect 确认 31 项，含 DTO、隔离契约和 committed/fresh OpenAPI 对比 |
| 生成契约和前端类型 | `python -m app.tools.export_openapi`、`npm run gen:api` | **PASS**，各 exit 0；旧 43 paths 和 123 schemas 逐项不变，只新增 5 paths |
| 成果前端 Mock | `node tests/submissions.browser.cjs` | **PASS**，exit 0，4.23s；是拦截 API 的 Chrome 测试，不是 PG 证据 |
| 原 Prompt 前端回归 | `node tests/prompts.browser.cjs` | **PASS**，exit 0，7.22s；在实践页嵌入变更后执行 |
| 最终生成类型后的构建 | `npm run build` | **PASS**，exit 0，TypeScript 与 Vite，55 modules |
| 真实手动 Chrome | `V2_SUBMISSION_ACCEPTANCE=v2-g4-20261002-01` 下 `node tests/submissions-real.browser.cjs` | **PASS**，exit 0；真实 loopback HTTP 和保留专用 PG，零模型/搜索 |
| PG 只读核对 | `python var/v2-g4/inspect_submission_acceptance.py` | **PASS**，exit 0；owner RLS、精确原文/依据、四回执及学习工作区保全 |
| 样本外部报告 | `python var/v2-g4/external_tool_report.py` | **PASS**，exit 0；自有 CLI 样本观察，作为 external_report 提交，产品平台未执行 |
| Ruff / diff / 原指导 | 9 个后端 owned 路径及 4 个 root 路径 Ruff、独立 `git diff --cached --check`、两指导 SHA256 | **PASS**，exit 0；原指导哈希保持 |
| 独立只读复核 | Rawls 对冻结契约、后端/迁移及相关测试源码的定向 review | 运行测试 **NOT RUN**；审查未发现可复现缺陷，不代替上方 PG/HTTP |
| 模型建议、真实来源核对、平台外部代码执行 | 本批不派发 | **NOT RUN**；界面/API 不显示这些能力已成功 |
| 负责人产品体验、全量发布和恢复门禁 | 后续完整 Goal | **NOT RUN** |

30 项 PG 包括精确原文/归因、owner/RLS/复合位置、错误 parent、三版本 CAS、同键同体/异体、保存/决定竞争、完整标准及证据索引、冻结依据漂移、已 accepted 补充不降级、receipt-point 原子回滚、不写学习与 Run、最新 20 条和历史分页、legacy 原数据、旧计划替换后回执和档案、SQL 不可变及非空 downgrade 拒绝。真实 lock-wait 观察后发布新 Plan，等待中的旧保存返回 409，位置头仍为 0。

HTTP 证明请求重新鉴权和 CSRF、422 不回显私密原文/非法对象、禁止客户端伪造等级/核验/身份、人工通过覆盖及限制确认、七组实际档案，以及新 Plan 后完全原 body/key 的保存和决定回放。换新 key 的旧 Plan 动作 409；账号 B 不能读账号 A 的成果/档案或回放 A 的回执。

Mock 证明原保存/决定结果未知时重试完全原 body/key、422 解锁、409 保留编辑、迟到 GET/保存不覆盖新文字、任务切换保留精确本地证据、旧路线复制及原请求核对、legacy 提示、档案分页与空分类。旧决定跨 Plan 的专门 Mock 交错 **NOT RUN**，其后端原回执恢复有 PG/HTTP 证据；不扩大为已在浏览器直接验证该交错。

## FAIL 与修复保留

后端先有缺模块的规则/夹具 FAIL，随后真实迁移后的 deliberate stub FAIL；首版 adapter 误用物理 `plan.version` 导致 6 FAIL/4 PASS，改为既有 revision/domain-version 后 PASS。测试-only publication lock 观察使用过长 application_name，被 PostgreSQL 截断；清理顺序又先等待未释放 blocker 的线程，原进程被实现者中断，exit 1，没有最终 pytest summary。保留失败，改为短 marker、释放连接先于线程 join 和有界超时，定向 barrier PASS 后最终 30 项 PASS。唯一已核实归属的中断测试库经既有 harness 清理并确认不存在；没有操作原库或全局角色。

前端最初缺成果区域和旧 unknown 请求控制分别 FAIL 后实现；两次 locator 歧义修正后 Mock PASS。Root 新 HTTP 先因未装配入口 404 而 FAIL；接线后 4 HTTP 用例通过，但包含 contract 的组合命令整体 **FAIL / exit 1**，原因是旧 OpenAPI 还未重新导出。导出后独立 31 contract **PASS / exit 0**，最终独立 HTTP4 **PASS / exit 0**；不把原组合重标 exit 0。

真实 Chrome 首次点击登录后过早 GET 工作区，401，**FAIL / exit 1**；当时没有成果保存/决定 intent。增加等待实际登录 HTTP200 与工作区加载后，以原未消费 Acceptance 再运行 **PASS / exit 0**。没有重复成果写入或外部派发。早期 failure JSON 保留。Root Ruff 先有两处 imports 和 zip strict 提示；修复后 PASS。首次 staged diff 发出 test 文件 EOF 空行错误；只删除末尾空行后独立 diff check exit 0。

## 实际 Chrome / HTTP / PG 证据

新无费用 Acceptance `v2-g4-20261002-01` 使用保留的专用合成账号、project `lpr_3b0829d7c2ce490798db5b300ae87d0a`，Plan3 `pln_a66621e6090a411c8023f6301fb29f74`，任务 `tsk_c1ec12a4deb14189b0a189cace62ee5c`。这不是负责人学习成果或产品体验批准。

1. 初次说明先存，原空白、换行和末尾字符保持。提交 `psb_972814f6818a4d0ba0d33aba130d0cd6` 为 insufficient；任务变为 awaiting_evidence/version2。明确人工记录 needs_more_evidence，未增加 task.version。
2. 外部 CLI 自有样本记录 `sum([2,3])=5`，以及字符串输入被拒绝的实际失败；Agent/model 集成、公开部署、外部仓库执行明确待实施。产品不执行该代码，这份报告按 external_report 归因，另有 user_statement 限定范围。
3. 补充提交 `psb_483fa490419442dfb2e88926379f4431` 引用第一条 parent，原记录和 needs_more_evidence 决定不变。位置头2、task.version2，保存时要求冻结于 Plan3，证据 reported。
4. 两条冻结标准分别选择已有证据和填写观察；缺覆盖或 ack 时按钮禁用。明确 ack 后服务端写 USER accepted，任务 version3；证据仍 reported，verification NULL，来源核对和平台执行 available 均 false，没有知识 VERIFIED/Exposure 完成。
5. 决定后继续编辑的本地文字保持；指定已存原文真实复制可用。Windows 把 LF 转为 CRLF，归一化后完全一致，`clipboard_exact=false` 如实记录，不声称 OS 字节完全相同。
6. 档案有项目说明与评估各1条，其余5组待补充；选择详情、回读两个保存版本及决定、刷新当前任务均 PASS。原2版 Summary、2版 Prompt、两类已有 export 及当前 Plan Exposure 全部 GET 前后一致。只读核对完整工作区除明确的任务 status/version 外不变。

ignored `var/v2-g4/` 保留原前后端 packet、raw 请求 intent/响应、preflight、前后工作区、外部样本报告、FAIL JSON、两个已查看 PNG、实际路由 auditor、只读 PG 元数据和契约对比。raw/private 材料与账号文件不提交。已完成脚本拒绝重跑；存在 intent 时必须先核对原回执，不重新派发。

## 运行环境、Rollback 与后续

专用业务库 `studyplan_test_v2g1real_2f6ac462` 增量 0021→0022；checkpoint 库 `studyplan_test_v2g1cp_e6270f82` 不改。只在核实原命令路径和端口归属后停止旧自有 practice listener22376，当前 `var/v2-g4/submission_acceptance_server.py`、exec session52925、8021/PID55044；无 worker，写入口只允许合成项目的手动成果和决定。原8000/PID43688、PG/PID8124、Ollama/PID22760、真实前端5175/PID41308及 Mock5174/PID49752未重启。不能保证未受支持的跨会话后台持续；续接须核实 live handle/端口归属。

Rollback 使用普通增量 Git/revert；不重置已保存原文、决定、回执或 fee ledger。0022 的非空 downgrade 拒绝已经在隔离测试事务证明，实际保留库不做破坏性降级。没有 merge develop/master 或 milestone 接受声明。

F12 人工存档/决定与 F14 初始实际资料归集已接通，其余按 [完整矩阵](../implementation/feature-acceptance.md) 连续推进。Q01 的全对象/RAG范围、Q07 的完整全路线历史、F02/Profile 与按目标完整归集、F03 三 Blueprint、其它 F13 操作、F17 真实 RAG、F18/Q12 备份恢复及负责人体验仍须相应证据；真实 GitHub 账号授权未接通不能以手动 URL 冒充。整体 Goal 保持 active / NOT_READY。
