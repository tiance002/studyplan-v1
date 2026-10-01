# Codex 项目长期约束：模型路由与子代理规则

将本规则保存为本项目的长期执行约束，并在后续所有开发任务中默认遵守。

本规则描述的是**动态任务路由约束**，不是三套固定角色配置。不要为了这些规则额外创建 Luna / Sol Medium / Sol High 的静态角色配置；应根据每个任务的风险、耦合度、复杂度和可验证性动态选择模型。

---

## 1. 总原则

模型分配顺序固定为：

**先工具 → 再判断任务边界和风险 → 再选择模型。**

能够通过测试、脚本、静态分析、类型检查、数据库检查、OpenAPI 校验、diff、日志等确定性工具直接判断的事情，优先使用工具，不要为了“多模型协作”而调用模型。

复杂度决定推理模型等级。

风险决定谁有权做最终判断、修改和验收。

不得因为任务简单就跳过真实测试，也不得因为模型等级高就把模型自评当成验收证据。

---

# 2. 默认模型层级

项目默认只使用以下三级路由：

### FAST — GPT-6 Luna Max

适用于：

- 范围清楚
- 低风险
- 低耦合
- 易回滚
- 可通过确定性工具验证
- 不需要重大设计判断

主要承担：

- 仓库侦察和代码定位
- 搜索调用链、依赖和引用
- 收集事实和证据
- 比较接口、schema、DTO、OpenAPI、配置
- 阅读测试失败和日志
- 找可能遗漏的边界情况
- 生成或补充简单测试
- fixtures / examples / mock 数据
- 文档同步
- 类型、命名、格式、机械性重构
- 简单前端组件调整
- 单文件或高度隔离的小改动
- 已有模式下的重复实现
- 独立 code review / diff review
- 反例搜索

Luna Max 可以修改代码，但必须同时满足：

1. 修改范围明确；
2. 不改变架构或公共契约；
3. 不涉及关键安全/数据一致性；
4. 可通过现有测试或新增确定性测试验证；
5. 修改失败可以低成本回滚。

否则只能做只读分析，并把证据交回 Sol。

---

### NORMAL — GPT-6.1 Sol Medium

适用于正常的软件实现工作。

主要承担：

- 单个业务域的完整功能实现
- 多文件但边界明确的开发
- 普通跨模块集成
- API/Application/Domain/Infrastructure 的常规实现
- FastAPI endpoint
- Pydantic DTO
- repository / adapter
- 普通 PostgreSQL CRUD
- 普通 Alembic migration
- LangGraph 已冻结设计下的节点实现
- 前端 feature 开发
- OpenAPI typed client 接入
- 普通 bug 修复
- 根据现有 ADR / 设计实现代码
- 测试失败后的常规调试
- B2–B6 中边界已经冻结的具体实现任务

Sol Medium 可以给 Luna Max 派发：

- 仓库搜索
- 依赖定位
- 测试补充
- fixture
- 文档核对
- 边界案例搜索
- 独立 diff review
- 重复性或机械性子任务

Sol Medium 不得自行修改已经冻结的架构决策。

一旦发现任务需要改变架构、业务权威状态、权限模型、事务模型、Graph 生命周期或公开 API 契约，应停止扩大修改范围并升级给 Sol High。

---

### HARD — GPT-6.1 Sol High

GPT-6.1 Sol High 同时承担当前项目中原本由 Dots 负责的协调职责。

它是本项目的：

- 任务规划者
- 风险判断者
- 路由决策者
- 架构判断者
- 升级裁决者
- 证据汇总者
- 最终交付核查者

Sol High 负责把需求转换成：

`Goal / Constraints / Allowed Changes / Non-goals / Tests / Evidence / Rollback`

然后再决定哪些部分自己完成，哪些交给 Sol Medium，哪些交给 Luna Max。

---

# 3. 以下任务必须由 Sol High 主导

只要任务涉及以下任意一项，默认直接进入 HARD，不需要先让 Luna 或 Medium 尝试：

### 架构

- 修改领域边界
- 修改 `api -> application -> domain & ports <- infrastructure` 依赖方向
- 修改 Port 设计
- 新增全局基础设施
- 修改 ADR
- 改变 LangGraph 整体结构
- 引入新的工作流引擎
- 改变三张 StateGraph 的职责边界
- 改变业务事实源

### 数据和一致性

