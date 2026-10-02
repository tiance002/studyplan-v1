# StudyPlan — Codex 10月6日最终交付 Goal（规划思想校正 + 截止期冻结版）

日期：2026-10-03  
目标交付：2026-10-06  
正式工程：`D:\studyplan`  
工作分支：`feat/v2-g1-user-slice`  
固定历史参考：`cf1537040bbf8c52469e00461723f70726f5a3b2`

> 本文件是新的续接执行入口。  
> 与旧指导冲突时：用户最新明确决定 > 本文件 > 既有 CODEX_GUIDANCE / Goal > 更旧文档。  
> 不删除历史文档，不回退代码，不以本文件冒充已经完成验收。

---

# 1. 总目标

10 月 6 日交付一个**真正可供个人使用的学习规划 Agent 成品**。

产品重点不是“生成一张课程表”，而是：

> 根据用户目标与起点，选择连贯的免费资料，
> 组织必要前置、重复复习、有限对比、贯穿实践和源码切片，
> 让初学者知道“为什么学、现在学什么、怎么学、以前学过什么、
> 本次新增什么、如何放进自己的项目”。

必须优先保证完整用户闭环，而不是继续增加架构先进性。

---

# 2. 启动前先核对，不要重复开发

先读取：

1. 最新《StudyPlan 规划算法思想校正版 v1.0》
2. `docs/implementation/CHATGPT_6_PRO_HANDOFF_2026-10-02.md`
3. `docs/implementation/CODEX_GUIDANCE_V2.0.md`
4. `docs/implementation/feature-acceptance.md`
5. `docs/implementation/progress.md`
6. ADR-0011 / 0012 / 0013
7. 当前 DomainPack / planning / resources / practice / workspace 实现
8. 当前 migrations / OpenAPI / frontend tests

核对：

- 实际 HEAD
- working tree
- migration head
- 当前运行服务归属
- 当前可用测试库
- 外部模型/Search累计额度
- 当前三 Blueprint / Seed 实际状态

固定 SHA 只作历史参考：

- **不要 reset**
- **不要 checkout 回固定点**
- **不要从 master 重做**
- **不要覆盖本地新增实现**
- **不要重复已经有可靠 PASS 的业务能力**

---

# 3. 当前阶段最重要的判断

根据当前功能矩阵，大量业务能力已经实现：

- 认证与持久会话
- 生成、草案、业务确认
- 资源搜索和替换
- 阶段总结
- 自动阶段完成
- Practice 变更
- Prompt
- Outcome / Evidence
- 多数历史保护和事务约束

本轮不要再围绕这些模块做架构重写。

截止期前真正关键的是：

1. 校正规划算法输出，使其符合最新学习思想；
2. 完成三 Blueprint 的正式内容；
3. 让跨教程重复/对比和贯穿实践真正进入生成与工作区；
4. 用有限操作完成全路线重规划；
5. 收口正常 Worker / 恢复 UX；
6. 完成真实产品 E2E、构建、重登录、备份恢复和交付说明。

---

# 4. 截止期冻结：必须主动放弃的“理想但过重”实现

以下设计理论上更漂亮，但 10 月 6 日前**禁止实现**。

## 4.1 禁止全自动教程语义去重 / 聚类

不要做：

- 所有章节 embedding
- 全库两两 similarity
- 自动重复率
- 自动覆盖率评分
- LLM 批量判定全部章节是否重复
- 自动删掉重复章节

### 简化方案

只对**受控 Seed 中已审核的少数教程章节**预置关系：

- `review`
- `compare`
- `deepen`
- `version_context`
- `unknown`

生成器读取这些关系即可。

对于临时联网找到的新资料：

- 可以显示为候选
- 不自动做深层重复关系推断
- 用户选择后按普通 Supplement / Reference 使用
- 后续维护者审核再加入公共映射

**学习效果几乎不受影响，但实现复杂度大幅降低。**

---

## 4.2 不新增复杂 Knowledge Exposure 推理引擎

