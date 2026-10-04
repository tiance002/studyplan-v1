Codex Goal — StudyPlan v6.8 单一真实收费代表复验（Projection Patch）
日期：2026-10-04
正式工程：D:\studyplan
0. 本轮唯一目标
在 v6.7 OUTLINE_PROJECTION_PATCH_READY 的基础上，执行 1 个全新的 Agent5 synthetic paid Run，验证：
1. stage_skeleton_v1 真实 provider 输入确实显著缩小；
2. outline 不再因旧的 20 万级输入而截断；
3. structure / practice 能继续完成；
4. reviewed knowledge / resources / guidance / extensions / practice 在真实模型输出后仍被确定性保护；
5. 草案可持久化、合成确认、PG回读、Chrome刷新/重登录；
6. 成功后的确认与只读消费不产生额外模型请求。
旧 v6.5 Acceptance / Run 永不复用。
完成后必须 STOP。
1. 授权范围
本次明确授权：
- 仅 1 个新的 Agent5 synthetic Run
- 全新 AcceptanceId
- 全新 owned 业务库
- 全新独立 checkpoint 库
- 使用当前正式候选 DeepSeek provider
- 当前 quota 从 24/50 继续累计
- normal 最大 13 请求
- local repair 最大 2 请求
- 总真实收费请求硬上限 15
- 最坏 quota 不得超过 39/50
本次不授权：
- 第二个 Run
- AI Fullstack / Cloud paid Run
- 原产品库写入
- 正式入口切换
- 正式 Worker daemon
- RAG
- GitHub/Tavily 新调用
- master/develop merge
- push
- 使用真实用户数据
2. 执行前硬预检
第一笔收费前必须全部 PASS：
1. branch / HEAD / tracked clean
2. v6.7 patch commit 在当前 HEAD 祖先链
3. outline_input_format=stage_skeleton_v1 对新 submission 实际冻结
4. marker 进入 manifest hash
5. 新格式 outline payload：
   - 不含 publication_evidence
   - 不含完整 resources catalog
   - 不含 practice/full extensions/full guidance
   - 不含未选 stage / source / section 全文
6. 6-stage 同一 synthetic 目标下：
   - messages chars 在 v6.7 结构上限内
   - HTTP bytes 在 v6.7 结构上限内
7. legacy path 未被本轮输入使用
8. DeepSeek runtime DNS仍公网
9. endpoint guard PASS
10. TLS / cert / hostname PASS
11. runtime cap：
    - outline 4096
    - practice 4096
    - structure 8192
    - repair 8192
12. 当前 quota 精确 24/50
13. 当前受控账本 unresolved = 0
14. provider key 存在但不得打印
15. frozen Agent5 publication digest正确
16. synthetic scope 无真实用户资料
17. request budget = 13 normal + 2 repair <= 15
任何一项 FAIL：
0 次收费请求，STOP。
3. 合成目标
继续使用与 v6.5 可比较的目标：
零基础系统学习 Agent 应用开发，先做一个最小应用。