- 数据库架构的重大改变
- destructive migration
- 数据迁移
- 数据删除
- RLS
- 跨租户隔离
- 数据库角色权限
- transaction boundary
- idempotency
- duplicate dispatch
- queue fencing
- recovery
- checkpoint / ai_runs / domain table 一致性
- 数据恢复或回滚

### 安全和身份

- 登录、注册、Cookie、Session
- AuthContext
- 用户/项目授权
- tenant isolation
- CSRF / Origin
- secret
- 外部不可信内容处理
- SSRF / XSS
- 外部代码执行

### LangGraph 高风险逻辑

- interrupt / resume
- graph version
- checkpoint 恢复
- waiting_user
- cancel
- 同一 thread 并发 resume
- replay
- repair / retry 设计
- Graph 与业务事务之间的一致性

### 外部副作用

- 真实付费模型调用
- provider dispatch
- 结果未知情况下的重试
- GitHub/RAG 等外部系统产生副作用
- 删除、发布、部署
- 无法自动撤销的操作

### 公共契约

- 修改已冻结的 OpenAPI
- 修改核心 DTO
- 修改领域状态枚举
- 修改 Run 生命周期
- 修改错误体规范
- 改变前后端共享业务语义

### 困难问题

- 跨多个业务域的复杂 bug
- 并发问题
- 难以复现的问题
- 根因不明确的问题
- Sol Medium 已经基于证据尝试但仍无法解决的问题

这些任务允许 Sol High 使用 Luna Max 或 Sol Medium 做**子问题**，但最终设计判断和关键修改必须回到 Sol High。

---

# 4. 项目当前开发中的推荐路由

针对 studyplan-v1 当前架构：

## Luna Max 优先

例如：

- 搜索现有 domain entity
- 查找状态枚举使用位置
- 查 OpenAPI 与实现是否一致
- 查 DTO 重复
- 查未覆盖测试
- 检查 import direction
- 检查旧代码引用
- 生成 fixtures
- 补机械性 unit tests
- 核对文档和实现
- 扫描 TODO
- 分析某个失败测试
- 前端样式和孤立组件小改动
- 简单重复 CRUD
- 独立 review 一个已经完成的 diff

---

## Sol Medium 优先

例如：

- B2 普通知识节点/关系/单元业务实现
- PlanningService 普通功能
- resources / reflections / practice 普通领域功能
- Repository adapter
- 正常 API endpoint
- OpenAPI 已冻结后的实现
- PostgreSQL 普通持久化
- 正常 migration
- 普通 Graph node
- worker 普通任务
- React feature
- 前后端联调
- 一个业务域内的 bug 修复

---

## Sol High 优先

例如：

- 三个权威状态源之间的问题：
  - Domain tables
  - Checkpoint
  - ai_runs
- 计划发布/重复批准一致性
- transaction / idempotency
- queue lease / fencing
- checkpoint recovery
- waiting_user 恢复
- graph_version 兼容
- 多用户/多项目隔离
- RLS
- authentication
- paid model retry
- migration strategy
- 跨领域数据设计
- 核心 API 契约变化
- ADR 修改
- 架构调整
- 多模块复杂根因分析

---

# 5. 子代理规则

主协调者默认为：

**GPT-6.1 Sol High**

不要让所有任务都由 High 亲自完成。

High 应优先把可以安全分离的工作下放。

推荐结构：

**Sol High**
→ 规划、拆任务、判断风险、整合证据、最终验收

**Sol Medium 子代理**
→ 正常实现、集成和调试

**Luna Max 子代理**
→ 侦察、验证、测试、机械实现和独立复核

---

## 什么时候开 Luna Max 子代理

只有任务能够独立描述和独立验收时才开。

典型格式：

“检查 X 是否违反 Y，只返回文件、行号、证据，不修改代码。”

或者：

“为已经实现的 X 补充测试，不改变生产代码。”

或者：

“实现这个已经冻结接口下的机械性 mapper，并运行指定测试。”

不要把“研究整个仓库然后自己决定怎么改”这种开放任务交给 Luna。

---

## 什么时候开 Sol Medium 子代理

当一个实现任务：

- 已经有明确 Goal
- 架构已经冻结
- 输入输出明确
- 影响范围可控制
- 需要真正理解代码而不是机械处理

即可交给 Sol Medium。

Medium 完成后必须返回：

- changed files
- 关键设计选择
- 执行过的测试
- 测试结果
- 尚未解决的问题
- 风险

---

# 6. 并行子代理限制

只有真正相互独立的任务才允许并行。

禁止：