现有 Exposure / KnowledgeNode 保留。

不要再做：

- mastery probability
- 0–100掌握度
- 自动能力诊断模型
- 根据每次行为更新知识概率
- 自动证明“已经学会”

### 简化方案

公共内容只预置：

```text
同一 knowledge stable_key
+ 本次 exposure 目的
+ 与前一次的关系
+ 本次新增关注点
```

例如：

```text
tool_calling
Exposure A：认识 Tool
Exposure B：实现 dispatch
Exposure C：看真实 Runtime
```

用户侧仍然只展示最新已经确定的阶段完成规则，不新增复杂能力分数。

---

## 4.3 不把教材前置 / 项目前置建成新的复杂图

知识前置继续使用现有 DAG。

教材前置与项目实践前置不再各建一套图数据库。

### 简化方案

先放进 Blueprint / Stage 的结构化元数据或现有 JSONB：

```text
knowledge_prerequisites
reading_prerequisites
practice_prerequisites
```

其中：

- knowledge_prerequisites 可映射正式 KnowledgeNode DAG；
- reading/practice 先作为有界字符串/稳定键引用；
- 只用于生成解释和检查；
- 不为它们单独建表。

---

## 4.4 不新增“Practice Thread”新业务实体

已有：

- PracticeProject
- PracticeTask
- task knowledge links
- Practice Change
- Submission / Evidence

已经足够支撑贯穿实践。

### 简化方案

“贯穿实践”是**规划规则**，不是新表。

每阶段任务只需能表达：

- 当前基线
- 本次增量
- 保持不变
- 验证方法
- 后续用途

能复用当前 task goal / requirements / acceptance / metadata 就复用。

只有字段确实无处承载时，才做最小 JSON payload 扩展。

---

## 4.5 不做源码自动理解平台

不要：

- 给 GitHub 仓库建代码知识图谱
- 全仓 AST 图
- 自动源码架构总结服务
- 自动完整 call graph
- 新代码 RAG 平台

### 简化方案

源码学习只是 `CASE_STUDY` 类型资源。

Seed 预置：

```text
repo URL
commit/ref
建议读取文件
建议寻找的调用链
阅读问题
与当前知识点关系
```

实际学习时由已有模型 + GitHub读取能力帮助解释。

核心要求只是：

> 围绕当前知识点读一条真实行为链。

---

## 4.6 不另建“全路线粗规划 / 近期详细规划”两套规划系统

理论上可以做 Progressive Planning Service，
但截止期前没必要。

### 简化方案

继续使用现有完整 Plan Draft。

所有阶段保留：

- title
- objective
- core modules
- primary resource
- practice direction

只给当前阶段/近期阶段额外展开：

- why_now
- previous_relation
- learning_focus
- comparison_focus
- practice_delta

不建第二套数据库、不建长期后台生成器。

---

## 4.7 不做自动实时重规划

用户每问一个问题都自动修改计划，会导致：

- 版本爆炸
- 历史继承复杂
- 用户失去控制

### 简化方案

日常疑问：

```text
解释
小补课
可选对照
继续主线
```

只有：

- 目标变化
- 必修范围变化
- 阶段顺序变化
- Primary Spine 替换
- 主实践方向变化

才创建 Plan Change Proposal。

---

## 4.8 Outcome Profile 不做复杂画像系统

截止期前不做：

- 多维能力雷达
- 自动岗位画像
- 动态招聘市场同步
- 复杂权重评分

### 简化方案

Outcome Profile 首版只需要：

```text
purpose:
  learn
  interview
  portfolio
  internship
  production

required_outputs:
  ...
```

再由 Blueprint 叠加少量要求。

例如 interview 增加：

- 设计解释
- 方案比较
- 失败复盘
- 2分钟表达

这足够影响路线与实践。

---

# 5. 两项外部能力必须降为“非核心增强”，否则 10/6 风险过高

## 5.1 GitHub OAuth / 私有仓库

