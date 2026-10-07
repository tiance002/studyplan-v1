# Planning Legacy Removal — 2026-10-07

## 结果与边界

PLANNING_LEGACY_REMOVAL_COMPLETE / NEW_PLANNING_NOT_IMPLEMENTED / STOP。

用户现在可继续使用非规划模块和具备完整来源快照的读取/发布基础服务；新计划生成及生成式路线变更明确暂不可用。未实现替代规划器、Prompt、资料搜索或新内容结构。

来源：用户附件 `C:/Users/22088/.codex/attachments/c464ffc4-4f42-4b7c-844d-997d87497783/已粘贴的文本.txt`。这是用户明确授权的 breaking prerelease cleanup，覆盖此前保留开发期历史 Planning compatibility 的要求。

- start HEAD：8921a680fabe8f75ee5f95c231b1eca8c9273216。
- branch：feat/n1-resource-discovery；已验证参考 bd6912268cfe33f545b62105c2c7d1f829368d4e 为祖先。
- checkpoint：本地 annotated tag `checkpoint/pre-open-planning-refactor`，指向 start HEAD，未推送。
- final HEAD：保存本报告的本地提交；确切 SHA 记录在本批答复及 `var/planning-legacy-removal-20261007/final.json`，不为填写自身 SHA 再改写提交。
- migration：`alembic heads` = 0025；全部迁移字节保持。

## 完全删除的源码

- `backend/app/domain/planning/alignment.py`
- `backend/app/domain/planning/semantic_content.py`
- `backend/app/infrastructure/db/domain_pack_catalog.py`

## 删除的函数与分支

- alignment 与 semantic_content 的目标关键词、固定阶段、requested/excluded、carrier、recipe、targeted 适配决策。
- domain_pack 的 DIRECTION_PACK_FILES、select_domain_pack、runtime_pack_key_for_goal、pack_key_for_goal、unsupported_domain_pack；仅保留 CURRENT_PACKS、load_pack 和内容 fixture 仍使用的 load_python_pack。
- PgDomainPackCatalog.select(goal) 及 composition 装配。
- PlanService selector 参数/字段、_freeze_submission 目标选择和生成路径；generate/submit_generation 在 scope 校验之后直接 DependencyUnavailableError。
- PgGeneratedPlanChanges.prepare 的旧路线决策；同样在 scope 后立即拒绝，保留既有 validate/save/发布事务。
- _merge_batches_legacy、markerless merge fallback、旧 approval batch builder/interpreter。
- markerless structure、v6.11 三字段与缺 focus marker 降级；provider 的对应历史 shape 分支同步删除，无新增 Prompt。
- checkpoint executor 的历史 builder/approval finish 回调；旧协议显式拒绝，不按新协议解释。
- PlanService _finalize_run 对旧 waiting Run 的改写；正式 Plan 缺来源 snapshot 时拒绝，不再读取当前目录补旧数据。Draft 中合法待解析/用户修订的资源校验仍保留。

## 完全删除的旧测试

- `backend/tests/integration/test_direction_blueprints_pg.py`
- `backend/tests/integration/test_v61_directions_pg.py`
- `backend/tests/unit/test_direction_routing.py`
- `backend/tests/unit/test_v610_planning_alignment.py`
- `backend/tests/unit/test_v612_historical_a2.py`
- `backend/tests/unit/test_v62_semantic_planning.py`
- `frontend/tests/v61-directions-pg.browser.cjs`
- `frontend/tests/v610-planning-alignment.browser.cjs`
- `frontend/tests/v62-semantic-pg.browser.cjs`

混合文件只删除固定目标→旧路线/阶段/完整 Seed、旧 marker/approval 兼容断言。精确删除定义见 `var/planning-legacy-removal-20261007/test-removal-inventory.json`。其余 canonical、source、focus、LearningUnit、publication、CAS、RLS、idempotency 等断言保留；用显式 reviewed content / frozen submission 的 test-only fixture 解除目标路由依赖，未给公开入口增加旁路。

## 因可靠性职责保留

