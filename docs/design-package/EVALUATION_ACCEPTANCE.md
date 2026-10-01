# 评测与交付验收

2026-10-01 / S0。围绕 Plan Quality、Resource Quality、Grounding、Learning Progress、Practice Quality、Cost 保存原始证据；不因数量指标增加无关能力。

## 完成度和结果

Implemented = 实现存在；Tested = 指定输入的命令/exit code/结果已核对；Integrated = API/持久化/UI 连接；Verified = 关键场景实际运行且原始 artifact 已核对。四者分别记录，不能由类定义或“passed”文本自动推导完整交付。

测试结果只用 PASS / FAIL / NOT RUN。历史报告是 Reported Evidence，引用其命令/commit/artifact 并核对才可提升对应能力，不将局部 PASS 扩大为 V1 PASS。

## 八个真实场景

| ID | 场景 | 主里程碑 | 需要的证据 |
|---|---|---|---|
| S1 | 零基础 Agent 完整规划 | M1 | Outline/结构/资源/任务、Draft 人工决定、正式版本读回 |
| S2 | 跳过 Prompt 并调整 | M1 | 用户决定、Proposal、新版本差异、依赖和旧记录保留 |
| S3 | 视频偏好替换资料 | M3 | 偏好作用域、可核对链接/定位、未影响稳定知识身份 |
| S4 | 临时询问 GraphRAG | M3 | 核心/扩展/高级/无关分类、来源、调整 Proposal；未批准不改结构 |
| S5 | 用户总结错误 | M2 | 原文、目标/rubric、具体误解与引导问题、不虚报已掌握 |
| S6 | 实践成果→Evidence→VERIFIED | M4 | 实际成果、来源核验、验收项、知识覆盖及状态事件 |
| S7 | 重开旧 Session | M2 | plan_version/节点/阶段、原事件、历史上下文恢复 |
| S8 | 修改计划与历史版本 | M1 | 新版本与当前引用、旧结构和历史成果可访问、稳定逻辑节点 ID |

M4.5 完整真实链：创建目标→生成路径→确认→选节点→访问资料→学习→总结→反馈→实践方案→Codex/IDE 实施→提交成果→验收→状态→计划调整。八场景与该闭环均通过才可交付 V1。

## 当前 Acceptance 09 的边界

20 Attempts 全部 succeeded（19 正常 + 1 reliability structure repair），Run waiting_user/review_draft、Draft awaiting_approval，最终错误为空。生成/修复/最终校验/Draft/等待暂停已核对；本次 Draft 批准/发布及后续学习闭环 NOT RUN。详见 [Run09 结果](../acceptance/b3f2/real-provider/2026-10-01-run09-result.md)。不再消费 Acceptance 09 或重复生成以收口文档。

## 五项危险边界验证

| 边界 | 实现阶段必须验证 |
|---|---|
| 本地身份 | 原 actor 的 Project/模型/Run 可达；客户端伪造 actor/跨项目拒绝；缺绑定或非本地访问拒绝 |
| 版本历史 | 新结构不覆盖旧版本；旧 Session/Reflection/Submission 恢复原 plan/content/rubric |
| 知识核验 | 阅读/自述/模型建议不升 VERIFIED；有效证据仅覆盖实际目标；失效证据保留并转 REVIEW_NEEDED |
| 隐私/检索 | 禁云/未许可外发请求 0；缺证据不猜、不虚构引用；本地失败不静默转云 |
| 旧图恢复 | waiting_user 按原 graph_version 批准/取消；批准不重跑模型；重复决定/崩溃不重复发布或付费 |

## 严重度与验证策略

P0：数据损坏、安全问题、主流程不可用，立即修。P1：核心功能明显错误，阶段内修。P2：边缘/低频，登记负责人及确认后延期。P3：体验优化进入 backlog。待实现功能列里程碑缺口，不把 S0 的实现缺口误记为 S0 文档测试失败。

日常 Unit → Targeted Integration → Critical E2E。验证入口复用 repo venv、显式测试文件；完整 suite 在 Milestone Verification，记录命令/exit code/输出/commit。仓库当前没有可核对的 `make verify-mX` 统一入口：到相应里程碑组合已有脚本/命令并冻结，禁止声称不存在的命令已 PASS。

## 付费和冻结

免费 preflight 核对身份/Project/队列、模型/endpoint/thinking/budget、worker/graph/checkpoint/lock、未消费 ID、历史哈希。真实验收须用户明确授权 ConfirmPaidRun + 新 AcceptanceId + 专用 ProjectId；journal/submission_intent/Attempt/result/evidence 保留，unknown 不重派。

里程碑证据包括 Schema/OpenAPI、Prompt、model、DomainPack/资源版本、输入样例、测试/E2E/真实 Run 和验收 artifact；有使用 embedding 时记录 Adapter 的版本配置，不把具体 embedding 名称绑定 StudyPlan Domain。commit→负责人确认→annotated milestone tag，master 合并仅在明确接受该里程碑后。