保持：
- 无真实用户项目
- 无私人资料
- 无面试 overlay
- 无 RL训练目标
- 无 RAG专项强制深化
- 默认偏好
这样可以把 v6.5 与 v6.8 的 outline usage 做可解释对比。
4. 第一门：只验证真实 outline
发出第1个真实请求后，先暂停后续阶段，核对：
4.1 必须记录
- HTTP status
- finish_reason
- input tokens
- output tokens
- total tokens
- cached/cache hit/cache miss（若provider返回）
- content长度
- JSON envelope
- adapter final state
- outline解析结果
4.2 核心比较
明确对比 v6.5：
v6.5 outline input = 209,998 tokens
v6.8 outline input = actual provider usage
必须报告真实减少比例。
不要用 char/4 代替真实 token。
4.3 第一门通过条件
只有：
- finish_reason 不是 length/truncated
- JSON/shape 可解析
- stage keys 与冻结集合一致
- 无越权字段
- provider receipt 完整
- ledger 完整
- unknown=0
才允许继续 structure。
否则立即 STOP。
5. 第二门：structure
对6个阶段逐阶段执行现有 structure。
每次请求记录：
- input/output tokens
- finish_reason
- known failure / unknown
- repair是否触发
每个阶段返回后立即验证 deterministic protection：
Knowledge canonical
以下必须与 frozen reviewed authority 相同：
- stable_key
- title
- objectives
- scope
- acceptance
- parent
- prerequisites
如果模型尝试改写：
- 必须被拒绝或本地canonical恢复
- 最终持久化不得保留模型污染值
任一阶段出现 unknown：
STOP_UNKNOWN。
6. 第三门：practice
对6个阶段逐阶段执行现有 practice。
每次返回后验证：
- reviewed task identity/count
- goal
- scope
- deliverable
- acceptance
- required/optional
- knowledge links
必须确认：
- 没有新增强制 Starter
- 没有额外 required task
- 没有冲突 acceptance
- 没有删除 canonical acceptance
- supplemental/optional 不进入 completion gate
- 当前不支持的显式 optional canonical task 仍 fail-closed
任一阶段 unknown：
立即 STOP。
7. repair 纪律
只允许系统现有 local repair。
上限2次。
允许 repair 的前提：
- 明确 known failure
- 原 request/result receipt 完整
- 不是网络/billing unknown
- repair 与原阶段绑定
禁止：
- 人工再开第二 Run
- 为“结果更好看”重试
- unknown 后重发
- 超2次 repair
8. 成功草案与内容保护总核对
如果完整生成成功：
必须逐项核对：
- 6 stage
- required knowledge
- 18 resource arrangements
- 35 exact section refs
- 13 extensions
- all guidance
- project/starter optional semantics
- user-project priority
- open Recipe semantics
- Evaluation cross-cutting
- RL optional
- hold exclusion
- canonical knowledge fields
- canonical practice fields
与 frozen authority 做精确比较。
不得只检查“数量大致一样”。
9. 确认、PG与Chrome
只有完整草案 PASS 后：
1. 合成账号明确 confirm
2. PG精确回读
3. 启动受控前端/API
4. Chrome：
   - 登录
   - 路线
   - 章节资料
   - guidance/extensions
   - practice
   - Project Study（适用内容）
   - 刷新
   - 退出
   - 重新登录
   - 再回读
从模型生成完成以后开始：
新增模型请求必须为0。
Chrome/GET 不得触发重新生成。
10. 成本与账本
起始：
24/50
本轮：
max +15
最终硬上限：
<=39/50
记录每一个真实 request：
- purpose
- attempt
- input tokens
- output tokens
- total
- finish_reason
- success/failure
- repair linkage
失败请求计量。
provider 不返回某字段则写 NOT OBSERVABLE，不得猜测美元费用。
11. PASS标准
只有全部满足才可声明：
PAID_REPRESENTATIVE_PATCH_PASS
必须包括：
1. 单一新Run
2. <=15收费请求
3. unknown=0
4. outline实际input显著低于209,998且成功解析
5. outline无length截断
6. 6个structure完成
7. 6个practice完成
8. deterministic content protection PASS
9. knowledge canonical PASS
10. practice canonical PASS
11. Draft persistence PASS
12. synthetic confirm PASS
13. PG readback PASS
14. Chrome refresh/relogin PASS
15. 成功后模型请求增量0
16. 原产品库/用户数据/RAG未触碰
否则只能：
PAID_REPRESENTATIVE_PATCH_FAIL
或：
PAID_REPRESENTATIVE_PATCH_STOP_UNKNOWN
12. 特别关注的真实指标
最终报告必须单列：
Outline improvement
- v6.5 real input tokens: 209,998
- v6.8 real input tokens: X
- reduction: X%
- v6.5 output: 4,097 / truncated
- v6.8 output: X / finish_reason
- latency comparison（仅实际值）
Total Run usage
- outline input/output
- structure total input/output
- practice total input/output
- repair total input/output
- grand total input/output
- request count
这样才能判断 patch 不仅“能跑”，也真正解决成本/职责问题。
13. STOP
无论 PASS / FAIL / UNKNOWN，完成后都 STOP。
不得自动：
- 升级原产品数据库
- 切正式入口
- 启动正式Worker
- 运行AI2/Cloud2真实代表
- 修改RAG
- push/merge
14. 最终报告格式
Baseline
- branch
- HEAD
- AcceptanceId
- Run
- quota before
Preflight
- format marker
- payload size
- DNS/guard/TLS
- budgets
Outline real comparison
- old 209,998
- new actual input tokens
- reduction %
- output tokens
- finish reason
- parse
Structure
- 6 stages
- request count
- token totals
- repairs
- knowledge protection
Practice
- 6 stages
- request count
- token totals
- repairs
- practice protection
Persistence
- Draft
- confirm
- PG
- Chrome
- refresh/relogin
- post-success model calls
Usage
- quota before/after
- total requests
- total input/output
- unknown
Safety
- real user data sent = NO
- product DB write = NO
- RAG touched = NO
Final
- PAID_REPRESENTATIVE_PATCH_PASS
- PAID_REPRESENTATIVE_PATCH_FAIL
- PAID_REPRESENTATIVE_PATCH_STOP_UNKNOWN
Next
只给一个最小下一动作。