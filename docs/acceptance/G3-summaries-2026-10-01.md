# G3 总结保存与反馈增量验收

2026-10-01。Goal仍为V2全部F01–F18/G0–G6/Q01–Q12，本报告仅覆盖F09总结的第一批。整体NOT_READY；负责人实际体验NOT RUN。当前分支feat/v2-g1-user-slice，进入本批的已推送基线为891208188bb7b242ade5fda739d2aa1a881d6de1；本批代码167345827a61049450f0f35c37f0075425e4a19c已正常推送，ls-remote与本地一致。随后文档提交由实际Git记录承接，不猜其SHA。

## Goal / Constraints / Allowed changes / Non-goals

用户按两项固定问题和一项情境问题写简短总结，明确保存原文，然后自愿请求反馈。原文保存允许1–20000个Unicode码点的非空白内容，完整保留前后空白、换行与修订；保存本身不调用模型。反馈绑定选定的已保存版本，不覆盖新原文或本地编辑，不改变Exposure、单元进度或掌握。

复用现有review graph、ai_jobs、Run及Attempt账本；保留owner/project scope、RLS、同事务lease/token/cancel fence和未知结果不重派。只增量增加0018/0019及总结领域/Port/Application/adapter/API，组合根负责接线，前端复用现有学习页面。原服务、原数据库、历史Run/Draft/checkpoint/旧AcceptanceId未操作。禁止目录未编辑或提交。

Kuhn为日志核实的gpt-6.1-sol/high，负责事务/队列/模型绑定；Gauss为gpt-6.1-sol/medium，负责前端，并在停止业务编辑后进行只读后端review。root为gpt-6.1-sol/high，负责公共契约、组合根和实际验收。复用工具不支持更改模型；本批没有成功创建Luna代理，不将提示词当作路由证据。

本批不代表Prompt工作台、阶段项目、成果验收、GitHub账号连接或RAG完整交付。反馈是学习引导，不能代替实际实验或核验结论。

## Implemented / Integrated

总结API支持位置CAS、同键同体回执、同键异体冲突、最新20修订窗口、项目历史分页、旧路线原文和旧结构反馈档案。历史缺少位置/快照的数据明确标为未冻结，不改写旧行或伪造当前结论。版本头与修订窗口来自同一次SQL快照。

反馈先持久化Run/绑定/提交/队列/回执，再使用冻结模型和summary-review-v1协议执行一次评审；闭合结构校验，无自动repair。反馈、Run终态和job终态在有效claim事务内原子提交。崩溃后复用已保留的成功模型响应，取消/过期claim拒绝迟到结果；未知派发结果进入reconciliation而不重派。取消先于账本预约时没有HTTP或Attempt，预约后取消保留账本结果而拒绝业务写回。

完整学习要求和当时资料绑定留在本地不可变快照；模型输入只取原文及必要学习要求，不发送私有资料URL、备注或绑定集合。已用真实PG私有sentinel证明保留在本地且不进入provider payload。

前端显示编辑框、已保存原文、版本对应反馈和可读历史。未知保存/取消重试保留相同body/key；409、慢GET、延迟保存和迟到反馈不覆盖更新的编辑。同项目位置切换保留内存编辑，刷新前提示未保存内容；退出清除内存，不写私有原文到localStorage。反馈要求对选定保存版明确同意，切版/新保存重置同意。

## Tests / Evidence

| 层次 | 结果 | 范围与限制 |
|---|---|---|
| 规则与真实PG | PASS | 最终41项：总结unit8、总结PG17、受影响既有queue/budget16；exit0，40.71s |
| HTTP与公共契约 | PASS | 最终12项：契约9、真实PG/cookie/CSRF/HTTP3；exit0。实际组合根worker使用明确离线provider，不能冒充云模型 |
| OpenAPI/生成类型/构建 | PASS | 导出、生成客户端、tsc/Vite，48 modules；frontend4单元PASS，exit0 |
| Chrome Mock | PASS | 原文、幂等未知重试、409、慢读/保存、取消、历史、迟到反馈、终态停轮询；root合并旧反馈档案显示后最新mock exit0 |
| 真实云模型+Chrome+HTTP+PG | PASS | 新AcceptanceId v2-g3-20261001-01，单次真实反馈，刷新回读；不是负责人最终体验 |
| Ruff/diff | PASS | 后端实现者15个路径和root组合根/HTTP路径，diff检查exit0 |
| 负责人体验/全Goal/破坏性降级 | NOT RUN | 未宣称完成全Goal，未进行非空历史downgrade或原库写入 |

真实验收沿用隔离测试账号自建的Project `lpr_3b0829d7c2ce490798db5b300ae87d0a`、当前revision2，不使用原用户私有学习内容。先免费配置/DNS/冻结预算/累计回执预检PASS，再预约一项真实请求。Run `run_824fccdb1b8848b1bd9d614b1df76df0`，最终succeeded；Attempt `run_824fccdb1b8848b1bd9d614b1df76df0:summary_review:1`，SummaryReviewV1，deepseek-flash，483 input/399 output tokens，3091ms，output cap4096，unknown0。

Chrome先保存原文 `sum_17de2029849c41ea87b8c2c831fa5e36`，明确请求反馈；受控调度屏障保持原worker heartbeat/fence，再保存新版 `sum_efc3cf24e70b4067812b341da28d5adc` 并继续输入未保存文字后释放派发。模型反馈仍归第一版；新版无该反馈，未保存文字未覆盖，Exposure完整GET值未改变。刷新恢复第二版原文，选择第一版可读保留反馈，项目历史同时含两版。没有生成、搜索或资料替换POST。

累计模型**21/50**，搜索**2/1000**；本批模型1、搜索0，全部已知结果。跨库计量沿用.git/v2-paid-quota-20261001/request-01..21及对应result；新验收journal先绑定本Run再按RLS只读检查终态，独占写入metadata-only evidence，不改旧journal/evidence或重用旧ID。

持久本机证据位于var/v2-g3：summary-backend-report.md、summary-ui-report.md、provider-preflight.json、summary-real.json、summary-run-inspection.json、summary-real.png及分阶段回执。原始文本/测试账号私密文件不提交；公开验收报告只记录ID及允许的元数据。真实浏览器脚本完成报告后拒绝重复验收。

早期FAIL保留：旧50字下限、实际plan列名、pending测试job污染、dispatch前取消窗口、撤销模型后的已有绑定重读、lock-wait观察角色不足、private来源sentinel外发、前端延迟终态清理、root HTTP夹具误用不存在的actors表。均按具体原因修复并有针对性PASS，最终41及12组合覆盖当前相关输入；未将历史失败批次改记PASS。0019最后仅修正downgrade还原SQL不再引用降级后总结表，upgrade保持语义一致、Ruff PASS，破坏性降级NOT RUN。

## Rollback / 下一批

正常增量commit/push保留实现历史；有新总结/绑定时迁移拒绝破坏性降级，已保存原文/反馈和收费证据不得删除。原8000保持PID43688；专用8021现为summary_acceptance_server.py，session21096/listenerPID38980，5175前端PID41308保留。专用业务库迁移到0019，checkpoint库未写新图状态。启动脚本只允许本新验收一次派发，不可盲重启以重复收费。

继续G3主项目/阶段任务、Prompt评审和指定导出，再推进其余切片。GitHub账号授权缺App配置、RAG缺地址/契约/凭证仅阻塞对应实际调用。未合并develop/master、未创建milestone，整体保持active/NOT_READY。
