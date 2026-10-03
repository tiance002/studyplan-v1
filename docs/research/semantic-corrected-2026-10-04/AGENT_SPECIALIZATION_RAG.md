# Agent 强化专项：Knowledge / RAG

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 类型：Reviewed Specialization Recipe（首批已审核专项参考骨架）；binding=optional，可组合、裁剪、替换，未命中该 Recipe 不阻止规划。Evaluation 横切各阶段，参数训练按目标单独选择。

> 研究快照：2026-10-03。本文是可执行的章节级学习路线；章节核查、目录问题、代码证据和研究范围见 [RESEARCH_LOG：RAG 深审记录](RESEARCH_LOG.md)，逐项资源、官方来源与复习范围见 [RESOURCE_CATALOG_DRAFT：RAG 资源目录](RESOURCE_CATALOG_NORMALIZED_DRAFT.json)。本轮只读研究，没有运行章节示例、模型、付费 API、容器或评测，也未验收 RAGFlow / WeKnora 部署。

## 路线结论

**Primary 教学主线：All-in-RAG 第1–6、8章。** 它覆盖文档入库和切块、Embedding/索引、稀疏与稠密检索、查询处理、上下文生成、评估和项目集成。**Hello-Agents 第8章用于 REVIEW/COMPARE**：复习 Agent 如何调用 RAG，并保留已做过的 PDF 助手实践；第9章用于 DEEPEN 相邻的 context engineering。两章都不能替代检索质量、来源引用和回答正确性的评测闭环。

建议顺序是“来源可追溯 → 单路检索基线 → 固定问题集 → 按失败逐项引入 hybrid、query transform、rerank、context 与引用 → 集成回归”。不要先堆方法：先区分失败发生在解析、召回、排序、上下文组装还是答案生成，再选择对应技术。RRF 是按排名融合多个结果列表；它不是 Cross-Encoder reranker。Weighted fusion 需先检查分数尺度，并在固定验证集上调权。

两项易混点须贯穿教学：All-in-RAG 第4章 `11_hybrid_search` 的示例由 BGE-M3 输出 dense 与 learned sparse 表示后做 RRF，不能说成 BM25；第8章 `03_index_retrieval` 才显式组合 `BM25Retriever`、FAISS dense 和 RRF。BGE-M3 learned sparse 与 BM25 都能做词项相关的稀疏检索，但权重来源与打分算法不同。课程还缺可验证的 citation contract，需补官方资料并将“引用格式正确”和“引用确实支持 claim”分开检查。

## Hello-Agents 已学内容的重叠处理

| 已学内容 | 专项处理 | 新增重点 |
|---|---|---|
| 第8章 RAG 基础、MarkItDown、chunking、Embedding、Qdrant、PDF 助手 | **REVIEW → DEEPEN**：不重搭同类助手；复用概念和数据切片 | provenance/稳定来源 ID、BM25 与 dense 对照、混合召回、固定检索评测、父子块与集成回归 |
| 第8章 MQE、HyDE 与查询结果合并 | **REVIEW + COMPARE** | 同一 query set 对比原查询、rewrite/MQE/HyDE、各检索通道与 RRF；该章结果合并不等于 RRF 或独立 reranker |
| 第9章 GSSC、context budget、history/tool/memory 选择 | **DEEPEN（邻接主题）** | RAG 命中的片段只是模型上下文来源之一；区分 query→知识库检索与整次调用的 context selection/compression |
| 第9章 JIT retrieval / TerminalTool 文件访问 | **COMPARE（邻接概念）** | 运行时按需取信息；不替代文档解析、索引、BM25/dense 或检索评测 |
| claim 到 source 的引用正确性、不可回答问题的拒答回归 | **NEW / 补充** | 建立 chunk/source/page 定位、引用支持关系和无证据拒答检查 |

## 主教学 Spine 与章节级安排

