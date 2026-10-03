当前这条完整学习闭环的验收结果为 **NOT RUN**。已有历史证据证明了若干独立切片，但不能证明当前工作区已通过整条链路。本次还确认了 **3 处测试或验收脚本与当前输入不一致的问题**；没有修改或修复文件。

审查起止 HEAD 均为 `dddda03b961ef18ff848daec5235195b93ded431`，分支为 `feat/n1-resource-discovery`。期间工作区仍有其他会话写入，涉及共享路由、DTO、计划服务及生成契约；因此本报告针对读取时的源码和保留证据，不是冻结构建的验收。本次没有运行测试、启动服务、操作数据库、联网、调用收费服务、切换分支或提交，也没有进入两个禁止目录。取消、派发、租约和发布竞态的未完成修改未作评价。

模型请求参数记录为 `gpt-6.1-sol/high`；主会话实际解析值为 **NOT OBSERVABLE**，未请求切换或派发额外代理。

**测试与有效证据映射。** 下表的历史结果只适用于报告所记录的输入；当前执行结果统一为 **NOT RUN**。

| 环节 | 具体测试文件与测试名 | 已有证据及实际覆盖 |
|---|---|---|
| 正常注册、登录、退出、持久会话 | [test_b3f1_access.py](D:/studyplan/backend/tests/e2e/test_b3f1_access.py:31)：`test_browser_registration_persistence_csrf_logout_and_isolation`；`test_registration_code_points_and_existing_hash_login`。浏览器：[auth-real.browser.cjs](D:/studyplan/frontend/tests/auth-real.browser.cjs) | [注册入口报告](D:/studyplan/docs/acceptance/F01-registration-entry-2026-10-02.md)记录真实 PG 认证 9 项 **PASS**；[auth-real.json](D:/studyplan/var/auth-fix/auth-real.json)记录真实 Chrome/HTTP/PG **PASS**，覆盖 6 位及 12 码点注册、刷新、退出、再次登录。长旧密码兼容由 PG 测试覆盖。 |
| 生成并持久化草案 | [test_short_generation_pg.py](D:/studyplan/backend/tests/integration/test_short_generation_pg.py:83)：`test_draft_success_has_no_interrupt_and_approval_preserves_run_result`；[test_v2_user_slice_pg.py](D:/studyplan/backend/tests/integration/test_v2_user_slice_pg.py:21)：`test_new_user_requires_no_actor_whitelist_and_status_url_survives_relogin` | [G1 报告](D:/studyplan/docs/acceptance/G1-v2-user-slice-2026-10-01.md)及[原始结果](D:/studyplan/var/v2-g1/v2-g1-20261001-01-report.json)：真实模型历史 **PASS**，20 请求、20 成功、0 未决，生成 9 阶段。PG 测试中的模型明确为 Fake。新用户纵向测试目前存在下述密码夹具缺陷。 |
| 草案编辑、明确确认 | [test_b3f1_access.py](D:/studyplan/backend/tests/e2e/test_b3f1_access.py:161)：`test_real_plan_workspace_edit_publish_refresh`；[test_learning_guidance_pg.py](D:/studyplan/backend/tests/integration/test_learning_guidance_pg.py:25)：`test_worker_edit_publish_reload_and_relogin_preserve_guidance` | [G1 浏览器结果](D:/studyplan/var/v2-g1/v2-g1-20261001-01-browser.json)为历史 **PASS**：编辑保存、发布、重登录回读。后续指导 PG 测试覆盖编辑/确认后指导保留；[generation-pg-browser-final.xml](D:/studyplan/var/oct6-guidance/generation-pg-browser-final.xml)记录 20 项、0 失败、0 错误，模型 Fake。 |
| 学习工作区、阶段导航与指导 | 上述 `test_real_plan_workspace_edit_publish_refresh`；[learning-guidance-pg.browser.cjs](D:/studyplan/frontend/tests/learning-guidance-pg.browser.cjs) | [P0–P4 报告](D:/studyplan/docs/acceptance/P0-P4-learning-orchestration-2026-10-03.md)及[browser-pg.json](D:/studyplan/var/oct6-guidance/browser-pg.json)记录真实 HTTP/隔离 PG/Chrome 历史 **PASS**：正常登录、指导展示、刷新、退出重登录、窄屏。浏览器读取真实业务响应，生成模型为 Fake；没有串联总结和成果写入。 |
| 阶段总结原文、修订及历史 | [test_stage_summaries_pg.py](D:/studyplan/backend/tests/integration/test_stage_summaries_pg.py:24)：`test_stage_exact_save_scope_snapshot_cas_receipt_and_no_progress`；`test_stage_and_unit_history_coexist_and_owner_or_foreign_stage_denied`；`test_stage_http_omitted_unit_is_stage_scope`。隔离 HTTP：[test_summary_http_pg.py](D:/studyplan/backend/tests/integration/test_summary_http_pg.py:62)：`test_cross_account_summary_and_history_http` | [学习工作台报告](D:/studyplan/docs/acceptance/frontend-learning-revision-2026-10-02.md)记录阶段总结 PG/HTTP 历史 **PASS**，覆盖精确原文、阶段快照、CAS、回执、旧单元历史及归属拒绝。[summary-real.json](D:/studyplan/var/v2-g3/summary-real.json)记录真实模型反馈和原文保留 **PASS**，但属于改版前的**单元总结**，不能替代当前阶段总结浏览器验收。 |
| 实践成果提交、补充、人工验收 | [test_practice_submissions_pg.py](D:/studyplan/backend/tests/integration/test_practice_submissions_pg.py:72)：`test_raw_save_and_user_acceptance_are_immutable_and_do_not_verify_learning`；`test_accepted_supplement_preserves_task_status_and_each_original`。HTTP：[test_submission_http_pg.py](D:/studyplan/backend/tests/integration/test_submission_http_pg.py:51)：`test_manual_decision_requires_saved_criteria_and_retains_originals` | [G4 报告](D:/studyplan/docs/acceptance/G4-submissions-outcomes-2026-10-02.md)记录 PG 30 项、HTTP 4 项历史 **PASS**。[submission-real.json](D:/studyplan/var/v2-g4/submission-real.json)记录真实 Chrome/HTTP/PG **PASS**：说明不足→要求补证据→关联补充→逐项覆盖与明确确认→USER accepted。没有平台执行或独立来源核验。 |
| 阶段自动完成 | [test_stage_completion.py](D:/studyplan/backend/tests/unit/test_stage_completion.py:16)：`test_stage_completion_requires_summary_and_all_present_accepted_tasks`；[test_stage_completion_pg.py](D:/studyplan/backend/tests/integration/test_stage_completion_pg.py:52)：`test_http_summary_and_manual_acceptance_automatically_complete_stage`；`test_summary_only_stage_completes_http`；`test_same_task_global_accepted_does_not_complete_new_plan_position` | 学习工作台报告记录规则及 PG/HTTP 历史 **PASS**。核对断言确实覆盖同 plan/stage 总结、人工 accepted、无实践阶段、旧路线不继承、排除单元总结及仅保存证据。浏览器真实写入后的自动刷新 **NOT RUN**；报告明确说明该流程未执行。 |
| 刷新、重登录、历史读回 | [test_stage_summaries_pg.py](D:/studyplan/backend/tests/integration/test_stage_summaries_pg.py:108)：`test_empty_stage_valid_new_plan_preserves_old_history_and_cas`；[test_practice_submissions_pg.py](D:/studyplan/backend/tests/integration/test_practice_submissions_pg.py:350)：`test_old_plan_archive_and_receipts_remain_after_real_practice_replacement`；`test_archive_pagination_thread_window_and_legacy_are_truthful` | G1 有路线重登录历史 **PASS**；G3 有原文及反馈刷新历史 **PASS**；G4 有成果、决定和档案刷新历史 **PASS**。它们跨不同时间、路线版本和验收入口，不能拼成当前普通入口的整条 **PASS**。 |

