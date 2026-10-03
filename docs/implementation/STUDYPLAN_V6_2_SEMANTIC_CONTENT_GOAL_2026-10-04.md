# Codex Goal — StudyPlan v6.2 语义校正版内容落地

日期：2026-10-04  
目标截止：2026-10-06  
正式工程：`D:\studyplan`

本轮输入资料：

1. `STUDYPLAN_SEMANTIC_CORRECTED.zip`
2. 本文件
3. 当前仓库已有 v6.1 实施与验收记录

如果压缩包内文件与旧研究包冲突，**语义校正版优先**。
用户最新指令 > 本文件 > 语义校正版 > v6.1 Goal > 更旧文档。

---

# 0. 本轮目标

v6.1 已经完成：

- 三方向最小路线
- Project Study Card
- “复制给 AI”
- reviewed 内容确定性保留
- Fake + 隔离 PG + Chrome
- worker / stage completion / backup restore 等回归

本轮不重做这些。

本轮只做：

> **把 Work 已深审并做过产品语义校正的三方向内容，映射到当前 StudyPlan 既有结构，并验证 planner 不会把 Starter、Recipe、Project Candidate 实现成硬限制。**

目标是从：

```text
outline_checked / selected_scope_pending
```

升级为：

```text
可发布的章节级冷启动教学内容
+
开放组合规划语义
```

---

# 1. 开始前必须做 N0：核对本机最新事实

先在：

```powershell
cd D:\studyplan
```

执行并记录：

```powershell
git status
git branch --show-current
git rev-parse HEAD
git log -8 --oneline
```

已知上一批报告的历史信息：

- 当时分支：`feat/n1-resource-discovery`
- 当时 HEAD：`841ef9e31f0db70af238fa8c89796e3a5cf1c3e1`
- 当时业务提交：`8a05cae60153b4af6c7a830668053af3d6d8d3f2`

**这些只能用于核对祖先关系，不能作为 reset 目标。**

禁止：

- `git reset --hard`
- force checkout
- 覆盖未提交用户修改
- 回退到历史 SHA

本机当前代码是事实源。

---

# 2. 首先只读审计语义校正版与当前实现的映射

必须先读压缩包内：

1. `SEMANTIC_CORRECTION_REPORT.md`
2. `PLANNING_SEMANTICS_STANDARD.md`
3. `SEED_MAPPING_NOTES.md`
4. 三份 `*_TEMPLATE_PRODUCTIZED.md`
5. `SPECIALIZATION_RECIPES.md`
6. `DEFAULT_STARTER_PROJECTS.md`
7. `PROJECT_STUDY_CARDS_NORMALIZED.md`
8. `RESOURCE_CATALOG_NORMALIZED_DRAFT.json`
9. 原六份 Agent 详细专项路径
10. `EXPOSURE_MATRIX_ALL.md`
11. `PREREQUISITE_MATRIX_ALL.md`
12. `RESEARCH_LOG.md`

然后对当前代码逐项分类：

- `DIRECT`：现有模型直接表达
- `CONTENT_ONLY`：只需新 DomainPack / Seed 内容
- `THIN_ADAPTER`：很小的 planner/content 适配
- `UI_WORDING`：只需文案或展示逻辑
- `HOLD`：资料证据不足，不能发布
- `DEFER`：不应在 10/6 前做

在报告中明确：

> **不得因为研究包里出现新的抽象名词，就新增数据库实体。**

---

# 3. 冻结产品语义：这是硬验收，不是文案建议

必须保证：

## 3.1 Direction 不是用户归属枚举

三方向是首批能力领域：

- AI Fullstack
- Agent Application
- Cloud Services

用户目标可跨方向组合。

不得新增：

```text
user.direction = 单选职业归属
```

---

## 3.2 Default Starter Project 只是 fallback

三个默认候选：

- Agent：研究与行动助手
- AI Fullstack：AI 资料工作台
- Cloud：Task Service

行为必须是：

```text
用户已有合适项目
→ 优先用户项目

用户项目太大
→ 裁成学习纵切面

用户没有项目
→ 才建议 Starter

某能力不适合项目
→ Micro Exercise
```

禁止：

```text
选方向 → 强制绑定 Starter
```

不要建立强制 capstone 关系。

---

