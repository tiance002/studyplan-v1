# v6.2 章节内容与开放规划语义验收 — 2026-10-04

用户现在新增能做什么：生成 AI Fullstack、Agent、Cloud 的章级学习路线；已有项目优先作为持续练习载体，没有项目时建议可替换 Starter；Agent 可同时选择 Browser、Workflow、RAG 等能力，Voice 等尚无专门审核范围的目标仍能生成 Common Core 并看到资料缺口。项目案例保持可选。“修改目标”与受控未来路线沿用同一载体语义。已在模型 Fake、真实 owned PG、正常认证与 Chrome 验证，原产品环境未部署。

本轮内容落地状态 **READY**；整体产品 **NOT_READY**。READY 仅指本文件的有界内容与语义门禁，不等于真实收费模型、独立 RAG、产品数据恢复、用户接受或上线。

## 实际基线与提交

- 分支：`feat/n1-resource-discovery`，沿用续接例外；不从 master 重做。
- N0 实际 HEAD：`841ef9e31f0db70af238fa8c89796e3a5cf1c3e1`；跟踪文件 clean，两个禁止操作目录未处理。
- 固定参考 `cf1537040bbf8c52469e00461723f70726f5a3b2` 及 N0 HEAD 均为当前提交祖先，PASS；无 reset、历史改写或强推。
- Commit A：`1b5a98c00506bc3c64204312e0021a83c4e8457a`，原资料、哈希及只读 schema 映射。
- Commit B：`63a77a99832806d5d942193e7208ffd8c32e770f`，下一版本内容与离线 mapper。
- 消费边界修复：`933441f4b8d6e2ae43db94f30deef719ad9c749e`，短章节 ID 与无损正文分片。
- Commit C：`0109b236404c507d4dcfeab7a0c8bf749cf22cb2`，私人选择、载体、发布资格、生成变更与最小 UI 文案。
- 最终实现 SHA：`168d9b4d674ac65030831c4781f946074e101d78`，追加排除“已有云服务经验”等学习起点误认；三个反例 RED→GREEN，明确项目名不受影响。
- 本文件随 Commit D 提交；最终实际 HEAD 在交付时由 `git rev-parse HEAD` 读取，不能用 C 冒充文档提交后的 HEAD。以上为本地 SHA，本批未推送/核实新远端 SHA，无 master/milestone 操作。

产品库只读 N0：migration 0023、已发布 Agent v1/Python v1；Registry 原 AI1/Agent4/Cloud1。下一合法版本已按实际状态确定，未写产品库。Repo migration head 0024 沿用。

## 输入与映射

[Goal 原文](../implementation/STUDYPLAN_V6_2_SEMANTIC_CONTENT_GOAL_2026-10-04.md) 与用户文件逐字节相同。ZIP SHA256：`55523f31a595985b274390f8cf4b5c8a8b80191ca5effafbc3240a10c3094d93`。23 个原文件按 [INPUT_MANIFEST](../research/semantic-corrected-2026-10-04/INPUT_MANIFEST.json) 保留且哈希 PASS；原 Markdown 的有意行尾空格未清理。

[N0/schema 审计](../reviews/2026-10-04-v6-2-n0-schema-mapping.md) 分为 DIRECT、CONTENT_ONLY、THIN_ADAPTER、UI_WORDING、HOLD、DEFER。优先既有 DomainPack JSONB、Knowledge/Stage/Practice blueprints、LearningGuidance、source/sections/roles、extensions 与版本快照。没有新实体、Migration、DTO/API/OpenAPI、依赖、Graph、第二套 planner、clone/index、固定源码切片或全局设置。

| Pack | 新版本 | 阶段/知识节点 | 来源实例 | 章节 |
|---|---:|---:|---:|---:|
| agent.application | 5 | 61 / 61 | 57 | 179 |
| ai.fullstack | 2 | 11 / 11 | 16 | 57 |
| cloud.services | 2 | 15 / 15 | 13 | 58 |

86 个来源实例由三包各自命名空间产生，**不是把研究 Catalog 的 86 条全部导入**：涉及 71 个不同 catalog scope，另有 12 个独立根仓库身份候选；其余为跨包复用。来源深度为 selected_sections_read 71、deep_reviewed 3、metadata_only 12。项目根候选均 legacy_index、无正文章节，不借教材审读等级认证源码。

四条 hold 未进入任何新包：ZCode 两个同名身份候选、MaxKB 内容候选、阿里课程访问候选。发布校验拒绝 hold、新语义版本漏策略标记、正文审核缺原证据、来源深度升级、章节比来源审得更深及 Primary 访问/审读资格不足。旧版本契约保留；本批不自动审批公共内容或重写旧 immutable Pack。

