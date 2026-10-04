# StudyPlan v6.13 — 四项已复现合同缺口收口

日期：2026-10-04。

## 本包用途

供用户转发 Codex，续接当前本机未提交的 v6.11/v6.12 候选。不是已实施补丁，不是验收通过报告。本包未访问用户的 Windows 运行环境，也没有执行真实模型、数据库或浏览器。

- `01_REVIEW_DECISION.md`：对 v6.12 交付的判断、证据边界和修复裁决。
- `02_CODEX_GOAL_v6.13.md`：实施与授权边界；按此执行。
- `03_REGRESSION_CASES.json`：新增定向回归规格，全部初始为 NOT RUN。
- `SHA256SUMS.txt`：本包文档校验值。

## 输入事实

以用户提供的下列文件为依据，不把报告中的代码位置当成本包已独立重跑验证的事实：

1. `v6-12-targeted-alignment-2026-10-04.md`
2. `contract-review.md`
3. `v6-12-acceptance-cases-2026-10-04.md`
4. `v6-12-fake-plan-review-2026-10-04.md`
5. `progress(6).md`
6. 前轮已批准 `StudyPlan_v6.12_Targeted_Alignment/03_CODEX_GOAL_v6.12.md`

原始输入不重新打包；Codex 使用本机已保存的原件。本包不含 API key、账号密码、DSN 或真实用户正文。

## 不变的产品决定

完整 Agent 路线保留 Framework 与 MCP；持续实践载体与参考源码分开；小型核心、专项教程、成熟切片、迁移验证分段；canonical Knowledge 与 LearningUnit 分离。冻结教学方案，不重做课程、不改成全固定闭集。

## 下一阶段边界

F1–F4 及其同一调用链的同类变体属于本次明确修复范围，不再逐项等待新授权。先完成非收费防护与真实 owned PG→API→Edge 验收，再按现有累计 100 次授权执行至多一个新完整合成真实代表；本包不新增额度。正式库、正式入口、正式 Worker、RAG、push/merge 不在范围内。

本包所列函数名、内部字段名和错误名如无实际源码对应，都是语义示例；优先复用现有命名与结构。