## 3.3 Agent Recipe 是开放的 0..N 组合

当前首批深审：

- `rag`
- `coding`
- `workflow`
- `browser`

另有：

- `evaluation` = cross-cutting
- `agentic_rl` = optional training specialization

禁止新增 closed：

```python
AgentBranch = Enum("rag", "coding", "workflow", "browser")
```

禁止要求用户四选一。

允许：

```text
旅行 Agent = Workflow + Browser + RAG + Tool/API
研究 Agent = RAG + Browser + Evaluation
企业知识助手 = RAG + Workflow + Auth/permission + Evaluation
```

一个阶段可以有一个主要 focus，但总体计划可包含多个能力。

---

## 3.4 Recipe 未命中不能导致规划失败

例如用户：

```text
“我要学习做语音 Agent”
```

首批没有 Voice Recipe。

正确行为：

```text
Common Core
+ 已有能力模块
+ 已审核资源
+ 明确缺口
```

若资料池不足：

```text
needs_research_or_review
```

但：

- 不拒绝目标
- 不编造章节
- 不静默把新资料升级为公共 Seed

---

## 3.5 Project Candidate 不是必学项目

RAGFlow、WeKnora、Pi、OpenHands、browser-use、LangGraph、AgentScope、
FastAPI Full Stack Template、Vercel Chatbot、KubeSphere、Sealos、1Panel 等：

全部必须保持：

```text
binding = optional
replacement_allowed = yes
```

用户项目可以替代它们。

公共模板不锁：

- commit
- branch
- 文件路径
- 函数名

---

# 4. 最重要的简化原则：优先 CONTENT_ONLY，不加 schema

上一批已经：

- Migration: NO
- 无新 DTO/API
- 无第二套 planner

本轮继续以此为默认。

除非先写出明确证据证明当前模型无法表达，否则禁止新增：

- ProjectCase table
- Recipe table
- AgentBranch enum
- Starter binding table
- carrier table
- mastery/scoring
- repo index
- clone job
- AST/call graph
- 新 worker

优先复用当前已有：

- DomainPack
- knowledge blueprints
- stage blueprints
- resource source/section
- StageResourceAssignment
- KnowledgeExtension
- PracticeProject / PracticeTask
- Plan version / snapshot
- CASE_STUDY / REPO
- 当前 planner deterministic merge

---

# 5. 内容落地策略：发布“下一版本 Pack”，不覆盖旧已发布 Pack

先核对当前实际 Registry 和当前版本。

对每个方向：

```text
agent.application
ai.fullstack
cloud.services
```

创建**下一合法版本**。

禁止假设版本号。
必须从本机当前 Registry / Seed / DB 状态读取后递增。

旧 Plan 必须继续引用旧 Pack/旧快照。

不得原地修改已发布 immutable Pack。

---

# 6. 不要把整个研究 Catalog 机械导入

`RESOURCE_CATALOG_NORMALIZED_DRAFT.json` 有 86 条研究切片。

本轮导入原则：

## 6.1 只发布实际被三份 Productized Template / 六份 Agent Recipe 引用的“可发布子集”

每条至少满足：

- 身份明确
- URL/来源可映射
- 免费阅读语义明确或允许的访问语义明确
- review_depth 足以支持当前推荐 scope
- 不在 hold

## 6.2 明确排除 hold

至少保留 Work 标出的：

- ZCode 同名身份歧义 → `hold_identity_review`
- MaxKB metadata-only → `hold_content_review`
- 阿里课程具体课时访问未验证 → `hold_access_review`

这些不得被升级为 Primary。

可继续作为：

- 未发布研究记录
- 私有候选提示

但不能进入“已审核公共 Primary”。

## 6.3 review_depth 不得升级

`metadata_only`
≠
`selected_sections_read`

`selected_sections_read`
≠
`deep_reviewed`

不要为了通过 Seed validation 改高等级。

---

# 7. 章节级教学信息必须保留

映射后不能退化成：

```text
React
FastAPI
RAG
Docker
Kubernetes
```

每个关键教学阶段至少要能保留/生成：

- why now
- JIT prerequisite
- primary chapters / section scope
- supplement / comparison
- exposure relation
- small practice
- continuous outcome increment / micro exercise
- exit gate

可以用当前现有结构组合表达，例如：

