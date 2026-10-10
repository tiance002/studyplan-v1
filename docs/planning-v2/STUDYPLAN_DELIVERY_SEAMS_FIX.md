# StudyPlan 审查包接缝修复

任务：`STUDYPLAN_DELIVERY_SEAMS_FIX_V1`，2026-10-10。

本轮根据 Owner“根据审查包里的内容做项目修改”实施有界修复。F01–F08 的指定程序接缝与独立审查通过；W5 的 tracked 准备与 owned 提交入口已落地，完整真实付费 runner **PARTIAL**。真实模型语义、真实教材质量、完整课程和浏览器验收 **NOT RUN**。

## 1. 基线与授权

- Start HEAD：`bcdcf1b5fe5e6d245417e65a0b35ff79429d1c2a`，分支 `feat/n1-resource-discovery`，tracked tree clean。
- 原有 `.workbuddy/`、`design-preview/` untracked 保留，未操作。复用当前分支及已有工作，不 reset、不重新实施 Item1–9。
- 审查 ZIP：`C:/Users/22088/Downloads/STUDYPLAN_DEEP_AUDIT_bcdcf1b5.zip`；五份文件的 manifest hash 校验 PASS，原样留在 ignored `var/codex-goals/delivery-seams-fix-20261010/`。
- 审查包是本次修改依据，其中引用的历史授权没有被重新用于外部派发。源码片段 probe 未执行，也不作为项目测试 PASS。
- 本轮模型、搜索、Reader、正文、官方价格/余额请求均为 **0**。无正式数据库、历史 Run/Receipt/账本、部署或配置修改，无新 migration。
- 专用测试只创建新的 owned 测试库，应用既有 migration。公开 `/plans/generate` 仍503。
- 开发代理请求：有界 UI 为 Sol6.1 medium，资源/引用/恢复独审为 Sol6.1 xhigh。实际主会话及代理解析均 **NOT OBSERVABLE**；未改变全局模型配置。
- 最终代码与本报告同一 local checkpoint；完整 SHA 由交付消息及 `git log -1` 给出。不得将其当作 GitHub 已存在的远程提交。

## 2. W0：项目使用语义与第189次结果

| project_usage | 产品含义 | 合法依据与下游行为 | 页面文案 |
|---|---|---|---|
| required | 本版贯穿项目需要使用 | 真实应用目标/必要项目实现依据；课程必须安排相应实践 | 项目需要使用 |
| optional | 是否纳入本版贯穿项目仍是可选项 | 非必用不能自动推导为排除；不强迫在原 CLI 集成 MCP | 项目使用可选 |
| excluded | 本版贯穿项目不使用；学习可由独立练习承担 | 必须有可追溯的用户限制或真实项目适配依据，沿用已有需求/约束引用；不能猜测隐藏理由 | 不用于贯穿项目，通过独立练习学习 |

历史第189次程序 PASS、当批语义 FAIL 与 failed Run 原样保留。该批独审原件明确记录 MCP `actual=excluded / expected=optional`，并指出原目标没有禁止在保留 CLI 中使用 MCP。它既记录了当批预期偏离，也记录了无充分来源依据缩小项目选择的判断；不能将其扩大为“所有 excluded 都违法”，也不能把 Enum 合法当作语义充分。未来判断不要求复制第187次能力清单。

本轮只在 Item2 专用 Prompt 澄清 optional/excluded 和依据要求；未新增理由字段，未改 Enum、Policy、Schema、Validator，也未把旧189响应或审查升级为 PASS。新 Prompt 的真实语义效果 **NOT RUN**。

## 3. F01–F08 实施结果

