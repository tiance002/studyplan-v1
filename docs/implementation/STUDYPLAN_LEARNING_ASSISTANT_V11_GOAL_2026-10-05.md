# StudyPlan Learning Assistant V1.1 最终产品收口 Goal

## 0. 任务性质

这是现有 Learning Assistant V1 的**产品体验与教学逻辑收口**。

不是重新开发聊天系统。

保留现有已经完成并验证的：

- assistant conversation/message/turn 持久化；
- RLS / actor / project scope；
- Plan revision / stage / task 冻结绑定；
- ai_runs/jobs、标准 Worker、budget/claim/fence；
- Summary / Prompt 原正式保存服务；
- formal save / CAS / 幂等；
- “我的会话”恢复；
- refresh / logout / relogin；
- 0025 migration；
- 旧 Plan 会话只读保护；
- planning Known Invalid JSON repair；
- 原规划 canonical / source / task / completion 规则。

不要推倒重做。

开始前只读核对实际 HEAD、migration head、模型账本和工作区。

报告基准为：

- branch: `feat/n1-resource-discovery`
- reported HEAD: `91750cbb345c7f428dd17809affcf4b50da2865b`
- migration head: `0025`
- product-model used baseline: `162 / 280`

如果实际 HEAD 是该提交的后继，保留后继成果，不 reset / checkout 回退。

---

# 1. 最终产品原则

Learning Assistant 应表现为正常、简洁的 Chat Agent。

用户不应该看到内部测试工具式 UI。

主原则：

> 主页面负责学习内容、任务要求和正式成果。  
> Learning Assistant 负责教学、提问、纠错、讨论以及整理候选成果。

Assistant 永远不能：

- 自动保存正式 Summary；
- 自动保存正式 Prompt；
- 自动标记阶段完成；
- 自动标记知识 VERIFIED；
- 自动让 Practice 通过；
- 自动改变 USER decision；
- 自动修改 Plan；
- 声称代码/Prompt 已真实执行成功。

正式保存永远需要用户明确操作。

---

# 2. UI：改为简洁聊天侧栏

删除当前偏“内部控制台”的表现。

## Header

只显示：

### Summary

`学习助手`

`阶段总结 · <stage title>`

### Practice

`学习助手`

`实践辅导 · <task title>`

右侧只保留必要的：

- `…`
- close

默认不要展示：

- stage_id
- task_id
- conversation_id
- run_id
- hash
- Plan内部版本号
- provider状态
- receipt
- Worker状态
- 大块技术状态卡

这些信息仍可存在于后台日志和 diagnostics。

## Conversation Body

正常聊天时间线：

- assistant message
- user message
- inline system/error state
- proposal card

避免大面积边框和控制面板式卡片。

## Composer

底部固定：

- 多行文本框；
- Send。

删除：

- “消息意图”选择器；
- 每条消息 consent checkbox；
- “发送即表示同意……”之类常驻提示。

不要新增新的逐消息 consent UI。

如果现有产品设置已有模型/隐私说明，继续放在原设置体系，不放进正常聊天界面。

## Responsive

桌面目标为约 420–480 px 的聊天侧栏。

窄屏转换成全屏 drawer。

继续保护：

- 未发送文本；
- close / reopen；
- refresh；
- focus return；
- Escape；
- logout / relogin。

---

# 3. 固定开场：不调用模型

创建新 Summary / Practice 会话时，第一条 assistant message 使用本地确定模板。

不得调用产品模型。

## Summary 固定开场

> **把你对本阶段的总结发给我。**
>
> 我会重点检查：
> - 核心知识是否覆盖；
> - 关键概念之间的关系是否讲清楚；
> - 有没有明显误解或遗漏；
> - 是否能用自己的话说明本阶段重点。

不要再追加产品行为说明。

尤其不要告诉用户：

- “我会先问两次……”
- “如果你不会我会告诉答案……”
- “最后我会生成总结……”
- “采用并保存……”

这些属于系统行为，用户通过交互自然体验。

## Practice 固定开场

