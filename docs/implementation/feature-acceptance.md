# V2.0功能与验收矩阵

整体：NOT_READY。起点develop `aa37e4b`；当前工作分支 `feat/v2-g1-user-slice`。本表保留F01–F18完整范围，Implemented不表示全部子能力完成；Verified仅来自本轮实际运行。具体范围以 [指导§4](CODEX_GUIDANCE_V2.0.md) 为准。

| ID | 功能 | 状态 | 已有事实 / 仍须交付与实证 |
|---|---|---|---|
| F01 | 注册/登录/退出/持久会话/项目管理 | IMPLEMENTED | 7项真实隔离PG认证PASS，Chrome+真实HTTP+PG退出重登录PASS；完整项目管理仍待补 |
| F02 | 目标/必要澄清/时间偏好/Outcome | IMPLEMENTED | 已有目标及prefs DTO；澄清默认值确认、Outcome还未接成品链路 |
| F03 | Blueprint/Module/依赖 | IMPLEMENTED | 有Agent/Python领域包及模型结构校验；DB运行发布版与三Blueprint完整内容待补 |
| F04 | 全阶段纲要/草案编辑/业务确认 | VERIFIED | G1真模型9阶段草案、浏览器编辑保存/独立业务发布revision1/刷新重登录PASS；仅G1已有Agent v2内容范围，三Blueprint内容由F03继续验收 |
| F05 | 主线/章节/资源角色 | IMPLEMENTED | 六角色及完整作者目录连续区间规则/实际PG PASS；稀疏索引、倒序/漏章/重复已测，浏览器Mock展示六角色PASS；已发布v2保留、新v3修正漏章。完整三Blueprint内容及负责人体验继续验收 |
| F06 | Exposure/进度/跳过/返回/历史 | IMPLEMENTED | 完整位置独立四态/CAS/幂等/不可变知识与来源快照、旧版本历史真实PG PASS；Chrome+真实HTTP+PG开始/完成/跳过/返回/刷新PASS。稳定逻辑模块身份与完整重规划链由F03/F13继续核对，负责人体验NOT RUN |
| F07 | 项目/单元/节点资料偏好覆盖 | IMPLEMENTED | 三层完整设置优先级、CAS、恢复继承保留版本、双层旧值修复PG PASS；生成冻结/搜索实际偏好接入HTTP PASS，Chrome项目/单元保存恢复刷新PASS、节点界面mock PASS。负责人体验NOT RUN |
| F08 | 真搜索/资源替换/GitHub/手动接入 | IMPLEMENTED | Tavily实际API+Chrome+PG候选选取/手动GitHub URL/刷新回读PASS，累计2/1000；受控主线差异→确认新版本→私人资料明确沿用→旧进度保留Chrome+真实HTTP+PG PASS。GitHub账号OAuth仍未接线，手动URL不代表账号连接 |
| F09 | 总结/反馈/修订/历史 | IMPLEMENTED | 原文保存/CAS/幂等/不可变修订/分页与旧版档案、单次有界反馈已接；规则+PG41及契约/HTTP12 PASS，Chrome+真实模型+HTTP+PG原文先存/反馈绑定旧版/新版与编辑保留/刷新PASS。负责人体验NOT RUN，见G3报告 |
| F10 | 主项目/阶段任务/知识/标准 | IMPLEMENTED | 候选或自选主项目、任务修订/新增、交付物/范围/验收要求及精确知识角色已接；受控预览/明确确认/取消/新身份与历史保全规则、真实PG/HTTP PASS，Chrome+保留PG自选项目/任务路线2→3 PASS。负责人体验NOT RUN，见[G3实践报告](../acceptance/G3-practice-changes-2026-10-02.md) |
| F11 | 方案/Prompt评审/修订/指定导出 | IMPLEMENTED | 明确保存/CAS/不可变修订/单次反馈/历史及指定旧版raw与实施导出已接；规则67/Prompt PG17/HTTP6/契约9及Chrome Mock PASS，真实失败保全与新真实反馈/下载/刷新PASS；Windows复制仅转换换行。负责人体验NOT RUN，见[G3 Prompt](../acceptance/G3-prompts-2026-10-01.md) |
| F12 | 成果/证据/验收/补充 | NOT_STARTED | EvidenceGrade/Verification基础存在；提交/实际验收链未接 |
| F13 | 局部修改/全路线新版本/历史 | IMPLEMENTED | 主线替换及实践方向/阶段任务受控变更已接；差异/冻结来源/新版本/CAS/幂等/旧Exposure与资料、Summary/Prompt/导出保全实际PG及Chrome PASS。其它局部操作、全路线重规划和未来成果历史仍须后续验收 |
| F14 | Outcome成果归集 | NOT_STARTED | 尚无实际任务/证据归集页面与服务 |
| F15 | Seed导入/校验/DB发布/审核边界 | IMPLEMENTED | 0011完整payload、严格校验、幂等/冲突回滚/DB目录/CLI：16规则+真实PG PASS；真生成使用发布Agent v2。三Blueprint内容及新网页审核仍待补 |
| F16 | 真模型/持久任务/取消/恢复 | IMPLEMENTED | 真云模型累计23/50请求，含G3总结1及Prompt已知失败1/成功1，unknown0；短任务、冻结绑定、锁后fence、崩溃草案/反馈复用已实测；完整用户恢复/故障UX后续验收 |
| F17 | 独立RAG真实薄集成 | BLOCKED | Port已定义；RAG_BASE_URL/RAG_API_KEY未配置，无真实检索/越权/故障证据 |
| F18 | 成品界面/启动/部署/备份恢复 | IMPLEMENTED | React/服务基础已有；本轮真实构建、完整流程、独立恢复和授权交付未完成 |

