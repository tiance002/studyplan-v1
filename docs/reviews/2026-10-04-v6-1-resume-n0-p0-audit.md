# v6.1 续接 N0/P0：复用最新成果

本次用户要求读取 v6.1 Deadline Optimized Goal、只读核对后连续推进，禁止 reset。指定的 Downloads 文件当前不存在；读取仓库归档 `docs/implementation/STUDYPLAN_V6_1_DEADLINE_GOAL_2026-10-03.md`。未声称已核对已删除附件与归档的原文一致性。

实际 HEAD：`161bacd5fa3e88c566b806697ebe52ef34cb6456`。实际分支：`feat/n1-resource-discovery`。固定参考 `cf1537040bbf8c52469e00461723f70726f5a3b2` 为祖先，PASS（exit 0）。没有 reset、checkout、覆盖、历史改写或 develop/master 合并。

本次进入时三个测试文件已有 RC-C 修改，另有 RAG 状态报告未跟踪；均保留。`.workbuddy/`、`design-preview/` 仍不操作。当前 HEAD 已包含 v6.1 后续 v6.2，不能退回旧 N0 SHA 或重做已通过能力。

| v6.1 范围 | 最新实际实现 | 本次处理 |
|---|---|---|
| P1 唯一 registry | `backend/app/infrastructure/domain_pack.py::CURRENT_PACKS`；seed CLI/runtime 复用；AI2/Agent5/Cloud2/Python2，旧专项仍可地址化 | 复用；不恢复 AI1/Agent4/Cloud1 |
| P2 审核事实 | `planning_batches.merge_batches_for_validation` 确定性保护蓝图资源/扩展及 stage guidance | 复用；旧模型-only fixture 改到审核蓝图，不放宽资格 |
| P3 三方向 | 三当前包已经过 v6.2 内容门禁；Agent Recipe、已有项目优先等按私人适配生成 | 不继续扩内容或再做三份最小包 |
| P4 卡片 | `ProjectStudyCard.tsx`；`MainWorkspace.tsx` 直接按 stage_id 过滤 `plan.extensions` | 不加 DTO/API/新表 |
| P5 纯 Prompt | `frontend/src/content/projectStudyPrompt.ts::buildProjectStudyPrompt`；当前源码、clone 建议、3–8 切片、事实/推断区分、最多迁移1–2机制 | 复用；没有服务端 clone/固定 commit/file path |
| P6 静态页 | `LearningPath.tsx` 只有 DEV + previewCurriculum=1 才显示静态课程 | 正式路线继续认已发布 Plan |
| P7 代表路径 | v6.1 三方向真实 ownedPG/Chrome及v6.2六场景已有证据 | 输入不变复用；不以它们替代真实产品副本 |
| P8 release | 产品0023、repo0024；产品仅Agent1/Python1；原入口当前停止；外部RAG/真实费用/用户接受仍有门禁 | 连续推进 RC 预检、真实副本恢复、回归失败分类和体验准备 |

只读源码核对：PASS。repo Alembic head：0024，PASS（在 backend cwd 执行；首轮从 repo 根调用因相对 alembic 路径失败，未发生迁移）。正式 PlanSnapshot/PlanView extensions 与 LearningWorkspaceView.plan 既有链路保留；本轮 migration/API/DTO/Graph/worker/业务代码新增 NO。

本轮全量 unit/contract：PASS 840、NOT RUN 2，`var/v63/unit-contract.xml`（842总项、0错误/失败、exit0；两个Windows symlink权限用例）。前端：PASS13，build PASS62 modules。修正夹具后的相邻真实PG/HTTP59 PASS及严格全表RLS gate1 PASS，见 RC-C 报告；保留四项历史 downgrade FAIL。匿名真实 Chrome + 副本 API/PG smoke PASS；真实用户副本登录与历史回读 NOT RUN，不能以匿名页替代。

模型/费用：开发请求 root Sol6.1/high、独立测试修正Sol6.1/medium、RAG只读Luna/high，实际解析 NOT OBSERVABLE。无6Astra/Sol max/全局配置切换。真实付费模型/GitHub/Tavily新增0；RAG免费本机health/OpenAPI16次GET尝试。历史模型23/50、搜索6/1000、unknown1不重置/重派。

整体 NOT_READY。下一动作属于剩余 release 门禁，继续普通已授权实施；不重建课程/框架，不擅自写原产品库、切入口或跑收费模型。回滚为正常 code revert/已验证备份恢复，禁止 destructive downgrade 或 reset。
