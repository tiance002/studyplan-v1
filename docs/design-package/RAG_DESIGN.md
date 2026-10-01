# 检索与证据边界

2026-10-01 / S0。StudyPlan 依赖 KnowledgeRetrievalPort 能力，复用当前 `backend/app/ports/rag.py` 的 RAGPort/Evidence/Citation 并增量适配，不维护并行检索接口或第二套索引引擎。

## 目标契约

`retrieve(query, scope, filters, limit) → Evidence[] | RetrievalUnavailable`。scope 由服务端产生；filters 明确 project、资源集合、版本、语言和媒体。未知/越界 filter 拒绝；未经授权来源不返回。当前接口只含 scope/query/limit，filters 与版本支持在 M3 补齐。

检索 Evidence 需 evidence_id、source_id、source_version、URL/章节/时间点、短片段、retrieved_at、授权范围和来源核验状态。检索分数不等于教学质量或用户能力。实践成果 Evidence 使用独立业务类型，禁止混用评级。

## 逐步采用的管线

Query → Restricted Rewrite → Keyword/Vector → 可选 RRF/Dedup/Version Filter/Reranker → Evidence Gate → ContextBuilder → LLM → Citation Verification。复杂阶段按实际需要启用；V1 可先资源索引/关键词及个人 RAG Adapter。个人 RAG 路径/服务契约当前未核对，接入前做只读 capability/license/版本清单，不阻断 M2。

Restricted Rewrite 保持原目标/scope，不扩大授权资料。Evidence Gate 检查可用、相关、来源/版本；证据不足允许一次有界 targeted retrieval，仍不足则明确反馈缺证据，不通过换强模型猜答案。未许可外部资料请求在调用前拒绝。

引用必须指向本次返回或已核对资源中的真实定位；验证来源、版本与引用片段匹配。不允许模型臆造链接、章节或时间点。生成计划可在检索故障时返回标注的搜索建议；声称基于资料的反馈/验收必须报告证据限制。

## 资源存储与输入安全

保存 title/author/source/url/version/sections/node links/media/difficulty/validation_status、检查时间及小型索引。大材料保存 URL/目录/哈希/更新时间，不复制大段第三方全文。优先连贯作者/课程/主项目；重复材料可标计划内复习。

外部页面、检索文本、上传材料都是不可信数据，不能成为系统指令。网络适配器校验协议、私网地址/重定向和大小/时限；前端安全展示。检索异常不回滚学习成果；外部服务不拥有进度或计划写权限。
