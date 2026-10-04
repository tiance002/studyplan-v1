# v6.10 三条新教学样本

这三条均明确来源于 **本轮 Fake provider + 新 owned PostgreSQL + 实际 Edge 普通用户界面**，不是 DeepSeek 输出，也不是 v6.8 旧真实 Plan。输入中的“已有项目”是合成学习场景，未连接、修改或运行任何外部项目。

每条均通过普通注册登录、生成、草案确认、PG 精确读回、Edge 刷新、退出重登录；生成后额外请求为0，外部网络尝试为0。阶段/任务尚未完成，安排资料、自述已有基础和复制 Prompt 都不等于已掌握。

本轮另有真实 DeepSeek 尝试，但 A2 结构/两次 repair 失败，**没有真实新 Plan**。三样本不替代此失败；最终状态见 [BLOCKED 审计](v6-10-planning-alignment-2026-10-04.md)。

## 样本一：系统学习 Agent 应用开发

**输入**：“零基础系统学习 Agent 应用开发，先做一个最小应用。”

来源：Agent6，Fake/owned PG/Edge；Plan `pln_c0bebea67b4e4c898b6ccede01024bbd`。实际7阶段、7任务，A8有1个可消费知识节点。

| 学习顺序 | 教学目的与可检查产出 |
|---|---|
| A0 程序与模型边界 | 区分模型请求、程序执行和结果消息；能解释正常/失败路径 |
| A1 最小 Agent loop | 有停止条件的循环，工具请求/结果配对，避免无限循环 |
| A2 组件化与受控行动 | 工具定义、参数/权限校验、派发和错误证据；承接 A1 |
| A3 简单知识问答 | 有限文档与引用，证据不足时明确无答案；不等于完成完整 RAG 专项 |
| A4 长会话与上下文预算 | 区分历史、事实、临时约束，解释召回/裁剪/摘要边界 |
| A7 系统评价 | 对正常和失败结果保留可检查证据；评价继续横切后续实践 |
| A8 可控真实项目 | 从教程与小实践进入真实 Runtime 核心地图，比较自己的实现并验证适合的一项迁移 |

**自己的实践载体**：默认“研究与行动助手”明确是可替换的 Starter 候选，不强制选择或安装。**参考学习项目**：Pi 轻量 Runtime 为可换候选，与自己的实践载体分开；初学 Demo 不自动满足成熟工程对比。

A8 实际绑定既有审核的 Pi SDK lifecycle/storage/prompting/events 与 Sessions and Context 两个文档范围，仓库入口为 `https://github.com/earendil-works/pi`。审核深度继承原 selected sections；本轮没有全仓审读或运行验证。

whole_core 指导与复制 Prompt 实际可见：

- 先画工具请求→派发→结果→下一轮和会话状态的核心地图。
- 读一条正常链和一条失败链，区分源码事实、工程解释和未核实推断。
- 产出调用地图、失败样例和比较记录；clone/运行成功本身不代表掌握。
- 最多选择1–2项适合自己载体的机制迁移，保留验证证据。

**完整方向与当前首步**：当前生成基础与轻量工程认识，后续 RAG/Coding/Workflow/MCP/Browser/深入 Evaluation 可按目标组合，RL 另选可选；这些未选专题没有被自动生成或标完成。匹配的大型成熟项目在满足对应前置后采取3–8个目标相关 slice，一次一个；当前不要求全仓掌握。

证据：`var/v610/system-browser-plan.json`、`system-pi-card-edge.png`、`system-workspace-edge.png`、`alignment-browser.json`。真实 provider A8：**NOT RUN**。

## 样本二：只学 MCP，已有基础 Tool 调用

**输入**：“我只想学 MCP；已经会基础 Tool 调用。”起点为“已经会基础 Tool 调用”。

来源：Agent6，Fake/owned PG/Edge；Plan `pln_90262202a05a412db7507426f6988bbc`。实际4阶段、4任务。

| 学习顺序 | 本次边界 |
|---|---|
| A0 程序与模型边界 | 简短进入检查，确认正常/失败证据；自述不代表已核验掌握 |
| A1 最小 Agent loop | 检查工具请求/结果配对和停止；已通过可沿已有样例继续，不机械完整重学 |
| A2 组件化与受控行动 | 检查参数、权限、派发/错误边界，作为外部工具协议的必要前置 |
| A6 接外部能力 | 围绕 MCP 与协议接入的新增边界开展学习 |