每阶段保留八项教学字段、原作者段落、JIT 先修、章级范围、补充/比较、Exposure、Micro Exercise、持续增量及退出门槛。原 schema 的 Primary 连续性保持：15 处非连续精选保留首连续段为 Primary，后续原选择成为 Supplement，保留原角色和精确顺序，不补未选章节。[精确映射报告](../research/semantic-corrected-2026-10-04/CONTENT_MAPPING_REPORT.json) 可逐项核查。

章节/source ID 使用包版本命名空间与确定性摘要，符合现有 64 字符消费者。扩展正文按 850 字符精确分片，指导列表按 750 字符拆分，保留原文与片段顺序；实际 Pydantic 消费测试覆盖三个公开完整包与 100 字用户项目名称。不是扩大 DTO 或截掉教学证据。

## 语义边界与真实链路

私人选择发生在冻结提交之前，深拷贝公开 Pack；actor/project、幂等、事务、claim/取消、旧图恢复规则沿用。明确原目标也参与选择，宽 GoalSpec 不遮蔽项目；学习基础描述不被误认成项目。否定训练不触发 RL/训练阶段。选中能力通过必要依赖闭包组合；未命中不 fatal，不自动增加已审章节。

用户项目是用户自由文本描述的外部成果载体。本计划的 PracticeProject 是学习实践记录；本批未绑定现有外部仓库，也不声称复用未提供的旧 DB PracticeProject ID。Starter 是可替换建议；不适合持续项目的能力可以做独立 Micro Exercise。Direction 未成为账号归属枚举；跨方向额外主题仍受现有公共资料与受控变更边界约束，本批没有新增多 Pack 自动合并器。

change_goal 保存公开 Seed digest 作为并发/发布 fence，再冻结私人章节与载体；future/add_topic 保留已决定的 after keys 并适配载体，不重新展开完整 61 阶段。旧无语义标记的包原样处理，已冻结 Run 不重选。

| 必做场景 | PG | Chrome | 实际阶段数 |
|---|---|---|---:|
| 已有旅行 Agent：Browser + Workflow + RAG，Evaluation 横切，无 RL | PASS | PASS | 27 |
| 无项目：Starter 为可替换默认候选，0 Recipe | PASS | PASS | 6 |
| Voice：Common Core 与明确补审缺口，不 fatal | PASS | PASS | 6 |
| 已有电商后台：用户载体优先，AI 全栈按目标裁剪 | PASS | PASS | 7 |
| 已有 Node.js API：无强制 FastAPI/Task Service，部署/监控/发布/恢复 | PASS | PASS | 9 |
| 用户知识库：RAGFlow/WeKnora 可选，无二选一阻塞 | PASS | PASS | 13 |

普通注册、Cookie/CSRF、服务端范围、worker/Fake、草案、确认、幂等、新容器登录与原 ID 回读；每场 Chrome 生成 POST 1、确认 POST 1，刷新/重登录新增生成 0。13 张 PNG 与 JSON 在 `var/v62`。Fake 内部模型请求数未捕获，不编造实际次数。

旅行 B3 的 Playwright Network/Frames/Dialogs 只有 TOC 资格，现有守卫正确剥离来源/章节，保留角色并提供搜索提示；该降级记录于 `pg-travel.json`。全部已审核章节逐源、逐角色、按原顺序精确断言。资料阅读资格与工程运行、学习者掌握分别记录，未执行外部项目。

## 测试与证据

以下测试均实际执行；重叠不累加。JUnit/log、截图、备份归档属于忽略的本机证据目录；入仓代码及本报告提供可复现入口。

