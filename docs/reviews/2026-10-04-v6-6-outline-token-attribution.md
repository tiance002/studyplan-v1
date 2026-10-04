# v6.6 Outline离线归因：MULTIPLE_CAUSES_CONFIRMED，STOP

用户现在新增能做什么：可基于可复现请求/组成表审批一个有界outline投影patch；本轮未改变任何正式生成行为，也没有新真实Plan。根因是**运行时把发布审核大对象当作outline上下文**：未选资源目录、跨方向整份教学材料、重复审核/guide事实和输出职责过宽。不是六阶段实际扩成61阶段，也不是179篇抓取的教程全文。

## Baseline / 证据身份

- 分支 `feat/n1-resource-discovery`；实际起始HEAD `3074432f4cff2b71507ea0460f75aa46d6fd56ee`，tracked clean。已有两个禁止目录保持，未reset/切入口/Worker/RAG/DB/推送/合并。
- 本轮Goal为用户明确批准的 [v6.6 Outline Offline Audit](../implementation/STUDYPLAN_V6_6_OUTLINE_OFFLINE_AUDIT_GOAL_2026-10-04.md)；原文精确归档。
- 唯一旧Acceptance `v65-agent5-synthetic-7a1040c10f15`，旧Run `run_cecd033d2fed4a3190a77df32a3cb382`；只读其本地synthetic/public证据，没有创建新Run/Acceptance，没有读取私人凭据/DSN。
- Agent5 publication digest `eeff800d60e332772045d32db8ff143a254b24d72d32462b35e7620842be0565`，当前public Seed与v6.5预检一致；frozen manifest哈希与原initial保持。
- 旧真实usage重读为input209998、output4097、HTTP200、finish_reason length、provider_output_truncated、failed、unknown本轮0。
- quota当前**24/50**；全部24对request/result完整、受控未决0，历史其他scope unknown不重派。原.env、v6.5证据、quota/journal hashes在最终不变检查中再次核对；本轮新增模型/网络/DB请求0。
- Root路由请求Sol6.1/high、独立回填代理Sol6.1/medium；实际解析NOT OBSERVABLE，无Astra/全局模式或模型配置变更。代理仅拥有ignored回填测试/证据。

## Exact payload与计量边界

使用 `PlanningNodes.normalize → generate_skeleton → _ScopedLLM → OpenAICompatibleLLM.generate_structured` 当前生产函数，由旧JSONB提交事件的initial重建，在真正HTTP发送之前的本地CaptureClient拦截。使用sentinel key，不载入真实key；socket/DNS/HTTP发送/psycopg连接均拒绝。DB attempt ledger未运行；其 `_planning_claim` 删除与适配器排除全部下划线字段已用等价性测试证明，scope/lease不影响messages。

不是手工写“相似prompt”：原system/SHAPES/context/domain_pack均由生产函数生成。当前生产文件与v6.5实现未变；用httpx.Request离线构造相同JSON body编码，不send。保留基线输出shape和thinking.disabled，不调整任何cap。

| 精确可重建项 | 实际值 |
|---|---:|
| system内容字符 | 2559 |
| user内容字符 | 575549 |
| messages内容总字符 | **578108** |
| HTTP JSON UTF8字节 | **816500** |
| developer message | 0（只有system/user两条） |
| 首次repair/retry context | 0 |
| GoalSpec / starting point / prior history | null / 无单独starting_point / 0 |

离线HTTP body SHA256：`4e38d9b03efd39f5d511497c21faac0d560e1e84b37d76043dafba794073cdb6`。v6.5没有保留原始wire body/hash，不能声称与当时wire逐字节对比已PASS；可证明的是保留initial+未变化生产路径重建的确定性、当前bytes/hash、实际元数据一致。key、base URL/timeout不进入messages；只记录模型body，不记录Authorization。

