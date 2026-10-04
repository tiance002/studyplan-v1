# Codex Goal — StudyPlan v6.7 Outline 投影与确定性内容保护 Patch

日期：2026-10-04
正式工程：`D:\studyplan`

## 0. 本轮目标

基于 v6.6 已确认的 `MULTIPLE_CAUSES_CONFIRMED`，实施一个**有版本边界、可回滚、完全离线验收**的局部 patch：

1. 未来新 Run 的 outline 改为“冻结阶段骨架投影”；
2. 旧 Run / 旧 manifest / 旧 attempt 保持 legacy 行为和 fingerprint；
3. outline 不再携带整包 resources / publication_evidence / practice / project-study 全文；
4. reviewed 内容继续由本地权威数据确定性恢复；
5. 同时修复 v6.6 暴露的两个既有保护缺口：
   - 唯一知识节点 `title/objectives/scope/acceptance` 未完整确定性保护；
   - 次级 practice 与冲突 acceptance 仍可能被模型/结构结果污染。

本轮 **真实模型调用 = 0**。

完成后 STOP，不自动执行收费重跑。

---

# 1. 事实基线

开始前核对：

```powershell
cd D:\studyplan
git status
git branch --show-current
git rev-parse HEAD
git log -8 --oneline
```

已知 v6.6 结论：

- 旧真实 provider input：209,998 tokens
- 当前离线重建：
  - messages 578,108 chars
  - HTTP JSON 816,500 bytes
- resources：402,175 chars
- publication_evidence：132,909 chars
- selected stage blueprints：22,170 chars
- manifest：8,705 chars
- 6 个 stage 已正确裁剪，不是 61 stage 全量进入
- 179 个 section metadata 进入，但不是 179 篇正文
- 推荐 Option1：
  - frozen skeleton projection
  - 4,112 message chars
  - char/4 估计 1,028 tokens
  - 同口径字符减少 99.29%
- quota：24/50
- 本轮不得增加真实请求

以上必须从当前 repo / v6.6 证据重新确认，不以本文件代替事实源。

---

# 2. 绝对边界

## 允许

- 修改生成器内部 outline input projection
- 修改 outline 专用 internal shape/system prompt
- 在 immutable manifest 中新增**有版本语义的内部格式标记**
- 新增/强化 deterministic merge / validation
- 新增 unit / contract / PG / Fake tests
- 新增 migration-free JSONB 字段使用（仅现有结构允许时）
- 文档和回滚说明

## 禁止

- 新 planner
- 新模型调用阶段
- LLM pre-summarizer
- embedding prompt compression
- 删除/降低 reviewed Seed
- 删除章节级内容
- 改公开 API / DTO（除非现有内部字段无法承载，需先 STOP 报告）
- 新 migration（默认不允许）
- 改 outline cap 4096
- 改 structure/repair cap 8192
- 改 provider/model/temperature
- 真实 DeepSeek 请求
- 写原产品库
- 切正式入口
- 启动正式 Worker daemon
- 修改 RAG

---

# 3. Patch A — 冻结 outline format marker

## 3.1 新未来提交

仅对**未来新提交**冻结内部格式标记，例如：

```text
outline_input_format = "stage_skeleton_v1"
```

具体字段名以现有 manifest 结构和命名规范为准，不要为了照抄示例引入新 DTO。

要求：

- marker 必须进入现有 immutable manifest hash / digest
- 同一个 Run 不允许执行中切换格式
- resume / recovery 必须读取冻结值
- 新格式只对未来 Run 生效

## 3.2 旧 Run

旧 manifest 没 marker：

```text
→ legacy
```

要求：

- legacy outline wire/input 行为保持
- 旧 attempt fingerprint 保持
- 旧 checkpoint 恢复不变
- v6.5 failed Run 不重派
- 历史 unknown 不重派

不得批量给旧 manifest 回填 marker。

---

# 4. Patch B — outline 专用 stage skeleton projection

实现局部 pure projection。

新格式 outline 输入只允许包含模型当前职责真正需要的内容：

## 必需

- user goal
- GoalSpec（存在则投影）
- starting point / constraints（存在则投影）
- resource preference 中真正影响阶段表达的简短字段
- semantic_context 的短语义：
  - user project / starter fallback
  - optional semantics
  - recipe/gap semantics
- 已冻结 6 stage：
  - stable key
  - current title
  - concise objective / capability summary
  - kind
  - prerequisite keys
