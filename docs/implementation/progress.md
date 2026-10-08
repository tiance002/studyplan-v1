## 2026-10-08 Planning V2 Item8 R1：LOCAL_REVISION_PASS / CONTINUING_R2_R3

- R0本地checkpoint f0a7a04a21c80afac9d3c839af6fafdef923e6f9；[Item8报告](../planning-v2/ITEM8_REPLANNING_REVISION.md)记录受控future说明/完整合法排序→Compiler→新Draft/hash→明确确认→原子Revision。typed revision context进入现有JSONB/hash，source/required/project事实保持原权威；自由文本待澄清，不使用is_semantic=false。
- fresh-context独审PASS，关闭连续Revision历史保护/消费者丢失，以及成功幂等重放错误hash/version问题；可信未知领域approval可服务端注入，默认缺失fail-closed，默认未知领域Local未装配/PG-HTTP NOT RUN限制明确保留。历史Source/Exposure/Summary/Prompt/Practice/验收只读保持，第2/第3Revision workspace精准引用原第1版；新位置不伪造progress/mastery。
- 核心8unit+10ownedPG=18PASS，受影响快照/发布50PASS；两个不同cookie/CSRF/PG HTTP用例PASS、DTO2PASS，不累加重叠复测。原HTTP预期422/领域400及其他中间FAIL保留，按实际handler修测试定向PASS；Ruff/diff PASS。业务/checkpoint新owned库保留、roles_created=[]、无migration或正式数据写入。产品模型/搜索/Reader0，public generate503，不push/merge/deploy，不进入Item9。R1本地checkpoint后按连续授权进入R2预算/同链重规划。

## 2026-10-08 Planning V2 Item8 R0：PRECHECK_PASS / CONTINUING_R1_R3

- 基线6b291d10ab439bc37a540a626174941cc90fd28b/feat/n1-resource-discovery匹配，tracked clean；[Item8报告](../planning-v2/ITEM8_REPLANNING_REVISION.md)记录连续R0～R3授权与边界。有界现有组件核对和fresh-context独审PASS，无合同或必要migration阻塞；本checkpoint为只读预检，unit/PG/HTTP NOT RUN。
- 复用Item7 Compiler/typed snapshot/Draft/Publication/current/history；旧PlanChange/PracticeChange缺snapshot会被marker双向保护拒绝，不能原样恢复旧Seed/selector语义。stage complete由同版本Summary+用户accepted任务推导，Exposure completed不等于掌握；新basis需含heads/reviews与来源/结构。
- 下一仅有界future说明/顺序Local、明确GoalSpec进入同Item1～7 Semantic、typed lineage及祖先/sibling预算累计；未知文本待澄清。每阶段独审与本地checkpoint，产品模型/搜索/Reader0、正式generate关闭、不改正式数据/迁移，不push/merge/deploy，不进入Item9。

## 2026-10-08 Planning V2 Item7 P1～P3：IMPLEMENTATION_COMPLETE / ITEM8_NOT_STARTED / STOP

- 本轮Start f1f3d139d197c29e8d76a0d5d0ce87a045278f4f；P1本地52a326bf5d11d297fd47623cea346d4f6b55ff0e、P2本地f7eeab33eeb59d6824b2bc23d3e1a355c3a83340；P3最终SHA见提交后交付回执。[统一报告](../planning-v2/ITEM7_PLANNING_EXECUTION.md)前置当前交付且逐字节保留原P0失败记录，[P3报告](../planning-v2/ITEM7_P3_RUNTIME.md)记恢复边界与独审闭环。
- 实际链为现有Worker/Run/Job→V2 Item1～6→确定性Compiler→typed单事务Draft→明确当前hash确认→原子Revision/current/history。受控owned202路径显式装配，默认产品工厂不启用，正式public generate503，无旧outline/structure/practice权威。
- P1/P2独审已PASS；P3独审主动关闭正文receipt/usage、错误分类、预算重放、Domain精确额度、checkpoint身份、candidate计数、Run终态和实际Worker接管等问题。最后Composer预算反例实际RED1FAIL→GREEN3PASS，Item6原合同不动。P3主PG20PASS、预算5PASS、传播3PASS，去重25不同用例；真实HTTP1PASS、DTO9PASS、相邻3文件23PASS，collection26PASS、Ruff/diffPASS。原恢复16PASS1FAIL及Composer RED保留，不隐瞒失败或重复累加。
- 真实新owned业务/checkpoint PG，既有0025/现有PostgresSaver初始化、roles_created=[]、库保留；成功receipt缺全部checkpoint重建同Draft/hash，实际新Worker租约接管零重复派发，旧fence拒绝。unknown/pending不重派；纯body成功但未有Reader成功receipt保持阻断，不冒称自动恢复。
- 产品模型/搜索/Reader0；历史unknown177/183、378证据、.env、旧Item6样例和历史progress保全核对。无架构/Policy/Prompt/Schema/Seed/审核映射/迁移/正式数据改动，不push/merge/deploy。主协调请求Sol6.1 high、关键实施/独审xhigh，实际解析NOT OBSERVABLE。
- 真实外部语义、官方未知领域证据、教学质量、浏览器与完整用户E2E NOT RUN；Assistant仅共享context/PG helper核对，完整会话NOT RUN。全产品仍NOT_READY，不自动进入Item8；本地P3checkpoint后STOP。

## 2026-10-08 Planning V2 Item 7 P2：PERSISTENCE_COMPLETE / CONTINUING_P3

- P2 基线 P1 checkpoint 52a326bf5d11d297fd47623cea346d4f6b55ff0e；[P2 报告](../planning-v2/ITEM7_P2_PERSISTENCE.md)记录显式 typed snapshot、单事务实体/Draft、当前 hash 编辑重编译、明确确认、Revision 与正式消费者。无 migration，公共来源只读，研究资料不升级资格。
- fresh-context 独审主动发现 Run/fence、首次 public 来源替换、compiled/Manifest 重哈希分叉及历史空约束快照兼容四项，分别 RED→GREEN，最终独审 PASS。Compiler/Snapshot 69 PASS（含原P1 62），相邻定向114 PASS；真实 owned PG20 PASS+新增fenced正例1 PASS；真实Cookie/CSRF/scope编辑确认/current/history HTTP1 PASS；DTO契约9 PASS；Ruff/diff PASS，不累加重复测试冒充全新覆盖。
- 仅新 owned PG 写入、现有0025、roles_created=[]，库及每次身份回执保留。真实产品模型/搜索/Reader0，正式库/历史证据/.env/旧样例不改，public generate503。真实教材语义/浏览器/全产品E2E NOT RUN。
- 本地 P2 checkpoint 后按用户连续授权进入 P3；不 push/merge/deploy，不进入 Item8，尚不声明完整 Item7 或产品 READY。

## 2026-10-08 Planning V2 Item 7 P1：COMPILER_COMPLETE / CONTINUING_P2_P3

- 基线 f1f3d139d197c29e8d76a0d5d0ce87a045278f4f；[P1 报告](../planning-v2/ITEM7_P1_COMPILER.md)记录完整字段流向与 P2 最小承载方案。新增纯 Compiler/Manifest，保留冻结课程、Profile、能力、来源、约束及项目事实，不补课程或生成 DB ID。
- 独审发现资料资格一致重算 hash 晋升及未知 accepted_known 误拒绝；同批 RED 5 FAIL 后修复，独立定向复核 PASS。最终 Compiler 62 PASS，直接受影响回归 56 PASS（不累计重复用例），Ruff/diff PASS。原完整样例 digest 002f913c52b7a9fbc002c83d4da9948865a3d76fc0d7a2f597db5f4ff42a9ce0；不完整拒绝；原样例字节不变。
- 本 checkpoint 产品模型/搜索/Reader/DB 写入 0；PG 持久化、事务、恢复、浏览器和真实教学语义 NOT RUN。既有 PG 角色只读预检满足要求，不修改全局角色。P2 拟在已有 JSONB 中增加 typed V2 snapshot，section_kind=v2_curriculum 仅协议 marker，真实 role 独立读回，须双向绑定与真实 PG 验证；无 migration。
- 用户最新授权连续 P1→P2→P3，每阶段独审和本地 checkpoint，无需阶段间再授权；遇冻结合同/核心语义/必要 migration 或无法关闭完整性问题仍 STOP。真实外部调用保持 0，公开 generate 关闭，无 push/merge/deploy；ITEM8_NOT_STARTED。

## 2026-10-08 Planning V2 Item 7 P0 上游修复：RESOLVED / DOMAIN_LIVE_PENDING / P1_P3_NOT_STARTED / STOP

- 基线 `5ca50020864bae52475fd0318a35677bb7ef203f`、`feat/n1-resource-discovery` 匹配；保留原 P0 报告字节/hash 与下方完整历史。[修复报告](../planning-v2/ITEM7_P0_UPSTREAM_UNBLOCK.md)记录三项上游修复、证据和限制。
- Item5 不再因任意硬约束拒绝全部研究：完整表达闭集选择实际事实检查，可信 reviewed/free 教材可复用；禁止联网仅本地复用，未知/歧义/强制中文仍 pending。Item6 根据实际选中教材访问证明、实际 carrier 与未解决事项判定，原文及source_refs保留；只读等无法证明的限制不放行。
- 新增有界来源验证 producer，复用实际安全 GitHubTeachingBody + ResearchSession；服务器固定来源/pins/定义与公开许可。源审批供 Item2，实际冻结Plan由服务器再绑定；统一扩展描述贯通 Research/Reader/Curriculum，fixture 默认不能进入正式Provider。独审复现同会话重派及整体Plan替换，RED3FAIL后修复：成功/失败/snapshot不重派、审批绑定实际Plan。
- 定向包PASS：约束22；研究/课程/Provider/JSON/fail-closed260；领域/Item2/Provider150；独审修复后领域/Provider98。包间重叠，不相加冒称不同用例。collection147PASS、独立只读审查PASS、diff及新增/受影响Ruff检查PASS。完整Provider Ruff两处基线E701为FAIL，未扩修旧助手逻辑。
- 实际本地MCP索引/版本/freeproof用于机械代表，ROS2来源/模型/Reader输出为合成，经实际adapter+Mock验证，不冒称真实语义。生产官方registry/pins、技术定义审核、真实来源/模型质量仍DOMAIN_VERIFICATION_LIVE_PENDING；进程内issuer不能替代持久Receipt/恢复。
- 真实产品模型/GitHub/Web/Reader调用0、数据库写入0；真实PG/行数、浏览器、Compiler/Worker/恢复NOT RUN。.env、378历史证据及未授权源码hash保持；无Policy/审核映射/Seed/架构/迁移/Runtime修改，无unknown重派、push/merge/deploy。仅本地提交；ITEM7_P0_CONSTRAINT_BLOCKERS_RESOLVED；ITEM7_P0_UNKNOWN_DOMAIN_STRUCTURAL_PATH_RESOLVED；DOMAIN_VERIFICATION_LIVE_PENDING；ITEM7_P1_P3_NOT_STARTED；STOP。

## 2026-10-08 Planning V2 Item 7：PRODUCT_FIT_BLOCKED / P1_P3_NOT_STARTED / STOP

- 基线 `5ca50020864bae52475fd0318a35677bb7ef203f`、`feat/n1-resource-discovery` 匹配，tracked clean；只读核对上位合同及当前 Item1～6、数据库/消费者接口。仅新增[Item7 P0报告](../planning-v2/ITEM7_PLANNING_EXECUTION.md)并前置本进度，旧正文完整保留；受保护未跟踪目录不动，未提交/推送/合并/部署。
- P0 **FAIL**：Item5任意硬约束直接 `constraints_pending`，在审核/免费证明复用和研究前阻断；Item6任意约束非空强制incomplete。真实本地MCP review/freeproof对照：无约束可complete，免费约束即使gap/unresolved皆空仍incomplete；reviewed复用无约束resolved、有约束unresolved，均零外部派发。属于产品符合性机制阻塞，不误报外部证据NOT RUN。
- A/B合成受信选择经实际接口保留accepted_known、B-only Coverage/Gap、项目carrier和MCP学习/项目用途分离，但研究全部constraints_pending。B仅json.cli诊断，不冒称独立异常处理或中文适配完整验收。C采用单一RAG代表：Item2 needs_verification，注入明确fixture证据后Item5仍public_descriptor_unapproved，Reader也只允许固定Policy；缺生产验证producer和受信公开投影消费，不能只靠Item7接线解决。
- 诊断断言PASS（产品P0仍FAIL）；4既有定向用例PASS。HTTP首次因全socket禁用误伤Windows asyncio self-pipe为1FAIL；只修ignored runner允许本地self-pipe、禁止外联/DNS后仅复核该用例1PASS，五个不同用例最终PASS，公开generate认证后503/零storage access保持。独立只读审查PASS并确认STOP及fixture质量限制。未重复宽范围回归。
- 仓库迁移单链head0025，真实PG applied version/行数NOT RUN；现有Draft/Revision hash/序列化/消费者只做字段清点，未宣称V2无损保存或无需migration。P1 Compiler、P2持久化/确认、P3 Worker/receipt/checkpoint/durable预算/恢复/owned HTTP全部NOT RUN且未开始，不创建实现占位。
- 真实产品模型/搜索/Reader/用户DB写入0，未创建Run/Job/Draft/Plan；历史183/280及unknown177/183保留不重派，378份历史证据和.env保持。源码/Prompt/Schema/Policy/审核映射/Seed/架构/Runtime/UI/migration均未修改。先评审上游有限约束适配及有界领域验证/安全公开投影，不能删限制、放宽Validator或固定Recipe追绿。主协调Sol6.1high、链路/独审Sol6.1medium、清点Luna medium请求，actual均NOT OBSERVABLE。ITEM8_NOT_STARTED；STOP。

## 2026-10-08 Planning V2 Item 6：CURRICULUM_COMPOSITION_COMPLETE / ITEM7_NOT_STARTED / STOP

- 基线 `b707ad8d667b2cd9c3f47ea87a7c5fa177ef2ad1`、`feat/n1-resource-discovery` 匹配、tracked clean；有界核对 Item6/7、Single Authority、Matrix 与现有教学实体。共享端口与 ResearchSession 可复用，无新搜索/预算平台。[本轮报告](../planning-v2/ITEM6_CURRICULUM_COMPOSITION.md)记录完整合同、代表课程和限制；九文件本地提交，未改上游 Policy/Schema/审核映射、Seed 或架构。
- 新增冻结 CurriculumContext/Plan、共享领域 Validator、单次 CurriculumComposer、专用 `planning.curriculum_composition` / `CurriculumPlanV1` Provider协议。只编排 B 类，A只满足前置不回流复习；真实DAG支持跨阶段和阶段内有序教学。知识/单元/rubric/指导/PracticeDelta/任务验收及成果有结构化 outcome 关联，无额外教程正文。来源、受信版本、hash、原用户项目/约束由服务器保留 compile snapshot，模型不能改写。
- 同时消费 Item3 reviewed content 和 Item5 research_checked；实际MCP v8 roles/interfaces+freeproof按现有证据冻结，minimal_connection研究及课程输出为合成fixture，不冒充正文或真实语义通过。同ID/version不同审核/免费事实不互借；缺教材/免费证明、未选合格案例、未判定硬约束保持incomplete。用户项目持续实践与whole_core/slices他人项目学习分开，MCP project_usage excluded仅micro，不强制主项目接入；interview不扩课。
- 同一session预算预留实际Provider输出cap和总请求/最坏费用；条件项目search1HTTP、inspect最坏3HTTP/256KiB先预留，不读取源码、不引入Reader/第二模型。qualified未选保case_selection_pending、零搜索。unknown保pending/block，可信已观察超额升usage下界不重派；Item7 reconciliation须避免二结算。成功receipt/持久化/并发互斥未实现，不把内存snapshot当恢复能力。
- RED Domain31FAIL、App25FAIL、Provider2FAIL保留；引用排序及unknown字节超额各1FAIL、独审两项2FAIL后局部修复。最终新三套件92PASS（51+28+13），受影响既有Provider/Reader/JSON与failclosed77PASS，合计169不同用例PASS，collection169PASS，Ruff/最终diff见报告。独立只读审查PASS，两项阻断关闭，最后源码差异与报告/证据有限复核无剩余具体阻断；未重复全量Backend。
- 产品真实LLM/GitHub/Web/Reader/DB调用0；历史183/280及unknown177/183保留，不重派。无Run/Job/Draft/Plan mutation、migration、Worker/Runtime/UI接线或public generate开放；真实PG行数/浏览器/外部接口/课程教学语义/Item7编译/E2E均NOT RUN。Item1条件接受、Item2语义待整链及Item5 Web正文/约束适配/持久化边界保留。
- 本地提交消息 `feat(planning): add v2 curriculum composition`；精确Final HEAD见最终答复及ignored final.json。主协调请求Sol6.1high、引用/预算Domain Sol6.1xhigh、App/独审Sol6.1medium、实体清点Luna medium，actual均NOT OBSERVABLE，不改全局配置，不用max/Astra。未push/merge/deploy；ITEM7_NOT_STARTED；STOP。

## 2026-10-08 Planning V2 Item 5：TEACHING_RESEARCH_COMPLETE / ITEM6_NOT_STARTED / STOP

- 基线 `37871f0fd861810bcb67c76d02cb96819722dfc1`、`feat/n1-resource-discovery` 匹配、tracked clean；先有界审计旧端口/安全/Provider/预算，再明确11文件所有权。[本轮报告](../planning-v2/ITEM5_TEACHING_RESOURCE_RESEARCH.md)包含字段、复用、真实本地审核依据及限制。未改Item1～4、Policy v2、Seed/审核映射、架构；既存排除目录未访问/修改/提交。
- ResourceResearcher仅消费冻结B missing outcomes，校验Gap/Plan/Coverage/Profile与actor/project/session来源；精确保留required/recommended、depth/text/refs及内部起点/事实。先scoped review+freeproof复用，再GitHub工程教程候选，Web仅不足时发现候选；标题/README/mainline_candidate不等于正文覆盖。真实本地MCP v8 roles/interfaces沿用既有review_record与实际free_public，不伪造正文hash/继承TOC资格；新正文只得research_checked，不晋升公共reviewed、不定课程角色。
- 最小正文适配复用固定GitHub pinned transport：README索引最多一章、2HTTP/64KiBwire/16KiBtext/15s，MIME/encoding/path/IP/TLS/禁代理重定向重试；git-blob版本+textSHA/chunk/location绑定。独立Reader purpose复用原LLMPort/Provider，仅批准Policy原文+匿名known IDs，无tools/DB/课程权限；finally清正文，result/cache/snapshot/receipt只留metadata与有界短意见，拒绝整chunk及跨字段分段复制。
- 共享预算reserve-before-dispatch，未知cost/token保worst，unknown/pending恢复阻断不重派。独立审查首轮FAIL发现分段正文、多指标超额漏记费用、completed错源回放；同批RED+局部修正后复核PASS，含跨repo缓存绑定、known失败后续research_stopped。typed snapshot不代表持久崩溃恢复，Item7仍须接实际预派发保存/总账/fence/reconcile。
- 有效RED：Research16FAIL、Body75FAIL、Reader11FAIL+隐私2FAIL+单字段echo2FAIL+分段echo2FAIL，HARD同批23FAIL21PASS；最终新定向144PASS（Research44+Body83+Reader17），既有资源75与Provider/failclosed60PASS，共279不同用例PASS、collection279PASS、Ruff/diff PASS。SSL guard/runner root import环境失败原证据保留后定向修正；Fake/Mock不证明真实Reader教材语义，未重复全量Backend。
- 820受保护tracked文件除允许Provider22行外、378历史账本、.env与旧progress全文保持。产品模型0/真实搜索0/真实Reader0/DB0；账本183/280、unknown177/183不动，无Run/Job/Draft/Plan mutation、migration、Worker/Runtime/UI接线，公共generate仍failclosed。真实PG行计数/浏览器/外部API/Reader语义/全量Backend/整链E2E均NOT RUN。
- 未评估hard_constraints保留constraints_pending且不外发；未知领域无批准publicdescriptor为unresolved；Web仅候选；旧搜索无typed dispatch/usage为search_unclassified保预留并停止；URL缓存仅同冻结Run metadata。无合适免费资料/预算不足保留required缺口。Item1条件接受、Item2真实语义待整链限制不变。十一文件本地提交消息 `feat(planning): add v2 teaching resource research`，Final HEAD见最终答复与ignored final.json；主协调请求Sol6.1high、NORMAL/独立审查Sol6.1medium、安全及预算/引用具体缺口HARD Sol6.1xhigh，actual NOT OBSERVABLE。不改全局配置、不push/merge/deploy；ITEM6_NOT_STARTED；STOP。

## 2026-10-08 Planning V2 Item 4：RESOURCE_GAP_EXTRACTION_COMPLETE / ITEM5_NOT_STARTED / STOP

- 基线 `2ef6f2ac16b4bc35a1bf1a826b3febcff4db406f`、`feat/n1-resource-discovery` 匹配，tracked clean。只新增纯领域 `extract(CapabilityPlan, CoverageResult)->ResourceGapSet` 与定向测试；[本轮报告](../planning-v2/ITEM4_RESOURCE_GAP_EXTRACTION.md)记录字段、接口、代表结果及信任边界。Item1/2/3、Policy v2、原审核映射、架构和历史报告不变。
- 仅B学习集合：full无gap，partial仅missing，none把该能力全部missing合成一项；ID/文本从冻结Plan原样取出，importance/depth/requirement_refs精确保留，policy-only系统性MCP空refs合法。A Python不形成资料需求，全部full或B为空正常空gaps，不制造Item5工作。两个source hash绑定Plan/Coverage，结果使用既有canonical hash约定。
- 复用Item3冻结Plan检查，明确拒绝错误来源/计算hash、v1/改写文本、额外/重复/过期/遗漏或交叠outcome及状态不一致；typed引用只核结构，不读取Index/正文或重判review。原始dict不当作冻结输入；双输入hash不证明缺失Profile/完整Index真实性，仍依赖上游，不新建parser/版本平台。
- API stub先RED28FAIL/0ERROR，GREEN28PASS。统一定向36PASS（新28含真实MCP接口2+Item3 hash/validator6+failclosed2），同范围collection36PASS，Ruff两文件/diff PASS；独立有限审查PASS，无剩余BLOCKER。真实既有MCP窄概念full为空、applied partial仅minimal_connection；ToolCalling none精确保留两项。合成fixture只证明转换算法，不冒称新教材审核或产品语义通过。
- 817受保护tracked文件、378历史账本、.env与旧progress全文保持；产品模型0/搜索0/Reader0，账本183/280、unknown177/183未重派。无DB/Run/Job/Draft/Plan mutation/迁移/UI/Worker/Runtime接线，公开generate仍failclosed。真实PG行计数/浏览器/产品模型/外部接口/正文审核/全量Backend/整链E2E均NOT RUN，Item1条件接受和Item2真实语义待整链的限制不变。
- 四文件本地提交消息 `feat(planning): add v2 resource gap extraction`，精确Final HEAD见最终答复与ignored final.json。主协调请求Sol6.1high，领域实现/独立审查复用Sol6.1medium，actual NOT OBSERVABLE，无全局配置或HARD升级；无多余服务/表/Provider/流程抽象，未push/merge/deploy。ITEM5_NOT_STARTED；STOP。

## 2026-10-08 Planning V2 Item 3：CONTENT_COVERAGE_COMPLETE / ITEM4_NOT_STARTED / STOP

- 基线 `91c17a63747ddd205880df488484a4fdf804d5f9`、`feat/n1-resource-discovery` 匹配，tracked clean；Policy v2 12 capabilities/27 outcomes 与前置报告一致，只做 Tool Calling 定向分区示例，没有重审全量粒度。原预检失败报告/架构/Item1与2/历史内容保持原文；[本轮实施报告](../planning-v2/ITEM3_CONTENT_COVERAGE_IMPLEMENTATION.md)记录合同、真实映射、验证及限制。
- 新增冻结 CoverageResult/Entry/ContentRef、只读 Index/Evidence/Mapping、确定性 Evaluator 和 ResultValidator，仅B学习集合参与；完整covered/missing分区产生full/partial/none，同section多outcome合并引用，无教学资产创建或Plan修改。无映射正常missing；配置身份/版本/正文审核/来源损坏明确ValidationAppError。独立审查先发现v2标签可隐藏旧/拼错ID，补RED3FAIL后局部加Policy全outcomes+本Plan受信未知定义范围校验，未改Policy或引入别名。
- 实际最小索引固定agent.application/v8、MCP10.2 source2与section稳定身份，核对既有chapter_review及197–205行审核文档；只映射mcp.roles/interfaces。窄foundation概念full，applied或systematic缺minimal_connection为partial，ToolCalling暂无充分精确映射为none。语义判断与机械身份检查分开；record/document hash不是10.2教程正文hash，v7 TOC不继承v8资格，没有重新审核Seed/新教程或让Seed决定课程。
- 行为RED Domain31FAIL/Index12FAIL保留；最初缺模块collection及sandbox temp错误如实记录，改仓库内独立basetemp后重做有效RED。最终统一56PASS（Domain35+真实本地索引12+接口3+现有审核3+failclosed3），同范围collection56PASS，Ruff四文件/diff PASS，独立有限审查PASS，无剩余合同BLOCKER。Fake上游/合成证据只证明算法，两个真实概念映射另有既有审核和独立语义依据，不代替Item1/2真实模型验收。
- 812受保护tracked文件、378账本文件、.env、原预检报告与旧progress全文保持；产品模型0/搜索0/Reader0，账本183/280、unknown177/183未重派。未运行DB/Run/Job/Draft/Plan写入，migration0，未接旧Graph/Worker/Runtime/组合根，公开generate仍failclosed。真实PG行计数/浏览器/产品模型语义/在线资料或教程执行/全量Backend/整链E2E均NOT RUN，不虚报数据库行数。
- 六文件本地提交消息 `feat(planning): add v2 reviewed content coverage`，精确Final HEAD见最终答复与ignored final.json。主协调请求Sol6.1high、领域实现/证据清点/独立审查Sol6.1medium，实际解析NOT OBSERVABLE，无全局配置或HARD升级。Item1仍CONDITIONALLY_ACCEPTED，Item2真实语义待整链；Coverage输出无Item4合同级前置阻塞，但本轮未实现Item4/Gap/Research/Reader/UI。未push/merge/deploy；STOP。

## 2026-10-08 Planning V2 Item 2 Policy Outcomes：REFINEMENT_COMPLETE / ITEM3_READY_FOR_PRECHECK_REVIEW / ITEM3_IMPLEMENTATION_NOT_STARTED / STOP