本机工程与bundled Python均没有tiktoken/transformers/tokenizers/sentencepiece或DeepSeek词表，本轮完全离线不下载。采用当前FakeLLM已有的**字符/4启发式**：对完整序列化messages的字符进行估算，使用小数方便精确相加。结果**144527 estimated tokens**，比provider真实209998少65471（**31.18%**）。原Fake直接对Python payload repr估算则为143784，二者都不是DeepSeek tokenizer。中文、ASCII标识、JSON标点分布和聊天framing导致偏差；无法精确归因provider内部token序列。精确的是字符/JSON字节，token列明确为估计。

`attribution.json`同时保留209998按字符占比分摊的辅助列，合计209998，但只是尺度校准，不冒充真实组件token。候选正文构成更偏ASCII，比例估计也不能替代下一授权门禁的实际usage。本报告不使用估算证明收费成功。

## Token attribution（所有>=1%项，全覆盖、互不重叠）

表中chars为原user JSON值的真实序列化片段字符，system为原文本字符；JSON keys/containers/separators另计。分母578108 messages字符。每个字段只归入一个component。资源/文档总体大小在下方单独给出，**不能再与此表相加**。

| Component | chars | estimated tokens | % of input | repeated? | needed by outline? |
|---|---:|---:|---:|---|---|
| `resources.review_evidence` | 111,177 | 27,794.25 | 19.23% | 部分相同审核叶子重复2–3次 | 全文不需要；本地索引/精确范围保持 |
| `JSON key/container/separator overhead` | 90,799 | 22,699.75 | 15.71% | 未发现完整片段重复；小公共字符串另计 | 对象移出可同步减少编码成本；不靠更换 JSON 格式修语义 |
| `resources.sections.review_note` | 44,176 | 11,044 | 7.64% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；本地索引/精确范围保持 |
| `publication.doc.CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md` | 21,875 | 5,468.75 | 3.78% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `publication.doc.AI_FULLSTACK_TEMPLATE_PRODUCTIZED.md` | 16,863 | 4,215.75 | 2.92% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `resources.metadata.exposure_with` | 16,369 | 4,092.25 | 2.83% | 部分相同审核叶子重复2–3次 | 全文不需要；本地索引/精确范围保持 |
| `publication.doc.PROJECT_STUDY_CARDS_NORMALIZED.md` | 13,573 | 3,393.25 | 2.35% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `publication.doc.AGENT_SPECIALIZATION_BROWSER.md` | 13,296 | 3,324 | 2.30% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `publication.doc.AGENT_SPECIALIZATION_WORKFLOW.md` | 13,250 | 3,312.50 | 2.29% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `publication.doc.AGENT_SPECIALIZATION_RAG.md` | 10,791 | 2,697.75 | 1.87% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `resources.sections.url` | 10,330 | 2,582.50 | 1.79% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；本地索引/精确范围保持 |
| `resources.sections.section_id` | 9,129 | 2,282.25 | 1.58% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；本地索引/精确范围保持 |
| `context.manifest` | 8,705 | 2,176.25 | 1.51% | 6个stage guide在pack/manifest各1份 | 只需冻结 stage/prerequisite 摘要，不需完整预算/guide/hash |
| `resources.metadata.review_note` | 8,250 | 2,062.50 | 1.43% | 部分相同审核叶子重复2–3次 | 全文不需要；本地索引/精确范围保持 |
| `resources.review_note` | 8,054 | 2,013.50 | 1.39% | 部分相同审核叶子重复2–3次 | 全文不需要；本地索引/精确范围保持 |
| `publication.doc.AGENTIC_RL_PATH.md` | 7,901 | 1,975.25 | 1.37% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `resources.metadata.teaching_weaknesses` | 7,741 | 1,935.25 | 1.34% | 部分相同审核叶子重复2–3次 | 全文不需要；本地索引/精确范围保持 |
| `publication.doc.AGENT_SPECIALIZATION_CODING.md` | 6,669 | 1,667.25 | 1.15% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `publication.doc.AGENT_EVALUATION_PATH.md` | 6,577 | 1,644.25 | 1.14% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `publication.doc.AGENT_APPLICATION_TEMPLATE_PRODUCTIZED.md` | 6,575 | 1,643.75 | 1.14% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；留本地发布审核证据 |
| `resources.sections.applicable_node_keys` | 6,243 | 1,560.75 | 1.08% | 未发现完整片段重复；小公共字符串另计 | 全文不需要；本地索引/精确范围保持 |
| 其余 97 项，每项 <1%（逐项JSON证据） | 139,765 | 34,941.25 | 24.18% | 逐项见 attribution.json | 同上职责分类 |
| **合计（互不重叠）** | **578,108** | **144,527** | **100%** | | |


