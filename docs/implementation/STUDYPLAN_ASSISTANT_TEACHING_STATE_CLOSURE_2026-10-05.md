# Learning Assistant V1.1 — Teaching State Closure

## 当前事实

当前分支：

`feat/n1-resource-discovery`

reported HEAD：

`09c8242b1df64f9dc641f67981d2ff967162b210`

migration head：

`0025`

产品模型账本：

`164 / 280`

remaining：

`116`

当前结果：

- 非收费实现与验收 PASS；
- request 163 教学 PASS；
- request 164 provider / JSON / Run 均成功，但教学 FAIL；
- 未达到 `LEARNING_ASSISTANT_CORE_PASS`。

必须保留 163 / 164 原 request、body、receipt、Run 和教学验收结果。

不得倒改历史。

---

## 1. 根因边界

不要把本问题归因为：

- provider失败；
- JSON失败；
- truncation；
- unknown；
- completed_rounds缺失；
- system prompt缺失。

现有证据已经证明：

- request164收到正确 completed_rounds；
- system包含“只问尚未解决问题，不重复已解决问题”；
- provider / JSON / 应用Run成功；
- 模型仍然确认一个问题已解决后再次追问它，并提前教学。

因此本轮不要继续通过单纯增加自然语言提示来解决。

目标是：

> 对需要确定执行的教学阶段增加最小结构状态。

---

# 2. 不建设复杂教学状态机

禁止新增：

- 每问题独立attempt counter；
- 教学工作流引擎；
- 新Agent；
- mastery系统；
- scorer；
-第二次模型judge调用；
-每轮多模型调用。

继续满足：

`1 user Send <= 1 product model request`

用户界面仍是自然聊天。

用户不得看到：

- issue ID；
- phase内部状态；
- evaluation JSON。

---

# 3. 最小 Current Issue Ledger

第一轮 Summary / Practice 诊断最多产生：

3～5 个关键问题。

模型输出结构化 issues。

概念合同：

```json
{
  "phase": "question_round_1",
  "reply": "简短自然过渡语",
  "issues": [
    {
      "topic": "简短主题",
      "question": "需要用户思考的问题"
    }
  ],
  "proposal": null
}
```

服务器校验后，为 issues 按顺序生成自己的稳定ID：

`i1 ... iN`

模型提供的ID无权威。

该 issue ledger 必须绑定：

- conversation；
-对应成功 turn；
-冻结 Plan/stage/task；
-原始用户消息。

优先复用现有 assistant turn/result/receipt 可表达结构。

不要修改0025。

只有在现有持久化无法安全恢复该ledger时，先提交证据说明，再考虑最小后继迁移。

---

# 4. Round 2：模型只做 issue evaluation

第二次用户回答时，请求必须包含服务器保存的 issue ledger。

模型输出：

```json
{
  "phase": "question_round_2",
  "reply": "简短反馈",
  "evaluation": [
    {
      "issue_id": "i1",
      "state": "resolved",
      "followup_question": null
    },
    {
      "issue_id": "i2",
      "state": "unresolved",
      "followup_question": "仅针对该未解决问题的追问"
    }
  ],
  "proposal": null
}
```

只允许：

`state = resolved | unresolved`

确定性校验：

1. 每个上一轮 issue 必须且只能出现一次；
2. 不允许未知 issue_id；
3. resolved：
   - followup_question 必须 null；
4. unresolved：
   - followup_question 必须为非空有界字符串；
5. 第二轮不得出现 teaching；
6. 第二轮不得出现 proposal；
7. 已 resolved issue 不得重新进入问题列表；
8. 不允许新增新的关键 issue 扩张本轮教学范围。

用户可见问题由服务器根据：

`unresolved + followup_question`

确定性组成。

不要让自由文本 reply 再承担“具体问哪些问题”的权威。

reply只能作为简短自然过渡。

---

# 5. 两轮以后：不再提问

第二轮用户再次回答后，对原 issue ledger重新评价。

## 全部 resolved

进入下一阶段：

- Summary → 可以 `ready_to_draft`
- Practice → 可以 `ready_to_draft`

## 仍有 unresolved

不得进行第三轮 Socratic question。

进入：

`teach`

模型只针对 unresolved issue 返回 explanation。

概念结构：

```json
{
  "phase": "teach",
  "reply": "简短教学引导",
  "teaching": [
    {
      "issue_id": "i2",
      "explanation": "正确解释"
    }
  ],
  "proposal": null
}
```

确定性校验：

- 只能解释 unresolved issue；
- resolved issue不得重复教学；
- 不允许question字段；
- 不允许新增issue。

---

# 6. Summary 教学后的重新表达

Summary 在 teach 后：

服务器/前端本地显示固定提示，不调用模型：

“现在请你再用自己的话重新总结一下这些关系。
不用照着我的表述复述，按你的理解说明就可以。”

用户下一次发送后才调用模型。