| 阶段 | Why now / JIT 前置 | 主读内容 | 已学关系与跳读 | 小实践与“研究和行动助手”增量 | Exit gate |
|---|---|---|---|---|---|
| 0. 入口：Agent 中的知识检索 | **Why now**：先把 RAG 放进 Agent 系统边界，再拆解各阶段的失效原因。**前置**：会读简单 Python 应用；Hello-Agents ch8 已完成则只复习。 | Hello-Agents ch8 §8.3–8.4、All-in-RAG ch1：RAG 最小链路与术语。 | **REVIEW** RAG 概念与工具入口，不重讲长篇导论。 | 画写入路径和查询路径，标出 parse、chunk、index、retrieve、context、answer 可能失败点。 | 能区分离线入库与在线查询，并为每个阶段说出一种可观察失败。 |
| 1. 入库、解析、切块与来源 | **Why now**：无法追溯来源就不能调试召回、引用或文档更新。**前置**：阶段0；先用 Markdown/纯文本。OCR、表格解析按真实资料需求 JIT 加入。 | All-in-RAG ch2 `04_data_load`、`05_text_chunking`；ch8 `02_data_preparation`。看 loader 输入输出、固定/递归/Markdown/语义切块与父子块。 | Hello-Agents MarkItDown/chunking **REVIEW**；解析保真、稳定 provenance、父子块 **DEEPEN**。第2章 loader 是入门介绍，不代表生产 OCR/表格课程。 | 导入虚构 Markdown，显示 chunk preview；保存 source ID、标题、顺序、页/段位置和解析错误；找出并修复一个标题或表格边界问题。 | 每块能定位回原文，失败可见；文档更新/重建时不丢来源关联。 |
| 2. Embedding、向量库与索引 | **Why now**：来源块稳定后再建索引，避免把解析问题误当模型问题。**前置**：阶段1。向量库部署与模型下载按可用环境/目标 JIT。 | All-in-RAG ch3 `06_vector_embedding`、`08_vector_db`；按资料形态选读 `07_multimodal_embedding`、`09_milvus`、`10_index_optimization`。 | Hello-Agents Embedding/Qdrant **REVIEW**；增加 chunk ID、metadata、模型/维度版本契约 **DEEPEN**。多模态和分布式 Milvus 不是普遍前置。 | 为每个 chunk 保存稳定 ID、模型名/版本、向量维度与 metadata；检查向量可回到原文。 | 查询与索引使用匹配的 embedding 版本；可追溯并能按文档 ID 重建索引。 |
| 3. 单路检索 baseline 与评测 | **Why now**：先有可重复的基线，才能判断后续加方法是否真在解决问题。**前置**：阶段1–2；建立小型人工核验 query/相关 chunk 集。 | All-in-RAG ch4 `11_hybrid_search` 中的检索基础、ch6 `18_system_evaluation`：BM25/dense、Precision/Recall/MRR/MAP 与评估工具概念。 | Hello-Agents 没有系统检索/回答闭环，属 **NEW**。Ragas ContextPrecision/ContextRecall 与传统 IR 指标同名相近但计算口径不同。 | 先独立运行 lexical/BM25 与 dense（缺模型时可用固定 stub 先校验接口）；按精确术语、语义改写、跨段、不可回答分组记录坏例。 | 能复现 baseline；分清解析缺失、未召回、排序差和答案错误。 |
| 4. Hybrid、融合与查询变换 | **Why now**：只有 baseline 显示某类 query 召回不足时，才选择增加检索通道或改写。**前置**：阶段3，有固定测试集和通道级结果。 | All-in-RAG ch4 `11_hybrid_search`、`12_query_construction`、`14_query_rewriting`；ch8 `03_index_retrieval`。对比 BM25、dense、BGE-M3 learned sparse、RRF、weighted fusion、metadata filter、MQE、HyDE、step-back、rewrite、routing。 | Hello-Agents MQE/HyDE **REVIEW + COMPARE**；显式 BM25+dense、RRF、通道诊断 **NEW/DEEPEN**。Text2SQL/Cypher 仅按数据需求选读。 | 保留各通道候选与最终顺序；同一测试集每轮只改一个因素，观察哪些 query 类型改善、哪些回退。 | 能准确解释通道和融合差异；不把论文/示例平均值推广成所有语料均有效。 |
| 5. Rerank、上下文、回答与 citation | **Why now**：候选已含正确证据但排序或答案组装失败时，才加 rerank 和 context 策略。**前置**：阶段3–4；回答层只接本轮真实检索证据。 | All-in-RAG ch4 `15_advanced_retrieval_techniques`、ch5 `16_formatted_generation`、ch8 `04_generation_sys`；补 Microsoft RAG/index provenance、Cohere RAG citations、RAGFlow citation prompt 或 WeKnora references API。 | 父子上下文、去重、证据绑定 **DEEPEN**；结构化 source citation 与 correctness **NEW**。citation prompt 规定格式，不证明 claim 被证据支持。 | 尝试候选 rerank、父块展开、压缩/去重和长度控制；答案带 chunk ID 与文件位置；加无证据问题及错误引用样例。 | 每条实质性 claim 能回到原文；引用不存在、错位、不支持 claim 和资料不足却作答都能被测试识别。 |
| 6. 集成与回归 | **Why now**：各组件可以单独诊断后，才把 pipeline 串起来并判断改动是否改善端到端结果。**前置**：阶段1–5通过。 | All-in-RAG ch8 `01_env_architecture` 至 `04_generation_sys`；ch6 `19_common_tools` 按需。 | Hello-Agents PDF 助手 **REVIEW**；本阶段增加版本化测试数据、索引和配置快照、badcase 修复后回归。 | 将导入、chunk、index、BM25/dense、融合、context、回答、引用接通；对同一问题集回归，不可回答样本要拒答。 | 每个坏例能定位到阶段；变更可复测；答案支持性、引用、拒答和检索指标均有记录。 |
| 7. 可选 Agentic RAG / GraphRAG | **Why now**：静态 RAG 已测过且多跳/多源失败仍可复现，才测试额外规划循环或图索引。**前置**：阶段6；有 baseline、轮次/延迟/token 观测与停止条件。 | All-in-RAG ch7 `21_agentic_rag`（其实际内容见正文与 sidebar）；有实体关系缺口时读 `20_kg_rag`。 | Hello-Agents ch9 JIT/context retrieval 是邻接概念，不等于 Agentic RAG 多轮检索决策。README 清单漏列 21 章节，细节见研究日志。 | 选一个复杂 badcase，对比静态 RAG 与 Agentic RAG 的证据、轮次、答案、延迟和 token；只有在收益超过成本时保留。 | 能证明新增循环解决了某个基线失败；上限/无结果/工具故障有明确终止和拒答路径，测量结果可复现。 |