| Finding | 修改位置 / 实际行为 | 验证与边界 |
|---|---|---|
| F01 | `capability_planning_contract.py::CAPABILITY_SYSTEM` 明确项目可选与排除的不同作用和已有引用依据；页面使用同一含义 | 专用 Provider MockTransport 仍消费原真实 Profile、序列化消息≤32KiB；合成响应不能证明模型会正确决策 |
| F02 | GitHub/Tavily 的成功空结果返回 `[]`；内部 `SourceSearchUnavailable` 提供 status、实际请求/bytes、receipts、stop_required；DurableIndex 保留源端事实 | 404/500 等明确普通失败可继续；403/429、重定向及安全拒绝停止；真正 lost reply 保持 reconciliation。未知 legacy Unavailable 不按 reason 猜测 |
| F03 | DurableBody 接受 known unread，持久化非正文 metadata 与实际计量，冷读回无需再读取正文 | 历史负回执若缺计量仍拒绝，不补0；body-only success 没有 Reader 证据仍拒绝重派；unknown 继续锁定 |
| F04 | Coordinator→DurableBody→GitHubTeachingBody 接通获准 outcome 文本；在 README 本地文本链接 allowlist 内有界选章，排除 CONTRIBUTING/LICENSE 等行政文件 | 精确 Policy 文本别名只帮助发现英文标题，不证明覆盖。无匹配/同分歧义/合法过长正文返回 unread；不截取或伪造审核。最多 README+章节两次 HTTP |
| F05 | partial GitHub 证据不再因 `resources` 非空阻断 Web fallback | 真实 GitHub空→Tavily候选→DurableBody 接缝已离线验证。普通 Web 正文仍 unsupported/unread，不虚构 Reader 或 covered |
| F06 | `_comparison_relation` 同时比较 outcome 集合与连续性、起点、示例、版本四维审核证据；order/incomparable 共用偏序 | 覆盖更宽但质量更差、互不包含的覆盖均 incomparable；质量/覆盖相当才中文优先；不足仍 insufficient，不声称全局最佳 |
| F07 | 先为 required、明确学习选择及其真实先修的缺失范围提供首轮候选审核机会，再处理剩余覆盖和有限比较，最后推荐范围 | 不改 importance/Gap 身份；发现批次在本轮复用，不重复搜索；已有成功 exact scope/depth/version 证据复用，不扩审读资格 |
| F08 | Curriculum 显示 unresolved 目标/原因、规划安排与运行未验证；excluded准确表达；依据冻结 GitHub URL 显示仓库/章节 | 保留真实可读 title；hash fallback 在按钮、阶段摘要和对话框一致。无 DTO/业务快照/hash 改动。SSR/HTTP-shaped fixture 通过，浏览器 NOT RUN |

正文绑定或 Reader 输入非法时设置 `session.blocked=True`，不再把来源错误当作普通不可读后继续搜索。模型、现金或教材资格保护未放宽。

## 4. 历史身份与预算保护

独审发现初版选章修改会给旧正文 `payload.options` 增加 `must_teach`，从而改变输入 hash，可能绕过已有 body-only 回执的不重派保护。修复如下：

1. Legacy research 不传新选择输入，原 options 保持。
2. Durable 选择仅用于 product-v2；逐项核对 `must_teach` 与原冻结 `review_scope` 的完整文本。
3. 原身份已经绑定 `review_scope/review_identity`，故 options 不重复增加该字段；新调用使用核对后的文本，原身份/hash 算法不变。
4. 同 scope 旧正文 success 仍命中同一 attempt 并拒绝无 Reader 结果的恢复；scope 不符在 ledger/HTTP 前拒绝。

真实 owned PG 验证上述单 attempt/两次 Mock HTTP、冷读回和拒绝路径。没有修改 PgV2Calls 的预约、累计、observed excess、fence/CAS、unknown family 逻辑；最坏预约继续保留，不将内部 `cost_micros` 转成人民币。已知搜索成功但缺实际费用时仍保留相应预约，不能将 `unknown_measurement` 等同 transport unknown，也没有擅自退款。

旧 `.env`、账本历史等506份既有保护文件 hash 无变化。实际 append-only 请求数仍189，无 request190；177/183 的原 `provider_transport_unknown` 记录保留。188/189请求/响应文件与旧失败报告未修改。未连接或修改旧失败 owned Run，两轮历史失败和旧授权保持原状态。

## 5. W5：tracked 准备入口，完整 runner 尚未完成

新增 `scripts/planning_v2_scenario_a.py`：

- `prepare` CLI：只读本地受控内容，一次冻结完整 SourceFacts，随后生成 manifest、全部预约计划与新的 acceptance 身份。
- 文件位于新的 ignored `var/` 目录，独占创建，重复准备或提交不会自动创建第二 Run。
- Owner 申请模板默认 `owner_approved=False`。单独受控证据必须绑定新身份、packet hash、用途/预算/请求选项和时间；同一 raw 字节用于 SHA 核验与 JSON 解码，拒绝文件替换、重复键、非法编码和超限文件。
- Python owned 提交复用实际 PlanService、现有 PG repositories、冻结工厂及 owned gate；原工厂继续拒绝正式/远程/同一业务与 checkpoint DSN。
- 默认外部 resolver 拒绝；CLI没有付费执行、账户预检、批准或循环 Worker 命令。`external_options` 和 `execute_claim` 不能开启真实派发。

入口：`python -m scripts.planning_v2_scenario_a prepare --goal-file <本地GoalSpec.json> --request-options-file <本地请求选项.json> --model-ref <冻结绑定> --output var/<新的受控目录>`。凭据、正式授权和原始证据不进入 tracked 源码。

**W5=PARTIAL**：成功准备与受控提交接缝已验证，完整真实 transport/binding resolver、全局模型/搜索账本、账户 preflight、Worker 驱动与独立审查续接尚未迁入该入口。本轮没有把旧 ignored 验收脚本硬编码的授权、身份或回执复制成新事实；当前脚本不能执行完整真实课程验收。下一步应先完成这一个真实 runner 接缝，不再新建第二套预算或审批平台。

