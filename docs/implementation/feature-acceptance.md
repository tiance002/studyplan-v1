# V2.0功能与验收矩阵

整体：NOT_READY。起点develop `aa37e4b`；当前工作分支 `feat/v2-g1-user-slice`。本表保留F01–F18完整范围，Implemented不表示全部子能力完成；Verified仅来自本轮实际运行。具体范围以 [指导§4](CODEX_GUIDANCE_V2.0.md) 为准。

| ID | 功能 | 状态 | 已有事实 / 仍须交付与实证 |
|---|---|---|---|
| F01 | 注册/登录/退出/持久会话/项目管理 | IMPLEMENTED | 7项真实隔离PG认证PASS，Chrome+真实HTTP+PG退出重登录PASS；完整项目管理仍待补 |
| F02 | 目标/必要澄清/时间偏好/Outcome | IMPLEMENTED | 已有目标及prefs DTO；澄清默认值确认、Outcome还未接成品链路 |
| F03 | Blueprint/Module/依赖 | IMPLEMENTED | 有Agent/Python领域包及模型结构校验；DB运行发布版与三Blueprint完整内容待补 |
| F04 | 全阶段纲要/草案编辑/业务确认 | VERIFIED | G1真模型9阶段草案、浏览器编辑保存/独立业务发布revision1/刷新重登录PASS；仅G1已有Agent v2内容范围，三Blueprint内容由F03继续验收 |
| F05 | 主线/章节/资源角色 | IMPLEMENTED | 公共source/section/映射已有；连续区间及全部角色待验收 |
| F06 | Exposure/进度/跳过/返回/历史 | NOT_STARTED | 有UnitProgress基础，但无Exposure实际学习链路；不将读取进度当实现 |
| F07 | 项目/单元/节点资料偏好覆盖 | IMPLEMENTED | prefs基础与优先级模型已有；局部写入与不污染默认值待实现 |
| F08 | 真搜索/资源替换/GitHub/手动接入 | IMPLEMENTED | Tavily凭证已配置、真预检HTTP200/1credit PASS；产品搜索/资源选择/手动接入尚未接线，GitHub浏览器授权需求已记录，不冒称集成 |
| F09 | 总结/反馈/修订/历史 | NOT_STARTED | SummaryAttempt/Review与评审节点已有基础；用户保存/真实反馈API及界面未接 |
| F10 | 主项目/阶段任务/知识/标准 | IMPLEMENTED | 规划可产生practice基础；用户自选项目及任务完整业务链待接 |
| F11 | 方案/Prompt评审/修订/指定导出 | NOT_STARTED | 领域基础存在，Prompt工作台未接；超时/冲突原文保全和绑定导出待实证 |
| F12 | 成果/证据/验收/补充 | NOT_STARTED | EvidenceGrade/Verification基础存在；提交/实际验收链未接 |
| F13 | 局部修改/全路线新版本/历史 | NOT_STARTED | 版本/编辑/原子发布基础存在；受控操作预览、新版本、旧成果/原文保全待接 |
| F14 | Outcome成果归集 | NOT_STARTED | 尚无实际任务/证据归集页面与服务 |
| F15 | Seed导入/校验/DB发布/审核边界 | IMPLEMENTED | 0011完整payload、严格校验、幂等/冲突回滚/DB目录/CLI：16规则+真实PG PASS；真生成使用发布Agent v2。三Blueprint内容及新网页审核仍待补 |
| F16 | 真模型/持久任务/取消/恢复 | IMPLEMENTED | 真云模型20/50请求，9阶段/27必需节点/unknown0；短任务、冻结绑定、锁后fence、崩溃草案复用已实测；完整用户恢复/故障UX后续验收 |
| F17 | 独立RAG真实薄集成 | BLOCKED | Port已定义；RAG_BASE_URL/RAG_API_KEY未配置，无真实检索/越权/故障证据 |
| F18 | 成品界面/启动/部署/备份恢复 | IMPLEMENTED | React/服务基础已有；本轮真实构建、完整流程、独立恢复和授权交付未完成 |

## 四层证据

规则/Fake与真实PG分别记录；G1真模型20/50、Tavily预检1/1000、Chrome+真实HTTP+PG已PASS，详见[G1报告](../acceptance/G1-v2-user-slice-2026-10-01.md)。预检不是产品搜索集成。RAG契约仍缺，仅阻塞相关真实调用；负责人最终体验单独确认。

本轮最新测试证据、退出码、输入版本和切片报告链接由 [progress](progress.md) 维护。状态为BLOCKED只暂停对应真实调用，不移除功能或终止其它独立实现。

## Q01–Q12门禁

| ID | 性质 | 本轮状态 / 尚缺证据 |
|---|---|---|
| Q01 | 全对象跨账号隔离、RAG私有证据 | NOT RUN：认证/现有对象可定向核对，未来Summary/Prompt/RAG仍须验证 |
| Q02 | 持久提交、断开浏览器重新打开 | PASS：G1真实PG持久提交及Chrome刷新/退出重登录；后续新模块须延续验证 |
| Q03 | 重复确认同结果、同键异体冲突 | PASS：新业务确认PG幂等/并发/冲突；不是所有未来写入接口完成 |
| Q04 | 取消/发布竞争、迟到结果、编辑竞争 | PASS：G1实际PG事务hash/version/token与锁等待至lease过期；未来重规划竞争仍须验证 |
| Q05 | 三个退出点恢复不盲目重复付费 | NOT RUN：已有实际PG短图保存后崩溃复用/unknown拒绝证据，完整真实服务退出点验收尚缺 |
| Q06 | Seed历史稳定、异体导入不半发布 | PASS：0011完整payload实际PG幂等/冲突/旧版本稳定；三Blueprint内容独立验收 |
| Q07 | 重规划历史、Exposure独立记录 | NOT RUN：G2/G4完整链待接 |
| Q08 | 搜索/资源/RAG故障显式降级 | NOT RUN：Tavily真预检PASS但产品故障路径未接，RAG契约缺 |
| Q09 | 合法JSON非法引用阻断 | NOT RUN：现有校验基础与新Seed目录绑定须实测 |
| Q10 | Summary/Prompt失败原文不丢、正确导出 | NOT RUN：G3用户写入链待接 |
| Q11 | 可查询status_url、终态停轮询、错误可操作 | PASS：G1实际PG status_url直接200，浏览器终态停止轮询、刷新/409保留编辑 |
| Q12 | 构建/启动/重登录/独立备份恢复 | NOT RUN：构建/隔离启动/重登录已PASS，独立备份恢复待G6 |

## 内容验收范围

初始Blueprint：Knowledge/RAG Agent、Coding Agent、Workflow/Automation Agent。已承诺Python工程入门继续保留；未审核其它领域只可成为显式未核验候选。每类用典型目标及约束冲突/资料缺失样例检查先修、全阶段、真实章节、补缺和可执行实践；不按课程数或JSON合法度宣称教学质量。
