# Planning V2 Item8 — Replanning & Revision

日期：2026-10-08。R0、R1独立审查PASS；R2～R3尚未实施，不提前声明整体验收。

## 基线、授权与停止条件

Start HEAD `6b291d10ab439bc37a540a626174941cc90fd28b`，分支 `feat/n1-resource-discovery`；tracked clean，仅已有受保护未跟踪目录，未访问或修改。用户授权R0～R3连续实施、独立审查及范围内修复、本地checkpoint；产品模型/搜索/Reader0，正式generate关闭，无正式数据写入、migration、push/merge/deploy、Item9。遇冻结合同变更、必要migration或无法安全承载/发布须STOP。实际开发模型解析NOT OBSERVABLE，不改全局配置。

## R0：已有实现与最小路径

- 复用Item7完整Compiler、typed快照、PG持久化、Run/Worker/Receipt/预算、Draft编辑、当前hash确认、原子Publication及current/history。
- 旧PlanChange/PracticeChange会构造不携带V2快照的Draft，现有marker↔snapshot双向校验会拒绝发布；不能直接作为V2入口，更不能移除marker绕过。复用其独立的progress basis/版本锁/幂等事务职责，不恢复Seed/added_topic_route/generated操作的业务权威。
- 局部路径采用有界服务端操作与冻结Capability/Outcome/约束比较，不提供任意结构编辑；优先支持未来阶段说明和真实前置合法的顺序调整。删除required、修改项目方向/目标或来源降级不得伪装局部修改。
- 语义路径接收明确新GoalSpec，以新Run进入同一Item1～7，绑定原current Revision/来源/hash、目标diff、进度basis与新manifest。不重新使用旧failed/unknown身份，不自动发布。
- 不明确的自由文本保持needs_clarification，不通过关键词、Seed或客户端is_semantic=false判定。
- 历史成果继续属于原Revision；完成、开始、未开始与用户learner claim独立。跨版本引用只用精确旧Revision+stage identity及验证过的lineage，不复制进度或自动升级mastery。
- 新增必要typed revision basis/lineage只利用现有Draft/Revision JSONB与hash机制，不建设第二历史系统。Preview/确认/恢复实际消费basis，并在原子发布事务核查current及进度未变化；变化拒绝。
- 新Run预算与祖先/相关重规划请求历史绑定，不能通过重新规划退款、重派unknown或增加总上限；详细共享方式在R2实现前由关键逻辑负责人核对，不能只记录未消费字段。

R0独立审查PASS：现有JSONB/Publication/精确stage remap足以承载，无合同/migration硬阻塞。验收门禁是typed revision context进入hash/序列化/remap/真实消费者，完整progress basis在既有项目锁内重算；预算必须累计祖先及并发siblings的reservation/excess/candidate与unknown阻断。R0未运行unit/PG/HTTP（NOT RUN），不把这些待实现项记为功能PASS。完整原始指令及baseline哈希保存在本机ignored证据目录 `var/planning-v2-item8-20261008/`；原378份账本/历史证据和.env不改。

## R1：有界 Local Change

实际调用链为受认证/CSRF/project scope保护的HTTP → `V2RevisionService` → `PgV2Revisions` → 当前Revision/进度basis冻结 → 原V2Snapshot重编译 → 新typed Draft/hash → 用户确认 → 原`PlanPublicationService`/PG事务 → 新Revision/current。新`V2RevisionContextV1`只存现有JSONB，进入Draft hash、Revision fingerprint、序列化和发布guard；不改`V2ExecutionSnapshotV1`字段合同，不另建历史表或队列。

路由：`GET /api/v1/plans/v2/changes/context`、`POST .../classify`、`POST .../local`、`GET .../{draft_id}`、`POST .../{draft_id}/confirm`及`.../cancel`。首轮Local仅支持未来stage title/what_to_learn及完整阶段排列；所有required outcomes、任务、资源、项目方向和真实prerequisites由冻结快照/Compiler校验。其他操作不通过任意JSON编辑绕过；未知自由文本返回needs_clarification。客户端is_semantic、GoalSpec或source_override等额外字段拒绝。

