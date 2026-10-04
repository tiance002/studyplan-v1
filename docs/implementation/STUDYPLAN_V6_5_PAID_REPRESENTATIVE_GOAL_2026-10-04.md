# Codex Goal — StudyPlan v6.5 单一真实收费代表验证

日期：2026-10-04
正式工程：`D:\studyplan`

## 0. 本轮唯一目标

执行 **1 个 Agent5 的真实 DeepSeek 代表 Run**，验证当前正式 provider 链、真实 JSON/长输出、确定性内容保护、持久化与刷新/重登录。

这是一次有界收费验收，不是正式上线。

完成后必须 STOP。

---

# 1. 授权范围

本次明确授权：

- 仅 1 个新的 Agent5 合成验收 Run
- 使用当前正式候选 provider：
  - openai-compatible
  - `api.deepseek.com`
  - 当前 `.env` 配置的 DeepSeek 模型
- 最大正常请求：13
- 最大 local repair：2
- **总收费请求硬上限：15**
- 当前历史额度从 23/50 继续累计
- 失败请求计量
- unknown 计量并立即阻止后续派发

本次不授权：

- 第二个 Run
- AI Fullstack 真实模型代表
- Cloud 真实模型代表
- 产品用户数据
- 原产品数据库
- 正式入口切换
- 正式 Worker daemon
- RAG
- GitHub/Tavily 新调用
- master/develop merge
- push
- 自动批准正式草案

---

# 2. 执行前硬预检

必须全部 PASS 才能产生第一笔收费请求：

1. branch / HEAD / clean 状态记录
2. `api.deepseek.com` runtime DNS 仍为公网
3. endpoint guard PASS
4. TLS/证书链 PASS 或复用当前 v6.4 未变化证据，并核对代理规则 hash 未漂移
5. `.env` runtime `LLM_MAX_OUTPUT_TOKENS=8192`
6. outline/practice = 4096
7. structure/repair = 8192
8. 当前受控账本精确为 23/50
9. unknown 没有新增未决项
10. provider key存在，但不得打印
11. 新 AcceptanceId 唯一
12. 新 owned 业务库
13. 新独立 checkpoint 库
14. 目标和输入全部为 synthetic
15. 冻结 manifest 与 Agent5 publication digest
16. 不含真实用户 Summary / Prompt / Outcome / project text
17. 请求预算：
    - normal max 13
    - repair max 2
    - total max 15
    - output aggregate upper bound 94208

任何一项 FAIL：
**0 次收费请求，STOP。**

---

# 3. 合成目标

使用单一目标：

> 零基础系统学习 Agent 应用开发，先做一个最小应用。

不额外加入：

- 用户真实项目
- RAG专项强制深化
- Browser/Workflow组合
- RL训练目标
- 面试 overlay
- 私人资料

目标是验证 Common Core 真实生成链，不验证所有个性化组合。

---

# 4. 真实请求执行纪律

## 4.1 单 Run

只能创建一个新的 Run。

不得因：
- 文案不好看
- 标题不理想
- 某阶段内容偏弱
- 测试想再确认一次

而创建第二个 Run。

## 4.2 repair

只允许系统既有的 local repair 机制。

最多 2 次。

repair 必须与原失败阶段绑定，不能变成第二套 retry。

## 4.3 unknown

一旦出现：

- 网络结果未知
- provider 超时后状态不确定
- response receipt 缺失
- ledger receipt 缺失
- 是否计费无法确认

立即：

```text
STOP_UNKNOWN
```

不得重发。

## 4.4 已知失败

已知明确失败且未产生成功结果时：

只允许系统既有规则决定是否进入 local repair。

不得人工新开 Run。

---

# 5. 需要验证的真实能力

## A. Provider contract

验证真实响应是否符合当前 openai-compatible 适配器预期：

- HTTP status
- JSON envelope
- choices/message/content 等实际字段
- usage 若 provider 返回则记录；缺失不猜
- finish reason
- content length
- malformed / empty handling

