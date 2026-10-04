# GR Project Candidate identity / consumer binding（2026-10-04）

## 当前结论：绑定与非收费教学 PASS；真实代表 FAIL；BLOCKED / STOP

用户现在新增能做什么：普通学习页面可把 RAGFlow、WeKnora 分别展示为一张绑定已冻结来源的候选卡，保留各自完整 guidance、仓库链接及 targeted Prompt；GR 仍只有一个“任选一个案例证明相同能力”的正式任务。这项消费能力已经 Fake、owned PG、真实 API 与 Edge 验证。唯一新收费 Run 在 A1 合同校验处失败，没有新收费 Draft / Plan。

正式工程 `D:\studyplan`，分支 `feat/n1-resource-discovery`；起始及停止 HEAD 均为 `1a3262e85296c95d3dfb4349d0d4ef83438f17da`。继承组合 v6.11/v6.12/v6.13 未提交工作树；本轮增量也未提交。没有 reset、整树 restore、切分支、push、merge。

## 保存基线与根因

- 新本机受限备份：`var/gr-binding-20261004/private-baseline`，55 候选文件及 binary tracked/staged patch；563 历史证据归档、SHA256 与 ZIP CRC 核对 PASS。旧 `.env`、账本、失败记录及 Plan 字节保持。
- 新实际 Edge RED：原 GR 显示 4 张候选卡，两个项目各重复一次，全部没有仓库链接。业务写/模型/Worker 尝试均为 0；旧失败证据未覆写。
- 原消费算法仅从 `ordered_sections` 提取 repo identity。metadata-only 资源没有固定章节，因此两个 extension 未绑定，又补两个 resource fallback 卡。
- fresh owned PG 证明同一 Plan 冻结快照已有 assignment、source_ref/version、source.source_id/version、canonical_url；两个 extension 也有对应冻结 links。来源仍为 `legacy_index`，sections=[]，snapshot_status=frozen。空章节本来合法，不代表 pending 或无来源。

## 本轮最小改动与边界

独立评审确认持久化结构能表达稳定绑定，因此采用必要的最小消费投影：已有 `StageResourceAssignmentView` 增加可选只读 `canonical_url`，更新既有 OpenAPI / TypeScript 合同；没有新增 endpoint、DB schema 或迁移。

URL 只取当前 Plan 匹配的冻结来源。assignment/stage/role/source/version 与冻结 source/view 不一致、资格未核验或存在警告时，输出 null；不读取当前 catalog 来补齐，不改变审核等级。新字段显式 null 不能退回章节 URL 绕过拒绝；真正旧 DTO 缺字段时保留既有精确章节链接消费。

ProjectStudyCard 的原冻结数据没有更强 source/candidate ID；经评审，仅以同阶段、同一冻结 Plan 两侧的唯一规范化精确 repo URL 对应到 Resource，最终卡 key 使用 assignment/source/version。标题只展示；同一绑定的指导按保存顺序拼接。不同仓库不合并；歧义或无法绑定时明确未绑定，不生成重复 fallback 卡，不用 extension URL 提升资源资格。

F1–F4 不作修复或放宽；独立 AST 核对 PlanService 仅 `_resolve` 消费方法变化，其保存、事务及保护方法保持；其余锁定合同生产文件和 Agent7/AI4/Cloud4 字节保持。课程、canonical、任务、来源资格、caps/model/temperature/repair2/RAG 均未改。

## 分项非收费验收

| 验收项 | 状态 | 实际证据 |
|---|---|---|
| 冻结来源身份/版本/URL与 metadata-only 合法消费 | PASS | 后端15反例；身份、版本、警告、资格、URL冲突输出null；保留RED |
| F1–F4及相邻资源合同 | PASS | 定向134测试；原独立 checkpoint/owned PG 证据与源码输入保持，未重做已完成切片 |
| 前端唯一绑定、歧义、不同仓库、标题变化、null及未审核来源 | PASS | 前端27测试，build PASS；反例RED→GREEN留存 |
| 未来新 Fake Plan / owned PG | PASS | 新隔离库1完整RAG案例，37 Fake请求，canonical/rubric/practice/A2/关系/确认/读回；GR2来源、1任务、资格和空章节保持；测试库按fixture回收 |
| GR普通页面 | PASS | 实际 API→owned PG→Edge：RAGFlow/WeKnora恰2卡，各自562/556字符guidance、正确冻结链接、targeted Prompt和剪贴板；正式任务1 |
| 多教学单元和路线 | PASS | A2可见3单元/1canonical/1任务；A5 Framework/A6 MCP/A8小型核心；G0–G6/GR/GT保留 |
| Long guidance | PASS | 独立合成1119字符两续片，页面/Prompt/剪贴板完整；另一候选独立 |
| System/MCP/Node及刷新重登录 | PASS | 五场景初始/refresh/logout/relogin精确API读回；Node任务仍使用已有Node.js API载体 |
| 旧v6.8 live PG | PASS | fresh真实应用/PG消费原已确认Plan，原资源/extensions/tasks/manifest保持 |
| 旧v6.10 live PG | PASS | 原收费Run仍failed，原6笔provider回执留存、零Draft/Plan；只读查看，不重发 |
| 旧v6.10 Fake Plan live消费 | NOT RUN | 原Fake数据库已不存在；未创建替代，也未伪称有旧Plan可消费 |
| 实际 binding / 免费 DNS、原endpoint guard、验证TLS | PASS | 模型HTTP0；按actual18-stage manifest和现有权威账本核算 |