- selected knowledge 的：
  - stable key
  - title
  - concise objectives
  - prerequisite keys
- outline 专用输出 schema
- personalization boundary

## 禁止进入新 outline prompt

- 全 resources catalog
- 未选 resource / section
- publication_evidence
- surrounding teaching Markdown
- full review_evidence
- URLs 全量
- section review notes
- teaching_strengths / weaknesses 全量
- full guidance
- extensions 全文
- practice blueprints
- project-study card prompt
- exposure/prerequisite 全矩阵
- hold 审核材料全文

这些对象继续留在 frozen full pack / local authority 中，
不是删除数据。

---

# 5. Patch C — outline 专用输出职责

新格式 outline 输出只允许模型修改/提供：

- stage stable_key（必须等于冻结集合，不能新增删除）
- personalized title
- personalized objective
- limited rationale（如现有 Draft/UI需要）

模型不得负责生成：

- resources
- section refs
- extensions
- guidance
- practice
- project-study
- prerequisite truth
- reviewed content
- hold/publication state

`_validate_skeleton` 必须：

- 拒绝丢 stage
- 拒绝新增 stage
- 拒绝重排（当前产品语义仍冻结顺序）
- 拒绝改 stable_key
- 拒绝非法空标题/目标
- 忽略/拒绝新格式输出中的越权字段

旧格式 validator 保持兼容。

---

# 6. Patch D — deterministic rehydration

新格式 outline 返回后：

```text
personalized stage skeleton
        ↓
deterministic merge
        ↓
full reviewed stage content
```

必须从 frozen local authority 恢复：

- required knowledge
- exact resource source/version
- role
- exact section refs/scope
- learning guidance / why now
- exposure relation
- extensions
- project-study semantics
- practice blueprint
- Starter optional semantics
- Project Candidate optional semantics
- Evaluation cross-cutting
- RL optional
- user project priority
- open Recipe semantics
- hold exclusion

模型不可通过 title/objective 输出覆盖这些事实。

---

# 7. Patch E — 修复知识节点保护缺口

v6.6 已证明当前存在：

> 唯一知识节点的 `title/objectives` 可被 structure 改写并通过 validator；
> `scope/acceptance` 未完整投影/回填。

本轮修复目标：

对于 reviewed/frozen knowledge node：

- stable_key：完全冻结
- title：本地权威
- objectives：本地权威
- scope：本地权威
- acceptance：本地权威
- prerequisite / parent：本地权威

模型 structure 只允许填充**明确授权的非权威表现层字段**。

如果当前确实需要模型个性化某个字段：

必须新增独立的 presentation/personalization 语义，
不能覆盖 reviewed canonical 字段。

不要通过“把全文继续塞给模型”实现保护。

---

# 8. Patch F — 修复 practice 保护缺口

v6.6 已证明：

- 只完整保护 task_index0
- 第二任务可夹带强制 Starter
- 第一任务可夹带额外冲突 acceptance 并通过 validator

本轮规则：

## reviewed practice blueprint

对 frozen reviewed practice：

- task count / required task identity
- goal
- required deliverable
- scope
- acceptance criteria
- required/optional
- linked knowledge

全部由本地 authoritative blueprint 决定。

模型可以：

- 个性化题目说明
- 按用户项目映射业务名/示例输入
- 增加不冲突的提示

模型不可以：

- 新增强制 Starter
- 将 optional 变 required
- 新增超出 frozen capability 的强制验收
- 删除原 acceptance
- 用新 acceptance 替换 reviewed acceptance
- 添加额外 required task 绕过 blueprint

若要允许 supplementary practice：

必须显式标为：

```text
supplemental / optional
```

且不能影响阶段完成门槛。

---

# 9. Token / payload 回归门

必须新增 deterministic payload size guard。

不是硬编码 provider tokenizer，而是防止整包重新泄漏。

建议同时检查：

1. 新格式 outline messages chars
2. HTTP JSON bytes
3. 禁止字段 presence
4. selected stage/resource relation
5. publication_evidence absent

对 v6.6 同一个 6-stage fixture：

期望接近 Option1 证据（约 4.1k chars）。

不要把 4,112 当逐字符永久常量；
应设置一个合理结构上限并解释来源。

例如：

```text
messages chars <= evidence-based ceiling
```

