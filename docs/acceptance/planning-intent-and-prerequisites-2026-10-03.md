# 显式目标、前置展开与成果用途增量

用户现在新增能做什么：在生成前可展开“补充目标与起点”，填写学习深度、自述起点、成果用途、范围和限制。未补充时继续使用原请求。草案显示服务端冻结的目标快照；当前表单改动不冒充已保存目标。确认、刷新、退出重登录后快照仍保留。模板必要模块沿知识依赖展开，阅读/实践前置可以随学习指导展示。面试、作品集、实习、实际项目等用途只叠加少量收尾实践要求；后续更改任务仍保留当前用途要求。

日期2026-10-03。本地代码SHA **`9b1a3ada60af22c0793c72c169eed3ac5a702a7d`**，分支 `feat/n1-resource-discovery`。前序指导代码 `506048164261be06a166c5c9b8be4b6a556b4301`，前序证据 `8782f9c8d38092a489819ed118a6ecf37fcbe330`。未核实远端，不把这些新SHA写成GitHub已存在。整体 **NOT_READY**，最终Goal继续active，未集成develop/master、未标milestone。

## Goal与实际改变

复用[最终交付Goal](../implementation/STUDYPLAN_OCT6_FINAL_DELIVERY_GOAL_2026-10-03.md)第6/8节和[ADR-0015](../adr/ADR-0015-learning-orchestration-deadline.md)，不再生成规划书等待实施。字段使用既有提交事件/草案payload/计划structure JSONB，无新迁移、依赖或第二规划器。

- `domain/planning/intent.py`：纯领域GoalSpec，显式目标与自述输入限长/枚举/列表校验；最多200受控模块的确定性DFS闭包，沿parent和prerequisite递归，拒绝未知/环/重复键，不要求不可达的optional模块。
- API/schema/views、PlanService/PlanningState/nodes/batches：可选GoalSpec规范化后在提交时冻结，带入manifest哈希、outline及结构/实践批次；不是Worker恢复时重新推断。API禁止额外身份字段，用户不能通过此字段改变actor/project范围。
- PlanDraft/PlanRevision/projection/PG仓储：目标快照参与确认哈希与版本指纹，旧记录无字段时省略，保持旧哈希。资源/实践新版本沿用；普通阶段编辑保留。
- 生成合并：成果用途只增加最后阶段首个实践任务的少量验收要求，与冻结指导相同；不重复所有练习，不因自述起点写Verified。
- Practice Change：独立复核发现最终任务编辑可丢失用途验收项，真实PG RED后修复。候选、预览哈希、发布任务和指导使用相同要求，旧任务/历史保留；现有事务/CAS/幂等直接复用。
- `LearningGuidance`：有界reading/practice prerequisites；空新增字段从哈希载荷省略。Primary替换清除旧阅读前置，实践变更清除旧实践前置，不将旧提示当新事实。
- PlanningPage/client：轻量可选澄清和草案快照。前端列表上限与后端一致；可选字段缺失安全显示。现有短生成浏览器夹具改为等待明确DOM值，保留409防覆盖断言，不以networkidle替代React已更新。
- OpenAPI/生成TS、unit/PG/Chrome验收同步。未批量扩教程或正式Seed。

## Tests

测试分组存在重叠，不相加推算完成率。

| 验证 | 状态 | 证据与限制 |
|---|---|---|
| 新目标/闭包规则TDD | PASS | 初次缺字段/冻结链FAIL，随后通过；生成合并丢失用途指导有实际RED→GREEN；前置提示缺字段RED→GREEN |
| Unit/contract较宽组合 | PASS | 649通过，exit0，41.84s；另2 skipped记NOT RUN。后续更窄契约/PG/provider检查核对新增输入 |
| 最终规则/指导/provider | PASS | 21通过，exit0，1.28s；真实provider网络NOT RUN |
| PG+生成恢复+资源/实践较宽组合 | PASS | 68通过，exit0，187.57s，包含Chrome真实HTTP/PG目标回读；模型Fake。发生在最后用途编辑修复前 |
| 最新目标/指导/contract/PG组合 | PASS | 46通过，exit0，48.05s；含非法范围、长度、嵌套身份字段拒绝、普通注册/Worker/草案编辑确认/新容器/重登录/跨账号403；模型Fake |
| 用途编辑PG RED | FAIL | interview要求在新任务与指导丢失；同一次learn用例另因误读夹具键FAIL，均保留诊断，不算成功证据 |
| 用途编辑定向回归 | PASS | 2通过，exit0，8.26s，默认与interview，预览/发布/指导/旧历史均检查 |
| 最新实践/HTTP真实PG回归 | PASS | 35通过，exit0，69.37s；包含用途修复、现有事务/幂等/身份/历史防护 |
| Frontend unit/build | PASS | 11单元通过；TypeScript/Vite生产构建通过。早期新增DTO数组可选性导致build FAIL，兼容修复后PASS |
| Chrome Fake | PASS | 显式目标浏览器：默认省略、单次POST、上限、无掌握写入、服务端快照/刷新；指导browser：折叠/逃逸/来源安全/旧数据/390px；短生成409重载修夹具后PASS |
| Chrome+真实HTTP+PG | PASS | 正常会话、指导/前置/刷新/退出重登录/390px，以及已确认草案目标快照再次刷新读回；loopback真实API，模型Fake，没有Fake业务响应 |
| 真实模型/公网搜索 | NOT RUN | 本批全部新增0，不能据Fake宣称真实provider生成可交付 |
| 静态/秘密 | PASS | 受影响Ruff、4个定向source mypy、暂存diff、28文件凭证模式检查 |

本机忽略证据：`var/oct6-guidance/intent-unit-contract.xml`、`intent-pg-browser.xml`、`intent-final.xml`、`purpose-change-regression.xml`、`intent-practice-final.xml`、`browser-pg.json`、`planning-intent-real-pg.png`。Fake/PG/公网证据分开，未以healthz或单元测试冒充浏览器。

## 额度、风险、回滚与下一动作

产品调用账不变：模型23/50；搜索4/1000，含旧unknown1；旧README读取2次。真实公开GitHub本批NOT RUN，按用户最新决定fake-ip-filter尚未设置、使用时再提示。旧unknown/Acceptance不重派，不清零计量。开发模型临时授权继续；快速服务模式偏好已记录，工具未提供开关，不能声称已开启；代理请求Luna/high、Sol/high，实际解析NOT OBSERVABLE。

本次迁移新增0，仓库head0024（N1），原产品库仍0023且未写入。真实PG均自有隔离测试库，结束清理；临时API停止，Vite5178自有，原正常/只读服务停用。未启动旧Worker。

当前scope仅作模型条件，没有任意主题裁剪或用户模块根自动识别；模板仍完整生成，正式三个Blueprint及免费正文/章节审核未完成。自述起点不是掌握证据。缺思想校正版全文、公共GitHub真实链、真实provider、有限全路线重规划、恢复UX、完整闭环/备份恢复/用户接受仍使整体NOT_READY。缺RAG契约仅暂停对应支线，按10月4日中午规则判断。

回滚普通revert本地代码提交，保留原JSONB、历史、旧任务与账本，不破坏性降级0024，不消费旧Run。下一安全动作为有限操作重规划的增量切片：复用现有草案/publisher/CAS和历史保护；随后常态Worker/取消/失败/unknown/刷新恢复门禁。10月3日不批量扩内容，10月5日结束Feature Freeze。公开GitHub验证需要时才请求DNS操作；不能因此停止独立算法工作。