| 范围 | 状态 | 证据 / 限制 |
|---|---|---|
| 最终单元/契约 | PASS 840；NOT RUN 2 | `var/v62/unit-contract-handoff-final.xml`，842 总项；两项目录符号链接创建需提升权限，本批不提升 |
| 新语义内容/选择/发布/变更定向 | PASS 88 | `semantic-route-unit-final.xml`，与上一行重叠 |
| 三包消费契约/映射 | PASS 12 | `content-consumer-green.xml`；离线可复现、Primary/holds/深度、章节角色、12 项目卡、实际 DTO |
| 六场景 + 旧计划/hold/隔离 + Chrome + change_goal | PASS 9 | `semantic-pg-browser-final-attempt7.xml`；`semantic-browser.json`、`pg-*.json`；模型 Fake + real owned PG |
| 新语义未来路线 | PASS 1 | `future-semantic-pg-green.xml`、`pg-future-route.json`；Node exact keys/carrier；相同 Fake 内容确认 created=false，保留原 revision 与旧阶段 |
| 旧变更/取消/派发/history/闭环 PG | PASS 61；NOT RUN 6 | `legacy-protocol-pg-final.xml`；受控旧夹具固定 legacy 2/3/4，不用高版本号冒充 v5+；六 Chrome 显式开关未在此命令打开 |
| 闭环/history/取消 Chrome | PASS 6 | `loop-history-cancel-browser-release.xml`，总结+两实践、无实践、原文历史、普通恢复、取消；包含上一行重叠 |
| 旧 checkpoint 恢复 | PASS 4 | `checkpoint-recovery-pg-release.xml`；kill/续跑零完成批次重派、旧 waiting/终态/未知图守卫 |
| 较宽受保护 PG 首轮 | FAIL | `protected-pg-release.xml`：87 项中 PASS77、FAIL8、NOT RUN2；旧版本夹具、后续 setup 连带及 checkpoint 写入时序失败保留；相关最终定向如上，不能把原命令改为 PASS |
| Auth/RLS/旧 DTO 更宽测试 | FAIL | 当前与 N0 原基线各61项，均PASS51/FAIL10；失败集合完全相同，见下一段 |
| Frontend | PASS 13；Build PASS | `npm test`、`npm run build` 62 modules；无新增依赖 |
| Ruff / mypy / diff / 输入哈希 | PASS | 所有本批 Python 改动；8 业务模块 mypy；原文及自写文档核对 |
| 独立 owned PG 备份恢复 | PASS 1 | `restore-consumer-final.xml`；`var/current-learning-loop/v61-restore-9011e2ff.json`。实际使用本批新包，63 表、ACL/RLS/policies 精确一致，普通登录/原文/成果/extensions 回读，恢复后模型请求0，两个测试库清理 PASS |
| 收费模型/GitHub API/Tavily/真实 RAG | NOT RUN | 本轮新增调用0；不以 Fake/PG/Chrome 替代真实服务验收 |
| 原产品库写入/产品数据恢复/用户接受/部署 | NOT RUN | 只读 N0 与合成测试不能证明这些门禁 |

更宽失败由 `baseline-auth-rls-pg.xml` 与 `auth-rls-pg-final.xml` 精确对照，原基线在 ignored 目录只读快照运行，未 reset。包括：把全局额度表当私有表要求 RLS、旧 entity→column 映射漏既有 JSONB 字段、旧虚构资源夹具与审核守卫不一致，以及四项已发布迁移 downgrade 路径错误。后者保留为整体交付风险；本批无迁移修改，不声称基线全绿或整体 READY。

早期 RED 不删除：mapper/资格/长度、载体诊断、否定训练/原目标、政策漏标、语义 PG attempts1–5、restore 首轮、future 首轮测试误要求相同内容创建新版本。修复/夹具更正与后续 PASS 分开记录。

六场景 API/worker/socket/Chrome context 退出断言 PASS，owned DB fixture teardown 无错误。attempt1–5 精确库名独立回查 PASS；attempt6/7 未捕获精确库名，独立回查 NOT RUN，不拿其它会话的库推断清理失败。`semantic-owned-cleanup.json` 记录该限制。原 PG 与 RAG helper 容器未停止；root 自有临时 Vite 结束。

## 用量、风险、回滚与下一安全动作

实际真实收费模型新增 **0**、外部搜索/公网读取新增 **0**。既有模型23/50、搜索6/1000、unknown1与旧 README/账本保持，不重置、不重派旧 Acceptance。开发请求 root Sol6.1/high，有界 Sol6.1/medium，只读 Luna/high；实际 model/effort **NOT OBSERVABLE**。无 Astra/Sol max/快速模式或全局配置切换声明。

剩余整体门禁：独立 RAG 检索与 scope 契约、受许可真实服务代表路径及故障验证、产品环境接线与私人数据备份恢复、用户实际接受，以及本次核实的既有 downgrade 遗留。较宽测试失败、TOC 参考降级、候选仅身份审核与跨方向自动组合限制已明确，不将内容可用包装成全产品交付。

回滚：在普通备份分支上按依赖倒序 revert D/C/消费修复/B；不 reset/强推，不改旧迁移、计划、Run、未知尝试和用量账本。若新内容已写入目标库，应先保留其不可变快照与读取兼容，再把新生成注册表切回旧包；不要删除新版本或历史计划。当前只有 owned 测试库写入，产品数据未变。

下一安全动作：先提供正式入口的只读配置核对与用户体验准备，核对产品库的发布版本/独立 RAG 契约；任何产品数据写入、真实收费或部署仍按现有独立门禁执行。普通已授权代码实施不用重复确认。
