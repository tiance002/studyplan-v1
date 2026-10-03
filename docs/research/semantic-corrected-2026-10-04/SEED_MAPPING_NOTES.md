# Seed映射说明：逻辑可映射，尚未发布

本轮未读取/修改StudyPlan代码、schema、DDL或实际Seed导入器，未写数据库、未发布Seed。因此以下是对现有“资源、章节/知识节点、阶段、实践、项目案例、曝光/前置”概念的逻辑映射，不宣称已经验证物理字段名或当前接口兼容。实施方导入前须只读核对当前数据契约；不匹配处留人工处理，不能猜PK或默默扩schema。

## 可供现有概念消费的字段

| 本包字段/内容 | 映射目标概念 | 映射边界 |
|---|---|---|
| stable_key | 导入时资源查重/外部语义键 | 不是数据库PK；若现有系统无对应列，可在导入映射表中关联现有ID，不要求新列 |
| title/url/language/media_type/content_access/role | 资源元数据与资料角色 | enum有界且值合法；仅按实际已有字段/允许值映射，不将自然语言拼回enum |
| teaching_purpose/usage_conditions | 资源选择说明、目标适配 | primary是特定切片的推荐角色，不是全用户必修；conditional在planner解释 |
| recommended_scope/skip_scope | 章节/章节组、学习与跳读范围 | 保留原推荐具体小节；不能只导入能力名 |
| prerequisite_assumptions/exposure_with | 前置和重复处理 | 源假设不等于用户不会；诊断后JIT，不创建无限先修链 |
| teaching_strengths/teaching_weaknesses | 教学质量与边界 | 用于解释与人工审核，不能自动评分用户 |
| capability_tags/specialization_tags/direction(s) | 开放检索标签/方向关联 | 标签是字符串引用，不创建AgentBranch职业枚举 |
| cost_note/access_note | 费用与访问说明 | 免费阅读与收费实践分开；unknown不能写成free_account或默认Primary |
| review_depth/review_note/reviewed_at/runtime_validation | 审读证据/运行边界 | 深度只对应被读切片；NOT RUN不能映射为运行PASS |
| 章级why/JIT/primary/supplement/Exposure/practice/increment/exit | 教学阶段/知识节点/实践内容 | 每个选中单元保留这些信息；项目increment替换成用户载体仍保持能力与验证 |
| 项目卡9项公共学习字段 | 可选项目案例 | URL/why/focus/prereq/depth/avoid/questions/outputs/migration；不固定commit/path |

## planner runtime语义

用户目标、起点与已有项目；primary_focus/supporting_capabilities；0..N Recipe组合；carrier选择及纵切面；是否需要career overlay；资料缺口needs_research_or_review；用户确认的exit证据与局部计划调整，均先作为规划过程/输出语义。它们不是本轮要求新增数据库列、表或职业路由。

Default Starter是fallback配置，Recipe是参考内容，Project Candidate是可选案例。实现可引用现有内容/配置或文档，不为这轮收口新增复杂关系数据库。一个用户同时组合多专项应由planner处理，不通过单值AgentBranch限制。

## 数据规范与溯源

规范目录保留86条教学切片。相同URL的不同scope_key不自动合并；可在物理层复用资源实体，并分别保存已有章节/推荐范围，具体适配需核对现有契约。stable_key由明确scope_key与canonical URL摘要生成，不取数组序号、标题、日期、commit或PK；同来源重排仍稳定。改变URL或scope身份时显式记录迁移，不偷偷覆盖。

source_review_record保存历史研究信息，其原始枚举说明改名为original_*_note，非Seed字段白名单；审计中的当前源码证据不作为教学路径锁定。reviewed_candidate是候选身份/适配范围的审读状态，不能推导whole-repo deep_reviewed。metadata_only和toc_checked保持原值。

## 发布资格与保留项

- 顶层`mapping_ready_not_published`表示结构与语义可映射，不是每条已获发布批准。
- 普通记录仍是`mapping_ready_review_pending`；本轮目录标准化不自动批准公共Seed。
- ZCode两个同名候选：`hold_identity_review`，不替用户消歧，不推荐默认安装。
- MaxKB：仅metadata候选，`hold_content_review`，不是已审Primary。
- 阿里课程：公开目录称免费但具体课时正文访问未验证，规范`content_access=unknown`与`hold_access_review`，不能用旧free_login_required推断免费账号可读。
- 项目README身份核对：可以做可选案例地图，但不声称源码或运行已验收。
- 退役平台/旧版本API：保留VERSION_CONTEXT与条件，不提升为新的默认平台练习。

公共已审核身份不授予可执行代码、付费调用或账号动作的授权；执行遵循用户当次范围。未知内容可作为标明状态的用户私有候选，不静默提升公共已审核Seed。

## 不建议新增

不建closed AgentBranch enum；不建固定职业归属；不建强制starter/capstone关系；不建固定commit/file-path索引；不建自动mastery/scoring体系；不因新增Recipe就新建复杂表。角色与费用说明不混入enum。能用当前资源/章节/阶段/实践/案例结构表达的内容先复用，实际字段冲突交人工审核。
