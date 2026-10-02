# 学习工作台改版与阶段总结验证

日期：2026-10-02。分支：`feat/v2-g1-user-slice`，延续既有 V2 Goal。本轮完成已批准的前端改版、阶段总结、资料浮窗及自动阶段进度增量，完整产品仍 NOT_READY；没有 develop/master 合并或 milestone 接受。

## 用户决定及范围

用户已接受浅色 HTML 审阅稿，要求落实正式前端并考虑附件中的教学反馈。后续明确取消退出条件、4/5 通关和每天总结；总结以整个学习阶段为单位。此决定见 [ADR-0012](../adr/ADR-0012-stage-summaries-and-learning-workspace.md)。实施边界见[本轮计划](../implementation/frontend-learning-revision-plan-2026-10-02.md)。

浅蓝主色、较轻分隔与紧凑的阶段内知识节点替代旧视觉。阶段默认折叠，展开参加正常文档布局。最新用户决定见 [ADR-0013](../adr/ADR-0013-automatic-stage-progress-and-resource-dialogs.md)：只展示自动计算的已完成/未完成及完成阶段数，移除手动进度表单、单元和知识节点学习状态。阶段选择同步总结和实践，已展开阶段的子项导航绑定所属阶段及具体任务；保留按位置的未保存编辑缓冲。

“替换本阶段主线 / 资料偏好 / 补充本单元资料”分别以按钮打开原生模态浮窗。原业务组件保持挂载，关闭重开保留未保存输入与待处理请求；阶段及单元切换仍按位置隔离。Escape/关闭返回触发按钮，正文可滚动，390px窄屏不溢出。

资料展示来源与阅读章节范围，工作区展示已有先修和实践要求。未核验候选不标记已阅读或已掌握。实践保留既有任务和成果验收，不新增阶段通关规则。

路线页顶部提供“当前正式路线 / 课程改进建议”。建议包括最小 Agent/Eval-Lite，RAG 与 Workflow 两条目标相关分支，Eval/Reward → Agentic RL 基础 → 高级评估。完整 RL 训练为可选进阶，高级评估只依赖 Eval 基础。细化 success rate、deterministic grader/LLM judge、trace、reward、RLVR、PPO/GRPO 直觉、长轨迹归因、稀疏奖励、失败分类、泛化、消融、费用与质量、安全及 reward hacking，给出可执行的练习产物。

**课程建议尚未发布为数据库课程版本。** 本轮没有新 Seed 导入或新私人路线批准；当前正式路线仍按原批准版本展示，其九阶段与历史资料不被静默替换。正式课程发布与私人重规划仍需既有受控版本和确认事务；不能把建议视图当生成引擎已采用新课程的证据。

## 真正的阶段总结

Summary API 保持原路径，省略/null `unit_id` 表示阶段总结，显式字符串继续旧单元调用与哈希。0023 增量迁移引入独立阶段版本头及 owner FORCE RLS、复合 FK/约束/唯一位置版本；不重写旧迁移。

保存冻结整个阶段的目标、全部单元及完整 rubric、节点、分配资料与来源。保持项目锁、CAS、幂等回执、原文不可变、历史版本与归属；保存不写旧 Exposure/UnitProgress/知识核验或触发模型。旧单元历史原位置保留。有阶段历史时 migration downgrade 明确拒绝破坏性降级。

新增只读阶段完成投影：同一 project/plan/stage 的最新非空阶段总结，加该阶段全部给定实践任务的现有 USER accepted 成果记录，满足时为已完成；无实践任务只要求总结，其余为未完成。旧单元总结、旧路线/别的阶段验收、任务全局状态、Prompt/方案保存、AI建议及仅提交成果都不能替代。此投影没有新增 migration/手动通关步骤，也不把学习状态提升为知识 VERIFIED。总结成功保存及实践完成后前端刷新工作区；刷新失败单独提示，不把已经成功的保存标为失败或要求重试原保存。

## 验证与证据