学习资料和开源项目本身以公共 GitHub 为主。

当前已经有：

- 公共搜索能力
- 手动 GitHub URL
- 公共仓库读取方向

### 10/6 成品建议

必须保证：

- 公共 GitHub 教程发现可用
- 手动粘贴公开仓库 URL 可用
- README / 有界章节检查可用

**GitHub OAuth / 私有仓库接入不应阻塞学习核心闭环。**

若当前已有大部分 OAuth 实现，可低风险补完；
若仍需完整 GitHub App 注册/PKCE/token vault/断开生命周期，
停止扩展，记录为 post-v1 enhancement。

不要为赶工存明文 token 或降低授权安全。

---

## 5.2 独立 RAG Service

当前 F17 仍受外部契约影响。

### 10/6 原则

若到 **10月4日中午** 仍没有明确：

- 实例
- 纯检索 endpoint
- auth/scope
- 无答案语义

则：

- 不猜接口
- 不复制 RAG 工程
- 不重建 embedding/index
- 不让它阻塞 StudyPlan 学习闭环

StudyPlan 核心学习上下文继续使用：

- 当前 Goal
- 当前 Plan
- Summary
- Practice
- Outcome
- 当前已保存资源

独立 RAG 保持可插拔 Port。

**注意：**
如果用户仍坚持 F17 必须作为 10/6 最终验收硬门禁，
则整体 READY 不能在契约缺失时虚报。
但 Codex 不得因为 F17 卡住而停止其它交付。

---

# 6. 规划算法正式采用的最小规则

本轮只实现下面这套，不继续扩展。

## 6.1 目标解析

得到：

```text
target
scope
desired_depth
starting_point
outcome_purpose
constraints
```

不做复杂 Persona。

---

## 6.2 Blueprint 匹配

首批只保证三个高质量 Blueprint：

1. Knowledge / RAG Agent
2. Coding Agent
3. Workflow / Automation Agent

以及 Python 必要前置包。

其它目标：

- 能落到已有 Module 时生成局部路线
- 否则明确“当前公共模板不足”
- 可使用联网候选补洞
- 不假装已经有完整正式 Blueprint

不要为了看起来“万能”批量生成几十个低质量模板。

---

## 6.3 依赖展开

只计算：

- required module closure
- 推荐模块
- optional 模块

并附加少量教材/实践前置提示。

---

## 6.4 Spine 选择

每阶段：

- 至多一个 Primary
- 保持选定章节原作者顺序
- 允许 Supplement / Comparison
- 教程正文必须免费
- 实践 API / 云成本允许，只提示

---

## 6.5 Exposure 编排

同一个 Module 再次出现时，从预置关系读取：

```text
review
compare
deepen
version_context
unknown
```

用户看到的不是“重复了”，而是：

```text
以前学过什么
本次新增什么
应该快速复习还是重点学习
如果比较，要比较哪一个问题
```

---

## 6.6 Practice 编排

每阶段只做：

```text
当前项目基线
-> 本次知识增量
-> 保持原行为
-> 验证
-> 为下一阶段留下可复用成果
```

教程自带小实验：

- 有价值可以做
- 不要求全部并入主项目
- 不要求每次做两遍

---

## 6.7 源码切片

当用户已经具备某个机制基础后：

- 读取真实项目的一条对应调用链
- 不要求看完整仓库
- CASE_STUDY 不自动变必修

---

# 7. 先用 Tool Calling 做纵向验收样例

这是规划思想落地的 acceptance fixture。

## 输入假设

用户：

- Agent 初学者
- 有基础 Python
- 已经在 Hello-Agents 看过 Tool 概念
- 主项目已有最小聊天 Agent
- 想真正理解 Tool Calling

## 正确输出必须包含

### Why now
为什么现在进入 Tool 实现。

### Previous relation
明确指出：

> Tool 概念已经见过，
> 本阶段不是重新定义 Tool，
> 而是学习 Loop / Dispatch / Result。

### New focus
例如：

