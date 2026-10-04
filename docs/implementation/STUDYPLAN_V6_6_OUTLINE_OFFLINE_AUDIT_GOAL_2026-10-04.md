# Codex Goal — StudyPlan v6.6 Outline Payload 离线审计与最小化方案

日期：2026-10-04
正式工程：`D:\studyplan`

## 0. 本轮唯一目标

针对 v6.5 唯一真实收费 Run 暴露的问题：

- `planning.outline`
- input = 209,998 tokens
- requested max_tokens = 4096
- provider output = 4,097 tokens
- `finish_reason=length`
- adapter = `provider_output_truncated`
- Run failed
- 本轮 unknown = 0

进行**完全离线**的输入组成审计，回答：

> 为什么一个 6 阶段 Agent5 Common Core outline 会形成约 21 万 input tokens？
> 哪些内容是 outline 真正需要的？
> 哪些内容应由确定性代码保护，而不应反复发送给 outline 模型？
> 哪些内容应延迟到 structure / practice 阶段？

本轮不允许任何真实收费请求。

## 1. 严格边界

允许：
- 读当前代码
- 读 v6.5 失败 Acceptance 的本地受限证据
- 读 frozen manifest / request metadata
- 在本地重新构造**完全相同的请求 payload**
- 计算字符数 / token 数 / JSON 大小
- 使用本地 tokenizer / 当前已有 token estimator
- Fake provider
- 单元测试
- 生成审计文档
- 在证据充分后提出最小代码修正方案

本轮默认不实施生产业务代码修正。

只有当根因已经被精确定位、方案是明显局部且不会改变规划语义时，
才可以额外给出 patch draft / diff proposal，但**不要提交真实业务改动**，
等待下一门禁授权。

禁止：
- 真实 DeepSeek 请求
- 新 Acceptance
- 第二 Run
- 调高 outline 输出 cap
- 降低内容保护
- 删除 reviewed Seed
- 降低章节粒度
- 改 RAG
- 改正式库
- 启动正式 Worker
- 修改用户数据
- 为了减少 token 改写/丢弃受审核事实

## 2. 事实基线

必须从当前仓库和 v6.5 证据重新读取，不要只抄报告。

核对：
- branch
- HEAD
- tracked status
- Agent5 publication digest
- 失败 AcceptanceId
- 失败 Run ID
- frozen manifest
- 实际 outline request metadata
- provider usage
- 账本当前 24/50
- v6.5 后没有新增模型请求

报告中不得输出：
- API key
- 密码
- DSN
- 用户私人正文

## 3. 精确重建 outline 输入

必须使用**当前生产代码路径**离线构造与 v6.5 首个 outline 尽可能相同的模型输入。

不要手工拼一个“看起来类似”的 prompt。

记录：
- system message
- developer/static instruction（如有）
- user/goal input
- GoalSpec
- learner profile / starting point
- selected DomainPack
- selected stages
- knowledge blueprints
- stage blueprints
- resource refs / section bodies
- guidance / extensions
- practice blueprints
- project-study cards
- exposure/prerequisite information
- prior/frozen facts
- schema / JSON examples
- output format instruction
- retry/repair context（如果 outline 首次请求实际没有，则应为 0）
- 其它实际进入 messages 的内容

如果某对象被多次序列化，必须分别记录。

## 4. Token Attribution：必须给出可核查的组成表

生成：

`docs/reviews/2026-10-04-v6-6-outline-token-attribution.md`

至少包含：

| Component | chars | estimated tokens | % of input | repeated? | needed by outline? |
|---|---:|---:|---:|---|---|

必须覆盖所有 >=1% 的贡献项。

另外单独列：

### Top 20 largest payload fragments

每项：
- 来源对象
- stable key / stage key（可公开）
- 字符数
- token 数
- 出现次数
- 是否重复
- 为什么被加入

## 5. 重复与膨胀检查

必须明确检查以下可能性，不要先假定任何一个是真的：

1. 三方向 Pack 是否意外同时进入 Agent outline
2. Agent5 61 个 stage 是否在裁剪到 6 阶段前就整体注入
3. 179 个章节正文是否全部进入 outline
4. `resource section` 正文是否被多层重复：source / section / stage assignment / guidance / extension
5. `KnowledgeExtension.guidance` 精确分片是否重复拼接
6. project-study prompt / project cards 是否全量进入 outline
7. exposure / prerequisite 矩阵是否被整体重复
8. practice blueprint 是否在 outline 阶段提前全量进入
9. output JSON schema / examples 是否异常巨大
10. deterministic protected facts 是否既进 prompt 又在 merge 后再次使用
11. selected 6 stages 是否仍携带未选 stage 的关联资源/知识闭包
12. serialization 是否把同一 reviewed section 放了多份完整正文
13. frontend/display-only prose 是否意外进入 model context
14. previous plan/history/private data 是否意外进入
15. prompt template 是否有递归嵌套/重复 dump

每项给：

`PASS / FOUND / NOT APPLICABLE`

并给证据。

## 6. Outline 的职责重新核对

必须区分三类信息：

### A. 模型真正需要看到

例如可能包括：
- user goal
- starting point
- constraints
- candidate stage keys
- 每 stage 极短 objective / capability summary
- prerequisite relation
- allowed personalization boundaries
- output schema

是否需要以上内容，必须由当前代码职责和测试证明。

### B. 模型不需要全文看到，但生成后必须由确定性代码保护