- 基线 `53c8b0851098d8905722d5867cfae27643672267`、`feat/n1-resource-discovery` 匹配；核对并保留两份预期未提交文档，没有reset。原Item3预检失败报告原样纳入本地提交，旧progress全文保留；[本轮修订报告](../planning-v2/ITEM2_POLICY_OUTCOME_REFINEMENT.md)记录最终映射与理由。
- Policy v2保留12 capability身份/标题/真前置/defaultdepth，9项复合定义按独立教学任务拆为新ID，总27 outcomes；code.review/error.permission/eval.lite保持单项ID和原文，不强制全部能力partial。六候选只做一次有界审查，各场景教学不靠通用错误类别代替。无旧ID缩义复用、旧审核映射继承或双版本Runtime平台。
- MCP roles/interfaces/minimal_connection分开；Policy唯一规则消费现有route/depth，systematic任意depth含最小接入；narrow/other foundation仅概念，applied/deep含实践。接入验证一次工具调用可独立练习，project_usage仍可excluded，不强迫主项目MCP。Validator仅回填接缝、Prompt仅一条指向Policy的适用说明；A/B/Schema/调用流程/hash算法保持。
- 先RED31项25FAIL6PASS，GREEN33PASS；最终受影响回归113PASS（新33+既有Domain/Service57+Provider23），同三文件collection113PASS，Ruff四文件完整规则/diff/链接PASS。独立审查PASS，接口“等”开放范围已收紧Tool/Resource；AST核对Domain还原单接缝后等价。集合测试读真实冻结B outcomes，仅证粒度支持完整部分分区，不实现Coverage或Reviewed Mapping。
- 805受保护tracked文件、378账本文件、.env、原预检报告hash及旧progress正文保持。产品模型0/搜索0/Reader0，账本仍183/280、unknown177/183未重派；无DB/Run/Job/Draft/Plan操作、migration/Seed/UI/Worker改动。真实PG/浏览器/产品语义/在线资料/全量Backend/Item3实现NOT RUN；公共generate代码保持fail-closed，本轮未重复运行入口测试。
- 八文件本地提交消息 `fix(planning): refine v2 capability learning outcomes`，精确Final HEAD见最终答复与ignored final.json。主协调请求Sol6.1high、实现/独立审查沿用Sol6.1medium，actual均NOT OBSERVABLE，无全局配置修改或HARD升级。Item1仍CONDITIONALLY_ACCEPTED，Item2真实语义待整链；仅ITEM3_READY_FOR_PRECHECK_REVIEW，未自动进入Item3/4，未push/merge/deploy；STOP。

## 2026-10-08 Planning V2 Item 3 预检：BLOCKED_BY_OUTCOME_GRANULARITY / ITEM2_MINIMAL_POLICY_REVISION_REQUIRED / STOP

- 基线 `53c8b0851098d8905722d5867cfae27643672267`、`feat/n1-resource-discovery` 与预期一致，开始tracked clean。12个Policy能力各一个outcome，按covered/missing完整分区的单能力partial不可达；单ID本身不违规，但Tool Calling参数校验/派发、Agent循环/终止/失败返回、MCP角色职责/工具协议边界包含必须分别审核的范围，触发用户编码前STOP门禁。
- 只新增[Item 3预检报告及最小Policy修订建议](../planning-v2/ITEM3_CONTENT_COVERAGE.md)并追加本进度。code.review证据关联、error.permission完整区分、eval.lite案例验证无需按名词机械拆；另外6个复合候选保留供独立修订任务收敛，不承诺仅拆重点3项就全面解阻。没有自动改Policy、CapabilityPlan、Profile或实现Coverage/Item4。
- 只读核对MCP v8 source/section身份、version、10.1正文审读与10.2继承审核的范围及限制；没有把published/reviewed标签、章节目录或hash等同outcome覆盖。正式内容索引资格验收/映射、Item3 RED/GREEN与回归/collection/Ruff、真实PG及本轮generate执行测试均NOT RUN；生产文件未改，不重复基线测试。
- AST/分区事实提取PASS、接口粒度门禁FAIL，独立开发审查确认阻断和建议范围；文档链接/diff/保护hash审计PASS。产品模型0、搜索0、Reader0，无DB/Run/Job/Draft/Plan操作、migration0、UI/Worker/公共generate改动0；历史账本及unknown177/183保持，Item1仍CONDITIONALLY_ACCEPTED、Item2真实语义验收未完成。
- Start/Final HEAD保持一致，仅两份文档工作树修改，未执行仅在预检与实施通过后授权的功能commit，未push/merge/deploy。主协调请求Sol6.1high，独立复核沿用Sol6.1medium，actual均NOT OBSERVABLE。最终 ITEM3_BLOCKED_BY_OUTCOME_GRANULARITY / ITEM2_MINIMAL_POLICY_REVISION_REQUIRED / ITEM4_NOT_STARTED；STOP，等待独立Policy修订授权，不自动跨边界实施。

## 2026-10-08 Planning V2 Item 2：CAPABILITY_PLANNING_COMPLETE / ITEM1_CONDITIONALLY_ACCEPTED / ITEM3_NOT_STARTED / STOP

- 基线 `18ff5cca095e5a2037ab1742d0bfcfb275adc2c2`、`feat/n1-resource-discovery` 与预期一致、tracked clean。完成 Profile-only CapabilityPlanner、冻结 CapabilityPlan/Pending、小型只读 Policy v1（12 个可组合能力）、专用 Provider purpose/schema/prompt；不读取 raw GoalSpec，不接旧 selector/Seed/Graph。修改九文件，完整清单、最终字段与剩余边界见[Item 2 实施报告](../planning-v2/ITEM2_CAPABILITY_PLANNING.md)。
- accepted_known(A) 可满足真前置，B-only 学习能力/outcomes 投影不重加 A；具体进阶学习目标独立保护。systematic_agent_route 要求 MCP 学习，project_usage 独立可 optional/excluded；排除学习冲突返回可回答澄清。未知领域无证据为 needs_verification，最多一份带来源/limitations/fixture 标记且 hash 绑定的离线证据补定义。没有 Item3～6 消费者或真实外部验证接线，不把结构验证当模型语义证明。
- RED 原始失败保留：Domain 缺模块 collection error、Provider 6FAIL、独立审查机械输入负例25FAIL；修正共享输入边界与 JSON tuple/list 表示后，统一定向回归269PASS（新Item2 80、既有189），Backend Collection2146PASS（仅收集）。新代码/测试Ruff全规则PASS、adapter沿用基线E701/I001排除PASS、diff PASS；独立审查PASS，无合同冲突/未解决代码BLOCKER。真实模型语义/在线领域验证/PG/浏览器/整链E2E NOT RUN。
- 产品模型0、搜索0、Reader0；账本仍183/280、unknown177/183保持未重派。800受保护tracked文件、378账本文件、.env及旧progress全文hash/内容保持，迁移0、前端0改动。公开generate仍scope后503，无新Run/Job/Draft/Plan操作；零依赖访问是离线门禁证据，真实PG行计数NOT RUN。未接Worker/组合根/旧Fake，未开放生成。
- Item1按本轮用户明确授权有条件接受；Case7真实模型验收未完成、历史unknown与完整Item1端到端未验收保持，不改写旧报告。主协调请求Sol6.1high、实现/独立审查请求Sol6.1medium，actual均NOT OBSERVABLE，无全局模型配置变更/HARD升级。
- 本地提交消息 `feat(planning): add v2 capability planning`，精确Final SHA见答复与ignored final证据。未push/merge/deploy，未进入Item3。最终 PLANNING_V2_ITEM2_CAPABILITY_PLANNING_COMPLETE / ITEM1_CONDITIONALLY_ACCEPTED / ITEM3_NOT_STARTED；完整产品未READY，STOP。

## 2026-10-08 Planning V2 Item 1 Project Context Reference Fix：FIX_READY / REAL_ACCEPTANCE_PENDING / ITEM2_NOT_STARTED / STOP

- 基线 `d16c136432280c9c214a067ced812d8219ac2fb1`、`feat/n1-resource-discovery` 与预期一致、tracked clean；只改专用 Prompt 的项目来源说明，将歧义 `project_context（指goal.project_context）` 改为合法引用 `project_context`、禁止 `goal.project_context`，补一个完整 requirement 示例。Schema/Validator/SHAPE/IDhash/其他 Prompt 行为保持，无架构合同变更。
- 新最小测试先 RED 1FAIL4PASS，修正后 5PASS；合并局部回归 33PASS（新5、硬约束12、GoalSpec9、Provider Prompt1、公开生成/范围/组合根6），Ruff/diff PASS。无全量或大规模无关回归；独立审查结论见[实施报告](../planning-v2/ITEM1_PROJECT_CONTEXT_REFERENCE_FIX.md)。
- 历史真实 Case7 原输出仍被 Validator 拒绝；仅离线副本三处引用替换后验证 PASS、ID/hash稳定，标记 OFFLINE_MODIFIED_HISTORICAL_OUTPUT_NOT_REAL_PASS。原失败证据不覆盖、不重发。此前真实 Cases2/4/5/6 PASS、Case7 FAIL 保持，本轮真实模型验收 NOT RUN/PENDING。
- 产品模型0（授权0）、搜索/Reader0、DB写入0、migration0；账本182/280全部375文件hash保持，unknown177保留未重派。797受保护tracked文件、配置、架构及历史Case7证据保持；public generate仍scope后503，Run/Job/PlanMutation0为依赖访问门禁证据，真实PG行计数 NOT RUN。未启动旧Planning、Worker、数据库或Item2，未改占位页。
- 仅 Prompt、新测试、本实施报告和本进度四文件；本地提交消息 `fix(planning): clarify project context source reference`，精确SHA见最终答复/ignored final证据，不push/merge/deploy。提出单独最多1次DeepSeek deepseek-flash、仅Case7、无retry/repair的新授权申请，未执行、不消费已耗尽的五次授权。
- 主协调请求Sol6.1high，实现/独立审查请求Sol6.1medium，actual均NOT OBSERVABLE，无HARD升级。最终 ITEM1_PROJECT_CONTEXT_FIX_READY / ITEM1_REAL_ACCEPTANCE_PENDING / ITEM2_NOT_STARTED；完整Planning V2未完成，STOP。

## 2026-10-08 Planning V2 Item 1 Hard Constraint Fix：READY_FOR_REAL_RETEST / SEMANTIC_ACCEPTANCE_PENDING / ITEM2_NOT_STARTED / STOP

- 基线 `e025f2f05b5b8216905f312a5ff80a6888b5e2d1`、`feat/n1-resource-discovery` 与预期一致、tracked clean；本地提交消息 `fix(planning): preserve explicit goal constraints`，final SHA见答复及 ignored final evidence。不push/merge/deploy。
- 仅专用SYSTEM Prompt明确所有获准输入的显式禁止/实现/范围/费用限制，即使constraints为空也进入hard_constraints；需求与约束可共存，structured同义合并仍逐条原文/index，Python声明/interview用途不误分类，无限制不虚构、冲突保留澄清。Schema/SHAPE/Validator/IDhash/Analyzer/transport/preflight/预算无改动；非Prompt AST与基线相同。
- 新12项先RED 1FAIL11PASS，修正后12PASS；统一回归198PASS（Item1 104+既有94，含JSON/unknown/GoalSpec/fail-closed），backend collection2061PASS、Ruff/diff PASS；独立有限审查PASS，无离线BLOCKER。正确fixtures仅证明机械表示/校验，漏自然语言约束仍Validator PASS反例保留，真实语义NOT RUN/PENDING，旧真实Case2 FAIL不被覆盖。
- 产品模型0（本轮授权0）、搜索/Reader0、DB写入0、migration0；新Run/Job/PlanMutation0为未接DB及依赖访问门禁证据，真实PG行计数NOT RUN。public generate继续scope后503、无旧Fake注册、Planning占位页保持。历史真实响应/失败报告/账本/unknown177/config/架构均保全，未重派unknown，账本177/280与unknown1保持。
- 仅Prompt、新Item1测试、本[实施报告](../planning-v2/ITEM1_HARD_CONSTRAINT_FIX.md)及本进度四文件；报告含根因、分层证据及独立审查。提出单独最多5次新身份复测（Case2/4/5/6+独立project_context，每案1次，无retry/repair）申请，尚未授权或执行，不消费上轮剩余次数。
- 主协调请求Sol6.1high，实施/独立审查请求Sol6.1medium，actual均NOT OBSERVABLE，无HARD升级。完整Planning V2仍未完成，全产品STAGING_BLOCKED/NOT_READY；本轮STOP，Item2未启动。

## 2026-10-07 Planning V2 Item 1：PLANNING_V2_ITEM1_GOAL_REQUIREMENT_ANALYSIS_COMPLETE / ITEM2_NOT_STARTED / STOP

- 基线 `31513e960723414645e4d3332c29718b603c96bd`、`feat/n1-resource-discovery`，与指定HEAD相同、tracked clean。上位[Architecture Contract](../planning-v2/PLANNING_V2_ARCHITECTURE_CONTRACT.md)原文保持；本地提交消息 `feat(planning): add v2 goal requirement analysis`，final SHA见答复与 `var/planning-v2-item1-20261007/final.json`；不push/merge/deploy。
- 新增单次Analyzer、冻结Profile与严格Validator、专用purpose/schema/prompt；结构化用户事实确定性保留，ID/hash由服务端canonical payload生成，无课程/能力/资源决策。GoalSpec最小可空project_context，空省略保旧六字段hash；OpenAPI/生成TS同步，Planning placeholder及所有UI组件保持。没有生产Analyzer接线，普通generate继续scope后503。
- 新增92项PASS；既有必需回归181项PASS（包含GoalSpec/intent5PASS、JSON/truncation/unknown、auth/scope/current-read、DTO），复用最新XML去重有效273PASS，不累加重复。初轮2个基线stale intent FAIL与中间1FAIL保留；仅迁现代冻结/Fake setup、一处旧字段断言对齐实际learner投影并补完整manifest/practice事实校验，hash/最终用途保护保持。额外旧partial markerless20FAIL已有baseline/hash/调用前拒绝证据，未改该suite/未放宽保护，不声称全backend regression PASS。
- backend collection2049PASS、类型生成/tsc/Ruff/diff PASS；独立Item1审查及同次intent测试差异复核PASS。真实语义代表/PG/checkpoint/产品端到端NOT RUN；poisoned MCP结构合法仍SEMANTIC_EVAL_REQUIRED，不用黑名单冒充语义证明。详细[A–F审计、代码边界、测试与限制](../planning-v2/ITEM1_GOAL_REQUIREMENT_ANALYSIS.md)，证据 `var/planning-v2-item1-20261007/`。
- 新Run0/Job0/provider0/PlanMutation0为依赖访问前spy/HTTP门禁证据，非真实PG行计数；产品模型0、搜索0、DB写入0、migration0，0025/架构合同/placeholder/.env等28文件hash保持。未接Worker/ledger/Reader/WeKnora，不改Seed/正式入口/全局配置/两保护目录，不消费余额或恢复历史failed/unknown。
- 主协调请求Sol6.1high，机械Lunamedium，有界Provider/测试/独立review Sol6.1medium，actual均NOT OBSERVABLE，无HARD升级。Item1实现无BLOCKER，无架构偏差；完整Planning V2尚未实现，全产品STAGING_BLOCKED/NOT_READY。STOP等待单项审查，不自动进入Item2或真实模型验收。

## 2026-10-07 Planning V2 Residual Cleanup：PLANNING_V2_RESIDUAL_CLEANUP_COMPLETE / PLANNING_V2_NOT_IMPLEMENTED / STOP

- 用户现在新增能做什么：学习计划主区只有指定不可用占位；旧生成/Run恢复/路线变更UI与19个旧浏览器helper移除。既有非规划能力保留，未实现V2。
- 起点6f62b9e1687ce79b8b3ca4190c0b9b4974323272，feat/n1-resource-discovery，annotated checkpoint/pre-planning-v2-residual-cleanup；最终本地提交SHA见本批答复与var/planning-residual-cleanup-20261007/final.json，不reset/push/merge。
- 旧长图生产builder/interpreter/interrupt wrapper删除；Fake demo移至测试夹具，组合根不再注册fallback。独有plan-changes/generate及request DTO/OpenAPI/TS删除；普通generate保留scope后503。混合outline/structure/batches/provider/source/JSON/预算/恢复/发布与public历史DTO逐函数HOLD，不为清理丢保护或拆大文件。[完整删除/迁移/HOLD/验收报告](../acceptance/planning-v2-residual-cleanup-2026-10-07.md)。
- compile/import/APIboot/failclosed/非规划smoke/collection PASS；当前保护432、历史图57与adapter/content9（唯一498）PASS，生产markerless仍拒绝；初轮历史夹具31FAIL原输出保留，改测试callback隔离而非放宽生产校验。前端27PASS/build/genAPI PASS，实际Edge本地HTTP fixture八种缓存状态+reload/截图PASS、规划请求0；真实PG/provider NOT RUN。
- 459受保护文件SHA保持，删除目标runtime/frontend/helper dangling refs0（HOLD和历史记录仍保留，不假称全旧字符串清零）。migration0025/新增0；generate Run0/Job0/provider0/PlanMutation0为依赖访问前证据、非PG计数。产品模型0，账本174/280余106，搜索/RAG0；原库/正式入口Worker/全局配置/两保护目录/旧历史未操作。
- 整体STAGING_BLOCKED / NOT_READY；STOP，仅等待下一Planning V2正式Goal，不自动使用余额或开始实现。

## 2026-10-07 Planning Legacy Removal：PLANNING_LEGACY_REMOVAL_COMPLETE / NEW_PLANNING_NOT_IMPLEMENTED / STOP

- 用户现在可继续消费非规划基础服务；新计划生成/生成式路线变更在scope校验后503，在Run/Job/model binding/provider前关闭，无替代规划实现。
- 起点8921a680fabe8f75ee5f95c231b1eca8c9273216，feat/n1-resource-discovery；保留参考bd691226后继。本地annotated checkpoint/pre-open-planning-refactor，最终SHA见本批答复与var/planning-legacy-removal-20261007/final.json。未reset/push/merge。
- 删除alignment/semantic_content/PG goal selector、旧domain pack目标路由、markerless/三字段/旧batch approval兼容与旧waiting Run改写、旧Plan无snapshot的动态目录fallback。公开生成及route preparation明确fail-closed。保留frozen/canonical/source/预算/repair2/unknown/Worker/RLS/CAS/发布事务与已审核内容、助手全部合同；[具体文件/删除测试/保留保护/验证](../acceptance/planning-legacy-removal-2026-10-07.md)。
- Pythoncompile/APIboot与10个fail-closed边界PASS；核心/助手/contract245PASS、当前结构65PASS、JSONrepair/预算68PASS、F2/MCP85+35PASS；全部backend collection与frontend buildPASS。真实PG/浏览器/provider、废弃semantic acceptance NOT RUN。依赖旧生成准备的9条generated-change与旧图fixture保护测试保留NOT RUN，不假称全套PASS。
- generate新增Run0/Job0/provider0/Plan修改0（依赖访问前拒绝证据，非PG计数）；本批产品模型0，账本174/280余106，search/RAG0。434文件SHA保持，迁移0025，内容JSON/语义资料/助手/.workbuddy/design-preview/旧证据未变，无DBreset/原库写入/正式入口Worker/部署/全局配置操作。
- 旧指定runtime/test符号引用0。整体STAGING_BLOCKED / NOT_READY，STOP等待下一份Planning设计，不自动实现。

## 2026-10-05 Learning Assistant User Acceptance Prep：PRE_USER_ACCEPTANCE_READY / STOP

- 用户现在新增能做什么：我的会话 detail 尚未读取/GET 失败时不再显示第四状态，也不猜未保存；卡片标题/类型/时间保持，成功读取才显示已保存/待确认/未保存。隔离本人入口 http://127.0.0.1:5205/ 已准备，等待本人体验。
- 开始 HEAD bd6912268cfe33f545b62105c2c7d1f829368d4e、feat/n1-resource-discovery；本地小后继 SHA 见 var/assistant-user-acceptance-prep-20261005/final-audit.json 及答复。仅4个前端源码/测试文件；后端/迁移/API/DTO/OpenAPI diff0，0025保持；原detail hydration及UI/教学合同保持。[本批报告](../acceptance/assistant-user-acceptance-prep-2026-10-05.md)。
- 前端定向51PASS、原套件27PASS、TypeScript/build PASS；真实安装Edge+ownedAPI首屏无第四状态、单条GET失败保卡且不猜状态、恢复三态、搜索/筛选/selected/助手/历史只读 PASS；截图路径在报告。扩展连接仍通信失败，采用现有Playwright-core驱动本机Edge，未冒称扩展恢复。backend full suite NOT RUN（后端无改动）。
- 新owned business_a5c03344/checkpoint_36c74c9c复制已有合成库；6既有历史会话两种模式/三态齐全、仍只读，当前revision3可由本人开始新总结/实践。API8050/UI5205/owned normal Worker运行，启动队列可派发0；本人Send才允许新assistant.coach，记录既有全局append-only账本，cap280，unknown STOP，无自动retry/repair/历史重派。准备未新建聊天内容或收费Acceptance。
- 免费binding/DNS/TLS/dispatch guards PASS；本批新增产品请求0，实际174/280余106；650历史/config/reference文件哈希及12类源owned核心表精确保持；两保护目录未操作。原产品库/正式入口/正式Worker/RAG/WeKnora/部署/push/merge未操作。本轮真实模型 NOT RUN，本人接受 NOT RUN。
- PRE_USER_ACCEPTANCE_READY仅表示入口与小修准备通过；既有LEARNING_ASSISTANT_CORE_PASS保持，整体STAGING_BLOCKED / NOT_READY。已STOP，下一仅本人体验与明确反馈，不自动使用余额或进入新开发。

## 2026-10-05 Learning Assistant Final Closure：LEARNING_ASSISTANT_CORE_PASS / STOP

- 用户现在新增能做什么：批准HTML已落正式React，我的会话轻量搜索/分类/三态/最近消息/时间/选中；Chat助手无intent/逐消息consent/内部ID，候选折叠展开、采用/改稿后原服务保存。历史路线只读和既有窄屏保持。新Practice final冻结practice_teach_with_proposal，精确remaining且必须完整非空候选，server ready_to_draft；旧171成功/教学FAIL不改。
- 基线31e739f5d395c312042bf9799ddfa37523e8f94d、feat/n1-resource-discovery后继保留；最终actual HEAD见var/assistant-core-closure-20261005/git-final.json及本批答复。migration0025保持、无API/DTO/schema变化。批准[Goal](STUDYPLAN_ASSISTANT_CORE_CLOSURE_2026-10-05.md)，[分层验收/来源文件/七类截图](../acceptance/assistant-core-closure-2026-10-05.md)。reference绝对路径与SHA在报告；555旧文件/config/ledger/reference bytes保持，两保护目录未操作。
- 非收费unit/contract1356PASS2NOT RUN（Windows未提权目录symlink创建不可用）；包含定向177PASS；owned PG/API/standardWorker74PASS；Fake Summary4/Practice3+采用/自定保存/恢复PASS；frontend52+原27PASS/buildPASS。Edge实际ownedAPI+Fake消费、133/2000/19960字末行/操作/composer、展开收起锚定与首行重置、inline known/unknown、选中/搜索/三态、refresh/logout/relogin、close/reopen、旧Plan只读、390px与截图人工结构对照PASS。不是以总数代替教学/视觉证据。
- 非收费全门禁及免费binding/DNS/TLS/security guard PASS后，唯一Acceptance assistant-core-closure-synthetic-f95d70a84a6c、新owned business_f1af4a11/checkpoint_ab386e2c/合成Plan与Practice会话；无新本人规划Run。真实172(1237in/209out)、173(1998/290)、174(2511/1171)均stop/provider/application/teaching PASS：集中4问→i2 resolved仅问i1/i3/i4→只teach remaining且772字最终Prompt，server ready_to_draft。原正式保存version1/PG/API/main页面/我的会话已保存PASS，保存/消费增量0。
- 全局append-only171→174/280余106，本轮3、unknown0、duplicate0、repair0；5746input+1670output，金额NOT OBSERVABLE。本批真实Summary NOT RUN，165–168原PASS保持；历史163–171/旧failed/unknown未重派改写。taskpending、无verified或阶段完成污染；原库写入0，正式入口/正式Worker/RAG/启动数据/部署/push/merge NOT RUN。
- 临时owned8046/8047/5203/5204无监听/对应进程，库/证据保留。浏览器连接在已保存实际消费截图后断开，临时viewport reset NOT RUN，不冒称已清理；本人后续验收再连接。root请求Sol6.1xhigh、有界前端/PG medium，actual NOT OBSERVABLE。
- 核心LEARNING_ASSISTANT_CORE_PASS，整体STAGING_BLOCKED / NOT_READY。已STOP，下一仅本人对正式React/学习助手的体验接受及另行正式操作授权；不因余106自动收费或进入下一开发阶段。

## 2026-10-05 Learning Assistant Final Closure：启动记录（历史时点，已由下方最终记录续接）

- 用户现在新增能做什么：本批批准HTML正式落React、Practice两轮后强制最终候选合同；正在非收费验收，尚未声明核心PASS。
- 启动实际HEAD31e739f5d395c312042bf9799ddfa37523e8f94d、feat/n1-resource-discovery、tracked clean；0025保持。唯一批准[Goal](STUDYPLAN_ASSISTANT_CORE_CLOSURE_2026-10-05.md)，reference/hash/555历史保护在var/assistant-core-closure-20261005/baseline.json。两保护目录不操作。
- 账本实际171/280余109；非收费门禁全部PASS后才唯一新Acceptance至多3次Practice，repair0，无Summary收费。旧171provider/application成功与教学FAIL保持，不重派或回改。原库/正式入口/Worker/RAG/部署/push/merge禁止，整体STAGING_BLOCKED / NOT_READY。
- root关键合同/预算请求Sol6.1xhigh，独立frontend/PG有界Sol6.1medium，actual NOT OBSERVABLE；同问题反例一次整合，无重复长历史调查。当前新ownedFake全链PASS，最终分层与Edge仍进行中。

## 2026-10-05 Assistant Teaching State Closure：非收费 PASS / 真实完整链 FAIL / STOP

- 用户现在新增能做什么：未来新自然会话冻结issue-ledger-v1，服务器ID与确定轮次，成功turn/receipt独立重建；第二轮只展示remaining、两轮后只teach unresolved，Summary本地重新表达0请求，候选明确采用/修改后原正式保存。UI/DTO/API/0025无变动，旧自然/显式legacy不回填。真实Summary4轮+正式保存PASS，真实Practice未产生最终Prompt，不能标LEARNING_ASSISTANT_CORE_PASS。
- 保留HEAD09c8242b1df64f9dc641f67981d2ff967162b210及feat/n1-resource-discovery后继；最终实际SHA见答复/git-final.json。新Goal[原文](STUDYPLAN_ASSISTANT_TEACHING_STATE_CLOSURE_2026-10-05.md)，[分层报告](../acceptance/assistant-teaching-state-closure-2026-10-05.md)。最小状态复用immutable payload/成功attempt，事件独立marker防降级、context/trigger/result_ref/receipt绑定、分页/恢复、resolved不回退、本轮新resolved交叉复问拒绝；破链fail-closed。
- 163/164原body与派生fixture边界PASS，新unit51/相邻unit-contract183 PASS；owned PG新11/相邻47 PASS；API+Worker MockTransport Summary4/Practice3+采用/改稿/幂等PASS。Frontend61/build输入SHA无变化复用PASS。native new restore精确14消息/7turn/8正式关联/4Summary4Prompt、0025、服务重建ledger/public view PASS。PG3条Windows UTF8 reader warning及初轮fixture/harness FAIL原输出保留，未改保护追绿。
- Edge actual owned Plan/API PASS：两mode服务器自然渲染、无ID、remaining/teach/本地重新表达/Practice候选、明确采用/自定保存、主区正式版/我的会话/refresh/logout/relogin；恢复/保存新增请求0，provider仅Mock。beforeunload NOT RUN按用户留本人验收。全部非收费+free binding/DNS/TLS PASS才执行新收费。
- 唯一Acceptance assistant-teaching-closure-synthetic-94c37d3ce90a，新owned两库/合成Plan/账号/两会话，无planner Run。真实165–168 Summary四轮与原服务显式保存1 PASS。169–171 Practice首轮4问、二轮i1 resolved消失/remaining3、三轮只teach i2/i3/i4 PASS，但第171笔proposal=null/statuscontinue，最终Prompt链FAIL即STOP；应用合同目前允许此null分支，无第8次/重试/repair/第二Acceptance。真实Practice保存/paid Edge NOT RUN，7 provider/JSON/Run均succeeded事实保持。
- 全局append-only165–171/PG/receipt usage reconciliation PASS；累计164→171/280余109，本轮7、repair0、unknown0；13648input+1960output=15608tokens，金额NOT OBSERVABLE。407旧文件/.env SHA保持，163/164原教学结论不改。paid14消息7turn1Summary0Prompt、taskpending无完成污染。搜索/RAG0，原库/正式入口/正式Worker/部署/push/merge/全局配置 NOT RUN。临时owned8045/Worker与5202已关闭，库/备份保留。
- 请求root关键Sol6.1xhigh、有界测试Sol6.1medium、机械fixtureLunamedium，actual NOT OBSERVABLE。CORE FAIL，整体STAGING_BLOCKED / NOT_READY，已STOP。下一仅新有界Practice teach强制候选合同评审/离线反例与PG，未实施；不能用余额自动补发或重派历史。

