# V2.0实施进度（唯一当前检查点）

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