整块视角：resources402175字符（约69.57%）；publication_evidence132909（约22.99%）；selected stage_blueprints22170（约3.83%）；manifest8705（1.51%）。资源中metadata114807、review_evidence111177、sections128514属于402175内部，包含结构/字段名成本；不能把这几个对象值与逐叶子表再次相加。

用户要求的小贡献功能族也逐项核对如下（是上述归因表的已计子集，不能再次相加）：

| 功能族 | chars | estimated tokens（char/4） | 本Run状态/用途 |
|---|---:|---:|---|
| system静态指令 | 2559 | 639.75 | outline/structure/practice通用；独立developer message0 |
| goal JSON值 | 30 | 7.50 | 唯一synthetic目标 |
| prefs JSON值 | 80 | 20 | 默认偏好；无独立learner profile |
| GoalSpec JSON值 | 4 | 1 | null；starting point/额外constraints未提供 |
| selected knowledge_blueprints | 2140 | 535 | 6个知识蓝图/前置/目标；非全部61 |
| required_node_keys | 198 | 49.50 | 6根键；manifest也带键，正文未完整保护见FAIL |
| selected stage resources引用值 | 5632 | 1408 | 18安排/35章节引用，无教程全文 |
| resource_refs | 3021 | 755.25 | 整包source引用清单，尚未随selected route裁剪 |
| stage learning_guidance值 | 4756 | 1189 | pack中1份；manifest内另1份 |
| stage extensions值 | 5407 | 1351.75 | 13说明；Common Core项目学习extension0 |
| stage teaching_evidence值 | 3891 | 972.75 | selected教学证据，不是模型必需全文 |
| selected practice_blueprints | 2545 | 636.25 | 6条提前进入outline，应留后续逐stage |
| semantic_context | 260 | 65 | 载体/optional/组合/缺口等短语义 |
| field_shape JSON例子 | 327 | 81.75 | 很小；输出资源/extensions职责可收窄 |
| prior Plan/history/summary/prompt/outcome | 0 | 0 | 无 |
| 首次retry/repair上下文 | 0 | 0 | 无 |


## Top 20 largest payload fragments

下表采用互不包含的frontier：每个完整resource对象、每篇publication Markdown、每个selected stage对象。chars包含其JSON值编码；出现次数用精确片段匹配。正文全字段在ignored本机body可核对，报告只列公开路径/key，避免大量复制公开研究材料。