不得在报告中输出 API key。

## B. 长输出与结构

必须至少观察：

- outline 请求
- structure 请求
- practice 请求

确认真实 provider 能在当前 4096/8192 配额下返回可解析结构。

不要求人为逼满 8192。

## C. 确定性保护

真实模型输出后，核对 reviewed Seed 事实未被模型静默删除/改写：

- required knowledge
- reviewed resources
- resource section/scope
- extensions/guidance
- project study semantics
- Starter optional
- Project Candidate optional
- Evaluation / RL语义

模型可个性化：
- title
- wording
- goal framing

模型不得覆盖受保护课程事实。

## D. 持久化

Run 完成后：

- draft存在
- Run终态正确
- result/ref一致
- ledger完整
- request/result receipt完整
- unknown=0

## E. 确认与回读

使用合成账号明确确认该合成草案。

然后：

- PG精确回读
- Chrome登录
- 查看路线
- 查看章节级资料
- 查看实践
- 查看Project Study
- 刷新
- 退出
- 重新登录
- 再次回读

确认/刷新/重登录阶段：
**不得新增模型请求。**

---

# 6. 成本与额度

本轮不设美元推测值。

只记录实际：

- 请求数
- input tokens（provider实际返回时）
- output tokens（provider实际返回时）
- cache字段（provider实际返回时）
- 每次终态
- repair次数
- 账本从 23/50 到实际值

硬门禁：

```text
request_count <= 15
final controlled quota <= 38/50
```

如果 provider 不返回 usage：
标 `NOT OBSERVABLE`，不得估造。

---

# 7. 失败判定

以下任何一项发生，本轮不算 PASS：

- endpoint真实请求失败且状态未知
- unknown > 0
- 超15请求
- 新开第二Run
- reviewed事实被静默删除
- provider返回无法进入现有repair/error机制
- 成功Run没有持久化
- refresh/relogin触发新收费请求
- 用户/产品私人数据进入请求
- 账本缺失或不一致

允许：
- 一个明确已知失败被现有local repair修复
- 不影响事实的模型措辞差异

---

# 8. 本轮通过标准

只有全部满足才可声明：

```text
PAID_REPRESENTATIVE_PASS
```

要求：

1. 单一 Agent5 synthetic Run
2. <=15真实收费请求
3. unknown=0
4. provider真实contract PASS
5. structure/practice真实解析 PASS
6. deterministic reviewed-content protection PASS
7. Run persistence PASS
8. explicit synthetic confirm PASS
9. PG readback PASS
10. Chrome refresh/relogin PASS
11. confirm/readback阶段新增模型请求=0
12. 原产品库/用户数据/RAG未触碰

否则声明：

```text
PAID_REPRESENTATIVE_FAIL
```

或：

```text
PAID_REPRESENTATIVE_STOP_UNKNOWN
```

---

# 9. 完成后 STOP

即使 PASS，也不得自动：

- 升级原产品数据库
- 切正式入口
- 启动正式Worker
- 跑第二方向真实模型
- 修改RAG
- push/merge

---

# 10. 最终报告

输出：

## Baseline
- branch
- HEAD
- acceptance id
- owned DB IDs/名称可脱敏记录

## Preflight
- DNS
- endpoint guard
- TLS
- cap
- current quota

## Paid run
- Run ID
- total requests
- normal requests
- repair requests
- known failures
- unknown
- provider final state

## Usage
- before quota
- after quota
- input/output/cache tokens if observable
- no fabricated dollar estimate

## Content protection
- protected facts PASS/FAIL
- any model customization
- any dropped/rewritten reviewed fact

## Persistence / browser
- PG
- confirm
- refresh
- relogin
- extra model calls after success

## Safety
- real user data sent: NO
- product DB written: NO
- RAG touched: NO

## Final
- PAID_REPRESENTATIVE_PASS
- PAID_REPRESENTATIVE_FAIL
- PAID_REPRESENTATIVE_STOP_UNKNOWN

## Next
只给一个最小下一动作。
