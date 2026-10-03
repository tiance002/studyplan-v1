# Agent 评估：从第一条工具调用到专项回归

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 类型：Cross-cutting Capability Path。Evaluation 横切 Common Core、全部 Recipe 与用户特有能力，不是独立职业分支，也不是仅在最后才出现的课程。

研究日期：2026-10-03。本文是教学设计；下面的实验尚未执行。阅读正文与静态检查示例不等于运行验收。

## 结论与主线

Eval-Lite 插在第一次工具调用之后；Hello-Agents 第12章在会实现基本工具 Agent 后主读。系统评估进入各专项之前建立，随后随 RAG、Coding、Workflow、Browser 分支深化。Agentic RL 可选，但训练之前必须具备独立测试集与任务成功判据；训练后增加泛化与奖励审计。不会把第11章 RL 变成第12章评估的前置。

连续主线：Hello-Agents 第12章建立全貌 → OpenAI 官方 agent-evals 指南建立 traces→datasets 的概念顺序 → LangSmith 官方 Evaluation types → Evaluate a complex agent 的 Final response / Trajectory / Single step 三节 → 对当前专项插入专门评估。LangSmith 的资料免费；云服务使用条件与模型调用费用另计。最早阶段采用本机 JSONL 和确定性判定，无需注册平台。官方教程是教授评估机制的材料，持续项目不需要复制音乐商店和退款业务。

## 官方评估资料的版本边界

OpenAI 官方 [Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals) 展示了从单条 traces 调试、给 trace 评分，到建立可重复 datasets/eval runs 的顺序；[Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) 可用于讨论规则评分、人工标注与 LLM judge 的适用范围及位置/冗长偏差。它们作为评估概念和章节补充，不要求绑定 OpenAI 平台。