| 来源对象 / stable key | chars | estimated tokens | 出现次数 | 是否重复 | 为什么加入 |
|---|---:|---:|---:|---|---|
| `domain_pack.resources[9]`<br>`src_agent_application_v5_v62_04a9cd3e245d91d3017e` | 38,222 | 9,555.50 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.publication_evidence.surrounding_teaching_documents.CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md`<br>`CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md` | 21,875 | 5,468.75 | 1 | PASS：完整片段仅1份；内部叶子另计 | 审核mapper写入surrounding_teaching_documents，未在语义裁剪/outline端投影 |
| `domain_pack.resources[29]`<br>`src_agent_application_v5_v62_dcf7836910e230d2cfc8` | 18,978 | 4,744.50 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[5]`<br>`src_agent_application_v5_v62_de71f08679b5bd598141` | 17,068 | 4,267 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.publication_evidence.surrounding_teaching_documents.AI_FULLSTACK_TEMPLATE_PRODUCTIZED.md`<br>`AI_FULLSTACK_TEMPLATE_PRODUCTIZED.md` | 16,863 | 4,215.75 | 1 | PASS：完整片段仅1份；内部叶子另计 | 审核mapper写入surrounding_teaching_documents，未在语义裁剪/outline端投影 |
| `domain_pack.publication_evidence.surrounding_teaching_documents.PROJECT_STUDY_CARDS_NORMALIZED.md`<br>`PROJECT_STUDY_CARDS_NORMALIZED.md` | 13,573 | 3,393.25 | 1 | PASS：完整片段仅1份；内部叶子另计 | 审核mapper写入surrounding_teaching_documents，未在语义裁剪/outline端投影 |
| `domain_pack.publication_evidence.surrounding_teaching_documents.AGENT_SPECIALIZATION_BROWSER.md`<br>`AGENT_SPECIALIZATION_BROWSER.md` | 13,296 | 3,324 | 1 | PASS：完整片段仅1份；内部叶子另计 | 审核mapper写入surrounding_teaching_documents，未在语义裁剪/outline端投影 |
| `domain_pack.publication_evidence.surrounding_teaching_documents.AGENT_SPECIALIZATION_WORKFLOW.md`<br>`AGENT_SPECIALIZATION_WORKFLOW.md` | 13,250 | 3,312.50 | 1 | PASS：完整片段仅1份；内部叶子另计 | 审核mapper写入surrounding_teaching_documents，未在语义裁剪/outline端投影 |
| `domain_pack.resources[12]`<br>`src_agent_application_v5_v62_2d824263edbf3518ed94` | 12,554 | 3,138.50 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.publication_evidence.surrounding_teaching_documents.AGENT_SPECIALIZATION_RAG.md`<br>`AGENT_SPECIALIZATION_RAG.md` | 10,791 | 2,697.75 | 1 | PASS：完整片段仅1份；内部叶子另计 | 审核mapper写入surrounding_teaching_documents，未在语义裁剪/outline端投影 |
| `domain_pack.resources[6]`<br>`src_agent_application_v5_v62_d3fcc3994894d29174e4` | 10,515 | 2,628.75 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[10]`<br>`src_agent_application_v5_v62_bb825e030c7385c9a978` | 10,293 | 2,573.25 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[30]`<br>`src_agent_application_v5_v62_4faf0a9e9f15b7bcfc96` | 9,812 | 2,453 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[40]`<br>`src_agent_application_v5_v62_01f03e0a227c3bbfc3b5` | 9,693 | 2,423.25 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[4]`<br>`src_agent_application_v5_v62_7b35476246aa1b12023c` | 9,611 | 2,402.75 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[15]`<br>`src_agent_application_v5_v62_2f5e62896028a2af86b8` | 9,502 | 2,375.50 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[13]`<br>`src_agent_application_v5_v62_4e3c3cda00c4a38db26c` | 9,473 | 2,368.25 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[8]`<br>`src_agent_application_v5_v62_243595be34a1cea2f8fb` | 9,247 | 2,311.75 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[21]`<br>`src_agent_application_v5_v62_9b248ab3820293737de6` | 8,864 | 2,216 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |
| `domain_pack.resources[11]`<br>`src_agent_application_v5_v62_2ff98861a5beb53ca056` | 8,590 | 2,147.50 | 1 | PASS：完整片段仅1份；内部叶子另计 | 全资源目录保留metadata/review_evidence/sections；outline原样转发整包 |


## 15项重复/膨胀核对

这里FOUND表示找到该类现象，不是测试状态；测试统一PASS/FAIL/NOT RUN。先逐项验证再下结论，没有先假定三方向/61stage/正文重复是真的。