四层证据的结论分别是：

| 层次 | 保留证据 | 当前输入 |
|---|---|---|
| 规则/Fake | 所读 [unit-contract-complete.xml](D:/studyplan/var/oct6-guidance/unit-contract-complete.xml)记录 646 项、0 失败、0 错误，其中 644 项 **PASS**、2 项 **NOT RUN**；含阶段总结、完成规则、成果规则 | **NOT RUN** |
| 真实 PG/HTTP | 各切片有历史 **PASS**，覆盖持久化、归属、历史和完成投影 | **NOT RUN** |
| 真实外部模型 | G1 生成及 G3 旧总结反馈有历史 **PASS**；当前规划契约及阶段总结的真实模型验证不能由其替代 | **NOT RUN** |
| 浏览器 | 认证、编辑确认、指导读取、旧总结反馈、成果验收各有历史 **PASS**；部分脚本拦截 API，属于 Fake 浏览器证据 | 完整当前闭环 **NOT RUN** |

**输入变化与明确缺口。**

已通过本地 Git 差异确认：G1 之后生成器、计划服务、计划持久化、provider、PlanningPage 和目标/指导契约发生变化；G3 之后总结 Domain/Application/DB/API/UI 改为阶段总结；阶段改版之后共享组合根、计划投影、前端入口及迁移 head 又有变化。另一方面，阶段完成规则、工作区完成查询、阶段完成 PG 测试、SummaryPage 和 SubmissionPanel 相对阶段改版提交没有差异，成果核心实现相对 G4 提交也没有差异。**核心文件未变只能支持保留局部历史证据，不能证明其当前依赖、接线、环境和整链执行已通过。**

