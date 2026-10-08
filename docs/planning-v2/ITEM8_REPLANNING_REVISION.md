# Planning V2 Item8 — Replanning & Revision

日期：2026-10-08～09。R0、R1、R2独立审查PASS；R3尚未开始，不提前声明整体验收。

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

## R2：同链 Semantic Replanning（独立审查PASS）

入口`POST /api/v1/plans/v2/owned/replan`要求明确`current_plan_id / expected_version / idempotency_key / goal_spec`，拒绝客户端model/budget/actor或is_semantic覆盖。薄Application → PgV2Revisions在现有计划/owner锁内冻结原current、progress、批准GoalSpec与目标diff；复用PgPlanningJobRepository的同事务enqueue写新Run/submission/Job。异常使所有入队行回滚，避免连接间owner FK自锁。Owned工厂、仓储与Jobs必须同一业务DSN，业务与checkpoint仍为独立loopback新owned库；默认runtime未装配保持503。

新Run实际进入原`V2PlanningRuntime.execute`：Item1 Profile → Item2 Capability → Item3 Coverage → Item4 Gap → Item5 Research → Item6 Curriculum → Item7 Compiler/P2 persistence。原current直到显式确认后才切换；失败、incomplete或unknown不会替换原current。相同请求身份同体仅返回原Run，不再派发，异体409；不恢复历史failed/unknown、不调用旧catalog/selector/outline/structure/practice。

原进度事实和来源仍属于精确旧Revision。Semantic不靠标题把旧完成状态映射为新Stage或accepted_known；原历史由v2_revision.history展示，新增教学来自新Profile/Capability/Compiler。新GoalSpec不能借过去无证据事实伪造掌握；已有用户项目独立保留为user_project载体，不混为Project Study案例。新的完整GoalSpec利用已有字段持久化，并与ctx/durable manifest及Profile结构化字段逐项绑定；Local后续只能精确继承。

Run运行时manifest单向绑定ctx.context_hash；Compiler ExecutionManifest仍由编译快照独立核验。ctx不为展示新结果而重哈希，user_content(execution=...)从冻结ctx和合法当前编译快照确定性展示前后阶段、outcomes/prerequisites、教材版本、实践/项目和unresolved。默认ctx历史投影与R1保持兼容。

预算读取原durable root submission的冻结上限。同actor/project/root的祖先和所有siblings累计reservation、实际excess、candidate、请求/搜索/正文等计量；派发和settlement共用root锁。取消不退款，未知/已派发未结算不通过新身份绕开；新工厂提高cap、偷换root或跨库依赖直接拒绝。Local→Semantic的后续版本仍使用同一root，没有新ledger或额度平台。

| 验证 | 证据 | 结果 |
|---|---|---|
| R2行为RED | r2-red.xml 3例；最初system python缺psycopg属于collection失败，另记录 | FAIL，真实业务RED使用.venv执行 |
| 真实PG主体 | r2-closure.xml | PASS，8例：同链/确认、共享cap并发、unknown、配置/DSN、progress stale、ctx/两类manifest、原子rollback |
| 最终源码goal/root/恢复 | r2-goal-root-recovery.xml | PASS，2例；与上行semantic重复1，合计9个不同PG用例，含semantic→local→后续semantic同root、缺GoalSpec/原文/结构化事实篡改拒绝、fresh Worker回执恢复零新增模拟派发 |
| 受影响离线 | r2-affected-offline.xml | PASS，15例，不重复全Item7矩阵 |
| HTTP真实owned PG+cookie/CSRF | r2-http-pg.xml | PASS，4例：两个Local兼容、新Semantic字段/用户项目/accepted_known/明确确认/fresh readback、并发确认CAS |
| DTO | r2-api-red.xml / r2-api-green.xml | 缺路由RED1 FAIL → GREEN3 PASS；客户端预算/model/is_semantic/错误GoalSpec等拒绝 |