| 层次 | 状态 | 命令/实际观察与范围 |
|---|---|---|
| 规则/Fake/契约 | PASS | 根最终 `.venv/Scripts/python.exe -m pytest backend/tests/unit backend/tests/contract -q` exit 0；605 PASS，2 skipped 为 NOT RUN；含新阶段总结及阶段完成规则。最终 OpenAPI 导出及前端类型生成 exit 0。 |
| 前端规则 | PASS | 根最终 `npm --prefix frontend test` exit 0；11项 PASS，覆盖阶段展开、路由、具体任务一次性意图和阶段统计。 |
| 前端构建 | PASS | `npm --prefix frontend run build`，TypeScript/Vite exit 0，57 modules；未增加依赖。 |
| 真实 PG / HTTP | PASS | 实施者最终定向 suite exit 0：新阶段 unit7、旧 unit8、新阶段 PG9、旧总结 PG17、HTTP PG3、共享资源变更 PG17，共61项 PASS。隔离测试库，覆盖 RLS、历史/CAS/幂等、nullable 契约、空阶段、完整 dict rubric 和有历史时降级拒绝。 |
| 自动阶段进度 / 真实 PG与HTTP回归 | PASS | 最终定向 suite exit 0：新阶段完成规则7、阶段完成 PG/HTTP7、学习 controls HTTP1、成果 PG30、成果 HTTP4，共49项 PASS。覆盖总结/部分/全部实践、无实践、旧单元总结排除、跨路线及阶段隔离、owner RLS、Unicode空白、真实保存与成果accepted后的GET变化、有界版本头查询。此行与前行及规则总数有重叠，不相加当独立覆盖数。 |
| 静态审阅 | PASS | 改动后端 Ruff、`git diff --check` exit 0；根协调核对增量 migration、快照、API、历史原文及共享类型变更。 |
| 浏览器 / 真实读取 | PASS | CUA Edge 在5177真实服务读取阶段总结及服务器0/9阶段状态；侧栏展开、子项所属阶段、总结/实践选择器同步、具体任务导航与随后手动选择不被覆盖、两个编辑器切换后恢复未保存文字。三个浮窗逐个关闭/重开保留选择/文字，Escape与焦点返回 PASS。所有临时输入已还原，未保存/搜索/批准/提交业务记录。页面390px/1024px与浮窗390px无横向溢出，临时viewport已reset。正常UI保存后刷新流程未在实际账号执行；隔离HTTP证据见上行。 |
| 浏览器脚本 | NOT RUN | 新 `redesign.browser.cjs`、`resource-dialogs.browser.cjs`及更新 summaries/resource-picker/resource-changes/learning-controls mock脚本语法检查 PASS；按本会话工具约束未运行 CLI Playwright，不能声称脚本内竞态检查通过。历史 real.browser.cjs未修改/未运行。 |
| 真实模型/搜索/RL训练 | NOT RUN | 没有本轮收费调用、Worker、反馈派发或模型训练。 |
| 备份恢复演练 | NOT RUN | 验证备份归档可读不等于恢复演练，Q12 不升级。 |
| 负责人完整体验 | NOT RUN | 本轮代理浏览器检查不替代负责人验收。 |

浏览器截图：`C:/Users/22088/.codex/visualizations/2026/10/02/01a0fade-8bde-7b13-aaf0-28b2e3b88153/studyplan-implemented.jpg`，已覆盖为最新三按钮/阶段二态/无节点状态的真实前端截图。同目录 `studyplan-resource-dialog-mobile.jpg` 为390px资料偏好浮窗。原 HTML 审阅稿未被当作实际服务证据。

观察过的失败与修复：nullable/评分上下文最初 unit FAIL；原 stage 调用 unit position 导致 PG FAIL；完整 dict rubric 被迭代成字段键的 PG FAIL 后修正。阶段进度与导航规则也先观察缺失实现 FAIL，再实现为 PASS。过长合成注册密码夹具按当前6–12规则修正，保留隔离与认证断言；成果降级拒绝测试的当前head从0022更新0023，拒绝及保留数据断言不变。根浏览器最初422是5177仍接旧8024代码；确认真实代理与只读 wrapper、更新 schema 和精确重启该进程后重新读取成功。生成类型一次 Windows UNKNOWN/-4094 打开文件 FAIL；针对性重试 PASS，随后完整contract PASS，未把包含后续命令的shell exit0当首次生成成功。

## 本地运行集成

本地正常开发库 `studyplan_b3_local_48fb59cc` 在原0022上仅应用0023，原59表/1516行原字段哈希保持；备份 custom dump 464752 bytes，目录 `var/frontend-redesign` ignored。正常API只按精确原命令核对 PID 后重启8022，Frontend5175保持其代理与数据来源。

5177原本连接8024的只读验收预览，继续保留同一个验收项目及全部写入保护。其隔离库 `studyplan_test_v2g1real_2f6ac462` schema 0022→0023 前备份431463 bytes，原59表/829行哈希一致；检查点库未改变。精确重启现有只读 server，未重跑历史 acceptance/journal 或消费旧请求ID。正常保存功能在5175→8022；5177仍用于审阅，不能把只读入口的403当正常保存失败。

两个报告和归档只保留在 ignored `var/frontend-redesign`，不提交秘密、用户内容或备份。没有改认证/RLS保护、全局角色、原RAG服务、私人路线或已发布迁移；没有触碰禁止目录。

## 路由与回滚

前端和阶段总结/自动进度两个可独立验收的任务按仓库路由要求派发 `gpt-6.1-sol/medium`；协调者已从会话 JSONL 核对两者实际解析值相符。最新独立只读进度/浮窗review派发 `gpt-6-luna/max`，根从会话JSONL turn_context核实实际相符；未发现可复现的实质缺陷，不以review代替测试。之前来源审阅子任务要求 Luna/max，缺独立可观测解析证据，不能声称已核实。最多两个并行业务写者，契约由 root 单一整合。

应用代码用普通逆向提交回滚；不重写共享历史。数据库有阶段总结后保留0023历史结构，禁止用 downgrade 删除新原文。备份保留可恢复性，但未执行恢复演练。当前更新不授权发布或合并完整产品 milestone。

本轮代码本地提交 `63689bc61f42e50b357e53f5d64fd34dd94a718f`，47个白名单文件，未推送；此SHA不是GitHub远端验收声明。文档另作正常提交承接本报告。
