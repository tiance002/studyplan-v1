# Planning V2 Item 1 — Project Context Reference Fix

日期：2026-10-08。范围：Case 7 的 source_ref Prompt 纠正及最小离线验证。

状态：**ITEM1_PROJECT_CONTEXT_FIX_READY / ITEM1_REAL_ACCEPTANCE_PENDING / ITEM2_NOT_STARTED / STOP**。

## 1. 基线与修改范围

- Start HEAD：`d16c136432280c9c214a067ced812d8219ac2fb1`；branch：`feat/n1-resource-discovery`，均与用户指定一致。
- 开始时 tracked tree 干净；原未跟踪 `.workbuddy/`、`design-preview/` 未操作、不提交。
- Final HEAD：本报告所属的本地提交，消息 `fix(planning): clarify project context source reference`；精确 SHA 随最终答复及 ignored `var/planning-v2-item1-project-ref-fix-20261008/final.json` 保存。不 push、merge、deploy。
- 上位 [Architecture Contract](PLANNING_V2_ARCHITECTURE_CONTRACT.md) 保持原文，无需架构合同变更。

修改文件仅以下四项：

1. `backend/app/infrastructure/providers/goal_requirement_contract.py`：Item 1 专用 SYSTEM Prompt 来源说明。
2. `backend/tests/unit/test_goal_requirement_project_context_refs.py`：五项最小测试。
3. 本报告。
4. `docs/implementation/progress.md`：前置本轮状态，保留旧进度全文。

Schema、Validator、GoalSpec、SHAPE、ID/hash、Analyzer、HTTP transport、Worker、Run、数据库、migration、UI、公开 API 均未修改。未引入 source_ref 别名、规则分类器或产品第二模型审核器。

## 2. 根因与 Prompt 差异

[上一轮真实复测](ITEM1_REAL_SEMANTIC_RETEST.md) 中 Case 7 收到明确模型响应，但三处使用 `goal.project_context`，严格 Validator 返回 `goal_requirement_profile_invalid / source_refs`。实际失败的直接原因是输出使用了未获准引用。原 Prompt 写作 `project_context（指goal.project_context）`，同时出现规范引用与物理输入路径，构成可定位的歧义和可能诱因；尚无新的真实响应证明修订后的模型行为。

原文：

```text
project_context（指goal.project_context）。不得发明来源。
```

改为：

```text
project_context。已有项目背景的合法source_ref是project_context；goal.project_context是非法source_ref，禁止输出。
例如用户要求基于已有项目继续实践，相关requirement可写为
{"text":"基于已有项目继续实践","source_refs":["project_context"],"origin":"explicit","rationale":""}。
不得发明来源。
```

仅替换该来源说明并添加最小示例。`goal.target`、`goal.scope` 及实际有效下标、`goal.starting_point`、`goal.outcome_purpose`、`goal.desired_depth`、`goal.constraints` 及实际有效下标保持现有规则：只有本次实际提供且非空的来源可引用。示例不授权无已有项目背景时编造该要求。

专用模块除 `GOAL_REQUIREMENT_SYSTEM` 外 AST 与基线完全相同；diff 确认其他 Prompt 句子保持。此前自然语言硬约束提取、结构化限制原文保护、能力声明/用途区分、澄清规则未被覆盖。

## 3. RED / GREEN 与受影响回归

新测试先加入、Prompt 后修改；保留首次失败输出。

| 验证 | 结果 | 能证明的事实 |
|---|---|---|
| 新最小测试，原 Prompt | 1 FAIL / 4 PASS，预期 RED | 实际 MockTransport 请求中的 system 缺少规范引用指导；Validator 原已拒绝错误拼写并接受合法拼写 |
| 新最小测试，修复后 | 5 PASS | 指令及示例进入真实适配器请求构造；requirement/constraint 错误前缀被拒绝，合法引用通过、项目原文与 hash 保持 |
| 合并受影响回归 | 33 PASS | 新 5 + 既有硬约束 12 + GoalSpec/project input 9 + Provider 专用 Prompt 隔离 1 + 公开生成/身份范围/组合根门禁 6 |
| Ruff（两个代码文件） | PASS | 有界静态检查 |
| `git diff --check` | PASS | 差异格式检查 |
| 非 SYSTEM AST / 受保护文件 hash | PASS | 未改确定性合同、其他模块及配置 |

