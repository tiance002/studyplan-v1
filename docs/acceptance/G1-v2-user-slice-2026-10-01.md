# G1：真实生成、业务确认与重登录回读

2026-10-01，整体V2仍NOT_READY。用户现在可注册/登录、提交持久202任务，用现有部署模型生成全阶段草案，编辑保存、确认发布并重登录读回。此报告仅验证G1技术纵向链；完整学习闭环和负责人实际体验尚未验收。

## Goal、约束、变更

Goal：新用户→DB Seed→202异步→真模型→编辑→业务发布→PG版本→浏览器回读。起点develop aa37e4bfa33a41aadb4cb689557e2c7d491d550f，工作分支feat/v2-g1-user-slice；代码本地提交be802e27dfa131ee232d07d40d9650dbd9d5ac21，推送结果由[检查点](../implementation/progress.md)登记。

Allowed changes：现有backend/frontend/contracts、受控Seed、增量迁移与必要测试。保留RLS、服务端scope、lease/token、取消与迟到防护、幂等及原文历史。未改历史迁移/全局PG角色/用户服务/原业务库，未处理旧Acceptance09、unknown或waiting_user。

变更：新密码15–128 Unicode码点/旧验证兼容；0011发布完整Seed payload、严格校验/幂等/回滚；0012窄原子领取、新用户无需白名单；部署模型冻结绑定；short-v2保存草案后END，确认走业务事务；事务内版本/hash/token/owner和锁后时钟防护、崩溃复用草案；前端按草案状态编辑、停止终态轮询、保留输入。

Non-goals：Exposure、完整项目管理、三Blueprint内容验收、总结/Prompt/成果、RAG、通用MCP/沙箱、公网部署。自动化不批准负责人或任何历史草案。

## Tests与Evidence

环境Windows/Python3.13.14/Node24.18.0/npm11.16.0，现有PG5432及安全pg_harness；业务写入只在本轮studyplan_test_*隔离库。以下PASS均exit0；FAIL不改写为PASS，后续修正单独记录。

| 验证 | 状态 | 范围 |
|---|---|---|
| .venv/Scripts/python.exe -m pytest backend/tests/unit backend/tests/contract -m 'not postgres' | PASS | 最终453通过，2 skipped为NOT RUN；契约重新导出后运行 |
| pytest backend/tests/e2e/test_b3f1_access.py（同一venv） | PASS | 7真实PG认证/归属/会话 |
| pytest backend/tests/unit/test_seed_validation_v2.py backend/tests/integration/test_seed_catalog_v2_pg.py | PASS | 16规则+实际PG；同版本幂等/冲突回滚/旧payload保留 |
| pytest backend/tests/integration/test_worker_admission_pg.py backend/tests/integration/test_planning_jobs_pg.py --tb=short | PASS | 47实际PG，含四种锁等待至lease过期后拒绝；语义RED为FAIL、8项 |
| 短生成较宽定向组合 | FAIL | 112通过/1旧publication异常类型失败，原命令见本机short-generation-report.md/tests.log |
| 原失败及并发批准/取消/基础版本4项修正复查 | PASS | 4通过、27.69s；short-generation-final-recheck.log，不冒称全组合重跑 |
| pytest backend/tests/integration/test_v2_user_slice_pg.py | PASS | 1实际PG业务链，provider明确Fake，不能代替云模型 |
| backend Ruff、git diff --check | PASS | 本轮输入；原文保留合法Markdown空格 |
| frontend npm test、npm run build | PASS | 4单元，TypeScript+Vite真实构建 |
| auth/progress/short-generation浏览器脚本 | PASS | 显式mock API；密码/轮询/opaque ID/编辑保全 |
| 新AcceptanceId真模型生成 | PASS | 20实际派发、20有结果、0unknown，9阶段/27必需节点 |
| Chrome+真实HTTP+PG | PASS | 编辑保存/发布revision1/重登录，未再消耗模型 |
| Tavily真预检 | PASS | HTTP200，1请求/1credit，产品搜索集成尚NOT RUN |
| 负责人体验、完整学习闭环、备份恢复、真RAG | NOT RUN | 后续G2–G6及外部条件 |

## 真实调用与恢复

AcceptanceId v2-g1-20261001-01，Project lpr_3b0829d7c2ce490798db5b300ae87d0a，Run run_5abb9605a32b40e3ba243fe2cda8e279。DeepSeek Flash、部署cap8000，outline/practice4096、structure/repair8000；20请求含1repair，usage输入31545/output15144。

浏览器首轮发布完成后因退出按钮accessible name失败，新增aria-label；第二轮续接因测试提前判断失败，改等实际草案标题。最终从保留revision1续测PASS（resumed_retained_publication=true），没有重新生成/付费。仅自动化新专用账号的新草案发布，未冒用负责人。

本机证据在var/v2-g1：v2-g1-20261001-01-report.json、-browser.json、-published.png及三代理报告；秘密账号文件不得打印/提交。计量在.git/v2-paid-quota-20261001，journal在.git/b3f2-controlled-live/v2-g1-20261001-01*.json；禁止同ID重派。Tavily request_id 94d2c6ec-e063-4bbb-894b-70068548402b，仅公开查询/未审核候选。累计模型20/50、搜索1/1000，后续不重置。

## Rollback与余项

普通revert保留数据/增量迁移，不默认downgrade；0011存在payload时拒绝破坏性降级。保留short-v2 checkpoint解释器，不按旧图重读。专用库暂保留：studyplan_test_v2g1real_2f6ac462、studyplan_test_v2g1cp_e6270f82。

完整项目管理/Outcome、稳定知识逻辑身份、三Blueprint、Exposure/偏好/搜索/连接、总结/Prompt/成果/历史及备份恢复继续交付。规则、真实PG、真实外部、浏览器证据分开；总测试数不替代教学质量或成品验收。
