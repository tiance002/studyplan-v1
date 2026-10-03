# v6.1 实施与验收 — 2026-10-03

用户现在新增能做什么：代码已支持 AI Fullstack、Agent、Cloud 三条最小路线；生成草案时查看为什么学、持续实践与项目学习安排；确认路线后查看当前阶段项目卡片并复制统一 Prompt 给外部 AI。正式路线只认已发布 Plan。全部新能力已在普通认证、模型 Fake、真实 ownedPG 与 Chrome 中验证；原产品环境未部署。

基线 `6621b89df37d334bd01fd0566622e1d9903f8f3f`；业务提交 `8a05cae60153b4af6c7a830668053af3d6d8d3f2`，分支 `feat/n1-resource-discovery`。SHA 为本地提交，未推送/核实远端。固定参考点祖先 PASS；无 reset/force checkout。最终文档提交后的实际 HEAD 用 git rev-parse HEAD 读取，不用业务 SHA 冒充文档 HEAD。

## 范围与改变

| 范围 | 文件/行为 |
|---|---|
| 权威入口 | [v6.1 Goal](../implementation/STUDYPLAN_V6_1_DEADLINE_GOAL_2026-10-03.md)、[N0/P0审计](../reviews/2026-10-03-v6-1-n0-p0-audit.md)、AGENTS、唯一progress |
| 单一注册表 | backend/app/infrastructure/domain_pack.py 的 CURRENT_PACKS 被 selector/Seed/tests 共用；PG运行仍只读已发布快照，无文件降级。三个旧专项包作为同一注册表中的保留能力 |
| 保护审核事实 | planning_batches.py merge 保留 stage kind/resources/extensions/guidance 与知识闭包；标题和目标可个性化。未知来源仍拒绝 |
| 最小内容 | ai-fullstack-v1.json 4阶段、agent-application-v4.json 5阶段、cloud-services-v1.json 8阶段。Python v2和旧v3/专项包未覆写 |
| Root-only资源 | plan_resources.py 窄支持 CASE_STUDY+REPO 根入口、批准的canonicalURL扩展链接；来源/章节不可伪造 reviewed 状态 |
| 现有数据直传 | main.tsx→MainWorkspace 直接 Plan.extensions 按 stage_id 过滤；先前知识仅来自较早阶段，不等于掌握 |
| 项目学习 | projectStudyPrompt.ts 单一纯函数、ProjectStudyCard.tsx 复制及失败手动回退；不调用AI、不clone、不依赖OAuth/固定commit/文件 |
| 正式路线入口 | LearningPath.tsx 静态课程仅DEV+明确preview参数；生产即使参数存在也隐藏。PlanningPage显示教学与实践说明；Resources根仓库不会伪装成章节或无来源 |
| 回归门禁 | 三目标 PG/浏览器、旧专项手机导航回归、历史九阶段协议压力夹具固定；当前闭环 E2 与 Outcome UI补齐 |

Migration **NO**，DTO/OpenAPI/API **NO**，新增运行依赖 **NO**。仓库migration head仍0024；产品库本批 NOT RUN/未写入。Auth/RLS/CAS/幂等/worker/取消/恢复/总结/人工验收与自动完成规则没有业务重写。

## 验证

| 层 | 状态 | 证据与范围 |
|---|---|---|
| 规则/Fake+契约 | PASS 795；NOT RUN 2 | var/oct6-guidance/v61-unit-contract.xml，pytest backend/tests/unit backend/tests/contract。定向193与之重叠，不累加 |
| 新方向 PG/HTTP+Chrome/Seed | PASS 10 | v61-pg-browser-green.xml：普通注册、后台Worker Fake、生成/确认/幂等/新容器重登录、extensions精确回读、Seed冲突原子回滚/RLS/CLI边界 |
| 最新新方向 Chrome | PASS 1（内部三目标） | v61-browser-ui-final.xml、v61-direction-browser.json。草案教学说明/卡片/真实剪贴板/当前源码 Prompt/刷新重登录/390px |
| 旧专项 Chrome | PASS 1（内部三目标） | direction-browser-regression-green.xml。修复测试移动端点击隐藏sidebar的假设，经正式路径进入阶段 |
| 受保护 PG | 原组合 FAIL；未失败49项证据有效 | v61-protected-pg.xml：53中两个恢复夹具仍硬编码旧次数；不是业务恢复失败 |
| 恢复 PG修正后 | PASS 4 | v61-recovery-pg-final.xml，保留历史九阶段19请求压力范围，实际kill/续跑零已完成批次重派、旧waiting/终态/未知图拒绝 |
| 闭环 E2 | PASS 1 | var/current-learning-loop/controlled-e2-first.xml：两实践0/2→1/2→2/2及无实践总结自动完成，刷新前已更新，刷新/重登录原文与冻结快照保留。明确受控Domain夹具，不证明普通生成无实践阶段 |
| 闭环 E1/E3/E4/E5及Outcome UI | PASS 1 | outcome-ui-first.xml、browser-pg.json：成果归档UI按原ID/原文/人工决定/冻结criteria回读，导航无新增POST；沿用原失败保存/503/409/越权门禁 |
| Frontend单元/build | PASS 13；PASS | npm test；最新npm run build 62 modules |
| Chrome Mock | PASS | 开发/生产项目卡片（复制成功/拒绝回退、旧阶段/新版本隔离）、既有workspace/guidance；Mock不替代真实PG |
| Ruff/mypy/diff/Goal复制 | PASS | 选定所有改动Python lint；四业务模块mypy；业务及自写文档git diff --check；用户Goal逐字节复制 |
| 真实模型/GitHub API/Tavily/RAG | NOT RUN | 本批无新增真实派发，不重用旧unknown/Acceptance |
| 独立 ownedPG 备份恢复 | PASS 1 | var/current-learning-loop/v61-restore-opt-in-final.xml（19.621s）、v61-restore-db1e45d0.json：原生custom dump/restore至另一个owned库，63张表数据与owner/ACL/RLS/policies精确一致，普通登录回读原ID/总结/成果/extensions，恢复后模型调用0，全局角色不变，两个库清理PASS |
| 产品环境/用户接受 | NOT RUN | 合成测试库恢复不能替代私人产品数据恢复与正式入口体验验收 |

