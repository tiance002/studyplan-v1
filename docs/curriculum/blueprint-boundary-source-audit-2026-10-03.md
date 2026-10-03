# Coding / Workflow 边界教材正文核对

本记录补充三方向候选的专属教材缺口。项目日期 2026-10-03；由主会话通过网页读取工具读取公开官方正文，不调用 GitHub API、Tavily 或产品模型，不运行外部仓库。审核的是正文可读性、指定阅读范围与教学适用性；学生练习执行和当前工程 SDK 示例兼容性均为 NOT RUN。

| 编号 | 实际地址与正文范围 | 阅读与版本证据 | 适用内容和限制 |
|---|---|---|---|
| B01 | [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)：Approve or reject、Review and edit state、Rules of interrupts、Side effects called before interrupt must be idempotent | 公开正文包含示例与说明，无登录/付款阅读门槛。页面无固定 SDK 发布版本，部分示例使用事件流 v3；内部 source_version=1 不代表 SDK v1 | Workflow 的批准/拒绝、恢复时节点重执行、重复副作用与分离执行节点。Coding 的修改前确认。该说明不能保证远端 exactly-once；输入基线哈希、业务键去重及 unknown 停止核对是本课程额外的实践要求，不能冒称官方完整实现 |
| B02 | [Git diff](https://git-scm.com/docs/git-diff)：Description、git diff 工作区/索引/提交、--no-index、--exit-code | 公开参考正文可读；官网版本列表随更新变化，须以学生本机 git --version 核对 | Coding 的差异预览与有限文件比较；这是工具参考 Supplement，不是完整 Coding Agent 教程。只读差异输出不能替代用户确认和工作区范围校验 |
| B03 | [Git apply](https://git-scm.com/docs/git-apply)：--check、--index、默认原子失败、--include/--exclude、--unsafe-paths | 公开正文可读；网页标示手册更新于 Git 2.55.0，且 2.56.0 无变化。核对日期不等于学生安装版本 | --check 检查补丁适用性；默认路径边界与失败行为可作为 Coding 修改练习的参考。课程不使用 --unsafe-paths；预检查与应用之间仍可能变化，应额外校验基线并限定目标文件。未证明 symlink/并发隔离或任意 shell 安全 |
| B04 | [LangChain Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)：配置工具审批、approve/edit/reject、恢复执行 | 公开教程正文可读，模型 API 成本另计；页面不固定本工程依赖版本 | 学习批准与实际执行分离，比较编辑提案后重新决定的行为。只用于教材，不因此新增项目中间件或运行平台。重复批准、已知失败/未知结果与本地模拟日志仍需独立练习 |
| B05 | [LangChain Unit testing](https://docs.langchain.com/oss/python/langchain/test/unit-testing)：Mock chat model、InMemorySaver checkpointer | 从 Test 页 Next 链接打开实际正文，包含 GenericFakeChatModel 的固定响应和工具请求、线程内存示例；免费正文无需账号，SDK 固定版本不可观测 | 三方向 Eval-Lite/项目验收的具体教程；与 Test 概览分开记录。本地 Fake 不代表真实模型质量，线程示例不代表持久化/隔离已验收 |
| B06 | [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation)：Offline/Online Evaluation、Evaluation workflow | 公开正文可读；页面运行流程需账号及 API key，成本/隐私与正文阅读分开 | 仅 Supplement 介绍数据集、规则与人工评价、实验结果分析。基础路线使用本地固定案例，不强制上传 trace、注册云账号或调用 LLM judge |

请求 `https://docs.langchain.com/oss/python/langgraph/durable-execution` 实际跳转至 [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)。所读正文区分 checkpointer 的线程状态与 store 的跨线程数据，不能将该跳转页审核为旧 durable-execution 完整教材。使用实际地址并交由公共教材审核记录单独说明。

[Python 3.14 Tutorial 总目录](https://docs.python.org/3.14/tutorial/) 已由主会话打开核对：实际章节顺序包含 4→5→6→7→8→9→10→11→12，所选 Primary 4→5 和 7→8 各自在真实作者目录中连续，第12章独立安排。未通过删目录章节制造跨章连续。页首说明面向已有编程认知而初学 Python 的读者；页面显示 Python 3.14.8、2026-10-02 更新，页尾列 PSF License v2，文档代码另有 Zero Clause BSD。课程只链接并保存原创摘要。

新内容的 `checked_at` 为本次审核证据整合的实际时间 `2026-10-03T03:27:29.094082+00:00`，不是网页工具未暴露的抓取时间。独立日期、所读范围和限制继续保留；没有虚构精确页面抓取时钟。

## 课程采用的清晰算法

这些是课程要求的原创实践算法，不是从网页复制的代码，也不是本产品新增执行平台。

- Coding：读取白名单文件 → 保存基线摘要 → 提出具体差异 → 展示目标与差异 → 用户明确确认 → 再查基线/范围 → 应用一次 → 运行事先指定的测试 → 保存原始输出。基线变更拒绝旧提案；确认重放读回原结果；执行结果未知先核对实际文件，不自动重试。
- Workflow：保留输入与规则版本 → 分类/缺信息 → 规则校验 → 生成动作提案 → 人工批准或拒绝 → 以业务键查询既有动作 → 本地模拟执行并记录结果。输入或规则变更使旧批准失效；unknown 停止自动执行；两个工单的原文、摘要和动作记录隔离。

收益是补齐两个方向的练习边界，依赖是已选教材和学生现有 Python/Git，无产品运行依赖或框架迁移。只链接外部教材并保存原创摘要，不复制整篇或源码；保留各站原许可证和署名。回滚是撤回新内容版本与目标路由，不修改旧版本或已有学习历史。

正文/指定段落核对：PASS。完整教学练习、SDK 示例运行、真实付费 API、生产 Seed 导入：NOT RUN。上述限制须保留在正式内容中；不可把审核字段等同于学生能力 VERIFIED。
