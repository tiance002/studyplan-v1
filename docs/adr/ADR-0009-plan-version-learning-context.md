# ADR-0009：稳定知识逻辑身份与不可变计划/学习上下文

- 状态：Accepted（S0设计），稳定身份补齐待M1.2，Session/Reflection来源待M2。
- 保留：ADR-0002三类权威、既有PlanRevision事务/幂等/不可变结构。
- 补充：当前内容hash生成node_id只保证同内容幂等，不代表跨重生成稳定逻辑身份。
- 关联：[DOMAIN_MODEL](../design-package/DOMAIN_MODEL.md)、[Gap B1/B3](../reviews/2026-10-01-v1-gap-analysis.md)。

## 决策

PlanVersion由现有PlanRevision承接；plan_version_id映射现有plan_id，序号revision仅在项目内有意义。结构调整新增版本，不复制另一套知识树或新建并行PlanVersion模型。

knowledge_node_id是项目/DomainPack/审核语义stable_key下稳定的逻辑身份。当前知识内容node_id、单元ID、历史FK和内容快照保留；通过增量身份/内容映射让新版本同时定位逻辑身份和确切内容。新增迁移在0010之后，不重写旧迁移或批量改历史外键。

精确同语义键才可关联；不同pack、同名但含义不同、历史多候选无法证明同一语义时fail closed并提出人工确认映射，不基于标题相似度合并。内容/rubric变化保存新内容版本，旧节点学习结论只对原目标/版本有效。

Session/Reflection/PracticeSubmission/Acceptance保存原plan_version、逻辑节点、content/rubric版本和source event/证据引用。当前路线改变不重挂历史。Summary只导航，不删除原事件；重开旧Session恢复旧学习现场。

## 后果与备选

逻辑身份与内容分别版本化，支持稳定进度和真实历史；增加必要映射/FK/读模型工作，M1.2须验证数据完整性。拒绝重命名PlanRevision后另建一套版本表、按最大revision判定当前、全内容hash当知识身份、原地覆盖内容、把旧成果自动视为新目标已核验。

## 验收

同项目/pack两版只改局部内容，未变语义节点逻辑ID相同；新版本读到正确内容，旧版本/总结/成果仍读原内容。冲突映射不自动合并；重复发布同结果，失败/取消不改变当前引用。