## 2026-10-05 Learning Assistant V1.1：非收费 PASS / 真实教学 FAIL / STOP

- 用户现在新增能做什么：简洁自然聊天、本地固定欢迎0调用、默认恢复精确位置最近会话、菜单新建；候选Summary/Prompt明确采用或修改后交给原正式保存服务，主区刷新正式结果。会话与正式产物分离，完成/canonical/source/task门禁保持。教学prompt已实现，但实际第二轮遵守失败，不能宣称真实教学闭环通过。
- 保留基线HEAD91750cbb345c7f428dd17809affcf4b50da2865b、feat/n1-resource-discovery；最终实际SHA见本批答复/git-final.json，不reset/回退。源码与所有新owned库migration0025，没有新迁移。新Goal[原文](STUDYPLAN_LEARNING_ASSISTANT_V11_GOAL_2026-10-05.md)，[最终分层证据](../acceptance/learning-assistant-v11-2026-10-05.md)。
- 仅助手projection reply/status/proposal；任意extra无ID/role/保存权威，原162failed不改不重派。proposal由server message/turn/result_ref/精确成功receipt/schema/protocol重建，6破链拒绝；既有FK与原Summary/Prompt CAS/幂等保持，不回改0025。无assistant repair/retry。
- Unit/contract183PASS；PG/API53唯一有效PASS（46组合+1fixture定向修正+6相邻；原FAIL保留）；frontend61唯一有效PASS（57+1限长+3焦点）/build PASS。真实owned普通API/Worker+MockTransport总结4轮/实践3轮、采用+改稿、幂等/恢复PASS；native fresh restore精确行hash/app角色14消息/7turn/4正式关联PASS。Fake不代表真实provider教学通过。
- Edge实际Plan/API PASS：简洁布局/两mode教学与保存、CAS409、close/reopen缓冲、refresh/logout/relogin/我的会话、430px桌面/760px全屏焦点循环、旧Plan只读、known失败原文/synthetic unknown不重发。首开Escape焦点FAIL最小修复后实际PASS，原FAIL保留；原生beforeunload弹窗自动化NOT RUN，未冒称浏览器通过。免费binding/publicDNS/securityguard/TLS PASS后收费。
- 唯一Acceptance assistant-v11-synthetic-c133125757c9，新owned business_da7d56f6/checkpoint_464a0019/合成账号/Plan/两会话。真实163初稿1016input401output/stop，4项集中诊断PASS；164部分回答1507input617output/stop，重复已答对输入/执行问题、第二轮提前教学，教学FAIL即STOP。provider/严格JSON/两应用Run均PASS，不能倒改成Run failed；后5回复/真实候选保存/Practice NOT RUN。正确completed_rounds1与明确不重复指令已入原wire，证据保留。
- 本授权280只一次；request/result累计162→164/280余116，本批2、repair0、unknown0；2523input+1018output=3541tokens，金额NOT OBSERVABLE。全局账/PG/rawreceipt reconciliation PASS，391旧文件/.env hash保持，唯一completion追加。新paid4消息2turn0正式产物，学习状态未污染。产品search/RAG0；原库/正式入口/正式Worker/deploy/push/merge NOT RUN。
- 请求root/关键复核Sol6.1 xhigh、前端有界medium，actual NOT OBSERVABLE。LEARNING_ASSISTANT_CORE_PASS条件FAIL，整体STAGING_BLOCKED / NOT_READY。当前STOP；下一仅新的有界离线教学合同定位/验收Goal，余额不自动授权重跑。

## 2026-10-05 Learning Assistant V1：非收费 PASS / 真实代表 FAIL / STOP

- 用户现在新增能做什么：开始总结/精确task开始实践创建冻结会话并打开右侧助手；工作稿/追问分离、多轮反馈、用户明确保存原Summary/Prompt服务、主区正式版本刷新与我的会话恢复。聊天不写完成事实；主区任务/正式历史/导出/成果/USER保留。源码与[本批报告](../acceptance/learning-assistant-v1-2026-10-05.md)同一本地提交，最终实际SHA见最终答复与var git-final审计；基线af2f3ae3fad226509ef6d149455a507acce49663，无reset/回退/push/merge。新迁移head0025，0024保持。
- 最终unit/contract156PASS、owned PG/API/普通Worker34PASS、前端51PASS/build PASS；非收费Edge两mode三轮+明确正式保存+主区消费、scope/409、close/refresh/logout/relogin、读取断连、旧Plan只读、无模型原文保存、760x860/Escape PASS。原生owned恢复精确行哈希与普通app-role消息/稿件/正式关联回读PASS，旧RC owned副本0024→0025旧行保持PASS。原154/33与初轮FAIL保留不重复计数。
- 新Acceptance assistant-v1-synthetic-bdeb680f4573，仅新owned两库/合成账号/Plan/两会话；免费binding/publicDNS/endpoint guard/TLS PASS后真实2次。第161笔summary初稿587input665output/stop内容PASS；第162笔追问1297input887output/stop，多出message_id，严格assistant_reply_invalid，应用Run failed、原文保留、无成功回复/正式产物。provider两笔receipt均succeeded，不能把provider成功当业务PASS。unknown0、repair0；后4次NOT RUN，未重发/新Acceptance/第二批收费。原response/receipt/失败Run保留并入fixture；提示明确禁止输出标识，同因离线回归PASS，真实效果NOT RUN。
- 本授权只登记一次 previous_cap200/additional80/new_cap280/used_before160/remaining120；本轮2，累计162/280余118；1884input+1552output=3436tokens，金额NOT OBSERVABLE。old160账/.env hash、PG/provider/rawbody reconciliation PASS；search/RAG0，无本人规划/旧failed unknown恢复/旧Draft确认/原库/正式入口Worker/deploy/全局config操作。
- 所有本批临时8041/8042/5198/5199已确证归属并停止，owned库/备份保留；无Worker保留回执入口5199的准确启动/合成登录/停止方式见报告。IMPLEMENTED/非收费PASS，PAID FAIL，USER ACCEPTED/DEPLOYED/F17 NOT RUN；不能标LEARNING_ASSISTANT_CORE_PASS，整体STAGING_BLOCKED / NOT_READY。下一只离线审阅与新有界验收评审，本批STOP不消费余额。

### 本批启动授权记录（历史时点）

用户授权按已冻结 Goal 连续实现总结/实践多轮助手与明确正式保存。基线 `af2f3ae3fad226509ef6d149455a507acce49663`，保留后继。原账本核对160请求/160结果；本授权只登记一次：previous_cap=200、additional_authorization=80、new_cumulative_cap=280、used_before_authorization=160、remaining_after_authorization=120。非收费门禁通过后至多6次新助手回复；本人规划、旧failed/unknown、原库/正式入口/Worker、部署、push/merge、RAG不在授权。整体STAGING_BLOCKED / NOT_READY。

## 2026-10-05 Known Invalid JSON → 有界 Batch Repair：非收费 PASS / STOP

- 用户现在新增能做什么：未来新Run的structure/practice在严格JSON失败、已知非截断响应、usage及durable failed attempt证明齐全时，可消耗原planning.repair；新deterministic attempt、Run repair2/request/output预算、完整canonical/task validator保持。没有新本人Run或新路线，本人原第一次生成仍FAIL。
- 基线88eb3b3492de7dff80ed812011cd09268075e38d、feat/n1-resource-discovery、tracked clean；只读核对/保留1416历史文件与160 request/result SHA，不操作保护目录，不reset/回退/切分支/push/merge。授权原文[本批Goal](STUDYPLAN_KNOWN_INVALID_JSON_REPAIR_GOAL_2026-10-05.md)，具体源码、边界与验收[本批报告](../acceptance/known-invalid-json-repair-2026-10-05.md)。
- adapter严格parser保持，仅增加HTTP200返回事实；ledger在failed事务commit后返回绑定证明，retained只接受实际failed且error/input/output列一致，冲突拒绝；batch显式失败占位由原validator→repair接手。独立failure receipt无payload/原文，checkpoint精确重建且final不能保存占位；成功batch包括null在内的失败marker拒绝。整批复核闭合failed-row及marker同调用链边界，不修改F1–F4成功语义或公开契约。
- 原真实G6 body7068bytes/SHA ffffffa319a2217bd889dca2f4c9416d21fc37d78903cbf4a090ccb3bf8d901c：严格parse FAIL事实保持；原冻结18stage/G6 index15未来离线副本→Fake repair1→practice validator PASS，坏原文不进checkpoint。新规则/compiled Fake/受影响unit与contract243 PASS（新58、contract31），negative matrix/budget/admission PASS。原RED和夹具字段/语法/tuple FAIL全部留存。
- 新owned business/checkpoint真实PG16定向案例PASS：两类完整Draft路径、normal/repair receipt-before-checkpoint恢复零新增Mock HTTP、unknown reconciliation/failed不claim、request/output/repair2、四类durable行冲突。标准owned Worker→PlanService success为succeeded/none/Draft1Plan0，非法repair failed/Draft0，unknown reconciliation/Draft0/repair0，后续均不领取；全部MockTransport/Fake，非真实provider。新临时库回收，全局角色修改0，PG初轮2 fixture FAIL保留，复用有效7项并定向修正2项+扩展7项。
- 原本人Run run_ba6527a948294cf0bbe9aab1ebc8c729 实际RC owned PG只读PASS：failed、34 succeeded+1 failed=35normal、repair0、Draft0/Plan0，禁止恢复/重派；history/usage/receipt/checkpoint保留。产品真实模型0，产品search/外部RAG0，quota160/200、剩40，原37normal+repair2≤39不变。新真实代表、浏览器/本人内容验收、正式操作NOT RUN。
- root/关键复核请求Sol6.1 xhigh、PG有界实现medium，actual均NOT OBSERVABLE，不改全局配置。KNOWN_INVALID_JSON_BATCH_REPAIR_PASS / STOP；只有用户下一明确批准才可新Acceptance/新本人Run，余额不自动授权。整体STAGING_BLOCKED / NOT_READY。下节保留原本人真实FAIL事实，不用fixture PASS覆盖。

## 2026-10-05 本人RC普通生成：已知JSON失败 / STOP，累计160/200

- 用户现在新增能做什么：`tiance7` 唯一普通提交已执行并终止，可在RC刷新读取failed历史；本次无Draft/Plan，不能进入新路线学习。API8034/UI5194保留，临时one-shot Worker已退出，不自动再收费。
- 产品源码不改，执行基线003423da16aabb0feaf119f7f5d0ce3fd8b2104f；复用P1/P2/P3技术PASS。新Run `run_ba6527a948294cf0bbe9aab1ebc8c729`，Acceptance `rc-user-tiance7-cebbca03153c`，仅原RC owned业务/checkpoint。没有第二生成POST/Run，没有confirm用户Draft。
- 实际冻结Agent8/18stage/37normal+repair2≤39/output241664；free binding/DNS/TLS PASS，exact meter MockTransport离线8 PASS，13项安全复核PASS，actual DSN名精确核对。harness GoalSpec合法purpose acceptance比较与mock字段修正，生产权威不改，原fixture FAIL保留。请求root/预算复核Sol6.1 xhigh，actual NOT OBSERVABLE。
- 首outline真实3671input/1319output/stop，JSON/keys/PG账本PASS，209998基线下降98.25188811%、无length。18structure+15成功practice逐阶段canonical/task保护PASS；G6 practice失败，GR/GT practice NOT RUN，不宣称全生成保护通过。
- 累计第160笔/本次第35笔G6 HTTP200/stop，provider_invalid_json；原content4177chars，JSON Expecting comma line113 col5 offset3506。实报2581input1534output，known FAIL非unknown/截断。generate_practice_batch的LLMFailure进入generation_errors，无parsed batch供localrepair，故35normal0repair/unknown0，Run failed，无Draft/Plan。旧failed不可恢复重派，未补用repair/另开Run。
- request/result126–160与PG/rawbody hash一致，34success1fail，费用reconciliation PASS；累计125→160/200、剩40；75617input+32927output=108544tokens，金额NOT OBSERVABLE。新FAIL completion同账本append-only，旧125账/1217证据/.env保持。产品search/RAG0；原库/正式入口/正式Worker/push/merge/全局配置 NOT RUN。
- 证据和下一准确门禁：[rc-user-plan-2026-10-05.md](../acceptance/rc-user-plan-2026-10-05.md)。需以原响应做离线fixture评审严格JSON拒绝与已知JSON失败的有界repair衔接，不改原失败结论、不自动使用剩40。本批USER_RC_GENERATION_FAIL / STOP，本人接受NOT RUN，整体STAGING_BLOCKED / NOT_READY；下方125/200是此前技术准备时点。

## 2026-10-05 正式运行收口：P1/P2/P3技术 PASS，P4授权包准备并STOP

- 用户新增能做什么：可访问 `http://127.0.0.1:5194/`，用本人正常账号登录本轮最新native restored/migrated/imported owned副本，读取旧项目/历史并体验页面。普通规划提交保持，Worker held，不会自动收费生成。本人目标、一次计量生成与主观接受仍NOT RUN；整体STAGING_BLOCKED / NOT_READY。
- 新 Goal `STUDYPLAN_RC_RUNTIME_CLOSURE_GOAL_2026-10-05.md`；基线 HEAD `8a28b17f7e019b93240343a5c6f071edf5af082e`、feat/n1-resource-discovery、tracked clean；1217历史文件/.env/receipt/账本 SHA 保存在 `var/rc-runtime-20261005/baseline.json`，不操作保护未跟踪目录。
- 实现SHA `954242a6e783cf5645cf477f6a11610081b57055`；普通PlanService两入口传独立frozen manifest，factory校验hash/model_ref后deepcopy，ledger实际purpose/key/output cap与Run repair2检查，modern新dispatch缺manifest拒绝/真正legacy与known replay保留。allowlist排除dispatched/reconciliation_required，与原trusted_server0020一致；published migration不改。
- P1全部13门禁PASS，组合unit/contract+ownedPG27、受影响fence/budget33、个人模型realadapter/MockTransport1，共61PASS；deployment binding另3PASS。普通Worker实际PGcheckpoint/Draft和独立submission对照；restart为runtime/ledger重建，OS kill NOT RUN。旧RED及fixture/diagnostic FAIL保留，只修fixture，不降来源权威；旧大套/本批UI build NOT RUN（复用前批有效证据）。证据p1-gate.json。
- P2源今日0023/61tables1517rows（13users18projects12Plans16Drafts26Runs），仅Agent1/Python1。PG16.4/client16.15；READ ONLY exported snapshot/nativecustom backup485041bytes SHA `a321631380f9dd1af32fbad0a09d3e77f4d9e68dcf80a25514e45aaa91d0a88d`，p2/private/source-20261005.dump。新owned business `studyplan_test_rc_p2_native_f482d3a3`/CP `studyplan_test_rc_p2_checkpoint_123aace8`，迁移前row/ACL/RLS/policies/columns/index/sequences/6函数精确PASS；已有0023→0024与Agent7+CURRENT AI4/Agent8/Cloud4/Python2/3依赖导入PASS，旧行/版本保持、10.1sourceV2、幂等/异体拒绝/nohalf PASS。harness UTC/tuple比较FAIL保留，从既有副本续接未重复dump/migrate。
- P2普通认证/app-roleRLS/admission/Fake bounded/真实PostgresSaver/Draft/syntheticconfirm/freshPlan-workspace/relogin/终态不重派3路线PASS：Agent8 18stage37Fake、AI4 8stage17Fake、Cloud4 11stage23Fake。仅本批3新synthetic Draft确认。副本63tables2922rows，旧私人/catalog业务行hash保持；1旧auth throttle临时行按正常认证过期，源全快照不变。原库写入0/globalroles0。
- P3真实Edge/API/PG Agent/AI/Cloud技术PASS：实际A2 3units1canonical1task、A5/A6/A8、小型/专项/成熟/迁移、GR2卡、A6 V2/10.1非fallback、catalog/fullguidance/Prompt/Node连续项目、refresh/relogin exact。首轮AI DOM whitespace FAIL原证据保留，仅harness normalization后继续AI/Cloud，Agent不重复。API8034 PID34332/session52961，UI5194 PID36476/session73794，健康200/200，owned-processes记录account/parents，服务保留，Worker held。settings/caps保持8192和4096/8192/4096/8192，modelceiling0为未指定，trusted_server正常。
- P1/P2 真实模型请求0；账本125/200、剩75保持。只有 P1/P2 PASS 后本人 RC 一次正常新生成才可使用既有最多37normal+2repair39授权；不会再开 synthetic paid representative。原库写入/正式入口/正式Worker/push/merge/全局配置 NOT RUN。
- RAG F17 BLOCKED：已识别本机PersonalRAGfrontend/DB归属E:/RAG quention；未见APIcontainer，static OpenAPI无pure retrieve/auth security contract。检索/隔离/citation/错误/无命中NOT RUN；未启动/修改RAG。GitHub OAuth当前未见完整配置/路由，真实验收NOT RUN，不与普通auth混淆。
- 请求root/预算安全复核Sol6.1 xhigh，独立P2/P3有界执行Sol6.1 medium，实际解析均NOT OBSERVABLE；不改全局配置，合并反例/复核、不重复大套。1217历史保护/.env/receipt/账本最终hash核对另存，历史failed/unknown、旧F2、Agent7保持。
- 唯一正式操作授权包：[rc-runtime-closure-2026-10-05.md](../acceptance/rc-runtime-closure-2026-10-05.md)。Gitrange/target、原库0024/import写表与私人保护、backup/rollback、API/UI/Worker命令/profile/ports/PID/stop、admission/费用、RAG/OAuth及本人动作集中列明。P4准备后STOP，不自动正式切换/push/merge；本人先提交真实目标，既有一次≤39授权仍有效，不另造synthetic paid代表。

## 2026-10-05 A6 来源/当前闭环及唯一新收费代表收口：PASS / 正式操作 STOP

- 用户新增能做什么：新Agent8保留有正文依据的MCP10.1；后置合法冻结资源丢失拒绝保存；新owned Plan已实证学习/GR/Prompt/总结/成果/完成/变更/历史/refresh/relogin。正式入口未开放，整体 STAGING_BLOCKED / NOT_READY。
- 实现SHA `859db09f4d154b0397ad763146d34561e5af404a`，进入本批本地/已核实远端 `9fef887af21dd5ff2a60aef306a6b9b02d176f5f` 的后继；无reset/回退/push/merge。仅10.1授权正文审读和新immutable Agent8/sourceV2，第十章source/section新ID；canonical、任务、F1–F4/F2/GR/教学结构/其他资格不变。
- 原事实STOP/旧45of46 FAIL保留。原目录级10.1不足正文资格；新实际10.1.1–10.1.4英文静态正文已审，runtime/图片/外链验证 NOT RUN。actual save-entry normalize后冻结合法资源断言、legacy与合法用户修订兼容 PASS。
- 新35同因边界PASS、旧同次执行197项PASS复用（有提取provenance，非重跑）、budget/contract31PASS、费用AST/mock7PASS、前端16PASS/buildPASS。原RED与11个新测试字段误读FAIL都保留，不以计数替代内容验收。
- 38原响应compiled replay、owned真实PostgresSaver/业务PG/新fake receipts/synthetic confirm/fresh readback PASS：18stage/16canonical/58units/18tasks/37extensions/46slots74refs；测试包装6处精确source alias，原响应不改；A2原5units仍同canonical1task。真实Edge23checks PASS，GR2卡2仓库1task、完整guidance、Prompt原文修订/指定export/未保存保护、summary409、synthetic external/USER决定、阶段完成无KnowledgeVERIFIED、一次资源diff/confirm/newrevision/旧history与refresh/relogin。回放新Run `run_fc8ca606ec0d446f805541901c7149ee`，当前Plan `pln_8397681c34e5415a9524886ed7cbe3f5` revision2，服务已关闭、库保留。
- 全非收费PASS后free binding/DNS/TLS PASS，唯一全新paid Acceptance `delivery-agent8-rag-synthetic-3c602f0ab1bc` / Run `run_96778f62c994478bb68f9df1ad5a67d3` succeeded/none，真实outline3673 input/1400 output/stop、209998基线下降98.25093572319736%、无length。18structure/18practice逐阶段canonical保护及独立readonlyPG/CP/receipt/source审计 PASS；实际53units原生保存（A2为2），46slots/16canonical/18tasks/37extensions保持。Draft `drf_08160109502b5c978d4f772ce0dd4aff` awaiting_approval、Plan0；新收费Draft确认/发布/其Edge NOT RUN（只回放Draft获syntheticconfirm许可）。
- 同账本append-only扩额previous_cap=100/additional_authorization=100/new_cumulative_cap=200/used_before_authorization=88/remaining_after_authorization=112已记录一次。本轮37normal/0repair/unknown0，最终125/200、剩75；81562input+37412output=118974实报tokens。首份代表PASS后不再收费；历史failed/unknown不重派。产品search/RAG0，授权同章目录1/body1；旧6/1000及921保护文件/.env/账本/response保持。
- 原F2库fresh scoped readonly：旧Draft awaiting、Plan0、45/46 FAIL保持。原实际配置库readonly PASS：schema0023，已发布仅Agent1/Python1；写入0。正式Worker预算/admission运行收口、latest native副本恢复forward0024/AI4-Agent8-Cloud4导入演练、原库/入口/Worker正式授权、用户非空Plan接受及独立RAG合同仍待。原库写入/部署/RAG/push/merge NOT RUN。
- 最终报告 `docs/acceptance/delivery-acceleration-2026-10-05.md`，证据 `var/delivery-20261005/`，账本 `.git/v2-paid-quota-20261001/`。当前Goal完成并STOP于正式操作边界，不因剩余额度再开Run。

## 2026-10-05 A6 正文授权续接 / Agent8 不可变版本（执行中）

- 用户明确授权仅同一教程 10.1 正文审读及下一不可变内容版本；覆盖先前冻结资格不足 STOP，仅此范围。原 Agent7/旧 F2 Run/Draft/response/receipt 不改。
- 新 Agent8 仅第十章来源与四章节获得新身份，source_version=2；仅10.1新增正文依据，其他审读资格、canonical、教学、practice、Framework/MCP/GR不变。全文98277bytes SHA256 e68e510739fc08527f994eac7ab4104b5abc38f4b51c3e788d2fa9ef2111a60d；英文静态正文审读，不宣称运行验证。
- 保存前从独立 checked_projection 与冻结 blueprint 校验合法资源来源/版本/章节/role/order/nodeIDs；normalize后丢失拒绝保存，legacy和合法已有用户修订不改。root新34例 PASS；附加已有修订兼容1例 PASS；budget/contract31例 PASS；前端 build PASS。首次组合中的11项测试错误保留（错误读取异常reason字段），已由新增组合修正，未改业务保护。
- 新 owned PG 编译图38份保留响应回放/1repair、46slots74refs/18阶段16canonical58单元18任务37extensions PASS；仅测试包装层6处精确来源身份别名，旧原文不变。新Run run_fc8ca606ec0d446f805541901c7149ee 已 synthetic confirm/freshPG/API/checkpoint读回 PASS；仅本轮新合成Draft。
- Edge当前闭环进行中；新收费代表 NOT RUN，累计88/200、剩余112、unknown0（本批）。本次正文公开目录读取1、同章正文读取1，产品搜索/外部RAG0。原产品库/正式入口/正式Worker/RAG/push/merge NOT RUN；整体 STAGING_BLOCKED / NOT_READY。

# V2.0实施进度（唯一当前检查点）

## 2026-10-05 用户追加产品模型额度：累计200，已用88，剩余112

用户明确新增100次产品模型调用授权，覆盖上一版Delivery Goal“本轮产品真实模型请求0”的额度限制；同一授权重复发送仅追加一次，不算两份100。previous_cap=100 / additional_authorization=100 / new_cumulative_cap=200 / used_before_authorization=88 / remaining_after_authorization=112。已在同一权威账本追加 `.git/v2-paid-quota-20261001/authorization-delivery-20261005-cap-200.json`，旧authorization-v610与88request/result/receipt字节保持，不重置账本、不更改全局配置；本次模型实际新增0，当前88/200。

继续原顺序与门禁：A6确定性修复→原response/Fake/ownedPG零收费回放→A6/46-slot/canonical/practice/Draft/Plan/Edge全部PASS→仅全新Acceptance/Run/owned两库的完整paid代表，37normal+repair最多2=39；每笔append-only计量，unknown立即STOP，首份完整PASS停止继续收费，独立FAIL先停止收费并离线定位/修复再决定第二份。当前A6已定位但10.1原冻结仅legacy_index/toc_checked，与现Agent教学章节资格合同冲突；非fallback门禁FAIL，扩额不授权升资格/改旧冻结，因此依赖的PG确认/Edge/paid仍NOT RUN并STOP。正文审读/下一不可变版本或TOC reference消费合同需明确裁决，详见下方本批报告。

原产品库/正式入口/正式Worker/部署/push/merge/全局配置/来源canonical任务预算安全放宽/历史failed unknown重派均未获授权；原搜索/下载/外部RAG0限制保持。下方88/100等是本次扩额前的历史时点，不覆盖本条最新200上限。


## 2026-10-05 Delivery Acceleration：A6 冻结资格矛盾，BLOCKED / STOP

用户现在新增能做什么：审阅[A6首次降级、完整原响应离线回放与正式操作剩余](../acceptance/delivery-acceleration-2026-10-05.md)。没有新体验入口/Draft/Plan。进入分支feat/n1-resource-discovery，HEAD与核实远端均9fef887af21dd5ff2a60aef306a6b9b02d176f5f；保留已提交组合v6.11/v6.12/v6.13/GR/F2成果，tracked原干净，仅两保护目录未跟踪，未操作。业务/包/资格/API/DTO/迁移/provider/全局配置差异0；本批只写ignored诊断/证据与本报告和progress顶部。