Edge GREEN记录233 HTTP、登录10/退出5，业务写/生成/confirm/provider/Worker/external请求0；自己的API/Vite已停止。这里的Plan来自已确认Fake数据，未称真实生成通过。

## 唯一真实代表与 STOP 原因

新 Acceptance：`gr-binding-agent7-rag-synthetic-329770a29268`。

唯一 Run：`run_5141feb22038497cabfaac09b14ba8ee`。仅新 owned 业务/checkpoint 两库；原库、正式入口与正式 Worker 未操作。

实际冻结来源 Agent7 / `agent.application` version7；18阶段 A0–A8、G0–G6、GR、GT；新 outline/structure/focus 合同保持。预算按实际 manifest 为37 normal +2 repair=39，输出上界241664；起始45/100，理论最坏84/100。

| Outline对比 | Provider真实值 |
|---|---:|
| v6.5 input tokens | 209,998 |
| 本轮 input tokens | 3,673 |
| 实际下降 | 98.2509357232% |
| 本轮 output tokens | 1,189 |
| finish_reason | stop |
| length/truncation | 未发生 |

首笔真实JSON、18阶段键、token usage、finish_reason及持久账本门禁 PASS 后才开始 structure。A0 canonical保护 PASS。A1 normal响应及两次local repair均被教学合同拒绝；所有5笔HTTP/provider响应均已知成功、finish_reason=stop，Run是逻辑合同失败，unknown0。A2及以后structure、全部practice、新Draft/Plan、收费后confirm/Edge均 NOT RUN。

原5份provider body bytes和解析JSON均保留。针对最后repair原响应的离线只读归因 PASS：units[2] 写“**不要求**照搬其工程结构或**新增工程任务**”，既有 `extra_required` 正向匹配命中“新增工程任务”，否定识别未覆盖“新增”。诊断副本仅去掉该否定新增任务句后，presentation错误由1变0；原响应/历史和生产代码未改。这是新发现的F2否定语句变体，超出本轮GR-only修复范围；按最新用户“不修改F1–F4”要求 STOP，不放宽校验、不追加repair、不重跑。

实际新增3 normal +2 repair=**5收费请求**，累计 **50/100**，剩余50；provider实报总input15414/output5038 tokens。本轮及当前授权受控unknown0；历史其他Acceptance unknown继续原样保留。搜索新增0，旧6/1000保持。没有第二Run、synthetic confirm、Plan改写或生成完成后的额外模型调用。fresh只读PG再次核对恰1Run/5回执/unresolved0/零Draft、Plan、业务物化，job终态且无活动租约；原始harness中stop布尔保留原值，不作为后续派发授权，当前Goal明确BLOCKED/STOP。

## 证据、风险、回滚与下一安全动作

本机证据根：`var/gr-binding-20261004`：baseline/backup-verification、binding-review、scope-invariants、postpatch-review、backend-red/green/targeted-contract/future-fake-pg XML、edge RED及green/checks、legacy-pg/postpatch、nonpaid-gate/free-preflight、paid原始响应/outline-gate/run-report/a1-offline-attribution、final-invariants。私人凭据/DSN仅在本机受限目录，不写入文档。

绑定源码与非收费教学 **PASS**；真实代表 **FAIL**；当前整体 **STAGING_BLOCKED / NOT_READY，BLOCKED / STOP**。新的F2变体会阻止合法否定文本完成生成；不可把非收费PASS当完整交付READY。来源metadata-only不代表全仓源码、运行或部署已核验。

回滚只可定向撤销本轮新增只读字段/绑定消费增量，参考受限组合基线、binary patch及HEAD对象；不得整树restore、覆写既有v6.11–v6.13或删除历史证据。下一安全动作是审阅已保存A1 normal/repair原响应及独立失败归因；另行Goal决定F2变体后续范围，未授权第二收费Run。当前不自动继续开发、部署、推送、合并或修改RAG。

开发请求模型：root/review `gpt-6.1-sol/high`，独立前端/PG/预检准备 `gpt-6.1-sol/medium`；实际解析全部 `NOT OBSERVABLE`。没有修改全局模型配置。