## 贯穿路线的术语边界

| 方法 | 本路线采用的准确说法 | 证据/常见误教 |
|---|---|---|
| BM25 | 基于词项统计、文档频率与长度归一等因素的 lexical ranker。 | All-in-RAG ch8 明确使用 BM25Retriever。 |
| BGE-M3 learned sparse | 模型产生的稀疏 token 权重，可做 sparse retrieval。 | All-in-RAG ch4 hybrid 示例获取 BGE-M3 sparse 与 dense；模型卡把 token weights 说成“similar to BM25”，但单独列 BM25 baseline，不能把它等同 BM25。 |
| Dense | embedding 向量相似度检索。 | 可与词项检索互补，效果需在同一语料和 query set 上测。 |
| RRF | 按各路候选的 rank 进行融合，不要求原始分数同尺度。 | 是 rank fusion，不是 Cross-Encoder 或语义 rerank。 |
| Weighted fusion | 按权重组合多个检索分数。 | 先核对尺度/归一化，再用验证集调权；不要直接相加不兼容分数。 |
| Reranker | 对召回候选重新计算 query-document 相关性并排序。 | 候选已含正确证据但排位差时才值得尝试；带来额外算力和延迟。 |
| MQE / HyDE / rewrite | 以多个问题、假设性文档或改写 query 扩展召回。 | HyDE 文本用于检索，不应当作事实证据；收益和额外成本都要测。 |