早期 FAIL 保留：新路由/事实恢复 RED；旧协议计数随selector变化、tuple/list观察差异；浏览器导航取消GET引发route清理报错及等待超时；Windows剪贴板LF→CRLF逐字断言；草案预览TS可选concepts未处理；恢复首轮历史包夹具无项目extensions（v61-restore-first.xml），改用CURRENT_PACKS代表目标后v61-restore-final.xml及最终显式门禁复跑PASS。最终分别最小修正后PASS。Browser只对被导航取消的附属GET处理特定Playwright错误，POST与HTTP/业务错误不会被吞。复制只归一化Windows换行，其余文本逐字相同。

## 内容与用量

三包均 `curriculum_review.status=outline_checked`、`review_status=selected_scope_pending`，来源 `legacy_index` 仅入口/标题/主题索引，不是章节深读、完整教学质量或实践执行。Agent首版不要求整门GenAI；AI先Web/自己的项目再GenAI/源码；Cloud先服务/Docker/单一Azure，手工部署前核对最低资源，再CI/CD，手工资源运维先于IaC。细致内容深审属于下一批生产，不阻塞本批开发验收。

产品模型累计23/50、搜索6/1000，unknown1保留；GitHub API/Tavily本批0。内容worker报告13次免费官方网页open，含3个仓库根标题/索引；3/6元数据读取已追加 `.git/n1-github-read-quota-20261002/v61-web-metadata-20261003.json`，旧README2/搜索未知记录不改写。仓库root仅 [FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)、[LangGraph](https://github.com/langchain-ai/langgraph)、[Azure FastAPI Quickstart](https://github.com/Azure-Samples/msdocs-python-fastapi-webapp-quickstart)；不下载/执行外部工程或复制其源码。无新组件依赖/许可证变更。

开发请求主协调Sol6.1/high，内容/UI/闭环Sol6.1/medium，只读复核Luna/high；实际解析全部 NOT OBSERVABLE。无Astra/Sol max/全局模型或服务模式设置。只读复核未发现可复现P0/P1/P2，不替代运行证据。

## 风险、回滚、下一安全动作

整体 **NOT_READY**。浅审核入口不能作为已深审课程宣传；真实provider、完整公开GitHub发现链、独立RAG契约、私人产品数据恢复、产品服务准备和用户接受继续受对应门禁。Repo RAG/服务端clone/固定源码映射按v6.1退出新设计；独立个人RAG集成需求保留，不混同删除。

回滚使用正常增量revert业务提交；已有已发布计划/Seed/总结/成果/账本保留，不降级/删除数据库或改旧快照。如果新Seed以后已导入，回滚仅关闭新入口/注册表路由，保留其版本和私人引用。未合并develop/master、未标milestone。

下一安全动作：内容生产按实际已选范围深审与完整交付入口准备；独立owned库恢复已完成，私人产品数据仍受操作门禁；缺外部契约/费用许可仅暂停相关真实支线，保持普通代码实施连续授权。不能以当前Fake全链或本地提交宣布正式交付。

恢复复跑：`STUDYPLAN_V61_RESTORE_NATIVE=1 .venv/Scripts/python.exe -m pytest backend/tests/integration/test_v61_restore_pg.py -q`。默认不设置开关时 NOT RUN；测试先核对现成客户端容器和目标实例身份，只备份/恢复自己创建的测试库，档案保存在忽略的var目录，无全局角色导入或容器自身数据库写入。

原始staged diff严格空白检查 FAIL：用户Goal P0–P7八行含Markdown双空格换行，逐字节原文保留；排除该原文后的严格检查PASS。没有为消除检查提示而改写用户Goal。
