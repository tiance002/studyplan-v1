# v6.10 Planning Alignment 验收：BLOCKED，STOP

日期：2026-10-04。实施提交：本地 `817b17b`，分支 `feat/n1-resource-discovery`。本轮没有 push、merge、正式部署或原产品库连接。整体仍为 **STAGING_BLOCKED / NOT_READY**。

## 结论

规划语义、下一版内容映射、私人任务适配与页面消费的非收费链路通过；**真实 provider 代表 FAIL**，因此不报告 `PLANNING_ALIGNMENT_PASS`。

唯一新 Acceptance：`v610-agent6-synthetic-c5c4af9fb8f8`；唯一新真实 Run：`run_9c00403807ee4ccb817529611e44efa6`。系统 Agent 的 outline 和 A0/A1 structure 通过；A2 新增了冻结知识目录外的 6 个节点，两次局部 repair 后仍不合法，Run 以 failed 结束，没有 Draft/Plan。保护没有放宽，未开启第二 Run。A8 的真实生成、真实 Draft 确认及真实 Plan 的 Edge 消费均 **NOT RUN**。

## 权限与本机基线

本机起点为 `ff3b6c42c16b0ec2b634b45441251cb8dc1e3249`，复用当前分支；没有 v6.9 实施提交或内容版本。已有 v6.7/v6.8 继续保留，无 reset 或回退。用户 ZIP 的五份文件逐字节归档在 [原始验收包](../reviews/planning-alignment-v6.10/README.md)，Goal/review/cases 哈希与其 MANIFEST 相符。附件提供需求与审查依据，执行授权以用户本轮消息为准。

用户随后只覆盖产品真实模型调用为 0 / 禁止收费验证，新增 50 次额度；其他约束不变。搜索新增仍为 0。原 `.env`、endpoint/TLS/预算 guard、旧 Agent5/AI2/Cloud2、v6.8 的 Plan 文件、Acceptance、receipt 和证据未改。未操作 `.workbuddy/`、`design-preview/`。

## 发现 → 修复 → 可核查结果

| 原偏差 | 本轮修复 | 结果与限制 |
|---|---|---|
| 泛词 AI 吞掉 Agent 目标 | 显式 Agent 对象优先；方向冲突保持保守判定 | G03 单元 PASS；不引入另一套规划器 |
| 完整方向和窄专题共用默认核心 | private snapshot 冻结前区分 complete/narrow；系统路线有 A8 与后续可组合路径，MCP 仅展开必要闭包 | 系统 7 阶段、MCP 4 阶段；地图不等于后续阶段已生成或完成 |
| 正向关键词覆盖否定、前置暗中复开专项 | 分开正向/排除语句，闭包后再次拒绝冲突；显式未来 route 也不能绕过排除 | G04/G08 单元 PASS；旧 policy v1 不重解释 |
| 起点/深度只是标题 | 自述已有基础改为简短检查；foundation 后置专项，deep 对比失败边界证据 | 不升级为掌握/VERIFIED，原验收能力保留 |
| A8 只有标题且无绑定 | Agent6 的 A8 绑定既有已审 Pi 两个文档范围，提供 whole_core 地图、正常/失败链、产出与迁移 | Fake/owned PG/Edge PASS；只认 selected sections，不宣称全仓深审或已运行；真实 A8 NOT RUN |
| 用户项目和成熟参考混为一谈 | 实践 carrier 与可替换 reference 分开；初学 Demo 不取消工程对比；指定 URL 保留资格待确认 | P03/P04 确定性 PASS；未知 URL 不变成已审公共资源 |
| 任务只加“在你的项目中” | 旅行输入/输出、审批链；电商 UI/API/ERD 实体；Node 运维任务在冻结前适配 | Node 不要求重写 Task Service/FastAPI；不自然匹配的任务明确 Micro Exercise |
| Cloud 缺口与任务相互矛盾 | S3 重用已审容器主线；S3/S7/S13 区分当前隔离本地练习和待选平台/语言/DB 专门操作，保留完整后续验收 | 草案与 workspace 均显示 needs_research_or_review；本地演练不等于云端/Node OTel/数据库恢复完成 |
| 新旧发布资源溯源身份冲突 | 新合法版本分配新的 source/section 身份，继承原 URL、审核正文与深度，stable knowledge keys 不迁移 | 新旧 owned 发布并存、重复导入及 immutable 拒绝 PASS，无迁移/公开 DTO/API |
| 第一张卡吞掉其他候选/续片 | 当前 stage + repo root + base topic 精确成组，有序无损拼接；未匹配候选保持 pending | 双候选、>850 字符、同仓跨 stage、无仓库、剪贴板失败退路 PASS |