必须补齐的证据为：

- 同一个新普通账号、同一个项目和路线，从生成走到阶段完成，再刷新、退出重登录并读回历史的浏览器链。
- 当前阶段总结的真实保存、修订及可选模型反馈；旧真实脚本验证的是单元总结。
- 总结保存或最后一项实践验收成功后，页面自动刷新完成状态；还需证明刷新失败不会把已成功保存误报为失败。
- 当前普通入口中“全部实践”门槛的浏览器验证，以及无实践阶段的总结单独完成路径。
- 当前全链对象的跨账号浏览器检查。现有 HTTP/PG 拒绝测试较完整，但没有同一完整场景的统一证据。
- 当前输入版本的可追溯执行记录：代码 SHA、相关工作区输入、迁移/Seed 版本、环境及各层结果。旧 G1/G3/G4 记录不能冒充这份记录。

**确认的验收资产缺陷。** 以下均由源码直接核对，执行结果仍为 **NOT RUN**，不冒称已观察到 pytest 或浏览器运行失败。

| 位置 | 触发条件与问题 | 影响 |
|---|---|---|
| [test_v2_user_slice_pg.py:28](D:/studyplan/backend/tests/integration/test_v2_user_slice_pg.py:28)，另见第 77 行 | 运行 `test_new_user_requires_no_actor_whitelist_and_status_url_survives_relogin`。首个密码为 `"我的学习口令😀" * 3`，共 21 码点；第二账号密码也超过 12。当前 [注册 DTO](D:/studyplan/backend/app/api/v1/session_routes.py:18)上限为 12，测试却断言注册 200。 | 首次注册会被当前输入校验拒绝，测试无法进入生成、确认、重登录及跨账号检查。 |
| [test_practice_submissions_pg.py:550](D:/studyplan/backend/tests/integration/test_practice_submissions_pg.py:550) | 运行 `test_nonempty_downgrade_guard_refuses_before_any_destructive_statement`。测试断言迁移版本为 `0023`，但其 [migrated_db 夹具](D:/studyplan/backend/tests/e2e/test_b2v_http_end_to_end.py:100)执行 `upgrade head`；当前迁移已包含 [0024](D:/studyplan/backend/alembic/versions/0024_resource_discovery.py:4)。 | 即使降级拒绝和成果保全都正确，最后固定版本断言仍不符合当前输入，不能沿用旧整套 PG 的 **PASS**。 |
| [summaries-real.browser.cjs:37](D:/studyplan/frontend/tests/summaries-real.browser.cjs:37)及第 38 行 | 旧脚本选择“总结所属学习单元”，并构造含 `unit_id` 的总结查询；当前 [SummaryPage](D:/studyplan/frontend/src/features/learning/SummaryPage.tsx:76)生成阶段目标，界面已移除该控件。 | 旧脚本无法直接验证当前阶段总结；旧真实反馈 **PASS** 的范围仍是旧单元总结。此外它绑定已完成 Acceptance 并拒绝重跑，不能直接当新验收入口。 |

