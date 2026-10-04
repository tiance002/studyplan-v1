# StudyPlan 下一批 Goal：正式运行收口，不再扩产品功能

## 0. 当前权威状态

上一 Delivery Acceleration Goal 已完成并 STOP。

当前已成立：

- A6 MCP 10.1 来源修复 PASS
- Agent application v8 不可变内容包 PASS
- 46 resource slots / 74 ordered refs PASS
- 原38份真实响应 replay PASS
- owned PostgreSQL / checkpoint PASS
- synthetic confirm / fresh readback PASS
- Edge/API 完整学习闭环 PASS
- 唯一新真实模型代表 PASS
- 37 normal / 0 repair / unknown 0
- 产品模型累计 125/200，剩余75
- 第一份代表 PASS 后已停止继续收费

不得修改旧 Agent7、旧F2 Run/Draft、旧45/46 FAIL、旧response/receipt、旧账本和历史证据。

当前目标不再是增加产品功能，而是使现有功能达到可以正式运行的状态。

---

# 1. 本轮优先级

严格按以下顺序执行：

P1. 正式 Planning Worker 的 runtime budget + admission 收口  
P2. 最新原数据库副本 native restore → forward 0024 → AI4/Agent8/Cloud4 导入演练  
P3. 准备用户本人非空 Plan 的 RC 验收入口  
P4. 输出唯一正式操作授权包

不要跳过 P1/P2 直接操作原产品环境。

---

# 2. P1：Planning Worker budget / admission

## Goal

证明普通日常 Worker，而不只是 acceptance wrapper，能够：

- 使用冻结 submission / manifest 的预算；
- 在 provider dispatch 前执行 request/output budget；
- 不重新派发 historical failed / unknown；
- 正确处理 lease / cancel / fencing / retained known result；
- 使用明确 admission 策略。

## 已知缺口

当前静态审查发现：

PlanningRuntimeFactory 构造 PgAttemptLLM 时，生产路径尚不能证明冻结 manifest 已传给 ledger。

因此历史 acceptance wrapper 的累计 quota 不能作为普通日常 Worker 的预算证明。

## Allowed

允许：

- 定位实际 runtime / factory / PgAttemptLLM / worker claim 调用链；
- 对已有实现做最小必要修改；
- 修改针对性测试；
- 新建 owned PG / checkpoint DB；
- 使用 Fake/provider stub；
- 启动仅属于本轮的临时 Worker/API；
- 运行确定性 PG、queue、lease、budget、admission 测试。

## Forbidden

不得：

- 调用真实付费模型；
- 消耗当前剩余75次额度；
- 修改模型/prompt/output cap；
- 增加 repair 上限；
- 建新预算系统；
- 引入 Redis / Celery / 新调度框架；
- 写原产品库；
- 启正式 Worker；
- 重派旧 failed/unknown Run；
- reset / restore 整树；
- push / merge。

## 必须验证

至少覆盖：

1. manifest request budget 正常绑定；
2. manifest output budget 正常绑定；
3. 第 N 个合法请求允许；
4. N+1 在 provider 前拒绝；
5. output budget 将超额时 provider 前拒绝；
6. repair 仍最多2；
7. unknown 不 claim / 不重派；
8. failed 不被自动重新生成；
9. known persisted result 按原规则 replay；
10. expired lease / fence / cancel 原语义不变；
11. admission 非授权 actor 拒绝；
12. authorized Worker 可处理新 owned Run；
13. restart 后预算数据仍有效。

不要为了“更完整”扩大为整个 Worker 重构。

P1 PASS 后直接进入 P2，不再次申请普通开发授权。

---

# 3. P2：最新原库副本恢复与内容导入演练

## Goal

证明今天实际原产品库能够：

READ ONLY backup
→ native pg_dump(custom)
→ 全新 owned restore DB
→ 完整一致性核对
→ forward migration 0023 → 0024
→ immutable AI4 / Agent8 / Cloud4 import
→ 应用只读/合成验证

整个过程不改变原产品数据库。

## 前置

先重新读取实际：

- HEAD
- migration head
- 原产品 DB revision
- 当前 published pack versions
- CURRENT_PACKS
- AI4 / Agent8 / Cloud4 文件 digest

不要复用 10月4日旧快照冒充当前状态。

## 恢复前记录

至少记录：

- schema revision
- table count
- row count
- user/project/plan/publication summary
- ACL / RLS / policies
- immutable pack versions
- source/version summary
- critical function ownership/security attributes

不要输出密码/DSN/token/原始私人正文。

## restore

使用 PostgreSQL native custom dump。

恢复到新的 owned DB。

先证明 restore 与源快照一致，再做 migration/import。

## forward

只执行正式已有 migration 0024。

不得修改 published migration 历史。

不得通过 downgrade 作为正式恢复方案。

## 内容导入

导入：

- AI 当前获准版本
- Agent application v8
- Cloud 当前获准版本

以及当前注册表要求的其它不可变依赖。

必须证明：

- Agent7 仍在；
- Agent8 是新版本，不覆盖旧版本；
- 新 MCP10.1 source/version2 正确；
- Python / 旧包仍可读取；
- 私人数据不被内容导入覆盖；
- 重复导入幂等；
- 异体冲突拒绝；
- 无半发布。