- frozen manifest/pack/hash、allowed canonical keys、focus authority、deterministic merge、repair2、预算、request identity、known invalid JSON repair。
- Worker claim/lease/fence/cancel、unknown/reconciliation、Run/Job/attempt/receipt ledger。
- catalog materialization、Draft/Plan domain publication、repository CAS/atomicity/idempotency、source snapshot 与稳定 candidate binding。
- 通用图/节点的 validation、relations、repair 和安全保护；当前 mixed-stage 中非 reviewed stage 的受控处理属于当前能力，不作为历史兼容误删。
- Auth/RLS/URL/来源证据/Seed 校验、Learning Assistant、Summary/Prompt正式保存、Practice Submission 未修改。
- 9 个 generated_plan_changes PG 测试及 run07/run08/batched 历史 provider fixture 的可靠性断言未删除；依赖已删除的生成准备或旧 fixture，本轮 NOT RUN，不宣称通过。后续应随新规划协议迁移这些 fixture，不恢复旧决策层。通用发布/CAS/幂等/RLS覆盖仍在 test_plan_publication、test_pg_plan_repository、B2V和short-generation suites 中。

## 验证

| 层 | 结果 | 证据/限制 |
|---|---|---|
| Python compile/import/组合根 | PASS | compileall；非规划服务装配未访问 SQL |
| API boot + generation | PASS | 真实 FastAPI TestClient，health/session/Run列表/当前Plan空态正常；未登录401、跨scope403、合法生成503 |
| 新 fail-closed边界 | PASS | 10 tests；同步/异步/route change、绑定/持久化/provider零访问、缺snapshot拒绝、旧checkpoint/marker拒绝 |
| 核心可靠性/助手/contract | PASS | 245 tests；reliability-final.xml；最终新增的read-only断言由fail-closed-final.xml复核 |
| 当前结构/canonical/outline/units | PASS | 65 tests；current-contract.log/json |
| known JSON repair/预算 | PASS | 68 tests；json-budget-final.xml；旧未冻结输入接受断言改为派发/repair前拒绝 |
| F2保护/MCP已审核来源 | PASS | 85 + 35 tests；protected-planning.xml，对应两模块无FAIL |
| backend全部collection | PASS | collection.log；不是全套运行PASS |
| frontend TypeScript/Vite build | PASS | frontend-build.log；受限环境realpath EPERM后在正常本机权限复核成功 |
| 真实Postgres/浏览器/真实provider | NOT RUN | 本Goal最小验收未操作数据库/浏览器/外部服务 |
| 旧planning semantic/direction/alignment acceptance | NOT RUN | 按用户要求不执行废弃产品合同 |

初轮检查的错误证据保留：本批新API测试误用未开放openapi URL；旧未冻结输入接受断言不再有效；当前结构fixture迁移失败。均未弱化业务保护；初轮日志/XML与最终复核并存。中止的过宽离线target无可用结果，NOT RUN，不计入PASS。

## 零副作用与不变量

- generate：0 Run、0 Job、0 provider、0 Plan修改。严格依赖spy验证在上述依赖访问前拒绝；不是PG计数查询。整个本批未连接业务库写入。
- 产品模型：新增0；账本174 request /174 result，累计174/280，余106；本批未消费余额。
- 搜索/外部RAG调用0；未读取新教材。
- 434份已审核内容、语义资料、迁移、助手源码及历史账本文件SHA保持；protected-invariants.json。
- 两保护目录仅保留原git status条目，未纳入提交；未修改已批准原型和历史证据。
- 七个指定旧符号的正式runtime/test源码引用均0；历史Markdown可保留溯源。
- 无迁移、DB reset、正式入口/Worker切换、部署、push、merge或全局配置修改。

## 后续接入边界与回滚

未来规划实现只能由下一份设计授权开始；现有 PlanService生成入口是明确关闭的接缝，CURRENT_PACKS仅代表内容资产清单。可复用已有冻结/校验、catalog materialization、Draft/Plan publication ports、模型/预算/回执/Worker基础设施，不复用已删除目标selector。

回滚依据为本地checkpoint及Git提交；本批不执行回滚、不恢复旧数据兼容。整体产品仍 STAGING_BLOCKED / NOT_READY。本轮完成后STOP。

开发路由：根协调关键权威边界请求gpt-6.1-sol/xhigh；两个独立有界worker请求gpt-6.1-sol/medium，实际解析均NOT OBSERVABLE；未修改全局配置。
