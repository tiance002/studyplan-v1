# G3：自选主项目与阶段任务受控变更

本批 F10 与 F13 的实践方向变更链技术验收 PASS：用户可保留生成候选或填写自己的主项目，修订/新增阶段任务、选择知识与角色，查看完整差异，再明确确认下一版路线。专用测试项目实际从路线 2 发布为路线 3。整体 V2 Goal 仍 active / NOT_READY，负责人体验 NOT RUN，其它 F13 操作、成果验收、Outcome 和外部接口继续实施。

基线远端提交为 `6fb56dbdd81f83d76e11383ab4e3642698b9663b`，分支 `feat/v2-g1-user-slice`。24个白名单代码/测试/契约文件已正常提交并推送，代码提交 `e01b82ad47fea1db0c24e37b3f0463d18c3ace1d` 与 GitHub `ls-remote` 完全相同；develop/master 未改。未提交秘密、忽略证据或禁操作目录。

## Goal、范围与保全

复用现有 PlanPublicationService、服务端 Cookie/CSRF、actor/project scope 和同事务发布。项目正文变化时新建主项目并克隆关联任务；仅任务变化时保留主项目及未变任务，新任务使用服务端新身份，保留前身 ID/key。既有唯一约束与已发布迁移不改写；新增迁移 0021。

任务需明确标题、交付物、范围、排除范围、验收标准和当前路线中的知识关联，至少一个核心知识。新增/变更任务 pending，不继承旧验收或模型建议。预览不修改当前路线；确认才发布。私人资料必须选择 copy_active 或 keep_history_only；复制仅保留来源绑定，不表示阅读或掌握。

普通草案编辑/发布/取消不能绕过受保护的实践或资源提案。advisory 等待后重查保护标记并锁草案；提案、正文、依据、来源观察、私人绑定与回执共同核对。确认及私人资料复制同事务，异常整体回滚；旧提案可明确取消，同键同体重放，同键异体冲突。

Allowed changes 为实践 Domain/Port/Application/DB/API、0021、窄 publisher guard 与资源 helper 复用、组合根、生成契约、前端和相关测试。Non-goals：不执行外部代码、不创建通用 Proposal/MCP/Sandbox/Skills Runtime、不替代真实功能核验；没有模型或搜索调用。Rollback 使用正常增量 Git；非空新历史拒绝破坏性 downgrade。

## 四层验证与失败记录

| 层次 | 命令 / 输入 | 状态与退出码 | 实际范围 |
|---|---|---|---|
| 规则 + 真实隔离 PG | `python -m pytest backend/tests/unit/test_practice_changes_v2.py backend/tests/integration/test_practice_changes_pg.py backend/tests/integration/test_resource_changes_pg.py --tb=short` | PASS，exit 0，52 项，74.02s | 6 规则、29 新实践 PG、17 资源 PG；不是 provider 验收 |
| 真实隔离 PG 增量 | `python -m pytest backend/tests/integration/test_practice_changes_pg.py -k 'two_previews or prompt_history'` | PASS，exit 0，2 项，7.66s | 双预览只发布一次，失败者可取消与重放；旧 Prompt/导出保全。与上行去重覆盖全部 30 新 PG 用例 |
| 真实 Cookie/CSRF/HTTP + 契约 | `python -m pytest backend/tests/integration/test_practice_change_http_pg.py backend/tests/contract/test_v1_dto_contract.py -q` | PASS，exit 0，12 项 | 预览/明确确认、回执、私密 422、CSRF、跨账号拒绝、零 Run |
| 受 guard 修改影响的现有实现 | `python -m pytest backend/tests/integration/test_pg_plan_repository.py backend/tests/integration/test_planning_jobs_pg.py backend/tests/unit/test_plan_publication.py -q` | PASS，exit 0，72 项 | 正常草案/发布、队列及已有发布行为 |
| 前端 Mock | `node tests/practice-changes.browser.cjs` | PASS，exit 0 | 自选/修订/新增/角色、未知原请求重试、409/422、完整预览、旧路线原文恢复、空上下文、旧主项目/阶段明确重选 |
| 前端现有回归 | `node tests/prompts.browser.cjs` | PASS，exit 0 | 原 Prompt 功能；Gauss 最终包，不重复收费 |
| 契约/构建/规则 | OpenAPI 导出、`npm run gen:api`、`npm run build`、`npm test`、owned Ruff、scoped diff | PASS，exit 0 | 52 模块构建、4 前端规则；本接口知识角色使用生成枚举，不改旧 Prompt DTO |
| 实际浏览器 + HTTP + 保留 PG | `V2_PRACTICE_ACCEPTANCE=v2-g3-20261002-01 node tests/practice-changes-real.browser.cjs` | PASS，exit 0 | 下述手动业务验收，新增模型 0 / 搜索 0 |
| 实际保留 PG 只读核对 | `PYTHONPATH=backend python var/v2-g3/inspect_practice_acceptance.py` | PASS，exit 0 | owner RLS、确认与两个回执、旧实体正文、冻结资源内容、无未决 Run |
| 负责人产品体验 / 完整 Q01–Q12 | 尚未执行 | NOT RUN | 不将本批技术 PASS 当作全功能接受 |