- tool schema
- model tool request
- dispatch
- observation/result
- error handling

### Comparison
如果安排两份教程：

不是两个链接。

必须有明确问题，例如：

> 两份实现新增第三个 Tool 分别修改哪里？

### Practice delta

```text
当前：
  最小聊天 Agent

本次：
  增加 read_file 和 search_note

保持：
  普通聊天不受影响

验证：
  正常调用
  未知 Tool
  错误参数
  Tool 抛错

后续：
  Permission / RAG / MCP 可继续复用
```

### Source slice
如读取真实 Runtime，只定位：

```text
tool registration
-> dispatch
-> result
-> next model turn
```

---

# 8. 数据实现优先级

## 优先 1：复用现有 JSON / JSONB / DomainPack payload

如果能够保存：

- exposure purpose
- previous relation
- focus
- comparison prompt
- practice delta
- source slice

就不要新增 migration。

## 优先 2：最小 DTO 扩展

如果 UI / API 需要字段，
优先做可选字段向后兼容。

## 优先 3：最后才 migration

只有当：

> 不加结构就会导致核心学习语义在发布/刷新后丢失

才允许新增迁移。

本轮目标不是“数据库模型最优雅”。

---

# 9. 前端截止期策略

不要大改现有 UI。

当前浅色风格、阶段折叠、资料浮窗、学习路径继续保留。

只需要在当前学习阶段增加一个轻量“学习指导”区域，能表达：

- 为什么现在学
- 已经见过什么
- 本次重点
- 对比问题（如果有）
- 本次实践增量
- 源码阅读入口（如果有）

可折叠。

不要新做：

- 知识图可视化
- 雷达图
- 复杂时间轴
- 拖拽路线编辑器
- 新设计系统

---

# 10. 全路线重规划：截止期版

不要做任意语义历史合并。

首版只支持有限操作：

```text
change_goal
add_topic
remove_optional_topic
reorder_future_stage
replace_primary_resource
change_practice_direction
regenerate_future_plan
```

流程：

```text
用户请求
-> 映射有限操作
-> 生成新草案
-> 展示差异
-> 用户确认
-> 新 PlanVersion
```

历史：

- 旧 Plan 永久保留
- 旧 Summary / Prompt / Outcome / Evidence 可读
- 新阶段完成不自动继承旧阶段 accepted
- 可以引用旧成果作为历史资料
- 不做复杂 completion 自动迁移

这是故意的简化。

---

# 11. 10月3日至10月6日关键路径

## 10月3日 — Freeze + Vertical Slice

必须完成：

1. 核对实际 HEAD / tests / migration
2. 把最新规划思想落成 ADR / guidance delta
3. 做 Tool Calling fixture
4. 确认字段承载方式
5. 让生成结果能表达：
   - why
   - previous relation
   - focus
   - comparison
   - practice delta
6. 当前学习工作区能显示这些信息
7. 定向 unit / contract / frontend PASS

**当天禁止批量扩内容。**

---

## 10月4日 — 三 Blueprint + 核心闭环

完成：

1. Knowledge/RAG Blueprint
2. Coding Agent Blueprint
3. Workflow/Automation Blueprint
4. Python 前置
5. 免费教程正文审核记录
6. 贯穿实践任务
7. Outcome purpose 简化接入
8. 真实生成一个普通用户计划
9. 草案编辑/确认/刷新
10. 公共 GitHub 资料发现链收口

中午做 F17 判定：

- 契约明确 → 做最小只读适配
- 契约仍缺 → 停止阻塞主线

---

## 10月5日 — 修改/恢复/完整验收

完成：

1. 有限全路线重规划
2. 历史保全
3. Worker正常启动/停止/恢复说明
4. cancel / failed / unknown / reload 用户体验
5. 正常账号真实 PG
6. 浏览器完整学习闭环
7. 跨账号/跨项目拒绝
8. production build
9. 独立备份恢复演练
10. 使用说明

当天结束后：