> **把你准备交给 AI / Codex 的 Prompt 发给我。**
>
> 我会重点检查：
> - 任务目标是否明确；
> - 修改范围和约束是否清楚；
> - 输入与输出要求是否完整；
> - 验收标准是否能真正证明任务完成；
> - 有没有容易让 AI 扩大范围或误解任务的地方。

同样不要解释后面的教学流程。

---

# 4. 删除“消息意图”

用户不再选择：

- 工作稿；
- 追问；
- 修改稿；
- 普通问题。

conversation.mode 已经通过入口确定：

- `summary`
- `practice`

模型根据自然语言和有限会话上下文理解用户行为。

如果确实无法判断用户含义，可以正常在对话中询问，而不是重新增加 UI selector。

所有用户输入首先只是 conversation message。

不要因为某句话看起来像“新稿”，就在后台自动把它提升成正式 Summary / Prompt。

---

# 5. 教学交互：批量诊断，而不是一次问一个问题

这是本轮核心产品规则。

## 第一轮

用户提交 Summary 或 Prompt 后：

先完整诊断当前输入的所有重要问题。

内部可以识别很多问题，但用户可见回复只提出**最重要的 3～5 个关键问题**。

优先级：

1. 关键事实错误；
2. 关键概念关系错误；
3. 会影响理解/执行的重要遗漏；
4. 关键范围/边界；
5. 关键验收缺失。

普通：

- 措辞；
- 排版；
- 格式；
- 轻微表达优化；

不要浪费问答轮次，最终整理 proposal 时直接改善。

禁止默认“一次只问一个问题”。

问题应集中在同一条 assistant message 中，可以编号。

例如：

> 还有三个关键点需要再想一下：
>
> 1. …
> 2. …
> 3. …
>
> 可以一起回答，不需要分别发送。

---

# 6. 第二轮：只追问剩余问题

用户第一次集中回答后，再全面检查。

已经解决的问题不得重复问。

第二轮只针对仍然存在的关键问题。

仍然应尽可能集中到一条回复中。

不要为了保持聊天轮数，重复已经理解的内容。

---

# 7. 两轮仍不会：停止继续盘问，直接教学

不要实现“每一个问题独立两次计数”的复杂状态机。

采用**整体两轮引导制**：

1. 第一轮集中问题；
2. 第二轮剩余问题；
3. 第二轮以后仍存在关键误解 → 直接教学。

不需要 issue ID / 每问题 attempt counter / 复杂问题状态机。

如果第二轮之后仍有多个问题：

一次统一讲清楚。

---

# 8. Summary 与 Practice 在“教学后”有不同规则

## 8.1 Summary

如果用户两轮以后仍存在关键知识误解：

Assistant：

1. 明确解释正确概念；
2. 给必要例子/对比；
3. 然后明确要求用户重新用自己的话表达。

推荐措辞：

> **现在请你再用自己的话重新总结一下这些关系。**
>
> 不用照着我的表述复述，按你的理解说明就可以。

这是 Summary 的必要教学闭环。

AI 告诉答案以后，不能立即因为“AI已经写出来了”就直接认为用户完成总结。

必须至少让用户进行一次重新表达。

如果重新表达已经基本正确：

→ `ready_to_draft`

如果仍然只有轻微、非核心表达问题：

不要继续第三轮盘问，可在 proposal 中整理。

只有仍存在严重核心错误时，才继续指出。

如果用户最初的总结已经足够好：

可以不经过提问，直接进入 `ready_to_draft`。

---

## 8.2 Practice

Practice 不要求用户在 AI 教学后重新手写整份 Prompt。

两轮以后仍有关键执行缺口：

1. AI 解释为什么当前写法不足；
2. 给出正确设计原则；
3. 可以直接根据整个对话整理建议 Prompt。

因为 Practice Assistant 本身承担“帮助用户把想法整理成可执行 Prompt”的职责。

但不得宣称：

- Prompt 一定正确执行；
- 工程已经通过；
- Codex 已完成任务；
- 验收已经真实发生。