HTTP的Provider/Search/Bodies是明确合成响应，Item1～7 Validator/Compiler/DB/认证链实际执行。Python claim不会进入learning stages，已有JSON CLI载体和完整GoalSpec读回PASS，只证明机械保全及接线，**不证明真实模型语义理解**。真实产品模型/搜索/Reader0。

中间失败完整保留：first-green 2PASS1FAIL/diagnostic定位原goal_spec非空保护，随后增加精确typed绑定；expanded 7PASS1FAIL发现Compiler清单替代runtime清单在工厂索引model_ref时抛KeyError并留running，随后在工厂前manifest_intact拒绝并分类为RecoveryBlocked，最终closure通过。不是以放宽Schema、修改旧历史或增加调用追绿。R2实施与HTTP源码hash packet已冻结，独立审查尚未给最终结论，不提前声明R2完成。

2026-10-09续接独审确认P1：原`/owned/generate`在已有current时仍创建无revision context的新root，绕过祖先预算/unknown/basis；无current但已存在初始Run时也可能重复创建独立root。真实HTTP `r2-initial-http-red.xml`复现202并新增Run/Job/submission，不作为通过证据。正在同一边界修复：初始root在项目锁内原子准入、同项目已有root任何状态拒绝新root、无ctx非零expected submission/Worker拒绝；不改历史Run，不为失败/unknown建立自动重派平台。R2仍未提交，独审未PASS。

同一闭包还检查修复前持久化的多个初始root：只关闭新入口不够，旧queued Run、已保存Draft的generic确认及后续Semantic root解析也必须拒绝歧义；共用durable submission/root校验，不删除或重写历史。实际`r2-gate-legacy-double-root-red.xml`已复现2 FAIL。另发现Semantic Draft持久化之后与最终checkpoint/Run终态之间的发布时序：外部Local先发布应使旧Semantic明确终结冲突；精确本Run的Draft先合法发布应完成succeeded，不能卡在running或误报失败。这两窗口由同一实际PG反例矩阵收口，不能用通用忽略CAS替代。

完成恢复另用`r2-gate-own-published-recovery-red.xml`真实复现1 FAIL：草案持久化后确认，模拟最终checkpoint中断，fresh Worker将已发布本Run误标failed。修复只投影精确approved+Publication/hash/typed snapshot/context绑定的本Run结果，并继续fence及原goal/source/domain冻结校验；一般dispatch仍按旧basis严格检查。新的publication budget校验只在mutation路径开启，不能让多root历史的current/history读取失效。最终源码与PG证据仍待独审收口。

Owned初始入口的有限恢复边界：尚无current但原初始root已failed/needs_clarification/cancelled/unknown时，本轮不允许通过新初始身份再分配预算；需显式核对原Run。Item8面向已有current的修订，本轮不建设原失败Run恢复平台。


### R2独审闭包的最终执行证据

- `r2-final-closure-green.xml`：PASS，42例＝25个新owned PG场景+17离线场景，0 failure/error/skipped，实际228.443s。源码在own-published完成恢复补丁后冻结；此大包早于最后一次原冻结输入校验的顺序前移。
- `r2-final-completion-input-green.xml`：最终源码PASS，3个owned PG场景，实际50.750s；精确本Run完成恢复、goal漂移与source facts漂移。仅将原比较前移至early completion之前，其他普通派发逻辑不改。own恢复与上一包重叠1例，两个XML合计27个不同PG场景+17离线场景，不把重跑累加。
- `r2-initial-http-green.xml`：PASS，2例（23.541s），existing-current初始请求409且Run/Job/submission零增量；合法Semantic HTTP仍同链成功并可确认。先前实际202/+1各行的RED保留。
- RED与诊断均保留：准入6 FAIL、无current历史root3 FAIL、旧双root2 FAIL、CAS/publication组合5 FAIL1 PASS、own完成中断恢复1 FAIL；中间reader/RLS诊断失败及对应修复均记录在`r2-business-closure-packet.json`，不隐藏失败。门禁仅mutation开启；reader保留原来源/hash/实体校验，历史歧义不屏蔽旧事实。
- `PgRunRepository`原SHORT_GENERATION_VERSION已批准草案分支保持；其旧真实PG fixture要求现已禁用的public generate202，本轮NOT RUN，不为跑旧fixture重新开放入口。

