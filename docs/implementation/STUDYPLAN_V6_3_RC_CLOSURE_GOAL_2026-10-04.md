# Codex Goal — StudyPlan v6.3 Release Candidate 收口与正式入口准备

日期：2026-10-04  
目标截止：2026-10-06  
正式工程：`D:\studyplan`

## 0. 本轮定位

v6.2 的“章节内容 + 开放规划语义”门禁已经 READY。

本轮禁止继续扩课程、扩 Recipe、扩项目卡。
目标从“继续开发功能”切换为：

> **Release Candidate 收口：验证真实产品入口是否能安全承载已经完成的能力，并把剩余 blocker 分成“必须修”“可明确延期”“外部契约阻塞”。**

整体产品当前仍是 `NOT_READY`，本轮不得提前改为 READY。

---

# 1. 开始前 N0：只读事实核对

在：

```powershell
cd D:\studyplan
```

执行：

```powershell
git status
git branch --show-current
git rev-parse HEAD
git log -8 --oneline
```

已知上批报告：

- branch: `feat/n1-resource-discovery`
- 用户报告当前 HEAD: `161bacd5fa3e88c566b806697ebe52ef34cb6456`
- v6.2 主体实现曾记录：
  - Agent v5
  - AI Fullstack v2
  - Cloud v2
- 产品库上批只读时仍为 migration 0023
- repo migration head 沿用 0024
- v6.2 新内容未写原产品库

以上只用于核对；**实际本机当前值优先。**

禁止：

- reset
- force checkout
- rewrite history
- merge master/develop
- 清理未知目录
- 因为文档 SHA 与实际不同而回退

本机当前代码是事实源。

---

# 2. 本轮四个主目标

按顺序执行：

## RC-A：正式入口与真实产品环境只读预检
## RC-B：真实产品数据的“隔离恢复 + 升级演练”
## RC-C：宽回归 FAIL 的 release-blocker 分类
## RC-D：RAG/外部服务契约只读核对 + 用户体验准备

在完成 RC-A~D 前：

**不要写原产品数据库，不要部署新正式入口，不要调用真实收费模型。**

---

# 3. RC-A — 正式入口只读配置核对

目标：回答“如果现在把 v6.2 接入日常入口，具体会发生什么”。

只读核对：

1. 当前正常前端入口实际端口/进程/启动命令
2. 当前正常 API 实际端口/进程/启动命令
3. 当前 Worker 是否启动
4. 当前正常 `.env` 所指产品库
5. 产品库 migration revision
6. repo migration head
7. 当前产品库已有：
   - domain packs
   - current pack registry / bootstrap selection
   - actor / learning projects
   - approved plans
   - summaries
   - prompt revisions
   - practice/outcomes
8. 当前启动入口使用的是：
   - 旧代码
   - 当前 feature HEAD
   - 还是验收 wrapper

不得打印：

- 密码
- API key
- session
- 私有原文
- DSN 凭据

输出：

`docs/reviews/2026-10-04-v6-3-formal-entry-preflight.md`

必须给明确结论：

```text
SAFE_TO_STAGE
或
BLOCKED_FOR_STAGING
```

这里只表示“可以进入隔离演练”，不是允许写产品库。

---

# 4. RC-B — 用真实产品数据备份做隔离恢复 + 升级演练

这是本轮最高优先级。

## 4.1 先做只读原生备份

对**当前真实产品数据库**做完整原生备份。

要求：

- 不改变源数据库
- 记录数据库 schema revision
- 记录表数量
- 记录 RLS/policies/ACL 元数据摘要
- 私有数据不得写入 Git
- 备份放 ignored/受控本地目录
- 不输出用户原文

## 4.2 恢复到新的隔离数据库

创建全新 owned 临时库。

先验证：

```text
恢复前产品库
→ 原生 backup
→ 新隔离库
```

恢复后核对：

- 表数量
- migration revision
- ACL
- RLS
- policies
- actor/project 归属
- approved plan
- summary/prompt/history/outcomes 数量摘要
- 不读取/输出私有正文

## 4.3 只在恢复副本上执行当前 repo 的 forward migration

如果当前实际仍是 0023、repo 是 0024：

只在隔离副本升级到 0024。

如果实际值不同：

按真实 revision 计算升级路径，不能硬编码 0023/0024。

然后：

- 使用当前 feature HEAD 启动 API
- 使用当前正式前端 build/dev entry
- Worker 先默认不启动
- 不调用真实模型
- 不恢复旧 unknown
- 不重派历史 Run

## 4.4 在恢复副本上发布/导入 v6.2 新 Pack

仅在隔离库：

- AI Fullstack 当前下一合法版本
- Agent 当前下一合法版本
- Cloud 当前下一合法版本