| 检查 | PASS / FOUND / NOT APPLICABLE | 证据 |
|---|---|---|
| 三方向 Pack 同时进入 | FOUND | 真正的 DomainPack 只有 agent.application v5 一份；publication_evidence 却包含完整 AI/Cloud 教学 Markdown，所以是跨方向发布材料泄漏，不是三个 pack 对象。 |
| 61 stage 在裁剪前全注入 | PASS | stage_blueprints/manifest均6；public原包61。未选阶段语义仍在全局文档/资源审核目录中。 |
| 179章节正文全部进入 | PASS | 179 section 项全部进入，但只有URL/title/review_note/selection_scope等，无 body/content/full_text/markdown/page_content 字段；不是179篇抓取全文。目录审核全文膨胀属FOUND。 |
| source/section/stage/guide/extension 多层正文 | FOUND | 完整 section对象每ID只1份；source.metadata/review_evidence/review_note确有重复审核文本，同一风险说明有3份。stage resources只引用section refs，没有复制全文。 |
| KnowledgeExtension.guidance 精确分片重复 | FOUND | Eval guide117字符在6阶段各出现一次；stage guide4756序列化字符在pack和manifest各1份。未发现递归拼接原始大段章节。 |
| project-study/card 全量 | FOUND | PROJECT_STUDY_CARDS_NORMALIZED.md原文13227字符（JSON值13573）进入publication；Common Core实际项目学习extension0/case-study0，其他路径项目案例语义另测。 |
| exposure/prerequisite 全矩阵 | FOUND | EXPOSURE_MATRIX_ALL.md3674、PREREQUISITE_MATRIX_ALL.md2787原文各1份；metadata.exposure_with另16369 JSON值字符，guide同义事实多层呈现。 |
| practice提前全量 | FOUND | 仅selected6条practice_blueprints、2545JSON字符（非public全部61）；outline其实不消费它们，现有practice_payload才取逐stage条目。 |
| output schema异常大 | PASS | field_shape327字符，不是21万input主因。其resources/extensions字段和通用system要求模型输出受保护事实，增加输出职责；原模型截断正文未保存，具体输出归因NOT RUN。 |
| protected facts进prompt再merge | FOUND | merge_batches强制恢复resources/extensions/guide；模型全文看到它们并非恢复的必要条件，测试已证明最小skeleton也恢复。 |
| 6stage仍带未选关联 | FOUND | 57sources仅12selected；45unselected sources267928JSON对象字符。179sections仅35selected，144未选。knowledge closure仅6，未发现全61知识蓝图。 |
| 同一reviewed section完整正文多份 | PASS | 179section_id均唯一，完整section无重复；197组>=80字符相同叶子产生44456额外序列化字符，不能误报为重复抓取章节正文。 |
| frontend/display-only prose进入 | FOUND | 未发现frontend HTML/页面对象；研究全量项目卡/教学展示正文、完整extensions说明都随整包进入，不属于outline输出职责。 |
| previous plan/history/private | PASS | context只有goal/prefs/manifest/goal_spec；GoalSpec null，prefs为合成默认值，无history/summary/prompt/outcome；服务端scope/lease以下划线字段被适配器排除。 |
| 递归嵌套/重复dump | PASS | domain_pack仅在user顶层1份，非context中再1份；json.dumps(message)再外层HTTP JSON编码为正常字符串封装，无递归堆叠。重复主要是事实对象冗余，不是序列化无限递归。 |


额外统计：>=80字符的完全相同字符串共197组，超出首份的JSON字符44456（7.69% messages字符），阈值以下重复未计；这是不同leaf路径的完全相同字串，不等于全部可无损去重量或独立实际token计量。风险描述常在metadata、review_evidence.chapter_review.risks、review_evidence.teaching_weaknesses出现3份。reviewed section整体179个ID均唯一。6个stage guide总4756JSON字符在stage蓝图/manifest各1份；同一Eval guide117字符重复6份。职责投影优先于全局字符串去重。

## Root cause / 调用链

