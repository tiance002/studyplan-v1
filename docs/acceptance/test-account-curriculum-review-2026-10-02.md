# 测试账号课程第 4 版审阅记录

日期：2026-10-02。用户最新明确要求把此前讨论的教学安排应用到目前测试账号的实际计划，便于在网站审阅。本次在现有 `feat/v2-g1-user-slice` 分支完成这个有界请求，完整 V2 Goal 仍为 NOT_READY；没有 develop/master 合并、milestone 接受或公网发布。

## 范围与实际结果

保留测试账号在 `http://127.0.0.1:5177/#path` 的正式路线从第 3 版更新为第 4 版，包含 13 个阶段、43 个知识节点、13 个学习单元、13 个具体实践任务及 27 项资料安排。课程原文见[版本化 JSON](../curriculum/test-account-agent-plan-2026-10-02.json)与[课程说明](../curriculum/test-account-agent-plan-2026-10-02.md)。

顺序为 Python/环境 → LLM/Prompt → 工具/结构化输出 → 最小 Agent/Eval-Lite → RAG 与 Workflow 两个能力分支 → 记忆 → 可选 MCP → Eval/Reward → Agentic RL 基础 → 高级评估 → 综合实践 → 可选完整 RL 训练。RAG 与 Workflow 不设彼此先修；高级评估直接依赖 Eval 基础，完整训练另需数学、PyTorch、数据与算力准备，且位于综合项目之后。页面阶段入口的先修只列其他阶段知识，当前阶段内部知识依赖仍在节点内显示。

Eval 明确成功定义、固定测试集、deterministic grader/LLM judge、trace、success rate、成本/延迟 baseline、奖励与钻空子。RL 基础通过确定性工具环境、规则/随机 policy 的 rollout、稀疏奖励与归因分析理解优化对象，再理解 PPO/GRPO；没有参数更新的模拟不称训练。高级评估涵盖 trace 评分、失败分类、鲁棒性、泛化、回归、消融、成本质量、安全和 reward hacking；RL 前后比较以实际存在训练结果为条件。每个任务指定代码、数据、trace 或报告等可检查产物，没有 4/5 退出门槛或每日总结。

阶段完成继续按现有只读投影：同一路线同一阶段的非空阶段总结，以及该阶段全部给定实践的 USER accepted 成果。新阶段位置未冒用旧计划的完成记录，因此显示 0/13；旧版本、总结、Prompt、成果、历史 Run 与发布记录均保留。

## 实施边界与证据

[维护脚本](../../scripts/publish-test-account-curriculum.py) 限定到保留的合成账号与专用测试数据库，提供 prepare/publish/verify 三种模式。受控资料目录只在这个测试库追加，冲突不覆写旧目录；正式业务写入使用应用角色、owner/project scope、现有 RLS、同一事务中的 catalog materialize、Draft 保存及 PlanPublicationService 的版本 CAS/原幂等键。未创建收费 Run、恢复历史 Graph、重派 unknown，未修改公共 Seed 或正常开发库路线，也没有放宽网站写入保护。

ignored 证据目录为 `var/frontend-redesign/curriculum-review-20261002-01/`，包含 reviewed-urls.json、intent.json、dry-run.json、result.json 和新备份 before-plan-v4.dump（435,538 字节）。不提交账号上下文或数据库秘密。prepare 在完整发布逻辑后回滚；随后独立确认当前版本仍为 3、草案不存在、原历史哈希完全一致。publish 实际提交第 4 版，verify 以只读事务核对当前计划与原历史行哈希保全。当前版本切换允许旧版本状态发生规范的 superseded 转换，不覆写其内容。

网站 5177 → 8024 仍是保留的只读审阅入口；当前进程已经实际读到第 4 版。ignored 启动脚本补充了有发布回执时限定该项目/版本的校验，本轮没有重启进程来验证这个新增启动分支。正常 5175/8022、原 RAG 服务均保留。课程资料的 19 个官方页面已在线核对内容、阅读范围和版本；页面跳转按实际落地地址修正，没有运行外部教程代码。

## 验证

| 检查 | 状态 | 证据与界限 |
| --- | --- | --- |
| 课程结构、键/引用、DAG、分支与可选训练顺序 | PASS | prepare 校验与课程数据检查 |
| 新备份归档可读 | PASS | pg_restore --list；不等于恢复演练 |
| 完整事务回滚预演与独立回滚核对 | PASS | dry-run、当前仍为 3、草案不存在、原历史一致 |
| 实际发布与只读保全核验 | PASS | publish/verify exit 0，正式版本 4、13 阶段 |
| CUA 真实页面 | PASS | 版本 4、0/13、13 阶段；Eval/RL/高级评估先修、资料和具体任务核对 |
| 前端测试与构建 | PASS | npm --prefix frontend test：11；run build：57 模块，exit 0 |
| 维护脚本 Ruff、Git diff | PASS | 收口时静态检查 |
| 真实付费模型、真实 RL 训练、CLI 浏览器脚本 | NOT RUN | 本次未调用 |
| 备份恢复演练、新启动分支运行 | NOT RUN | 本次未替换数据库、未重启服务 |
| 完整 V2 功能/门禁与负责人最终验收 | NOT RUN | 不能用本次课程审阅替代 |

过程失败保留：首次新 ID 前缀带连字符、旧 ai_jobs 不含 project_id、supplemental 与领域枚举不一致分别为 FAIL；最小修正后最终 prepare/publish/verify 为 PASS。失败时业务事务回滚，目录只追加测试资料，没有改变旧计划内容。OpenAI Markdown URL 的工具读取因 content-type 为 FAIL，改用同一官方 HTML 页面后内容核对 PASS。没有把这些失败隐藏或把资料浏览称为训练验收。

## 回退

旧版本及全量备份保留。若用户要继续修订或恢复路线，应通过正常发布流程产生下一版，并保留第 4 版历史，不直接改已发布结构或删旧记录。整库备份恢复涉及替换数据库，本次没有执行。无需因网页审阅反馈重复运行已有 publish 或产生新收费调用。