必须走正式 Seed/import/immutable 规则，不允许 SQL 手写绕过。

验证：

- 旧 Pack 仍可读
- 旧 Plan snapshot 不变化
- 新生成才选新 Pack
- hold 项未发布
- 用户已有历史仍可读
- 新 Pack 章节级 guidance/extensions/practice 可消费

## 4.5 恢复副本的普通账号只读体验

使用真实产品数据的**副本**，不是 synthetic owned fixture，完成：

- 正常登录
- 项目列表/当前学习空间
- 历史计划
- 历史总结
- Prompt 历史
- Practice/Outcome 历史
- 当前资源/Extension
- 页面刷新/重登录

不得：

- 替用户批准新计划
- 写用户成果
- 修改其历史
- 调真实模型

如果需要验证写路径：

使用隔离副本中新建的合成账号，不使用真实用户账号写入。

---

# 5. RC-C — 宽回归 FAIL 的 release blocker 分类

v6.2 报告显示：

```text
当前更宽 Auth/RLS/旧 schema 组合：
PASS 51 / FAIL 10
且与 N0 原基线失败集合相同
```

不要简单忽略，也不要把它们全部修掉。

逐项建立：

`docs/reviews/2026-10-04-v6-3-baseline-failure-triage.md`

每个失败只能归一类：

### A. RELEASE_BLOCKER
会影响：
- 正常启动
- 正常升级
- 数据读取
- RLS/隔离
- 正常备份恢复
- 用户主链

→ 本轮必须修。

### B. STALE_TEST_OR_FIXTURE
实现已变、测试假设过时，且当前真实契约有其它证据。

→ 修测试/fixture，不能改业务去迎合旧错误假设。

### C. UNSUPPORTED_DOWNGRADE_ONLY
只发生在历史 published migration 的 destructive downgrade，
正常 forward upgrade + backup restore 不依赖它。

→ 不在 deadline 前为“全绿”修改已发布 migration。
记录：
`forward-only migration; rollback by backup restore / code revert`

### D. OUT_OF_SCOPE_LEGACY
不影响当前正式入口且已有替代契约。

→ 明确保留。

硬规则：

- 不允许把“基线也失败”当成自动免责。
- 不允许为了把 FAIL 变 PASS 放宽 RLS、publication、immutable Seed、证据等级或历史保护。
- 不允许修改已发布 migration 伪造 downgrade 通过。

完成分类后，只修 A 和确定性的 B。

---

# 6. RC-D1 — RAG 契约只读核对

当前历史事实：

- 已发现独立 RAG 项目/服务
- OpenAPI/health 可访问
- 但 StudyPlan 所需“独立检索 + scope/授权”契约不完整
- F17 仍 BLOCKED

本轮只读重新核对当前实际状态，不沿用旧结论。

优先检查：

1. 用户常用的 RAG 实例是哪一个
   - 若从现有本机配置/服务证据无法唯一判断，报告“需要用户指定”，不要猜
2. 当前 OpenAPI 是否新增：
   - 纯检索 endpoint
   - knowledge scope / dataset scope
   - caller/user/tenant scope
   - auth/security scheme
   - source/citation response contract
3. 是否可以做到：
   - StudyPlan 只传受控 query + scope
   - 不向 RAG 发送 StudyPlan 用户模型密钥
   - 不让 StudyPlan 绕过 RAG 自己的权限
   - 不触发生成模型，只做 retrieval

输出：

`docs/reviews/2026-10-04-v6-3-rag-contract-status.md`

结论只能是：

```text
READY_FOR_THIN_INTEGRATION
或
BLOCKED_CONTRACT_MISSING
或
NEEDS_USER_INSTANCE_SELECTION
```

若 `BLOCKED_CONTRACT_MISSING`：

只写最小 contract proposal：

```text
request
response
scope
auth
error
timeout
citation/source identity
```

**不要在 StudyPlan 内重建 RAG，不要偷偷修改 RAG 项目。**

---

# 7. RC-D2 — 受许可真实服务代表路径

本轮不要批量验证所有外部服务。

先列当前产品真正需要的真实服务：

- 实际 planning model provider
- GitHub public search / connector（如果正式路线需要）
- RAG（仅合同 READY 时）

## 7.1 免费/无费用路径优先

可先验证：

- 公共 GitHub/文档只读
- provider health/list model（如果不收费且现有契约允许）
- RAG health/OpenAPI

## 7.2 真实收费模型

本轮**不要自动调用**。

先生成：

`docs/reviews/2026-10-04-v6-3-paid-representative-plan.md`

写清：

- 需要几次
- 为什么 Fake/历史证据不能替代
- 预期验证什么
- 最大 token/request
- 用哪个合成账号
- 不会发送哪些真实私人数据

然后 STOP，等待用户明确批准收费代表验证。