1. `map_semantic_content.py:441–442`同时保存metadata和source_review_record（review_evidence）；`:640–645`为每pack附入全部14个surrounding Markdown，包括AI/Cloud/RL/未选Recipes和项目卡。作为本地发布审核证据有意义，不等于模型每请求需要。
2. `semantic_content.py:39`深拷贝public包，`:105–112`裁剪stage/knowledge/practice，却不裁剪resources/resource_refs/publication_evidence。因此6阶段仍带57source/179section及14全文文档。45未选sources267928JSON对象字符；35选中章节之外144项仍可见。
3. `nodes.py:550–566 generate_skeleton`将完整manifest和完整domain_pack送入outline。`openai_compatible.py:169–175`仅把domain_pack从context挪到user顶层，不限制其字段；序列化上述整包。
4. `freeze_manifest`包含guide，pack stage又包含guide，两者同时发送；mapper审核对象还有相同叶子冗余。
5. `SHAPES['planning.outline']`和通用system让模型生成resources/extensions并同时提structure/practice职责，但 `nodes._validate_skeleton`实际只要求冻结keys顺序和非空标题；`merge_batches:498–504`之后直接用本地reviewed数据覆盖resources/extensions/guide。输出职责过宽有代码证据，但v6.5未保存截断模型正文，**不能证明具体多少输出token被resources/extensions占用**。不把输入膨胀与输出截断的全部因果合并成已验证结论。

最终 **MULTIPLE_CAUSES_CONFIRMED**：未选资源/发布全文越过prompt职责边界，审核事实多重表示，以及模型承担了已由确定性merge接管的输出字段。没有网络/模型tokenizer实验来补猜测。

## Outline职责A/B/C

**A 模型需要看**：synthetic/user goal、原GoalSpec/starting_point/constraints（有则投影，无则null）、prefs，已经由代码选择并冻结的stage key顺序、短title/objective/capability和前置key、载体/optional/Recipe gap短语义、outline专用输出shape及个性化边界。现有 `_validate_skeleton`拒绝重排/删阶段，所以推荐不是让模型重新选/排序路线。

**B 全文不需要进outline但必须留本地保护**：精确resource source/version/section refs/role、审核记录、URL/catalog、why_now/guide/practice_delta、extensions/project-card说明和发布证据。完整reviewed Seed、公有catalog、冻结pack/manifest保持；模型看不见不等于删库/删课程/降章节粒度。merge从这些本地权威恢复，Draft只存typed指引和引用范围，catalog解析不依赖模型吐全文。

**C 现有后续逐stage需要**：structure用本stage node_blueprints/required keys/guide/resources引用/外部前置；practice用本stage validated nodes/units、对应practice blueprint/guide；project-study/learning workspace读本地extensions和source索引。无需新增planner/embedding/压缩模型pre-pass/模型请求阶段。

防止转移膨胀：原structure六条完整adapter messages为5481–6237字符（1370.25–1559.25 estimated tokens），不带完整DomainPack/publication；提案不改变这些输入。practice本次只用确定性结构fixture测量为5403–5542字符（1350.75–1385.50 estimated tokens），不是v6.5真实practice证据；同样没有全包。没有把被移出outline的14文档/全catalog搬入structure。

## 两个候选与修正后离线预算

候选均在ignored `var/v66/attribution.py`纯函数原型中构造；只有候选payload/outline专用system/shape变化。**生产函数/配置未实施修改**。

| 方案 | messages chars | 离线estimated input tokens | 与原messages字符减少 | 按原209998字符比例校准（非真实分词） | stage / protected counts | cap |
|---|---:|---:|---:|---:|---|---|
| Option1 frozen skeleton | 4,112 | 1,028 | 99.29% | 1493.69 | 6stage / 6required keys / 18assignments / 35refs / 13extensions / 6first practices | outline4096，structure/repair8192不变 |
| Option2 skeleton plus existing focus projection | 5,634 | 1,408.50 | 99.03% | 2046.55 | 6stage / 6required keys / 18assignments / 35refs / 13extensions / 6first practices | outline4096，structure/repair8192不变 |