候选包括：
- reviewed resource exact section refs
- full teaching guidance
- practice acceptance criteria
- project-study card full prompt
- detailed exposure notes
- exact URLs
- long chapter descriptions

这些如果本来由 deterministic merge / protected facts 恢复，
则不应为了“模型不能删”把全文塞给 outline。

但不能凭猜测删除，必须追调用链证明。

### C. 应推迟到后续阶段

核对哪些只属于：
- structure
- practice
- project-study rendering
- learning workspace

不应进入 outline 首次调用。

## 7. 最小目标架构

在不新增第二套 planner 的前提下，设计最小方案。

### Option 1 — Outline 只选/个性化 stage skeleton

模型输入：
`goal + learner constraints + candidate stage keys + concise capability summaries + prerequisite relations + output schema`

模型输出：
`ordered/selected stage keys + personalized title/objective + limited rationale`

然后：
`deterministic merge → 恢复 reviewed knowledge/resources/guidance/extensions/practice/project-study`

### Option 2 — 分层摘要

如果 outline 确实需要部分教学语义：
为每个 stage 使用已有确定性 concise projection，
而不是完整 Markdown / section body。

### Option 3 — 其它

只有证据证明 1/2 不够时再提出。

禁止：
- 新 planner
- 新模型调用阶段
- embedding prompt compression
- LLM summarizer pre-pass
- 牺牲 reviewed content

## 8. 必须计算“修正后的离线预算”

对每个候选方案，离线重建 payload 并给出：

- chars
- estimated input tokens
- 相比 209,998 的减少比例
- stage count
- protected content count
- information dropped from model visibility
- information restored deterministically
- output cap 是否仍需 4096
- 是否需要更改 structure/repair cap

目标不是追求最少 token，而是：

> 在不损失规划正确性和 reviewed 内容保护的前提下，
> 将 outline 输入缩到与 6-stage skeleton 职责匹配的量级。

不要先规定 10k/20k 等人为阈值；
先根据实际组成和最小信息集合给出证据。

## 9. 保护不回退检查

任何方案都必须证明以下信息即使不进入 outline 全文，也不会丢失：

- stage key
- required knowledge
- reviewed Primary / Comparison / Case Study resource
- exact section scope
- why now / guidance
- exposure relation
- practice blueprint
- project-study semantics
- Starter optional
- Project Candidate optional
- Evaluation cross-cutting
- RL optional
- hold 不发布
- user project priority
- Recipe open-composition semantics

如果当前 deterministic merge 不能保证其中某项：
明确列为真正缺口，不通过“继续全量塞 prompt”掩盖。

## 10. 离线测试

至少新增/执行：

1. **payload attribution test**
   - 同一 synthetic goal
   - 可复现 component token accounting

2. **no-unselected-stage test**
   - 6-stage route 不携带未选 stage 全文

3. **no-duplicate-reviewed-section test**
   - 同一 section body 不因多层引用重复序列化

4. **outline-responsibility contract**
   - outline 输出不能修改 reviewed facts

5. **deterministic-rehydration test**
   - Fake outline 只返回 stage skeleton
   - merge 后完整 reviewed content 仍恢复

6. **semantic regression**
   - travel Agent
   - no-project Agent
   - Voice missing Recipe
   - Node Cloud
   - AI Fullstack existing project
   不要求浏览器；只验证 planner semantics 未因压缩倒退

本轮所有模型使用 Fake 或 deterministic fixture。

## 11. 不要立刻做的“简单修复”

### 禁止方案 A
`outline 4096 → 8192`

原因：v6.5 已显示 input 209,998 是独立问题；提高输出 cap 不解决输入职责膨胀，也会增加成本。

### 禁止方案 B
直接删课程正文/章节

原因：会破坏 v6.2 的教学质量。

### 禁止方案 C
让 DeepSeek 自己总结 209k 输入

原因：增加额外收费阶段，且把确定性事实保护变成模型任务。

### 禁止方案 D
把所有详细内容搬到另一个同样巨大的 structure prompt

必须从职责边界解决，而不是转移膨胀。

## 12. 最终结论格式

本轮只允许：

- `ROOT_CAUSE_CONFIRMED`
- `MULTIPLE_CAUSES_CONFIRMED`
- `ROOT_CAUSE_NOT_CONFIRMED`

## 13. STOP 门

完成：
- 精确 payload 重建
- token attribution
- duplicate audit
- outline responsibility analysis
- 1–3 个最小方案
- 修正后离线 token 预算
- deterministic content protection 验证
- Fake/contract tests
- 推荐唯一下一 patch

然后 STOP。

不得：
- 真实收费重跑
- 改正式配置 cap
- 写产品库
- 正式入口切换

## 14. 最终报告

### Baseline
- branch
- HEAD
- v6.5 evidence identity
- quota 24/50

### Exact payload
- reconstructed total tokens
- difference vs provider 209,998
- explanation of estimator difference

### Attribution
- top contributors
- duplicates
- selected vs unselected content

### Root cause
- exact cause(s)
- call chain

### Responsibility
- what outline truly needs
- what deterministic merge should protect
- what belongs to later stages

### Candidate fixes
- option
- offline input tokens
- reduction %
- semantic risk
- code surface
- rollback

### Tests
- attribution
- duplicate
- rehydration
- semantic regression

### Recommendation
只选一个最小 patch 方案。

### Final
- ROOT_CAUSE_CONFIRMED
- MULTIPLE_CAUSES_CONFIRMED
- ROOT_CAUSE_NOT_CONFIRMED

停止，不执行收费验证。
