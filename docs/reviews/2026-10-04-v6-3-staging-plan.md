# RC staging 方案与真实副本演练

状态：**STAGING_BLOCKED**，整体 **NOT_READY**。原库升级/Seed写入、正式入口切换、收费调用仍STOP；本轮只完成方案和隔离副本。

## 已执行的真实产品数据演练

源：`.env`实际 `studyplan_b3_local_48fb59cc`、0023、61表/1517行。目标：本轮新建owned `studyplan_test_v63_realcopy_a798a903`，明确与源不同、独立命名。没有使用合成fixture冒充真实产品数据恢复。

同一READ ONLY/REPEATABLE READ源事务导出snapshot，pg_dump custom从该snapshot备份。既有PG16容器只供应client工具，先核对本机/容器连接host.docker.internal的cluster identity相同；未使用/写容器自身数据库。完整archive在 ignored `var/v63/private/product-20261004.dump`，不入Git、不输出正文/密码/DSN。

归档及其专用目录已限制本机ACL为当前用户、SYSTEM和Administrators；不沿用更宽的父目录继承权限，未修改工作区其它目录或全局配置。最终archive完整性、源snapshot不变及原函数owner/security/ACL/definition在升级副本保持均PASS，证据 `final-readonly-source-audit.json`。

| 演练 | 状态 | 证据 |
|---|---|---|
| 原生完整备份/归档可读 | PASS | `var/v63/real-copy-evidence.json`，archive SHA256与exported snapshot |
| 新owned库restore、61表/1517行 | PASS | 所有表server-side行计数/摘要、column/ACL/RLS/policies/schema ACL一致 |
| 副本动态upgrade head | PASS | 实际0023→0024，63表；`migration-copy.log`；未硬编码upgrade revision |
| 副本官方immutable Seed导入 | PASS | `seed_reviewed_pack`；AI2/Agent5/Cloud2；旧Agent1/Python1完整行摘要不变 |
| 旧Plan/归属/Run/历史不变 | PASS | 除公开catalog与migration外的旧表全部count/hash不变；源库最终snapshot不变 |
| app role实际PG catalog/章节指导消费 | PASS | 三新包catalog校验digest与publication、manifest/private selection；`catalog-and-paid-budget.json` |
| hold资格 | PASS | 受控Seed/catalog校验；发布sources无hold；复用v6.2内容资格门禁，不提升TOC/候选为深审 |
| 当前frontend+copyAPI匿名Chrome | PASS | `anonymous-copy-smoke.json/png`：正常登录页、真实proxy、401、业务写403，无Mock；已查看PNG |
| 真实用户普通登录/当前与历史/刷新重登录 | NOT RUN | 已邀请用户在副本私下登录；不获取密码/伪会话/重置散列 |
| 原库写入/正式切换/收费 | NOT RUN | 实际模型/搜索新增0，Worker OFF，旧unknown不重派 |

源中Summary/Prompt/Submissions/AcceptanceReview均0，空数据已恢复相等；没有伪造非空用户原文。非空历史主链的Synthetic PG/Chrome证据另列v6.2，不替代本副本普通账号体验。

## 当前可访问的副本

- frontend：`http://127.0.0.1:5179/`，Vite当前feature入口，PID33136（本次快照）。
- copy API：127.0.0.1:8024，PID20012（本次快照），`var/v63/copy_server.py`。
- 独立cookie名；使用正常密码认证和现有RLS，不复制/重置用户密码，不伪造会话。auth login/logout可写副本会话，其余业务写入403。
- Fake配置仅作为副本无派发保护，model calls0；无Worker，也无旧job tick/unknown恢复。search/RAG/GitHub credentials在copy进程关闭；所有数据保留本机。
- 原脚本日常API8022/前端5175当前停止，未被此入口替换。

## 用户批准后的正式staging顺序（本轮未执行）

1. 重新核对正式入口/profile/HEAD，确认备份窗口与新数据增量；备份当前真实库到全新archive，不复用可能过时备份覆盖新原文。
2. 保持Worker停止，用已有合法migration role仅forward升级实际revision→repo head；保留revision及ACL/RLS审计。禁止旧published destructive downgrade。
3. 经官方immutable Seed导入下一合法三版本，核对digest；旧pack/plan不变，新生成选新包。Python2/其它包如需发布另核已有正式范围，不自动扩大本批三包。
4. 统一cap候选8192，验证绑定预算；保持source环境变量/secret本机，不提交.env。构建当前feature，再按显式API/frontend端口和origin启动正常入口。
5. **Worker独立门禁**：先只读核查现存job/attempt协议、claim/unknown与资格。精确排除旧unknown/Acceptance；未确认既有任务可领取前，不开启全局trusted_server轮询。只能对获批新合成/日常请求运行既有Worker；不新建第二调度平台。
6. 免费smoke：正常登录/空间/历史GET、已发布Seed、当前Plan/Extension/资源、刷新/重登录及跨scope拒绝。收费代表必须另获批准，在全新synthetic owned库完成。
7. 用户按 [体验清单](../acceptance/USER_ACCEPTANCE_CHECKLIST_2026-10-04.md) 主观接受；完整门禁未满保持NOT_READY。

## 回滚

代码兼容当前schema时正常revert；保留已发布新包/计划的读取兼容，不删数据。schema/data恢复采用经过验证的native backup→另一个全新owned recovery库→一致性核对→用户批准入口切换；禁止先drop/restore原库、禁止历史downgrade。确认正式切换后再决定旧入口处置，不清理未知目录或别的服务。

当前阻塞：真实用户副本消费NOT RUN；正式配置cap冲突待staging窗口修正；RAG实例/契约和付费代表另有STOP。后两者不能让独立已完成恢复证据失效，也不能宣称全产品READY。下一最小动作：完成副本正常账号只读检查；不切正式入口。