与209998比较：Option1启发式1028较实报少99.51%，按原字符比例校准1493.69；Option2启发式1408.5少99.33%，校准2046.55。公平同口径字符/启发式下降分别99.29%/99.03%；前两组不可作为真实DeepSeek token承诺。没有预设10k/20k阈值。

- Option1：goal/prefs/GoalSpec/semantic_context + fixed stage key/title/objective/kind + selected知识title/objectives/前置key。999字符outline专用system，shape只outline_ref/sections(stable_key/title/objective)。模型不看全guide、resource目录、public审核文档、practice蓝图/项目卡；由本地权威保留并回填。语义风险低但要求legacy/frozen格式兼容、真实成功门禁仍NOT RUN。
- Option2：在同一骨架上增加已有why_now/learning_focus/previous_relation/exposure_relation和practice increment的确定性投影，不使用模型摘要；增加1522字符。职责稍宽，当前测试没证明这部分对outline正确性必需，因此不优先。
- 共同保留阶段6、required keys6、精确资源安排18/section refs35、extensions13、第一实践6；此Common Core原本project-study extension0、case-study0，不能假称本次回填了项目案例。适用项目候选的其他语义路线单独验证。output cap维持4096，structure/repair8192不变，不承诺输出真实成功。

## Deterministic保护与真实缺口

21项离线测试PASS，**不等于全内容保护已PASS**：有诊断测试专门证明现存保护缺口，发现缺口本身的测试PASS。

| 信息/行为 | 本轮状态 | 实际证明边界 |
|---|---|---|
| stage key / 冻结顺序 / required knowledge keys | PASS | 最小skeleton接受；删/重排被拒；6 required keys完整 |
| Primary/Comparison精确role/ref/version/section scope | PASS | 原Common Core18arrangements/35refs相等，恶意outline改写被权威替换 |
| Case Study / 项目学习候选 | PASS | 原Common Core数量0；其他5场景逐项资源与optional项目extension语义核对，未编造本Run案例 |
| why now / guide / exposure | PASS | frozen guide和typed projection等价，无outline全文也恢复 |
| reviewed extensions / project semantics | PASS | 13extensions逐项相等，optional/replaceable保留 |
| 第一practice goal / original acceptance包含 | PASS | 6首任务恢复curated事实；不证明额外冲突已被拒 |
| Starter optional / user project priority / open Recipe / Voice gap | PASS | 五语义场景+开放缺口fixture，无原pack变更 |
| Evaluation横切 / RL optional / hold不发布 | PASS | Common Core与适用场景规则核对；hold未进published resources |
| 知识title/objectives/scope/acceptance全部确定性保护 | **FAIL** | 唯一节点title/objectives可被structure改写且通过validator；scope/acceptance未投影/回填；仅重复曝光节点canonical overwrite |
| 次级practice与冲突验收要求 | **FAIL** | 只保护task_index0并union；第二任务强制Starter及首任务额外冲突验收可存活且通过validator |
| PG source-index解析/正式发布/Chrome/真实模型 | **NOT RUN** | 本轮禁止这些服务；本地完整catalog留存，不冒充下游真实服务验证 |

上述两类FAIL是**既有**缺口，旧全量outline也不能消除，当前提案不改structure/practice合并和validator，不能用继续发送全文来掩盖。移除outline可见性没有删除local pack，也不降低这些现有门禁。下一真实代表之前需要这些保护的明确验收，不在本轮追加业务修复。

## Tests / 可复现证据

