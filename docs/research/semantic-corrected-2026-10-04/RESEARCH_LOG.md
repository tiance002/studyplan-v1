# 三方向研究日志

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 本轮为语义标准化，未新增研究、未扩大审读范围；下方原研究日志为历史证据。原审读日期/运行状态/审计快照保留，其数目及旧方案表述不作为当前 planner 规则。公共学习卡不继承快照 commit/path。当前产品规范与目录覆盖历史编排措辞。

审阅日期：2026-10-03。只读独立资料快照；未修改StudyPlan、未commit、未发布Seed。教程/API/云部署/GPU训练未运行。主模型运行配置由平台控制，不能据用户偏好宣称已切换；并行研究使用获授权的6 Luna Max，没有升级XHigh。



## root_research.md

# 主线研究记录（整合到RESEARCH_LOG）

本轮日期2026-10-03；用户时区Asia/Shanghai。主模型不能由工具自行切换，平台实际配置不伪称6.1 Sol High。并行资料研究实际使用5个GPT-6 Luna Max子代理（全栈、云、Workflow/Browser/Eval/RL、Hello逐章、RAG）；未升级XHigh。未修改StudyPlan仓库、未提交、未发布Seed、未运行付费模型API。

## 路由与检索

先读取用户附件全文，采用当前原文的范围。公共资料用web获取仓库身份与官方文档；Hello-Agents/All-in-RAG/LCC/Pi在独立research目录浅clone，用当地正文与代码核对，不运行其模型任务。clone用于读教材证据，不是StudyPlan产品功能，不意味着要求学员长期锁版本。

## 正文审读与判断证据

LCC：README新版17章及旧12章映射。根目录中文s01–s09全文读取；s10任务数据/依赖/claim/complete，s11后台状态/收集/生命周期，s13任务板/消息/审批/worktree，s14动态工具池/mock，s15集成，s16语义journal/resume，s17Goal判断器和出口相关正文。s12定时正文部分读取。综合等级selected_sections_read，不能标全仓deep_reviewed。

代码：s02工具实现与循环入口；s04权限hook前180行；s08压缩/摘要/prepare与实际loop末段；s01/02/03/04/08/09/10/11/14/15/16/17函数/类型定义索引仅用于定位，不算正文深读。未做安装与API运行。

Pi：coding-agent docs文件全目录；SDK全文、security全文、containerization全文、sessions全文；extensions前220行包括lifecycle/events/tools/exposure/嵌套调用、MCP相关正文；SDK01-minimal、05-tools正文。未读全部session-manager源码、未运行TS例子。selected_sections_read。

OpenHands：Getting Started正文及29行agent/conversation示例；Security/Persistence/Docker Sandbox已打开但本轮主代理未正文完整核读，按toc_checked子项处理。其官方示例可执行性未运行验证。SDK及tools包应配套版本；此为官方入门提示，安装不强制使用latest。

ZCode：查询发现Softorize（Zig）、zerx-lab（oh-my-pi下游）和prodigeproject等多个名称。prodigeproject页面DisabledError。仅用直接官方仓库README身份判断，不引用新闻/Reddit allegations；附件未给URL，保留歧义，不选作Primary，不凭名称拼接架构。

FastAPI full-stack template：直接官方仓库README核查身份和技术栈，项目研究卡仅制定学习目标，不断言源码实现细节已验证。browser-use/RAGFlow/WeKnora的官方仓库身份核查；细读范围由专项日志列出。

## 重要修订

1. LCC新版章节号必须改；教材各章有分支kernel，不能称每章都累加全部特性。
2. s14是mock工具发现/调用，不是实际transport。Hello ch10与之为COMPARE。
3. deny list/cwd/worktree不足以形成安全隔离；权限、进程清理和OS边界分别教授。
4. s02只替换第一个old_text；要加入歧义编辑与diff验证练习。
5. s04README权限片段比当前实际代码简化，学习时动态核验。
6. s15工具数量26/25存在正文不一致；编排不固化工具总数。
7. s16缓存续跑不自动提供任意副作用exactly-once。
8. s17独立判断器没有工具，只能读记录；需要真实测试证据。

## 访问/运行边界

公共GitHub下载可用；最初clone需要等待，随后成功。OpenHands猜测路径workspaces/docker不可访问，改为官方页面内链接agent-server/docker-sandbox；不把失败URL推荐给学员。所有教材/第三方工程测试NOT RUN；本轮只验证交付文件完整性、JSON与包内一致性。运行时模型/SDK稳定性未实测，不能承诺两年不变。

## 主线可复查URL

- https://github.com/datawhalechina/hello-agents
- https://github.com/datawhalechina/all-in-rag
- https://github.com/shareAI-lab/learn-claude-code
- https://github.com/earendil-works/pi
- https://pi.dev/docs/latest/sdk
- https://pi.dev/docs/latest/extensions
- https://docs.openhands.dev/sdk/getting-started
- https://docs.openhands.dev/sdk/guides/security
- https://docs.openhands.dev/sdk/guides/convo-persistence
- https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox
- https://github.com/Softorize/zcode
- https://github.com/zerx-lab/zcode
- https://github.com/fastapi/full-stack-fastapi-template

补充前置：Python官方中文教程已读controlflow 4.1/4.2/4.8/4.9.1、datastructures 5.5/5.6、inputoutput 7.2/7.2.2、errors 8.2/8.3相关正文及例子；全章节导航核查。5.1列表正文未完整读，目录已核查。selected_sections_read，NOT RUN。用作即时补课，不要求全书前置。官方/3链接是版本浮动入口，学习时选择已有兼容稳定解释器。


## 汇总复核补充

主审重新搜索并核对OpenAI官方Working with evals与Evaluation best practices的当前正文摘要，确认截至2026-10-03的2026-10-31只读、2026-11-30计划关闭提示。引用来源：https://developers.openai.com/api/docs/guides/evals 。此处只复核平台时间提示，不提升整站阅读深度，也未调用Evals API。

对专项Workflow/Browser阶段表、Evaluation/RL路径、全栈/云深审、Hello逐章记录进行了合并审阅；跨文件差异按分节而不是简单章级标签协调。


## rag_research.md

# Knowledge / RAG 专项深审与教学编排

研究快照：2026-10-03。All-in-RAG 的本地审读以 `main` 分支 `cec956e80ae28d6c0ca84c9d39dddcf61ad633fd` 为准；RAGFlow、WeKnora 和补充官方文档按当日公开页面复核。本文用于学习规划，不修改上游仓库、不运行示例/容器/模型/评测或任何付费 API，也不声称复现了质量、延迟或成本结果。

## 核心结论

All-in-RAG 适合作为系统 RAG 的主教学线：它从文档准备、切块、Embedding/索引、稀疏与稠密检索、查询处理、上下文生成走到评估和项目集成。Hello-Agents 第8章先让学习者看懂“Agent 如何调用 RAG”，第9章则讨论如何选择和组织模型本轮可见的全部上下文。两章都不替代 RAG 的工程质量闭环。

教学应把检索质量评估提早建立：先保留固定的小型问题集和单路基线，再根据坏例引入 BM25、dense、融合、改写、rerank 或更大的上下文。RRF 是多个检索列表的 rank fusion，不是 Cross-Encoder 这类 reranker。Weighted fusion 使用原始分数时必须先检查分数尺度并在同一验证集调权。

有两个术语与目录问题需要明确纠正。第一，All-in-RAG 第4章混合检索代码调用 BGE-M3 产生的 dense 与 learned sparse 表示；它没有在该示例里运行 BM25。BGE-M3 learned sparse 与 BM25 都属于词法/稀疏检索路径，但不是同一种打分算法。第二，第7章已有 Agentic RAG 教程及配套代码，在线 sidebar 已列出，但根 README、`docs/README.md` 和对应英文 README 的章节清单仍只列 GraphRAG。

引用是课程目前的主要缺口。已检查的 All-in-RAG 第1–6、8章会提到来源元数据、页码和回答生成，但没有形成稳定的 source/chunk/page 映射、逐句 citation contract、引用支持度与不可回答问题拒答的回归检查。应补官方引用资料，把“格式上有引用”与“引用确实支持该事实”分开检验。

## 推荐学习顺序与章节职责

