# 相对上一轮研究包的变更

基线：Library中较新的STUDYPLAN_THREE_DIRECTION_REVIEW.zip；本轮读取的字节与上一轮交付本地包一致。原包18文件保持不变；语义校正版作为独立交付。任务日期2026-10-03，收口2026-10-04。

| 原内容 | 新内容 | 变更性质 |
|---|---|---|
| AGENT_APPLICATION_TEMPLATE_DETAILED.md | AGENT_APPLICATION_TEMPLATE_PRODUCTIZED.md | A0–A8、章节/实践/exit保留；默认项目fallback、开放Recipe组合、Common Core边界、Career overlay |
| AI_FULLSTACK_TEMPLATE_DETAILED.md | AI_FULLSTACK_TEMPLATE_PRODUCTIZED.md | 0–10及FastAPI前Python JIT保留；项目可替换，单人/团队/多租户按目标 |
| CLOUD_SERVICES_TEMPLATE_DETAILED.md | CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md | -1–13及教程细节保留；用户服务优先、K8s/微服务独立实验、实际分支替换 |
| 6份专项/能力路径 | 同名语义校正正文 | 4 Recipe、Evaluation横切、RL可选；章级细节及实践未删 |
| 3份DEEP_REVIEW | 同名语义校正正文 | 研究发现不变；项目与职业表达降为候选/目标overlay |
| 两份矩阵 | 同名语义校正正文 | JIT/Exposure原则不变；用户载体、开放组合说明新增 |
| PROJECT_STUDY_CARDS_ALL.md | PROJECT_STUDY_CARDS_NORMALIZED.md | 真实项目卡逐项标reviewed_candidate/optional/替换；Task Service自建卡转入starter语义；AgentScope已有卡汇入候选索引 |
| RESOURCE_CATALOG_DRAFT.json | RESOURCE_CATALOG_NORMALIZED_DRAFT.json | 原86教学切片全保留；enum拆说明、稳定键、开放标签、源审读溯源；未新增资源研究 |
| FINAL_THREE_DIRECTION_REVIEW.md | SEMANTIC_CORRECTION_REPORT.md、PLANNING_SEMANTICS_STANDARD.md等 | 一页产品语义摘要、规划算法、Recipe规则、starter定义、映射边界与YES/NO自检 |
| RESEARCH_LOG.md | 同名历史审计+本轮语义记录 | 保留实际审读/NOT RUN；新增基线、转换、QA、无新增补查说明 |

未改变：Hello/LCC编号与章节关系；All-in-RAG术语/示例边界；permission≠sandbox；checkpoint≠exactly-once；FastAPI教程认证与标准的冲突；免费阅读/付费实践分离；Eval-Lite提前、系统评估与训练后评估分层；稳定发行优先；JIT三条件与局部Spine连续性。未改变阅读深度、未声称新运行结果。

新增语义而非新课程：Common Core/能力模块/Recipe/横切/训练专项/Starter/用户项目/案例的定义；0..N组合与未命中回退；可替换Continuous Outcome Carrier；面试/模型路由仅目标触发；候选提案与公共审核分开。

本轮没有新增专项研究、没有新增未经研究的项目卡；未将Vercel Chatbot/KubeSphere/Sealos/1Panel等举例自动列为已审公共候选。没有修改StudyPlan代码、数据库、schema或Seed。