> **Feature Freeze**

不再增加业务能力。

---

## 10月6日 — Release Candidate

只允许：

- 修复 P0/P1 bug
- 补失败门禁
- 修复文档/启动脚本
- 最终回归
- 最终浏览器人工验收
- 备份恢复复核
- release/checkpoint

禁止：

- 新 framework
- 新 data model
- 新 Blueprint
- 新搜索源
- 新 UI 大改
- 架构重构

---

# 12. 10月6日“最终成品”门禁

核心成品必须实际证明：

## 用户入口
- 注册 / 登录 / 退出 / 重登录
- 创建或进入学习项目

## 规划
- 输入目标
- 必要澄清
- 生成完整阶段路线
- 看出前置关系
- 看见学习指导
- 草案编辑
- 明确确认

## 内容
- 三个正式 Blueprint
- Python 前置
- 免费学习资料
- Primary / Supplement / Comparison
- 重复知识的 review / compare / deepen 表达
- 贯穿实践

## 学习
- 阶段导航
- 学习资料
- 总结
- Practice
- Prompt
- Outcome
- 自动阶段状态

## 调整
- 资料替换
- Practice 变更
- 有限全路线重规划
- 历史不丢

## 稳定
- 持久任务
- 刷新/断连恢复
- cancel / fail / unknown 有明确 UI
- build
- 启动文档
- 备份恢复
- 跨账号隔离

任何一项没有真实验证：

- 写 NOT RUN
- 不用 Fake 冒充
- 不用单元测试冒充浏览器
- 不用 healthz 冒充集成

---

# 13. 模型与子代理临时授权

直到用户明确说“恢复原计划”：

- 6luna：所有实际可用档位
- 6.1sol：除 max 外所有实际可用档位
- 6astra：low / medium / high

目标是减少实际交付时间。

建议：

- 架构/契约/高耦合修改：
  - 6.1sol high/xhigh
  - 或 6astra high
- 独立 reviewer / contract / failure case：
  - 6astra medium/high
- fixture / 明确实现 / 回归：
  - 6luna 合适档位
  - 或 6.1sol medium

不要求低档失败后才能升级。

保留：

- 最多 3 个活动子代理
- 最多 2 个业务代码写者
- DTO / migration / transaction 单一负责人

不要建立固定角色配置。

---

# 14. 每个切片的输出格式

每批先回答：

## 用户现在新增能做什么

然后报告：

- Goal
- Changed files
- Actual SHA
- Tests
  - PASS
  - FAIL
  - NOT RUN
- Real PG
- Browser
- External Provider/Search usage
- Migration
- Risks
- Rollback
- Remaining blocker
- Next safe action

不要用：

- “大概完成”
- “预计通过”
- “AI认为正确”
- 测试数量推算百分比

---

# 15. 停止条件

出现以下情况立即停相关分支，不扩大实现：

1. 需要猜外部 API 契约
2. 需要重写已发布 migration
3. 需要破坏历史数据
4. 需要自动迁移旧完成状态
5. 需要新建大型框架才能继续
6. 某一小功能预计吞掉一天以上且存在低影响替代方案
7. 新设计没有直接改善“用户怎么学”

遇到第6类问题，先提出：

```text
原方案
实现成本
真正学习收益
简单替代
效果损失
```

优先选效果损失小的简单替代。

---

# 16. 现在开始

执行顺序：

1. N0：核对最新本机状态
2. P0：最新规划思想与当前实现差异审计
3. P1：Tool Calling 纵向 fixture
4. P2：最小生成契约
5. P3：工作区展示
6. P4：定向真实链验收
7. 三 Blueprint 内容接入
8. 有限重规划
9. 最终稳定/恢复/交付

不要再生成另一份大而全规划后等待。

从 N0/P0 开始，发现可复用实现立即复用。

**目标不是把设计做得最完整，而是在 10 月 6 日前交付一个学习体验正确、数据安全、真实可运行、以后还能继续扩展的成品。**