原冻结submission与38body/response/receipt绑定精确复核PASS；新memory fake/replay compiled graph按51–88原序列、58normal→59knownrepair，未改原内容/manifest/pack。18stage/16canonical/58unit/18task/37extensions和全部46原slot经merge/独立checked_projection保留；首次清空是restrict_pack_resources，45保留1降级。A6 reference order0 source reviewed/version1但10.1 section为legacy_index/toc_checked，原注释明确正文审读10.2/10.5.1、10.1仅chapter structure/summary；身份/版本/归属/适用键正确，非selected_scope_pending。既有Agent合同要求该未深审参考剥离引用并fallback；validate_seed允许候选入包不等于审核章节消费。原冻结74section引用含1目录级，消费73；非fallback门禁RED1FAIL保留，资格诊断最终8不同PASS（首轮7PASS1测试seamFAIL保留、仅ignored诊断修正），一次Sol6.1xhigh组合复核PASS。按活动Goal§4.2 STOP来源修复及依赖PG/Edge，未改冻结资格追绿、未新增落库断言或UI链接伪修复。

本轮真实PG只读角色预检PASS，新owned业务/checkpoint/确认/Edge/Prompt总结成果变更闭环/build NOT RUN；没有数据库/服务/Worker新建或启动。921旧历史/已完成F2/.env/账本文件保护；原F2 Run/Draft不连接业务写入、不确认、不重派、不改原FAIL。产品模型新增0，88/100/余12保持；搜索新增0（旧6/1000）、正文/外部RAG0，本轮unknown0，历史unknown保留。日常Worker默认trusted_server与100验收wrapper不同；静态runtime ledger未传manifest，实际预算绑定须非收费核实后才可开正式Worker，未扩大为本轮修复。无新收费申请（旧v6.7下一代表已由v6.8完成，不能据历史下一动作重复申请39）。下一准确缺口为10.1正文审读依据/下一不可变版本，或明确带资格限制的TOC reference消费合同；原Agent7和旧Run/Plan保持。原库/正式入口/正式Worker/RAG/push/merge未动；A6_SOURCE_QUALIFICATION_BLOCKED，整体STAGING_BLOCKED/NOT_READY并STOP。请求root/复核Sol6.1xhigh、独立机械Lunamedium，actual均NOT OBSERVABLE。以下历史进度正文原字节保留。


## 2026-10-04 F2-negative-extra-task：修复PASS，唯一新代表来源FAIL，BLOCKED / STOP

用户现在新增能做什么：合法“不要求照搬其工程结构或新增工程任务”在structure/repair不再误判；正向/混合义务仍保护。最新路由已同步AGENTS与model-routing-policy：Luna low/medium机械提取；Solmedium有界代码/常规测试；Solxhigh安全/预算/引用/有证据升级；同问题测试与复核合并，不重复读长历史，actual均NOT OBSERVABLE。详见[本轮合同/教学/真实用量与STOP审计](../acceptance/f2-negative-extra-task-2026-10-04.md)。

实际起止HEAD 1a3262e85296c95d3dfb4349d0d4ef83438f17da、feat/n1-resource-discovery，组合工作树未提交、不回退。67候选+binarypatch+692unique历史与路由原文受限备份CRC/SHA PASS；唯一业务差异planning_structure文字门禁/helper，F1/F3/F4/GR/3pack/任务/来源资格不改。保留旧A1 normal48/repair49/50精确fixture，RED62PASS41FAIL→GREEN117PASS；173不同unit/contract PASS、28收费harness离线安全反例PASS、4新ownedPG教学/compiled checkpoint/Fake PASS。原GR/System/MCP/Node/long refresh/relogin Edge通过94消费者hash复用，本轮新paid Edge NOT RUN。

免费binding/DNS/TLS PASS后只开新Acceptance f2-negative-task-agent7-rag-synthetic-48ea731e4a48 / Run run_9f6db411f8d1415a818e7d3f69e14ab8。实际18stage/16knowledge/58units/18tasks/46resources/37extensions，A2五单元单canonical/任务，A5Framework/A6MCP/A8Pi/G0–G6/GR两候选一任务/GT保持。真实outline3673input/1396output/stop，较v65 209998下降98.25093572%，JSON18keys与PGledger门禁PASS后才继续；18structure+18practice逐阶段canonical PASS。37normal+1A6已知顶层shape localrepair=38requests，quota50→88/100、unknown本轮0、input85528/output42965、38known stop，生成后收费增量0、搜索新增0。

完整生成技术succeeded且Draft drf_aa6f1f8b3478527185cdb1f2c009fb22 awaiting_approval，但独立教学来源精确复核46slot为45PASS1FAIL：A6首reference丢失已冻结MCP10.1 source/section，实际Draft及只读ownedPG空source/version0/空章节fallback；这是新独立缺口，按用户规则STOP，不修/不补来源/不放宽，不确认、不创建第二Run。approved Plan/publications0，nodes16/units58/tasks18保留，job completed保留terminal lease token、无runningjob。确认/PG消费/Edge服务仅准备NOT RUN，原库/正式入口/正式Worker/RAG/push/merge未动。692历史/.env/旧50receipt字节保持，旧失败/unknown永不重派，新Draft与两owned库/38response+receipt保留。F2_PATCH_PASS；PAID_REPRESENTATIVE_PATCH_FAIL；STAGING_BLOCKED/NOT_READY；下一须新Goal有界定位A6来源落盘缺口，剩12不自动派发。


## 2026-10-04 GR Project Candidate binding：非收费PASS，真实代表FAIL，BLOCKED / STOP

用户现在新增能做什么：普通学习页面能把RAGFlow与WeKnora各显示为一张绑定冻结来源的候选卡，各自完整guidance/仓库链接/targeted Prompt保持，GR仍只有一个任选案例证明相同能力的正式任务。详见[本批来源/教学/用量及STOP审计](../acceptance/gr-project-candidate-binding-2026-10-04.md)。最新用户授权仅修GR消费，保留组合v6.11/v6.12/v6.13候选，不改F1–F4/Agent7/canonical/任务/资格。起始/停止HEAD均1a3262e85296c95d3dfb4349d0d4ef83438f17da、feat/n1-resource-discovery；未提交，无reset/restore/切分支/push/merge。55候选+binarypatch与563历史受限备份、SHA/CRC PASS。

实际Edge RED复现4重复pending卡；freshPG证明同Plan已有assignment/source_ref/version/source.source_id/version/canonical_url及对应冻结extension links，metadata-only sections=[]合法。独立评审确认持久化足够，必要最小增量为既有资源DTO可选只读canonical_url（无新endpoint/schema/迁移）；仅同Plan匹配frozen来源输出，身份/版本/资格/warnings冲突null，不当前catalog补齐。consumer经审评unique规范化exact repo对应，最终key使用assignment/source/version，title仅display；显式null不得legacy降级，歧义unbound不补重复fallback，资格legacy_index保持。PlanService仅_resolve消费AST变化，保存与F1–F4逻辑/其他锁文件和3pack字节保持。

后端15PASS、相邻合同134PASS、前端27PASS/buildPASS；未来新ownedFakeRAG生成/确认/读回1PASS（37Fake/真实0，新测试库回收），GR2资源1任务/空章节/原资格/canonical rubric/3单元1canonical1task保持。真实Auth/API/ownedPG/Edge五场景PASS：GR恰2卡各562/556guidance与targetedPrompt/复制；A5Framework/A6MCP/A8smallcore、G0–G6/GRGT；long两片1119chars完整；System/MCP/Node及五场景refresh/logout/relogin精确GET。233HTTP/auth10+5/business写及generation/confirm/model/Worker/external0，自有服务已停。旧v68 live Plan与v610 live failed Run只读PASS；v610历史FakeDB不存在单列NOT RUN，不造替代/重派；旧PG/证据hash保持。

免费actualbinding/DNS/原guard/TLS PASS；实际Agent7v7全RAG manifest18stage/18structure/18practice、37normal+2repair39/output241664，起始45/100理论最坏84。仅一个新Acceptance gr-binding-agent7-rag-synthetic-329770a29268 / Run run_5141feb22038497cabfaac09b14ba8ee，仅新owned两库。首笔outline真实input3673/output1189/stop、JSON18keys/PG账本PASS后才继续；相对v65 input209998下降98.2509357232%，无length/truncation。A0canonicalPASS，A1normal+两repair仍被合同拒绝，Run failed，无Draft/Plan。5provider回执均known成功stop，freshPG1Run/5receipt/unresolved0/无业务物化或活动租约PASS。

新增3normal+2repair=5真实请求，最终50/100/余50/50对receipt/本scopeunknown0；实报总input15414/output5038；搜索新增0，旧6/1000保持。A2及后续structure、全部practice、paidconfirm/Edge NOT RUN。原5body bytes/JSON保留；最后repair独立纯离线归因PASS：否定句“不要求…新增工程任务”被extra_required正向regex误判，否定规则未覆盖新增；仅诊断副本去该句完整validator1→0，原响应及生产未改。这是新F2变体；latest明确不改F1–F4，所以STOP不修、repair不增、不第二Run，不复用failed/unknown。绑定与非收费教学PASS≠真实完整路线PASS；整体STAGING_BLOCKED/NOT_READY。原库/入口/正式Worker/RAG/部署未操作，563历史/.env/旧账保持。root/review请求Sol6.1high，独立实施/PG/Edge/准备medium，actual全部NOT OBSERVABLE。下一仅审阅保留A1/repair及独立失败归因，后续F2实施或收费需新Goal，不自动续跑。以下为历史时点。



## 2026-10-04 v6.13 Contract Closure：BLOCKED，STOP

用户现在新增能做什么：审阅[F1–F4合同修复/真实PG与STOP审计](../acceptance/v6-13-contract-closure-2026-10-04.md)、[新Agent7 Fake/ownedPG Plan及实际教学消费](../acceptance/v6-13-plan-and-teaching-2026-10-04.md)和[27定向+原31项矩阵](../acceptance/v6-13-acceptance-cases-2026-10-04.md)。执行用户批准v6.13而非重规划；HEAD起始/停止均1a3262e85296c95d3dfb4349d0d4ef83438f17da/feat/n1-resource-discovery，继承v6.11/v6.12+本轮候选尚未提交。38相关文件/425历史已受限ignored备份，无法精确拆旧批次则保留组合基线，无reset/整树restore/push/merge；425hash/.env/45对旧账/继承Agent7AI4Cloud4与UI字节保持。

F1新增共享纯重建/比对：独立server planning_submission+同Run/stage/attempt原成功响应→确定性hydration/merge→比对全部拟持久化投影，实际executor与PlanService物化前共用，差异拒绝同一验证副本；raw和normalized一起伪造不能自证。F2所选focus正向许可/比较/排除与GoalSpec明确负约束分离，合法Cloud实践及不相关约束保留。F3normal/output/repair分离JSON字符/UTF8上界，11058反例完整Mock repair，超大预检SQL/HTTP/Fake0、实际repair_count0；caps/repair2保持。F4独立完整合同识别阻止单项/全部marker删除、null/unknown及perbatch降级，真legacy和短outline旧structure保持。只读review定位repairreceipt先提交checkpoint滞后时序，局部精确pending known-replay处理，真实checkpoint+SQL回执MockHTTP0，final不能例外。

最终unit/contract1018PASS2NOT RUN（Windows symlink）；ownedPG21独立PASS（主轮18PASS1PythonSeed夹具FAIL，修夹具定向3PASS；历史FAIL保留）；兼容PG60PASS1裸fixtureFAIL+显式依赖修正单项1PASS、route/concurrency7PASS。F1–F4保护与独立源码复核PASS；本轮frontend unit/build NOT RUN复用字节未变的v6.12有效证据。新RAGPlan pln_8173fe1c0c7a49ada2a0cc589dfe4b2a/Run run_f9d2da474bb04ed39fb07b493fdaf41f、Agent7/18stage16canonical20unit18task46安排73可读refs37extensions，A2three/one/one。系统9、MCP4、Node11及Browser/Coding/旅行/Voice/AI/Python/search-only非收费PG持久化PASS；原源资格不升级。

实际普通Auth→API→ownedPG→Edge初始准确读回/A2三单元/A5A6A8/G0–G6/GRGT/whole_core Prompt PASS，GR真实卡片FAIL：RAGFlow/WeKnora各重复两张共4，全pending无仓库链接；两case_study/repo资源ordered_sections=[]而两extensions有rootURLs，既有分组缺可信绑定后补fallback卡。独立新消费结构根因触发最新用户及Goal§0/§12 STOP，未修UI/DTO/来源资格或改Plan追绿。剩余RAG刷新重登录/system/MCP/Node/long Edge、旧版本livePG、免费真实binding/DNS/TLS与paid代表NOT RUN。自有API8031/Vite5191关，62HTTP/authPOST2/业务写0/provider+Worker尝试0；清理代理8000连接拒绝记录保留，仅harness薄清理修正NOT RUN。

合同源码PASS不等于合同整体闭合：CONTRACT_CLOSURE_BLOCKED、PEDAGOGY_AND_UNITS_BLOCKED；真实代表NOT RUN，真实新增0，权威45/100/余55/该scopeunknown0、搜索新增0（旧6/1000）。37+2=39/output241664/理论84≤100未执行实际binding门禁；无本轮paidAcceptance或第二Run，不重派历史failed/unknown。请求root/reviewSol6.1high、独立测试/PG/Edge/准备Sol6.1medium，实际NOT OBSERVABLE。原产品库/正式入口/正式Worker/RAG/公开DTO/API/迁移未改；整体STAGING_BLOCKED/NOT_READY并STOP。下一仅评审GR来源消费身份绑定最小修复范围，不自动进入后续阶段。以下为历史时点。

## 2026-10-04 v6.12 Targeted Alignment：BLOCKED，STOP

用户现在新增能做什么：审阅[来源明确的新完整Agent+RAG Fake/owned PG计划](../acceptance/v6-12-fake-plan-review-2026-10-04.md)、[31项教学验收与缺层](../acceptance/v6-12-acceptance-cases-2026-10-04.md)及[本批审计](../acceptance/v6-12-targeted-alignment-2026-10-04.md)。以用户批准的交接包01产品决定/03Goal为语义与授权；真实本机HEAD起点/停止均1a3262e85296c95d3dfb4349d0d4ef83438f17da、feat/n1-resource-discovery，ff3b6c4祖先PASS，复用v6.10与已有v6.11未提交候选，无reset/回退/新格式平台。工作树候选与审计尚未提交，不称已接受版本。

N0公共Agent6 canonical61阶段与旧失败私有7阶段分别导出；旧v610 failed Run仅owned PG READ ONLY查证三次已保存parsed原响应一致，原HTTP wire未存。6新增key中5项是受审范围教学细分，timeout-audit完整实施证据不足；不接纳新知识key。旧原fixture字节保留，legacy三次仍失败1/9/1，不重派failed/unknown。

候选复用reviewed_structure_v1并冻结stage_focus_v1、逐批次canonical eligibility、完整units四字段及local focus/short boundaries，原始响应与本地canonical回填分层。Agent7/AI4/Cloud4分开受审教程/小型源码/成熟切片；新完整Fake路线A0–A8含A5 Framework/A6 MCP→G0–G6详细RAG→GR目标切片→GT迁移，18stage/16canonical/18task，A2三单元同canonical/一task。RAGFlow/WeKnora可替换案例只一任务；Node11stage自己的API连续；窄MCP四阶段、专项待选Agent9阶段。旧包/已冻Plan未改，资料深度/runtime资格不升级；独立已审TypeScript课程仍缺。页面在普通主区显示unit顺序/标题/目标/关联知识，无API/DTO/迁移或新完成门禁。

最终unit/contract951 PASS、2 NOT RUN（symlink），内容定向69 PASS，owned PG/Fake10 PASS（4条新合成确认Plan与checkpoint批次保护），frontend16 PASS/build PASS，真实Edge renderer+Mock API多单元/项目卡PASS。实际owned Plan Edge NOT RUN，真实provider/free preflight/paid代表/paid确认NOT RUN。中途FAIL与修正前证据保留。

只读合同复核发现四项FAIL且均未修：F1 save_draft_projection前checkpoint顶层canonical/teaching rubric篡改绕过恢复检查，实际compiled graph+内存saver保存回调一次收到篡改值，恢复新增Fake0（真实PG越权保存未验证）；F2否定K8s说明被当许可；F3repair完整失败对象输入上界提前拒绝并消耗local repair_count；F4外层marker+hash同时删除后直接批次走legacy（正式恢复/merge仍拒绝）。按Goal§0“新的结构性问题STOP”停止实施与Edge/收费派发，PEDAGOGY_AND_UNITS_READY未建立，最终BLOCKED/STOP；已有PASS不覆盖这四项。

真实模型新增0，权威45/100、45对回执/该scope unknown0、剩余55；搜索新增0、旧6/1000保持。18阶段Fake manifest37normal+2repair=39、output241664、45+39=84≤100；真实binding门禁NOT RUN，不自动消费剩余额度。335受保护历史文件/.env/旧账/旧Plan证据hash PASS，新Fake owned库与private账号保留无服务开放，未新建本轮paid Acceptance/Run。正式库/入口/Worker/RAG/push/merge/reset/两受保护目录未操作，整体STAGING_BLOCKED/NOT_READY。下一仅评审F1有界恢复/保存防护方案，不自动进入下一开发阶段。以下为历史时点。

## 2026-10-04 v6.10 Planning Alignment：BLOCKED，STOP

用户现在新增能做什么：查看[三条新 Fake/owned PG/Edge 教学样本](../acceptance/v6-10-planning-alignment-samples-2026-10-04.md)与[逐用例/账本/真实失败审计](../acceptance/v6-10-planning-alignment-2026-10-04.md)。完整 Agent 有 A8 Pi whole_core 的实际知识/任务/资源/Prompt及后续组合路径；窄 MCP 仅四阶段；Node API 使用自己的载体，明确隔离 Micro Exercise 与云商/语言/DB 待审边界。新源码候选 Agent6/AI3/Cloud3 仅在 owned catalog 验证，正式目录未导入。基础本机为ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/feat/n1-resource-discovery，没有v6.9实施内容；复用v6.7/v6.8，不reset/回退。实施本地提交817b17b，无push/merge。

用户明确只覆盖产品模型调用0/禁止收费验证：原受控历史39次保持，同scope总上限50→100，新增授权50、理论初余61；搜索新增仍0。权威账本沿用.git/v2-paid-quota-20261001，追加authorization-v610审计，不新建全局计费系统、不改.env cap8192。先离线/Fake/unit/owned PG/Edge通过才执行唯一新Acceptance v610-agent6-synthetic-c5c4af9fb8f8 / Run run_9c00403807ee4ccb817529611e44efa6，仅新owned业务/checkpoint两库。

非收费验证：完整unit/contract **898 PASS、2 NOT RUN**（Windows symlink权限，exit0）；最新规划/canonical定向58 PASS；owned PG教学/发布/长文本8 PASS；marker/真实checkpoint/失败不重派7 PASS；语义/hold/旧snapshot/digest/未来route9 PASS；前端16 PASS/build PASS。实际Edge三条普通认证→生成→合成确认→workspace→刷新→退出重登录PASS，系统7stage/7task/A8node1、MCP4stage/4task、Node9stage/9task/4独立练习；页面error0/externalattempt0/额外generate0。双候选与>850有序指导另由组件Edge及独立owned PG合成v7夹具验证，不覆盖CURRENT Agent6。

免费实际绑定、public DNS、原endpoint guard、direct TLS及输入隔离PASS；新7stage manifest上界15normal+2repair=17，output106496。短outline4653chars/6460bytes，真实首请求1516input/413output/stop，7keys与PG账本门禁PASS。真实A0/A1 structure与逐阶段canonical恢复PASS；A2新增6个未审核知识键，repair1缺必需nodes/units/relations，repair2仍新增相同键，2次repair耗尽，Run failed无Draft/Plan。因此真实代表FAIL，A8/practice/真实确认/真实Plan Edge **NOT RUN**；MCP/已有项目收费代表NOT RUN。不以HTTP200或Fake链路替代真实Plan验收，不追加第二Run或放宽schema/canonical。

**起始39；本轮新增授权50；总上限100；实际新增6（正常4+repair2）；最终45/100；本轮unknown0；理论剩余55；搜索0增量（旧6/1000保持）。** 六笔完整回执/PG request6/unresolved0一致，失败Run新进程不可claim，无重派；188受保护文件含历史39对receipt、旧包、v6.8 Plan/Acceptance/evidence及.env哈希PASS。新失败账本及owned两库保留；正式库连接/正式入口切换/正式Worker/RAG/外部项目写入0。源码协议、公开DTO/API/迁移、安全与repair2门禁保持；root Sol6.1/high、前端Sol6.1/medium、内容Luna/high请求，实际解析NOT OBSERVABLE。完整原始输入哈希归档及RED/中途FAIL保留，未宣称全方向真实provider通过。

BLOCKED后STOP，整体STAGING_BLOCKED/NOT_READY。当前阻塞是A2冻结知识键集合与真实structure/repair输出不匹配；后续须定位精确生成/repair契约、先做非收费验证，再评审新的代表，不删A8、接纳未审节点、增repair或改旧真实Plan。55次剩余授权记录保留，不因还有额度自动派发。以下均为历史时点。

## 2026-10-04 v6.8单一真实代表：PAID_REPRESENTATIVE_PATCH_PASS，STOP

用户现在新增能做什么：已有一个真实provider生成、合成确认并在owned PG/获准Edge刷新重登录消费通过的完整Agent5 Plan，可评审内容与体验；正式入口/原产品库/正式Worker未启用，全产品仍STAGING_BLOCKED/NOT_READY。[批准Goal](STUDYPLAN_V6_8_PAID_PROJECTION_GOAL_2026-10-04.md)精确归档，[完整审计/逐笔用量/保护/浏览器/风险](../reviews/2026-10-04-v6-8-paid-projection-representative.md)。起点2ed6485e3cb1b52e199e9c8aeb04f99e3f3cc2b1、feat/n1-resource-discovery、tracked clean，v6.7 patch在祖先链；本轮业务源码/.env/cap/model/API/DTO/迁移/Seed未改。

唯一新Acceptance v68-agent5-synthetic-67ca1224a56f、Run run_3170cfe33c3f4b71b9dd7746b228443f，新owned业务studyplan_test_v68_business_f064eec7/独立checkpoint studyplan_test_v68_checkpoint_a598073d，仅公共Agent5与同v6.5可比零基础synthetic目标。17硬预检PASS、实际提交stage_skeleton_v1/hash绑定、4112chars/5239bytes、当前公网DNS/原guard/directTLS1.3与13+2预算PASS。v6.5旧Acceptance/Run永不复用。

首个outline HTTP200、LLMResult/JSON/shape/冻结6keys/ledger PASS，真实input209998→1351（减少99.35666054%），output4097/length→603/stop，无截断；latency实际16222→3020ms。total1954、cachehit0/miss1351。持久化outline回执和unknown0门禁后才继续structure。6structure+6practice+2local repair完成；A1先缺结构顶层字段，再修复引入未声明子键，第二次repair校验通过，原known失败及绑定保留。normal13/repair2/总15，不再有本轮费用授权。

真实token totals：outline1351/603、structure10114/4336、practice10956/6815、repair6929/1737；总input29350/output13491/total42841；15响应均stop，美元费用NOT OBSERVABLE。12逐阶段canonical门禁PASS；完整Draft与已发布PG逐项核对6stage/6knowledge/18安排/35refs/13extensions/all guidance，canonical知识完整rubric/实践实体、5依赖边/6task知识links/6completion gates精确PASS，额外required task/extension0。无强制Starter或冲突验收。Common Core无project-study/case-study安排，其可替换载体extension正常；用户项目/开放Recipe/RL optional等复用v6.7未变语义证据。

最终owned PG1succeeded Run/15attempt/1approved Draft/1PlanRevision/unresolved0；唯一synthetic confirm、fresh container PG读回/退出/重登录PASS。Chrome工具不可用后用户明确“允许改用Edge”；Edge登录、路线35章节、guidance/extensions/practice、刷新/退出/重登录PASS，Chrome本轮NOT RUN。浏览器一次401登录/403注册保留，注册guard拒绝无副作用；两次登录200/退出200，未打开外部资源链接/模型按钮。生成后模型请求增量0。受控API8028/前端5188验收后关闭，正式Worker OFF。

quota24→39/50、本轮unknown0、搜索新增0/最新6/1000；起始48账本/旧Acceptance/9份v6.5证据/正式.env hash保持，旧unknown不重派。原库/真实用户/RAG/AI2/Cloud2/正式入口/Worker/merge/push均未操作。隔离脚本编码/DTO字段/可选默认/候选topic/login额外字段及最终审计错误保留，纠正后消费与审计PASS，没有模型重发、第二Run或重复confirm。宽unit/frontend build NOT RUN，复用v6.7有效结果；root请求Sol6.1/high、实际NOT OBSERVABLE，无子代理或全局设置修改。普通文档提交SHA动态报告；费用不可回滚、两owned库及证据保留。PAID_REPRESENTATIVE_PATCH_PASS后STOP，整体仍NOT_READY；唯一下一动作是用户验收本轮合成Plan内容与体验。以下为历史时点。

## 2026-10-04 v6.7 outline投影与内容保护：OUTLINE_PROJECTION_PATCH_READY，STOP

用户现在新增能做什么：未来新提交使用冻结 `stage_skeleton_v1` outline短契约，并确定性保留reviewed知识和practice事实；可据离线与owned PG证据评审下一单一收费代表。本批没有真实模型Plan，正式入口/Worker未启用，全产品仍STAGING_BLOCKED/NOT_READY。[批准Goal](STUDYPLAN_V6_7_OUTLINE_PROJECTION_PATCH_GOAL_2026-10-04.md)逐字节归档，[完整审计/测试/用量/风险/回滚](../reviews/2026-10-04-v6-7-outline-projection-patch.md)。基线df10870add16d658cd706ec26e021d276db0932d、feat/n1-resource-discovery；续接现有成果，不reset/切分支/merge/push。

新marker进入manifest_hash与既有attempt语义指纹；无marker保持legacy hash/wire/merge/恢复语义，不改历史Run/checkpoint或重派v6.5。新outline只携带短目标/起点/偏好/语义及阶段和知识键、顺序、必要前置；完整resources/章节/guidance/extensions/practice/project-study仍在本地权威数据，structure/practice局部输入未膨胀。独立短system/shape，不全局升级prompt_version/cap/model。六阶段实际adapter离线messages578108→4112chars（减少99.29%）、HTTP816500→5239bytes；真实tokenizer/收费tokens NOT RUN，不把char/4估计当实报。精确回填18安排/35refs/13extensions及全部guidance，五语义路线PASS。

新格式唯一及重复知识恢复title/objectives/scope/acceptance/parent/prerequisites；实践按reviewed身份/数量/目标/范围/交付物/验收/links重建，额外次级任务、强制Starter和冲突acceptance移除，不任意union。现有rubric JSONB持久化完整canonical事实，无迁移/API/DTO或阶段完成规则改变；当前契约不支持显式optional canonical task，新冻结对此fail-closed，optional项目/Starter extensions保持。review发现删除/置空marker可绕过格式门禁，RED确认后在生成/merge/真实checkpoint恢复前补强digest与pack检查；规范JSON比较兼容tuple/array。

本批新unit/Fake PASS38；完整unit/contract PASS878、NOT RUN2（已有symlink权限），exit0。owned业务PG+真实PostgresSaver/checkpoint PASS7，覆盖普通Auth/CSRF新提交、持久化重建、Fake Draft/显式synthetic confirm/Plan回读、新旧恢复、失败不重派与篡改拒绝。相邻恢复PG最终21PASS/1FAIL；force-kill时序单项新owned库复核1PASS，原FAIL保留，未宣称一次全绿或根因完全定位。Ruff/diff PASS；Chrome/frontend build/真实provider/正式发布 NOT RUN。所有RED和中途fixture FAIL保留于var/v67。