最终业务源码HTTP `r2-final-business-http-green.xml`：PASS，2例，22.76s；仅复测existing-current409/零行增量与合法Semantic整链确认。与先前相同HTTP场景重叠，不另加用例数。

业务14文件最终hash、前后两份source版本与各XML绑定冻结在`r2-business-closure-packet.json`；root API/HTTP7文件冻结在`r2-root-gate-packet.json`。R2最终独审PASS：实际14个业务文件与7个API/contract文件hash一致，42+3例的source时序、最终2HTTP XML/hash已核对；无剩余actionable P1，可以创建本地R2 checkpoint。独审回执保存在`r2-review-receipt.json`。R3尚未开始。

## 新增事实的实际消费者矩阵

| 事实 | 冻结/存储 | 实际消费与拒绝边界 |
|---|---|---|
| actor/project | 服务端scope与typed context；现有Run/submission/Draft/Revision JSONB | PgV2Revisions owner/RLS核查、冻结submission与budget族归属；请求不能自报actor |
| base plan/revision/structure hash | V2RevisionContext | Preview、保存/发布guard与恢复检查服务端current；旧Preview不能覆盖新current |
| base execution manifest hash | 原V2ExecutionSnapshot的Compiler清单摘要 | 精确旧版本/lineage核验；这不是Run运行时清单 |
| progress_basis/hash | 精确旧位置的records/heads/reviews/source snapshots及stage facts | 在计划锁内重新捕获，学习/成果或来源变化使Preview失效；不按标题继承 |
| lineage/history source | source plan/revision/stage/hash与目标stable key，JSONB/hash保留 | Local递归历史保护、current/workspace历史展示；Semantic保留原记录引用，不猜新旧阶段关系或自动mastery |
| Local change_diff | 有界future说明/排列前后值 | Compiler重编译与冻结语义比较；用户实际看到新说明和顺序，不要求新Draft hash等于初始Curriculum hash |
| approved_goal_spec | Semantic context + 新Run initial；现有Plan GoalSpec字段精确绑定 | Item1重新生成Profile；scope/depth/starting_point/purpose/project_context与Profile一致，原目标hash与durable submission绑定；Local仅精确继承base |
| Semantic diff | ctx保存批准目标差异和原future/source/practice事实；新facts来自当前合法compiled snapshot | user_content(execution=...)只做确定性投影，展示新旧阶段/outcomes/prerequisites/material versions/practice/unresolved；不回写ctx hash |
| runtime manifest / v2_revision_hash | 新durable submission，单向绑定context hash | Worker、PgV2Calls、checkpoint与P2 bridge一致性校验；不能用Compiler清单替代运行授权 |
| budget_root_run_id | context与原durable root/sibling submissions | budget_family/PgV2Calls按同actor/project/root累计请求、reservation/excess/candidate及unknown；Local后续不换root，新Run不退款或扩上限 |
| input_hash/context_hash | 规范化请求/冻结context | 同身份同体复用、异体拒绝；context进入Draft hash/Revision fingerprint和runtime单向绑定 |
| 实际发布内容/hash | typed snapshot、Draft content_hash、Revision structure_fingerprint | 专用及generic明确确认、Publication原子事务、current/history fresh readback |

没有新增第二Planner、独立版本历史表、业务队列或review平台。原Item1～6领域语义、Policy、Schema、Prompt和审核映射不变。Item8对现有V2 goal_spec非空保护只允许带合法context的精确绑定，不放宽无绑定旧路径；`V2ExecutionSnapshotV1`字段集合保持不变。

## 后续证据

R2独审已收口，checkpoint后进入R3；仅补受影响可靠性与最终保护/contract/collection，不重跑完整Item7。真实外部语义与Item9 UI NOT RUN。