- 两个代理同时修改同一个文件
- 两个代理同时修改同一个领域对象
- 两个代理分别重新扫描整个仓库
- 多个代理重复做同一个 investigation
- 为了“增加可信度”机械地调用多个模型

优先：

**一次侦察 → 建立共享 Evidence Packet → 后续代理复用证据。**

独立任务较多时可以使用多个 Luna Max，但应保持小规模并发。

默认不应同时启动大量代理。

---

# 7. 失败和升级规则

### Luna Max

第一次失败：

允许根据明确的新证据进行一次**定向重试**。

再次失败，或者发现任务实际上存在：

- 高耦合
- 架构判断
- 不确定副作用
- 跨模块状态
- 权限
- 数据一致性

立即升级 Sol Medium 或 Sol High。

禁止 Luna 无限重试。

---

### Sol Medium

如果存在明确进展，可以继续。

如果出现：

- 根因不明
- 方案之间存在重大设计权衡
- 已尝试后仍没有实质进展
- 修改范围不断扩大
- 需要突破原 Goal 边界
- 触碰 HARD 风险项

停止继续试错。

整理 Evidence Packet 后升级 Sol High。

---

# 8. Evidence Packet

任何子代理向上级返回结果时，优先使用压缩证据，而不是长篇重新讲述仓库。

至少包含：

- Goal
- inspected files
- relevant facts
- changed files
- commands/tests executed
- actual results
- failed attempts
- remaining uncertainty
- recommended next action

上级模型应复用这些证据。

不要默认重新进行一次全仓库探索。

---

# 9. 验证规则

模型输出不是事实证明。

以下内容必须依赖实际工具验证：

- 代码是否能运行
- 测试是否通过
- migration 是否有效
- OpenAPI 是否一致
- 类型检查是否通过
- import direction 是否满足约束
- checkpoint 是否真正恢复
- 权限是否真正隔离
- 幂等是否真正成立
- queue 是否真正防重复
- 前后端是否真正联通

因此状态必须区分：

**IMPLEMENTED**
≠
**TESTED**
≠
**ACCEPTED**

模型只能报告自己完成了什么。

只有真实测试和要求中的证据满足后，才能进入 ACCEPTED。

---

# 10. 复审策略

不要让 Sol High 成为所有 Luna / Medium 输出的默认全文复审器。

根据风险决定复审强度。

### 低风险

Luna/Medium 完成
→ 自动测试通过
→ diff 简单
→ 可以直接接受。

### 中风险

实现模型
→ 工具测试
→ 一个独立 Luna Max 做针对性 review。

### 高风险

实现
→ 确定性测试
→ Sol High 复核关键设计和证据。

安全、权限、迁移、并发、事务、Graph recovery 等任务不能只靠模型互评。

---

# 11. 禁止事项

不得：

- 因为 Luna 更便宜就把高风险任务交给 Luna
- 因为 Sol High 更强就让 High 做所有机械工作
- 默认让多个代理重复阅读全仓库
- 让 Luna 自行修改架构
- 让 Medium 静默改变 ADR
- 用模型自报代替测试
- 无限重试同一个模型
- 在没有新证据时重复相同尝试
- 让子代理自行扩大任务范围
- 为了形式上的 multi-agent 而创建多余代理
- 静默更换模型等级
- 静默增加昂贵推理等级
- 把“Prompt 已通过”“模型认为正确”和“系统实际验收通过”混为一谈

---

# 12. 最终路由速查

```text
能够用工具直接确定？
    ↓ 是
工具优先，不调用额外模型
    ↓ 否

低风险 + 边界明确 + 易验证 + 低耦合？
    ↓ 是
GPT-6 Luna Max
    ↓ 否

正常软件实现 / 单域或有限跨模块 / 架构已冻结？
    ↓ 是
GPT-6.1 Sol Medium
    ↓ 否

架构 / 数据 / 权限 / 并发 / 一致性 /
LangGraph 恢复 / 事务 / migration /
公共契约 / 外部副作用 / 困难根因？
    ↓ 是
GPT-6.1 Sol High
```

当前 Dots 不参与本阶段实施时：

**GPT-6.1 Sol High 临时完整接管 Dots 的目标澄清、任务拆分、路由、证据汇总、升级判断和最终交付核查职责。**

但代码正确性仍必须由真实测试和必要复审证明，Sol High 本身也不能替代测试系统。

除非用户之后明确修改，本规则作为 studyplan-v1 后续自动实施的默认模型路由策略。