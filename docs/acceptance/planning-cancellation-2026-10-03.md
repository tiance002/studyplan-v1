# 普通规划取消与审查输入收口

用户现在新增能做什么：普通规划排队或运行中可显式取消；响应丢失时保存运行编号和原取消请求，刷新不自动提交，可手动读回或重试同一次取消。确认取消后可明确生成新运行；可能已派发的请求保留待核对状态并阻止新生成。已在正常登录、真实HTTP/Worker/隔离PG/Chrome验证，模型Fake；原产品环境尚未部署。

本地代码SHA：`8c1595d24bb9d7f06387fdd6a498c0011da6d314`，分支 `feat/n1-resource-discovery`。本次没有推送或核实新远端SHA，没有集成develop/master或创建milestone。整体NOT_READY。

## 约束与实现

复用现有 ai_jobs/ai_runs/ai_run_events/plan_drafts，无新迁移、依赖、调度器或Graph恢复接口。POST取消采用Cookie/CSRF、服务端actor/project、严格版本号和幂等键。只接受当前SHORT协议的活动规划；旧waiting、旧协议、已完成和待核对记录不由此接口恢复或重派。

普通新派发携带服务端exact claim，在记录dispatched的同一事务复核租约。内部claim排除于语义指纹和实际provider参数，租约更换不破坏保留回执识别；成功、未知及失败回执均不产生第二次调用。旧jobless保留兼容，新SHORT jobless关闭。

取消与派发使用预算advisory→项目plan-decision advisory→Job/Run/项目行锁。取消回执、Run/Job状态、token失效与关联待确认草案取消原子提交，正文/hash保留。已发布草案拒绝取消。派发先提交时请求可能仍进入HTTP，状态保留reconciliation_required；迟到Attempt结果记录保留，不自动释放待核对运行或产生业务发布。

真实barrier发现草案先发布后Worker完成会被旧base CAS误记失败。完成事务在项目锁内核对本Run的已确认草案及匹配publication，保留成功事实；其他草案仍检查原base版本。取消先完成时旧对象发布被拒绝，发布先完成时取消被拒绝。

UI保留作用域/请求序号/卸载保护。POST503保留原body/key，恢复无自动POST；409先手动GET后再明确发起新版本请求。迟到轮询、同一挂载组件切actor/project的取消确认不能覆盖新作用域。未知及旧waiting不暴露取消/重派动作。既有UI、阶段总结及自动完成规则保留。

## 验证

| 范围 | 结果 | 输入与证据 |
|---|---|---|
| 规则/契约/发布规则 | PASS | 67项，planning-cancel-contract.xml |
| 真实owned PG/HTTP/租约/短生成/派发 | PASS | 81项，planning-cancel-final-pg.xml；provider为synthetic/MockTransport/Fake |
| 审查fixture修复及最新取消HTTP | PASS | 5项；另1个浏览器开关用例NOT RUN，learning-audit-fixtures-and-cancel-final.xml |
| 正常登录、真实HTTP/Worker/PG、Chrome取消 | PASS | 1项，planning-cancel-real-browser-final.xml；运行中取消、刷新/重登录、一次取消POST、零生成/重派POST；模型Fake |
| Fake浏览器 | PASS | 新取消专项含503原请求恢复、409、待核对、迟到轮询、卸载及实际actor/project切换；已有recovery/progress回归PASS |
| 前端 | PASS | 11项工具测试及最终build；重复数量不相加 |
| 静态与文件保护 | PASS | Ruff14文件、mypy5入口、diff；22文件凭据模式0；导入审查链接及V2原文hash |
| 真实收费模型/Tavily/GitHub | NOT RUN | 本批新增请求0 |
| 当前完整学习闭环/备份恢复/用户接受 | NOT RUN | 保留最终交付门禁 |

忽略证据目录 `var/oct6-guidance/`：各XML、planning-dispatch-evidence.md、planning-dispatch-green.log、planning-cancel-real-pg.json/png。子代理最终派发专项28项PASS、summary/legacy/model-settings19项PASS及MockHTTP完整19请求图1项PASS；与上表重叠不合计。

初始FAIL均保留：取消方法/HTTP入口缺失、派发21个反例、旧jobless协议兼容、发布先完成误记失败；修复后定向PASS。测试观察/夹具FAIL包括owned清理遗漏Attempt、pg_stat_activity权限观察、超长注册密码、冷库不必要生成前置、浏览器定位器匹配运行与历史两处文本、末尾空行；修正后对应门禁PASS。真实外部接口没有用Fake结果替代。

## 外部会话审查

用户转交的[闭环审查](../reviews/2026-10-03-learning-loop-audit.md)与[三个Blueprint候选](../reviews/2026-10-03-blueprint-candidates.md)完整保存为读取时的输入，不冒充当前冻结验收。

闭环审查两项失效测试已真实RED复现：新用户测试使用超12码点密码；非空降级保护测试把head固定0023。修复为合法Unicode注册/登录及保护前后版本一致，ownedPG定向PASS。旧summaries-real浏览器绑定已完成Acceptance与旧单元控件，保持历史，不重跑；当前阶段总结要走新验收入口。

三个候选仍未审核/发布/导入。后续分别设置必修闭包与贯穿项目，不把RAG/MCP强加到Coding/Workflow；修正Python作者章节顺序，在新内容版本补学习指导及免费正文证据，保留已发布旧版本。Coding文件修改安全和Workflow审批/副作用教材尚缺证据。

## 用量、运行归属与回滚

产品模型累计23/50、搜索6/1000、unknown1、旧README读取2不变；新增外部模型/搜索/内容/metadata为0，不重置旧账或重派unknown。派发难题子代理请求Sol/xhigh，UI请求Sol/medium，实际解析NOT OBSERVABLE；Luna全部可用档位仍获授权，Sol/max与6Astra不使用。快速模式请求仍已结束，工具无服务模式切换证据，不改全局配置。

仓库head0024、原产品库0023沿用；仅owned测试库迁移/写入并清理。临时API/Worker已结束；自有Vite5178重新启动，session84785、PID57788已核实StudyPlan路径，原PG5432不变。未把前端预览表述为正式账号环境已上线。

回滚采用普通revert本批代码，保留Attempt、取消回执、草案与原文历史，不降级数据库、不恢复已取消Job。回滚到缺少派发保护的版本前停止相应Worker，避免取消记录被旧执行路径使用。既有路线payload读取兼容继续保留。

下一安全动作：落实三个内容候选的新JSON/依赖/免费教材审核，并在新普通账号、新owned环境运行当前阶段总结及成果的E1–E5浏览器闭环；真实模型代表路径仍等待对应明确授权。额外GitHub一次搜索仍只等待此前额度选择，不阻塞其它工作。完整门禁与用户接受前保持NOT_READY。
