# F2-negative-extra-task 与当前路由优化（2026-10-04）

## 用户现在新增能做什么

合法的“**不要求照搬其工程结构或新增工程任务**”不再被 structure/repair 门禁误判。正向新增任务、同句混合正向义务、跨字段义务仍被拒绝。GR binding、Agent7路线、canonical/来源/practice权威及repair2保持。

本轮新生成了完整 synthetic Draft，**尚无已确认 Plan**。新发现A6来源绑定缺口，按用户边界 STOP，未进入下一开发阶段。

## 四层结论

| 层 | 状态 | 证据与实际限度 |
|---|---|---|
| F2合同与离线/Fake | PASS | 173个不同unit/contract例；F2矩阵85例+旧focus32例；相邻合同56例；另有28个收费harness离线安全反例 |
| 新owned PG教学 | PASS | 4场景：全Fake RAG及精确48/49/50原响应；真实checkpoint、普通生成/Draft/confirm/SQL读回，repair0；新测试库已回收 |
| 免费真实binding/DNS/TLS | PASS | 原安全guard、公共DNS、CA/hostname TLS；真实模型HTTP0；实际manifest37normal+2repair=39，上界89/100 |
| 新真实outline/调用生成 | PASS | 18structure+18practice逐阶段canonical；所有38次provider known/stop；技术Run succeeded与Draft持久化 |
| 新真实代表整体教学/来源 | FAIL | 46来源slot为45PASS/1FAIL；A6首reference丢失冻结MCP10.1来源/章节，真实Draft与PG相同 |
| 本轮真实synthetic confirm/新Plan/Edge | NOT RUN | 新独立缺口触发STOP；未启动消费服务、未确认、未发布 |
| 既有GR/刷新重登录/System/MCP/Node Edge | PASS | 复用上一轮实际HTTP+owned PG+Edge证据；94消费者文件hash完全相同。本轮未重复旧昂贵验收 |
| 本轮前端build | NOT RUN | 消费者代码/构建产物未变；原build及Edge证据保持 |

**F2_PATCH_PASS；PAID_REPRESENTATIVE_PATCH_FAIL；BLOCKED / STOP；整体STAGING_BLOCKED / NOT_READY。**

## 修复与合并复核

唯一业务差异是`backend/app/agent_workflows/planning_structure.py`中`_teaching_text_errors`及局部私有helper/常量：使用现有正向action vocabulary的共同matcher，逐动作判定否定，字段/逗号/分号/转折限定子句范围，新明确义务截断协调否定；不把含“不要求”的整句豁免。覆盖“不仅/not only”和“必须不/must not”、Kubernetes/训练/付款/任意命令/Cloud合法实践。此为有界规则与有证据案例，不能宣称任意自然语言语义证明。

原48/49/50三份A1 normal/repair content逐字节作为fixture；旧46–50五份HTTP正文、response与receipt和失败Run全部保留。RED为62PASS/41FAIL；整批GREEN117PASS，源/test运行期hash一致。普通调用和repair均用同一合同，耗尽repair2后不再派发。

同一问题的测试矩阵与独立复核由同一有界任务一次完成。安全harness核对另确认首outline必须严格`stop`，本地未派发拒绝不计intent/receipt；真实HTTP后异常仅一请求并unknown STOP。生产F3没有修改。

## 唯一新真实代表

- Acceptance：`f2-negative-task-agent7-rag-synthetic-48ea731e4a48`
- Run：`run_9f6db411f8d1415a818e7d3f69e14ab8`
- Draft：`drf_aa6f1f8b3478527185cdb1f2c009fb22`，`awaiting_approval`；未修改为failed、未代用户确认。
- 冻结manifest：`f0ef4458ad2862ac7b67c2e9b8480a0c53c088fd7f7bf8fc78558d3be12a465a`；pack hash：`2fdea28793bda458a652f9c3aec25b99b2c32aee39b72e55e02a58a318b6199a`。
- 格式：`stage_skeleton_v1` + `reviewed_structure_v1`，既有focus格式/版本完整。
- 来源版本：Agent `agent.application` v7，当前Agent7审核事实；未改包/canonical/资格/公开API或迁移。
- 实际冻结：A0–A8通用Agent主线（Framework A5、MCP A6、系统评价A7、Pi小型核心A8）→G0–G6详细RAG→GR成熟切片→GT迁移；18stage/16knowledge/58LearningUnit/18formal tasks/46resources/37extensions。
- A1新实际响应为3单元，**没有重复旧exact否定句**；真实新响应的合法否定通过，旧exact句由保留fixture与ownedPG证明。
- A2为5教学单元绑定单一canonical node与单一任务；不以旧Fake的3个单元限制合法细分。
- GR保留RAGFlow和WeKnora两张独立冻结候选卡与各自guidance/Prompt，仍仅一个正式任选任务；metadata-only repo空章节合法。本次未改GR binding。