早期 FAIL 如实保留：缺模块/preview stub 与保护竞态的 4 项 PG RED；新增 basis 指纹调用漏括号导致 20 FAIL/9 PASS，修复后完整 29 PASS；新竞争用例有测试表名和断言位置错误，修正后 targeted 2 PASS。Root HTTP 初次 404 RED；测试误把领域缺警告确认的 400 当成 422，修正测试后 PASS。字段类型无效仍为 sanitized 422。

前端经历入口缺失、明确 422 后 pending 不释放、TS18046、生成 role 过宽的 FAIL，均有定向修复与最终 PASS。只读复核发现项目克隆后选择器显示与保留旧目标不一致的 P2；复现后修复并测试。现有 publisher 同时生成新 stage ID，root 补充阶段重选的 RED→GREEN。旧目标、旧任务编辑与本地文字明确保留，不自动改归属。空 practice_projects 的合法 context 也已 RED→GREEN。

只读证据脚本初次误要求新旧资源 assignment/stage ID 逐字相同而 FAIL。核对现有 build_revision_snapshot 后按它明确允许的绑定 ID 重映射比较；9 个冻结资源的 source、sections、timestamps 和 view 内容保持原值，没有重新观察旧来源。没有为修正证据重发提案或重复发布。

## 实际业务验收

AcceptanceId：`v2-g3-20261002-01`。沿用隔离项目 `lpr_3b0829d7c2ce490798db5b300ae87d0a`；业务库 `studyplan_test_v2g1real_2f6ac462` 增量 0020→0021，checkpoint 库不变。仅按已核实命令路径停止自有旧 8021 listener，启动无模型 Worker、拒绝外部派发及其它业务写入的专用入口。原 8000、PG、Ollama、5175 未重启。

- 主项目自选“我自己的 Agent 调试学习工具”，第一阶段任务改为“自选交付：可检查的 Agent 调试记录”；交付物、范围和验收要求明确说明设计仍待执行。
- 主项目内容变化克隆其全部 30 个关联任务；差异可见，预览期间当前路线仍为 2，确认按钮需要明确阅读警告。用户操作确认后发布路线 3。
- 提案 `pcp_f4088a2bc95a4cd69bf14b76d3f19b4d` 已 confirmed；存储 preview/confirm 两个不可变回执。新任务 pending，新位置 Exposure 为 not_started / version 0，新 Prompt 列表为空。
- 旧主项目及 30 个旧任务正文未改。旧已保存 Summary 两版、Prompt 两版、已绑定反馈及两种已存导出，在确认后和刷新后与之前 GET 结果相同。旧路线 2 的 Exposure 观察不变；该路线实际已记录 Exposure 为 0，不能据此声称非空旧进度的浏览器验收。非空旧进度及私人资料复制/只留历史由实际隔离 PG 两种策略用例验证。
- 发布时仍在编辑的旧路线 Prompt 以只读原文和旧任务标签可见，复制后逐字保留正文。Windows 系统剪贴板将 LF 变为 CRLF，LF 归一化后相同；不声称系统剪贴板字节完全一致。
- 刷新后读取新主项目、路线 3 和旧方案历史 PASS。两张实际截图已经人工查看。没有自动把旧文字保存到新任务，没有把设计变更标为实际成果验收。

忽略的证据目录 `var/v2-g3` 包含独占 intent/preview/confirm/before 文件、`practice-real.json`、`practice-real-db-inspection.json`、`practice-real-recovery.png`、`practice-real.png`、前后端实现包。完成的脚本拒绝重跑；部分结果须先读取已知提案和当前路线，不盲目再次确认。秘密、账号密码、原文与 `.env` 不提交。

模型路由以本机会话元数据为据：root 为 gpt-6.1-sol / high；Kuhn 后端为同模型 / high；Gauss 前端及有界只读复核为同模型 / medium，均为复用会话。没有成功创建 Luna，本批不伪称使用 Luna。累计模型 23/50、搜索 2/1000、unknown 0，跨日及专用库不重置额度。

后续继续 G4 成果/证据/Outcome，以及其余 F01–F18 缺口。GitHub App 与独立 RAG 缺配置仅暂停对应实际接口，不终止整体 Goal；本批不合并 develop/master，不标 milestone，不代负责人确认验收。
