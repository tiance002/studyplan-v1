# 测试账号知识库 Agent 课程审阅数据

本目录的 [JSON](test-account-agent-plan-2026-10-02.json) 将 `frontend/src/content/agentCurriculum.ts` 的能力建议落实为测试账号计划内容，顶层格式为 `version: 1`、`title`、`stages`。贯穿项目是可验收的知识库 Agent。

13 个阶段依次为基础环境、LLM、工具、最小 Agent/Eval-Lite、RAG、Workflow、记忆、MCP、Eval/Reward、Agentic RL 基础、高级评估、综合实践、可选完整训练。RAG 与 Workflow 为兄弟能力分支，没有彼此先修；知识应用优先 RAG，调试与自动化优先 Workflow。MCP 按目标选修。高级评估直接依赖 Eval 基础；完整 RL 训练位于综合实践之后，另需数学、PyTorch、数据和算力准备，不成为综合项目必经先修。

数据包含 43 个知识节点、13 个学习单元与 13 个具体实践任务。单元与任务引用同阶段的 `node_keys`；所有 key 在本文件中唯一。实践标准检查代码、输入数据、运行记录、trace、评分与成果说明，没有统一分数通关或每日总结要求。RL 基础使用本地确定性工具环境；轨迹模拟与奖励分析不冒称参数训练。

每阶段提供一个主要来源及最多两个补充/参考来源，共 27 项资料安排、19 个不同官方 URL，阅读范围限定到相关章节或主题段落。主协调者已在线核对页面内容与章节，修正跳转后的 RAG、Persistence、PyTorch、LoRA 地址及阅读范围，MCP 固定到 2026-07-28 文档。Python 按入门例子分段阅读；RL 基础以 GRPO 概念为主线，PPO 补充、强化微调文档参考。资料可访问及内容对应不代表已经执行示例或真实训练。

验证：JSON 解析、字段、数量、引用、唯一键、先修 DAG、分支及训练顺序检查 **PASS**。课程子任务只创建数据；主协调者随后依据用户明确授权，在保留的隔离测试库为当前测试账号正式发布第 4 版，复用现有 owner/RLS、版本 CAS 与发布事务，事务回滚预演、实际发布及旧记录逐行保全检查均 **PASS**。CUA 实际网站已显示版本 4，并核对 Eval、RL 和高级评估。没有发布新公共 Seed 或修改正常账号路线，模型调用、真实 RL 训练与备份恢复演练 **NOT RUN**。详见[本轮验收记录](../acceptance/test-account-curriculum-review-2026-10-02.md)。
