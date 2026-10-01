# G2资料角色与受控主线替换验收

日期2026-10-01；feature分支feat/v2-g1-user-slice。整体成品NOT_READY，本报告不代表负责人接受里程碑。

本批代码已正常推送到GitHub，commit `a294078b590d0f8a5d04c652b0c7d0af22fd8aea`；ls-remote核对与本地相等。无历史重写、develop/master合并或milestone标记。

Goal：六种资料角色、作者目录连续区间、用户查看差异后发布新的计划版本；保存当时公共来源标题/URL/章节/版本，私人资料沿用由用户明确决定，旧进度与历史保留。

Constraints：不改已发布Seed v1/v2或旧迁移，不伪造模型Run，不恢复旧checkpoint/Draft，不操作原服务和原业务库，不运行外部代码，不新增真实模型/搜索调用。复用原PlanPublicationService与版本构造，在同一PG事务内发布、沿用资料和保存回执。

Allowed changes：角色/连续性与完整目录Port、增量0016/0017、ordinary proposal应用与API、正式资源快照及必要旧publisher接线、客户端和针对性质测试。Non-goals：通用MCP Runtime、自动证明知识覆盖或教学质量、GitHub账号授权的真实验收及缺配置RAG调用。

## 已核对证据

| 验证范围 | 状态 | 证据 |
|---|---|---|
| 六角色/连续区间/资源规则/provider prompt（仅Mock） | PASS | 实现者58项，exit0；主线按完整目录rank检查，允许稀疏索引，拒绝倒序/重复/漏章 |
| 六角色DB CHECK及完整目录只读Port | PASS | 实际隔离PG2项，exit0；首次迁移FK及临时表夹具FAIL已修并保留记录 |
| 受控v3 Seed/角色/发布/幂等/版本保留 | PASS | Root组合37项，exit0；先新文件缺失FAIL、错误消息匹配FAIL，再定向修复 |
| 出版/资源规则/新快照的哈希与身份重映射 | PASS | Root组合76项，exit0 |
| 更新v3后的G1纵向/私人资料/偏好回归 | PASS | 实际隔离PG20项，exit0 |
| 后端离线unit+contract组合 | PASS | 551项，exit0；2个skipped为NOT RUN；发生在后续P1修复前，不冒充修复后所有输入重跑 |
| 新接口真实Cookie/CSRF/HTTP/PG纵向 | PASS | Root1项，exit0：仅预览、同键缓存、客户端actor拒绝、提示确认门禁、revision2、原回执及匿名拒绝；首次夹具缺导入和HTTP状态断言FAIL已修 |
| Mock Chrome界面 | PASS | 连续区间/显式沿用策略/确认勾选/取消/精确重试/409保留/GET刷新预览/新版本未开始；零提示时确认框语义先FAIL再修复PASS |
| 前端构建/单元 | PASS | 47模块build及4单元，exit0；契约按实际OpenAPI生成 |
| 受控替换并发与最终关键PG组合 | PASS | 实现者最终20项，exit0、35.89s：2规则+17实际proposal PG+1G1关键生成回归；独立review两项P1实际RED4→GREEN4，含新增/移除/等量换绑及锁等待跨lease |
| 修复后HTTP/G1/Seed PG组合 | PASS | Root8项，exit0、25.66s；验证最新schema/选择摘要/lease后检查输入；未重复整个551离线组合 |
| 保留专用库的Chrome真实替换/刷新/旧历史 | PASS | 新AcceptanceId v2-g2-20261001-03，revision2、私人绑定沿用2、旧Exposure保持原值、新Exposure全version0/未开始、刷新回读；调用计量20/2 unchanged |
| 负责人实际体验 | NOT RUN | 待完整功能链与负责人明确验收 |

## 内容与历史

严格连续性检查发现已发布agent v2的stage.context主线选择目录5和7，跳过retrieval第6章。新增受控[agent v3](../../backend/app/infrastructure/content/agent-application-v3.json)，只修正为5–7区间并保存publication_lineage；保留v1/v2原文、公共来源原审核日期，未宣称新增网页审核。当前bootstrap和新测试夹具使用v3，旧计划仍引用其原发布包版本，旧v2不能通过新的严格导入。

新正式计划来源快照涵盖标题、作者、URL、章节和版本。缺少当时快照的历史记录明确标为未知，当前目录值只能供参考，不能称为历史确认事实。资料候选/章节映射、自述进度均不是Verified掌握证据。预览显示已记录先修、知识映射缺口、必需补缺、章节工作量、未知时长/环境/节奏，以及新Exposure从version0起步。

独立review发现并以实际PG重现两项P1：预览后新增/移除/等量替换私人资料导致确认时复制未预览的集合；source锁等待发生在生成lease检查之后，可跨越lease期限继续存草案。已同事务比较选择身份/快照摘要，并在新锁等待后重查原fence；4项实际反例先FAIL再PASS。有限SECURITY DEFINER只锁既有公开reviewed source/sections、固定search_path、撤销PUBLIC执行；不授予目录写权限或修改全局角色。实际PG证明app直接UPDATE被拒绝，FK新章节插入等待确认事务释放。

真实Chrome第一次FAIL发生在成功发布后的脚本回读断言：SelectedResourceView的候选位于resource子对象，脚本误按顶层读取沿用说明。保留已创建proposal及确认回执，修正断言后仅GET读取同一结果继续PASS，没有新预览、再次确认、再生成或付费调用。最终确认回执proposal rcp_9cd4544e18a64afb97581750721b1036、plan pln_00f8fb6d8a35407cb00238f5f50ed20d，截图已视觉核对。

Tests/Evidence：原始实现者和浏览器测试报告位于忽略目录var/v2-g2；本次用户服务计量仍模型20/50、搜索2/1000，不重置预算。

模型路由补充审计：原工具返回未给实际模型，后经本机JSONL父线程/agent_path与turn_context核对，Gauss为SolMedium、Kuhn为SolHigh、Helmholtz为SolMedium、Lovelace为SolHigh。本轮复用现有代理且新spawn达到thread limit；没有Luna Max运行证据，也不把任务提示中的模型声明当实际路由。最新审计和后续展示要求见[唯一当前进度](../implementation/progress.md)。

Rollback：通过feature分支正常revert应用代码保留历史。0016/0017增量迁移仅用于专用studyplan_test_*；非空proposal/回执历史拒绝破坏性downgrade。原库、原服务、收费journal与历史Run不改动。本批正常commit/push核对后在当前进度记录远端SHA；不合并master或声明完整Goal完成。