本次没有获得可运行复现的业务缺陷证据，也没有据此断言业务代码不存在缺陷。

**最少补验收用例：五组，均为 NOT RUN。** 以下是交付给实施/验收会话的操作规范，本次未执行。使用独立验收环境、新账号 A/B 和新验收编号；普通产品认证与业务接口必须真实，API 成功响应不得用 Mock 替代。第一组承担当前真实模型代表路径，其执行需要另有明确授权。

| 用例 | 操作 | 预期结果与保留要求 |
|---|---|---|
| **E1：普通账号完整主链** | A 注册、退出再登录；输入目标并生成；取得草案后修改一个阶段标题/目标，保存并明确确认；进入工作区。保存阶段总结两版。实践先提交不足说明、记录补证据，再保存关联补充，逐项填写观察并明确人工通过。完成该阶段全部实践。 | 注册/登录成功；草案生成结束为 `succeeded + none`，确认前没有正式路线；确认后的路线与编辑内容一致。总结及成果精确保留空白、换行和 Unicode，旧版本及决定不可变。只有满足同位置总结与全部 USER accepted 实践时阶段完成。保存和人工验收不触发模型，人工通过不升级知识 VERIFIED。记录所有对象 ID、版本、内容哈希和外部调用数。 |
| **E2：阶段门槛与位置隔离** | 在独立受控验收路线准备“两项实践阶段”和“无实践阶段”。依次检查：仅总结、仅全部实践、总结加一项实践、总结加全部实践；无实践阶段保存非空总结。再检查旧单元总结、另一阶段成果和旧路线 accepted。 | 前三种不足组合保持未完成，完整组合完成；无实践阶段仅非空阶段总结即可完成。空白总结被拒绝；旧单元、别阶段、旧路线记录不贡献当前完成。全部原记录继续可读，不产生人工通关记录或错误继承。 |
| **E3：刷新、重登录及历史读回** | 复用 E1 已保存数据，逐页刷新、关闭浏览器后重新打开、退出再登录；读取两版总结、初始成果、补充成果、人工决定和 Outcome。若需验证旧路线历史，顺序创建新路线后再读取旧记录，不做竞态操作。 | 对象 ID、原文哈希、冻结任务标准和来源版本保持一致；完成投影一致；读取及重登录不触发生成或反馈 POST。新路线不继承旧阶段完成，旧记录仍可定位。未保存文字按页面提示处理，不能要求它在整页刷新后自动恢复。 |
| **E4：保存成功后读取失败、冲突保全** | 浏览器只对指定后续 GET 注入一次 503；另一次让真实保存成功后响应不可见，再核对原请求；用第二页面制造总结或成果版本冲突。 | 页面区分“已保存但刷新失败”和“保存失败”；保留编辑及已知回执，不要求新键重复提交。未知保存用原 body/key 核对，记录不重复；409 保留本地文字，读取最新记录后可明确重试。恢复读取后阶段状态正确，外部调用数不增加。 |
| **E5：跨账号统一拒绝** | B 正常登录并使用 B 的有效 CSRF。对 A 的 project、Run/status URL、Draft、workspace、总结详情/历史、成果详情/历史、Outcome 发 GET；尝试编辑/确认草案、保存总结、提交成果、人工决定及回放 A 的回执。再以 B 自己的 project 参数配 A 的对象 ID 检查。 | 指定 A 项目时拒绝 403；混用对象 ID 按契约返回 403/404，不泄漏正文、标题或快照。B 页面和缓存不显示 A 的私有内容。所有拒绝操作不增加 A 的记录、版本、决定、任务或外部调用；A 随后登录仍能完整读回 E1 数据。 |

这五组覆盖本次限定链路及其必要的数据保留和账号隔离边界；取消、派发、租约和发布竞争继续由主会话负责，不在本报告中重新判定。