新源码版本为 **Agent6 / AI3 / Cloud3**，只在本轮 owned catalog 导入验证，正式 catalog 未导入。已有已发布包不原位修改。构建器从 Agent5/AI2/Cloud2 的既有审核事实生成新版本，拒绝覆盖已有目标文件；新源版本的资源审核深度/原正文证据继承检查 PASS，hold 不升级。

## 验证分层

测试状态仅用 PASS / FAIL / NOT RUN。下表“真实”专指 provider，不把 Fake 与实际浏览器混为一谈。

| 层 | 结果 | 证据 |
|---|---|---|
| 完整 unit/contract | 898 PASS，2 项 symlink 权限场景 NOT RUN（900 total，exit0） | `var/v610/unit-contract-stop.xml` |
| 最新语义与 v6.7 canonical/projection 定向复核 | 58 PASS | `var/v610/alignment-protection-final.xml` |
| owned PG 教学/发布/精确读回/长文本 | 8 PASS | `var/v610/pg-teaching-final.xml`；其中独立合成 v7 长文本夹具不属于 CURRENT_PACKS |
| 旧/新 marker、checkpoint 恢复、失败不重派 | 7 PASS | `var/v610/guard-pg.xml`；历史六阶段 checkpoint 显式使用 Agent5 |
| 相邻语义/hold/旧快照/公开 digest/未来 route/隔离 | 9 PASS | `var/v610/semantic-pg.xml`；scratch 证据写入本轮目录 |
| 前端单元与 build | 16 PASS；build PASS，62 modules | `var/v610/frontend-unit-final.log`、`frontend-build-final.log` |
| Edge 组件夹具 | PASS | 双候选、长指导、跨阶段/版本、pending、真实剪贴板与拒绝退路、390px；Fake HTTP fixture 不冒充 PG |
| Edge 三条普通用户链路 | PASS，页面错误 0、外部请求尝试 0 | `var/v610/alignment-browser.json`；普通注册→生成→合成确认→PG workspace→刷新→退出重登录，额外生成 0 |
| 免费真实网络/预算/绑定/短 outline | PASS | `var/v610/free-preflight.json`；4653 chars / 6460 bytes；7 阶段正常 15 / repair 2 / 总 17；output upper bound 106496 |
| 单一真实 provider 代表 | FAIL | A2 违反冻结目录，2 repair 用尽；`run-report.json`、`stage-protection.json`、`execution-state.json` |
| 真实 A8 / practice / Draft 确认 / Plan Edge | NOT RUN | 未生成合法真实 Draft/Plan |
| MCP 与已有项目的真实 provider 代表 | NOT RUN | Fake/PG/Edge 已证明本轮裁剪与适配；本轮未机械增加收费 Run |
| 外部 AI 源码学习、clone/安装/运行成熟参考仓库 | NOT RUN | Prompt 仅内容与复制核对，不冒充外部执行 |

初始规则复现 10 FAIL / 2 PASS，Cloud/电商具体任务补充 RED 2 FAIL 均保留。过程中 PG 验收脚本错误、旧 checkpoint 常量及 Edge 定位错误的 FAIL 也保留于 `var/v610`；后续修正不抹除原记录。两项 symlink NOT RUN 是现有 Windows 提权限制，本轮没有申请提权。

## 配套用例逐项映射

每列分别描述证据层；未运行的维度标 NOT RUN，不用单元证据冒充真实 provider。

