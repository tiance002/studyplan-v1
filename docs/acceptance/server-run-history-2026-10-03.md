# 服务端规划运行查找与恢复（2026-10-03）

用户现在新增能做什么：浏览器没有本地运行编号时，可在学习规划页显式读取本账号、本学习空间最近20条规划运行，选择一条继续查看。已成功的草案通过普通GET回读；未知结果保留核对阻塞，不重新提交生成。刷新后沿用所选编号，已有活动运行或未确认草案不会被另一条历史运行绕过。原产品数据库尚未部署此增量，整体 **NOT_READY**。

本批在 `feat/n1-resource-discovery` 续接本地 `b410c1ec46107934422a0be0bdd6a4fb0b6e4b50`，固定参考点 `cf1537040bbf8c52469e00461723f70726f5a3b2` 祖先关系PASS。实际代码SHA `7ac7cf7086b1e8b2fd25b9cbe879a1ee943c663a`；本文件只引用本地成果，未推送或核实新的远端SHA。

新增只读 `GET /api/v1/runs?project_id=...&limit=...`：默认10、最多20；按服务端会话actor及项目精确过滤，仅 `plan_generate`，创建时间及run_id倒序。复用 `RunView`，列表进度为null，所选运行通过已有详情接口读取真实业务进度。不输出graph/thread/提交清单、模型提示词或私人正文。单运行读取也核对actor匹配。端口、应用服务、PG查询、API、OpenAPI和前端类型同步，无新迁移/依赖/调度器。

页面只在用户操作后读列表，经原有 `acceptRun/loadRun` 恢复；未知状态/操作、reconciliation、queued/running/旧waiting、未处理草案保留原阻塞。列表错误可重读，不改变提交；空缓存恢复也不生成POST。账号/项目与请求序号隔离迟到响应，所选编号读取失败仍可手动GET。不把读取结果当作用户批准。

验证文件位于忽略目录 `var/oct6-guidance/`，以下真实PG均为自有 `studyplan_test_*` 隔离库；模型明确Fake，测试结束清理库与临时API/Worker。重叠回归不累计成比例，也不以Fake替代真实provider验收。

| 层次 | 状态 | 证据与边界 |
| --- | --- | --- |
| 契约 | PASS | 31项，`run-history-contract.xml`；同步导出及类型生成 |
| 真实PG/HTTP，模型Fake | PASS | 2项，`run-history-pg.xml`；数量/排序/actor/project/kind、内部字段不外露、错误额度、无身份、unknown只读无claim/dispatch |
| 正常Chrome/HTTP/Worker/真实ownedPG，模型Fake | PASS | 最终2项，`run-history-scoped-final-browser.xml`（47.667秒）、`run-history-browser-pg.json`；空缓存找回unknown和正常待确认草案、刷新、零生成POST、390px；另有生成路线变更/确认/重登录/取消草案的正常浏览器回归。此前单项PASS也保留，重复数量不相加 |
| 旧unknown生成PG回归，模型Fake | PASS | 1项，`run-history-generated-unknown-regression.xml`；旧ID不重派，新请求被阻塞 |
| 旧普通HTTP/PG链，模型Fake | PASS | 4项，`run-history-http-regression.xml`；生成/编辑/确认/回读、跨actor/project拒绝、进程重启后草案仍可处理 |
| Frontend | PASS | 11项复用（工具规则输入未变）、最终build；scope/history/generated-route/planning-recovery四个Fake Chrome最终PASS，planning-progress在5178下PASS；规则/Fake与真实服务分开 |
| 静态与文件边界 | PASS | Ruff、3入口mypy、diff；18文件凭据模式0、本地文档链接0缺失、两份V2原文hash不变 |
| 真实收费模型/Tavily/公开GitHub | NOT RUN | 本批新增请求0；GitHub额外1次搜索仍等待此前额度选择 |

先观察API缺失404与UI按钮缺失的FAIL再实现。浏览器验收早期FAIL来自测试使用了不匹配的状态文案，以及关闭context时仍有转发请求；修正定位器并在关闭前等待route收尾后PASS。progress首次未设5178而落到5173，旧generated-route及最终scope附加测试一度断言旧文案或忽略busy按钮文案，修正环境/定位器后PASS，保留失败事实，不将它们声称为产品故障。

只读审查发现详情作用域边界；在实际React组件保持挂载的Fake harness观察到旧actor/project详情覆盖新详情的FAIL后，加入scope、请求序号、卸载保护和scope重置。最终harness覆盖A→B→A旧结果、草案第二次await、旧action错误/busy不跨scope。另修复结果回读前解除accepted阻塞的窗口：草案503失败时仍保持编号/生成阻塞，手动刷新等待结果时零生成POST，读回成功后解除阻塞。不是新写操作/支付/取消协议。

最新用户决定已停止6Astra，本批仅复用请求Luna/high的UI/只读代理；实际model/effort解析NOT OBSERVABLE。主协调独占公共契约及事务边界，最多两名业务写入者。快速服务模式仍无可核实切换接口，不改全局配置、不声称切换成功。

累计产品模型23/50、搜索6/1000、旧unknown1、旧README读取2；本批模型、搜索、内容、metadata新增均0。旧账、Acceptance、unknown与历史Attempt未重置或重派。原PG5432及自有Vite5178沿用，原产品库仍未写入/迁移。

取消功能尚未完成。只读核对发现普通规划在Worker guard与provider ledger派发之间存在竞态：规划claim未加入派发事务，而摘要/Prompt已有同事务fence。下一步复用服务端claim、现有job/run/project锁与派发账本，取消先取得锁时阻止新派发；派发先记录时保留可能已发送的Attempt与核对状态。不能承诺终止已记录派发对应的HTTP请求，不将其假标cancelled或重派。需要真实PG barrier验证取消/dispatch/迟到结果两种先后顺序后再开放按钮。

其余门禁仍是三个正式Blueprint/免费正文及章节审核、真实模型与公开GitHub完整链、完整学习E2E、备份恢复和用户接受；10月3日不批量扩内容。缺外部契约只暂停相关支线。本批可普通revert撤回只读接口/UI并保留历史、运行与账本；无数据破坏性downgrade。回退前保留已存在生成路线payload的读取兼容。不执行develop no-ff/master/milestone接受。