## 四层证据

规则/Fake与真实PG分别记录；G1真模型20/50，G2产品Tavily累计2/1000，新增学习控件没有外部派发。Chrome+真实HTTP+PG已PASS，详见[G1报告](../acceptance/G1-v2-user-slice-2026-10-01.md)、[G2资源报告](../acceptance/G2-resources-2026-10-01.md)及[G2学习控件报告](../acceptance/G2-learning-controls-2026-10-01.md)。RAG契约仍缺，仅阻塞相关真实调用；负责人最终体验单独确认。

本轮最新测试证据、退出码、输入版本和切片报告链接由 [progress](progress.md) 维护。状态为BLOCKED只暂停对应真实调用，不移除功能或终止其它独立实现。

## Q01–Q12门禁

| ID | 性质 | 本轮状态 / 尚缺证据 |
|---|---|---|
| Q01 | 全对象跨账号隔离、RAG私有证据 | NOT RUN：已接认证、Summary/Prompt原文/历史/导出、实践变更上下文/提案/决定及其它当前对象有真实PG/HTTP隔离PASS；未来成果/RAG及全对象矩阵仍须验证 |
| Q02 | 持久提交、断开浏览器重新打开 | PASS：G1真实PG持久提交及Chrome刷新/退出重登录；后续新模块须延续验证 |
| Q03 | 重复确认同结果、同键异体冲突 | PASS：新业务确认PG幂等/并发/冲突；不是所有未来写入接口完成 |
| Q04 | 取消/发布竞争、迟到结果、编辑竞争 | PASS：G1实际PG事务hash/version/token与锁等待至lease过期；未来重规划竞争仍须验证 |
| Q05 | 三个退出点恢复不盲目重复付费 | NOT RUN：已有实际PG短图保存后崩溃复用/unknown拒绝证据，完整真实服务退出点验收尚缺 |
| Q06 | Seed历史稳定、异体导入不半发布 | PASS：0011完整payload实际PG幂等/冲突/旧版本稳定；三Blueprint内容独立验收 |
| Q07 | 重规划历史、Exposure独立记录 | NOT RUN：G2不同位置/版本、G3实践变更保留旧Summary/Prompt/导出/Exposure及私人来源策略PG PASS，Chrome旧原文和当前新版本回读PASS；未来成果与全路线重规划仍须后续验证 |
| Q08 | 搜索/资源/RAG故障显式降级 | NOT RUN：Tavily真实成功及离线故障/未知/单元资源隔离PASS；完整真实故障矩阵和RAG契约仍缺 |
| Q09 | 合法JSON非法引用阻断 | NOT RUN：现有校验基础与新Seed目录绑定须实测 |
| Q10 | Summary/Prompt失败原文不丢、正确导出 | PASS：规则/真实PG与Chrome Mock覆盖超时/unknown、409、取消及迟到反馈保全；真实Summary反馈、Prompt HTTP400失败保全及新成功反馈/指定旧版导出/下载/刷新PASS。Windows剪贴板仅LF→CRLF，服务端/下载逐字一致；负责人体验NOT RUN |
| Q11 | 可查询status_url、终态停轮询、错误可操作 | PASS：G1实际PG status_url直接200，浏览器终态停止轮询、刷新/409保留编辑 |
| Q12 | 构建/启动/重登录/独立备份恢复 | NOT RUN：构建/隔离启动/重登录已PASS，独立备份恢复待G6 |

## 内容验收范围

初始Blueprint：Knowledge/RAG Agent、Coding Agent、Workflow/Automation Agent。已承诺Python工程入门继续保留；未审核其它领域只可成为显式未核验候选。每类用典型目标及约束冲突/资料缺失样例检查先修、全阶段、真实章节、补缺和可执行实践；不按课程数或JSON合法度宣称教学质量。