ceiling 由当前投影字段最大合理变化确定，
不能设成 200k 这种失去意义的阈值。

---

# 10. 必做测试

## A. Legacy compatibility

1. no marker → legacy path
2. legacy payload/hash/fingerprint 与 patch 前 fixture 等价
3. legacy checkpoint resume 不改变
4. v6.5 failed Run 不可重派

## B. New marker

5. 新 submission 冻结 `stage_skeleton_v1`
6. marker 进入 manifest digest
7. resume 读取同一 marker
8. 同一 Run 不可切格式

## C. Payload

9. 6-stage fixture 不含 unselected resources
10. 不含 publication_evidence
11. 不含 practice blueprint/full extensions/full guide
12. 不含未选 stage全文
13. payload size guard PASS
14. structure/practice 输入没有因本 patch 膨胀

## D. Rehydration

15. 18 resource arrangements 相等
16. 35 exact section refs 相等
17. 13 extensions 相等
18. guides 相等
19. hold仍排除

## E. Knowledge protection

20. 恶意 structure 改 title → canonical restored/rejected
21. 改 objectives → restored/rejected
22. 改 scope → restored/rejected
23. 改 acceptance → restored/rejected
24. prerequisite/parent 不可改

## F. Practice protection

25. 第二 task 强制 Starter → rejected/removed
26. 额外 conflicting required acceptance → rejected/removed
27. 删除 canonical acceptance → restored/rejected
28. optional→required → rejected
29. supplemental task 不进入 completion gate

## G. Semantic routes

30. travel Agent
31. no-project Agent
32. Voice no Recipe
33. Node Cloud
34. AI Fullstack existing project

必须保持：

- user project priority
- Starter fallback only
- open Recipe composition
- Evaluation/RL semantics
- needs_research_or_review

---

# 11. PG/Fake 验收

本轮允许 Fake + owned PG。

至少验证：

- new submission freeze marker
- persisted manifest/readback
- worker Fake outline with skeleton format
- structure/practice downstream
- Draft 完整 reviewed content
- explicit synthetic confirm
- Plan readback
- old legacy fixture still readable

不要求 Chrome，除非 UI 因内部字段泄漏发生变化。

如果前端无改动：
Chrome 可 NOT RUN，并说明 v6.2/v6.3 已有 UI证据，本轮只改内部生成契约。

---

# 12. 不允许出现的“优化”

不得：

- 只删除 `publication_evidence`，却继续发送57个完整资源
- 仅字符串去重
- gzip prompt
- 缩短审核文本后继续全量发送
- 把整包挪去 structure
- 把 practice 全量移到另一次新模型调用
- 依靠 DeepSeek 超大 context 硬扛
- 把 outline cap 提到8192作为主要修复

必须解决职责边界，而不是压缩同一职责错误。

---

# 13. Ready 条件

本轮只有全部满足，才可标：

```text
OUTLINE_PROJECTION_PATCH_READY
```

要求：

- legacy compatibility PASS
- new marker immutable PASS
- new outline payload bounded
- reviewed content rehydration PASS
- knowledge protection PASS
- practice protection PASS
- semantic route regressions PASS
- Fake + owned PG PASS
- quota 仍24/50
- real provider requests 0
- no migration / DTO / API change
- no product DB write

否则：

```text
OUTLINE_PROJECTION_PATCH_BLOCKED
```

---

# 14. STOP

完成后 STOP。

不得自动执行真实模型代表验证。

下一步只能提出：

> 是否批准一个新的、单一 Agent5 synthetic paid Run 验证 patch。

旧 v6.5 Acceptance 永不复用。

---

# 15. 最终报告

## Baseline
- branch
- HEAD
- quota

## Code surface
- files changed
- migration/DTO/API changes
- marker semantics

## Legacy
- compatibility
- fingerprint
- recovery

## New outline
- messages chars
- HTTP bytes
- estimated tokens
- forbidden fields absent
- reduction vs v6.6

## Content protection
- resources
- sections
- guide
- extensions
- knowledge canonical fields
- practice canonical fields

## Tests
- unit/contract
- Fake
- PG
- semantic routes
- frontend/build if affected

## External
- paid requests = 0
- search requests = 0
- quota remains 24/50

## Final
- OUTLINE_PROJECTION_PATCH_READY
- OUTLINE_PROJECTION_PATCH_BLOCKED

## Next
只给一个最小下一动作。
