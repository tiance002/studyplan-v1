# Planning V2 Item8 — Replanning & Revision

日期：2026-10-08。R0独立只读预检PASS；R1～R3尚未实施，不提前声明功能验收。

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

## 后续证据

R1～R3需补充精确路由/Preview/Confirm调用链、protected history与future处理、来源与Hash/CAS、owned PG/HTTP/恢复、每阶段独立发现与修复、checkpoint、未运行项。真实外部语义与Item9 UI NOT RUN。
