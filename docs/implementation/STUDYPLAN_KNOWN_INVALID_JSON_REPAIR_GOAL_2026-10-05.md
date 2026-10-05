# StudyPlan 下一批 Goal：Known Invalid JSON → 有界 Batch Repair

## 0. 当前事实

本人 RC Run 已失败并保持终态：

- Run：`run_ba6527a948294cf0bbe9aab1ebc8c729`
- Acceptance：`rc-user-tiance7-cebbca03153c`
- 18 structure：PASS
- 前15个 practice：PASS
- G6 practice：FAIL
- GR / GT practice：NOT RUN
- Draft / Plan：0 / 0

第35笔真实请求：

- HTTP 200
- finish_reason = stop
- 非 length/truncation
- dispatch 结果已知
- unknown = 0
- 严格 JSON parse FAIL
- error_class = `provider_invalid_json`
- repair = 0

当前累计：

- 160 / 200
- 剩余40

旧失败 Run 永久保留，不 resume、不 retry、不 resubmit。

---

# 1. Goal

只修复一个缺口：

> 对已经明确得到 provider 响应、非截断、非 unknown 的
> `provider_invalid_json`，
> 允许 structure/practice batch 消耗现有有界 repair 通道。

不是放宽 JSON 校验。

不是重试旧 attempt。

不是恢复旧 failed Run。

---

# 2. 核心语义

严格区分：

## A. 可进入 repair

仅：

`provider_invalid_json`

并且必须证明：

- provider request 已实际 dispatch；
- provider response 已明确返回；
- dispatch_unknown = false；
- 非 output truncation；
- 原 attempt 已持久化为 known failed；
- usage/receipt 已记录。

## B. 继续直接 FAIL / STOP

包括但不限于：

- transport unknown
- timeout outcome unknown
- connection reset outcome unknown
- provider_output_truncated
- finish_reason length
- auth failure
- endpoint/security rejection
- budget/preflight rejection
- cancellation/fence failure
- unsupported schema
- 未知 error_class

不得把 `retryable` 扩展解释成“所有失败都能repair”。

必须使用显式 allowlist。

---

# 3. 实现原则

优先复用现有：

- `repair_target`
- `repair_batch`
- `max_repairs = 2`
- `planning.repair`
- deterministic attempt_key
- manifest budget
- retained attempt / receipt

不得新增新的 retry engine。

## 推荐最小实现

对于 structure/practice generation：

若返回普通 `LLMFailure`：

### 非 provider_invalid_json

维持当前行为。

### provider_invalid_json 且满足 §2.A

不要写 fatal `generation_errors` 导致直接结束。

为当前 batch 建立仅用于确定性 validation → repair 的失败占位。

例如 practice：

```text
practice_batches[index] = {
  stage_key,
  batch_index,
  payload: {}
}
```

随后继续现有：

```text
validate_practice_batch
→ structure_errors
→ repair_target(kind=practice...)
→ repair_batch
```

structure 采用同一思想，但必须保证 reviewed/canonical validator 仍然 fail-closed。

不得把 placeholder 当模型成功结果。

provider attempt 表仍必须保存：

```text
status = failed
error_class = provider_invalid_json
```

repair 必须创建新的 repair attempt。

---

# 4. 不把坏 JSON 放宽解析

禁止：

- json5
- ast.literal_eval
- 正则自动加逗号
- 自动补括号
- 自动删除 markdown fence 后猜 JSON
- substring extraction 后冒充严格响应
- 修改原 provider body
- 将 parse failure 转为 LLMResult
- 将坏正文写成正常 batch

严格 parser 继续保持。

修复发生在**工作流级有界 repair**，不是 parser 容错。

---

# 5. 原坏正文处理

使用本轮保存的真实 G6 invalid JSON 作为 immutable fixture。

必须核对 SHA，不修改原文件。

测试 adapter：

```text
真实保存response
→ strict parser
→ provider_invalid_json
→ known failure
```

