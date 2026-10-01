# 领域模型与状态契约

2026-10-01 / S0。[上位规格](supplements/studyplan_requirements_design_supplement_2026-10-01.md)；本文是目标设计，不声称新字段已实现。已实现/缺口见 [审查](../reviews/2026-10-01-v1-gap-analysis.md)。

## 实体与现有概念映射

| 产品概念 | 职责与稳定引用 | 当前承接 / 补齐 |
|---|---|---|
| Goal | 目标、方向、主项目意图；属于 LearningProject | goal_snapshot 与项目已有；目标修订与来源补齐 |
| KnowledgeNode | 领域知识身份、学习目标、子主题和前置关系 | catalog KnowledgeNode 已有；跨生成的逻辑身份缺口见 ADR-0009 |
| Plan | Project 的学习路线及当前版本引用 | 复用当前路线查询与版本集合，不另造复制知识树 |
| PlanVersion | 用户确认的不可变结构，版本引用为 plan_version_id | 当前 PlanRevision 承接；plan_version_id 映射其 plan_id，revision 是项目内序号 |
| PlanNode | 版本内知识、顺序、单元、资源与任务的关联 | 复用 PlanStage/PlanUnitLink/UnitNodeLink，增补明确知识逻辑身份和内容引用 |
| Resource | 来源、作者、URL、版本/章节/语言/媒体/核验元数据 | ResourceRecord、ResourceSource、章节和偏好基础复用 |
| LearningSession | 当时目标/阶段/节点/计划版本与会话过程 | 新增学习会话；auth_sessions 是认证会话，不复用为学习事实 |
| Reflection | 用户总结原文、尝试、rubric 快照、AI 反馈 | SummaryAttempt/SummaryReview 复用并补节点/Session/plan_version 绑定 |
| PracticeTask | 主项目中的阶段交付、目标、范围、产物、验收标准 | PracticeTask + TaskKnowledgeLink 复用，明确为何做及验证哪些知识 |
| Evidence | 原始成果或可追溯核验来源 | PracticeSubmission / VerificationRecord；与 retrieval Evidence 区分用途 |
| AcceptanceResult | 结论、理由、检查项、证据与核验主体 | AcceptanceReview 复用，补覆盖节点/目标/版本与核验记录引用 |
| Memory | 可追溯的结构化记忆候选和批准记录 | PROJECT/SESSION 先启用，USER 预留；见 MEMORY_CONTEXT |

KnowledgeNode 建议内容字段由关联/版本化记录或读模型表达：description、prerequisites、subtopics、learning_objectives、recommended_resources、reflection_prompts、practice_refs、optional_extensions。不把正反向引用保存成两份可独立修改的树。

## 稳定身份与内容版本

目标 knowledge_node_id 是跨计划版本稳定的逻辑身份；节点内容、rubric、计划和学习成果各自有版本。当前 PgPlanningCatalog 将全量生成内容哈希放入 node_id namespace，不能认定已经满足此目标。

M1.2 为 `(project_id, pack_key, stable_key)` 建立逻辑身份及内容引用映射。现有 node_id/外键视为不可变内容引用保留；新增版本明确引用逻辑身份和具体内容记录。仅精确、审核确认的语义键可衔接，同名或相近标题不自动合并。多个不同含义的历史键冲突时拒绝自动衔接，生成待人工确认的映射 Proposal。既有数据库数据的增量衔接与旧 E 盘工程迁移无关，不创建旧 API 双轨。

计划结构变更必须 Proposal → Schema Validation → Domain Rules → 用户确认 → 单事务 Plan Update。发布校验 expected_version、draft_hash、幂等键，写新版本/关系/当前引用；失败和取消保留原当前路线。版本化资源替换新增版本；临时偏好调整只更新配置。

Session/总结/任务提交/验收需保存 project_id、plan_version_id、knowledge_node_id（或明确覆盖集合）、content_ref、rubric_version 和来源记录。旧记录保留原关联；不能按最新版本重新解释历史。新版本阶段 ID 可变化，语义知识身份不随之变化。

## 节点六态

状态是项目学习事实的投影，不修改知识结构定义。规范枚举为 NOT_STARTED、LEARNING、LEARNED、VERIFIED、REVIEW_NEEDED、SKIPPED；未来 API 序列化采用对应小写值，在实现切片同步 DTO/OpenAPI/client。

| 动作/条件 | 迁移 | 证据要求 |
|---|---|---|
| 开始学习 | NOT_STARTED/SKIPPED/REVIEW_NEEDED → LEARNING | 用户动作，保存来源和版本 |
| 阅读完成/用户自述完成 | LEARNING → LEARNED | 保存事实，不能直接 VERIFIED |
| 有效核验覆盖当前目标 | LEARNING/LEARNED/REVIEW_NEEDED → VERIFIED | 可检查证据、实际核验记录、目标覆盖和适用版本匹配 |
| 跳过 | NOT_STARTED/LEARNING/LEARNED/REVIEW_NEEDED → SKIPPED | 用户决定；不等于完成或核验 |
| 返回补学 | LEARNED/VERIFIED/SKIPPED → LEARNING | 原验收证据保留，记录新学习动作 |
| 新证据反驳或当前目标实质变化 | LEARNED/VERIFIED → REVIEW_NEEDED | 原结论保留；只更新当前适用状态，附理由 |

已有 UnitProgress 四态描述单元执行；COMPLETED 不等于节点 LEARNED/VERIFIED。节点状态和单元进度分别管理，明确读模型聚合规则，禁止批量将整个单元全部节点标记 VERIFIED。

## Evidence 与验收门

reported = 用户自述/外部报告/未核验 URL 或日志；verified = 平台可追溯核验；insufficient = 无法支持结论。模型可帮助检查总结/成果，但来源、检查项和实际结果必须可核对；单一模型“通过”文本不升级证据等级。

任务 ACCEPTED、总结 SATISFIED、EvidenceGrade.VERIFIED 与节点 VERIFIED 是不同状态。节点升级必须由领域服务核对覆盖的知识目标和版本；支撑/扩展关系不自动证明掌握全部知识。所有迁移采用 expected_version/幂等操作，原始提交追加保存。