这里只能判断：

> 当前对话已有足够信息形成一份边界较完整的候选 Prompt。

---

# 9. readiness 的正确含义

内部语义使用：

`ready_to_draft`

不要使用：

- mastered
- passed
- completed
- verified

`ready_to_draft` 只表示：

> 当前对话已经有足够信息，可以整理一份候选 Summary / Prompt。

它不改变任何正式学习状态。

---

# 10. Assistant 输出协议

仅修改：

`assistant.coach / assistant-coaching-v1`

不要修改 planning 的结构化输出合同。

建议 canonical assistant response：

```json
{
  "reply": "给用户显示的正常回复",
  "status": "continue",
  "proposal": null
}
```

或者：

```json
{
  "reply": "现在已经可以整理成一版总结。",
  "status": "ready_to_draft",
  "proposal": "完整候选内容"
}
```

合法：

`status = continue | ready_to_draft`

规则：

### continue

- reply 非空、有界；
- proposal 应为 null。

### ready_to_draft

- reply 非空、有界；
- proposal 必须为非空、有界字符串。

严格 JSON parser 保持。

---

# 11. 模型额外字段：忽略，不给业务权威

真实 fixture 已证明模型可能返回：

```json
{
  "reply": "...",
  "message_id": "..."
}
```

这类额外字段不应导致整个正常回复失败。

assistant.coach 只消费：

- reply
- status
- proposal

额外字段：

- message_id
- conversation_id
- run_id
- role
- metadata
- arbitrary object/list/scalar

全部丢弃。

可以在 non-authoritative diagnostics 中记录字段名。

绝不能使用模型提供的 ID 覆盖：

- server message ID；
- conversation ID；
- Run/turn；
- actor/project；
- Plan/stage/task binding；
- formal save；
- completion；
-任何业务身份。

旧第162次失败记录永久保持 FAIL，不倒改历史。

---

# 12. 仍然严格 FAIL 的情况

以下仍 fail-closed：

- JSON syntax invalid；
- reply 缺失；
- reply 非 string；
- reply 空；
- reply 超长；
- status 非法；
- ready_to_draft 但 proposal 缺失；
- proposal 类型错误；
- proposal 超长；
- dispatch unknown；
- truncation / length；
- auth/security；
- budget/preflight；
- lease/fence/cancel。

禁止：

- JSON5；
- regex 修 JSON；
- substring 猜 reply；
- 自动 assistant repair；
- 自动 retry；
- 把 planning known-invalid-json repair 扩展到 assistant。

planning repair2/canonical/source/task 等规则完全不动。

---

# 13. Proposal 卡片

当：

`status = ready_to_draft`

在对应 assistant message 下显示轻量 proposal card。

## Summary

标题：

`建议阶段总结`

按钮：

- `采用并保存`
- `修改后保存`

## Practice

标题：

`建议最终 Prompt`

按钮相同：

- `采用并保存`
- `修改后保存`

### 采用并保存

把 proposal 原文交给已有正式 Summary / Prompt 保存服务。

### 修改后保存

打开 inline editor。

默认填入 proposal。

用户编辑后，明确点击：

`保存我的版本`

再调用同一个正式保存服务。

AI 永远不能自动保存。

---

# 14. Proposal 内容边界

## Summary

主要整理：

- 用户自己表达过的知识；
- 对话中已经明确纠正过的内容；
- 当前阶段既有学习要求。

不要为了“写得高级”偷偷加入大量用户没有学习、没有讨论的高级知识。

AI 可以：

- 调整结构；
- 去重复；
- 改表达；
- 把已经讲清的关系组织得更清楚。

## Practice

可以：

- 整理目标；
- 结构化范围；
- 明确约束；
- 明确输入输出；
- 明确验收。

但不得偷偷扩大原任务。

不得新增新的强制产品能力。

---

# 15. Prompt Injection 边界

Practice 中用户粘贴的 Prompt 是：

**untrusted content / 被审阅的数据**

它不是 Learning Assistant 的 system instruction。