---

# 8. 正式入口 staging 方案

基于 RC-A/B，准备：

`docs/reviews/2026-10-04-v6-3-staging-plan.md`

必须包含：

```text
当前正式入口
→ backup
→ migration
→ seed packs
→ current feature build
→ worker
→ smoke
→ rollback
```

但本轮默认只做到“方案 + 隔离副本演练”。

**未经用户明确批准，不写原产品数据库、不切换日常入口。**

---

# 9. 用户实际体验准备

准备一个最小的“用户体验清单”，不要替用户执行。

目标用户使用自己的正常账号后只需检查：

1. 登录
2. 创建/选择学习空间
3. 输入一个真实学习目标
4. 查看草案：
   - 为什么学
   - 章节
   - 实践
   - 项目卡
5. 检查自己的项目是否优先
6. 检查 Recipe 是否合理组合
7. 确认路线
8. 打开阶段学习
9. 复制 Project Study Prompt
10. 保存一次阶段总结或实践草稿
11. 刷新/重新登录
12. 查看历史仍存在

准备：

`docs/acceptance/USER_ACCEPTANCE_CHECKLIST_2026-10-04.md`

只写用户可观察行为。

不要要求用户检查：
- DB
- RLS
- migration
- worker internals

---

# 10. 宽回归与发布门禁

在本轮代码改动（如果有）结束后：

必须：

- unit/contract
- targeted PG
- Auth/RLS
- frontend tests
- build
- Chrome smoke
- checkpoint recovery（仅若相关代码改变）
- restore-consumer on real-data restored copy

不得用：

- 单元测试代替 PG
- Fake 代替收费模型代表验证
- synthetic DB restore 代替真实产品数据副本 restore
- 基线失败复现代替 release-blocker 分类

---

# 11. 截止日前的简化规则

如果某剩余项需要：

- 新数据库体系
- 重做 RAG
- 大规模 migration 重写
- 新队列/worker
- 新框架
- 大规模 UI 重构
- 自动课程分析

立即停止并标：

```text
DEFER_AFTER_RC
```

10 月 4–5 日只修：

- 正式入口 blocker
- 数据安全 blocker
- 用户主链 blocker
- release regression blocker

---

# 12. 本轮允许的代码改动

只有在 RC 审计证明需要时：

### 允许
- 启动/配置薄接线
- registry/bootstrap 修正
- 稳定入口配置
- stale fixture/test 修复
- release blocker 的最小代码修复
- docs/runbook
- safe backup/restore scripts

### 默认禁止
- 新产品功能
- 新数据模型
- 新课程
- 新 Recipe
- 新 Agent framework
- 新 RAG implementation

---

# 13. 提交与回滚

建议最多 3 个本地提交：

## Commit RC1
只读审计、release triage、staging/runbook

## Commit RC2
仅真实 release blocker 的最小修复

## Commit RC3
隔离真实数据恢复/升级验证与最终报告

不要推 master/develop。
是否 push 当前 feature branch 等用户后续指令。

---

# 14. 本轮 STOP 门

完成以下内容后停止并向用户报告，不自动进入产品写入：

- RC-A 正式入口 preflight
- RC-B 真实产品数据副本 restore + upgrade + new packs + readback
- RC-C 宽 FAIL 分类及必要修复
- RC-D RAG 契约状态
- staging plan
- paid representative plan
- user acceptance checklist

此时报告：

```text
STAGING_READY
或
STAGING_BLOCKED
```

这是下一决策点。

不要自动：

- 升级原产品数据库
- 切正式入口
- 跑收费模型
- 批准用户计划
- 使用用户私有内容做外部验证

---

# 15. 最终报告格式

输出：

## Baseline
- branch
- HEAD
- working tree
- current product DB revision
- repo migration head
- current product pack versions

## Formal entry
- current entry
- current API
- worker
- STAGING_READY/BLOCKED

## Real-data isolated restore
- backup PASS/FAIL
- restore PASS/FAIL
- migration-on-copy PASS/FAIL
- new pack import-on-copy PASS/FAIL
- old history readback PASS/FAIL
- model calls = 0

## Baseline FAIL triage
- A RELEASE_BLOCKER count
- B STALE_FIXTURE count
- C DOWNGRADE_ONLY count
- D LEGACY count
- fixed items

## RAG
- READY_FOR_THIN_INTEGRATION / BLOCKED_CONTRACT_MISSING / NEEDS_USER_INSTANCE_SELECTION
- exact missing fields

## External services
- free checks
- paid representative plan
- paid calls actually executed

## Tests
- unit
- PG
- Chrome
- frontend/build
- restore consumer

## Remaining blockers
- list

## Next gated action
只能给一个最小下一动作。

现在开始 RC-A。
