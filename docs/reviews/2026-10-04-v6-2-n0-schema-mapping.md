# v6.2 N0 与真实 schema 映射审计

基线：本机实际 HEAD `841ef9e31f0db70af238fa8c89796e3a5cf1c3e1`，分支 `feat/n1-resource-discovery`；git status、branch、rev-parse、log -8 已只读核对。跟踪文件 clean，保护目录不操作。历史 HEAD 祖先 PASS；没有 reset。上一轮业务与验证能力复用，不重做。

输入：用户 v6.2 Goal 与语义校正 ZIP（SHA256 `55523f31a595985b274390f8cf4b5c8a8b80191ca5effafbc3240a10c3094d93`）。23份原始文件逐字节保存于 `docs/research/semantic-corrected-2026-10-04`，INPUT_MANIFEST 记录各自摘要；这里只是研究证据，不是自动发布。核心语义/Seed说明由root读取，三模板/六路径/矩阵/日志/Catalog/项目卡由独立内容代理完整审计；planner由只读代理定向追踪。

## 当前版本与数据边界

真实 .env 产品连接使用 READ ONLY 事务，仅查询 migration/pack key/version/status：migration0023；agent.application v1、python.engineering v1。Registry AI1/Agent4/Cloud1/Python2与三旧专项1。下一版本按max(Registry、现有文件、可见DB)递增为 AI2/Agent5/Cloud2。没有产品写入；测试仅自有 studyplan_test_*，沿用repo0024，无新迁移。后续产品导入前仍须重新核对版本冲突，不假定本轮可写产品库。

## 分类与实际字段

| 语义要求 | 分类 | 现有表达与差异 |
|---|---|---|
| 三方向与章节骨架 | CONTENT_ONLY | DomainPack published_payload、knowledge/stage/practice blueprints；发布新版本不改旧包 |
| why/JIT/Exposure/增量/exit | DIRECT | LearningGuidance why_now/previous_relation/reading_prerequisites/practice_prerequisites/practice_delta，KnowledgeExtension 与实践 acceptance。NEW在既有 unknown关系+说明表达，不扩大枚举 |
| 章节scope与角色 | DIRECT | public_resource_sources/sections，StageResourceAssignment source_ref/source_version/section_refs/role，保留作者有序范围；切片独立稳定键 |
| review_depth/access/runtime证据 | CONTENT_ONLY | JSON published_payload 元数据与 dated provenance/review_note；物理verification仅reviewed/legacy_index/unverified，不把选段读冒充全仓深读 |
| Starter fallback与用户项目 | THIN_ADAPTER | 现有 GoalSpec target/starting_point/scope/constraints承载私有项目意图，冻结前映射载体和纵切面；merge实践名称固定Pack.title现状须修复。生成的学习PracticeProject记录表示该载体，不宣称重新绑定用户外部仓库或既有DB项目ID |
| 开放0..N Recipe与裁剪 | THIN_ADAPTER | 现有Pack JSON保存开放selection/capabilities；freeze前依目标与知识前置选择阶段，保持原batch/graph/事务。单Pack完整冻结现状不能表达组合 |
| Recipe miss | THIN_ADAPTER | CommonCore+已审局部内容，现有可选extension明确needs_research_or_review，不编造Voice章节、不拒绝 |
| Candidate替换语义 | CONTENT_ONLY / UI_WORDING | CASE_STUDY+REPO+required=false extension，guidance写optional/replacement。当前UI项目标题未明确可选，需最小文案 |
| ZCode2/MaxKB/阿里课时 | HOLD | 4条不得成为已审Primary；原始研究记录保留，不导入公共发布子集 |
| clone/index/新实体/职业归属/第二planner/mastery | DEFER | v6.2明确禁止；既有结构足够，无需新增 |

**不得因为研究包里出现新的抽象名词，就新增数据库实体。**

## 内容证据风险与映射裁决

Catalog86条：82 mapping_ready_review_pending，4 hold；75 selected_sections_read、7 metadata_only、3 deep_reviewed、1 toc_checked。角色primary是切片建议，不是全用户必修。只映射模板/路径实际引用且访问和审读证据足够的子集，不机械导入86条；保留原depth/access/usage/runtime NOT RUN。12卡均optional/root-only/replacement。OpenHands、LangGraph、OTel卡repo URL与catalog docs URL不同，保存卡身份与独立保守入口核对，不借教程深度证明仓库源码深读。

Python中文5.1列表原日志只核目录，不能套用整体selected_sections_read升级；OpenHands security/persistence/sandbox存在section_review_depth=toc_checked。42条exposure relation_tags为空，不自动推断关系，依据矩阵和章节正文映射。当前root-case资源规则保留legacy_index，不改为全仓reviewed。

发布资源全局immutable：新source/section IDs按pack版本命名空间+catalog稳定scope派生，原catalog stable_key作为溯源；跨包不覆写旧全局ID。公共案例不保存commit/branch/path/function，源码定位由既有外部AI Prompt动态完成。

## 实施与验证边界

A：输入/审计提交；B：三新章级包与严格发布子集验证；C：冻结前纯选择/载体适配及最小UI，普通新增规划走现有Graph；旧恢复/已冻结Run不重新适配；D：六条Fake+ownedPG+Chrome、immutable旧计划与保护回归，数据内容变化后owned恢复。root单一契约整合，最多两业务写入者。无收费模型或搜索调用，旧账和unknown不改写。

模型请求：root Sol6.1/high，内容Sol6.1/medium，只读planner Luna/high；实际解析NOT OBSERVABLE。没有Astra/max/全局设置。审计只读证据PASS；新业务/PG/Chrome目前NOT RUN，整体NOT_READY。