- stage objective
- knowledge node objectives
- resource section refs
- comparison/supplement role
- KnowledgeExtension.guidance
- thinking_prompts
- practice blueprint acceptance

不要求新增列。

---

# 8. Agent 内容落地的最低要求

## 8.1 Common Core 继续可裁剪

保留 A0–A8 的详细骨架。

但不要生成：

```text
所有 Agent 用户必须 A0→A1→...→A8 同深度
```

应根据：

- 用户已有能力
- 用户目标
- 当前 Primary Spine
- 必要依赖

裁剪。

## 8.2 Hello-Agents + LCC

保留章节级：

- Hello-Agents 为主要连续 Teaching Spine
- LCC 在对应位置 REVIEW / COMPARE / DEEPEN

不要把两门课程各完整重跑。

## 8.3 Agent 专项

RAG / Coding / Workflow / Browser 的详细文件继续作为 planner 参考骨架。

Evaluation 横切到相关阶段。

Agentic RL：
- 应用开发者可以在 R0–R4 停止
- 只有训练目标才进入 R5–R9

---

# 9. AI Fullstack 内容落地最低要求

必须体现：

```text
Web mental model
→ React
→ FastAPI
→ persistence
→ GenAI engineering
→ 持续产品
→ 真实项目
→ 大型专项
```

但：

- JS/Python/SQL 必须 JIT
- 不把所有基础堆入口
- AI资料工作台只是 Starter
- 用户已有 AI Web 项目优先
- 团队/多租户/Auth/RAG/queue 等只按目标展开
- 项目案例 optional

---

# 10. Cloud 内容落地最低要求

必须体现：

```text
service development
→ DB/config/test/health
→ Docker/Compose
→ real cloud deployment
→ 按需求 K8s/OTel/CI/CD/IaC/platform
→ backup/restore
```

注意：

- Task Service 只是 Starter
- 用户已有 Node/Go/Java/Python 服务可直接作为 carrier
- Python/FastAPI 不是 Cloud 用户强制技术栈
- K8s 不是所有 Cloud 用户必修终点
- Terraform/平台工程按目标
- 恢复是实际证据，不是概念阅读

---

# 11. 现有 Project Study 功能只需更新内容，不重写能力

上一批已经实现：

- 项目学习卡
- 重点/深度/比较/avoid scope
- “复制给 AI”
- 当前源码动态学习 Prompt

本轮：

- 替换/扩充为语义校正版项目卡内容
- 保留 optional / replacement semantics
- Prompt 中继续让外部 AI：
  - 没 repo 就 clone 当前版本
  - 动态读当前代码
  - 不锁历史 commit/path
  - 小项目先地图
  - 大项目 3–8 slice
  - 事实/解释/推断分离
  - 最终迁移 1–2 项

不要新增 clone backend。

---

# 12. UI 最小语义修正

只在当前 UI 会误导用户时改。

需要检查：

- 是否写成“你的项目”而实际只是 Starter
- 是否写成“必须选择分支”
- 是否把 Project Candidate 显示成必修
- 是否把 Evaluation / RL 显示成普通并列职业分支

推荐文案：

- “默认项目候选”
- “可替换真实项目”
- “本阶段主要强化”
- “可组合专项”
- “项目案例（可选）”
- “训练专项（可选）”

没有误导就不为文案重构组件。

---

# 13. 必做语义 E2E

使用 Fake 模型 + 隔离 PG + Chrome。

至少验证以下 6 条：

## E2E-1：Agent 用户已有旅行项目

输入表达：

```text
我已经有一个旅行规划 Agent，
希望系统补 Agent 基础，并强化网页信息获取、
可恢复规划和知识检索。
```

期望：

- carrier 优先旅行项目
- 不强制研究与行动助手
- 能组合 Browser + Workflow + RAG
- Evaluation 贯穿
- 不要求 RL

---

## E2E-2：Agent 无项目

输入：

```text
我没有项目想法，想系统学习 Agent 应用开发。
```

期望：

- 可以建议“研究与行动助手”
- 明确是默认候选
- 用户可替换
- 不要求一次学完所有专项

---

## E2E-3：未命中 Recipe

输入：

```text
我想学语音 Agent。
```

期望：