本轮真实模型请求0、GitHub/Tavily0，quota24/50与搜索最新6/1000不变；48账本/26Acceptance/9份v6.5证据/正式.env哈希保持，旧unknown不重派。仅owned隔离测试库写入，产品库0、无正式Worker/入口/RAG修改。root请求Sol6.1/high、两个独立worker请求Sol6.1/medium、review请求Sol6.1/high，实际解析均NOT OBSERVABLE；无Astra/Sol max/全局配置修改。普通本地提交后最终SHA动态报告。代码可局部revert；未来已有新格式Run时须保留两格式读取与保护，不改冻结manifest。OUTLINE_PROJECTION_PATCH_READY后STOP；下一最小动作须另行明确授权全新单一Agent5 synthetic收费代表，本轮不自动执行。以下为历史时点。

## 2026-10-04 v6.6离线outline审计：MULTIPLE_CAUSES_CONFIRMED，STOP

用户现在新增能做什么：可以据精确请求重建/组成表评审局部outline投影patch；本轮未新增真实Plan或改正式行为。[批准Goal](STUDYPLAN_V6_6_OUTLINE_OFFLINE_AUDIT_GOAL_2026-10-04.md)已精确归档，[118组件/Top20/15检查/预算/保护缺口/唯一patch建议](../reviews/2026-10-04-v6-6-outline-token-attribution.md)。起点3074432f4cff2b71507ea0460f75aa46d6fd56ee、feat/n1-resource-discovery、tracked clean；无reset/业务修改/付费/DB/网络。

当前生产normalize→generate_skeleton→scope wrapper→adapter capture重建messages578108chars（system2559/user575549）、httpx离线JSON816500bytes，SHA2564e38d9b03efd39f5d511497c21faac0d560e1e84b37d76043dafba794073cdb6；原wire未保留，不能声明与原wire逐字节对比PASS。Agent5 publication digest/v6.5 frozen保持；v6.5原209998input/4097output/length/failed从receipt重新读取。无可用本地DeepSeek tokenizer且禁止下载；沿用char/4估计144527，较实报少65471/31.18%，Fake直接payload repr143784另列，不把估计伪装精确token。

根因：6阶段蓝图裁剪正确（public61→6），但resources402175chars/57source/179审核目录项保留，其中45未选source267928chars、144未选sections；publication_evidence132909chars夹带14完整教学Markdown，含AI/Cloud/项目卡/RL/未选Recipes。没有179份下载教程正文或递归dump；197组>=80chars相同叶子额外44456JSONchars，6stage guide4756chars在pack/manifest各一份，Eval117chars六份。outline原样注入整pack/manifest且要求生成后被merge覆写的resources/extensions；实际截断正文未存，输出token组成不猜。

两候选原型只在ignored var：Option1冻结骨架4112chars/1028 estimatedtokens，同比减少99.29%；Option2加现有focus投影5634chars/1408.5，同比减少99.03%。对209998按字符比例校准1493.69/2046.55仅辅助，不是真实tokenizer。保留本地full Seed/frozen事实、6stage/6requiredkeys/18arrangements/35refs/13extensions/6首实践；该Common Core实际project-study/case-study0，其他场景optional语义另测。现有structure5481–6237chars仍局部、不转移全包；practice5403–5542chars明确结构fixture，非真实服务。outline4096、structure/repair8192不改。

最终Fake/contract PASS21/exit0（归因7+回填14）：精确accounting、scope过滤、未选全文隔离、sectionID唯一/重复审计、最小skeleton与恶意事实防护、stage-local输入不膨胀、travel/no-project/Voice/NodeCloud/AIexistingproject语义/hold/开放Recipe/Starter/user-project规则。诊断证实既有保护FAIL两类：唯一知识title/objectives可被structure改写并通过validator、scope/acceptance未回填；次级任务强制Starter/首实践冲突额外acceptance可存活。PASS测试发现FAIL能力，不宣布全保护绿；真实PG/catalog消费/Chrome/收费/tokenizer NOT RUN。首轮审计脚本错误/20PASS1FAIL保留，纠正后21PASS；未改生产掩盖。

唯一推荐下一patch：未来新提交manifest冻结outline格式marker；旧Run/旧fingerprint保留legacy；局部pure skeleton projection与outline专用system/shape，复用现有merge，不全局换prompt_version/新planner/API/迁移/模型阶段。不实施该patch，不自动续收费。模型quota24/50、搜索6/1000、本轮真实HTTP/模型/DB0，旧unknown不重派，env/Seed/ledger/历史evidence hash保持；UI/阶段规则不变。root请求Sol6.1/high、独立回填Sol6.1/medium，实际NOT OBSERVABLE，无Astra/全局配置。全产品STAGING_BLOCKED/NOT_READY、STOP；最终文档SHA交付时动态读取。以下为历史时点。

## 2026-10-04 v6.5单一收费代表：PAID_REPRESENTATIVE_FAIL，STOP

用户现在新增能做什么：未生成可用真实Plan，现有副本体验保持；新增实际证据证明DeepSeek网络/envelope可用，但当前Common Core outline在4096下截断，真实生成代表不通过。基线a2c9435785687ce7d908fd5b13b9980d542a7bca、feat/n1-resource-discovery、tracked clean；业务源码/正式.env/预算未改，无reset/push/merge。[批准Goal](STUDYPLAN_V6_5_PAID_REPRESENTATIVE_GOAL_2026-10-04.md)精确归档，[审计/用量/风险/回滚](../reviews/2026-10-04-v6-5-paid-representative.md)。

17项首费预检PASS：公网DNS119.188.175.46/123.125.246.121、原guard/真实binding、与产品trust_env=False相同的直接TLS1.3/证书链/hostname；proxy配置与旧账hash不变，正式脚本加载runtime8192、outline/practice4096、structure/repair8192，Agent5 publication digest与实际冻结6阶段manifest精确一致，normal13+repair2=15/94208输出。新Acceptance v65-agent5-synthetic-7a1040c10f15、新owned business studyplan_test_v65_business_b6a8ba0f与checkpoint studyplan_test_v65_checkpoint_6959d5a8；仅synthetic目标/默认偏好+公共审核包，原产品库不连接。两处验收脚本首轮检查FAIL（回执名称拼错/不存在plans表）已修正后检查PASS，非产品修复/非收费重跑，原失败保留。

唯一Run run_cecd033d2fed4a3190a77df32a3cb382，唯一outline正常请求1、repair0。真实HTTP200/envelope PASS，finish_reason=length/content12858chars；provider_output_truncated→Run failed/result_ref null，无第二Run/重发。实际input209998/output4097/total214095/cachehit0/cachemiss209998；requested max_tokens4096但provider报告4097，多1原样保留，不伪造严格cap，也不放宽预算。模型受控账23→24/50、失败计量、本轮unknown0；旧其他scope unknown1保留，搜索仍6/1000、新GitHub/Tavily0。

最终owned app-role+actor/project只读1Run/1failed attempt/unresolved0/0draft/0plan_revisions；请求/result/Acceptance journal及evidence完整，旧quota/journal逐字节hash不变，failed persistence PASS。成功outline FAIL；structure/practice/repair、真实内容保护、synthetic confirm、成功Plan PG消费与Chrome refresh/relogin均NOT RUN；终止后新请求0。无正式Worker/入口/原库/用户私有外发/RAG/推送；业务回归Fake/宽PG本批NOT RUN（无业务变动），ignored harness语法PASS。主协调路由请求Sol6.1/high、实际NOT OBSERVABLE，无子代理/Astra/全局变动。

PAID_REPRESENTATIVE_FAIL后STOP，不自动修业务/改cap或收费再验；全产品STAGING_BLOCKED/NOT_READY。新明确blocker真实outline截断；下一唯一最小动作另开有界离线审查outline输入209998的组成与最小受保护上下文/输出职责，不使用本次Acceptance重发。新owned库/受限本机证据保留，收费不可回滚、账本不可清零；本提交最终SHA交付时实际读取。以下为历史时点。

## 2026-10-04 v6.4网络门禁：PROVIDER_NETWORK_READY，整体NOT_READY，STOP

用户现在新增能做什么：正式配置加载链的DeepSeek网络解析/endpoint guard/部署binding与免费TLS均通过；本轮没有开放模型生成、正式入口或Worker。最新[v6.4 Goal](STUDYPLAN_V6_4_PROVIDER_NETWORK_GATE_2026-10-04.md)已执行至STOP，源码能力与v6.2内容继续保留，不扩实现。

基线0d65a1e、feat/n1-resource-discovery，tracked clean；OS/Python修前同为198.18.0.161、2001:2::9a，Meta TUN与core fake-IP运行证据确认B1 LOCAL_PROXY_FAKE_IP。dns_config.yaml里已有域名但GUI DNS覆写false，实际core没有filter；不是上游异常/hosts/容器差异。仅在当前订阅实际option.merge对应profiles/mxAo9JFl7Wm5.yaml追加dns.fake-ip-filter=[api.deepseek.com]，生成配置同一字段对应修正，本机实际production named pipe现有secret重载204；基本runtime全字段不变，未开控制端口/改SAFE_PATHS/提升权限。受限本机原配置备份与hash已保留。

修后OS/正式Python DNS为119.188.175.46、123.125.246.121，全部公网；真实guard/bind_submission PASS。HTTPX实际从Windows注册表发现127.0.0.1:7900代理，经同一路径CONNECT后TLS1.3与certifi证书链/hostname PASS；未发送provider HTTP/API key/chat/completion。14unsafe URL+14混合DNS拒绝PASS；endpoint/binding/budget/provider Mock unit PASS24，0FAIL/NOT RUN。正式链runtime8192、structure/repair8192与outline/practice4096不变，原.env/guard/hosts/GUI编辑DNS/profiles引用哈希不变；23/50账本和旧journal全部hash不变、unknown新增0、收费0。

没有业务/测试源码或依赖改变、没有产品库写入/migration/Seed、正式API/入口/Worker/付费/RAG。Goal精确归档、审计文档与progress更新；最终SHA提交后动态报告，不推送/合并，两禁目录不操作。[完整网络审计/证据/限制/rollback](../reviews/2026-10-04-v6-4-provider-dns-audit.md)。网络门禁READY与全产品STAGING_BLOCKED/NOT_READY分开；下一唯一最小动作另行审批既有收费代表方案，本轮不执行。以下DNS FAIL等为历史时点。

## 2026-10-04 staging单项配置修正：runtime8192与预算PASS，真实端点binding FAIL，仍STAGING_BLOCKED

用户现在新增能做什么：后续获批正式staging启动时实际读取8192，不再因8000阻塞structure/repair预算。唯一事实源D:\studyplan\.env的LLM_MAX_OUTPUT_TOKENS，单值8000→8192；其它行hash、其它runtime Settings摘要保持，provider/model/purpose预算/计量不变。基线3f302346、feat/n1-resource-discovery；没有业务/测试源码或启动脚本改动。

实际scripts/b3f1-dev.ps1加载语句AST在新隔离进程执行→get_settings/build_llm/bind_submission：runtime8192、structure8192/repair8192预算与隔离binding PASS，outline/practice4096不变；6阶段synthetic冻结manifest15请求/94208输出/repair2、超请求/超输出拒绝PASS。真实绑定FAIL：api.deepseek.com DNS非公网被现有安全policy拒绝，不绕过/改代理。隔离DNS的binding PASS明确与真实结果分开，不宣称正式API/Worker已重启。

现有受控50次账本23/50、所有request/result哈希不变；原reserve_request AST仅在临时合成目录执行第50允许/51拒绝、failed计量、unknown/缺失回执停止PASS。该50总额度是现有受控验收wrapper保护，普通API全局自动计数未集成/未验证；本次不扩大实现。正式Worker、费用仍STOP。原库snapshot/归档/函数保全只读复核PASS，收费/外部HTTP0，无旧unknown重派。

最小unit回归PASS65/NOT RUN2（symlink权限）；原PG budget PASS3/FAIL2为固定旧stage.tools/21的stale fixture；保留原FAIL、原测试不改，复制至ignored var的当前manifest隔离PG边界PASS5。backend/scripts/.env.example diff空；两禁目录保留。完整报告含证据/限制/单值rollback：[staging cap修正](../reviews/2026-10-04-staging-output-cap-correction.md)。本项完成后STOP；cap配置阻塞已解除，DNS/非空原账号历史/RAG/真实模型及完整用户接受仍待门禁，STAGING_BLOCKED/NOT_READY保持。不自动进入下一门禁。以下此前记录均为历史时点。

## 2026-10-04 RC最终STOP报告：原账号认证/空状态PASS，STAGING_BLOCKED / NOT_READY

用户现在新增能做什么：可继续在5179副本用原账号只读体验；本次本人反馈“一切正常”，已核实其登录/退出/重新登录及原有空状态，无需重复要求登录。尚未开放业务保存或正式入口。源/副本的用户提供账号tiance均1项目0Plan；只读新有效原actor聚合唯一对应该账号。排除自有合成Chrome第6–18行后login200两次/logout200两次/session200一次/workspace404三次；frontend404映射空状态，符合无正式Plan。认证与可执行空状态PASS；非空原账号Plan/Summary/Prompt/Practice/Outcome/资源/extensions消费NOT RUN，不能将全库12Plan或合成workspace200冒充本人验收。

本轮已到[v6.3第14节STOP报告点](STUDYPLAN_V6_3_RC_CLOSURE_GOAL_2026-10-04.md)，审计/备份恢复/副本forward三包/必要fixture修复/三包实际PG与Chrome/RAG状态/收费方案/体验清单均已报告；结束本轮RC执行，不自动进入产品操作。完整12步用户接受未完成，STAGING_BLOCKED/NOT_READY保持。正式cap8000<structure/repair8192为配置阻塞，候选8192离线PASS；非空原账号历史缺样本、RAG实例/契约和收费代表继续门禁。

本回合没有业务/测试代码改动；复用此前PASS840/NOT RUN2 unit、PASS59相邻PG、PASS10 Auth、PASS13 frontend/build与三包PG/Chrome，未重跑宽套件。新增认证/范围聚合及最终源snapshot/归档/原函数保全只读检查PASS；首轮误用系统Python缺psycopg检查FAIL，工程.venv重跑PASS，不安装依赖。服务仍同一5179/8024 PID33136/20012，Worker OFF、业务写403；原库及.env未改。模型/搜索新增0，历史23/50、6/1000、unknown1保留，无新外部私有正文或凭据读取。

本地实施/既有证据提交341b7b5、c703655；最终文档提交后实际HEAD动态报告，当前feat/n1-resource-discovery，无push/master/develop集成，两禁目录不处理。[完整证据/风险/回滚](../acceptance/v6-3-rc-closure-2026-10-04.md)。下一唯一最小门禁动作：批准正式staging配置修正8000→8192并验证绑定预算；不包含原库升级、入口切换、Worker或收费。

以下保留此前各时点记录，NOT RUN/等待状态不覆盖本节最新认证结果。

## 2026-10-04 RC续接：恢复副本三包实际生成/发布及Chrome补证PASS，原账号消费仍NOT RUN

用户现在新增能做什么：5179只读入口继续保留，正常账号可私下登录看已有历史；本回合没有开放业务保存或切正式入口。上一回合完成恢复/审计/commit为progress；本回合同一8024/5179进程与exec handle核实仍活跃，没有因超时重启。

在既有真实产品数据恢复副本中分别新建合成账号，普通Auth/CSRF、精确新actor allowlist/Fake有界tick、确认/PG工作区/新容器登录回读，Agent5/AI2/Cloud2三项PASS。实际阶段13/7/9，资料36/17/9、extensions29/21/25、tasks13/7/9。旧业务行摘要多重集合子集全部保留，旧Run/Job/Attempt/unknown不动；原库全表snapshot及archive/hash、原函数owner/security/ACL/definition只读复核PASS。

Agent另走真实Chrome5179→8024，无API Mock，章节/optional RAGFlow卡/纯Prompt/刷新/重登录精确Plan与Workspace PASS，生成POST0，已退出自有浏览器，PNG已看。此为真实数据恢复环境中的**新合成写路径**，不代替原账号历史消费。[完整增量证据](../acceptance/v6-3-rc-closure-2026-10-04.md)。合成登录的metadata第6–18行排除；原actor新会话聚合0、其后login200计数0，原账号consumer NOT RUN，仍需本人私下登录。

收费0，模型23/50、搜索6/1000、unknown1不变；Fake不是收费代表。本回合无tracked业务/测试代码变化，已有unit/contract/PG/Auth/前端结果输入不变复用，不重复宽套件。`.env.example`已正确8192，本机.env8000冲突仅待正式staging配置；不改原.env。RAG待用户指定实例；STAGING_BLOCKED/NOT_READY、Goal不标complete。下一最小动作仍为原正常账号在副本登录/历史/刷新重登录。

## 2026-10-04 最新：v6.1续接审计PASS，RC真实副本基础演练PASS，STAGING_BLOCKED / NOT_READY