## 演练验证

在 restore DB 上：

- 普通认证；
- app-role/RLS；
- 当前 catalog；
- current pack selection；
- Fake bounded generation；
- Draft；
- synthetic confirm；
- Plan/workspace；
- refresh/relogin。

真实模型请求 = 0。

P2 PASS 后进入 P3。

---

# 4. P3：用户本人 RC 验收准备

这一阶段先准备，不得代用户做主观接受。

使用最新 restored + migrated + imported owned RC 数据库。

使用和计划正式环境相同的：

- API代码
- UI代码
- runtime设置
- Worker路径
- budget/admission
- current packs

但仍不是原产品库。

建立明确 RC URL / port / process ownership。

不得复用历史端口号码而不先核对实际所有者。

## 用户需要实际体验

为用户准备以下路径：

1. 登录自己的正常账号；
2. 创建一个真实学习目标；
3. 正常提交规划；
4. 查看生成进度；
5. 查看非空 Draft；
6. 查看阶段/单元/知识；
7. 查看免费章节资料；
8. 查看 Learning Guidance；
9. 查看 Framework / MCP / Project Study；
10. 查看 Prompt；
11. 查看阶段总结；
12. 查看实践和成果；
13. 尝试一次已有受控资源或实践变更；
14. 查看旧历史；
15. 刷新；
16. 退出；
17. 重新登录并确认状态保持。

用户本人负责判断教学内容和使用体验是否可接受。

synthetic USER / automated Edge 不能替代该结论。

---

# 5. RC 中真实模型调用

P1、P2 未 PASS 前真实模型请求必须为 0。

P1/P2 PASS 后，为用户本人 RC 正常生成可使用现有授权。

当前权威额度：

- cumulative cap = 200
- used = 125
- remaining = 75

如果用户本人需要生成一个全新正常 Plan：

- 只开一个新 Acceptance / Run；
- normal 最大37；
- repair 最大2；
- 总最大39；
- append-only request/result/receipt/usage；
- unknown 立即停止；
- 不重派；
- 不创建第二个用户 Plan 只为了增加证据。

这是用户实际使用验收，不是再次重复 synthetic paid representative。

---

# 6. P4：唯一正式操作授权包

P1/P2 以及 RC 技术准备完成后 STOP。

不要自动修改正式环境。

只生成一个最终授权包，必须写清：

## Git / code

- 当前 branch
- HEAD
- working tree
- 是否需要 push
- 是否需要 merge
- 目标 branch
- 精确提交范围

## DB

- 当前原库 revision
- backup 文件/hash
- migration 0023→0024
- immutable pack import
- 预计写哪些表
- 明确不会修改哪些私人表
- 幂等/冲突语义
- rollback 方法

## Services

- API command/profile
- UI command/profile
- Worker command/profile
- exact ports
- running account
- process ownership
- stop commands
- health verification

## Worker

- admission mode
- allowed actor/service identity
- failed/unknown exclusion
- lease/cancel/fencing
- request/output budget source

## External

- model endpoint
- current remaining quota
- RAG status
- GitHub OAuth status

## User actions

把用户必须亲自执行或确认的项目单独列出。

正式操作前等待一次明确批准。

---

# 7. RAG 支线

不得让 F17 阻塞 P1/P2/P3 的独立工作。

只允许只读识别当前 Personal Multimodal RAG 实例：

- 服务/容器归属
- OpenAPI
- auth
- caller scope
- tenant/project/dataset isolation
- pure retrieve endpoint
- retrieved chunk/source metadata
- citation identity
- timeout/error/no-hit semantics

如果现有 RAG 已有足够契约：

只设计最薄 StudyPlan Port/adapter。

如果没有：

保持 F17 BLOCKED。

不要：

- 新建第二套RAG；
- clone/复制RAG业务逻辑；
- 重新embedding；
- 建新向量库；
- 为了READY伪造citation；
- 把healthz当检索集成PASS。

---

# 8. 防止过度优化

本轮明确禁止：

- 新Teacher/Evaluator/Coach/Review Agent
- 新评分体系
- 新复习系统
- 新知识图谱
- 新Proposal平台
- 新综合报告中心
- 重写前端
- 重写LangGraph
- 新数据库抽象层
- token进一步微优化
- 为代码漂亮做大规模重构
- 重复完整paid representative
- 重跑无输入变化的大型测试

只有实际阻断 P1/P2/P3 的问题才允许修改。

---

# 9. STOP 条件

以下情况必须局部 STOP 并保留证据：

- provider dispatch unknown
- 原产品库意外写入
- migration 非forward-only
- restore摘要不一致
- RLS/ACL发生未解释变化
- Worker可绕过预算
- failed/unknown被重新派发
- immutable内容版本被覆盖
- 需要修改核心权威合同
- 需要扩大repair/model/cap
- 需要部署/push/merge/正式入口操作

普通fixture、脚本、测试断言问题在当前范围内修复后继续，不因每个小问题重新申请Goal。

---

# 10. 最终原则

当前产品功能已经足够。

本轮目标不是“让架构更先进”，而是：

**把已经验证有效的 StudyPlan 安全地带到真正可日常使用的状态。**