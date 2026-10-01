# V2.0实施进度（唯一当前检查点）

日期：2026-10-01。整体 **NOT_READY**；目标仍为F01–F18、G0–G6、Q01–Q12和用户实际验收。G1技术纵向链已实测，G2真实搜索/单元资料第一批已实测，继续G2余项。

## 基线与归属

正式目录D:\studyplan；origin=tiance002/studyplan-v1。起点develop为aa37e4bfa33a41aadb4cb689557e2c7d491d550f；工作分支feat/v2-g1-user-slice。V2入口54c7d3e及G1代码be802e27dfa131ee232d07d40d9650dbd9d5ac21/验收6713c18已推送。G2资源代码237d8c3f385de04f432eeaeca37c3269af0e6f64及验收73e9f8466660d98a8286be056aad47301dd2d4b2也已推送。G2学习控件代码9c1d85abf8987c4434af1ba10fa944e20428f2fd已正常推送并ls-remote核对相等；本报告后的文档提交需续接时读取实际HEAD，不猜SHA。本轮业务编辑均停止；下一轮先核对实际HEAD/状态，不重做已有效验收。既有.workbuddy/和design-preview/禁止操作/提交。develop/master不变，未接受milestone。

原后端8000、PG5432、Ollama11434未重启。原业务库迁移0010，13账号/18项目/26Run，盘点只读；旧waiting_user、unknown、Acceptance09及live journal未处理。原文哈希保持：指导7531B8DA74B043D169E8AE6DFEB1BB738747A0BE936E15B1934C53416D974F35，Goal D4DBCF0FD8F72CDE53385C307F1CCED02F81DC9D7E4449A1A17C4731A350E13B。文件专属whitespace规则保留CRLF及Markdown双空格，不改原文。

## 路由与外部条件

root实际turn_context为gpt-6.1-sol/high。此前仅根据工具返回将子代理实际解析记为NOT OBSERVABLE；用户追问模型显示后补查本机JSONL的session_meta父线程/agent_path与最新turn_context，已获得运行证据：Gauss/g1_credentials为gpt-6.1-sol/medium，Kuhn/g1_short_generation为gpt-6.1-sol/high，Helmholtz/g1_seed为gpt-6.1-sol/medium，Lovelace/g1_binding_review为gpt-6.1-sol/high。这些既有代理没有使用Luna Max；复用工具followup_task/send_message没有model/effort参数，本轮新增代理又被agent thread limit拒绝。不能把提示词或失败spawn当路由证据，未改全局配置。之后派发说明同时展示任务、日志核实模型/effort和复用/新建状态；低风险可新建时明确路由Luna Max，工具限制时报告限制，不把Sol标为Luna。原始实现者报告保留其当时可观测判断，以本条补充审计为准。

用户授权累计模型50请求、Tavily1000请求：**模型20/50，搜索2/1000（2credit）**，下一切片不重置。20模型及2实际搜索均有结果/回执，外部unknown0。Tavily三项配置已存在，预检和G2实际API/PG/Chrome成功。RAG地址/契约/凭证缺失，只阻塞其实际调用；公网部署未授权。GitHub浏览器授权需求已记录，尚未注册App或安装MCP；手动GitHub资料不是账号连接。见[外部服务](external-services.md)。

模型沿用DeepSeek Flash/cap8000，专用验收structure/repair目标8000，不提升cap、不改私有.env。免费预检先因缺dotenv和预算不一致FAIL；复用加载语义、限制目标后PASS。派发前append-only计量：.git/v2-paid-quota-20261001/request-01..20.json及result；搜索.git/v2-search-quota-20261001/request-0001..0002.json及result。未知结果阻断继续，禁止修改记录或重跑同AcceptanceId。产品计数器按单部署DB，验收跨库仍由.git计量承接旧消费。

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
