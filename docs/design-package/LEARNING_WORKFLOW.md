# 学习闭环与状态变化

2026-10-01 / S0。所有学习动作绑定 [领域身份与版本](DOMAIN_MODEL.md)，模型动作同时受 [许可和预算](MODEL_ROUTING.md) 约束。

| 阶段 | 输入 | 输出/持久化 | 状态与 Gate |
|---|---|---|---|
| 定义目标 | 从零目标、可选主项目、动态资源偏好 | LearningProject/Goal | 用户确认目标；不做能力评分 |
| 规划 | Goal、DomainPack、资源索引、许可预算 | Outline、结构/实践 Proposal、Draft | Schema+Domain 校验；当前分批最多 2 repair、21 请求 |
| 确认路线 | Draft、hash、expected_version、决定 | 新 PlanRevision 和当前引用 | 用户批准后单事务；重复批准同结果，无模型生成 |
| 选择节点/学习 | 当前版、节点、内容版本、资料 | LearningSession、访问/用户学习事件 | NOT_STARTED → LEARNING；资料不可达如实反馈 |
| 总结 | 用户原文、节点/单元目标、rubric 快照 | 不可变 Reflection 尝试 | 自述只能支持 LEARNED；原文不被 AI 改写 |
| AI Feedback | 原文、目标、必要引用和许可 | covered/gaps/misconceptions/questions、来源 | 单次有界评审；不自动改计划或核验全部节点 |
| 实践方案 | 同一主项目的阶段任务、用户方案/Prompt | 方案修订与评审、指定版本导出 | 明确为何做/验证哪些知识；意见可结束/跳过，不无限纠缠 |
| 外部实现 | 导出的指定版本方案 | Codex/IDE 中实际项目 | StudyPlan 不运行外部代码、不启用 Sandbox |
| 提交成果 | 仓库/commit/文件/运行结果/说明 | 不可变 Submission 与 Evidence | 自述和外部报告先 reported，核验实际来源 |
| 验收 | 任务标准、证据、版本、具体检查项 | AcceptanceResult / VerificationRecord | 不足则 needs_more_evidence；有效核验经领域门更新节点 |
| 下一阶段/调整 | 进度、用户跳过/重排/展开建议 | Proposal、新计划版本（结构改变时） | 用户确认；旧 Session/总结/成果仍链接旧版 |

## Session 和历史恢复

Session 保存 project_id、plan_version_id、knowledge_node_id、content_ref、stage_ref、session_type、goal_snapshot 和原始事件。重新打开按当时版本读回；当前路线变更时显示“历史会话”，不静默切到最新目标。旧节点不再出现在当前计划时仍可只读恢复。

用户主动将历史讨论转入当前学习时创建新 Session 并记录来源 Session/event，不覆盖旧会话。跨节点切换助手创建/恢复对应 Session，发送时冻结绑定上下文，异步回答不能错挂到后来选中的节点。

## 跳过与路径外探索

跳过保留理由和记录；如影响计划顺序/学习集合则生成调整 Proposal、新版本。GraphRAG 等问题先按知识节点归类核心/扩展/高级/无关，再回答或建议展开。用户可取消 Proposal；模型不能直接改知识图或路线。

## 验收边界

普通总结是理解证据，阅读/自述不是核验。只有可检查总结/实践证据被实际评审、覆盖目标并保留来源结果后才可能 VERIFIED。已核验部分目标不等于全部节点掌握；内容/rubric 实质变化转 REVIEW_NEEDED，历史结果保持。

检索不足、provider 未知、数据库故障分别反馈，用户输入可恢复；网络中断不自动再付费。用户批准和成果验收是业务数据写入，本轮 S0 不代为执行。
