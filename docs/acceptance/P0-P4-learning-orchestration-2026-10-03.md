# P0–P4 学习编排与资料发现增量证据

日期：2026-10-03。整体 **NOT_READY**；本报告不是10月6日成品接受记录，也不是公开GitHub真实验收。执行入口为[最终交付Goal](../implementation/STUDYPLAN_OCT6_FINAL_DELIVERY_GOAL_2026-10-03.md)，算法承载决策见[ADR-0015](../adr/ADR-0015-learning-orchestration-deadline.md)。

用户现在新增能做什么：生成的新阶段能显示为什么现在学、前次关系、本次重点、具体对比问题、贯穿实践增量和可选源码建议。刷新、退出重登录及普通草案编辑后说明仍保留。受控模板能在后续阶段复用精确知识键，保留不同学习目的和独立学习记录；调整实践或主要资料会更新新版本说明，旧版本可读。前述能力已在合成账号、Fake模型、真实隔离PG和Chrome中验证，尚未向原产品库部署。

同时保留并提交前一批有界公开GitHub发现、README/少量章节检查、私人选取、不可变来源快照和账号切换防护。其规则、Fake、PG及浏览器验证有效；本批实际公网链 NOT RUN。

## Goal、约束与实际SHA

代码SHA：`506048164261be06a166c5c9b8be4b6a556b4301`，本地分支 `feat/n1-resource-discovery`。固定参考 `cf1537040bbf8c52469e00461723f70726f5a3b2` 是祖先，基线 `3f31b182855c608bbc48fdf185204494eb4be09c`；没有 reset、master重做或覆盖用户前端/课程。此SHA尚未在远端核实，不能写成GitHub已存在提交。

允许改变：已有阶段JSONB、可选DTO、生成条件、轻量可折叠工作区、性质与回归测试。保留阶段总结、自动完成、身份/RLS/原子发布/lease/claim token/幂等、旧草案/原文/成果。Tool Calling fixture为合成验收输入，**不是公共Seed发布**。源码入口状态 suggested，文件路径为空；没有伪造源码审核、掌握结论或来源章节关系。

禁止改变：已发布迁移/Seed、原产品数据、旧unknown、付费调用、外部工程写入、自动运行外部仓库、框架迁移、语义去重或复杂画像。用户纠正DNS尚未配置，本批停止真实GitHub请求。快速模式是用户偏好；当前工具未暴露service mode切换，未声称已经切换，也没有改全局配置。

## Changed files

- Domain：`planning/guidance.py`、`planning/models.py`、`domain_packs/validation.py`，精确键复用与受控指导校验。
- Generation/Application：`planning_batches.py`、`draft_projection.py`、`plan_service.py`及原provider提示，冻结与合并受控说明；模型自行声称已学/已审核不能覆盖受控事实。
- Persistence/API：`plan_repository.py`、`practice_changes.py`、`resource_changes.py`、`schemas.py`、`views.py`，复用既有草案payload与版本structure；普通编辑保留，实践/主线更改清除过时关系。
- Frontend：`LearningGuidance.tsx`、`MainWorkspace.tsx`及局部样式，保持原UI；OpenAPI与生成TS类型同步。
- N1：GitHub安全transport/index、typed证据、预约与检查回读、0024迁移、ResourcePicker和账号缓冲防护。修复私人来源快照丢失source_version及架构边界import。
- Tests：受控Tool Calling fixture、学习指导unit/真实PG/Chrome、资源发现规则/PG/HTTP/浏览器与实践变更回归。

## Tests与证据