截至本研究日期 **2026-10-03**，OpenAI 官方 [Working with evals](https://developers.openai.com/api/docs/guides/evals) 标明 Evals 平台计划于 **2026-10-31** 对现有用户转为只读，并计划于 **2026-11-30** 关闭。新路线因此把 OpenAI 页面用于理解 traces、datasets 和评价流程，不把 Evals API/旧平台操作列为长期主实验；从第一周起用本地 JSONL、确定性 grader 和可迁移的测试接口。上线或授课前应再次核对官方 deprecations 页面。

## 实际检查与教学边界

| 资料 | 检查范围 | 真正教授 | 需要补充或调整 |
|---|---|---|---|
| [Evaluation types](https://docs.langchain.com/langsmith/evaluation-types) | 全目录与正文；offline/online、code/judge/composite/pairwise evaluator | 区分评估时机与评分方法 | 不能将平台操作当作理解指标；本路线自己补数据划分与误差分析 |
| [Evaluate a complex agent](https://docs.langchain.com/langsmith/evaluate-complex-agent) | 环境/SQLite/路由图，评估三节正文与对应代码 | 最终回答、工具路径、单节点分别构建数据与评估 | 示例假设 API、Python async 和 LangGraph 基础；退款演示省略鉴权，不可直接迁入真实应用 |
| [AgentEvals](https://github.com/langchain-ai/agentevals) | README完整评估目录，strict/unordered/subset/superset、args override、judge代码 | 路径匹配与语义评分的不同用途 | 是组件参考，不是完整初学者课程；严格路径仅适合路径本身是业务约束的任务 |
| [Evaluate a RAG application](https://docs.langchain.com/langsmith/evaluate-rag-tutorial) | 建索引、数据集、四类grader及运行代码 | correctness/relevance/groundedness/retrieval relevance | 主线额外加入有人工相关文档标签的检索指标；相关性judge不能替代Recall@k |

当前示例中的模型名、SDK导入和 tracing 配置只作 VERSION_CONTEXT。学习当时读取当前稳定文档并在独立环境中检查依赖；不照抄 `pip install -U` 升级运行项目。

## E0：第一次工具调用后立即做 Eval-Lite

- **为什么现在**：能输出正确文本，不代表工具选对、参数正确或行动真正发生。
- **前置**：能看懂函数、字典、JSON与一次工具调用。不会测试断言时，临时补一个输入/输出相等断言即可。
- **主读**：Hello-Agents 第4章工具循环相关段落回顾；第12章评价对象部分预读。这里提前插入一个小练习，不提前搬整章。
- **新增/重复**：工具循环 REVIEW；将一次运行拆成 input/tool/args/result/final/outcome 是 NEW。
- **小实践**：自己写6条样例：需要计算、无需工具、缺必填参数、非法类型、工具异常、达到步数上限。用固定工具返回值；分别检查工具名、参数schema、异常处理和最终状态。
- **持续增量**：研究与行动助手开始保存测试用例与结构化执行记录，记录实际工具调用，不要求隐藏思维过程。
- **退出标准**：能指出“回答正确但调用了错误工具”的用例；能解释每条断言测什么。6条是教学起点，不是生产可靠性保证。

## E1：单步与端到端系统评估

先读 Evaluation types 的 Benchmarking / Unit / Regression / Pairwise，再按 complex agent 的 Final response → Single step 顺序完成；不要求复制全部复杂图。前置是有两个工具及一套可复现输入。

主读图教程中的数据集、target function、code evaluator与结构化judge输出；对照 OpenAI best practices 中的 metric-based、human、LLM-as-judge 三类评估。SQLite退款业务快速了解，复杂子图构建可以跳过；已有Workflow经验者将它作为 COMPARE。

小实践：按场景写20条题，先分“开发集”和封存测试集，近似改写的同一题不能跨组。每条包含 task_id、输入、可接受结果、必须/禁止动作、环境fixture、失败标签。确定性grader检查参数、环境状态及结果文件；回答语义无法规则检查时才增加judge。

持续增量：提供一次评估入口，输出按题结果、成功数/总数、排除与失败原因。退出标准是能定位单步失误与最终失败之间的关系，避免一个平均分掩盖全部失败类别。样本小就列逐题结果和计数，不宣称统计显著。

## E2：轨迹评估与 LLM judge 校准

主读 complex agent 的 Trajectory evaluator，配 AgentEvals 的 matching modes 与 Tool args match modes；再读 OpenAI best practices 对位置偏差、冗长偏差和人工校准的建议。前置是能采集真实工具序列，知道状态变化和用户约束。

REVIEW 工具与上下文；DEEPEN 允许多条合法路径。先检查任务终态，再检查顺序约束。例如“先确认再修改”需要偏序或确定性约束；两个独立检索工具交换先后不应自动判失败。严格参考轨迹不适合所有自由规划任务。

小实践：对同一题写两个合法轨迹、一个遗漏关键动作轨迹、一个多余但有害动作轨迹。比较strict/unordered与自定义约束；对12条人工标注结果让judge评分，查看分歧而非仅汇总相关性。交换A/B次序、盲化模型名，检查位置与篇幅偏差。

持续增量：保存rubric版本、grader/judge版本、人工复核结论，保留“不确定”并检查失败输出。退出标准：能说明何时judge仅为辅助，何时规则判定是最终依据；能解释更长答案为何不应天然得高分。

## E3：RAG 专项评估

出现位置：首次检索时就测召回；引入混合/Rerank前必须有固定题集。主读 RAG tutorial 的 Create a dataset / Define evaluators / Run evaluation；索引构建 REVIEW，回答与证据分开评价 DEEPEN。进入 RAG 专项时沿用同一评估原则，并把检索召回与答案证据分别验收。

小实践：人工标注30条合成题及相关文档，包含精确实体、同义问法、多文档、否定、无答案和图表问题。固定语料与chunk标签比较dense、BM25、hybrid；先看Recall@k/MRR或nDCG，再看答案正确、证据支持、引用定位。标注单位是document还是chunk必须明确；重新切分时重建相关性映射。

持续增量：记录 query → 候选 → fusion → rerank → context → answer，坏例分解析丢信息、切分、召回、排序、上下文裁剪、生成、引用。退出标准：能用一题解释混合为何比纯向量差，而非先调更多权重。

## E4：Coding 专项评估

出现位置：引入file/shell工具时就检查修改边界；加入真实修复任务后测任务成功。前置是独立练习目录、基础Git diff与测试输出。

主读 learn-claude-code 当前 Permission / Goal Loop 相关段落，作为执行边界与停止条件 COMPARE；评估方法沿用E1–E2。一次用例包含初始项目、问题、验收测试、允许修改范围、预算。教学阶段选3–5个小缺陷，不开始跑大型公开基准。

小实践：设置“修复函数”“修复后未测试”“测试失败却声称完成”“删除测试来通过”“改了无关文件”。核对实际diff、完整退出码和隔离环境，不能让Agent自述充当成功证据。持续增量是变更任务账本与可回放fixture；退出标准是第三方在相同fixture能验收，未运行明确记 NOT RUN。

## E5：Workflow / Browser 专项评估

出现位置：checkpoint/interrupt、浏览器动态操作第一次加入时。Workflow看持久化与HITL正文，Browser看可见状态、定位器、断言和session章节；参考对应专项文件。

小实践：Workflow在批准前/副作用后/状态落盘前注入失败，检查重复恢复是否多执行一次；两session穿插运行检查隔离。Browser使用本地测试站：迟到的按钮、导航后失效定位、过期登录、弹窗、重复提交。用页面或后端状态验证任务成功，不只看最后一句“提交成功”。

持续增量：恢复率、重复副作用次数、最大重试/耗时及session隔离记录。退出标准：每个失败分层可解释，禁止操作零执行，重试预算耗尽可结束并回报状态。高风险动作的断言是业务要求，不能为了成功率关闭。

## E6：回归、消融、延迟与费用

主读 Evaluation types 的 regression / benchmarking / pairwise，并将 OpenAI evals API 作为当前退役中的 VERSION_CONTEXT；前置是已有基线与封存数据。一次只变一个因素，比较同题、同环境、同模型设置与预算。任务随机时按题重复，保留失败/超时，记录运行顺序；不要只保留成功样本。

学习实验：分别关掉query rewrite、rerank或context compact比较；记录success、p50/p95（小样本同时给原始值）、input/output/cache token、工具调用次数、云API账单口径。token节省与费用节省分列；嵌入、judge、失败重试的调用都计入相应费用。不因用了本地模型就宣称质量相同或必然省钱。

持续增量：基线快照、逐题差异、成本账本和一页bad-case解释。退出标准：能回答“改善来自哪一步”“有没有偷看测试集”“安全或延迟是否退步”；只在数据支持时作结论。

## E7：RL 之后的高级评估

仅训练分支必读：按任务族划分train/validation/test，奖励函数开发只用train与validation。测试grader独立于训练reward；若两者相同，要另加未优化的任务成功标准与人工审计。检查reward上升但成功率不升、工具调用无效增加、长轨迹退化和新任务泛化。比较base、SFT、RL，在相同推理预算下报告多seed与重复采样范围。训练集记忆不能算能力增长。

退出成果：一份可复核报告，明确数据版本/划分、基线、配置、reward与测试指标、所有失败及无法确认的限制。没有真正训练就称“轨迹与奖励教学实验”，不能称Agentic RL训练完成。

## StudyPlan 的评估阶段输出契约

每个阶段至少返回：评价对象、判据、数据范围/划分、grader方法、失败标签、资源费用条件、预期产物、进入下一步的证据。阈值由任务目标确定；本文件样例数量是练习设计，不是统一合格分。

源码学习提示词：读取当前实现，先定位输入、工具调用和最终环境状态；输出事实/解释/推断；用独立fixture复现一个失败并给证据，未执行显式注明。只迁移1–2项评分或日志机制，不为运行基准关闭保护。