## 默认贯穿项目候选示例：研究与行动助手

使用一个小型、可人工核验的虚构研究语料；阶段上升由失败证据驱动，不以组件数量验收。

| 版本 | 增量实践 | 验收点 |
|---|---|---|
| V0 来源可追溯 | 导入 Markdown/纯文本，记录 document ID、标题、顺序、页/段位置；显示 chunk preview 和解析错误。 | 每个 chunk 可还原到来源位置；坏切块可定位。 |
| V1 词法检索 | 运行本地 BM25，展示 top-k、排名、分数和原文。 | 精确词项问题有可解释候选；无匹配时不伪造证据。 |
| V2 Dense / 可替换检索器 | 添加可用 embedding，并保存模型/维度/索引版本；先用本地模型、stub，或在有预算与数据许可时选择 API。 | query/index 模型匹配；召回结果能回到 chunk。 |
| V3 Hybrid | 分别保留 BM25、dense、可选 BGE-M3 learned sparse 通道；比较 RRF 与经过校验的 weighted fusion。 | 通道级差异可见；调融合后同一测试集显示改善与回退。 |
| V4 排序与上下文 | 正确证据已召回而排名靠后时才测 rerank；按需加父块、去重、长度控制。 | 检查模型上下文确实含所需证据，且长度/排序符合预算。 |
| V5 答案、citation 与拒答 | 让回答层只引用当前检索块；记录 chunk ID 和原始文件定位；无证据时拒答。 | 引用可追溯且支持回答；不可回答问题不编造来源。 |
| V6 评测闭环 | 固定测试集版本、配置快照、检索/回答指标、人工 badcase 与修复记录。 | 修改前后可重放；LLM judge 抽样人工审核，不作为唯一 oracle。 |
| V7 条件性 Agentic RAG | 只对 V6 留下的多跳/多源失败加入有界 Agent 循环。 | 明确比较质量、轮次、延迟、token 和故障复杂度；收益不足时回退静态方案。 |

本轮没有执行这些实践，也没有下载模型或调用付费 API。未来实践可依目标数据、硬件、预算和隐私要求选择本地模型、固定 stub 或有预算的 API；开始前查清服务价格、数据使用和版本依赖，不将本轮未测试结果写成已验收效果。

## JIT 深化与成熟项目入口

| 主题/项目 | 何时进入 | 学习范围和门槛 |
|---|---|---|
| OCR、表格/版面保真 | 目标资料含扫描件、复杂表格或图文混排，且已有坏例证明文本抽取损失关键证据。 | 只选真实文件类型追一条 parse→chunk→source locator；先用小样本和人工标注核验。 |
| Milvus/分布式索引 | 数据量、并发、过滤或运维需求超出本地索引；不是入门必修。 | 先具备单机检索 baseline，再按目标负载读相关索引和容量说明。 |
| Text2SQL / GraphRAG | 用户问题必须触及结构化数据或实体多跳，文本 RAG 失败集能复现该缺口。 | 分开设计安全查询/实体关系评估；不为“用上新技术”提前引入。 |
| Agentic RAG | 固定 pipeline 对多步问题持续失败，并有静态 baseline。 | 设最大轮数、错误/空结果退出、最终证据检查与成本观测；先做一个可对照纵切片。 |
| RAGFlow | 需要观察成熟 RAG 产品中的解析、检索测试、rerank 和 citation 工程边界。 | 本次研究发现 `v1.0.0-rc1` 是 Go rewrite 的 preview，只作为当前架构/文档研究对象；本次官方 `v0.27.2` Quickstart 标为 Stable。后续动手前重新确认官方稳定 tag，并按该版本核 OS、Docker/数据库、模型和 SDK/API 兼容；也可选择 WeKnora。RC 的 4 CPU/16 GB/50 GB 是特定部署参考，不是初学者入门门槛。 |
| WeKnora | 更关注当前文档处理、hybrid search、references API 与 evaluation 数据契约。 | 本次官方 README 标记 `v0.8.2`；只选 ingestion→search→references 或 evaluation 的 3–6 个切片。后续实践前重核版本与依赖；不声称本轮已部署或验收。 |