| 层级 | 状态 | 实际范围 |
|---|---|---|
| 规则/契约 | PASS | 最新 `pytest backend/tests/unit backend/tests/contract -m 'not postgres' --tb=short`：644通过，exit0，96.43s |
| 未运行用例 | NOT RUN | 上述2 skipped；不计入PASS |
| 真实PG、生成恢复与浏览器组合 | PASS | `STUDYPLAN_GUIDANCE_BROWSER=1 pytest test_learning_guidance_pg.py test_short_generation_pg.py`：20通过，exit0，97.03s；模型Fake |
| 实践/资源/发现PG较宽组合 | FAIL | 修复前3失败+50通过；后一次53通过+1夹具ERROR。不将整条命令改标PASS |
| 失败回归 | PASS | source_version与6–12密码夹具修复后三原失败用例通过；恢复scenario显式fixture后资源发现HTTP/PG单项通过 |
| 新实践指导PG回归 | PASS | 指导+实践组合8通过；旧验证要求RED后新要求GREEN |
| 精确知识键复用PG | PASS | 独立运行1通过；最终20组合再次覆盖。一个node、两unit、独立exposure，修改一次记录不继承到另一次 |
| Frontend | PASS | npm test 11通过；production build通过；学习指导和N1资料发现Chrome Fake脚本通过 |
| Chrome+真实HTTP+PG | PASS | 正常账号登录、当前工作区、选择Tool阶段、指导展示、刷新、退出重登录、390px；请求转发到临时自有Uvicorn/PG，未Fake业务响应；模型Fake |
| 真实模型生成 | NOT RUN | 本批新增收费请求0，不能以Fake生成替代真实模型接受 |
| 真实GitHub/Tavily | NOT RUN | 本批新增0；DNS配置未做，按用户指令推迟 |
| 静态检查 | PASS | 受影响Python Ruff、4个定向source mypy、代码diff检查、58个暂存文件凭证模式检查；无秘密匹配 |
| 文档原文 | PASS | 新Goal副本与Downloads SHA256一致：74459816f5821c9dc266e83ba0db1bd801327399a21e33c7b1a3e002f7869a2f；原文Markdown双空格保留，代码diff检查排除此文件的原文行末空格 |

本机证据在忽略目录 `var/oct6-guidance/`：`unit-contract-complete.xml`、`generation-pg-browser-final.xml`、`browser-pg.json`、`learning-guidance-real-pg.png`。JSON仅记录请求方法/路径/状态，不记录密码/凭证。原较宽FAIL记录保留，失败项按实际修复后定向结果记录，不拼接成虚构总数。

## 用量、迁移与服务

追加账保持模型 **23/50**、搜索 **4/1000**（Tavily2、旧GitHub预检1、N1 unknown1）；旧README读取2次。旧 `n1-github-20261002-01` unknown 不重派、不改写、不因新predispatch分类器而追溯认定未发送。本批新增模型/Search/内容/元数据请求均0。

0024是此功能分支的N1增量，未重写已发布迁移；学习编排新增迁移0。仓库head0024；原产品库只读核对仍0023。真实PG测试只操作自有隔离测试库，迁移0024后测试，结束删除自有库；不升级/写入产品库。原8022/5175及8024/5177已停；自有Vite5178运行，浏览器PG验收的临时Uvicorn已停。没有启动旧Worker或重派旧任务。

代理：只读事实审计请求 Luna/high，指导UI请求 Sol/high；工具未回传实际解析model/effort，记录 NOT OBSERVABLE。主协调统一公共契约/迁移/事务，至多两名业务写入者，无静态角色或新调度平台。

## Risks、Rollback、剩余门禁

当前产品库0023不能被称为已接入新N1入口；正常启用需要受控迁移/启动验证。教程正式免费正文及章节/源码映射尚未完成。思想校正版全文路径仍缺；收到后只审计差异。三个正式Blueprint、目标purpose、有限全路线重规划、真实provider生成/公共GitHub链、全闭环、Worker恢复UX、备份恢复、用户实际体验均属于剩余门禁。独立RAG缺契约仅暂停相关分支，按10月4日中午规则处理。

回滚用普通revert代码提交，保留JSONB、原版本和历史/账本；不破坏性downgrade0024或清除已产生的非空历史。可关闭GitHub入口。未完成真实外部门禁不做N1 no-ff集成；不合并master或打milestone。

下一安全动作：继续目标解析、required closure与阅读/实践前置提示的最小兼容接入；不再批量扩内容，不访问GitHub。后续真正需要公开GitHub验收时再让用户处理fake-ip-filter；缺配置不停止独立算法工作。