| 用例 | SOURCE_TRACE / UNIT | PG | EDGE |
|---|---|---|---|
| G01 完整路线与首步 | PASS：A8/后续组合地图 | PASS：system | PASS：system |
| G02 窄 MCP 与真正前置 | PASS：四阶段、简短复习 | PASS：mcp | PASS：mcp |
| G03 AI Agent 方向优先 | PASS：显式路由 | NOT RUN | NOT RUN |
| G04 RAG/Browser 排除与工作流前置 | PASS：闭包与排除 | 相邻 travel 闭包 PASS；该否定组合 NOT RUN | NOT RUN |
| G05 voice 缺口 | PASS：公共核心保留，不编造 voice | PASS：voice 相邻回归 | NOT RUN |
| G06 起点差异 | PASS：React/JS/SQL 复习任务，自述非掌握 | 起点对照 NOT RUN | MCP 自述提示 PASS；全栈对照 NOT RUN |
| G07 深度差异 | PASS：选定 RAG 与未选专项两种对照 | NOT RUN | NOT RUN |
| G08 scope/constraints 冲突 | PASS：冲突与显式未来 route 门禁 | NOT RUN | NOT RUN |
| P01 旅行 carrier 与 reference | PASS：具体业务适配、角色分离 | PASS：travel | NOT RUN |
| P02 无项目可换 Starter | PASS：optional | PASS：system/starter | PASS：system |
| P03 初学 Demo 不替代成熟对比 | 确定性 PASS | NOT RUN | NOT RUN |
| P04 指定成熟项目候选 | 确定性 PASS：资格待确认、不强制 Pi | NOT RUN | pending 组件 PASS；该 URL 组合 NOT RUN |
| P05 已有 Node API | PASS：语言/DB 不强改、独立练习 | PASS：node | PASS：node |
| P06 具体任务适配 | PASS：旅行、电商 UI/API/ERD、Node | PASS：travel/commerce/node | Node PASS；旅行/电商 NOT RUN |
| P07 额外强制任务/冲突验收 | PASS：旧 canonical 回归 | canonical 往返 PASS | NOT RUN；真实 A2 越键拒绝 PASS |
| C01 A8 可消费内容 | PASS：Pi 已审范围与模式 | PASS：system | PASS：A8 card/knowledge/task/Prompt |
| C02 RAG 大项目切片 | PASS：模式/可替换边界 | PASS：rag | 目标切片组件 PASS；rag 普通路线 NOT RUN |
| C03 G6 双候选 | PASS：精确配对 | PASS：RAGFlow/WeKnora | 双候选组件 PASS |
| C04 >850 字符 | PASS：有序无损拼接 | PASS：独立长文本夹具 | 组件 PASS |
| C05 同仓跨 stage | PASS：stage/root/topic 组合 | NOT RUN | 组件 PASS |
| C06 whole_core / targeted_deep_dive | PASS：模式/指导 | PASS：A8/G6 | system + 组件 PASS；whole_system 实际路线 NOT RUN |
| C07 复制失败退路 | PASS：文本与权限边界 | NOT RUN | 真实剪贴板及拒绝退路 PASS，模型增量 0 |
| C08 安排过不等于掌握 | PASS：原保护保留 | PASS：guidance 精确往返 | PASS：Prompt 自述/阅读非掌握 |
| C09 无可核验 repo | 确定性/组件 PASS：pending 不造 URL | NOT RUN | pending 组件 PASS |
| T01 A1→C1 / A3→G0 | PASS：REVIEW/COMPARE、可观察新增能力 | 相邻 frozen guidance PASS | NOT RUN |
| T02 主课内部前置 | PASS：必要闭包，无额外整门 Python 课 | MCP/Node 路径 PASS | MCP/Node PASS |
| T03 可观察目标与阅读范围分开 | PASS：新版知识/私人阶段目标 | canonical PG PASS | system/node 可见目标 PASS |
| T04 云商未知 | PASS：当前本地/后续待审 | PASS：node | PASS：draft/workspace 缺口与任务 |
| T05 hold/toc/metadata | PASS：继承深度、源证据 | PASS：hold/immutable 相邻回归 | NOT RUN |
| T06 替换与历史兼容 | PASS：资格不提升、旧 policy 不重解释 | PASS：旧 snapshot/current digest | 跨 revision 组件 PASS |
| S01 v6.8 历史不改 | PASS：原包及 Plan/receipt/evidence 哈希 | owned 旧 Plan 保持 PASS；原 v6.8 DB 读取 NOT RUN | 原 v6.8 NOT RUN |
| S02 marker/checkpoint/失败 Run | PASS：canonical/hash/fingerprint | PASS：7 项 checkpoint 与失败不重派 | NOT RUN |
| S03 新阶段预算 | PASS：7 阶段 15+2、106496 | PASS：实际冻结 manifest | Fake 7 阶段 PASS；真实 A8 NOT RUN |
| S04 新库/Fake/网络封锁 | PASS：原 DSN 不载入收费进程、搜索禁用 | PASS：owned/新合成账号 | PASS：外部网络尝试 0 |
| S05 配额授权更新 | PASS：用户仅覆盖模型 0，39 保留，上限100 | PASS：45 回执一致/unknown0 | 不适用，NOT RUN |
| S06 既有确认/事务 | PASS：没有 SQL 原位补历史阶段 | PASS：普通 Draft 决定、幂等与精确读回 | PASS：普通合成确认 |
| S07 三新样本 | PASS：来源明确 | PASS：三路线 | PASS：普通认证/刷新/重登录 |

