# v6.3 RC-C 宽回归失败分类与确定性测试修正

日期：2026-10-04。归属：release。Goal：用户批准的 `StudyPlan_Codex_Goal_v6.3_RC_Closure.md` RC-C。

任务请求模型为 `gpt-6.1-sol / medium`；实际解析值 **NOT OBSERVABLE**。工作基线 HEAD 为 `161bacd5fa3e88c566b806697ebe52ef34cb6456`。仅修改本报告与三个既有测试文件，不改生产代码、公共契约、迁移、课程或产品环境。未读取产品 `.env`、产品库或私有正文，未调用网络或收费模型，未操作历史 Run 或批准用户计划。

## 基线和原始 RED

`var/v62/auth-rls-pg-final.xml` 与 `var/v62/baseline-auth-rls-pg.xml` 均为 61 个真实 PG/HTTP 测试，PASS 51 / FAIL 10 / NOT RUN 0。按 `(classname, test name)` 比较，失败集合相同。这只证明失败已存在，不证明它们可免责；下表每项均根据触发条件、代码契约及新隔离库证据分类。

原报告 SHA-256：

- `auth-rls-pg-final.xml`：`ca9ce141656243d683ea6d6aeeaf04d3633caed603378fcf79fa854c1e026e5d`
- `baseline-auth-rls-pg.xml`：`12f2d89a258bae62a647bef41353267827e2e0466a05f48ec28af2d06866cdce`

本轮在修改前单独重跑全部六个 B 类失败，结果 FAIL 6；日志和 XML 保留于 `var/v63/rc-c-stale-red.{log,xml}`，没有覆写历史 v6.2 artifact。其 XML SHA-256 为 `cac80065a911a356ce06596bf774f0141615efc8562467aa33e106ef193997b6`。

## 逐项分类