统一回归命令使用 `.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit`，只选择上表相关文件/测试；没有运行大规模无关回归或 backend 全量 collection。完整选择参数与结果在 `var/planning-v2-item1-project-ref-fix-20261008/regression.xml`、`regression.log`。

全部 HTTP 测试使用 `httpx.MockTransport` 或 FastAPI `TestClient`，不发送产品请求。手写正确字段证明结构表示和接线，不能证明 DeepSeek 会正确生成。

## 4. 历史 Case 7 的离线定位

读取上一轮原始 `case-7.provider.json` 的副本，只将以下三处 `goal.project_context` 替换为 `project_context`：

- `required_requirements[2].source_refs[1]`
- `required_requirements[3].source_refs[0]`
- `hard_constraints[0].source_refs[0]`

原输出仍被 Validator 拒绝，错误字段 `source_refs`；修改副本通过 Validator，项目背景原文完整保留，重复验证 Profile/ID/hash 一致。离线副本 `profile_hash`：`a55bd72c28f379551b5f3dc4e1de898d729a8f07f83e93bbd02c520d43945b2d`。

诊断明确标记 `OFFLINE_MODIFIED_HISTORICAL_OUTPUT_NOT_REAL_PASS`，保存在 ignored `case7-offline-diagnostic.json`。没有修改、覆盖或重发历史响应；不将此副本计为真实模型 PASS，上一轮 Case 7 FAIL 原结论保持。新的真实模型验收为 **NOT RUN**。

## 5. 独立审查

独立开发审查代理请求 `gpt-6.1-sol / medium`，使用同一有限 Evidence Packet 对照 Prompt diff、五项测试、历史三处引用诊断和本报告；不调用被测 DeepSeek，不新增产品审核阶段。主协调请求 `gpt-6.1-sol / high`，实现请求 `gpt-6.1-sol / medium`；实际模型解析均 **NOT OBSERVABLE**，没有宣称角色名等于实际模型身份，没有升级 HARD。

独立审查结论：**PASS**，无代码 BLOCKER。审查确认仅纠正引用说明及最小示例；合法来源规则、严格 Validator、此前 hard_constraints 修复、ID/hash 均保持，没有课程扩展或产品第二审核器。XML 实读确认 RED 1FAIL4PASS、GREEN 5PASS、局部回归 33PASS；历史副本验证与新真实验收明确分开。采纳审查建议，将 Prompt 歧义表述为可能诱因，不把尚未真实复测的因果效果写成已证明。证据保存为 ignored `independent-review.md`。

## 6. 边界、未运行项与后续授权

- 本轮产品模型请求 **0**，搜索 **0**，Reader **0**，数据库写入 **0**；本轮产品模型授权上限 **0**。
- 产品账本全部 375 文件字节 hash 保持，使用值仍为 182/280；历史 unknown 第 177 次保持且未重派。本轮没有调用余额查询、变更 Provider/模型/凭据/预算、充值或消费旧授权。
- 797 个受保护 tracked 文件、`.env`、历史 Case 7 输入/请求/输出/诊断、架构合同及旧进度保持；新增 migration **0**。
- 公开 `/plans/generate` 仍在身份/项目 scope 后返回 503，门禁测试证明 Run/Job/Provider/Plan 依赖访问前拒绝，组合根未注册旧 Fake Planning。
- 新 Run/Job/Draft/Plan mutation **0** 为未执行生产入口/DB 写入及测试 spy 门禁的证据，**真实 PG 行计数 NOT RUN**，不冒充数据库统计。Planning 占位页文件 hash 保持；真实浏览器验证 **NOT RUN**。
- 新真实 DeepSeek Case 7 **NOT RUN**；本轮只能声明离线修复准备完成，不能声明 Item 1 已获真实验收。

修复完成后仅提出单独授权申请：**最多 1 次新的 DeepSeek 官方 API 请求，沿用 `deepseek-flash`，只测 Case 7，每案一次，无 retry/repair/模型切换**。取得明确授权后仍须检查最新 Provider/余额/账本和参数，不扩大产品预算、不复用已耗尽的五次授权、不重派 unknown177。当前不执行该请求。

最终：**ITEM1_PROJECT_CONTEXT_FIX_READY / ITEM1_REAL_ACCEPTANCE_PENDING / ITEM2_NOT_STARTED / STOP**。不启动 Item 2。