| 阶段 | 教学入口 | 章节级内容与实践 | 对 Hello-Agents 的关系 | 持续“研究与行动助手”增量与退出条件 |
|---|---|---|---|---|
| 0. RAG 在 Agent 中的位置 | Hello-Agents 第8章 §8.3、§8.4；All-in-RAG 第1章 | 只回顾 RAG 解决什么问题与最小数据流：导入→切块→索引→检索→构造上下文→回答。第1章用来统一词汇，不重复做长篇概念课。 | RAG 概念、Agent 调用入口为 **REVIEW**。 | 画出数据写入和查询两条路径；能指出解析、切块、索引、检索、生成各自可能失败的位置。 |
| 1. 入库、解析、切块 | All-in-RAG 第2章 `04_data_load`、`05_text_chunking`；第8章 `02_data_preparation` | 比较加载器的输入输出、固定/递归/Markdown/语义切块；第8章再看父子块如何让小块用于检索、较大上下文用于生成。用 6–10 段虚构 Markdown 检查标题、表格、边界、来源 ID、页/段位置和坏切块。 | MarkItDown 和基础 chunking **REVIEW**；保真、metadata/provenance、父子块 **DEEPEN**。 | 加入单份 Markdown/纯文本的导入与 chunk preview。退出条件：每块可定位回原始文档；指出并修复至少一个边界问题。第2章对 loader 明确偏简，不能当成生产 OCR/表格解析课程。 |
| 2. Embedding、向量库与索引 | All-in-RAG 第3章 `06_vector_embedding`、`08_vector_db`；按需 `07_multimodal_embedding`、`09_milvus`、`10_index_optimization` | 先看文本向量和存取契约，再了解向量库、metadata/句子窗口。只有资料含图表/图片时读多模态；初学不部署 Milvus 集群。 | Hello-Agents 的 Embedding/Qdrant **REVIEW**；同一模型/维度/元数据规则和 chunk ID 可追溯 **DEEPEN**；多模态为 **NEW/按目标**。 | 保存稳定 chunk/source ID、模型名称/版本、维度和元数据。退出条件：索引条目能回到原文 chunk；索引模型与查询模型匹配。 |
| 3. 建检索 baseline 并读评测 | All-in-RAG 第4章 `11_hybrid_search` 的基本 BM25/dense 对照；第6章 `18_system_evaluation` | 用可回答、不可回答、精确术语、语义改写、跨段问题建立手工审核集；先分别跑 lexical/BM25 与 dense，记录 top-k、相关块、Recall@k/MRR 和失败类别。学会传统 IR 指标与 Ragas 指标字段的区别。 | Hello-Agents 没有成体系的 retrieval/answer eval，属于 **NEW**。MQE/HyDE 先留作后续比较。 | 加离线测试集、配置快照和 bad-case 记录。退出条件：能复现同一 baseline，并区分解析缺失、未召回、排名差和答案错误。Precision@k/Recall@k 与 Ragas ContextPrecision/ContextRecall 名称相近但不是同一计算口径。 |
| 4. Hybrid、融合与查询变换 | All-in-RAG 第4章 `11_hybrid_search`、`12_query_construction`、`14_query_rewriting`；第8章 `03_index_retrieval` | 第4章示例是 BGE-M3 learned sparse+dense+RRF；第8章项目则明确用 BM25Retriever+FAISS dense+手写 RRF。比较 BM25、dense、RRF、weighted fusion；再按坏例比较 metadata filter、MQE、HyDE、step-back、rewrite 或 route。每轮只变一个因素。Text2SQL 只在结构化查询场景选读。 | MQE/HyDE **REVIEW + COMPARE**：Hello-Agents 已介绍并实践过；BM25/dense hybrid、RRF、查询路由和结构化评估 **NEW/DEEPEN**。 | 显示各分路命中块与最终顺序。退出条件：解释每种方法改善的是哪类失败，且没有把“平均改善”推断成全部问题都变好。 |
| 5. Rerank、上下文和回答 | All-in-RAG 第4章 `15_advanced_retrieval_techniques`、第5章 `16_formatted_generation`、第8章 `04_generation_sys` | 正确块已进入候选但排位差时再测试 Cross-Encoder/其他 reranker；之后看压缩、父块展开、去重、context 长度和响应合成。用固定模板检查证据、source ID 和拒答，不需要生成 API。 | 把检索结果交给 Agent 为 **REVIEW**；父子上下文、上下文去重、证据绑定与 citation/拒答为 **DEEPEN/NEW**。 | 只把真实命中块传给回答层，输出答案、证据 ID、原文位置；没有支持材料时明确回答资料不足。退出条件：每条实质性陈述都能定位到原文，不存在或不支持的引用会被测试发现。 |
| 6. 集成与回归 | All-in-RAG 第8章 `01_env_architecture` 至 `04_generation_sys`；第6章 `19_common_tools` 按需 | 将 data preparation、embedding、BM25/dense、RRF、route/rewrite、父子块和生成连起来；随后用同一测试集回归检索和回答。Ragas、LlamaIndex、Phoenix 先读 schema/指标和适用范围，API 按学习时官方文档确认。 | RAGTool 到完整知识问答系统是 **DEEPEN**；本阶段不再重复 Hello-Agents PDF 助手的搭建。 | 形成端到端的离线版本，记录每个配置和坏例变化。退出条件：失败有可定位的阶段、修改能复测、有引用和拒答检查。教程第8章示例需要 `MOONSHOT_API_KEY`；阅读免费不等于运行免费。 |
| 7. 可选 Agentic RAG / GraphRAG | All-in-RAG 第7章 `21_agentic_rag`；图需求触发时看 `20_kg_rag` 与第9章 | 先有评测过的固定检索 baseline，再看 Agent 何时多轮规划、调用检索、评估充分性并改写；设置最大轮次、失败输出、日志与成本观测。GraphRAG 只有在跨实体、多跳关系存在可测缺口时引入。 | Hello-Agents 第9章的 JIT/context retrieval 是邻接概念，不等同于这个多轮知识检索决策循环。 | 只拿一个 baseline 失败的复杂问题比较静态 RAG 与 Agentic RAG，记录实际轮数、检索结果、答案证据、token/延迟；未测量前不写“提升率”。 |

### 查询/排序术语的准确边界

| 方法 | 用途 | 本次章节核查结论 |
|---|---|---|
| BM25 | 由语料统计和查询词匹配对文档排序；擅长精确词项、编号、名称 | 第8章 `03_index_retrieval` 明确配置 BM25Retriever。 |
| BGE-M3 learned sparse | 模型学习得到稀疏 token 权重表示，可做 sparse lexical retrieval | 第4章 `11_hybrid_search` 调用 BGE-M3 sparse 输出；官方模型卡称 token weights 与 BM25 类似，但同时单独比较 BM25。不要教成“BGE-M3 就是 BM25”。 |
| Dense retrieval | 用文本向量相似性找到语义相关块 | 第3章 Embedding、向量库及第8章 FAISS 项目。 |
| RRF | 按文档在多个检索结果列表的排名融合，不要求分数同尺度 | 是 hybrid 融合方法，不是 Cross-Encoder，也不是语义 reranker。课程有 RRF 公式和实现。 |
| Weighted fusion | 按权重融合多路分数 | 教材说明需分数归一化，Milvus 部分提到 `WeightedRanker`；要用固定验证集检查分数可比性、调权和分段效果。 |
| Reranker | 对已经召回的候选按 query-document 相关性重新排序 | 只在正确候选已召回但排位不理想时尝试；有计算/服务延迟。第4章 advanced retrieval 讨论 cross-encoder/ColBERT/LLM 排序。 |
| MQE / HyDE / rewrite | 扩展或转换查询以改善候选召回 | MQE/HyDE 与 Hello-Agents 已有内容做复习、比较；HyDE 的假设性文本只用于检索查询向量，不当作事实来源。 |

第4章 `11_hybrid_search` 的代码注释把 BGE-M3 sparse 说成“词频统计”，与模型学习的 sparse token weights 不完全相同；该节教学最好把传统 BM25 与 learned sparse 明确分开。该节主要运行的是 RRF，而 weighted linear fusion 主要停留在概念说明。第8章 `03_index_retrieval` 才是 BM25+dense+RRF 的完整显式示例。当前小规模示例输出不能说明哪一种方法在真实研究语料上更优。

## Hello-Agents 第8/9章重叠分类

| Hello-Agents 内容 | 分类 | 在 RAG 专项中的处理 |
|---|---|---|
| 第8章 §8.3.1 RAG 基础与 Agent 中的 RAG 入口 | REVIEW | 快速复述 RAG 为什么是 Agent 的工具/知识来源，不再重复完整导论。 |
| 第8章 MarkItDown、切块、Embedding、Qdrant、PDF 学习助手 | REVIEW → DEEPEN | 保留已有纵切面；在 All-in-RAG 深化 chunk/provenance、BM25/dense、检索测试和集成。 |
| 第8章 MQE、HyDE 代码与结果合并 | REVIEW + COMPARE | 不重抄实现；用同一问题集跟原查询/BM25/dense/hybrid 比，记录效果和额外调用。已查看范围的合并去重不等于 RRF 或独立 reranker。 |
| 第8章 BM25 hybrid、RRF、reranker、citation validity、RAG eval | NEW | 已检查的章节正文与助手代码范围没有建立这些系统实践。 |
| 第9章 Context Engineering 的 context budget、GSSC、历史/工具/记忆筛选 | DEEPEN（邻接主题） | 讲模型每次调用可见的完整信息如何 Gather/Select/Structure/Compress；检索块只是其中一种来源。 |
| 第9章 JIT retrieval / TerminalTool 文件系统浏览 | COMPARE（相邻概念） | 说明运行时按需加载 context 的思路；它不是知识库文档 parser、BM25/dense index 或 RAG 检索评测的替代课程。 |
| 每条回答的引用来源、claim 支持关系与拒答测试 | NEW / 补充 | 两章都不能代替 source ID→chunk→文件页段的引用数据契约和验证集。 |