| # | 原失败测试 | 唯一分类 | 依据与处置 |
|---|---|---|---|
| 1 | `test_pg_migration_rls::test_all_private_tables_enable_and_force_rls` | **B STALE_TEST_OR_FIXTURE** | 旧测试把 public 中除 alembic_version 外的所有表当成私有表。0013 的 `search_usage_counter` 与 0024 的 `resource_read_usage_counter` 是部署全局预算 singleton，不含 actor、project 或用户原文；它们按正式迁移授权 SELECT/UPDATE，并有单调增量 trigger。只列出这两个明确例外，并断言列集合仍严格为预算字段；其他所有表继续 ENABLE + FORCE RLS，不放宽生产权限。 |
| 2 | `test_pg_migration_rls::test_downgrade_is_refused_when_business_data_exists` | **C UNSUPPORTED_DOWNGRADE_ONLY** | 测试先 upgrade head，再 downgrade base；在到达原早期“拒绝降级”检查前，0022→0021 因 policy 对 actor_id 的依赖而被 PG 拒绝。FAIL 是历史 destructive downgrade 路径，不是 forward upgrade 或备份恢复路径。保留原测试与 FAIL，不把任意非零返回改成 PASS。 |
| 3 | `test_pg_migration_rls::test_downgrade_succeeds_on_empty_database` | **C UNSUPPORTED_DOWNGRADE_ONLY** | 同一 head→base 逆向路径，即使空库，0022 downgrade 也先 DROP actor_id、后 DROP policy，顺序使 PG 拒绝。不得修改已发布迁移追求全绿。 |
| 4 | `test_pg_contract_alignment::test_0003_downgrade_refused_when_new_table_has_data` | **C UNSUPPORTED_DOWNGRADE_ONLY** | 名称虽为 0003，实际先 upgrade head 再 downgrade 0002；未到 0003 数据保护检查，先被 0022 的依赖拒绝。该测试不构成正常产品升级失败证据。保留原 FAIL。 |
| 5 | `test_pg_contract_alignment::test_0003_downgrade_succeeds_on_empty` | **C UNSUPPORTED_DOWNGRADE_ONLY** | 同一 0022 policy/actor_id 逆向依赖，正常 head forward + 原生 backup restore 不依赖它。保留原 FAIL。 |
| 6 | `test_pg_contract_alignment::test_domain_entity_fields_have_columns[PlanStage]` | **B STALE_TEST_OR_FIXTURE** | `learning_guidance` 是可选复合字段，正式 `plan_repository._stage_payload` 写入 draft payload / revision structure；revision 读回按 stable_key 从 structure 的 stages 回填 guidance，正规化 stage 列仍负责结构事实。矩阵改为明确 JSONB 载体映射，并检查 `plan_revisions.structure` 类型为 jsonb；不新增 migration。 |
| 7 | `test_pg_contract_alignment::test_domain_entity_fields_have_columns[ResourceRecord]` | **B STALE_TEST_OR_FIXTURE** | `discovery` 是受控私有选择证据。`PgLearningResources.select` 将完整候选 snapshot 写 `learning_resource_selections.resource_snapshot`，resource_records 只保存共享于项目内的基础地址/元数据。不能假设 discovery 必须同名落列；矩阵声明并核对真实 jsonb 载体。 |
| 8 | `test_b2v_http_end_to_end::test_full_chain_generate_edit_approve_readback` | **B STALE_TEST_OR_FIXTURE** | 当前 `merge_batches_for_validation` 用受审核 `stage_blueprints.resources/extensions` 覆盖模型纲要资源/扩展。旧 fixture 只在 Fake 模型响应声明它们，蓝图无声明，故 extensions 为空。把 fixture 的事实放入审核蓝图，保留完整编辑/确认/发布/读回断言。 |
| 9 | `test_b2v_http_end_to_end::test_draft_view_and_current_plan_agree_on_resources` | **B STALE_TEST_OR_FIXTURE** | 同一蓝图事实缺失造成 stage_resources 为空。fixture 正式声明主线来源/章节/版本，同时 DB source/section 的 reviewed 状态、checked_at 与受审核 pack 一致。保留作者章节顺序和草案/正式路线一致性断言。 |
| 10 | `test_b2v_http_end_to_end::test_missing_public_resource_degrades_explicitly` | **B STALE_TEST_OR_FIXTURE** | 缺失来源在旧模型响应声明，但蓝图为空使条目根本不存在；不是资源降级代码失效。审核蓝图加入明确缺失 source/section 引用，仍故意不入库。测试继续要求无伪造章节、显式 fallback，发布后同样降级。 |

分类计数：**A RELEASE_BLOCKER 0 / B STALE_TEST_OR_FIXTURE 6 / C UNSUPPORTED_DOWNGRADE_ONLY 4 / D OUT_OF_SCOPE_LEGACY 0**。A=0 仅限此十项失败的审计，不表示整体产品 READY，也不替代 RC-A/B、真实产品副本体验或外部契约验收。

## C 类确定性根因与回滚要求

额外在全新 `studyplan_test_v63_down_*` owned 库运行正常 `upgrade head`，结果 PASS；随后仅在该库运行 `downgrade base`，结果 FAIL，记录于 `var/v63/rc-c-downgrade-cause.log`。关键错误为：

```text
Running downgrade 0022 -> 0021
DependentObjectsStillExist: cannot drop column actor_id of table practice_submissions
policy practice_submissions_owner depends on column actor_id
```

源码证据：`backend/alembic/versions/0022_practice_submissions.py` downgrade 先删除 actor_id，后删除依赖该列的 owner policy。测试库已由 owned harness 删除；未修改迁移、不采用 DROP CASCADE、不改产品库。

正式发布/恢复规则：**forward-only migration; rollback by backup restore / code revert**。代码回退只有在旧代码兼容现 schema 时单独采用；schema/数据回退必须按 RC-B 已验证的 backup restore 路线。此报告的 synthetic owned 库 forward PASS 不替代真实产品数据副本 restore/upgrade。

## 修正范围与验证

修改：