- `python -m pytest var/v66/test_attribution.py var/v66/test_rehydration.py -q -p no:cacheprovider --junitxml=var/v66/offline-tests.xml`：**PASS21**，exit0。
- attribution精确字符相加/重建稳定：PASS；原baseline未选资源FOUND，candidate no-unselected全文测试PASS。
- no-duplicate section正文：PASS（实测全文字段不存在、ID唯一）；相同审核leaf与guide重复FOUND且计数可复现。
- outline职责/恶意字段隔离/最小skeleton deterministic merge+Draft projection：PASS。
- travel/no-project/Voice/NodeCloud/AI已有项目：PASS；无真实账号/历史/外发。
- 最后21test输入已包含改后的HTTP byte计量。首轮归因脚本NameError和合并测试首轮局部变量遮蔽20PASS/1FAIL已修正；`offline-tests-first-failure.xml`保留；子代理首轮tuple/list比较错误亦记录。未改生产来掩盖失败，未重复收费。
- 真实PG/Chrome/provider/tokenizer：NOT RUN；所有capture/Fake结果与v6.5真实usage分列。禁止socket/DNS/httpx sync/async和psycopg连接。

本机ignored证据：`var/v66/exact-outline-body.json`、`exact-http-body.bin`、`initial-sizes.json`、`attribution.json`（完整组件及Top20/重复路径）、`candidate1-body.json`、`candidate2-body.json`、`rehydration-evidence.json`、`offline-tests.xml`、`baseline.json`、`final-invariants.json`。精确重建体仅含原公共审核包+synthetic，不输出key/password/DSN/用户私正文；原v6.5凭据目录未读取。

## 唯一推荐最小patch（提案，不实施）

选择 **Option1：冻结阶段骨架投影 + outline专用输入/输出契约**。复用现有选择/manifest/structure/practice/merge/Draft，不让模型二次规划路线，不新增API/DTO/迁移或模型阶段。

最小代码面与兼容条件：

1. `planning_batches.freeze_manifest`允许一个可选outline格式标记，默认legacy；`PlanService._freeze_submission`只对**未来新提交**冻结该标记并由现有manifest hashing覆盖。不改已存在manifest/checkpoint/旧Run，不手动改v6.5或重派unknown。
2. `PlanningNodes.generate_skeleton`在新格式标记下调用局部pure projection，只送上述4112字符候选所需输入；无标记的旧Run保留当前构造。完整pack仍在冻结initial，用于后续确定性恢复。
3. `OpenAICompatibleLLM.generate_structured`仅对带新outline格式的planning.outline选择短system/shape；marker通过内部payload随attempt fingerprint绑定但不外发。**不全局修改prompt_version**以免旧structure/practice/retained attempt fingerprint失配；旧格式仍用旧模板，模型/cap/provider/thinking/budget不改。
4. 下一patch门禁须加legacy wire等价/new冻结marker与hash/新outline最小输出/恶意事实回填/未选内容隔离/五场景/不膨胀structure性质测试；上面既有知识/次级practice保护FAIL独立登记，不能声明完整门禁绿。

这一格式标记是现有immutable manifest的小字段，不是新调度/第二planner。投影算法与template只影响模型可见性/要求的outline输出，课程权威内容与merge规则保持。marker设计/legacy指纹验证尚未实施，状态NOT RUN；不得把纯原型测试写成生产patch已经PASS。

收益：移出约99.29% messages字符和模型不需要生成的资源/extensions字段，不扩大输出cap、不删reviewed内容、不转移到structure。回滚：本轮无生产改动无需回滚；后续patch可停用未来新格式提交并保留两格式读取，撤回局部projection/template。已冻结的新格式Run必须按其冻结版本读，不在执行中静默改回旧payload；quota/旧Acceptance/v6.5请求不可撤销或重用。部署/真实验证仍有独立授权门禁。

## Final / STOP

**MULTIPLE_CAUSES_CONFIRMED**。本轮完成离线精确重建、归因、15项核对、职责分工、两候选预算、21 Fake/contract tests和保护缺口揭示；完全离线收费0、24/50保持、业务配置/原库/UI/阶段规则不变。

唯一下一动作：另行审批并实施上述有版本边界的Option1局部patch，先离线验收；本轮不执行patch、不收费重跑。整体继续**STAGING_BLOCKED / NOT_READY**，STOP。