## README 目录不同步与第7章 Agentic RAG 审查

本地目录里存在 `docs/chapter7/21_agentic_rag.md`、`code/C7/agentic_rag/README.md`、`demo.py`、`agent.py`。`docs/_sidebar.md` 已把 Agentic RAG 列为第7章第二节；根 `README.md`、`docs/README.md`、`README_en.md` 和 `docs/en/README.md` 的第7章章节清单仍只列 `20_kg_rag`。因此课程正文/在线导航比 README 内容清单多一节，需要 StudyPlan 使用正文和导航作为当前内容证据，并把目录遗漏记为维护缺口。

新章节自称要求读者已掌握第1–4章检索基础并了解第6章评估，因此安排在传统 RAG 质量闭环之后更合理。它把静态单次检索升级为 Plan→Retrieve→Critique→Refine 循环，作为 Agentic RAG 的概念入口可以保留。代码示例使用硬编码小语料、OpenAI `gpt-4o`，可选 Tavily；运行并非零费用。

有两项不能未经核查就拿来教学：

- 章节里的比较表列出 Context Recall、Faithfulness、Answer Relevance、延迟和 token 消耗的数值，但 `demo.py` 实际只输出检索轮数、收集文档数和答案长度，没有实现这些质量指标、延迟或 token 的计算，也没有展示标注集与测量记录。应标成“未验证示例数字”或补一套可复现评估，不能当作 Agentic RAG 的普遍收益证据。
- `agent.py` 的 `_should_continue` 在达到 `max_iterations` 后返回 `max_iter`，而状态图把 `max_iter` 映射到 `END`；这条路径不会经过 `_generate`。正文称达到上限时“强制生成答案”，实现与说明冲突，需以运行测试/修正后的代码确认终止时用户会收到什么。

这意味着 Agentic RAG 适合做一个受控比较实验，不宜直接加入初学者主线、也不应作为提升质量的默认方案。必须记录轮数、最终依据、空结果/工具失败、延迟和 token；若没有信息就应输出“不足以回答”，不能因迭代次数已用完而强行生成。

## 分阶段完成“研究与行动助手”

保持一个很小的虚构研究语料，让每个功能都能映射到固定问题与源片段：

1. **V0 来源可追溯**：仅 Markdown/纯文本导入；保存文档 ID、标题、顺序、页/段位置；展示 chunk preview 与解析失败。
2. **V1 词法检索**：用本地 BM25 检索，展示 top-k、分数、原文 ID；暂时只展示证据，不承诺自然语言回答。
3. **V2 dense / 可替换检索器**：如本机已具备模型再增加 dense；记录模型、维度和索引版本，不为教程下载模型或调用付费 API。
4. **V3 hybrid**：分别运行 BM25、dense、可选 BGE-M3 learned sparse；比较 RRF 与经过校验的 weighted fusion；把各通道候选保留下来用于坏例诊断。
5. **V4 排序与上下文**：正确证据已被召回但排名不足时才测 rerank；然后尝试父块展开、去重、长度控制。
6. **V5 答案、引用和拒答**：答案只能根据本轮真实检索块生成；引用映射到文件/页/段；不可回答问题必须触发拒答。
7. **V6 评测闭环**：保存测试集版本、配置、检索/回答指标和人工审核坏例；每轮只改变一个变量。所有 LLM judge 结果保留人工抽查。
8. **V7 条件性 Agentic RAG**：只有多跳/多源问题在 V6 留有可复现缺口时才加 Agent 循环，并测收益是否超过延迟、token 与故障复杂度。

小语料可验证输入输出契约、来源映射和该条件下的相对效果；不能证明生产质量、商业模型等价、线上延迟/可用性或成本节省。

## 进入生产项目学习/试用的门槛

满足下列条件再选 RAGFlow 或 WeKnora 的一个项目切片；学习项目不要求先部署整套系统。

- 能画清 parsing→chunk/provenance→embedding/index→BM25/dense→fusion/rerank→context→answer/citation 的数据流；区分设计、当前实现和已验证结果。
- 有一套人工检查过、包含可回答与不可回答样本的测试集；能复现 baseline 与至少一个坏例修复，按查询类型检查 Recall@k/MRR、答案支持性和拒答。
- 引用 ID 能回到当前检索结果和原文件位置；引用不存在、跨轮漂移或不支持 claim 均有检查；检索结果无证据时有拒答策略。
- 入库有可观察状态、错误/重试/幂等约定；文档更新/删除、解析器或 Embedding 版本变化不会悄悄留下旧索引。
- 对生产级质量作判断前，在目标数据和权限配置上测量延迟、吞吐、模型调用/token/费用、失败率、索引恢复，并设质量回归门槛。检索时必须按用户/知识库做访问过滤，处理文档提示注入与敏感信息隔离。

## 两个成熟项目的当前官方学习卡

### RAGFlow

截至本快照，官方 releases 标记 `v1.0.0-rc1` 于 2026-09-29 发布，是全面 Go rewrite 的预览版；保留它用于阅读当前架构和文档，不把 RC 设为默认练习版本。官方 `v0.27.2` Quickstart 在本次核查时标为 Stable。若后续要动手，应在当时重新确认官方稳定 tag，并核对该版本的操作系统、Docker/数据库、模型服务与 SDK/API 兼容要求；也可改选 WeKnora。本文未安装、运行或验收任一版本。RC Quickstart 提到的 4 CPU、16 GB RAM、50 GB 空闲磁盘仅作该版本部署资源参考，不是初学者的必备条件。

推荐 3–5 个切片：

1. README/release notes：确定学习时的架构和版本背景，识别旧版 Python 教程的失效边界；RC 只读作版本背景。
2. 一个文档从上传、解析、chunk 到 provenance 的路径；只选目标文件类型，不逐个审所有 parser。
3. 对固定问题使用 Retrieval Testing 检查目标 chunk、排名、噪声、metadata filter 和 Top/threshold。
4. 只在候选已召回但排名差时对比 rerank；注意 Retrieval Testing 的参数改动不会自动应用于实际 Chat/Agent。
5. 跟踪一次 answer 的 citation marker/source ID 到原文；citation prompt 只规定模型输出格式，不证明引用事实正确。