然后用 Fake repair response 完成：

```text
known invalid normal
→ repair_target
→ planning.repair attempt 1
→ strict parsed result
→ practice validator
→ PASS
```

原则上不需要把整段坏 JSON 保存进 LangGraph state/checkpoint。

如果现有 durable attempt 已经保存原body，只引用其既有证据。

不要为本任务新增“把模型原文写进checkpoint”的机制。

---

# 6. 必须测试

至少包含以下独立案例。

### repairable

1. practice known invalid JSON → repair1 → PASS
2. structure known invalid JSON → repair1 → PASS
3. normal invalid JSON attempt 仍是 failed
4. repair attempt 使用新的 deterministic ID
5. repair_count 从0→1
6. 总 request budget 正确增加1
7. output budget包含该repair
8. repaired batch仍需完整 canonical/task validator
9. repair返回合法JSON但业务非法 → 仍按现有规则处理
10. repair自身 known invalid JSON → 不绕过上限

### 必须禁止

11. dispatch_unknown → 0 repair
12. truncated/length → 0 repair
13. local preflight拒绝 → 0 repair
14. budget拒绝 → 0 repair
15. auth/security失败 → 0 repair
16. failed历史Run启动新Worker后不能claim/resume
17. 当前本人失败Run不能恢复
18. 同一 normal attempt 不会重新派发

### checkpoint / PG

使用新 owned business + checkpoint DB：

- known failed attempt可读取；
- repair attempt单独持久化；
- crash/checkpoint replay不重复 normal；
- crash后已有 repair receipt 不重复收费；
- unknown保持 reconciliation；
- repair成功后后续batch继续；
- 最终 Draft 只能来自完整校验通过状态。

---

# 7. 保留当前真实失败证据

以下事实永久保留：

- 本人RC第一次完整生成 FAIL
- 35 normal
- repair0
- request160 provider_invalid_json
- original provider body
- receipt
- usage
- failed Run
- Draft0 / Plan0

不得把修复后的 fixture PASS 写成：

“原本人RC已PASS”。

它只能证明：

“该失败类型现在可被未来新Run的有界repair处理”。

---

# 8. 收费边界

本轮实现和验证：

**产品真实模型调用 = 0。**

当前：

```text
160 / 200
remaining = 40
```

在下面全部 PASS 前不得使用剩余额度：

- fixture
- unit/contract
- Fake
- owned PG
- real checkpoint
- budget/admission
- invalid-json negative matrix
- failed/unknown no-replay

全部 PASS 后 STOP 并提交报告。

不要自动创建新用户Run。

---

# 9. 下一次收费执行

仅在上述修复全部非收费 PASS，且用户批准后：

创建：

- 新 Acceptance
- 新 Run
- 同一 RC 用户正常UI流程

不得复用：

`run_ba6527a948294cf0bbe9aab1ebc8c729`

完整预算仍是：

```text
37 normal
+ max 2 repair
= max 39
```

当前余额40，因此：

- 只允许最后一个完整用户Run；
- 不建立第二个代表；
- unknown立即STOP；
- 不因余额存在而重复生成。

如果该新Run PASS：

停止收费，进入用户内容/体验验收。

如果出现新的独立FAIL：

STOP，不自动再次生成。

---

# 10. 明确禁止过度优化

本批不要：

- 修改 prompt 以“顺便提高 JSON 稳定性”，除非离线证据证明现有 schema 指令缺失且这是必要根因；
- 换模型；
- 提升 temperature/cap；
- 新建 retry framework；
- 新建通用 parser；
- 重写 Graph；
- 改 API/DTO/schema/migration；
- 改 Agent8 内容；
- 改 canonical/practice 权威规则；
- 改 repair2；
- 重跑完整收费代表；
- 启正式Worker；
- 写原产品库；
- push/merge/deploy。

目标只有：

**让一个“已知、非截断、严格JSON语法失败”的结构/practice batch，安全地消费现有 repair，而不是让整条 Run 直接死亡。**