进入真实项目学习前，应能画清 parse→chunk/provenance→embedding/index→BM25/dense→fusion/rerank→context→answer/citation 数据流；拥有可回答与不可回答的人工检查集；复现 baseline 与坏例修复；验证引用 ID 能回到原文；观察入库状态、失败/重试、更新/删除与索引版本；并在目标权限配置下评估延迟、吞吐、token/费用、失败率和恢复。真实系统还需做访问过滤、提示注入隔离和敏感数据边界。项目学习不要求先部署整套系统。

## 第7章 Agentic RAG：使用前的内容核查

本地版本中存在 `docs/chapter7/21_agentic_rag.md` 及配套代码，sidebar 也列出该节；根 README、`docs/README.md` 与英文 README 的第7章清单未列出。课程内容将其放在传统检索基线与评估之后，作为选修比较更合适。

章节表格给出 Context Recall、Faithfulness、Answer Relevance、延迟和 token 的比较数字；配套 `demo.py` 实际只输出轮数、文档数和答案长度，没有测量那些指标。`agent.py` 在达到 `max_iterations` 时路由到 `END`，正文却称上限时强制生成答案；实现和文字不一致。实际教学前应补可复现评估并核对终止路径，不把章节数字当成普遍收益或已验证结论。该示例使用硬编码小语料、OpenAI 模型，Tavily 为可选外部搜索；本轮仅阅读，没有运行。

## 官方补充资源

- [Microsoft Foundry：RAG and indexes](https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation)：来源 title/URL/filename 等 provenance 字段、引用质量、权限和 retrieved content 安全边界。
- [Cohere：RAG citations](https://docs.cohere.com/docs/rag-citations)：answer span、引用文本和 source document ID 的结构化引用实例；阅读文档无需调用 API。
- [BAAI BGE-M3 模型卡](https://huggingface.co/BAAI/bge-m3) 与 [原始论文](https://arxiv.org/abs/2402.03216)：dense、learned sparse、multi-vector 和独立 BM25 baseline 的区分。
- [RAGFlow releases](https://github.com/infiniflow/ragflow/releases)、[v0.27.2 Stable Quickstart（研究快照时）](https://ragflow.io/docs/v0.27.2/)、[v1.0.0-rc1 Quickstart](https://ragflow.io/docs/v1.0.0-rc1/)、[Retrieval Testing](https://ragflow.io/docs/v1.0.0-rc1/retrieval_testing)、[citation prompt](https://github.com/infiniflow/ragflow/blob/main/rag/prompts/citation_prompt.md)。
- [WeKnora 官方仓库](https://github.com/Tencent/WeKnora)、[API overview](https://github.com/Tencent/WeKnora/blob/main/website-docs/04-api/01-api-overview.md)、[evaluation 文档](https://github.com/Tencent/WeKnora/blob/main/website-docs/03-features/15-evaluation.md)：hybrid 搜索、references 事件和评测数据契约。
- 本地课程入口：[All-in-RAG 中文 README](https://github.com/datawhalechina/all-in-rag/blob/main/README.md)、[课程 sidebar](https://github.com/datawhalechina/all-in-rag/blob/main/docs/_sidebar.md)、[Hello-Agents 第8章](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/Chapter8-Memory-and-Retrieval.md)、[Hello-Agents 第9章](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter9/Chapter9-Context-Engineering.md)。
