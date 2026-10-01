# F01注册规则与正常用户入口修复

日期：2026-10-02。代码提交：`b0e342fa9cdd948a7b4d882de8c4aa0458416afc`，已正常push且GitHub ls-remote一致；完整Goal仍NOT_READY。

## Goal / Constraints / Allowed changes / Non-goals

修复用户报告的新注册范围及注册403；定位并恢复正常数据库入口，使现有账号继续登录。最新用户要求新注册6–12码点，旧密码校验独立兼容。允许修改Domain、DTO、AuthPage、认证测试、生成契约和本地启动脚本；复用已有认证/散列/RLS，不重建账号或框架，不改私有.env，不代用户登录或批准数据，不调用模型或搜索。

## 根因与实施

旧Domain/RegistrationRequest/AuthPage按V2原默认值15–128执行，与用户最新6–12要求不符。用户5175入口连接8021的限定成果验收wrapper；实际POST register在前端代理和8021均返回403及`This owned acceptance permits only manual submissions and decisions`。

只读、带认证表scope定位用户给出的旧用户名：正常.env产品库存在该账号和一个学习项目，而验收库没有。未获取用户密码、未重置散列、未把账号复制到验收库。已将正常API启动在8022，并使5175实际代理到该服务；8021原验收服务及历史证据保持。

注册Domain/DTO/UI现在6–12；登录继续1–128。OpenAPI变化只包含RegistrationRequest的两个边界，其它路径与schema语义保持。新启动脚本显式传ApiPort/FrontendPort、代理到正确端口、只增加精确本地前端Origin且strictPort避免静默换入口；不改系统/私有环境文件。

正常本地开发库原head0010，先制作私有custom pg_dump，再应用已有0011–0022增量迁移。原41张表的原字段逐行哈希及1,513行数据升级前后完全一致，旧账号保留。未恢复旧Run、启动Worker或批准Draft。备份位于ignored `var/auth-fix/product-before-0010.dump`，含私有数据，不提交；归档可读已核对，独立恢复演练NOT RUN，不能算Q12通过。

## Tests / Evidence

| 范围 | 结果 | 证据 |
| --- | --- | --- |
| 修复前新规则回归 | FAIL | 7失败/21通过：旧策略拒绝6–12，exit1 |
| 密码/Domain定向 | PASS | 两unit文件完整53项，exit0 |
| 离线unit与contract | PASS | 591 passed，2 skipped为NOT RUN，exit0 |
| 真实PG认证/业务既有流程 | PASS | test_b3f1_access.py，9 passed，exit0；6–12注册与旧1/长密码/128码点散列登录、CSRF、跨账号拒绝、会话保留 |
| 受注册fixture影响的Worker/资源PG | PASS | 两文件45 passed，exit0，未改变隔离/预算性质断言 |
| Chrome Mock | PASS | 6/12可请求、5/13本地拒绝、Unicode、不截断、粘贴及旧密码范围；初始新6位被拦的RED为FAIL |
| 前端单元/最终生成类型构建 | PASS | 4 tests，55 modules，exit0 |
| 实际Chrome+HTTP/Vite+新隔离PG | PASS | frontend/tests/auth-real.browser.cjs；6位ASCII及12码点emoji实际注册200、刷新会话、退出和再次登录200，无Fake响应；报告及PNG在ignored var/auth-fix，PNG已查看 |
| 正常8022与用户5175代理 | PASS | 实际OpenAPI注册6–12/登录1–128；两入口5/13注册422且不回显密码，不再被验收403拦截 |
| 用户旧账号正常认证 | PASS | 正常服务实际login HTTP200；随后带认证表owner scope只读确认该旧账号在升级/启动后签发了一个新有效会话，未获取密码/token、未代用户创建会话；主观使用反馈仍NOT RUN |
| 新模型/搜索调用 | NOT RUN | 新调用0；累计仍23/50、2/1000、unknown0 |

真实Chrome初次两个注册/登录流程结束后，脚本因提示文案少匹配“无需混合特定字符”而最终FAIL；改用提示节点与6–12范围检查后完整PASS，不把初次失败改为成功。正常HTTP探测初次读错OpenAPI路径404使组合FAIL；正确路径/api/v1/openapi.json及正常代理随后PASS。备份准备初次缺本机pg_dump/pg_restore而FAIL，迁移未开始；复用既有PG16容器客户端工具后备份/迁移/原数据核对PASS，不改RAG文件或数据库。Ruff初次import排序FAIL，最小修正后PASS。

## Evidence / Rollback / Remaining

实现：[Domain](../../backend/app/domain/workspace/models.py)、[DTO](../../backend/app/api/v1/session_routes.py)、[AuthPage](../../frontend/src/features/auth/AuthPage.tsx)、[启动脚本](../../scripts/b3f1-dev.ps1)、[真实浏览器测试](../../frontend/tests/auth-real.browser.cjs)。替代规则：[ADR-0011](../adr/ADR-0011-registration-and-user-entry.md)。

代码回退通过普通revert；数据库保留增量结构及备份，不自动downgrade/覆盖恢复。用户仍可使用原账号/原密码；不要求发送密码。当前正常API无Worker，本报告只证明认证入口；计划生成与其它完整个人体验继续后续Goal，不自动派发历史或新付费任务。完整项目管理、其他功能缺口和完整交付门禁仍待完成。

实际浏览器结束后，只停止经命令/PID/端口核实的自有8023/PID51356和5176/PID44540；确认新隔离库`studyplan_test_authfix_0ffbc5ce`为0022、仅4个本轮合成账号、无Run/Draft/活动连接后，删除该唯一临时库，无强制终止其他连接。正常产品库及保留验收库不清理。