用户现在新增能做什么：在 [5179只读副本](http://127.0.0.1:5179/) 用原正常账号登录，查看恢复的学习空间/路线/历史、刷新/重新登录；当前不开放生成/确认/保存。真实产品库未修改、正式日常入口未切换。当前源码三方向/纯Prompt/已有项目优先/Recipe/当前UI与自动阶段完成均复用，不重新开发已通过能力。

N0实际 `161bacd5fa3e88c566b806697ebe52ef34cb6456`、feat/n1-resource-discovery；固定cf153704祖先PASS。Downloads v6.1指定文件已不存在，读取仓库归档；[最新N0/P0差异审计](../reviews/2026-10-04-v6-1-resume-n0-p0-audit.md)。进入时三个RC测试文件已有修改，保留；两禁目录不处理、无reset/checkout/历史改写/remote push/develop/master集成。普通实施授权连续执行；当前 [RC Goal](STUDYPLAN_V6_3_RC_CLOSURE_GOAL_2026-10-04.md) 原产品/费用STOP不扩大。

RC-A [preflight](../reviews/2026-10-04-v6-3-formal-entry-preflight.md) SAFE_TO_STAGE（仅副本）。原日常前端/API/Worker当前停止；正常脚本默认5175/8022。源.env数据库0023、61表1517行、13user/18space、12plan revision/14publication、Summary/Prompt/Submission/Review0；已发布Agent1/Python1。源只读检查与原生snapshot backup、native restore到新owned studyplan_test_v63_realcopy_a798a903 PASS；全表计数/摘要、columns/ACL/RLS/policies/schema ACL一致。副本动态upgrade head0024 PASS，官方immutable导入AI2/Agent5/Cloud2 PASS；旧pack/所有私人表/history、源库最终snapshot保持PASS。App-role PG catalog/private manifest/guidance消费PASS，真实用户普通登录及历史页面回读NOT RUN；不能用账号存在/匿名页代替。副本5179/PID33136、8024/PID20012为本次快照，Worker OFF/外部key disabled/业务写403。

新配置blocker：`.env`部署output cap8000小于structure/repair8192，绑定预算gate FAIL、请求dispatch0；staging候选8192离线PASS，未改原.env。已明确写入 [staging/rollback方案](../reviews/2026-10-04-v6-3-staging-plan.md)。不拿基线相同免责，RC-C10个宽FAIL [分类](../reviews/2026-10-04-v6-3-baseline-failure-triage.md) A0/B6/C4/D0；六个B先RED6后修fixture/载体断言PASS7，相邻PG/HTTP/RLS59 PASS与最后singleton严格gate1 PASS；四个C根因0022→0021 policy依赖actor_id，原FAIL保留、不改published migration。正常forward-only/backup restore回滚，不伪造全宽绿。

本轮最终unit/contract PASS840、NOT RUN2（842总、symlink权限；39.34s）；新Auth/入口/普通用户ownedPG PASS10；frontend PASS13/build62 modules；匿名Chrome真实5179→8024→restoredPG smoke PASS，首轮旧health字段断言FAIL后只改检查脚本，非业务问题。Checkpoint相关代码未变、沿用v6.2 PASS4，本次NOT RUN。新迁移/API/DTO/Graph/依赖/产品功能 NO。源码只改三个stale测试文件，其余为文档/ignored本机证据。

RAG只读16次本机GET尝试，唯一在线18086，现有配置不能证明用户常用，NEEDS_USER_INSTANCE_SELECTION；没有pure retrieve/auth/caller tenant/citation/error timeout完整契约，[报告](../reviews/2026-10-04-v6-3-rag-contract-status.md)。[收费代表计划](../reviews/2026-10-04-v6-3-paid-representative-plan.md)：建议单独新synthetic库的Agent6阶段1Run、正常13请求/最大15（含repair2）、output94208，当前执行0，不自动批准用户草案。模型23/50、搜索6/1000、unknown1原账保留，不重置/重派；GitHub/Tavily公网新增0。Root请求Sol/high、有界fixtureSol/medium、RAG只读Luna/high，实际NOT OBSERVABLE；无Astra/max/全局设置。

已备 [用户12步体验清单](../acceptance/USER_ACCEPTANCE_CHECKLIST_2026-10-04.md)，由用户接受，不代执行。当前剩余最小动作是用户在副本私下登录/看旧历史/刷新重登录；后续正式cap/原库staging/收费代表/RAG合同分别有门禁。缺用户密码不伪会话、不重置hash；独立代码/资料工作已推进。当前STAGING_BLOCKED、整体NOT_READY；文档提交后真实HEAD动态读取，不猜SHA，不推送。

## 2026-10-04 最新：v6.2 内容门禁 READY，整体 NOT_READY

用户现在新增能做什么：三方向按已审章节生成、确认和回读；已有项目优先，Starter可替换；Agent 0..N专项组合，Voice缺口可见且不fatal，项目案例optional；修改目标与受控未来路线保留私人载体。六场景已走普通注册/Worker Fake/真实ownedPG/Chrome，原产品入口未部署。[完整验收、证据、风险和回滚](../acceptance/v6-2-semantic-content-2026-10-04.md)。

实施SHA `168d9b4d674ac65030831c4781f946074e101d78`（主体0109b23，末次carrier经验排除168d9b4）；内容63a77a9、消费修复933441f；分支feat/n1-resource-discovery。N0实际841ef9e及固定cf153704祖先PASS，无reset。23原文哈希/Goal复制PASS；AI2/Agent5/Cloud2为下一版本，87阶段/知识、86来源实例/71不同catalog scope与12独立root候选、294章节、4hold排除，不是研究86条全导入。Migration/DTO/API/Graph/依赖NO；产品0023只读未写，repo0024沿用。

最终unit/contract PASS840、NOT RUN2（Windows目录symlink权限）；六语义PG+Chrome/immutable旧Plan/hold/RLS/change_goal PASS9；未来新语义PG PASS1（Node exact keys/carrier、相同内容不制造新revision）；旧变更/取消/派发/history/闭环PG PASS61、NOT RUN6；显式Chrome闭环/history/cancel PASS6；checkpoint定向恢复PASS4；owned原生恢复PASS1（63表+ACL/RLS/policies、普通登录原文/成果/extensions、恢复模型调用0、两库清理）。Frontend13/Build62modules、Ruff/mypy8、diff/哈希PASS。重叠不累加，早期FAIL原样保留。

更宽Auth/RLS/旧schema组合当前与原基线同样PASS51/FAIL10，ignored只读基线快照复现，不能写全绿；四项published migration downgrade错误留整体风险，不改旧迁移。受保护首轮87项PASS77/FAIL8/NOT RUN2，旧夹具/连带setup与checkpoint时序失败保留，相关最终定向如上。TOC参考仍剥离refs提供fallback，未升级审读/候选/工程运行资格。attempt6/7精确owned库名未捕获，独立回查NOT RUN，fixture/API/worker/socket/context退出PASS；root临时Vite已结束。

真实付费模型/搜索/公网读取本轮0；模型23/50、搜索6/1000、unknown1与旧账不重置/重派。root请求Sol6.1/high、两有界Sol6.1/medium、只读Luna/high，实际解析NOT OBSERVABLE；Astra/max/全局配置不使用。无新远端SHA验证/推送、master/milestone。文档提交后的实际HEAD交付时动态读取，不冒充实施SHA。

下一安全动作：正式入口只读配置/发布版本核对及用户体验准备；独立RAG契约、受许可真实服务、私人产品数据恢复和用户接受仍待门禁。普通代码授权持续。以下保留N0及历史时点。

## 2026-10-04 最新：v6.2 N0 PASS、章节落地与语义薄适配实施中，整体 NOT_READY

用户现在新增能做什么：本轮目标是深审章节教学、用户项目优先与可组合Recipe；新界面尚未声明已验收。最新权威[v6.2 Goal](STUDYPLAN_V6_2_SEMANTIC_CONTENT_GOAL_2026-10-04.md)，输入ZIP及23份哈希证据已保存，审计本地提交 `1b5a98c`。[真实schema映射](../reviews/2026-10-04-v6-2-n0-schema-mapping.md)。

实际起点 `841ef9e31f0db70af238fa8c89796e3a5cf1c3e1`，分支 feat/n1-resource-discovery、跟踪clean、旧点祖先PASS，无reset。READ ONLY真实产品库0023、Agent1/Python1；Registry AI1/Agent4/Cloud1，下一合法AI2/Agent5/Cloud2。产品库未写入。优先现有JSONB、Guidance/resources/extensions/practice；不新增Migration/DTO/API/Graph/职业实体。

纯选择/载体薄适配定向RED→GREEN：用户项目、3Recipe、Starter可替换、Voice/open标签缺口、旧包兼容、前置闭包、模型重引Starter合并防护；发布资格7个真实RED后门禁GREEN。相关unit共PASS20，不累加重复。新三包、六条ownedPG/Chrome、完整受影响回归本批仍NOT RUN，不能用unit声明新服务已上线。内容/PGChrome两位writer独立文件，root公共契约/整合唯一负责人；原v6.1证据保留。

模型23/50、搜索6/1000、旧unknown及元数据账本不重置，本轮新增真实付费/外部搜索0。请求root Sol6.1/high、两个有界Sol6.1/medium、只读Luna/high；实际解析NOT OBSERVABLE，无Astra/max/全局设置。下一安全动作三新包受控校验、语义PG/Chrome与immutable旧计划回归；普通实施不重复询问。以下为历史时点。


## 2026-10-03 最新：v6.1 P1–P7 实施通过、P8回归收口，整体 NOT_READY

用户现在新增能做什么：代码支持 AI Fullstack/Agent/Cloud 最小路线，草案中可读教学与持续实践安排，正式学习阶段可查看项目重点/深度/比较问题并“复制给AI”。只认已发布Plan，静态课程生产入口隐藏。已在普通注册、Worker Fake、ownedPG与Chrome验证；原产品环境未部署。

业务本地SHA `8a05cae60153b4af6c7a830668053af3d6d8d3f2`，分支 feat/n1-resource-discovery，固定参考祖先PASS。Migration NO；Plan.extensions直接传递，不改DTO/API/worker/事务/自动阶段完成。旧专项、Python v2与Agent v3保留；新Agent v4/AI v1/Cloud v1为outline_checked/selected_scope_pending，详细内容深审按v6.1留后续。[详细证据与回滚](../acceptance/v6-1-directions-project-study-2026-10-03.md)。

验证：unit/contract PASS795、NOT RUN2；三代表目标+Seed真实PG/HTTP/Chrome PASS10；最新Chrome三目标PASS1；旧专项三目标Chrome PASS1；恢复PG最终PASS4，原受保护PG组合FAIL53中仅两夹具旧计数失败，其余49未受影响，不改写原命令结果。Frontend13/build62modules、Mock开发/生产卡片、Ruff/mypy/diff/Goal复制PASS。闭环新增两实践/无实践Chrome PASS1及Outcome UI+受影响主链PASS1。独立ownedPG原生custom备份恢复PASS1（v61-restore-opt-in-final.xml），63表与ACL/RLS/policies精确保留、普通登录原ID回读、恢复模型调用0、两个临时库清理PASS。真实服务/产品数据恢复/用户接受本批NOT RUN。重叠不累加，早期FAIL均保留。

模型23/50、搜索6/1000、unknown1及旧README2不重置；真实收费模型/Tavily/GitHub API本批0。13次免费公共网页open含3仓库根元数据，3/6已追加原GitHub账本，不深读/clone/执行源码。开发请求Sol high/medium、Luna high复核，实际解析NOT OBSERVABLE；无Astra/Sol max/全局设置。

未推送/核实新远端SHA，不接受milestone/master。文档提交后HEAD续接动态读取。下一安全动作内容范围深审与正式入口准备；owned恢复已完成，私人产品数据恢复不作已验收声明；缺外部RAG契约/真实费用许可只暂停相关支线，不删除需求。下文为历史时点。

## 2026-10-03 最新：v6.1 N0/P0 PASS，连续实施中，整体 NOT_READY

用户现在新增能做什么：本轮正在收口三个主方向与项目学习卡片，尚未声明新界面已通过验收。最新权威为 [v6.1 Goal](STUDYPLAN_V6_1_DEADLINE_GOAL_2026-10-03.md)，保留既有 RAG/Coding/Workflow 专项包和学习闭环。

只读基线 HEAD `6621b89df37d334bd01fd0566622e1d9903f8f3f`，分支 `feat/n1-resource-discovery`，固定参考祖先 PASS；跟踪文件 clean，禁操作目录不处理。repo migration head0024 PASS，本批不新增迁移/DTO/API，产品库本次 NOT RUN。PlanView 已有 extensions，采用前端直接 stage_id 过滤。[差异审计](../reviews/2026-10-03-v6-1-n0-p0-audit.md)记录单一注册表、审核事实丢失风险与静态课程入口漂移。

责任：root 单一整合 CURRENT_PACKS/Seed/确定性合并/资源保留及门禁；两个有界 worker 请求 Sol6.1/medium 分别拥有新三包+内容单元测试、前端纯 Prompt+项目卡片+静态预览降级，root 在两人业务编辑期间只做只读审计/文档，不写业务代码。实际 model/effort NOT OBSERVABLE；无 Astra/Sol max/全局设置操作。

已有证据复用：direction-unit-final PASS180、direction-pg-first PASS4；current-loop PASS3/browser-final PASS1，模型 Fake + ownedPG。上一方向浏览器最后 FAIL1（刷新/移动端阶段定位器超时），不能标通过。闭环两实践/无实践浏览器和 Outcome history UI NOT RUN，已有 PG PASS 不替代。新 v6.1 业务/PG/浏览器本次 NOT RUN。

模型产品23/50、搜索6/1000、unknown1及旧README2不重置；本批收费调用/产品搜索新增0。详细内容深审留后续内容生产，AI/Cloud允许入口索引核对与 selected_scope_pending，不伪造章节深审。保留真实外部接口、恢复演练、用户接受的独立门禁，整体 NOT_READY。下一安全动作连续 P1–P7，不重复普通代码授权。

## 2026-10-03 最新：普通规划取消与审查输入，整体NOT_READY

用户现在新增能做什么：排队/运行中规划可显式取消；503保留原请求、刷新不自动提交；取消后可明确创建新运行，可能已派发则待核对并阻止再生成。真实正常登录/HTTP/Worker/ownedPG/Chrome验证运行中取消、刷新/重登录和零重派，模型Fake；原产品环境未部署。

本地代码SHA `8c1595d24bb9d7f06387fdd6a498c0011da6d314`，分支 `feat/n1-resource-discovery`。[证据与回滚](../acceptance/planning-cancellation-2026-10-03.md)。规则/契约PASS67，相关ownedPG/HTTP/租约/短生成PASS81，最新审查fixture+取消HTTP PASS5/NOT RUN1，独立真实Chrome PASS1，Fake取消/scope/recovery/progress与Frontend11/build PASS；Ruff/mypy/diff/凭据模式/原文hash PASS。早期FAIL及修复保留，重叠不合计。真实外部与完整闭环NOT RUN。

取消、派发和待确认草案共享事务锁；token失效、幂等回执与状态原子，Attempt/原文不删除、不重派unknown。发布先完成的真实竞态曾误记生成失败，已在锁内核对本Run的已确认publication后修复。无新migration/依赖/平台；product0023未写、repo0024沿用。临时API/Worker与owned库清理；Vite5178自有session84785/PID57788，PG5432不变。新SHA未推送/核实远端，不no-ff/master/milestone。

用户转交[闭环审查](../reviews/2026-10-03-learning-loop-audit.md)与[三个Blueprint候选](../reviews/2026-10-03-blueprint-candidates.md)已保存。失效注册密码及硬编码迁移head的测试真实RED后修复PASS；旧总结Acceptance脚本保留不重跑。三个候选待新JSON/免费教材证据及导入，不能标正式课程；当前阶段总结、全部实践门槛、自动刷新、历史与隔离的E1–E5整链仍NOT RUN，后续实施不重复大规划。

模型23/50、搜索6/1000、unknown1、旧README2不变，本批外部新增0。请求Sol/xhigh派发难题、Sol/medium UI，实际解析NOT OBSERVABLE；最新Luna所有档位、Sol难题xhigh授权保留，Sol/max/6Astra停用，快速模式请求已结束且无工具切换证据。

下一安全动作：三个候选内容落成与免费正文审核、当前普通账号阶段总结/成果/自动完成的真实PG浏览器闭环；真实模型代表路径按授权门禁，额外GitHub1次仍等待此前选择，RAG缺契约不阻塞独立工作。备份恢复及用户接受继续为门禁。下文保留历史时点。

## 2026-10-03 最新：Luna自由档位与Sol难题升级，整体NOT_READY

用户现在新增能做什么：后续开发保留原风险路由，同时允许 Luna 所有实际可用档位自由使用，有证据的难题使用 Sol 6.1/xhigh。普通有界实现 Sol/medium、主协调 Sol/high；Sol/max 与6Astra不使用。快速服务模式请求仍已结束，实际模型/服务模式解析不可核实时记 NOT OBSERVABLE，不修改全局配置或产品费用授权。当前取消链路仍在实施，不因路由调整宣称完成；既有成果与门禁保留。

## 2026-10-03 最新：恢复原开发路由，整体NOT_READY

用户现在新增能做什么：用户明确“恢复原计划”，后续开发默认按原动态路由执行，不再沿用临时自由档位授权。主协调/HARD Sol/high、有界实现/NORMAL Sol/medium、低风险/FAST Luna/max；6Astra 继续停用。快速模式临时请求结束，当前没有主会话模型/服务模式切换接口，实际解析 NOT OBSERVABLE，不能声称已切换到标准服务模式。当前无活动子代理，不创建静态角色或修改全局配置。

本次只同步 AGENTS、ADR-0014、ADR-0015 与忽略的续接检查点。恢复前本地 HEAD `4db279d72cda1e001c2558a2b0342e7312130c1b`，仍在 `feat/n1-resource-discovery`，固定点祖先 PASS；既有代码与测试证据不变。文档 diff/恢复记录一致性检查 PASS；业务、真实PG、浏览器和外部服务本次 NOT RUN。外部请求新增0，模型23/50、搜索6/1000、unknown1、旧README2不变。没有新远端SHA验证。

交付Goal与当前分支例外继续有效，不回退、不从master重做。下一安全动作仍为常态Worker取消的派发claim fence、取消/派发锁顺序、已保存草案与发布窗口的真实PG验证。三个正式Blueprint、真实服务完整链、完整E2E/备份恢复与用户接受门禁保留。

## 2026-10-03 最新：服务端运行查找与只读恢复，整体NOT_READY

用户现在新增能做什么：学习规划页可显式读取本账号/项目最近20条规划运行，在本地编号丢失时选择恢复正常草案或待核对运行；刷新沿用所选编号、不生成POST。活动/unknown/旧waiting/未确认草案不能经另一历史条目绕过。已在正常登录、真实HTTP/Worker/隔离PG/Chrome验证，模型Fake；原产品库未部署，尚非正式入口已上线声明。

代码SHA `7ac7cf7086b1e8b2fd25b9cbe879a1ee943c663a`，分支`feat/n1-resource-discovery`，固定点祖先PASS；本地提交、未推送/核实新远端SHA。[本批证据](../acceptance/server-run-history-2026-10-03.md)。契约PASS31、真实PG/HTTP模型Fake PASS2、旧unknown生成PG PASS1、旧普通HTTP/PG PASS4；最终正常Chrome/HTTP/Worker/PG模型Fake PASS2；Frontend11有效复用、最终build及scope/history/generated/recovery/progress Fake Chrome PASS。Ruff/mypy/diff/18文件凭据模式、文档链接与原文hash PASS。重叠数量不相加；早期FAIL、环境/定位器问题与修复保留。

只读GET列表精确服务端actor/project/kind、默认10/最多20，不暴露thread/manifest/私人正文；所选GET单独读取业务进度，详情新增actor匹配。审查后实际组件harness先观察旧scope详情覆盖FAIL再修复：scope/请求序号/卸载保护，旧异步错误与busy隔离；结果仍在回读或503失败时继续阻止新生成、手动GET可恢复。无迁移/依赖/新调度平台。

用户停止6Astra持续生效，仅复用请求Luna/high的UI及只读代理，实际解析NOT OBSERVABLE；快速服务模式无可核实切换，不改全局配置。累计产品模型23/50、搜索6/1000、unknown1、旧README2；本批真实模型/Tavily/GitHub新增0，旧账/unknown不动。临时API/Worker与owned库结束清理，原PG5432/Vite5178不变。

下一安全动作继续常态Worker取消：派发事务接入服务端claim fence，与取消共用锁；处理已派发/未知、迟到结果以及已保存草案/发布窗口，经真实PG barrier门禁后开放UI。当前取消尚未实现，不假标完成。额外GitHub1次搜索仍等待此前额度选择，只暂停该支线；三个正式Blueprint/免费正文、真实provider/GitHub完整链、完整E2E/备份恢复/用户接受仍待完成，10月3日不批量扩内容。普通revert可退回本批接口/UI并保留数据/账本，注意已有路线payload读取兼容；不no-ff/master/milestone。下文为此前时点。

## 2026-10-03 最新：受控主题追加与公开GitHub DNS，整体NOT_READY

用户现在新增能做什么：可勾选同一已发布课程尚未覆盖的主题，补齐父/前置及同阶段内容，经完整差异/明确确认创建新路线；旧阶段与历史保留、刷新/重登录读回、新版完成不继承。正式Seed目前全覆盖，页面如实显示无候选；不是自由主题或跨模板语义合并。原产品库未部署。

本地代码SHA `1a8b3f69820bdb3b763232a071b8c40bd1cee4c4`，分支`feat/n1-resource-discovery`，固定点祖先PASS；未推送/核实新远端SHA。[本批证据](../acceptance/add-topic-and-github-dns-2026-10-03.md)。较宽规则/contract PASS705、2skipped NOT RUN；最终定向PASS77；真实PG/HTTP/Worker模型Fake PASS7；最终PG标题+两个真实Chrome PASS3；Frontend11/build/两个Fake Chrome、Ruff/mypy/diff/凭据与原文hash PASS。早期FAIL与fixture ERROR修复保留，重复数量不相加。

DNS已由用户配置，返回公网20.205.243.168；新增两次真实公开搜索均HTTP200，第二次5候选含指定教程。完整GitHub浏览器链FAIL（首查询空、第二次测试错误要求目标排第一）；修正为显式选择目标，README/章节/私人映射真实链本次NOT RUN。首批3次搜索已用完（旧unknown1+本次2），追加1次请求待用户选择；不重置/重派。模型23/50、搜索6/1000、unknown1，新增模型/Tavily/内容/metadata0，旧README2不动。

无migration/依赖/全局配置变化。临时服务关闭、owned库清理，PG5432/Vite5178沿用，原产品库未写。用户最新停止6Astra；后续只选授权Luna/Sol，实际解析仍NOT OBSERVABLE，快速服务模式未声称已切换。

下一安全动作：常态Worker取消和服务端运行查找/恢复；额外公开请求仅等待相关支线。三正式Blueprint/免费正文审核、真实模型、完整学习闭环、备份恢复与用户接受继续是门禁；10月3日不批量扩内容，10月5日结束Freeze。当前可普通revert代码保持历史；未来有新payload时回退前须保留读取兼容。不no-ff/master/milestone，不虚报READY。下文是此前时点。

## 2026-10-03 最新：有限生成路线变更与恢复，整体NOT_READY

用户现在新增能做什么：规划页可修改目标或重新生成受控未来路线，共用现有Worker和持久运行恢复；原目标/完整阶段内容与新草案对照，保留已开始前缀，经明确确认创建新版本。未知/旧待确认运行阻止新生成、不自动重派；202后首GET失败保留新编号并支持手动读取。当前库体验未切换到新代码/模板。

本地代码SHA `a616838c327ab724916be59618bcc0e3d68acaa4`，分支 `feat/n1-resource-discovery`，固定参考点祖先关系沿用；未推送/核实远端新SHA。[本批证据](../acceptance/generated-route-and-recovery-2026-10-03.md)。规则/契约PASS688，2skipped NOT RUN；新规则+真实PG/HTTP/Worker、模型Fake PASS33；定向目标/隐私PG PASS1；手动有限/短生成断点恢复PG PASS25；正常Chrome真HTTP/Worker/ownedPG、模型Fake PASS1；Frontend11/build/4个Fake Chrome PASS；Ruff/mypy/diff/25文件密钥模式/原文哈希PASS。早期FAIL与修复留在证据，不合计重复测试数量。

复用原有完整有界生成器而非另一套planner；当前会生成完整固定课程再丢弃保留阶段候选，尚未优化为仅派发未来批次。server保存冻结basis/hash/身份/精确知识ID与版本，模型看不到旧私有资料或历史原文。普通草案写入防绕过，确认/取消及回执原子，旧历史保留、新版不继承完成状态。无迁移/依赖/全局配置变化；原产品库未写入、隔离PG结束清理，验收API/Worker已停，Vite5178当前可读、PG5432不变。

外部请求新增0，账本模型23/50、搜索4/1000（unknown1）保留。开发参数请求Sol/medium及Luna/high，实际解析NOT OBSERVABLE；快速服务模式无可核实切换工具，未声称切换。最多2业务写者，共享契约/事务主协调整合。

下一安全动作：受控add_topic、常态Worker恢复。移除仍为明确optional阶段粒度；三正式Blueprint/免费正文审核、真实provider/GitHub、最终E2E/备份恢复/用户接受仍待完成。DNS按用户最新决定未配置，真正需要公开GitHub验证时才提示。10月3日不批量扩内容；不no-ff/master/milestone，不重置旧账或unknown。

## 2026-10-03 最新：有限未来路线调整，整体NOT_READY

用户现在新增能做什么：规划页可预览调整未来阶段顺序或移除明确optional的未来阶段，再确认创建新路线；刷新和正常账号重登录读回。已开始前缀与最终综合实践保护，必需闭包/前置顺序校验；旧路线、学习/总结/Prompt/成果历史保留，私人资料沿用来源lineage。正式Seed无optional阶段，因此不猜可选；当前移除为阶段粒度，全部七种操作尚未完成。原产品库未部署。

本地代码SHA `736f0ba5dd202ffbd413e7894a6fb68b54451476`，分支 `feat/n1-resource-discovery`，固定点祖先PASS，新SHA未推送/核实远端。[本批证据](../acceptance/finite-route-changes-2026-10-03.md)、[ADR-0015](../adr/ADR-0015-learning-orchestration-deadline.md)。规则最终PASS10；unit/contract PASS658，2 skipped NOT RUN；资源/实践/指导/有限真实PG PASS58；正常Chrome+HTTP+PG PASS1；Frontend11/build/Fake Chrome PASS，Ruff/mypy/diff/原文/秘密模式PASS。早期FAIL及修复记录保留，数量不相加。

无新migration/依赖，原产品库0023只读、仓库0024，测试仅owned隔离PG并清理，临时API已停，Vite5178自有。新增外部请求0，模型23/50、搜索4/1000（unknown1），旧账/unknown不动。Sol/high UI代理capacity错误后复用部分成果改派Luna/high；只读审查Luna/high；实际解析NOT OBSERVABLE。快速模式没有工具切换证据，未声称切换/未改全局配置。

下一安全动作：其余有限生成操作与常态Worker恢复UX；三正式Blueprint/免费章节审核、真实provider/GitHub、完整E2E/备份恢复/用户接受仍为门禁。按最新用户决定GitHub DNS未配置，真正需要时才提示；缺RAG支线不阻塞独立工作。10月3日不批量扩内容，10月5日结束Freeze。普通revert保留历史/账本，不no-ff/master/milestone。下文为此前时点。

## 2026-10-03 最新：显式目标与依赖/用途增量，整体NOT_READY

用户现在新增能做什么：生成前可明确补充范围、深度、自述起点、成果用途、限制；草案快照经确认/刷新/重登录仍保留。必要模块沿parent/prerequisite递归闭包展开；阅读/实践前置可在指导展示；收尾实践按用途增加少量验收要求，更改任务后仍与新指导一致。旧请求、旧hash、阶段总结、自动完成规则保留。仅在合成账号/Fake模型/真实隔离PG/Chrome核对，未向原产品库部署。

代码SHA `9b1a3ada60af22c0793c72c169eed3ac5a702a7d`，分支 `feat/n1-resource-discovery`，无新迁移。新SHA为本地，未核实远端。详细[目标与前置证据](../acceptance/planning-intent-and-prerequisites-2026-10-03.md)，[ADR-0015](../adr/ADR-0015-learning-orchestration-deadline.md)。较宽unit/contract PASS649，2 skipped NOT RUN；PG/恢复/资源/实践/Chrome PASS68；最新目标/指导/契约/PG PASS46；独立复核用途任务编辑丢要求P1实际RED后修复，定向PASS2、最终实践/HTTP PG PASS35；最终规则/provider PASS21。范围重叠不相加。Frontend11/build/Fake浏览器PASS；短生成重载夹具等待DOM后PASS。真实模型/公开GitHub NOT RUN。

产品模型23/50、搜索4/1000（unknown1）不变，本次外部请求0；旧账/unknown不动。原产品库0023只读，仓库0024；本批JSONB字段无需迁移。原8022/5175、8024/5177停，临时验收API已停、Vite5178自有，无旧Worker重派。快速服务模式无工具开关，未声称切换；临时模型授权继续，代理请求Luna/high、Sol/high，实际解析NOT OBSERVABLE。

scope目前仅生成条件、尚不裁剪完整模板。思想全文路径、三正式Blueprint/免费正文和章节审核、有限重规划、真实服务、恢复/完整闭环/备份恢复与用户接受仍是门禁。下一安全动作有限全路线重规划与恢复；10月3日不批量扩内容，GitHub实际需要时再提示DNS配置。普通revert保留历史/账本，不N1 no-ff/master/milestone，不因支线缺配置停止独立开发。下文为此前时点。

## 2026-10-03 当前：P0–P4学习编排增量，整体NOT_READY

用户现在新增能做什么：新阶段可显示why/前次关系/重点/对比问题/贯穿实践增量/可选源码建议；普通编辑、发布、刷新和重登录保留。受控模板可以复用精确知识键，独立保存两次学习目的和Exposure；修改实践或Primary会更新新版本指导，旧历史继续可读。已用合成账号、Fake模型、真实隔离PG和Chrome核对；原产品库未部署此增量。

最新权威入口为[10月6日最终交付Goal](STUDYPLAN_OCT6_FINAL_DELIVERY_GOAL_2026-10-03.md)及[ADR-0015](../adr/ADR-0015-learning-orchestration-deadline.md)。代码SHA `506048164261be06a166c5c9b8be4b6a556b4301`，分支 `feat/n1-resource-discovery`，参考点祖先PASS；复用N1未提交成果与用户UI，不回退。SHA为本地，未核实远端。下一文档提交须读取实际HEAD；不猜自指SHA。

Tests：最新unit/contract PASS644，2 skipped记NOT RUN；真实PG+生成恢复+Chrome组合PASS20（模型Fake）。Frontend11/build/Fake浏览器PASS；原较宽PG组合FAIL保留，三个失败项修后定向PASS、fixtureERROR修后HTTP/PG PASS。不是测试数量推算交付比例。详细[证据报告](../acceptance/P0-P4-learning-orchestration-2026-10-03.md)，忽略证据目录 `var/oct6-guidance/`。

额度：模型23/50、搜索4/1000，unknown1；旧README读取2次。本次新增外部模型/搜索/内容/元数据均0。旧unknown不重派。用户最新纠正api.github.com的fake-ip-filter尚未配置，真实GitHub验证NOT RUN；等实际需要时再提供操作。快速模式为用户偏好，但工具没有service mode切换接口，未声称已切换、未改全局配置；代理请求Luna/high、Sol/high，实际解析NOT OBSERVABLE。

迁移仓库0024（本批N1增量），原产品库只读核对0023；本次指导新增迁移0。只在自有测试库迁移/写入并清理。原8022/5175、8024/5177已停；Vite5178自有，临时PG浏览器API已停，无旧Worker/unknown恢复。不得把产品库0023描述为可使用新N1入口。

剩余门禁：规划思想全文路径、三个正式Blueprint与免费正文/章节审核、purpose/有限全路线重规划、真实模型/公开GitHub链、完整浏览器闭环、正常Worker恢复UX、备份恢复和用户接受。10月3日不批量扩内容；10月5日结束Feature Freeze。缺RAG契约只暂停支线。下一安全动作：继续目标解析与required closure、教材/实践前置提示的最小接入，不重复已有效的大型验证。正常revert可回滚代码并保留历史/计量；不破坏性降级、不N1集成、不master/milestone接受。下文保留各历史时点，旧“服务保留/unknown0/等待指令”不代表当前。

## 2026-10-02 续接：N0 PASS，N1a/N1b实施中

用户现在新增能做什么：本批正在实现独立 GitHub 来源和教程检查，尚未宣称产品入口可用。用户已给出续接实施授权，下文“等待新指令”仅为旧交接状态。

执行依据为[续接计划](STUDYPLAN_CONTINUATION_PLAN_2026-10-02.md)、[新 Goal](STUDYPLAN_CONTINUATION_GOAL_2026-10-02.md)及[ADR-0014](../adr/ADR-0014-continuation-slices.md)。N0 固定点与实际 HEAD 均为 `cf1537040bbf8c52469e00461723f70726f5a3b2`，祖先检查 PASS；只有禁操作目录未跟踪。原文保存与入口提交 `3f31b18`，切片分支 `feat/n1-resource-discovery`，原父线保留。迁移原 head0023，本批分配0024，不改已发布迁移。

额度按本机追加账重新计数：模型23/50，搜索3/1000，旧README读取2次；本批模型/Tavily/GitHub新增0。搜索旧回执字段版本不同，按原证据逐项核对，不把缺字段当成功或重发依据。PG安全测试入口只读预检 PASS，既有角色符合要求，无全局角色操作。现有正常8022/5175和只读8024/5177入口均保留。

责任：主协调整合DTO/OpenAPI、0024和事务约束；后端子代理请求 `gpt-6.1-sol/xhigh`，前端 `gpt-6.1-sol/high`，只读契约审查 `gpt-6-astra/high`。工具不提供实际解析值，均记录 NOT OBSERVABLE，不声称已切换；最多两名业务写入者，两个代理写入时主协调不写业务代码。共享证据包位于忽略目录 `var/n1/evidence-packet.md`。

测试：基线/祖先/PG安全预检 PASS；新切片真实GitHub、PG链和浏览器 NOT RUN。整体 NOT_READY。下一安全动作：完成有界发现、独立检查与来源快照，再用新合成账号/新AcceptanceId完成写入模式HTTP+PG+浏览器；第一批外部上限3搜索/9内容/6元数据，收费模型及Tavily新增0。回滚可关闭GitHub入口；已产生数据保留，非空历史拒绝迁移降级。

2026-10-02规划交接：用户要求上传当前项目，并把后续方向交给ChatGPT-6-pro规划后再返回执行指令。本轮仅整理[规划交接包](CHATGPT_6_PRO_HANDOFF_2026-10-02.md)、核对与推送当前工作分支；不开展新业务切片，不接受里程碑。原完整Goal仍未达成、整体NOT_READY；后续业务实施等待用户新指令。具体远端SHA以本轮实际push/ls-remote核对结果为准。

最新补充（2026-10-02）：沿用用户已提交的第4版测试课程/学习前端，当前本地HEAD `3d8ba67`。资料要求改为教程教学性优先、官方细节补充；GitHub匿名真实公开搜索1次及两个README读取PASS，产品专用适配/MCP/OAuth仍未实现，不能用预检替代F08完整验收。当前累计模型23/50、搜索3/1000（Tavily2+GitHub1）、unknown0。详见[GitHub公开教程发现预检](../acceptance/github-public-search-preflight-2026-10-02.md)；下文保留各时间点原始状态。

日期：2026-10-01。整体 **NOT_READY**；目标仍为F01–F18、G0–G6、Q01–Q12和用户实际验收。G1技术纵向链与G2搜索、学习控件、受控主线替换已实测；当前进入G3总结保存、反馈和修订历史，GitHub授权及RAG局部缺口继续保留。

## 基线与归属

正式目录D:\studyplan；origin=tiance002/studyplan-v1。起点develop为aa37e4bfa33a41aadb4cb689557e2c7d491d550f；工作分支feat/v2-g1-user-slice。V2入口54c7d3e及G1代码be802e27dfa131ee232d07d40d9650dbd9d5ac21/验收6713c18已推送。G2资源代码237d8c3f385de04f432eeaeca37c3269af0e6f64及验收73e9f8466660d98a8286be056aad47301dd2d4b2也已推送。G2学习控件代码9c1d85abf8987c4434af1ba10fa944e20428f2fd已正常推送并ls-remote核对相等；本报告后的文档提交需续接时读取实际HEAD，不猜SHA。本轮业务编辑均停止；下一轮先核对实际HEAD/状态，不重做已有效验收。既有.workbuddy/和design-preview/禁止操作/提交。develop/master不变，未接受milestone。

原后端8000、PG5432、Ollama11434未重启。原业务库迁移0010，13账号/18项目/26Run，盘点只读；旧waiting_user、unknown、Acceptance09及live journal未处理。原文哈希保持：指导7531B8DA74B043D169E8AE6DFEB1BB738747A0BE936E15B1934C53416D974F35，Goal D4DBCF0FD8F72CDE53385C307F1CCED02F81DC9D7E4449A1A17C4731A350E13B。文件专属whitespace规则保留CRLF及Markdown双空格，不改原文。

## 路由与外部条件

root实际turn_context为gpt-6.1-sol/high。此前仅根据工具返回将子代理实际解析记为NOT OBSERVABLE；用户追问模型显示后补查本机JSONL的session_meta父线程/agent_path与最新turn_context，已获得运行证据：Gauss/g1_credentials为gpt-6.1-sol/medium，Kuhn/g1_short_generation为gpt-6.1-sol/high，Helmholtz/g1_seed为gpt-6.1-sol/medium，Lovelace/g1_binding_review为gpt-6.1-sol/high。这些既有代理没有使用Luna Max；复用工具followup_task/send_message没有model/effort参数，本轮新增代理又被agent thread limit拒绝。不能把提示词或失败spawn当路由证据，未改全局配置。之后派发说明同时展示任务、日志核实模型/effort和复用/新建状态；低风险可新建时明确路由Luna Max，工具限制时报告限制，不把Sol标为Luna。原始实现者报告保留其当时可观测判断，以本条补充审计为准。

用户授权累计模型50请求、Tavily1000请求：**模型23/50，搜索2/1000（2credit）**，下一切片不重置。23模型及2实际搜索均有结果/回执，外部unknown0。G3总结1次，Prompt已知HTTP400失败1次及新成功1次；失败不退还请求额度，usage缺失不猜费用。Tavily三项配置已存在，预检和G2实际API/PG/Chrome成功。RAG地址/契约/凭证缺失，只阻塞其实际调用；公网部署未授权。GitHub浏览器授权需求已记录，尚未注册App或安装MCP；手动GitHub资料不是账号连接。见[外部服务](external-services.md)。

模型沿用DeepSeek Flash/cap8000，专用验收structure/repair目标8000，不提升cap、不改私有.env。免费预检先因缺dotenv和预算不一致FAIL；复用加载语义、限制目标后PASS。派发前append-only计量：.git/v2-paid-quota-20261001/request-01..23.json及result；搜索.git/v2-search-quota-20261001/request-0001..0002.json及result。未知结果阻断继续，禁止修改记录或重跑同AcceptanceId。产品计数器按单部署DB，验收跨库仍由.git计量承接旧消费。

## G1已实测事实

用户可注册/登录、使用DB发布的Agent v2 Seed提交202任务，真实模型生成9阶段草案后计算结束，编辑保存、业务发布再重登录读回。完整项目管理、三Blueprint和学习闭环仍未完成。见[G1报告](../acceptance/G1-v2-user-slice-2026-10-01.md)。

- 新密码15–128 Unicode码点及旧密码兼容；真实隔离PG认证7项PASS。部署模型冻结/轮换拒绝3单元PASS。
- Seed预SQL校验、0011完整payload发布/DB只读目录、重复幂等/异体回滚：16规则+PG PASS，bootstrap选择1 PASS。保留v1章节原文，新增v2修正，不冒充新内容审核。
- 0012窄原子worker领取，保留scope/RLS/unknown排除；锁后时间/token/owner检查，新旧job47实际PG PASS。
- short-v2保存草案后END，succeeded+none/result_ref稳定；确认不resume旧Graph。同事务catalog/draft/Run fence、锁后expiry、基础版本、并发发布、崩溃复用已存草案定向实测。较宽命令FAIL：112通过/1旧异常类型失败；修复后原失败及相关4项PASS，不冒称全组合重跑。
- 父级真实PG业务纵向1 PASS（provider明确Fake）；最终离线unit+contract 453 PASS/2 skipped（NOT RUN），exit0；Ruff/diff/OpenAPI PASS。
- frontend 4单元及build PASS；auth/progress/short-generation mock浏览器PASS，覆盖终态停止轮询、opaque ID和刷新/409保留编辑。
- 真实AcceptanceId v2-g1-20261001-01，Project lpr_3b0829d7c2ce490798db5b300ae87d0a，Run run_5abb9605a32b40e3ba243fe2cda8e279：20云模型请求含1repair，27/27必需节点、9阶段、succeeded。
- Chrome+真实HTTP+PG编辑/保存/发布revision1/退出重登录PASS，模型仍20。第一次FAIL在已发布后的退出按钮accessible name，补aria-label；第二次FAIL为测试提前断言，改等实际草案标题，从保留发布结果续测PASS，无再生成/付费。只批准新隔离测试账号自己的草案，负责人体验NOT RUN。

## G2第一批

真实搜索→5个未核验候选→用户选取→私有单元绑定/快照→刷新PG回读PASS；手动GitHub URL保存/回读PASS，但不是GitHub账号授权。0013预算全局串行预约及单调计数，最高1000/0禁用；同键缓存、异体冲突、未知不重派。当前版本共享plan-decision锁，等待发布后重读approved；私有resource_records和完整plan/stage/unit绑定同事务，移除保留历史。

规则/契约/PG组合89 PASS exit0（50adapter、31契约、8PG）；新增0预算/非法Unicode及最终手动公开DNS/异常脱敏定向4 PASS，5 deselected，exit0。frontend build/4单元/mock资源浏览器PASS，实际Chrome+Tavily+HTTP+PG PASS（5候选，刷新后两份选择保留，GET原查询无新派发）。Ruff/diff PASS。明确区分命令范围，不重复无变更昂贵检查。

独立review P2发布竞争已阶段内修复，回归先FAIL再PASS。第一次真实浏览器FAIL为本机验收wrapper以GBK读取UTF-8 journal，在外部HTTP派发前失败；修复脚本保留原预约，以显式新请求完成真实链路，模型未调用。新AcceptanceId v2-g2-20261001-01/request_id 6cbd7349-21f3-43a4-91a5-aaf32207d55c，HTTP200/1credit。详见[G2资源报告](../acceptance/G2-resources-2026-10-01.md)。

## 服务、证据与下一步

本轮保留专用库studyplan_test_v2g1real_2f6ac462（已到0015）及checkpoint库studyplan_test_v2g1cp_e6270f82，无额外worker运行。旧96940后端及36922/PID28096已按归属关闭；当前会话30734后端8021/PID11360为var/v2-g2/controls_acceptance_server.py，新本地Acceptance02且含跨库计量wrapper；45314前端5175/PID41308，24837前端5174/PID49752为mock测试。续接先确认监听/归属，只操作本轮进程，不承诺跨会话后台持续。原8000服务未操作。

忽略目录var/v2-g1与var/v2-g2包含代理report、短生成日志、真实report/browser JSON、PNG、Tavily预检/新回执和有计量的专用server脚本。*-browser-private.json有测试账号秘密，禁止打印/提交。保留收费证据和专用库，复用未失效检查。

本批已实现并核对G2 Exposure独立出现位置/进度/跳过/返回/历史及局部偏好。复用plan_unit_links、KnowledgeNode稳定键及既有四态规则，不把单元完成当模块掌握，不污染旧计划版本。GitHub账号OAuth尚需维护者App配置，RAG缺契约仅暂停对应真实调用。本批新增外部调用0，累计仍20/50、2/1000。业务代理已停止编辑；整体Goal仍active。

## G2第二批执行边界与证据

Goal：每个project/plan/stage/unit位置有独立Exposure；四态变化、跳过与返回记录不可变历史；project/unit/node偏好按最具体完整设置解析，恢复继承保留CAS版本。GET不写学习记录，资料绑定与自述完成均不是核验掌握证据。

Constraints/Non-goals：不改旧unit_progress、历史Run/Draft/checkpoint或原服务/数据库；不外发内容，不新增收费验证；不建设通用MCP Runtime或自动批准。当前选择来源在每次进度操作时保存快照，之前事件保持原快照；不声称用户已阅读该资料。写入统一先取plan-decision锁，再锁project owner行，最后重查approved和成员归属。只读审查确认真实生成materialize/save_draft也是advisory→job/run/project；root之前project-first判断错误，已撤回，资源既有反向顺序列为本批P1修复并补回归。

Allowed changes/Ownership：SolHigh实现Exposure领域/Port/应用/DB/API/测试及0014，并修复资源adapter锁顺序和针对回归；SolMedium实现偏好Port/应用/DB/API/测试及0015偏好tombstone迁移；root拥有组合根/容器/工作区投影/生成偏好冻结/共享契约和前端整合。最多两名业务写入者，两个后端代理编辑时root只读源码及维护本检查点。代理实际模型解析仍NOT OBSERVABLE。

Tests/Evidence：最终受影响后端组合139项PASS，exit0，78.73s，覆盖规则/契约/隔离PG/真实generation fence竞争/HTTP/原G1纵向回归。偏好worker23 PASS；Exposure worker组合FAIL(30通过/1夹具未建旧记录)，修夹具后定向PASS1，保留原FAIL记录。根级新增34项及83项组合PASS后，以139项最终组合核对最新后端输入，不虚构合并数。frontend4单元/build/两个Chrome mock PASS；同位置慢GET P2先FAIL再序号保护PASS。真实Chrome+HTTP+保留专用PG Acceptance02：4次进度与原资料绑定快照、project/unit保存/恢复version2、刷新回读PASS；模型20/搜索2 unchanged。真实节点偏好界面非本浏览器范围，PG和mock已覆盖。Ruff/diff/原文hash PASS。见[G2学习控件报告](../acceptance/G2-learning-controls-2026-10-01.md)。负责人体验NOT RUN。

Rollback：新功能在本feature分支保留有意义提交；0014/0015只作增量迁移，非空学习历史迁移拒绝破坏性降级。仅受控测试库可应用新迁移，原库不写入；不重置计量或清除验收证据。完整Goal仍active/NOT_READY，不合并master或标记milestone。

下一条安全动作：继续G2六角色/章节连续性与受控资料替换，沿用现有公共source/section与计划版本机制；GitHub浏览器授权按薄集成及维护者App配置推进，RAG只暂停缺契约分支。随后G3总结/Prompt原文与反馈历史。不重复G0、真实生成或已完成搜索/控件验收，不将G2本批当完整Goal。

## G2第三批执行边界（进行中）

上一轮分类：progress。当前HEAD57bb309d8ed5342a6b039d710dcfafa780a12073，与已核对远端一致；工作区仅既有禁操作目录未跟踪，业务基线无未提交内容。本批不重跑收费验收，模型20/50、搜索2/1000继续累计。

Goal：六种资料角色可表达；主线连续章节区间依据作者目录相邻位置校验；替换主线先生成可回读差异预览，再由用户明确确认新计划版本。历史来源标题/URL/章节/版本保存，旧出现位置进度与资料选择不被改写。

Constraints/Non-goals：保留现有业务publisher/版本构造和source/section，禁止重复publisher、伪造模型Run或知识事实源；不依据标题相似/URL可达性证明覆盖或掌握。无真实模型/搜索调用，原数据库/服务和旧journal不动，不运行外部仓库，不改已发布迁移/Seed版本。GitHub/RAG缺配置仅暂停对应分支。

Allowed changes/Ownership：SolMedium拥有角色enum/curation/Seed验证/资源角色schema与0016及针对测试；SolHigh拥有新resource_changes领域/Port/应用/DB/API/0017、必要的旧publisher事务复用与正式来源快照读写、针对性质测试。root维护唯一契约、组合根、前端与当前检查点；两个后端写入者活动时root不写业务代码。迁移0017依赖稳定0016，不并行改相同文件。派发参数被工具接受不作为实际模型解析证据，仍NOT OBSERVABLE。

Tests/Evidence：规则/契约→隔离PG归属/CAS/幂等/取消竞争/目录变更/回滚/旧历史→前端mock与自有计划的真实HTTP/Chrome。依据目录rank验证连续性，允许作者order_index稀疏，禁止排序掩盖倒序/重复/缺章。本批测试NOT RUN，待实际产物核对。非空新历史迁移拒绝丢失数据的downgrade；正常revert保留历史表和回执，不做master/milestone合并。

本批增量证据：角色实现者已停止业务编辑，规则/curation/provider 58项PASS，六角色CHECK与完整目录读取真实PG 2项PASS。0017首次FK无匹配unique导致迁移FAIL，已在新0017修复；临时表夹具首次缺DEFAULTS导致FAIL，修夹具后定向PASS。Root严格目录检查发现已发布agent v2 context主线跳过retrieval，新增受控v3保留v1/v2原文，更新当前bootstrap和测试夹具；旧v2仍明确拒绝新的严格导入，不放宽规则。v3性质先FAIL（新文件未存在），后一次错误消息匹配FAIL（11通过），修断言后Seed/角色/真实Seed PG组合37项PASS，exit0；出版/curation/新快照规则组合76项PASS，exit0；更新v3后G1纵向/私有资料/偏好PG组合20项PASS，exit0。一次错误测试路径命令FAIL（未运行测试）已用实际路径纠正，不算业务验证。Frontend build PASS；六角色标签和历史来源未知说明已可显示。Root组合根接线进行中，proposal API/PG竞争与替换浏览器仍NOT RUN，不提交未完整代码。累计外部调用仍20/50、2/1000。

本批收口：业务与测试实现者均已停止编辑。独立只读review发现私人绑定集合漂移及新增source锁等待跨越lease两项P1，实际PG RED4→GREEN4，阶段内修复。最终实现者20项PASS（2unit+17实际proposal PG+1关键G1），root最新HTTP/G1/Seed PG组合8项PASS；早期较宽组合50通过/1测试import失败不重标全PASS。后端离线unit+contract551 PASS/2 skipped NOT RUN发生在P1修复前，相关后续PG已核对修复输入。OpenAPI/export/gen/build/4单元和Chrome mock PASS。真实Acceptance03 Chrome+HTTP+保留PG发布revision2、沿用2份私有绑定、旧Exposure原值保留、新版全version0未开始和刷新PASS。第一次实际浏览器FAIL在成功发布后的测试DTO层级误读，修断言后只GET同proposal/回执继续PASS，无再生成/发布。报告[G2资料替换](../acceptance/G2-resource-replacement-2026-10-01.md)。

当前专用PG已到0017并受控导入Agent v3，旧v2 payload不动。旧30734/PID11360 controls服务按命令路径核验后关闭；当前session23755、8021/PID28388为var/v2-g2/replacement_acceptance_server.py，Acceptance03、无modelworker、搜索累计wrapper承接2次。前端5175/PID41308不变；原8000/5432/11434未重启。新的真实浏览器脚本完成报告后拒绝重跑；若未来仅观察恢复，读取既有结果，不重新创建proposal。累计仍模型20/50、搜索2/1000，unknown0。GitHub账号授权未接线、真实RAG缺契约仍局部BLOCKED，整体Goal保持active/NOT_READY；下一独立切片为GitHub薄授权与G3总结/Prompt原文历史，继续F01–F18。

G2第三批代码已正常commit/push，远端存在SHA `a294078b590d0f8a5d04c652b0c7d0af22fd8aea`，ls-remote与本地相等；未改develop/master。随后本验收/当前检查点/服务配置及矩阵文档提交需续接读取实际HEAD，不猜SHA。Ruff受影响Python/diff/新真实脚本syntax/秘密忽略规则及两份原指导hash PASS。业务编辑已停止；只有原禁操作目录未跟踪，不清理或提交。

## G3第一批执行边界（进行中）

上一轮分类：progress，依据本机session_meta与turn_context核实了四个既有代理的实际模型，纠正“不可观测”记录。当前实际HEAD `891208188bb7b242ade5fda739d2aa1a881d6de1`，业务工作区无未提交内容；既有禁操作目录不动。本批复用Kuhn/SolHigh与Gauss/SolMedium；followup没有模型切换参数，不能假称新路由。

Goal：用户结束学习时按两项固定问题和一项情境问题写简短总结；原文先明确保存，保存成为不可变修订；随后可选择真实模型反馈，反馈绑定该修订，旧原文/反馈及计划版本仍可读。失败、迟到、刷新与409不覆盖本地编辑。此批是F09/Q10的增量，不取代G3主项目、阶段任务、Prompt评审/导出及完整F01–F18目标。

Ruling：V2简短总结允许1–20,000个Unicode码点的非空白原文，保存时保留所有空白；旧领域50字符下限不再作为保存门禁。原文保存不发模型、不改变Exposure/掌握。反馈为引导，不能成为强制通关或证据验收。每个新出现位置独立CAS头，attempt_no保留单元全局递增的既有约束；历史缺少位置/快照的旧记录显式标明来源不完整，不冒充新版本事实。

Constraints/Non-goals：保留服务端owner/project scope、RLS、现有ai_jobs/ai_runs与付费Attempt账本、不盲重派unknown、同事务lease/cancel/owner fence。复用现有load→review→validate→persist有界评审执行器，不新增通用工作流/第二套队列。原服务/数据库、历史Run/草案/checkpoint/journal不操作；不外发原用户私有内容；真实新验收只使用隔离测试账号自建内容并承接累计额度，先免费preflight。模型20/50、搜索2/1000，目前无新增调用。

Allowed changes/Ownership：Kuhn/SolHigh拥有总结领域、Port、Application、DB/API/测试、新0018及必要0019窄领取扩展、现有queue/provider账本与评审的有界接入；Gauss/SolMedium拥有总结前端、客户端方法及独立浏览器Mock。root拥有公共契约裁决、组合根/容器/路由注册、生成OpenAPI、证据与实际验收。两人编辑业务时root只维护文档及只读核查。模型绑定/预算/同键异体及结果写入事务由High负责。

Tests/Evidence：先原文/短文/CAS/幂等/跨账号/不可变历史规则与真实PG，再异步反馈一次派发、原文先落库、未知恢复/取消/lease/迟到结果性质；前端Mock覆盖网络/409/迟到反馈/终态停轮询，再用专用PG和Chrome验证真实保存/反馈/刷新。当前新测试NOT RUN，不以Mock或静态检查代替真实反馈。新迁移只增量，不改已发布迁移。

Rollback：保留已有有效历史及收费证据，仅本feature分支正常增量commit/push；非空总结/回执历史不允许破坏性downgrade。未完成全Goal不合并develop/master、不标milestone；缺GitHub App/RAG配置仅暂停相关实际分支。

本批收口：两名业务代理均已停止编辑。最终总结unit/真实PG及既有queue/budget41项PASS exit0；root公共契约9/真实HTTP3组合12项PASS exit0。OpenAPI、生成类型、frontend4单元、build与最新Chrome Mock PASS。只读review发现头/窗口快照不一致P2，单SQL读和真实PG barrier已修复；root发现private来源进入反馈payload的P1，白名单projection保留本地完整快照，真实PG RED→GREEN。root首批HTTP因不存在actors夹具FAIL，修为实际auth_users后最终组合PASS；早期失败详见[G3报告](../acceptance/G3-summaries-2026-10-01.md)，不重标。

新AcceptanceId v2-g3-20261001-01，免费preflight PASS，Chrome+真实HTTP+专用PG+实际deepseek-flash一次反馈PASS，Run run_824fccdb1b8848b1bd9d614b1df76df0 succeeded。原文先保存，排队期间再保存新版并继续未保存编辑；反馈仍绑定第一版，新版/编辑及Exposure不变，刷新读回两版原文和历史反馈。RLS只读检查1 succeeded Attempt、unknown0，当前新journal/evidence按已有工具收口；旧ID不动。累计模型21/50、搜索2/1000。

当前服务：旧23755/PID28388按命令路径核验后关闭；新session21096为var/v2-g3/summary_acceptance_server.py，8021 listener PID38980（Python launcher PID53156），受控最多新派发1次，现已消费。前端5175/PID41308仍在，原8000/PID43688未操作。专用业务库studyplan_test_v2g1real_2f6ac462迁移到0019；cp库不变。var/v2-g3保存实现者报告、分阶段回执、预检、真实浏览器JSON/PNG及只读Run元数据，禁止提交私密原文与账号文件。后续只GET保留结果，不盲重跑新服务器/验收。

下一条安全动作：继续G3主项目/阶段任务和Prompt评审/修订/指定导出，保持一次反馈引擎及历史保全；GitHub薄授权与RAG真实契约局部缺口另记。F09技术第一批已IMPLEMENTED，负责人体验NOT RUN；整体active/NOT_READY，未合并develop/master或接受milestone。

G3本批代码167345827a61049450f0f35c37f0075425e4a19c已正常push，ls-remote与本地相等；develop/master未改。验收/路由显示说明/当前检查点文档提交随后承接，续接读取实际HEAD。秘密忽略规则、两份原指导hash、Ruff/diff及浏览器脚本syntax PASS。只剩原禁操作目录未跟踪，不处理它们。

## G3第二批执行边界（进行中）

上一轮分类progress：总结真实验收和代码/文档已推送，当前HEAD0241f376b6cb1178d156fb66ba240bacda6f84d4，跟踪业务工作区clean。Goal为已有主项目/阶段任务要求→用户方案/Prompt明确保存→指定修订单次反馈→指定版本复制/下载及历史；保持全F01–F18，后续自选实践方向/任务调整仍须受控新版本，不能以本批读取候选要求冒充全部F10。

Constraints：复用现有practice_projects/tasks、plan_task_links/knowledge快照、review graph、队列及Attempt账本；不重建引擎、不改已发布0018/0019、不写原库/原服务/旧Run或journal。原文1–40000 Unicode码点非空白、保留所有空白，先存后反馈；导出明确选定不可变修订，raw精确原文，implementation确定性绑定冻结要求，不产生模型润色或伪造成果。反馈不得更改学习/实践验收状态，未知不重派。Summary与Prompt活动反馈额度合并计算。

Allowed changes/Ownership：Kuhn（本机日志gpt-6.1-sol/high、复用）拥有Prompt领域/Port/应用/DB/API、0020及必要provider/ledger/claim扩展和真实PG性质测试；Gauss（gpt-6.1-sol/medium、复用）拥有PromptPage、独立promptClient、main实践挂载/SupportingPages、practice样式及Chrome Mock。root冻结公共DTO，维护组合根、生成契约、实际验收和证据；两个业务代理编辑期间root不写业务代码。低风险事实由工具直接核对，既有thread数量限制下不伪称已新建Luna。冻结契约位于忽略证据var/v2-g3/prompt-contract.md。

Non-goals：本批不做外部项目执行、真实成果验收、通用MCP/Skills/Sandbox或任意AI覆盖用户原文；自选项目及任务新版本仍继续推进，GitHub/RAG缺配置只保留对应局部BLOCKED。

Tests/Evidence：先规则/真实PG/CAS/幂等/归属/取消/未知/隐私/导出版本，再公共HTTP/类型/build/Chrome Mock，最后新AcceptanceId下已授权额度内代表真实反馈与实际导出。当前本批测试NOT RUN；累计模型21/50、搜索2/1000，不重置。Rollback使用正常增量提交，非空Prompt/导出/回执拒绝破坏性降级；历史原文与账本保留，完整Goal未完成不标master/milestone。

本批收口：Kuhn与Gauss均停止业务编辑，root完成组合根/生成契约和实际验收。规则/provider/domain/budget最终67 PASS exit0（真实HTTP400修复后0.56s）；Prompt实际隔离PG17 PASS exit0 35.56s。受影响Summary/规划队列/预算33个用例PASS，其组合命令整体FAIL exit1，因为Prompt夹具导入被Ruff删除导致17个setup error；恢复测试import后只重跑Prompt17 PASS，不虚构组合exit0。Root Prompt3+Summary3实际Cookie/CSRF/HTTP6 PASS exit0 23.47s、契约9 PASS、OpenAPI/生成类型/build50modules/frontend4单元/Chrome Mock/Ruff/diff PASS。独立只读复核无可复现P0/P1/P2，具体范围与限制保留于ignored报告，不当作运行验收。

上一轮模型显示追问分类progress：本机JSONL核实了实际路由并纠正用户可见说明；本轮继续业务验收。第一次Acceptance02真实Run `run_4fdb6092681d4711905fe5e0023fdacb` HTTP400、failed、unknown0：Prompt JSON模式缺少明确JSON输出指令。离线回归RED1→最小提示词修复→最终67 PASS。既有失败原文/Run/Attempt/证据全部保留；同一Run不重派。真实失败浏览器观察原文/历史/指定旧版导出/继续编辑保全PASS，没有新增模型调用。

新Acceptance03 `v2-g3-20261001-03` 免费预检PASS；真实Chrome+配置deepseek-flash+HTTP+保留PG一次反馈PASS。Run `run_a492896d702d4ee5ac68ce7232dc99f4` succeeded；433input/723output、4428ms、cap4096、unknown0。原文先存，排队中再保存新版和输入未保存文字；反馈绑定旧版，新版和编辑不动。旧版raw/实施导出、实际复制/下载、Exposure及task状态不变、刷新读回与历史PASS。Windows剪贴板会将LF转CRLF，按换行归一化后完全一致；服务端导出和UTF8下载逐字相同。初次逐字剪贴板断言FAIL及阶段文件独占写FAIL如实保留，只调整平台观察/沿用已有导出，没有重派收费。

累计模型23/50，搜索2/1000；02为已知失败1、03为成功1。两个本批新journal/evidence通过已有工具分别按真实failed/succeeded终态收口，旧ID与账本未改写。var/v2-g3保存preflight、失败/成功元数据、分阶段原文/回执、两个PNG及实现/只读review报告；秘密原文、账号与.env不提交。已完成实际脚本拒绝重跑。

本批代码 `dff7fc10eaed1339b3ec40134a8d9d347c546ca8` 已正常commit/push并ls-remote核对存在；仅31个白名单代码/契约/前端/测试文件提交，未提交原禁操作目录。实际服务：先后按精确命令路径停止自有summary listener38980及失败Prompt listener4368，当前session94246、8021/PID33812为prompt_corrected_acceptance_server.py；前端5175/PID41308保留，原8000/PID43688、PG/PID8124、Ollama/PID22760未重启。专用业务库增量到0020，cp库不变；当前wrapper已消费唯一派发，不盲重启。

F11技术第一批IMPLEMENTED/Integrated，Q10代表技术门禁PASS；负责人体验NOT RUN。见[G3 Prompt报告](../acceptance/G3-prompts-2026-10-01.md)。下一安全动作为G3/F10自选主项目和阶段任务的受控Proposal→差异→明确确认新计划版本，保留旧Summary/Prompt/Exposure及来源；随后推进G4成果/Outcome及其余缺口。GitHub App与RAG缺契约仅暂停对应实际分支，整体继续active/NOT_READY，不合并develop/master或标milestone。本验收文档提交后的实际HEAD续接时读取，不猜SHA。

## G3第三批执行边界（进行中）

基线为已核对远端 `6fb56dbdd81f83d76e11383ab4e3642698b9663b`；上一业务轮分类progress（F11真实失败/成功与指定版本导出、代码/文档已推送）。模型23/50、搜索2/1000、unknown0。原服务不变，自有8021的已消费验收wrapper不再次派发。本批不调用模型/搜索。

Goal：用户沿用候选主项目或填写自己的项目，修改/添加阶段任务、明确交付物/范围/知识/验收标准，先看完整差异与历史影响，再确认新PlanRevision；旧实体与Summary/Prompt/Exposure/成果历史保留。不会把手写方案或新任务标为已验收。

Constraints/Ruling：复用现有PlanPublicationService及同事务发布/私人选择复制；现有publisher仅保存task链接，正文不在结构指纹内，禁止原位改旧project/task正文。项目内容变化时新project及对应tasks；只改任务时保持project和未变task身份，更新任务为服务端新ID/key并保存精确前身lineage，保留UNIQUE(practice_project_id,stable_key)。知识ID不变，只允许当前计划引用的节点及合法角色，至少一core。新任务pending，历史不冒充新证据；受保护草案不能绕过预览入口普通发布/编辑/取消。

Allowed changes/Ownership：Kuhn（复用gpt-6.1-sol/high）拥有新practice_changes领域/Port/Application/DB/API、0021、新测试及窄plan_repository guard/resource_changes复制与digest helper提取；Gauss（复用gpt-6.1-sol/medium）拥有新PracticeChangePanel/客户端/Mock、PromptPage嵌入与旧路线未保存原文可见恢复、main回调和局部样式。root冻结公共契约/迁移编号并拥有后续组合根/生成类型/实际验收；双业务代理编辑期间root只写本进度/ignored证据，读取必要边界，不写业务代码。契约var/v2-g3/practice-change-contract.md，事实映射practice-version-map.md；按已接受V2连续实施授权推进，不重复请求普通设计授权。

Tests/Evidence：当前本批NOT RUN。规则→隔离PG原文/旧实体保全、归属/CAS/幂等、绕过拒绝、basis/private/source漂移、取消与发布竞争、事务注入回滚→HTTP/生成类型/build/Chrome Mock→自有真实PG+Chrome无费用发布新版本与旧历史回读。独立事实映射已完成，NOT RUN测试、不当作验收。Non-goals：不执行外部代码、不建新工作流/通用Proposal框架；其它F13操作及全路线重规划仍须后续切片。Rollback为普通增量Git，非空新历史拒绝破坏性降级；不写原数据库、旧Run/Draft/journal，不合并master/milestone，整体active/NOT_READY。

本批追加边界：Kuhn已完整读冻结契约并开始规则/实际PG RED；其发现guard读取保护标记早于advisory等待，root同意将resource/practice闭合保护重查放在advisory之后并锁draft，同批用PG barrier证明拒绝绕过，不扩大通用框架。Gauss前端仍编辑中。collaboration.list_agents已确认两者running，并针对它们执行一次60秒有界wait（未完成）；不得以观察超时当作终止/重启。当前没有本批完成测试声明，后续先读真实回传/当前文件，不重复已有效F11收费验收。RAG/GitHub配置presence-only本机检查仍MISSING，不打印端点/密钥；只暂停相应实际接口。

2026-10-02跨日续接：仍同一Goal/分支/累计授权，不重置.git/v2-paid-quota-20261001（23/50）或搜索（2/1000）。Kuhn报告advisory保护标记barrier原4FAIL→锁后重查4PASS exit0 9.26s（save/publish×resource/practice），0021在新隔离harness upgrade；主preview从事务stub RED1开始，未完成整体PG声明。Gauss首轮Chrome Mock与build PASS，临时DTO遵守冻结契约，旧路线脏Prompt已有可见恢复/复制，尚在补预览元数据与回归，未STOP；实际HTTP/PG/浏览器NOT RUN。新验收日期按实际执行记录，原指导/已完成历史报告不因跨日重写。

Gauss（实际gpt-6.1-sol/medium）已BUSINESS EDITS STOP；root（实际gpt-6.1-sol/high）随后成为第二个业务写者，拥有组合根/main/生成类型与HTTP测试，Kuhn（实际gpt-6.1-sol/high）继续后端事务及其PG验证。metadata-only route auditor再次核实上述路由；历史Helmholtz为Sol/medium，Lovelace有Sol/high日志但pending_init不能当作活跃复核。未成功创建Luna，不声称低风险任务已经改走Luna。

Root实际Cookie/CSRF/隔离PG HTTP：新入口404 RED→服务装配/路由/私密422后3 PASS；中间测试把未确认警告的DomainError误期望为422，实际400，修正测试后PASS（字段无效仍422）。新窄知识角色DTO输入后HTTP3+契约9 PASS exit0。OpenAPI/gen aliases/build52模块/frontend4单元 PASS；第一次接generated aliases因旧Prompt知识role为宽string而TS FAIL，新PracticeChangeTaskKnowledgeView仅收紧本接口响应角色为三枚举后build PASS，不改旧Prompt DTO。

Gauss复用只读复核报告一项P2：主项目clone→refresh保留旧form.projectId，而选择器显示新项目，后续提交错目标。Root先新增定向Mock FAIL，再显示旧目标占位、明确选择新项目时保留本地文字、旧任务不自动赋新身份且核对前禁预览，Mock PASS exit0；另无实践项目context初挂载缺空状态已定向FAIL→最小null form/空提示→PASS。已解决，不延期。受guard新输入影响的PlanRepository/PlanningJobs/Publication72用例 PASS exit0，非模型调用。

Kuhn最新完整Practice PG29 PASS exit0 47.23s；其新增basis结构指纹调用漏括号导致中间20 FAIL/9 PASS，修复后重跑29 PASS，失败如实保留。最终规则/Ruff及受影响Resource PG仍在执行，尚未STOP。Root准备新无费用手动Acceptance `v2-g3-20261002-01`，但专用0021迁移/服务重启/实际Chrome发布仍NOT RUN；不因准备脚本声称实际验收。原8000/PG/Ollama和5175核对PID保持，当前owned8021仍已消费Prompt wrapper，累计23/2不重置。

本批收口：Kuhn BUSINESS EDITS STOP，最终规则6+Practice PG29+Resource PG17组合52 PASS exit0 74.02s；追加双pending预览竞争及旧Prompt历史2 PASS exit0 7.66s，去重覆盖全部30新PG；其owned11文件Ruff PASS。根组合根/HTTP/生成类型已接；定向Mock新增空context、clone后旧项目/旧task与stage ID更新的RED→GREEN恢复防线，最终Mock/build52模块/前端4单元 PASS。按现有publisher新stage/assignment ID重映射核对冻结资源内容，只读脚本原错误逐字ID断言FAIL已注明，最终owner RLS只读PASS，未重发业务。

新无费用Acceptance `v2-g3-20261002-01` 实际Chrome+HTTP+保留PG PASS exit0：专用库0020→0021，新自选主项目和任务预览后明确确认，Plan2→3，clone30。提案pcp_f4088a2bc95a4cd69bf14b76d3f19b4d confirmed，preview/confirm两回执。旧project/tasks正文、2版Summary/2版Prompt/反馈/两种已存export及旧Plan2 Exposure观察保持；该Plan2实际记录Exposure0，非空旧进度由PG策略用例证明，不扩大浏览器证据。新task pending、新Prompt空、新Exposure not_started/v0。旧Plan未保存原文可见只读并复制，Windows LF→CRLF归一相同；刷新新路线/旧历史PASS，两PNG已看。模型23/50/search2/1000/unknown0不变，没有新Run/付费journal。

精确核对后只停自有旧8021/PID33812，当前自有practice_acceptance_server.py session43312、8021/PID22376无模型Worker/外部派发；原8000/PID43688、PG/PID8124、Ollama/PID22760与5175/PID41308保持。完成的实际脚本拒绝重跑，部分intent必须先读取已知提案/当前路线。F10技术Implemented/Integrated，负责人体验NOT RUN；F13其它操作、F12/F14及全功能缺口继续，整体active/NOT_READY。

代码 `e01b82ad47fea1db0c24e37b3f0463d18c3ace1d` 已正常commit/push，GitHub ls-remote一致，24个白名单文件；两指导文档原hash不变。详细[G3实践报告](../acceptance/G3-practice-changes-2026-10-02.md)与ignored前后端包/实际分阶段元数据。文档提交随后承接，续接读取实际HEAD。未合并develop/master、标milestone或代负责人接受。下一安全动作G4/F12成果及可检查证据/分级验收，F14Outcome归集；缺GitHub/RAG配置仅暂停相关实际分支。

文档提交 `e8faf51d0f9b0111accd25567e5246b7169581e6` 已push并ls-remote核对存在；22个相关文档链接、两原指导hash、quota23/search2/unknown0与diff PASS。此时跟踪工作区clean，只剩两原禁操作目录未跟踪，不处理。

## G4第一批执行边界（进行中）

上一轮分类progress：G3/F10真实手动新版本及代码/文档已推送。基线远端e8faf51；仍同一Goal，模型23/50、搜索2/1000、unknown0。Goal：外部成果原文/来源分类归档→保存当时任务要求→明确人工标准覆盖决定/需补证据→不可变补充链/历史，Outcome按实际保存记录归集七类（六产物加其它），空项待补充、不编造数据或结论。完整F01–F18范围保留。

Constraints/Ruling：复用现有PracticeSubmission/AcceptanceReview/EvidenceGrade及两个权威表，0022增量位置/版本/快照/原始细节和heads/receipts，不建平行业务事实源；复用PgSummaries owner/advisory/receipt/paging与PgPrompts冻结上下文，不加graph/worker。本批零外部派发。用户自述/外部报告/来源引用均未平台核验；新证据仅reported/insufficient，note-only沿现领域规则insufficient，不接受客户端grade/verification/reviewer/actor。明确USER人工确认需要完整冻结标准与证据索引覆盖及核验限制确认；不能代表平台实测或KnowledgeVERIFIED，不改Exposure/总结/Prompt。旧历史位置没有依据则legacy_unfrozen，不用当前要求补写历史。

Allowed changes/Ownership：root（已核实gpt-6.1-sol/high）冻结ignored var/v2-g4/submission-contract.md；Kuhn（复用gpt-6.1-sol/high，未伪称降Medium）拥有新practice_submissions Domain/Port/Application/DB/API、0022及规则/实际隔离PG；Gauss（复用gpt-6.1-sol/medium）拥有SubmissionPanel/OutcomeArchive/client/Mock及必要PromptPage嵌入/scoped样式。两业务writer并行期间root只读必要边界、写本进度/ignored契约；不写共享业务。复用Gauss只读入口映射，未重做全仓调查；当前工具未成功创建Luna，不假装实际路由。

Tests/Evidence：本批NOT RUN，先规则RED→GREEN、精确raw/来源语义、owner/RLS/FK、三版本CAS/receipt/atomicrollback、人工覆盖/旧位置/依据变化拒绝、补充不降已accepted、不可变历史/legacy/Outcome分页，前端unknown/409/422/迟到输入/旧Plan本地可见复制；双方STOP后rootHTTP/组合根/生成类型及新专用Chrome手动验收。Kuhn已确认完整契约并采用闭合PgPracticeSubmissions(PgSummaries)仅重用事务/回执/分页，不调用review队列。Non-goals：此批不执行外部仓库、不伪建平台实测/来源核对、不调用模型、不假称完整Outcome Profile已完成；模型建议/真实来源核对及F02/Profile与其余F13继续后续切片。Rollback普通增量提交、非空新历史拒绝破坏性降级；不写原库/旧Run/journal，不操作禁目录，不合并master/milestone或代负责人接受。

当前服务仍自有practice_acceptance_server.py/8021/PID22376（无Worker/外部派发）、5175/PID41308；原8000/PID43688、PG/PID8124、Ollama/PID22760未重启。当前专用Plan3。新0022/API/真实验收未接不得宣称已经可用。下一安全动作读取两个worker最新packet/稳定DTO，等待BUSINESS EDITS STOP，接组合根和生成类型；不重跑完成的G3实际发布/收费验收，不重置累计授权。

本批收口：Kuhn/Gauss均BUSINESS EDITS STOP后root接组合根/两个router/私密422/生成类型。新规则13+既有EvidenceGrade20组合33 PASS exit0 1.22s；最新实际PG30 PASS exit0 43.88s，包括真实发布锁等待后旧保存409、三版本CAS/回执/原子回滚、不可变/legacy/父位置/人工覆盖/补充不降已accepted/不写学习、非空0022 downgrade拒绝。测试-only长application_name被PG截断及cleanup先join导致中断FAIL保留；短marker/有界timeout/先释放连接修正后定向和最终PG PASS。只清理已精确核实归属的唯一中断测试库，没有原库或全局角色操作。

Root HTTP先404 RED；接线后新4HTTP用例通过，但含契约的组合命令整体FAIL exit1（旧OpenAPI未导出），不重标。导出后contract31 PASS exit0；root最终独立真实Cookie/CSRF/private422/owner/人工覆盖/新Plan后exact原save/decision回执HTTP4 PASS exit0 17.64s。生成类型/build55模块 PASS；旧43paths/123schemas语义逐项不变，新增5paths。前端成果Mock PASS，原Prompt Mock回归 PASS；422/409/未知/迟到编辑、旧Plan可见复制/原body/key核对及legacy/分页已测。旧决定跨Plan专门Mock交错NOT RUN，不拿后端证据替代浏览器声明。

Rawls只读review实际gpt-6-luna/max已由2026/10/02 JSONL核实；指定owner/receipt/人工非实测/不可变/legacy后端边界无可复现缺陷，运行测试NOT RUN。Kuhn SolHigh/Gauss SolMedium仍沿原会话，不伪称切换。Root Ruff imports/zip strict、staged EOF空行初次FAIL已最小修复，最终独立Ruff/diff PASS；两原指导hash保持。

新零费用Acceptance `v2-g4-20261002-01` 真实Chrome+HTTP+保留PG PASS exit0：note-only先存insufficient→明确needs_more_evidence→新的parent补充记录reported→两条冻结标准分别引用证据/观察+明确核验限制ack→USER accepted/task.version3。初始psb_972814f6818a4d0ba0d33aba130d0cd6、补充psb_483fa490419442dfb2e88926379f4431，position head2，四save/decide回执。样本是自有CLI真实sum成功/输入失败报告，按external_report归因；产品没有执行/来源核对，不标verified/Knowledge/Exposure完成，不代表负责人体验。先一次登录未完成即GET的401 FAIL，成果intent0；等实际login200/工作区后原未消费验收PASS，失败JSON保留。新编辑保持、实际复制Windows LF→CRLF归一相同、两历史刷新及7组档案/5空组待补充PASS。两PNG已看，owner RLS只读核对PASS，完整学习工作区仅明确任务status/version变化，原Summary/Prompt/export/Exposure GET保持。

代码 `9cf4cdb94d8db073f98b386da89766d15be66ca8` 已正常commit/push且ls-remote相等，22个白名单文件。详见[G4成果报告](../acceptance/G4-submissions-outcomes-2026-10-02.md)。旧自有22376按精确命令/port确认后停止，当前`var/v2-g4/submission_acceptance_server.py` exec52925、8021/PID55044，无Worker/外部派发；专用business DB0022，cp库不变。原8000/PID43688、PG/PID8124、Ollama/PID22760、5175/PID41308和5174/PID49752未重启。累计仍模型23/50、搜索2/1000、unknown0；已完成实际脚本不重跑，所有raw/intent/账号/packet留ignored var，不提交秘密。

F12人工存档/决定与F14首批实际分类档案Implemented/Integrated，负责人体验NOT RUN，完整Goal active/NOT_READY。下一安全动作推进F02目标/Outcome Profile与剩余F13有界操作/全路线新版本，并补F01项目管理、F03三个Blueprint内容及完整Q门禁；GitHubApp/RAG缺条件只暂停相关真实分支。不能把初始档案当完整Profile或一批人工验收当F01–F18完成；不merge develop/master或标milestone。文档提交随后承接，续接读取实际HEAD。

文档提交 `da580f4e1b6bcb9a05951993be1e8a3084df371b` 已正常push并核对GitHub存在；26个文档链接、两原指导hash、quota23/search2/unknown0及diff PASS。本轮最新presence-only检查RAG_BASE_URL/RAG_API_KEY及GitHub三个App变量均MISSING，不打印值。

下一批准备：复用已实际核实gpt-6-luna/max的Rawls，只读定位F01现有项目管理/身份范围/API/UI与生成fence；collaboration.list_agents已确认running，非凭旧状态推定。root独立读取F02现有PlanGenerateRequest/PlanningPage/Seed验证入口，事实包var/v2-g4/goal-profile-facts.md：目前只有goal+资料prefs，澄清/时间/Profile未实现，不以自然语言目标替代。尚未冻结新公开契约或启动本批业务写入，不把定位当功能完成。续接读取Rawls具体结果、先冻结F01管理边界再派发；不能重跑已完成G4实际脚本/23次收费证据。当前保留server52925/8021/PID55044、业务库0022及原服务，root本进度改动未提交；原禁目录仍不处理。

## 2026-10-02用户进展评估与RAG只读定位

用户新增实施约束已写入AGENTS：针对已定位问题优先复用独立成熟组件/清晰算法，核对收益、依赖、许可证及回滚成本；收益不足且牵引大量工作时改用更小方案，临近交付不轻易迁移整套框架。

当前功能矩阵为16项IMPLEMENTED、1项VERIFIED、1项BLOCKED；这些是整项状态，不能换算成17/18完成。Q门禁6项已有范围内PASS、6项完整验收NOT RUN。核心纵向流程有真实证据，可开始负责人早期体验；完整项目管理、目标澄清/时间/Outcome Profile、三Blueprint内容、完整重规划、GitHub账号授权/RAG、全量门禁/启动备份恢复仍为实质剩余工作。用户体验不能替代技术隔离/恢复门禁。当前5175 HTTP200，8021仍为无Worker/外部派发的G4限定验收预览，只允许登录/退出及成果相关写入；其它写入403是wrapper保护，不能邀请用户把该入口当整套正常运行版本。可用保留测试账号浏览已发布路线、原文与成果档案；真实个人完整体验入口须下一独立准备，不恢复旧Acceptance或新增收费生成。

日期仅作条件性排布：以10月2日现状，早期体验收口目标10月4–5日，完整交付候选目标10月8–10日；剩余约4–6个有效开发日加1–2日集成/用户反馈修复，非已完成承诺。原七天目标继续作为冲刺目标，外部授权/scope契约未明确前不可保证完整READY日期；不得用删功能或未运行门禁换日期。

只读本机定位发现独立RAG工程 `E:\RAG quention`，三个现有Docker API在8000/18086/18087；在线Personal RAG OpenAPI与healthz均HTTP200，已有契约文件contracts/openapi.json。D:\codex-rag-tools仅工具/实验目录。外部调用为健康/文档GET，无检索/问答/模型/私有资料读取，无服务改动；费用累计模型23/50、搜索2/1000不变。先前“无接口条件”表述补充为已找到接口/服务，但StudyPlan接线、实例选择、纯检索与跨账号授权契约未解决；当前OpenAPI无独立检索endpoint及securitySchemes，不要求用户发送模型密钥或猜填RAG_API_KEY。具体实例/前端对应见external-services.md，F17仍BLOCKED。用户只需确认哪套是常用且资料正常的实例。

本轮再次从JSONL元数据核实：Gauss/g1_credentials Sol Medium；Kuhn/g1_short_generation Sol High；Helmholtz/g1_seed Sol Medium；Lovelace/g1_binding_review Sol High；Rawls/g4_submission_review Luna Max。界面省略模型的具体原因无法由此证明，后续派发说明显式展示实际模型/effort，复用不冒称切换。

## 2026-10-02用户注册故障优先修复

F01项目管理尚未开始业务写入时，用户报告注册范围应为6–12、15位以上仍被owned acceptance403拒绝及旧账号登录失败，优先切换到真实故障修复。Gauss实际SolMedium仅AuthPage与Auth Mock，root SolHigh负责Domain/DTO/旧密码兼容、数据库和运行入口。原F01只读包已完成，按项目保留组件内存+归档/退出guard建议留后续，不冒称实现。

已真实重现5175→8021 register403。用户给出旧用户名后，正常.env库账号存在/1学习项目/无已批准路线，验收库不存在该账号；未获取/重置密码或迁移账号。最新注册规则6–12码点，登录继续1–128，权威替代见[ADR-0011](../adr/ADR-0011-registration-and-user-entry.md)，两原指导hash保持。Domain/DTO/UI及生成OpenAPI同步，只两个注册边界改变；认证/RLS/散列/限流/CSRF保留。

先备份正常本地开发库studyplan_b3_local_48fb59cc，再应用既有0011–0022，原41表/1,513行原字段逐行哈希完全保持。备份及元数据在ignored var/auth-fix，不提交私有数据；归档可读不等于恢复演练，Q12仍NOT RUN。当前正常API8022/PID59912 exec77291读取.env正常库；5175/PID37636 exec25717已通过新脚本代理到8022。旧owned Vite41308身份核对后停止；原8000/RAG和8021/PID55044验收wrapper均保留，不移除原保护。没有Worker/模型/搜索派发，累计23/50、2/1000、unknown0。

密码规则RED7 FAIL/21 PASS后Domain定向53 PASS；全部unit+contract591 PASS/2 skipped NOT RUN；真实PG认证9 PASS，受影响Worker/资源PG45 PASS。Gauss Auth Chrome Mock、前端4单元与生成类型后build55模块 PASS；新隔离PG+HTTP/Vite/Chrome真实6位及12码点注册/刷新/退出/登录PASS，PNG已看。初次实际Chrome文案末尾匹配遗漏FAIL、HTTP探测错OpenAPI路径组合FAIL、备份native工具缺失FAIL（未迁移）及Ruff import FAIL均保留；定位最小修复后相关最终PASS，详见[注册入口报告](../acceptance/F01-registration-entry-2026-10-02.md)。

已请用户刷新5175用原密码确认旧账号；用户真实登录仍NOT RUN，不能用账号存在替代。完整项目管理/F02/F03等Goal继续active/NOT_READY。正常API启动未启动Worker，完整日常生成入口需后续额度/发布Seed及运行条件收口，不能自动恢复旧Run。下一安全动作：收口本修复、保留正常入口并接收用户反馈，继续F01冻结/实现；不重跑已完成收费验收。

代码`b0e342fa9cdd948a7b4d882de8c4aa0458416afc`正常commit/push，GitHub SHA一致。实际Auth临时8023/5176精确停止并核对唯一自有studyplan_test_authfix_0ffbc5ce的schema/4合成账号/无Run/Draft/无活动连接后清理；正常8022/5175及保留8021不停止。最终新文档24链接、原文hash/额度检查PASS；当前仅文档收口，随后承接提交。

收口时重新轮询实际77291服务，观察一次login401后正常login200；随后仅只读auth owner scope，确认用户旧账号在本轮库升级/启动后有一个新有效会话，未调用issue/login或获取秘密。正常旧账号认证技术证据PASS，用户主观体验反馈仍NOT RUN；workspace404对应该账号此前没有已批准路线，不标为登录失败。metadata留var/auth-fix/owner-login-observation.json。此前“实际登录NOT RUN”是观察前的时间点，以本条新增证据为准。

## 2026-10-02学习前端、阶段总结与自动阶段进度收口

用户已认可浅蓝HTML稿并要求实施；最新决定取消退出条件/4-of-5及每日总结，只做阶段总结，并将三项资料操作改为独立按钮/浮窗。阶段进度仅已完成/未完成，系统按同一路线同一阶段非空阶段总结及全部给定实践的既有成果完成记录计算；无实践时只要求总结。移除手动Exposure表单、节点与单元学习状态，不写旧进度/知识核验数据。见[ADR-0012](../adr/ADR-0012-stage-summaries-and-learning-workspace.md)、[ADR-0013](../adr/ADR-0013-automatic-stage-progress-and-resource-dialogs.md)与[本轮验收](../acceptance/frontend-learning-revision-2026-10-02.md)。

React浅色重排、阶段折叠/嵌套小字号、资料章节范围、三浮窗保持未保存输入、阶段选择与总结/具体任务双向同步均已实现。总结API unit_id省略/null为整阶段，显式unit_id保留旧行为；0023新增阶段heads/RLS/FK/版本约束及完整冻结快照。阶段完成为只读投影，复用现有USER accepted成果记录，无新通关操作；旧路线/别阶段/任务全局accepted、旧单元总结及Prompt保存不算本阶段完成。工作区读取绑定owner/project/plan/stage，成功保存后的刷新失败与保存失败分离。

课程建议视图补充Eval-Lite、Eval/Reward→Agentic RL基础→高级评估及可执行产物，RAG/编排目标相关，真实RL训练可选。**尚未导入/发布新Seed，不是生成器课程已更新的声明**；已批准九阶段及历史原文保留，正式课程版本与私人路线变更继续受控事务。

验证：根最终unit+contract605 PASS、2 skipped NOT RUN，前端11 PASS/build57模块 PASS；阶段总结/原行为隔离suite61 PASS，最新阶段完成/成果HTTP与PG定向suite49 PASS（这些suite存在重叠，不累加）。Ruff/diff PASS。阶段完成覆盖无实践、部分/全部、Unicode空白、同位置/RLS隔离、有界head读取和真实accepted后GET。生成类型一次Windows文件打开FAIL，针对重试PASS后contract完整PASS。CUA真实5177三浮窗输入往返、Escape/焦点、默认折叠/嵌套、阶段总结与实践编辑缓冲、具体任务导航、页面390/1024及浮窗390px PASS；所有临时输入恢复，无业务保存/搜索/批准/付费派发。更新mock脚本语法PASS、脚本执行NOT RUN，真实UI保存后的刷新未在实际账号执行；负责人体验/真实provider/RL/恢复演练NOT RUN。

原正常库与保留只读预览库均备份后仅0022→0023，59原表及1516/829原行字段hash一致，归档可读PASS，恢复演练NOT RUN；ignored var/frontend-redesign保存报告/备份。当前正常API8022 exec41685/PID60348、前端5175维持正常业务代理；5177继续8024 exec29938只读预览，仅供审阅，原验收账号/项目保留，业务写入保护不移除。没有Worker、新收费Run、历史journal重派或数据迁移复制；原RAG服务不操作。

前端及阶段总结/进度两个worker均STOP，实际SolMedium已从JSONL核实；独立只读进度/浮窗review实际LunaMax亦核实，无可复现实质缺陷。契约由root整合，最多两业务writer。继续既有feat/v2-g1-user-slice，普通代码/文档提交留后续SHA；没有develop/master合并或milestone接受，完整V2 Goal保持active/NOT_READY。

本轮代码本地提交 `63689bc61f42e50b357e53f5d64fd34dd94a718f`，47个白名单文件，未推送，不声明GitHub已存在。文档提交随后承接；不处理两原禁目录。

## 2026-10-02测试账号课程实际第4版

用户新增明确授权“按之前讨论的对目前测试账号里的计划做对应修改”，现已通过现有owner/RLS/CAS/幂等发布事务将保留的测试账号私人路线3→4。13阶段、43节点、13单元、13具体实践、27资料安排；19官方URL及阅读范围由root在线核对。最小Agent/Eval-Lite提前，Eval/Reward→Agentic RL基础→高级评估顺序落地；RAG/Workflow为兄弟分支、MCP可选、完整RL训练在综合实践之后可选，没有4/5退出门槛或每日总结。新位置阶段进度0/13不继承旧位置，旧原文/成果/Run/发布记录逐行保全PASS。详情见[本轮验收](../acceptance/test-account-curriculum-review-2026-10-02.md)。这替代此前“只提供课程建议、未更改私人计划”的时间点记录；仍未发布新的公共Seed或改生成器课程，未更改正常账号路线。

新专用维护脚本限定原合成账号及隔离数据库，fresh备份归档可读PASS，prepare全流程ROLLBACK及独立回滚检查PASS，publish实际4版PASS，verify只读当前/历史核对PASS。入口先修排除当前阶段内部节点的小修正后前端11测试/build57模块PASS；CUA真实5177版本4及Eval/RL/高级评估的先修、资料、任务PASS。Ruff/diff收口PASS。初次ID前缀/ai_jobs范围/资料角色映射FAIL均有最小修正及事务回滚，未覆盖历史。CLI浏览器、付费模型、真实RL训练、恢复演练及ignored启动新分支运行NOT RUN。

5177/8024继续只读审阅，当前服务已实际显示第4版，无Worker/历史Run恢复/收费派发；5175/8022与原RAG不操作。复用课程worker实际SolMedium只写数据，root整合目录/共享发布事务及核验，无并行同文件修改。继续既有feat/v2-g1-user-slice，禁止目录不处理，无develop/master合并/里程碑/公网发布。完整V2 Goal保持active/NOT_READY。