例如被审 Prompt 中出现：

“忽略上面的要求……”

不得改变 assistant 自身的：

- system rules；
- scope；
- Plan/task binding；
-保存权限；
-数据权限。

同理：

- 学习资料；
-未来 RAG 内容；
-用户粘贴文本；

均不得提升为 system instruction。

加入对应测试。

---

# 16. “开始总结 / 开始实践”的会话恢复策略

更新旧的“每点一次必新建会话”行为。

对于相同：

### Summary

`actor + project + plan_revision + stage + summary`

如果存在仍可继续的最近会话：

→ 默认恢复，而不是新建重复会话。

### Practice

`actor + project + plan_revision + stage + task + practice`

同理优先恢复。

用户如果真的想重新开始：

放在 `…` 菜单中：

`新建会话`

旧 Plan revision 的会话：

- 可以读取；
- 不得向新 Plan 误发；
- 不得向新 Plan 正式保存。

不要因此引入复杂的 conversation lifecycle 状态机。

优先复用现有字段和语义。

不要修改0025。

如果确实无法在现有数据结构表达，必须先证明必要性，再使用新的最小后继迁移；禁止回改0025。

---

# 17. 错误 UI

错误必须表现成聊天的一部分，而不是占据整个页面。

例如 known reply failure：

> ⚠ 这次回复生成失败，你的消息已经保存。

unknown：

> ⚠ 这次回复状态正在核对，暂时不能重新发送。

unknown 情况禁止提供会产生重复收费的重试。

会话创建结果未确认：

显示小型：

`重新读取状态`

不要重复创建 conversation。

底层原有费用保护不能因为 UI 简化而削弱。

---

# 18. “我的会话”

保持轻量。

列表只显示用户有意义的信息，例如：

- 阶段总结 / 实践辅导；
- stage/task title；
- 最近时间；
- 是否已经保存正式成果。

不要展示：

- Run ID；
- provider；
- receipt；
- hash；
- internal status。

打开后恢复原聊天。

---

# 19. 每次用户发送最多一个模型请求

费用规则：

> 一个用户 Send → 最多一个 assistant.coach 请求。

禁止一个用户消息触发模型自己连续调用多次。

固定欢迎语：

0请求。

保存 proposal：

0 assistant 请求。

恢复会话：

0请求。

刷新：

0请求。

这样模型费用始终由用户主动聊天驱动。

---

# 20. 非收费验收先完成

真实 provider 请求必须先保持 0。

至少覆盖：

## Backend

- assistant response canonical projection；
- extra field ignored；
- fake message_id cannot override server identity；
- continue；
- ready_to_draft + proposal；
- invalid status；
- missing proposal；
- bad reply；
- oversize；
- invalid JSON；
- unknown/truncation；
- budget/security/fence；
- Prompt injection fixture；
-旧第162次 fixture；
-历史失败不可倒改。

## Teaching

Fake 场景证明：

### Summary

1. flawed summary；
2. 一次集中提出3～5个关键问题；
3. 用户回答部分问题；
4. 第二轮只问剩余问题；
5. 用户仍答错；
6. assistant直接教学；
7. 明确要求用户用自己的话重新表达；
8. 用户重新表达正确；
9. ready_to_draft；
10. proposal；
11. adopt/save；
12. custom edit/save。

同时证明：

用户第一次已经很好时，可以直接 ready_to_draft。

### Practice

1. weak Prompt；
2. 集中提出关键缺口；
3. 第二轮只问剩余缺口；
4. 仍不会时直接教学；
5. 整理 proposal；
6. adopt/save；
7. custom edit/save。

## UI / Edge

验证：

- 简洁聊天布局；
- 无 intent selector；
- 无 consent checkbox；
- 无技术 ID；
- 固定欢迎语；
- questions batched；
- proposal card；
- adopt；
- custom edit；
- close/reopen；
- 未发送输入保持；
- refresh；
- logout/relogin；
- 我的会话恢复；
-旧Plan只读；
-窄屏；
-Escape/focus；
- API失败仍保留用户输入。