没有 A3/A4/A7/A8，没有完整 RAG、Browser 或大项目路线，没有 Pi 卡。保留必要能力闭包并把已有基础安排为复习检查；MCP 专题没有被完整 Agent 默认核心吞掉。后续方向地图只是可选说明，不会因此生成未选择的课程。

证据：`var/v610/mcp-browser-plan.json`、`mcp-draft-edge.png`、`mcp-relogin-edge.png`、`alignment-browser.json`。真实 MCP provider 代表：**NOT RUN**；本轮裁剪行为由确定性/Fake/PG/Edge 验证，未额外收费。

## 样本三：已有 Node.js API，学习部署运维

**输入**：“我已有一个 Node.js API，希望学习部署、监控、自动发布和恢复。”起点为“已有 Node.js API，熟悉 JavaScript 与 HTTP”。

来源：Cloud3，Fake/owned PG/Edge；Plan `pln_120b967732db44798a6458d6f66745c3`。实际9阶段、9任务；9项任务包含用户载体，4项明确为独立 Micro Exercise。没有 fallback Task Service 阶段。

| 学习顺序 | 当前可做与后续边界 |
|---|---|
| S0 服务基线、配置与健康 | 沿现有启动命令、路由和测试确认服务边界 |
| S1 Docker Image/Container/Dockerfile/端口 | 容器化现有服务，沿已审材料核对健康、启动与端口 |
| S2 Compose 网络、卷、依赖健康 | 通用本地容器与合成数据隔离演练，保持语言与 DB 选择 |
| S3 第一次云部署 | 当前只做隔离本机的启动、健康、日志/网络检查；云商部署与数据库恢复细项待选/待审，不将本地检查当完整验收 |
| S7 Node API 可观测性 | 当前保存正常/失败请求的通用日志、时间与边界证据；Node OTel instrumentation 和 DB spans 的专门教学范围仍待核对 |
| S8 OpenTelemetry Demo 大系统切片 | 可替换成熟参考，目标切片比较；不把 Demo 当自己的实践载体，不要求全仓安装或运行 |
| S9 GitHub Actions CI | 先自动化已经能手工做对的测试与检查，不直接授权正式入口变更 |
| S10 容器交付、受控部署与身份 | 保留最小权限、配置、环境与回退边界，具体环境按选择核对 |
| S13 备份、恢复、最终验收 | 当前本机合成文件/卷持久化检查和方案核对；数据库 dump/restore、迁移与 smoke tests 待选 DB/教材后执行，原后续验收完整保留 |

**不强制改语言或 DB**。当前载体是测试输入中的 Node API；源框架/数据库专门示例不自然匹配时为独立小实验，适合后才迁入。Cloud S3/S7/S13 的任务、结构化指导及章级提示均明确后续待选/待审；本地演练不等于已部署云端、已实现 Node OTel 或已恢复数据库。

草案和 workspace 均显示“资料缺口：通用本地演练与待选范围”及 `needs_research_or_review`。已审 Docker/Compose/Actions 可以继续学习；云商未知、Node instrumentation 和对应 DB 恢复的缺口没有被升级为完整已审教程。教材中的 Task Service 只在可选参考项目的“无项目时”条件里保留，不是当前用户的任务指令。

证据：`var/v610/node-browser-plan.json`、`node-draft-edge.png`、`node-workspace-edge.png`、`node-relogin-edge.png`。真实 Cloud provider、真实云端部署及数据库恢复：**NOT RUN**。

## 多候选与长指导的额外证据

普通 RAG Fake/PG 路线保留 G6 的 RAGFlow 和 WeKnora 两个可替换参考。另在独立新 owned DB 创建合成 v7 长文本夹具，经普通生成/确认/PG读回验证续片有序无损，未改变 Agent6 CURRENT_PACKS。

实际 Edge 组件夹具显示两候选、各自精确 root/重点/Prompt、>850字符完整指导、同仓不同stage、pending 项目、真实剪贴板和拒绝后的手动选取退路。组件夹具与普通 PG 样本分别标注，未把 API mock 冒充真实 PG，也未把 Prompt 验证冒充外部 AI 源码执行。