## 唯一受控账本及六次真实调用

沿用 `.git/v2-paid-quota-20261001`，新增 `authorization-v610.json` 记录用户追加 50 次，上限 50→100。没有新全局计费系统，没有清零/重写/移动历史 scope。原受控历史脚本作为证据保持不变、未执行；本轮新 one-shot harness 使用同一账本和单一授权上限。

```text
起始累计调用：39
本轮新增授权：50
新总上限：100
本轮实际新增调用：6
最终累计：39 + 6 = 45 / 100
unknown：0
repair：2
理论剩余：55
搜索新增：0（原 6 / 1000 保持）
```

| 请求 | 目的 | input / output tokens | 已证明 / 未证明 |
|---|---|---|---|
| 40 | outline | 1516 / 413 | HTTP/JSON/7keys/stop/PG receipt PASS，真实短输入；未证明后续生成 |
| 41 | A0 structure | 1725 / 255 | 结构与逐阶段 canonical 恢复 PASS |
| 42 | A1 structure | 1743 / 360 | 结构与逐阶段 canonical 恢复 PASS |
| 43 | A2 structure | 1508 / 2035 | provider 回执完整；模型新增 6 个未审核知识键，领域验证 FAIL |
| 44 | A2 repair 1 | 3554 / 2095 | provider 回执完整；nodes/units/relations 等必需字段缺失，验证 FAIL |
| 45 | A2 repair 2 | 3662 / 1525 | provider 回执完整；仍新增同类知识键，验证 FAIL，repair2耗尽 |

全部请求 HTTP200、finish_reason=stop、返回 model=deepseek-flash；这不等于 Run 成功。outline 相比历史 209998 实报输入降为1516，减少99.2781%；字符估算不当 tokenizer 实报。收费请求 6 次全部计数，无退款计数。最终 PG request_count=6、unresolved_count=0；新进程失败 Run 不可 claim，Fake 调用也为0；未重派历史 unknown。

188 个受保护文件哈希最终 PASS；历史39对intent/result不变。新增失败 Acceptance/journal/evidence 保留，新 owned 业务/checkpoint 两库保留以溯源。本轮没有连接原产品库、切正式入口、运行正式 Worker、修改 RAG、关闭 RLS、放宽安全保护或写外部项目。

## 三条样本与停止点

[三条来源明确的教学样本](v6-10-planning-alignment-samples-2026-10-04.md) 均为普通 Fake+owned PG+Edge 的本轮新数据；不混用 v6.8 真实 Plan，不把本轮失败代表冒充真实新 Plan。

**BLOCKED 后 STOP**。尚有55次理论额度，授权记录保留；本轮不因额度仍在而自动新开 Run。阻塞是严格冻结节点目录与真实 A2 structure/repair 输出不匹配，需后续独立定位精确响应/repair 契约并先做非收费验证；不能用删除A8、放宽schema、接纳未审核节点、增加repair或重写旧真实Plan来绕过。

回滚仅限普通源码 revert 和未来包选择的受控变更；新内容一旦已有冻结 Run，应保留对应读取、manifest/canonical 验证与旧 policy 两格式兼容。不得覆写已发布包、旧 Plan 或失败账本。最终交付只含本地提交与证据，未推送、合并或部署。