- `backend/tests/integration/test_pg_migration_rls.py`：列出预算 singleton，并检查其字段形状；其余全表 RLS gate 保留。
- `backend/tests/integration/test_pg_contract_alignment.py`：只把两个复合字段对应到真实 JSONB 载体，保留其余每个字段的落列检查，增加载体类型核对。
- `backend/tests/e2e/test_b2v_http_end_to_end.py`：审核蓝图声明资源和扩展，source/section fixture 携带审核证据。没有移除、放宽已有资源/发布/隔离断言。

所有执行采用 `.venv\Scripts\python.exe`。`STUDYPLAN_TEST_PG_DEDICATED` 显式置空，使用安全 harness 与已有 migrator/app 角色；仅新建及删除各次测试所属临时库，不 CREATE/ALTER/DROP 全局角色。

| 检查 | 状态 | 证据 |
|---|---|---|
| 六个 B 修正前原始复现 | FAIL | `var/v63/rc-c-stale-red.{log,xml}`：6 FAIL，原断言保留 |
| 六个 B 修正后 + JSONB carrier 检查 | PASS | `var/v63/rc-c-stale-green.{log,xml}`：7 PASS |
| 最终预算 singleton 字段形状 gate | PASS | `var/v63/rc-c-global-counter-shape-green.{log,xml}`：1 PASS，exit 0 |
| 新 owned 空库正常 forward head | PASS | `var/v63/rc-c-downgrade-cause.log`：forward_exit 0 |
| 历史 destructive downgrade | FAIL | 同上：downgrade_exit 1，明确 policy 依赖；四个 C 原测试未修改 |
| 相邻 HTTP/Auth/RLS/FK/历史/JSONB 读回 | PASS | `var/v63/rc-c-adjacent-green.{log,xml}`：59 PASS，0 FAIL，0 skipped，exit 0 |
| 真实产品数据副本 backup/restore | NOT RUN | 由 RC-B 单一负责人验收，此子任务不操作产品库 |
| 外部接口/付费模型 | NOT RUN | 外部调用与付费调用均 0 |

完整非 downgrade 的相邻回归只围绕这三个改动文件，加既有 guidance PG 读回与 discovery selection snapshot 测试；四个 C 测试在此次定向命令用 `-k 'not downgrade'` 排除，不删除、不 skip/xfail，不宣称全宽套件 PASS。原 FAIL artifacts 永久保留作为 release 分类证据。

首次相邻命令因手写 discovery 测试名称错误，在收集阶段 FAIL（未运行用例），随后按源码真实名称纠正。无生产修复尝试、无业务契约修改。

最终相邻验证命令（四个 C 已按明确分类排除）：

```powershell
$env:STUDYPLAN_TEST_PG_DEDICATED=''
.venv\Scripts\python.exe -m pytest backend/tests/e2e/test_b2v_http_end_to_end.py backend/tests/integration/test_pg_migration_rls.py backend/tests/integration/test_pg_contract_alignment.py backend/tests/integration/test_learning_guidance_pg.py::test_worker_edit_publish_reload_and_relogin_preserve_guidance backend/tests/integration/test_resource_discovery_pg.py::test_inspection_reserves_once_freezes_result_and_selection_uses_evidence -k 'not downgrade' -q --junitxml=var/v63/rc-c-adjacent-green.xml
```

`git diff --check`：PASS。该命令完成后增加了预算 counter 的严格列形状断言，再独立重跑 `test_all_private_tables_enable_and_force_rls`，结果 PASS 1。其余修改仅为报告及说明文字。

## 下一步与 STOP

由主协调者整合 RC-A/B/C/D 证据，执行其余已授权门禁。此报告不允许升级原产品库、切换正式入口、跑收费模型或批准用户计划。已修六个 B；四个 C 按 forward/restore 回滚规则保留。仅发现影响 forward/restore、正常入口或 RLS/历史保护的新证据时，才升级为 A 并交单一负责人最小修复。