如果已基本解决关键问题：

返回：

`ready_to_draft`

并产生 proposal。

如果仍存在严重核心误解：

可以继续直接纠正，但不得重新进入第一/第二轮盘问。

不要形成无限教学循环。

保留用户随时使用主页面非AI正式保存路径。

---

# 7. Practice 教学后的处理

Practice 在两轮后仍有 unresolved：

- 直接解释；
- 可以在同一成功回复中进入 `ready_to_draft`；
- 基于当前对话整理建议最终 Prompt。

不得要求用户重新手写完整 Prompt。

不得扩大原任务范围。

不得声称 Prompt 已执行或任务已验收。

---

# 8. ready_to_draft

继续保留：

```json
{
  "phase": "ready_to_draft",
  "reply": "...",
  "proposal": "..."
}
```

或与现有 status 字段兼容的等价结构。

仍然只有用户明确：

- 采用并保存；
- 修改后保存；

才调用原正式 Summary / Prompt 保存服务。

保存 = 0 assistant model requests。

---

# 9. extra fields 与严格失败边界继续保持

继续保留 V1.1 已实现规则：

模型额外无权威字段：

- message_id；
- conversation_id；
- run_id；
- role；
- metadata；

忽略并仅记录 diagnostics。

不得用于业务身份。

继续严格 FAIL：

- invalid JSON；
- missing/wrong reply；
-非法 phase/state；
- issue集合不匹配；
- resolved却带followup；
- unresolved缺followup；
- teach引用未知/resolved issue；
- proposal合同错误；
- unknown；
- truncation；
- budget/security/fence。

无 assistant repair。
无自动HTTP retry。
不修改 planning known-invalid-json repair。

---

# 10. 使用 request163/164 作为离线真实 fixture

不得重新调用provider。

保留原body SHA。

首先把163解析为：

- 初始issue ledger。

然后将164当作真实失败fixture。

离线证明新的结构合同会阻止以下行为：

- 已resolved issue重新进入followup；
- 第二轮提前teach。

同时增加正例：

- 部分resolved；
-全部resolved；
-多个unresolved；
-第二轮只剩一个问题；
-第二轮后teach；
-Summary teach→本地重新表达提示；
-Practice teach→proposal。

先完成 unit/contract/Fake/owned PG/API/Worker/Edge。

产品模型调用必须保持0。

---

# 11. 不重新做已经稳定的UI

本轮不要重新设计：

-聊天侧栏；
-固定欢迎；
-我的会话；
-采用保存；
-修改后保存；
-窄屏；
-恢复；
-正式保存页面。

只有新结构结果需要的最小渲染改动允许修改。

原生 beforeunload 自动化 NOT RUN 留到本人体验验收。

不要为了这个问题阻塞核心修复。

---

# 12. 最终真实教学代表

所有非收费门禁 PASS 后：

允许一个新的 Acceptance。

最多 **7 个新的 assistant.coach 请求**。

执行前读取真实账本，不能只相信164基准。

顺序：

## Summary

1. flawed summary  
   → 一次提出3～5项关键问题。

2. 用户部分回答  
   → 已解决问题必须消失，只追问remaining。

3. 用户仍有错误  
   → 不再提问，直接teach unresolved。

4. 用户按固定提示重新用自己的话表达  
   → ready_to_draft + Summary proposal。

然后显式保存候选或修改后保存。

保存不得产生assistant请求。

## Practice

5. weak Prompt  
   → 集中问题。

6. 用户部分回答  
   → 只追问remaining。

7. 用户仍有关键缺口  
   → teach + ready_to_draft + Prompt proposal。

然后显式保存。

---

# 13. Stop规则

任一新请求出现：

- unknown；
- truncation；
- invalid JSON；
- issue ledger identity不一致；
- resolved issue重新被question；
-第二轮提前teach；
-第三轮继续Socratic question；
-重复收费；
-正式成果污染；
-权限/scope问题；

立即 STOP。

不得为了完成7次继续请求。

---

# 14. PASS标准

只有全部通过才标：

`LEARNING_ASSISTANT_CORE_PASS`

至少包括：

- request163/164离线fixture合同关闭；
- round1 issue ledger PASS；
- round2 resolved/unresolved PASS；
- solved issue不重复提问；
-第二轮不提前teach；
-两轮后teach PASS；
-Summary重新表达 PASS；
-Practice直接整理proposal PASS；
-两种proposal正式保存 PASS；
-UI恢复/刷新/重登录 PASS；
-RLS/scope PASS；
-unknown0；
-无学习状态污染；
-原产品库写入0；
-真实Summary + Practice完整链 PASS。

---

# 15. Scope Freeze

本轮不做：

- WeKnora；
-其他RAG；
-启动数据；
-部署；
-正式库；
-多Agent；
-Streaming；
-附件；
-向量记忆；
-评分；
-新教学功能。

不push。
不merge。
不deploy。

完成后报告并 STOP。