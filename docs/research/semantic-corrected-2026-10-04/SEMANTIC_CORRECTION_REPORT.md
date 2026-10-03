# StudyPlan语义校正：一页摘要与验收

本轮在原研究包上完成产品语义收口，保留章级教学。方向是能力领域；Recipe是可组合参考骨架；Starter是fallback；项目案例是可替换候选。

## 一页摘要

| 用户关心的问题 | 校正结果 |
|---|---|
| 哪些原文容易把用户锁死？ | Agent“核心成果是研究助手”、云“每阶段保留同一API”、专项“先二选一”、节奏“一次只选一个目标”、RAG入口“本地云路由”、面试成果要求。它们可能被误读成固定项目/分支/个人目标，不是资料研究错误。 |
| 如何用户项目优先？ | 有合适项目直接使用；太大就裁纵切面；没有才用默认候选。不适合项目的能力先micro exercise；代码可重构/替换，保留问题、测试、数据、接口、决策与证据。旅行Agent可直接做载体。 |
| Agent Recipe如何组合？ | 选择0..N个RAG/Coding/Workflow/Browser；Evaluation横切，RL只在训练目标展开。阶段primary_focus仅表示当前聚焦问题，可有多个supporting_capabilities，不给用户单选归属。 |
| 未命中Recipe怎么办？ | 从能力、前置和已审资源池组合局部连续教学；缺审核资料明确needs_research_or_review，不拒绝目标、不编造章节、不静默升级公共Seed。 |
| 哪些项目/资料仍只是候选？ | RAGFlow/WeKnora/Pi/OpenHands/browser-use/LangGraph/AgentScope及全栈/云案例均可替换；候选审读不等于全源码或运行验收。ZCode同名歧义、MaxKB仅metadata、阿里课时访问未验证保留发布hold。未审的新举例不新增为已审项目卡。 |
| Catalog能映射Seed吗？ | 86条切片已规范enum、稳定键、范围、费用和审读溯源，结构/语义达到可映射草案；不是已验证当前物理schema的导入包，也没有发布。hold记录仍需相应审核。 |

## 原文到产品规则

| 原位置/具体措辞 | 校正 | 保留的教学内容 |
|---|---|---|
| Agent模板首段“核心成果是…” | Default Starter候选；优先用户载体 | A0–A8与全部章节、练习、出口 |
| Agent专项入口“资料问答/本地云路由” | Knowledge / RAG Agent；local-cloud routing仅optional cost/quality主题 | RAGpipeline、hybrid退化诊断与检索/回答eval |
| Agent模板“一次只选一个主要目标” | 一个阶段少量聚焦；总体可组合多个专项 | 前置顺序、降低认知负荷与Evidence gate |
| RAG项目“先二选一” | 可替换已审候选；按目标选或直接用户项目 | 原项目focus/questions/depth/avoid与准入 |
| 云模板“每阶段同一API” | 连续的是问题/证据；允许换实现 | API/DB/config/test/health→Docker/Compose→按需云/K8s/OTel/CI/IaC→恢复 |
| AI模板“AI团队资料工作台” | AI资料工作台默认候选；团队按目标 | React/FastAPI/SQL/AI/SSE/Auth/测试/部署细节 |
| “面试成果要求/面试价值” | 核心调用链/失败/取舍保留，Career Overlay按目标触发 | 工程解释与验证能力 |
| Catalog role/access/media自然语言 | 单枚举字段+独立purpose/access/media/cost/usage/review说明 | 原审读范围和深度不升级 |

## 完成前自检

以下YES表示本包规范允许/要求该行为，不是运行中的StudyPlan功能测试结果。本轮未修改或执行其代码。

| # | 问题 | YES/NO | 核验依据 |
|---|---|---|---|
| 1 | 用户旅行Agent可直接作持续项目？ | YES | 用户项目优先与纵切面规则、组合情景 |
| 2 | 同时需要RAG+Browser+Workflow？ | YES | 0..N Recipe与supporting_capabilities |
| 3 | 不属于四Recipe规划仍继续？ | YES | capability/prerequisite/resource pool回退；缺证据显式补审 |
| 4 | Starter明确仅fallback？ | YES | 三份productized模板与独立Starter文档 |
| 5 | RAGFlow只是候选？ | YES | 卡片reviewed_candidate、binding=optional、replacement_allowed=yes |
| 6 | Evaluation是横切能力？ | YES | 类型及逐阶段挂接，非职业分支 |
| 7 | Agentic RL可选？ | YES | Optional Training Specialization，训练目标触发 |
| 8 | role/content_access/media_type无自然语言混用？ | YES | 86条顶层与枚举字段校验；原说明改名original_*_note |
| 9 | 详细章节级编排保留？ | YES | 3模板与6路径阶段、原技术链接和章号检查；只改语义/增量载体/职业表达 |
| 10 | 没有改代码或发布Seed？ | YES | 仅新文档/目录/ZIP；无数据库或发布操作 |

## 交付与边界

先读本报告→[规划语义标准](PLANNING_SEMANTICS_STANDARD.md)→三份PRODUCTIZED模板→[Recipe索引](SPECIALIZATION_RECIPES.md)和原六份详细路径→[Starter](DEFAULT_STARTER_PROJECTS.md)/[项目卡](PROJECT_STUDY_CARDS_NORMALIZED.md)/[标准目录](RESOURCE_CATALOG_NORMALIZED_DRAFT.json)→[Seed映射说明](SEED_MAPPING_NOTES.md)。三份深审、两个矩阵和历史日志随包保留语义校正副本；原包不变。

未重新大范围搜索、未新增资料审核、未修改StudyPlan代码、未写数据库、未发布Seed、未自动mastery/scoring。Catalog发布前仍需核对真实数据契约、人工审核hold/待发布记录；本轮不虚构数据库字段匹配。


## 实际检查结果

86条目录记录通过必填、枚举、数组、稳定键及深度不升级检查；12张项目卡通过字段/optional状态检查；14份详细教学文档的技术来源URL、阶段/章号和表格行数保留检查通过。三模板A0–A8、全栈0–10、云-1–13完整；六条详细路径未压成能力清单。所有内部文件链接和表格列数检查通过。总包包含11份指定新文件与12份保留的语义校正详细正文，共23文件。
