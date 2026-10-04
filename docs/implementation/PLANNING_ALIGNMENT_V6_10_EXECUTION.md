# v6.10 规划一致性执行记录

基线：`ff3b6c42c16b0ec2b634b45441251cb8dc1e3249`，`feat/n1-resource-discovery`。
N0：跟踪文件干净，仅两个禁操作目录未跟踪；本机无 v6.9 实施提交或内容版本。ZIP 的 Goal、review、cases 哈希与 MANIFEST 相符，逐字节归档在 `docs/reviews/planning-alignment-v6.10/`。附件是需求及审查证据；执行权限以用户本轮消息为准。

## Goal / Constraints / Allowed changes / Non-goals

修复方向、完整/专题范围、排除/前置、A8 绑定、私人任务适配及多项目/续片消费。仅现有框架内薄规则、下一版 JSON 内容、现有 DTO 字段消费、Fake/owned PG/Edge。禁止搜索、原产品库连接、正式入口/Worker、RAG、外部项目写入、push/merge/reset。不增加公开契约或迁移。

用户最新授权仅覆盖产品真实模型调用为 0 / 禁止收费验证：历史累计 39 次保持原样，新增授权 50 次，原受控总上限 50 → 100，理论剩余 61。先确定性/Fake/unit/owned PG/Edge，通过后才允许新 owned 单一系统 Agent 代表；其他代表仅按未证明的真实行为需要使用。失败计数、unknown 保守计数并停止派发/reconciliation、最多 2 repair、冻结 manifest/canonical/endpoint/TLS/budget guards 保持。达到 100、无法 reconciliation、新结构性设计问题或原有外部副作用门禁时 STOP。

## 顺序及责任

1. 复现 G/P/C 偏差；root 拥有选择、冻结、内容版本与事务边界。
2. 下一合法 Agent6/AI3/Cloud3；旧包 immutable；复习不代表 mastery。
3. 前端独立 writer 拥有 ProjectStudyCard/Prompt/MainWorkspace 及消费测试；无 DTO 改动。
4. 规则/Fake、受影响相邻回归、owned PG/Edge 三新样本及双候选/长文本。
5. 记录来源、逐用例状态、历史/账本保持、回滚，报告局部 PASS 或 BLOCKED 后 STOP。

## Tests / Evidence / Rollback

以归档用例的用户期望为 expected，不从 selector 输出倒推。新样本明确标 Fake/确定性或真实 provider；全产品继续 NOT_READY。历史与冻结协议回归；搜索新增必须为 0。最终记录起始 39、新增授权 50、总上限 100、本轮实际请求/repair/unknown 与各组验证目的。本地代码可普通 revert；未来新格式/内容快照须保留读取兼容，不能修改旧 Plan。证据保存在 ignored `var/v610`，安全报告保存 `docs/reviews`；不提交私有运行数据。

请求 root Sol6.1/high，前端 Sol6.1/medium，内容定位 Luna/high；实际解析 NOT OBSERVABLE。

## 最终状态

BLOCKED，STOP；详见 [验收与账本审计](../acceptance/v6-10-planning-alignment-2026-10-04.md)、[三条 Fake/owned PG/Edge 新样本](../acceptance/v6-10-planning-alignment-samples-2026-10-04.md)及唯一 [progress](progress.md)。非收费链路通过；真实7stage代表在A2越出冻结目录，两次repair后失败，未产生新真实Plan。起始39，新增授权50，上限100，实际新增6（4正常+2repair），最终45/100，unknown0，搜索新增0；历史哈希与reconciliation PASS。真实A8/practice/确认/Plan Edge NOT RUN，不自动派发第二Run、push/merge/部署。
