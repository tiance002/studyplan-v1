# Codex Goal — StudyPlan v6.1 截止期优化版

日期：2026-10-03
目标：2026-10-06 最终成品
正式工程：`D:\studyplan`

> 本文件覆盖此前 v6 中“可以进一步简化”的实施部分。
> 用户最新指令 > 本文件 > v6 实现校正文档 > 更旧 Goal/指导。
> 不回退、不重做已通过能力。

---

# 0. 开始前

本任务会使用 Codex 额度。

先执行只读核对：

```powershell
cd D:\studyplan
git status
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
```

然后核对：

- 当前 migration head
- 当前 DomainPack/Seed
- 当前正式 Plan DTO
- 当前 `Plan.extensions`
- 当前 Learning Workspace 数据流
- 当前 `agentCurriculum.ts`
- 当前 selector / seed registry
- 当前测试状态

禁止：

- reset / force checkout
- 用远端旧 SHA 覆盖本地新实现
- 为本轮教学调整重写事务/RLS/worker/历史系统

---

# 1. 产品职责重新冻结

StudyPlan 负责：

- 学习路线
- Teaching Spine
- 真正必要的前置
- 重复知识 REVIEW / COMPARE / DEEPEN
- 持续实践
- 开源项目选择
- 项目学习重点
- 学习深度
- 不必掌握范围
- 给外部 AI 的源码学习 Prompt

StudyPlan 不负责：

- clone 服务
- GitHub 代码索引
- AST / call graph
- Repo RAG
- 固定 commit
- 固定源码文件路径
- 长期维护项目逐函数教程
- 替代 Work Buddy / Codex / Claude Code 等 Coding Agent

---

# 2. 进一步简化：不要为 Project Study 再改数据库

当前已有：

- `StageResourceRole.CASE_STUDY`
- `MediaType.REPO`
- `KnowledgeExtension`
- `PlanSnapshot.extensions`
- `PracticeProject`
- `PracticeTask`

全部复用。

## Project Study Card 首版表达

一个项目学习阶段：

### CASE_STUDY resource
只保存：
- repo root URL
- title
- source/version metadata
- learning resource role

不保存：
- commit
- file path
- function name
- call graph

### KnowledgeExtension
表达：
- why now
- learning focus
- desired depth
- avoid scope
- comparison questions
- migration question

约定：

> 10/6 首版每阶段最多一个主要 Project Study Card。

这样无需：
- ProjectCase table
- ProjectSlice table
- repo analysis migration
- source index schema

---

# 3. 进一步简化：优先不改 StageWorkspaceView

当前 `LearningWorkspaceView` 已经包含 `plan: PlanView`，
而 `PlanView/PlanSnapshot` 已经包含：

```text
extensions
```

因此先检查前端数据流。

如果前端已经拿得到：

```text
workspace.plan.extensions
```

则：

- **不要给 `StageWorkspaceView` 新增 extensions**
- 不改 OpenAPI
- 不重生成 DTO
- 不加 contract test 负担

前端直接：

```text
workspace.plan.extensions.filter(x => x.stage_id === currentStageId)
```

再把结果传给当前阶段 Workspace。

只有当前前端数据链确实无法取得 Plan extensions，
才做最小 additive DTO change。

---

# 4. 项目源码学习 Prompt：只做一个纯函数

新增：

```text
buildProjectStudyPrompt(context)
```

优先放在前端/content 或前后端都可共享的纯模块，
不要增加新 API。

输入：

- repo_url
- project_title
- direction
- goal_branch
- current_stage
- known_knowledge
- learning_focus
- desired_depth
- important_questions
- avoid_scope
- practice_project_context

输出：
一段可复制文本。

必须包含：

1. 本地没有仓库时，让外部 AI 自行 clone；
2. 使用当前仓库；
3. 不要求历史 commit；
4. 不依赖 StudyPlan 固定文件名；
5. 小/中型项目先建立整体地图；
6. 大型项目只按目标生成 3–8 个学习切片；
7. 自动标记 REVIEW / COMPARE / DEEPEN / VERSION_CONTEXT / NEW；
8. 区分源码事实 / 工程解释 / 未核实推断；
9. 最后最多迁移 1–2 项机制回用户项目。

禁止：
- 为每个 Repo 写一份独立长 Prompt
- Server-side clone
- GitHub OAuth 强依赖
- 执行用户本地命令

---

# 5. 前置规则再简化：不做用户能力评分系统

不要做：

- mastery score
- 自动考试
- skill probability
- 新 learner profile 表
- 复杂前置推断 Agent

首版规则：

```text
外部前置 = Primary Spine 首次使用前不教授 + 用户明确缺失/默认初学者必要
```

DomainPack 只维护：

- 当前 Spine 的最低进入能力
- Spine 内部会教授的能力
- 后续深化能力

对于用户没有明确说明基础的情况：

- 使用方向模板的 beginner default
- 只补最小进入缺口
- 用户可在草案中删/改

---

# 6. Exposure 关系不要新增 enum/table

10/6 前不新增：

```text
ExposureRelation table
relation_type enum
semantic overlap service
```

用已有内容表达：

- `role=comparison`
- `node_ids`
- `KnowledgeExtension.topic`
- `guidance`
- `thinking_prompts`

推荐内容约定：

```text
topic:
  对比学习：Tool Calling

guidance:
  已学：...
  本次新增：...
  关系：COMPARE / DEEPEN

thinking_prompts:
  - 两种实现分别怎么...
```

UI 不需要复杂标签系统。
如容易实现，可从 guidance/topic 显示一个文本 badge；
不值得为 badge 改数据库。