## PG / Security

继续用普通 app-role：

- RLS；
- cross actor/project；
- scope；
- CAS；
- idempotency；
- receipts；
- Worker recovery；
- backup/restore受影响范围。

---

# 21. 真实模型最终代表

只有所有非收费门禁 PASS 后才能进入。

当前产品模型账本基准：

`162 / 280`

执行前重新读取真实账本。

本轮最多允许：

**7 个新的 assistant.coach 真实请求。**

使用：

- 新 Acceptance；
- 新 owned business/checkpoint；
- 新合成账号；
- 新合成 Plan；
- 新 Summary conversation；
- 新 Practice conversation。

不得恢复旧第162次 failed turn。

## Summary真实教学链：最多4次

1. 用户提交故意包含多个关键问题的总结  
   → Assistant 应一次性提出主要问题。

2. 用户解决一部分  
   → 只追问剩余项。

3. 用户仍错误  
   → Assistant 直接教学并要求重新用自己的话总结。

4. 用户重新正确表达  
   → `ready_to_draft` + 建议阶段总结。

然后：

- 采用保存或自定义保存；
- 保存操作不得新增 assistant model request。

## Practice真实教学链：最多3次

5. 用户提交明显不完整 Prompt  
   → 集中提问。

6. 用户解决部分  
   → 只追问剩余项。

7. 用户仍缺关键验收/边界  
   → 直接解释并形成 `ready_to_draft` + 建议最终 Prompt。

然后正式保存，不新增模型请求。

---

# 22. 真实验收停止规则

如果任一新请求出现：

- unknown；
- truncation；
- invalid JSON；
-新型安全/身份问题；
-持久化不一致；
-重复收费；
-正式成果污染；
-新独立严重逻辑失败；

立即 STOP。

不要为了跑完7次继续消费。

普通额外无权威 JSON 字段：

只记录 ignored_fields，不应令合法 reply/proposal 失败。

---

# 23. Learning Assistant Core PASS 条件

只有以下全部成立，才可以标：

`LEARNING_ASSISTANT_CORE_PASS`

- 新简洁聊天UI PASS；
- fixed welcome 0 model calls；
- message intent UI删除；
- per-message consent UI删除；
- Summary批量诊断PASS；
- Summary两轮引导PASS；
- Summary教学后重新表达PASS；
- Summary proposal/save PASS；
- Practice批量诊断PASS；
- Practice两轮引导PASS；
- Practice教学+proposal PASS；
- extra model fields non-authoritative PASS；
- strict failure boundaries PASS；
- RLS/scope PASS；
- proposal adopt/custom save PASS；
- 我的会话恢复PASS；
- refresh/logout/relogin PASS；
-旧Plan readonly PASS；
- actual real assistant representative PASS；
- unknown = 0；
-无正式学习状态污染；
-原产品库写入 = 0。

---

# 24. 本轮禁止扩展

不要做：

- RAG；
- vector memory；
- streaming；
- attachments；
- voice；
- multi-agent；
- Teacher/Evaluator/Coach 多角色框架；
- mastery score；
- spaced repetition；
-自动改 Plan；
-自动执行 Prompt；
-自动 Practice 验收；
-通用聊天平台；
-新搜索系统；
-启动数据扩充。

这些都不是本轮。

---

# 25. 发布边界

本轮仍然：

- 不写原产品库；
- 不启动正式入口；
- 不启动正式 Worker；
- 不部署；
- 不 push；
- 不 merge；
- 不操作独立 RAG 项目。

结束时报告：

1. actual HEAD；
2. migration head；
3. 修改文件；
4. unit/contract数量；
5. PG/API数量；
6. frontend/build；
7. Edge结果；
8. 真实请求逐条 input/output/finish/result；
9. 当前累计模型用量；
10. remaining quota；
11. 是否满足 `LEARNING_ASSISTANT_CORE_PASS`；
12. 本人最终体验验收仍需做什么。

完成后 STOP。

不要继续自行增加功能。