`V2RevisionContextV1`冻结actor/project、原plan/revision/structure和manifest hash、progress_basis、change_diff、精确lineage、approved_goal_spec、budget_root_run_id、input_hash/context_hash。ctx没有指向新manifest的反向hash，避免循环；R2新manifest将单向绑定ctx。Local的approved_goal_spec为null。Preview展示保留/修改阶段、说明与顺序的前后值，以及outcome/prerequisite/material/practice不变事实。确认核查本次Draft hash、原base version、当前Revision及完整进度basis，使用既有项目锁和Publication原子切换；成功重放仍校验hash/base version，同身份异体拒绝。

进度basis按精确Plan/Stage读取Exposure、Summary/Prompt/Practice历史、heads、用户验收review及来源快照；Stage完成仍需本版本Summary与全部linked tasks用户accepted。Exposure阅读完成不升级掌握。连续Local沿经校验的父Revision结构/hash与sourceStage/hash递归保留历史保护，不靠标题。原学习记录不复制、不写回。`GET /workspace`独立输出`historical_learning`（source_plan_id/source_revision/source_stage_id/started或completed）和`historically_completed_stages`；新位置自己的completion/progress仍独立，防止把历史事实冒充新版本完成。current的v2_revision.history也持续指向真正原始证据。

独审首轮发现连续Revision历史保护/消费丢失，以及未知领域合法Local缺可信审批两项。前者通过精确递归lineage、只读workspace投影及第2/3Revision实测修复。后者允许服务端注入原可信DomainApproval，覆盖重编译和Publicationguard，缺审批继续拒绝，不能信任snapshot自报审批。**默认composition未注入未知领域审批，默认未知领域Local仍不可用**；受控装配可用，不能宣称默认路径全支持，也不增加模型审核调用。

测试证据均保存于本机ignored `var/planning-v2-item8-20261008/`：

| 层级 | 实际证据 | 结果 |
|---|---|---|
| RED | r1-unit-red（缺模块collection）、api-local-red（路由缺失）、r1-reorder-red（知识链接顺序错误） | FAIL；collection不冒称行为RED |
| 核心/PG | r1-closure-final.xml：8 unit + 10 owned PG | PASS，18例；包含合法重排/前置拒绝、hash/异体幂等、历史成果、连续started/completed、来源失效、review freshness |
| 受影响快照/发布 | r1-affected-offline.xml | PASS，实际50例；最初错误argv/0例不作为PASS，保留失败记录 |
| 独立未知领域反例 | r1-unknown-probe.xml | PASS，缺原可信审批拒绝/提供原可信审批接受 |
| 真实cookie/CSRF/PG | r1-http-pg.xml第一例 | PASS，认证、scope、preview/confirm/current/history/fresh login、stale、cancel、成功后错误hash/version重放、public generate503 |
| 连续历史HTTP/DTO | r1-http-history-green.xml：历史HTTP1 + DTO2 | PASS，3例；原r1-http-pg第二例FAIL仅测试期望422与既有domain400不符，修测试后定向收口，原XML保留 |

不累计重叠复测冒充新增覆盖。其他中间FAIL也保留：lineage-reader-red的review join局部变量shadow导致3FAIL，修复后定向4PASS及最终18PASS；history测试错误异常类型断言已修。新owned业务库用既有0025、新checkpoint库只初始化既有PostgresSaver，roles_created=[]，库保留；无migration、正式库写入或真实外部请求。根与实施者各自源码hash packet已冻结供独审，Ruff/diff检查PASS。

R1独立审查最终PASS：实际源码、18/50例XML、两个不同HTTP用例读回及12+9文件hash逐项核对一致。连续历史与确认重放缺陷关闭，默认未知领域注入限制保留；未知领域装配后的PG/HTTP NOT RUN。允许本地R1checkpoint后继续R2，不代表R2预算/恢复或真实外部语义已验收。

## 后续证据

R2～R3需补充Semantic同链、祖先/sibling预算累计、新Run/Manifest绑定、恢复与unknown/CAS测试、最终独审和checkpoint。真实外部语义与Item9 UI NOT RUN。