---

# 7. Teaching Spine 也不要新建实体

不新增：

- TeachingSpine table
- SpineVersion table
- CurriculumGraph service

继续使用：

- DomainPack
- stage_blueprints
- resources
- section_refs
- KnowledgeNode prerequisite DAG

“Teaching Spine”是**内容编排规则**。

公共模板用稳定 `pack_key/version` 管版本已经够用。

---

# 8. 重点修复：不要让人工审核内容被模型丢掉

当前生成链要核对：

- reviewed DomainPack 的 stage/resources/extensions
- 是否在 Outline/Structure 模型生成中可能被遗漏或改写

原则：

> 预置审核事实由确定性代码保护，模型只个性化。

优先采用薄适配：

1. 模型生成阶段标题/objective等个性化内容；
2. DomainPack 中审核过的：
   - stage key
   - required knowledge
   - Primary/Comparison/Case Study
   - learning focus
   - project study guidance
   必须确定性合并/保留；
3. 模型不能静默删除审核内容。

不要为此重写 planning graph。

---

# 9. 三方向 Route 只做简单 Registry + 保守匹配

首批：

```text
ai.fullstack
agent.application
cloud.services
```

保留：
`python.engineering` 作为基础内容包。

一个权威 registry：

```python
CURRENT_PACKS = {
  "ai.fullstack": "...",
  "agent.application": "...",
  "cloud.services": "...",
  "python.engineering": "...",
}
```

要求：
- Seed 发布
- runtime select
- tests

共用一个 registry。

不要上分类模型。

目标明显不清楚时：
- 通用 route + 提醒用户确认
- 不猜复杂职业标签

---

# 10. 静态 `agentCurriculum.ts` 降级，不再维护第二套正式路线

当前静态课程页如果继续作为生产推荐入口，会与 DomainPack 漂移。

最小处理：

- 正式路线只认已发布 Plan
- 静态 curriculum：
  - dev preview / test fixture / 暂时隐藏
  - 不作为用户正式推荐真相源

不要花时间把静态文件同步成 v6 内容。

---

# 11. 内容层：本轮不要急着批量做“详细三方向数据”

当前开发阶段只需要：

- 数据结构能表达
- 3 个方向最小可用 Pack
- Project Study Prompt 能展示
- 路线生成不违背新规则

**详细内容数据的深审属于下一批内容生产任务。**

特别是 AI Fullstack / Cloud：
在没有逐段深读 Primary 资料前，
不要为了赶 10/6 伪造精细章节映射。

可以先标：

```text
review_status = outline_checked / selected_scope_pending
```

开发验收不依赖“所有课程已深审完成”。

---

# 12. 10/6 前真正必须实现的用户体验

## 生成路线时

用户应该看到：

- 路线阶段
- 为什么学
- 资料主线
- 实践方向
- 项目学习阶段

不要求看到内部算法术语。

## 学习阶段

至少能看到：

- 本阶段目标
- 前置
- 学习资料
- 对比/思考提示
- 持续实践
- 如果是 Project Study：
  - Repo
  - 学习重点
  - “复制给 AI”

## 外部 AI Prompt

无需 StudyPlan 自己运行 AI。
只要复制文本正确。

---

# 13. 代表性测试

### A. Agent

目标：
“零基础系统学 Agent，后面重点 RAG。”

必须：
- 不把 GenAI 整门课作为硬前置；
- Primary Spine 能覆盖 Agent 基础；
- Comparison 能出现；
- 真实 Runtime / 大项目阶段能出现；
- Project Study Prompt 有 clone 指令；
- Prompt 不含固定 commit/file path。

### B. AI Fullstack

目标：
“做 AI 资料工作台。”

必须：
- JS/Python/SQL 不是全部入口前置；
- Web 教学后才 GenAI；
- 自己项目先于真实源码拆解；
- Project Study Prompt 可复制。

### C. Cloud

目标：
“学习云服务，能开发、部署和运维 API。”

必须：
- 先 Service Development；
- 再 Docker；
- 再单一 Cloud Spine；
- CI/CD 在手工部署后；
- IaC 在手工资源后；
- Project Study 使用当前源码动态拆解。

---

# 14. 不要因为新设计破坏的部分

冻结：

- Auth / RLS
- PlanVersion
- draft confirm
- CAS / idempotency
- worker fencing
- cancel / reconciliation
- summaries
- prompt revisions
- practice changes
- outcomes/evidence
- USER accepted
- stage completion
- history preservation

---

# 15. 实施优先级

P0：本机最新状态 + 差异审计  
P1：Pack registry / 方向选择唯一真相源  
P2：reviewed content 确定性保留  
P3：三方向最小 Pack  
P4：Project Study Card 复用现有 resources/extensions  
P5：纯 Prompt builder + Copy UI  
P6：静态 curriculum 降级  
P7：三条代表性 E2E  
P8：回归 / release

---

# 16. 停止条件

如果某功能需要：

- migration
- 新表
- 新 worker
- repo clone backend
- 代码索引
- AST
- semantic course dedupe
- mastery model

先证明现有结构无法完成。

如果只是“更漂亮”，DEFER。

---

# 17. 输出

每批报告：

- 用户新增能做什么
- Changed files
- Actual HEAD
- Migration: YES/NO
- Tests PASS/FAIL/NOT RUN
- Browser PASS/FAIL/NOT RUN
- Real PG PASS/FAIL/NOT RUN
- Model/Search usage
- Risk
- Rollback
- Next

现在执行 N0/P0。