官方资料：[当前 GitHub/发行说明](https://github.com/infiniflow/ragflow/releases)、[v0.27.2 Stable Quickstart（本次核查时）](https://ragflow.io/docs/v0.27.2/)、[v1.0.0-rc1 Quickstart](https://ragflow.io/docs/v1.0.0-rc1/)、[Retrieval Testing](https://ragflow.io/docs/v1.0.0-rc1/retrieval_testing)、[FAQ](https://ragflow.io/docs/v1.0.0-rc1/faq)、[citation prompt](https://github.com/infiniflow/ragflow/blob/main/rag/prompts/citation_prompt.md)。选定练习版本后，应按该版本的官方文档重新核对兼容性；研究快照不构成部署验收。

### WeKnora

官方 README 当前标 `v0.8.2`（2026-09-24）。项目范围同时含 RAG、Agent、Wiki、MCP、连接器、模型和多种存储；学习时只跟一条文档处理/检索/引用纵切片。官方 README 列出 keyword+vector hybrid、rerank、parent-child chunking 与 evaluation 等 RAG 能力。

推荐 3–6 个切片：

1. 当前 README 和 architecture overview：看服务和能力边界，不扫全部模块。
2. 上传一份文档到异步 ingestion，追踪解析、chunk/provenance、索引完成状态与失败重试。
3. 用官方 raw chunks/search 入口检查 keyword/vector 通道、结果 ID、`knowledge_id`、`chunk_index`、分数和 `match_type`。
4. 从 Chat/API 的 `references` 事件追踪 `knowledge_references` 回到来源，不只检查 answer 文本。
5. 如需学习评测，再读 evaluation 的数据契约和异步任务。`RetrievalIDs` 必须和数据集 passage ID 对齐；`chunk_index` 是库内分块序号，不能直接代替评测 passage ID，否则检索指标会恒为 0。
6. 只在真实目标需要时看父子块、GraphRAG 或 Web/Agent 工具，不把它们设成普通 RAG 前置。

官方资料：[当前仓库/README](https://github.com/Tencent/WeKnora)、[Release 页面](https://github.com/Tencent/WeKnora/releases)、[API overview](https://github.com/Tencent/WeKnora/blob/main/website-docs/04-api/01-api-overview.md)、[evaluation](https://github.com/Tencent/WeKnora/blob/main/website-docs/03-features/15-evaluation.md)、[hybrid search chunks](https://github.com/Tencent/WeKnora/blob/main/cli/skills/weknora-rag-search/references/search-chunks.md)。文档/API 当前变化较快，下一次源码学习先重读版本和当前文档，不固定文件/函数名。

## 建议补充的官方引用资料

- [Microsoft Foundry: RAG and indexes](https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation)：说明来源标题、URL、文件名等 index 字段有助于引用质量，并提醒权限控制与 retrieved content 的安全边界。
- [Cohere: RAG citations](https://docs.cohere.com/docs/rag-citations)：展示 answer span 的 start/end、引用文本和 document IDs，可作为结构化 citation 设计示例；在线执行不是课程必需。
- [RAGFlow citation prompt](https://github.com/infiniflow/ragflow/blob/main/rag/prompts/citation_prompt.md)：作为引用输出格式参考，需搭配来源映射和 correctness 检查。
- [WeKnora API overview](https://github.com/Tencent/WeKnora/blob/main/website-docs/04-api/01-api-overview.md)：将 `references` 事件和 `knowledge_references` 作为真实项目 API 数据结构案例。

## 主要本地审读入口

- [All-in-RAG 中文 README](https://github.com/datawhalechina/all-in-rag/blob/main/README.md)、[docs README](https://github.com/datawhalechina/all-in-rag/blob/main/docs/README.md)、[sidebar](https://github.com/datawhalechina/all-in-rag/blob/main/docs/_sidebar.md)
- [All-in-RAG 第2章数据加载](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter2/04_data_load.md)、[切块](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter2/05_text_chunking.md)
- [All-in-RAG 第4章混合检索](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter4/11_hybrid_search.md)、[query rewriting](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter4/14_query_rewriting.md)、[advanced retrieval](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter4/15_advanced_retrieval_techniques.md)
- [All-in-RAG 第6章评估](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter6/18_system_evaluation.md)、[第8章检索](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter8/03_index_retrieval.md)、[第8章生成集成](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter8/04_generation_sys.md)
- [Hello-Agents 第8章记忆与检索](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/Chapter8-Memory-and-Retrieval.md)、[第9章上下文工程](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter9/Chapter9-Context-Engineering.md)


## special_research.md

# Agent 专项研究记录

研究快照：2026-10-03。范围包括 Workflow / Automation、Browser / Computer-use、Evaluation 与可选 Agentic RL。此文记录公开官方正文、示例和项目入口的选读范围，用于解释四份路线的编排选择；不是完整文档或代码库审计。

本轮只做静态阅读与目录/示例检查：没有运行教程代码、安装依赖、启动浏览器、调用模型、训练参数、租用算力或部署服务。路线中的小实践均为教学设计，不能当作已经验证的实验结果。资源表的 `review_depth` 采用保守口径：具体读过的章节和示例记为 `selected_sections_read`；仅查项目介绍的 MaxKB 记为 `metadata_only`。本次不使用 `deep_reviewed` 标签，避免将选读正文、页面抓取或静态代码阅读夸大为深审。

## Workflow / Automation

| 资源 | 实际核对范围 | 路线用法与边界 |
|---|---|---|
| [Hello-Agents 在线教材](https://github.com/datawhalechina/hello-agents) | 第4章 ReAct/Plan-and-Solve/Reflection；第5章 Dify 与 n8n 初览；第6章框架抽象、AgentScope、LangGraph StateGraph 及 Understand→Search→Answer 示例；第7章工具注册、异步执行、会话分支/回滚；第8章仅作 RAG 先后关系。 | 把 ch4 loop、ch6 图和 ch7 工具作为 REVIEW 起点；第6章练习触及条件重试，但没有系统教授持久 checkpoint、跨进程恢复、审批审计或外部副作用幂等。会话回滚不能等同于运行时持久化。 |
| [LangGraph Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) 与 [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) | 核对 prompt chaining、parallelization、routing、orchestrator-worker、evaluator-optimizer、agent 图模式；读 state/node、按错误类型处理、retry、timeout、human review 与 Saga/补偿相关正文和示例。 | 选择 LangGraph Python Graph API 作为代码主线。先固定流程/显式 state，再学有界分支与 loop、错误分类与恢复；动态多 Agent 只在项目指标需要时出现。部分 API 与版本相关，学习时回查稳定文档。 |
| [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) | state schema、reducer、node/edge、conditional routing、loop/recursion limit 等选读章节。 | 把并行写 state 时 reducer 的责任与 loop 上限列为退出条件；不把 compile/invoke 当作持久存储。 |
| [LangGraph Persistence / Checkpointers](https://docs.langchain.com/oss/python/langgraph/persistence) | 核对 checkpointer 与 Store 的边界、thread ID、InMemorySaver/SQLite/Postgres、checkpoint/replay 与 durability 相关正文和示例。 | thread 内的 graph checkpoint 用于运行恢复；跨 thread Store 是另一个应用数据面。InMemorySaver 不能证明进程重启后的持久恢复。回放可能重新运行外部调用，不能宣称 exactly-once。 |
| [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | 核对 checkpointer 与稳定 thread_id 的要求、`interrupt()` / `Command(resume=...)`，审批/编辑/拒绝样例，以及 resume 从所在节点开头重跑的限制。 | 将 HITL 放在 checkpoint 基础之后。interrupt 前副作用必须可幂等、移到之后或拆分；审批数据还需由业务应用留存对象版本、决定、审批者和幂等标识。 |
| [LangGraph Agent Server](https://docs.langchain.com/langsmith/agent-server) 与 [data plane](https://docs.langchain.com/langsmith/data-plane) | 选读当前 threads/runs、后台任务与服务组件的入口/资源说明。 | 仅在需要后台 run、多用户 API、取消或部署时作为高级支线；托管功能与费用学习时重核。本轮未部署。 |
| [AgentScope 官方仓库](https://github.com/agentscope-ai/agentscope) 与 [FAQ/迁移线索](https://agentscope.io/blog/agentscope-faq/)；[旧版 pipeline 教程](https://doc.agentscope.io/tutorial/task_pipeline.html) | 查当前 2.x 仓库/NEWS/FAQ 的 breaking-change 与迁移线索，选读公开 v1 pipeline、handoff/concurrent 流程页。 | 仅在目标需要 message-driven team/runtime 时比较；不能把旧 v1 MsgHub、pipeline 示例当成 v2 当前代码。公开教程版本断层记 `VERSION_CONTEXT`。 |
| [Dify Quick Start](https://docs.dify.ai/en/quick-start)、[FastGPT workflow 文档](https://doc.fastgpt.cn/en/guide/build/workflow/intro)、[MaxKB 仓库](https://github.com/1Panel-dev/MaxKB) | Dify 快速开始的 workflow/node 例子；FastGPT workflow/loop/user-selection 示例；MaxKB 本轮只看项目简介及 release。 | 只有目标平台已确定时，Dify 或 FastGPT 才升为 Primary；其余用于视觉流程对照。MaxKB 只保留候选，明确标为 metadata-only，不推断它的教学或可靠性能力。托管平台/模型/云资源可能另收费。 |

## Browser / Computer-use

| 资源 | 实际核对范围 | 路线用法与边界 |
|---|---|---|
| [Playwright Python 文档](https://playwright.dev/python/docs/intro) | Intro、Writing tests、Locators、Actionability、Input、Navigations、Pages、Authentication、Trace Viewer；并按目录定位 network、frames 等可选专题。核对角色/名称定位、自动等待、web-first assertion、context 隔离和 trace 内容。 | 先用 Playwright 建确定性 baseline：语义 locator、wait、输入、断言、tab/context 与失败诊断。Auto-wait 只证明动作可执行，不证明业务事务完成；storage state 是敏感凭据。 |
| [Browser Use 开源 quickstart](https://docs.browser-use.com/open-source/quickstart)、[Agent 参数](https://docs.browser-use.com/open-source/customize/agent/all-parameters)、[Browser 参数](https://docs.browser-use.com/open-source/customize/browser/all-parameters)、[tools](https://docs.browser-use.com/open-source/customize/tools/add)、[sensitive-data](https://docs.browser-use.com/open-source/examples/templates/sensitive-data) | 核对 Python 开源库 quickstart、Agent/Browser 配置、custom tool、人机介入、domain allowlist、action/failure/time budget、storage state 与敏感信息章节；只读当前项目指引与相关示例，不通读整个源码库。 | Playwright 后再引入 LLM observe/act/re-observe 循环。先用本地或明确允许的假站只读任务，设置域名范围、步数和超时；凭据不进入模型输入，截图日志也需按敏感数据处理。模型 API/云浏览器可能收费。 |
| [Hello-Agents Extra 11](https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra11-WebAgent%E7%A7%91%E6%99%AE%E4%B8%8E%E5%AE%9E%E6%88%98.md) | 选读 Web Agent 与 RPA/GUI 区分、DOM/AX tree/screenshot 感知和动作循环；检查 TinyFish 托管示例及其登录/API key、stealth/proxy/anti-bot 内容。 | 只用于概念 REVIEW/COMPARE；不把 hosted provider 或绕过站点限制纳入练习。行业成功率等未经本轮独立验证的宣传陈述不作为事实。 |
| [browser-use 当前仓库](https://github.com/browser-use/browser-use) 与 [项目操作说明](https://github.com/browser-use/browser-use/tree/main/skills) | 核对当前 repo README/目录、开源 quickstart/Agent、Browser、Examples/Sensitive-data 相关引用和 system prompt 的观察/动作规则；检查源码/测试入口，未完整阅读约 4k 行 agent service 文件或运行 tests。 | 项目学习采用动态目录地图后挑 3–8 个代码/测试切片。成功由 DOM、URL、假后端或任务 oracle 独立判定，不只信 `is_successful` 或 final answer。 |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym) 与 [WebArena 论文页](https://proceedings.iclr.cc/paper_files/paper/2024/hash/4410c0711e9154a7a2d26f9b3816d1ef-Abstract-Conference.html) | 查基准/论文入口，未运行基准。 | 仅作为较后面的 benchmark 选读；先在本地小任务上建立可验证状态 oracle。旧版页面与仓库活跃度需按学习当日核验。 |

## Evaluation

| 资源 | 实际核对范围 | 路线用法与边界 |
|---|---|---|
| [Hello-Agents 第12章](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter12) | 选读 BFCL/GAIA、tool call categories、LLM judge/win rate/human scoring、边界样本/练习正文。 | 能力初次出现时 REVIEW；DEEPEN 为自建小型任务数据集、轨迹/安全/恢复评分与持续回归。不将大基准排名当成学习者首个 eval。 |
| [LangSmith Evaluation types](https://docs.langchain.com/langsmith/evaluation-types) | offline/online、unit/regression/benchmark/pairwise 与 code/LLM/composite evaluator 所选正文。 | 作为评估对象、时机、评分法的分类材料；实际最早练习仍可用本机 JSONL 和确定性 grader，不需先建云平台账户。 |
| [LangSmith Evaluate a complex agent](https://docs.langchain.com/langsmith/evaluate-complex-agent) | SQLite/路由示例和 Final response / Single step / Trajectory evaluator 的正文/代码。 | 用同一业务任务对照最终结果、单步行为、完整轨迹；示例退款/音乐商店不搬入持续项目，生产鉴权/副作用需自行设计。 |
| [AgentEvals](https://github.com/langchain-ai/agentevals) | README 中 strict、unordered、subset/superset trajectory matching、tool-args 与 judge 示例。 | 用于说明多种合法路径与约束评分；组件 README 不是完整评估入门，strict matching 只适合顺序本身是业务要求的任务。 |
| [OpenAI Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals) | 查 trace 涵盖模型/工具/guardrail/handoff 的说明，先单条调试、再转可重复 datasets/eval runs 的顺序。 | 用作概念补充，支持 Eval-Lite 早于高级专项；不要求绑定平台实现。 |
| [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | 选读 metric-based、人类评价、LLM judge、位置/冗长偏差与 edge-case 覆盖建议。 | 先规则和环境 oracle，LLM judge 仅在确有语义评分缺口时加入，并用人工样本校准；输出质量评分不能代替 workflow/browser 的真实状态检查。 |
| [OpenAI Working with evals](https://developers.openai.com/api/docs/guides/evals) | 核对 task→test inputs→analyze/iterate 概述、Datasets 推荐和 deprecation notice。 | 截至 2026-10-03 官方注明 Evals 现有用户将在 2026-10-31 起只读，平台计划 2026-11-30 关闭。因此只作流程/版本边界材料，不把 Evals API 作为长期课程依赖；课程发布前重查官方 deprecations。 |
| [LangSmith RAG evaluation tutorial](https://docs.langchain.com/langsmith/evaluate-rag-tutorial) | 选读 dataset、correctness/relevance/groundedness/retrieval relevance grader 与示例。 | RAG 专项从首次检索就单独测 recall/relevance 与回答证据；模型 judge 相关性不能替代人工标注的检索 Recall@k/MRR/nDCG。 |

**阶段决定**：第一条工具调用之后立即做 Eval-Lite（少量案例、确定性 tool/args/outcome 检查）；完整的多轨迹/模型 judge 在采到真实轨迹后；领域评估跟随 RAG、Coding、Workflow、Browser 能力插入；只有训练分支才在 RL 前要求封存独立测试集。Eval-Lite 早于 RL。训练时奖励函数不能同时充当唯一最终 grader。

## 可选 Agentic RL

| 资源 | 实际核对范围 | 路线用法与边界 |
|---|---|---|
| [Hugging Face Deep RL Unit 1](https://huggingface.co/learn/deep-rl-course/en/unit1/rl-framework)、[Policy Gradient Unit 4](https://huggingface.co/learn/deep-rl-course/en/unit4/policy-gradient)、[PPO Unit 8](https://huggingface.co/learn/deep-rl-course/en/unit8/clipped-surrogate-objective) | state/observation/action/reward/return、policy-gradient 到 PPO clipped objective 的所选正文。 | 把 Unit 1 与工具 Agent 的 observation/action 对齐；Policy Gradient 仅补 PPO 直觉所需段落，不把整门游戏强化学习设成 Agent 入门前置。未运行课程 notebook。 |
| [Hugging Face LLM Course 第12章](https://huggingface.co/learn/llm-course/en/chapter12/2) | 选读后训练、GRPO 分组、配置、reward、LoRA 与练习代码。另核对 ch11/2–4 的 Chat Template/SFT/LoRA 前置。 | 作为 GRPO 概念连续线，附带版本/例子缺陷说明：示例拼写与当前接口存在差异，`len` 字符串不是 tokenizer token 数，模型说明与 ID 需核验。概念可读，不能声称即拷即跑。 |
| [TRL GRPO Trainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) | 当前目录、Tools/Environments/metrics 和选定配置/API。 | 当前文档有开发版与实验性内容；执行前对照 stable 文档/依赖版本。先做环境 reset/rollout/独立 reward 验证，算力与模型推理成本不作免费保证。 |
| [Agent Lightning stable docs](https://microsoft.github.io/agent-lightning/stable/) 与 [论文](https://arxiv.org/html/2508.03680v1) | 当前 Quick Start/Basics/Calc-X 与 rollout/controller 相关说明；论文所选架构和 credit-assignment 部分。 | 高级系统参考，quick start 的 Linux/A100 条件不是普通入门实验。`stable` 页面本身仍出现 development 提示，旧版 API 不与新页混用。未运行项目或复现实验。 |
| [DeepSeek-R1 paper](https://arxiv.org/html/2501.12948v1) | 核对 §2.2.1–2.3 对 GRPO、reward 与训练流程的引用/概述。DeepSeekMath 原始论文网页访问不完整。 | 用于校准 GRPO 的历史归属和终局奖励限制；不据论文报告外推目标应用性能，不宣称读完未访问全文。 |

路线分两层：应用开发者只需理解轨迹、state/action/reward、奖励可能被利用的例子，并在 Eval-Lite 与独立系统评测之后判断 RL 是否适用；不需训练参数。训练研究者才继续 SFT/LoRA 前置、PPO/GRPO、TRL 工具环境、受控训练和 train/validation/test 隔离。真正训练须说明硬件、预算、数据/模型版本及独立 grader；没有训练则记录为未训练。

## 证据边界和可复核要求

- `special_resources.json` 的字段 `actual_scope_reviewed` 仅描述本轮读过的章节、示例与页面；具体受审条目保守标为 `selected_sections_read`。MaxKB 仅 `metadata_only`。
- 搜索摘要只用于定位入口，不作为关键技术结论的唯一证据。OpenAI Evals 退役日期已于本轮从官方当前页面正文核对；之后课程使用时仍须重新核验。
- 教学章节中的练习步骤是编排者设计，均注明尚未执行；不把设计建议写成工具运行结果。
- 免费公开阅读与模型 API、云托管、数据库、Browser-use Cloud 或 GPU 成本分开说明。没有验证或承诺免费额度、基准表现、生产 SLA。
- 四份路线的内部资源/审计链接指向同目录的 `special_resources.json` 与本文件，方便审阅来源与限定范围。


## fullstack_research.md

# AI Fullstack 研究证据日志

研究日期：2026-10-03。只记录本轮实际打开并阅读的正文/示例范围。除特别注明外，`review_depth` 为 `selected_sections_read`；没有把目录/README 阅读写成全站深审。正文中资源 `url`、章节建议与限制也见 [`fullstack_resources.json`](RESOURCE_CATALOG_NORMALIZED_DRAFT.json)。

| 资源 | 访问链接 | 实际查看内容 / 深度 | 关键观察与用于路线的结论 |
|---|---|---|---|
| MDN JavaScript Scripting | [中文模块](https://developer.mozilla.org/zh-CN/docs/Learn_web_development/Core/Scripting)；[English canonical](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting) | 模块说明、课程目录；正文中网络请求/JSON、异步、Promise、表单提交/错误和调试示例；`selected_sections_read` | HTML/CSS 基础为前置；顺序由语言基础推进到 DOM/网络。async 部分假设稳固 JS。用于按缺口补课，不要求掌握者整套重学。``正文检索/打开 refs: `turn17view0`, `turn17view2`, `turn17view3-5`, `turn22view3`, `turn22view6`, `turn29view7-8`, `turn32view0-8`。 |
| MDN HTTP Overview | [Overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) | client/server、无状态/session、HTTP flow、消息结构、Fetch 与 SSE 段落；`selected_sections_read` | 浏览器发起请求；request 有 method/path/header/body，response 有 status/headers/body；SSE 是 HTTP 上服务器到客户端单向 event stream。Refs `turn115view0`。 |
| javascript.info | [教程目录](https://javascript.info/)；[Fetch](https://javascript.info/fetch)；[Promise chaining](https://javascript.info/promise-chaining)；[async/await](https://javascript.info/async-await)；[中文站](https://zh.javascript.info/) | 三部分目录及以上具体正文/代码；`selected_sections_read` | Fetch example 表明 HTTP 404/500 不会让 `fetch` Promise reject，需查看 `response.ok/status`；作为 MDN 缺口解释，避免两套全修。Refs `turn17view6-9`, `turn51view7`, `turn48search24`。 |
| Python Tutorial | [官方教程](https://docs.python.org/3/tutorial/)；[Control Flow](https://docs.python.org/3/tutorial/controlflow.html)；[Data Structures](https://docs.python.org/3/tutorial/datastructures.html)；[Errors](https://docs.python.org/3/tutorial/errors.html) | 官方范围说明/目录，以及控制流、数据结构和异常正文示例；`selected_sections_read` | 明确面向“懂编程、刚学 Python”的人，不适合零编程起点。只在 FastAPI 前按缺口读函数/list/dict/module/异常，不提前设置 Python 硬门槛。Refs `turn95view4-7`, `turn107view0-3`。 |
| React Learn 中文官方文档 | [Learn](https://zh-hans.react.dev/learn)、[Describing UI](https://zh-hans.react.dev/learn/describing-the-ui)、[Thinking in React](https://zh-hans.react.dev/learn/thinking-in-react)、[Adding Interactivity](https://zh-hans.react.dev/learn/adding-interactivity)、[Managing State](https://zh-hans.react.dev/learn/managing-state)、[You Might Not Need an Effect](https://zh-hans.react.dev/learn/you-might-not-need-an-effect)、[Synchronizing with Effects](https://zh-hans.react.dev/learn/synchronizing-with-effects) | Quick Start 与主要章节的正文/示例；`selected_sections_read` | UI 教学次序按 UI 描述→静态产品/最小 state→交互/状态→状态管理→Effect 逃生口；列表例子用 `filter/map` 与稳定 key；用户 POST 应在事件处理逻辑，不应为每个派生值添加 Effect。Refs `turn22view8-11`, `turn35view0-1,4`, `turn97view4-6`, `turn98view4-6`。 |
| Vite | [Guide](https://vite.dev/guide/)、[Build](https://vite.dev/guide/build)、[Static Deploy](https://vite.dev/guide/static-deploy) | 当前 build/static deploy 正文；`selected_sections_read` | `vite preview` 用于本地预览构建，不是生产 server。Refs `turn51view5-6`, `turn97view7`。 |
| FastAPI 中文官方教程 | [Tutorial TOC](https://fastapi.tiangolo.com/zh/tutorial/)、[First Steps](https://fastapi.tiangolo.com/zh/tutorial/first-steps/)、[Path Params](https://fastapi.tiangolo.com/zh/tutorial/path-params/)、[Query Params](https://fastapi.tiangolo.com/zh/tutorial/query-params/)、[Body](https://fastapi.tiangolo.com/zh/tutorial/body/)、[Response Model](https://fastapi.tiangolo.com/zh/tutorial/response-model/)、[Errors](https://fastapi.tiangolo.com/zh/tutorial/handling-errors/)、[Dependencies](https://fastapi.tiangolo.com/zh/tutorial/dependencies/)、[SQL](https://fastapi.tiangolo.com/zh/tutorial/sql-databases/)、[Testing](https://fastapi.tiangolo.com/zh/tutorial/testing/)、[CORS](https://fastapi.tiangolo.com/zh/tutorial/cors/)、[SSE](https://fastapi.tiangolo.com/zh/tutorial/server-sent-events/)、[Settings](https://fastapi.tiangolo.com/zh/advanced/settings/)、[Deployment](https://fastapi.tiangolo.com/zh/deployment/concepts/) | 目录和对应正文/代码选段（SSE/Testing/CORS/Security 当前中文页已阅读）；`selected_sections_read` | 顺序形成 request→validation→response model/error→dependency→DB/test→SSE/deployment；SQL 页明确短且非 SQL 教程；SSE 页新 API 与版本有关；中文页有 AI+人类翻译警告，细节双看英文。Refs `turn75view0`, `turn77view0`, `turn80view0-11`, `turn97view0-3`, `turn98view1-3`。 |
| FastAPI Auth | [Security first steps](https://fastapi.tiangolo.com/zh/tutorial/security/first-steps/)、[OAuth2/JWT](https://fastapi.tiangolo.com/zh/tutorial/security/oauth2-jwt/) | First Steps 正文示例及 JWT 代码段；`selected_sections_read` | First Steps 的 Bearer dependency 只提取 token；JWT 页有 fake in-memory users 和示例 secret key。它适合理解依赖/身份流，不是完整生产 auth。Refs `turn97view0`, `turn98view3`。 |
| Datawhale Wonderful SQL | [Repo/readme](https://github.com/datawhalechina/wonderful-sql)、[ch01](https://github.com/datawhalechina/wonderful-sql/blob/main/ch01_%E5%88%9D%E8%AF%86%E6%95%B0%E6%8D%AE%E5%BA%93.md)、[ch02](https://github.com/datawhalechina/wonderful-sql/blob/main/ch02_%E5%9F%BA%E7%A1%80%E6%9F%A5%E8%AF%A2%E4%B8%8E%E6%8E%92%E5%BA%8F.md)、[ch04](https://github.com/datawhalechina/wonderful-sql/blob/main/ch04_%E9%9B%86%E5%90%88%E8%BF%90%E7%AE%97.md)、[ch05](https://github.com/datawhalechina/wonderful-sql/blob/main/ch05_SQL%E9%AB%98%E7%BA%A7%E5%A4%84%E7%90%86.md) | README 课程顺序；ch01/ch02/ch04 正文与 SQL 示例；ch05 选段；`selected_sections_read` | README 指定 MySQL 8.0；有实践库/练习。审阅发现 ch01 对 DCL/COMMIT/ROLLBACK 分类及 MongoDB 例子不准确，ch02 有错误逻辑执行顺序说明；中文课程可用于讲解和练习，规则用官方 DB 文档校正。Refs `turn105view0`, `turn106view0-3`, earlier selected body refs `turn70view0`, `turn71view1-8`。 |
| PostgreSQL 官方 SQL | [Tutorial](https://www.postgresql.org/docs/current/tutorial.html)、[JOIN](https://www.postgresql.org/docs/current/tutorial-join.html)、[Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html) | 官方 tutorial TOC，JOIN/表表达式部分正文；`selected_sections_read` | JOIN 用显式 `ON`、列名显式选取并限定表名是可靠教法；SQLite/MySQL/PostgreSQL 方言需分辨。Refs `turn17view15`, `turn22view13`, `turn97view8`, `turn98view0`, `turn104search11`。 |
| Microsoft GenAI for Beginners | [Repo](https://github.com/microsoft/generative-ai-for-beginners)、[01](https://github.com/microsoft/generative-ai-for-beginners/tree/main/01-introduction-to-genai)、[04](https://github.com/microsoft/generative-ai-for-beginners/tree/main/04-prompt-engineering-fundamentals)、[06](https://github.com/microsoft/generative-ai-for-beginners/tree/main/06-text-generation-apps)、[07](https://github.com/microsoft/generative-ai-for-beginners/tree/main/07-building-chat-applications)、[08](https://github.com/microsoft/generative-ai-for-beginners/tree/main/08-building-search-applications)、[13](https://github.com/microsoft/generative-ai-for-beginners/tree/main/13-securing-ai-applications)、[14](https://github.com/microsoft/generative-ai-for-beginners/tree/main/14-the-generative-ai-application-lifecycle)、[15](https://github.com/microsoft/generative-ai-for-beginners/tree/main/15-rag-and-vector-databases) | Repo 当前目录，01/04/06 正文和代码、07/08/13/14/15 部分正文；`selected_sections_read` | Lesson 04 有 Jupyter/API setup；06 提供 model-call 代码但混合 provider/version。README 标明 GitHub Models 于 2026-07 退役。只作概念/调用补充，使用当下官方 provider 文档。Refs `turn56view0-2`, `turn60view0-2`, `turn62view0-7`, `turn65view2-7,10-11`。 |
| OpenAI API guides | [Text](https://developers.openai.com/api/docs/guides/text)、[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、[Streaming](https://developers.openai.com/api/docs/guides/streaming-responses)、[Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)、[Errors](https://developers.openai.com/api/docs/guides/error-codes)、[Production](https://developers.openai.com/api/docs/guides/production-best-practices) | 阅读选定正文/示例；`selected_sections_read` | Text guide 推荐 Responses API；structured output 仍需处理 refusal/incomplete；SSE 有 created/delta/completed/error；限流按 Retry-After、backoff+jitter、有限总次数；API key 置环境变量/secret。Refs `turn89view0-5`, `turn91view1-8`, `turn98view7-10`。 |
| OAuth 安全规范 | [RFC 9700 §2.4](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.4) | 正文 Section 2.4；`selected_sections_read` | 规范表示不得使用 Resource Owner Password Credentials grant；与 FastAPI tutorial password-flow 示例形成需明说的冲突。Ref `turn108search0`。 |

## 开源项目身份与范围核查

| 项目 | URL | 已核实来源与 README 范围 | 结论 |
|---|---|---|---|
| FastAPI Full Stack Template | https://github.com/fastapi/full-stack-fastapi-template | README 在 FastAPI GitHub org；列出 FastAPI、SQLModel、Postgres、React/TypeScript/Vite、auth、邮件、pytest/Playwright、Docker Compose/CI。只建议抽一个 CRUD 垂直片段。README 正文选读。 | 真全栈模板但整体过大；新手先独立实现单条 CRUD，再用此项目对照，不要求全盘搭建。Ref `turn95view0`。 |
| OpenAI Responses Starter App | https://github.com/openai/openai-responses-starter-app | README 在 OpenAI org；Next.js + Responses API，列多轮、stream/tools、文件搜索、MCP 和 Google connector。README 正文读到用法/功能/安全 key 配置。 | 适合模型产品实现比较；其 Next.js 与学习路线的 FastAPI 不同，不要求移植整个模板。Ref `turn95view1`。 |
| Open WebUI | https://github.com/open-webui/open-webui | 主项目 README 自述并链接 docs；当前 README 列会话、provider、RAG、多向量库、enterprise auth、OpenTelemetry/Redis/multi-node，读选段。 | 大型产品只选 1 个用户目标切片；不要求仓库整体读完。Ref `turn95view2`。 |

## 重要冲突与保守处理

1. **OAuth password flow**：FastAPI 仍在官方中文教程里演示 password + bearer/JWT；IETF RFC 9700 §2.4 最新安全 BCP 明确禁止 Resource Owner Password Credentials grant。教学路径使用教程理解 FastAPI dependency/Bearer/JWT 层次，但不把它列作生产 Auth 做法；公网 browser app 交由维护型 OIDC/IdP + Authorization Code/PKCE。
2. **Microsoft sample provider**：GenAI for Beginners 文档仍有 provider setup/version 混合；仓库注明 GitHub Models 已在 2026-07 退役。因此 lesson 代码用于概念说明，具体请求从当前 provider docs 重新起步。
3. **SQL 逻辑与 DB 方言**：Wonderful SQL 的 MySQL 教学有可用例子，但个别语义描述不应照搬；路线把手写 SQL、官方 Postgres 语义和 SQLite/SQLModel 执行交叉验证。
4. **SSE 版本边界**：FastAPI 当前教程 SSE 页写明新功能进入版本 0.135.0；学习路径要求 pin/检查安装版本，旧版本阅读通用 streaming response，而不照抄新 API。


## cloud_research.md

# Cloud 方向研究日志（供并入 `RESEARCH_LOG.md`）

核查日期：2026-10-03。该日志只记录页面访问范围、失败边界、未执行项与版本风险；教学编排见 `CLOUD_SERVICES_DEEP_REVIEW.md` 和 `CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md`。

| 来源 | 实际访问/阅读范围 | 深度 | 未核实项与版本风险 |
|---|---|---|---|
| [Docker Run an app](https://docs.docker.com/get-started/tutorials/run-an-app/) | 正文完整按原序：容器运行、应用栈、Dockerfile build、share、cleanup、what learned/next；查看实际命令与示例 | `deep_reviewed` | 未本机运行。清理命令可能删卷。 |
| [Docker Compose Getting Started](https://docs.docker.com/compose/gettingstarted/) | 7 步正文/示例：Flask+Redis、Dockerfile、`.env`、`.dockerignore`、healthcheck/depends_on、Watch、volume、多文件/include、config/logs/exec | `deep_reviewed` | 未本机运行；示例中的 Redis 需迁移到 Task Service 所需 DB。 |
| [Docker concepts](https://docs.docker.com/get-started/docker-concepts/)、[Dockerfile best practices](https://docs.docker.com/build/building/best-practices/) | 选读 container、port publishing、volume、multi-container、Dockerfile 示例和 hardening 章节 | `selected_sections_read` | 未覆盖所有 build/runtime 参考页；版本/最佳实践需执行时复核。 |
| [Kubernetes Basics（中文入口）](https://kubernetes.io/zh-cn/docs/tutorials/kubernetes-basics/) | 核对六模块顺序/目标，选读 Minikube、Deployment、Pod/Node、Service、scale、rollout/rollback 正文与代表命令 | `selected_sections_read` | 未逐段审完六模块/所有语言变体；POSIX shell 对 PowerShell 需要适配。未部署集群。 |
| [OpenTelemetry Demo Docs](https://opentelemetry.io/docs/demo/)；[Docker](https://opentelemetry.io/docs/demo/docker-deployment/)；[K8s](https://opentelemetry.io/docs/demo/kubernetes-deployment/)；[Architecture](https://opentelemetry.io/docs/demo/requirements/architecture/)；[Telemetry Features](https://opentelemetry.io/docs/demo/telemetry-features/)；[诊断场景](https://opentelemetry.io/docs/demo/feature-flags/recommendation-cache/)；[Collector 排障](https://opentelemetry.io/docs/collector/troubleshooting/) | 选读架构/信号流、Compose 与 Helm 命令、故障 flag 诊断、sanity tests/Collector debug 内容 | `selected_sections_read` | 未读完文档站或 Demo 源码，未本机运行；官方 Docker 页面 2026-09-11 有 Compose 命令更新，执行时复查。Docker full 约 6GB RAM/14GB disk、minimal 约 3GB；K8s 页面要求 6GB app memory，此为文档值未实测。 |
| [GitHub Actions workflow model](https://docs.github.com/en/actions/get-started/understand-github-actions)、[sample](https://docs.github.com/en/actions/tutorials/create-an-example-workflow)、[Python CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)、[deploy controls](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)、[security](https://docs.github.com/en/actions/reference/security/secure-use)、[billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | 选读事件/job/runner/step、实际 YAML、Python setup/test、Environment/concurrency/approval、artifacts、安全与账单说明 | `selected_sections_read` | 未执行 workflow；runner/action 版本、配额、费用按账号计划和当期规则变化。OIDC provider policy 尚未指定。 |
| [Terraform Docker tutorial](https://developer.hashicorp.com/terraform/tutorials/docker-get-started) | 完整七课顺序；查看 build/change/destroy/variables/outputs 的命令和例子、plan/apply/state/lockfile 说明 | `deep_reviewed` | 未本机执行；Docker provider 教学示例不是 cloud architecture。 |
| [Terraform AWS tutorial](https://developer.hashicorp.com/terraform/tutorials/aws-get-started) | 选读 create/manage/destroy：EC2/VPC/security group、credentials、module、destroy warning | `selected_sections_read` | 未登录/执行或估价；官方说明 Free Tier eligible resources 仍可能收费；按 region/SKU/时长变化。 |
| [阿里云 CNCF x Alibaba 云原生课程](https://developer.aliyun.com/learning/roadmap/cloudnative) | 公开路线页和模块目录；尝试打开课程 1–14 | `toc_checked` | 每个课时页均跳转登录，未读正文/视频/作业；公开页称免费免注册，但按委托保守标 `free_login_required`。 |
| [Docker Getting Started Todo App](https://github.com/docker/getting-started-todo-app) | README、项目架构和开发启动说明；核对 React + Node、Compose、Dockerfile、tests/Actions | `selected_sections_read` | 未 clone、运行或逐文件审阅；仓库 issue 存在环境兼容性报告。仅作项目卡候选。 |
| [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/first-steps/) / [SQLModel FastAPI intro](https://sqlmodel.tiangolo.com/tutorial/fastapi/) | Cloud 方向选读 First Steps、path/body/response/errors/testing/settings 页面示例；SQLModel 仅看目录、FastAPI intro 和建表页代表正文。FastAPI SQL Database 连续 CRUD 主读引用 AI Fullstack 方向已深审正文，云方向不重复认领该深度。 | 本方向 `selected_sections_read`；跨方向 FastAPI SQL Database 以 Fullstack 研究日志为准 | SQLModel 全站 CRUD 正文未审、不是本方向 Primary；具体可读章节及完整范围由统一目录合并时引用 Fullstack 证据。 |

没有创建云账号或登录课程；没有实际运行 Docker、Kubernetes、OpenTelemetry Demo、GitHub Actions 或 Terraform；没有检查个人云/GitHub 账单。费用结论仅指出计费因子与应核查入口，不提供未经选型和用量验证的金额。


## Hello-Agents 静态检查与阅读边界

{
  "scope_notes": [
    "Each docs/chapter1-chapter12 folder contains a Chinese and an English Markdown chapter. Code directories chapter1-chapter12 are present. Chapters 13-16 also exist but were outside this assignment.",
    "learn-claude-code is a separate resource. The user noted its current root lessons are s01-s17 while docs contains a legacy 12-chapter version; that resource was not reviewed here.",
    "Course assumes basic Python and basic familiarity with LLM API calls. Text is free to read; hands-on tasks may require paid API calls, service accounts, hosted vector databases, Docker, HF tokens, model downloads or GPUs.",
    "No chapter exercise was run. Chapter review class labels are reading recommendations, not runtime validation claims."
  ],
  "inventory_and_static_checks": {
    "documentation": "Two Markdown language versions are present for each of chapters 1-12 (24 files total).",
    "chapter_code_file_counts_all_files": {
      "1": 2,
      "2": 1,
      "3": 5,
      "4": 6,
      "5": 4,
      "6": 16,
      "7": 13,
      "8": 12,
      "9": 17,
      "10": 35,
      "11": 15,
      "12": 38
    },
    "python_ast_check": {
      "python_files_checked": 103,
      "syntax_parse_failures": 0,
      "execution_status": "not_run",
      "limits": "AST parsing checks syntax only. Imports, package compatibility, credentials, services, generated outputs, inline Markdown code blocks, network behavior, safety and runtime semantics were not validated."
    },
    "notebook_check": "code/chapter1/FirstAgentTest.ipynb is valid JSON with 9 cells; notebook cells were not executed.",
    "dependency_locking": "No chapter1-12-wide lockfile found. Individual requirements and project files exist in some chapter folders, but do not make the book a single reproducible environment."
  },
  "runtime_validation": "not_run"
}

## 本地资料快照（仅审计，不作为学习版本锁）

```json
[
  {
    "repo": "hello-agents",
    "commit_observed": "4b014ad47e2658af24b59f21e7bdb3f89a66205e",
    "commit_date": "2026-09-29T21:53:44+10:00"
  },
  {
    "repo": "all-in-rag",
    "commit_observed": "cec956e80ae28d6c0ca84c9d39dddcf61ad633fd",
    "commit_date": "2026-10-01T05:49:14+08:00"
  },
  {
    "repo": "learn-claude-code",
    "commit_observed": "ce8f9f186058939da54c9d6fead78dfb5d0fd6c3",
    "commit_date": "2026-09-28T21:49:16+08:00"
  },
  {
    "repo": "pi",
    "commit_observed": "4c6fb7cfe8c538a668726f6f8b3554098c39faee",
    "commit_date": "2026-10-03T14:21:11+02:00"
  }
]
```


## 实际交付质量检查

2026-10-03检查通过：18个指定文件存在且UTF-8可读；Catalog 86条教学切片记录的14个要求字段完整，review_depth枚举与记录ID检查通过；Markdown交付文件的内部文件链接均指向总包内文件；表格列数一致性静态检查通过；四个独立研究仓库git status为空。未对外部链接做全量HTTP可达性保证，未执行教材/API/云部署/训练。ZIP内仅包含18个指定交付文件，并逐项检查解包字节与源文件一致。


## 本轮语义校正日志（2026-10-04，任务标记2026-10-03）

基于较新的原包副本，已确认下载字节与上一轮交付一致。原18文件未修改。仅做产品语义与数据标准化，没有网络资料补查；没有新增资源/专项研究，未改变review_depth或运行状态。

主要变更：Starter fallback、用户载体/纵切面优先、开放0..N Recipe、Evaluation横切/RL训练可选、Career overlay、模型路由按目标、项目候选可替换、enum与说明分离、稳定键与发布hold。新增候选卡仅汇入原Workflow里已存在的AgentScope，不新增审读。

资格边界：阿里课程仅公开目录与登录墙核查，content_access规范为unknown；ZCode保留身份消歧hold，MaxKB保留内容审核hold；README候选不升级成源码/运行深审。物理Seed字段未核对，不宣称导入兼容。

QA结果：86条记录必填字段、enum、数组形状、stable_key唯一/倒序再生成稳定性通过；原记录的URL、推荐/跳读范围和review_depth逐条保留；12张项目卡九项公共字段和四项可选状态通过。3模板、6专项、3深审、2矩阵共14份详细文档的原技术URL、阶段/章号、表格行数完整保留，文本量未压缩；Markdown表格列数与内部文件链接检查通过。Source studyplan修改、数据库写入、Seed发布、自动mastery/scoring均为NO。教程/API/云/GPU执行仍NOT RUN。

```json
[
  {
    "source": "AGENT_APPLICATION_TEMPLATE_DETAILED.md",
    "target": "AGENT_APPLICATION_TEMPLATE_PRODUCTIZED.md",
    "source_chars": 5036,
    "target_chars": 6474,
    "table_rows_preserved": 25,
    "technical_urls_preserved": 7,
    "chapter_stage_markers_preserved": 23
  },
  {
    "source": "AI_FULLSTACK_TEMPLATE_DETAILED.md",
    "target": "AI_FULLSTACK_TEMPLATE_PRODUCTIZED.md",
    "source_chars": 15989,
    "target_chars": 16678,
    "table_rows_preserved": 20,
    "technical_urls_preserved": 56,
    "chapter_stage_markers_preserved": 11
  },
  {
    "source": "CLOUD_SERVICES_TEMPLATE_DETAILED.md",
    "target": "CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md",
    "source_chars": 20795,
    "target_chars": 21626,
    "table_rows_preserved": 11,
    "technical_urls_preserved": 36,
    "chapter_stage_markers_preserved": 0
  },
  {
    "source": "AGENT_SPECIALIZATION_RAG.md",
    "target": "AGENT_SPECIALIZATION_RAG.md",
    "source_chars": 10134,
    "target_chars": 10690,
    "table_rows_preserved": 44,
    "technical_urls_preserved": 16,
    "chapter_stage_markers_preserved": 10
  },
  {
    "source": "AGENT_SPECIALIZATION_CODING.md",
    "target": "AGENT_SPECIALIZATION_CODING.md",
    "source_chars": 6008,
    "target_chars": 6579,
    "table_rows_preserved": 21,
    "technical_urls_preserved": 4,
    "chapter_stage_markers_preserved": 31
  },
  {
    "source": "AGENT_SPECIALIZATION_WORKFLOW.md",
    "target": "AGENT_SPECIALIZATION_WORKFLOW.md",
    "source_chars": 12550,
    "target_chars": 13116,
    "table_rows_preserved": 57,
    "technical_urls_preserved": 2,
    "chapter_stage_markers_preserved": 15
  },
  {
    "source": "AGENT_SPECIALIZATION_BROWSER.md",
    "target": "AGENT_SPECIALIZATION_BROWSER.md",
    "source_chars": 12584,
    "target_chars": 13180,
    "table_rows_preserved": 43,
    "technical_urls_preserved": 1,
    "chapter_stage_markers_preserved": 7
  },
  {
    "source": "AGENT_EVALUATION_PATH.md",
    "target": "AGENT_EVALUATION_PATH.md",
    "source_chars": 5949,
    "target_chars": 6467,
    "table_rows_preserved": 6,
    "technical_urls_preserved": 7,
    "chapter_stage_markers_preserved": 8
  },
  {
    "source": "AGENTIC_RL_PATH.md",
    "target": "AGENTIC_RL_PATH.md",
    "source_chars": 7258,
    "target_chars": 7768,
    "table_rows_preserved": 7,
    "technical_urls_preserved": 11,
    "chapter_stage_markers_preserved": 13
  },
  {
    "source": "AGENT_APPLICATION_DEEP_REVIEW.md",
    "target": "AGENT_APPLICATION_DEEP_REVIEW.md",
    "source_chars": 13294,
    "target_chars": 13741,
    "table_rows_preserved": 34,
    "technical_urls_preserved": 2,
    "chapter_stage_markers_preserved": 60
  },
  {
    "source": "AI_FULLSTACK_DEEP_REVIEW.md",
    "target": "AI_FULLSTACK_DEEP_REVIEW.md",
    "source_chars": 16216,
    "target_chars": 16733,
    "table_rows_preserved": 17,
    "technical_urls_preserved": 44,
    "chapter_stage_markers_preserved": 5
  },
  {
    "source": "CLOUD_SERVICES_DEEP_REVIEW.md",
    "target": "CLOUD_SERVICES_DEEP_REVIEW.md",
    "source_chars": 9398,
    "target_chars": 9829,
    "table_rows_preserved": 23,
    "technical_urls_preserved": 18,
    "chapter_stage_markers_preserved": 0
  },
  {
    "source": "EXPOSURE_MATRIX_ALL.md",
    "target": "EXPOSURE_MATRIX_ALL.md",
    "source_chars": 3260,
    "target_chars": 3674,
    "table_rows_preserved": 30,
    "technical_urls_preserved": 0,
    "chapter_stage_markers_preserved": 16
  },
  {
    "source": "PREREQUISITE_MATRIX_ALL.md",
    "target": "PREREQUISITE_MATRIX_ALL.md",
    "source_chars": 2373,
    "target_chars": 2787,
    "table_rows_preserved": 22,
    "technical_urls_preserved": 0,
    "chapter_stage_markers_preserved": 0
  }
]
```