### 真实outline

| 项 | 实际值 |
|---|---:|
| v6.5 input tokens | 209,998 |
| 本轮Agent7+RAG input tokens | 3,673 |
| 实际下降 | 98.25093572% |
| output tokens | 1,396 |
| finish_reason | stop |
| JSON / 18stage keys / durable ledger | PASS |
| length/truncation | 未发生 |

都是provider实际usage，未用字符估算替代token。首笔完整门禁后才进入structure。

### 用量

37normal（1outline+18structure+18practice）+1已知local repair=**38次**，quota **50→88/100**，剩12；硬上界39/repair2未增加，unknown本轮0。A6唯一repair用于去除不允许的顶层fields，修后合同通过。38次全部known、HTTP正文与receipt完整保存；provider input合计85,528/output42,965；保留output预算233,472≤241,664。生成后模型请求增量0，搜索新增0（原6/1000账本保留）；原历史unknown继续保留，不重派。

## 新独立阻断与STOP

A6 order0 `reference`的冻结source为`src_v612_1f6742530460b0908234a6d3`，章节`sec_v612_d79f6a54976fb31d5159ac60`（10.1 MCP协议角色）。实际Draft与owned PG为`source_ref=""`、`source_version=0`、空section_refs/ordered_sections并出现官方教程fallback。其它45slot按身份、角色、顺序、章节精确相同。

这是独立来源绑定缺口，底层生产根因尚未调查/修复。本轮不将其纳入F2修复、不补来源、不放宽权威、不恢复Run或再次收费。真实PG最终只读核对：Run succeeded、Draft awaiting_approval、approved plan/publications0、nodes16/units58/tasks18、38succeeded attempts；job completed且保留terminal lease token（不是active running job），无新worker启动。确认与Edge脚本仅准备，全部NOT RUN。

## 基线、模型路由与回滚

实际branch=`feat/n1-resource-discovery`，起止HEAD=`1a3262e85296c95d3dfb4349d0d4ef83438f17da`；历史df10870检查点为祖先PASS。沿用组合未提交v6.11/v6.12/v6.13/GR工作树，未reset/restore/回退/切分支/commit/push/merge。67候选文件、binary patch、692个unique历史文件及路由原文已作受限zip备份，CRC/SHA PASS。692旧历史/.env/旧50对账本字节不变；受保护.workbuddy/design-preview未操作。真实只写本轮新owned业务/checkpoint库，原产品库/正式入口/正式Worker/RAG均NOT RUN。

最新路由已持久化到AGENTS与model-routing-policy：Luna默认low/medium用于机械提取/哈希/清单/报告/明确符号；Sol6.1 medium用于有界修改与常规测试；Sol6.1 xhigh用于安全/预算/引用及有证据的升级问题；合并同一问题边界测试与复核，避免多个会话重读长历史。Solmax禁用、Astra停用、并发/单一权威负责人规则保持，无全局配置修改。当前F2权威/费用复核请求Solxhigh、PG常规执行请求Solmedium，实际解析均NOT OBSERVABLE。

回滚仅针对本轮planning_structure局部差异，从受限组合基线取对应符号；保留已通过的F1–F4/GR及所有历史/新response、receipt、账本、Draft和owned两库，不reset或整树restore。未自动回滚。

下一安全动作是用户给出新的有界Goal后，先定位A6已冻结MCP来源在哪一消费/保存步骤变为空。剩余12次不自动派发，不自动部署、推送或继续开发。

## 证据

- `var/f2-negative-extra-task-20261004/unit/{red,green,contracts}.json`、contracts.xml、boundary-matrix.json；原fixture/provenance。
- `pg/execution-report.json`、final.xml、各场景manifest/Plan/workspace/SQL验收；4场景真实PG PASS。
- `review/combined-review.json`、harness-probes.json；非收费整批review与28安全反例。
- `nonpaid-gate.json`、free-preflight.json、prepaid-invariants.json、final-invariants.json。
- `paid/outline-gate.json`、run-report.json、generation-complete.json、stage-protection.json、responses/51..88.{body,json}。
- `paid/teaching-review.json`、teaching-review.md、final-pg-readonly.json、reconciliation-before-confirm.json。

私有DSN、凭据、.env内容仅留本机受限文件，未输出。