- 不因没有 Voice Recipe 失败
- 使用 Common Core + 可复用能力
- 对缺少审核资料明确 `needs_research_or_review` 或等价用户可理解状态
- 不虚构具体章节

---

## E2E-4：AI Fullstack 用户已有项目

输入：

```text
我已经有一个电商后台，
想把它改造成带 AI 商品文案与客服能力的全栈应用。
```

期望：

- 不强制 AI资料工作台
- Web/React/FastAPI/GenAI 依用户现状裁剪
- SQL/Auth/Streaming 按真实需求展开

---

## E2E-5：Cloud 用户已有非 Python 服务

输入：

```text
我已经有一个 Node.js API，
想学习如何部署、监控、自动发布和恢复。
```

期望：

- 不强制重写为 FastAPI
- 不强制 Task Service
- Docker/Cloud/CI/Observability/Restore按目标
- K8s/IaC非必要时可后置或省略

---

## E2E-6：项目案例可替换

在 RAG 路线中：

- RAGFlow/WeKnora 显示为可选候选
- 可以继续使用用户自己的知识库项目
- 不存在“必须二选一”阻塞

---

# 14. 必做结构测试

至少覆盖：

1. Starter 不产生强制绑定。
2. Recipe 不是 closed enum。
3. 多 Recipe 组合可进入生成输入/内容选择。
4. Recipe miss 不报 fatal。
5. hold catalog 不进入发布 Primary。
6. immutable Pack 通过新版本发布。
7. 旧 Plan 快照不被新 Seed 静默修改。
8. detailed section refs 顺序保留。
9. comparison/supplement/case study roles 保留。
10. Project Study Prompt 不出现固定 commit/path。
11. 现有 Auth/RLS/PlanVersion/worker/stage completion/history 全回归。

---

# 15. 不要做的事情

本轮禁止：

- 重写 planning graph
- 新增第二套 planner
- 新数据库体系
- mastery score
- 全局课程 embedding 去重
- 自动 Recipe 学习/生成系统
- 自动公共 Seed 审批
- repo clone/index
- 把 Work 研究稿所有 86 条无差别发布
- 把 hold 项“为了完整”强行转 PASS
- 使用真实收费模型做必要验收

---

# 16. 交付策略

建议拆成四个本地提交：

## Commit A — content mapping
- 语义校正版资料入仓库审计目录
- mapping/registry/content versions
- no runtime behavior change

## Commit B — next Pack versions
- 三方向下一版本 Pack
- reviewed publishable resource subset
- detailed sections/extensions/practice
- tests

## Commit C — semantic planner/UI thin adjustments
仅当实际审计证明需要：
- Starter fallback
- open Recipe composition
- recipe miss fallback
- wording
- project optional semantics

不得无证据扩大改动。

## Commit D — acceptance evidence
- PG
- Chrome
- regression
- restore if data changes materially
- final report

提交前均保持可独立 revert。

---

# 17. Ready 判定

只有以下全部满足，才能把“本轮内容落地”记 READY：

- 三方向新 Pack 可生成/确认/回读
- 章节级 scope 未退化
- 用户项目优先行为有 E2E 证据
- 多 Recipe 组合有 E2E 证据
- 未命中 Recipe 不 fatal
- Starter 仅 fallback
- Project Candidate optional
- hold 未误发布
- 旧计划不变
- 无 Auth/RLS/worker/history 回归
- Chrome / PG 证据存在
- 所有 NOT RUN 明确记录

如果产品整体还有其它既有 blocker，
总体产品状态继续 `NOT_READY`，
不得因为本批 PASS 改写为整体 READY。

---

# 18. 报告格式

最终输出：

- Actual HEAD / branch
- 输入资料版本
- 映射策略
- 新 Pack key/version
- 发布资源数量 / hold 数量
- 是否 Migration
- 是否 DTO/API change
- 用户项目优先：PASS/FAIL
- 多 Recipe：PASS/FAIL
- Recipe miss：PASS/FAIL
- Starter fallback：PASS/FAIL
- Project optional：PASS/FAIL
- Unit tests
- PG
- Chrome
- Build
- Backup/restore（若本轮需要）
- paid model calls
- external search calls
- remaining blockers
- rollback
- next action

现在从 N0 和“语义包→当前 schema 只读映射审计”开始。