## 6. 测试与独审证据

原始日志位于 `var/codex-goals/delivery-seams-fix-20261010/`，不提交凭据或教材正文。

| 检查 | 最终状态 | 证据 |
|---|---|---|
| 最小算法 RED | FAIL（预期） | `root-red.log`：4项比较、后备、首范围饥饿反例在原代码失败 |
| 真实 adapter RED | FAIL（预期） | 最初32项源端状态、选章边界反例失败，保留实施证据 |
| 后端定向最终集合 | PASS，374 | `final-targeted.log/exit`：Item2原Profile Provider、资源actual adapters、durable桥、比较/恢复、product-v2课程/快照、runner准备、公开503保护；不是完整Backend |
| 最新隔离 PG | PASS，2 | `owned-pg-review-green.log/exit`；新库 `studyplan_test_delivery_seams_87048ae4`。真实DB；HTTP/Reader合成或Mock，无真实教材资格主张 |
| 前端定向 | PASS，14 | `node --test tests/planning-facts.test.mjs tests/planning-render.test.mjs`，真实组件+保存的HTTP shape/合成显示分支 |
| 前端构建 | PASS | `npm run build`，tsc与Vite成功，72 modules |
| Ruff / diff | PASS | 仅受影响文件，无全库重构 |
| 独立审查 | PASS，指定范围 | 独立上下文 Sol6.1 xhigh 请求；P1旧正文身份、P2标题漏接、P2授权重复读取均关闭。PG为只读源码/实际日志复核；独审未另建数据库 |
| 浏览器、真实模型、教材、Reader、完整课程闭环 | NOT RUN | 未消费任何外部额度或开启收费 acceptance |

中间失败均保留：早期综合定向运行1/3/5项 FAIL；Prompt断言字符串和Web fixture来源不一致已纠正；旧PG日志1 PASS是早期源码时点。新增product-v2 PG fixture最初在同项目插入两个初始根，被原保护拒绝（1 PASS/1 FAIL）；改为新项目首次冻结，未改根校验器或失败库。最终2 PASS只引用最新日志。runner默认Temp权限及过长pytest参数ID造成setup FAIL，改工作区临时目录和短ID后27 PASS；前端Vite初次因沙箱realpath EPERM FAIL，同一构建在批准执行环境复测PASS。没有把以上历史失败删成PASS。

## 7. 下一真实批次与剩余边界

以下为现有 owned policy 的条件预约计划，不是本轮新授权或现金硬门禁：

| 指标 | 现有候选整批预约 |
|---|---:|
| Goal / Capability / Reader / Curriculum | 1 / 1 / 6 / 1，合计9模型 |
| 输出预约 | 3×4096 + 6×1024 = 18,432 tokens |
| 教材搜索 | 6请求 |
| 正文 | 6操作，最多12 HTTP，总wire bytes≤393,216 |
| Durable请求 | 9模型 + 6搜索 + 12正文 = 27 |
| 候选 | 最多8 |
| 内部费用预约 | 186,000，保持原单位，非人民币 |
| 本准备脚本 metadata | 0；未来价格/余额最多2次仍需独立授权 |

本次有界选章不增加目录/commit HTTP，不能因此无限探索。普通Web、Notebook/HTML/PDF正文，以及单章/README超过16KiB的阅读仍未支持；它们是阅读边界，不是“外界没有好资料”。MCP理论与实践、跨能力新增scope仍需各自真实正文证据。六Reader预算不能保证全部必学均有资料且完成充分比较；不足应保持缺口/比较不足，不另开Root追绿。

下一批还必须完成可追踪真实 runner、重新核实授权/账号/价格/原始usage，并独立评审真实资料和课程；任何受控报价都不能替代尚未证明的严格人民币现金上限。未批准新模型、搜索、Reader或正文请求。

## 8. 修改清单与结束

- 生产范围：`teaching_resource_research.py`、资源 `models.py`、`v2_planning_runtime.py`、Item2 `capability_planning_contract.py`、GitHub/Tavily/TeachingBody 三适配器、前端 `Curriculum.tsx` 与 `facts.ts`。
- 新增四份后端unit反例（adapter/durable/research/runner）及一份owned PG接缝测试；更新相邻四份资源unit和两份前端测试。
- 新增 tracked preparation脚本、本报告，prepend唯一 progress，保留旧历史字节。未修改 curriculum领域快照、架构合同、Policy、数据库结构、Worker或正式配置。
- 回滚：保留本地checkpoint，以后仅通过新revert提交撤回本次变更；不reset历史Run、回执或账本。

`DELIVERY_SEAMS_OFFLINE_FIX_PASS`

`OWNED_PAID_RUNNER_PARTIAL`

`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`

`STOP`：不 push、merge、deploy，不自动执行新真实验收。
