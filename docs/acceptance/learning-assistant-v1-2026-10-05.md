# Learning Assistant V1：非收费 PASS / 真实代表 FAIL / STOP

日期：2026-10-05。分支 `feat/n1-resource-discovery`；基线 `af2f3ae3fad226509ef6d149455a507acce49663`，保留后继及既有成果，无 reset/回退。源码与本报告在同一本地提交；实际最终 SHA 见本轮最终答复及 `var/learning-assistant-v1-20261005/git-final.json`。迁移 head：**0025**（0024 未改）。

## 用户现在新增能做什么

已确认路线上的“开始总结”创建绑定 Plan/阶段的 summary 会话；精确任务上的“开始实践”创建绑定 Plan/阶段/task 的 practice 会话，并打开右侧助手。工作稿、追问、助手回复各自持久化；追问不替换工作稿。用户明确保存后，原 Summary/Prompt 服务创建正式修订，主区显示正式版本。“我的会话”只读恢复两种会话，刷新、退出和重登录可恢复服务器原文。

多轮聊天与正式产物分开。新聊天不写正式 Summary/Prompt、任务验收、知识 VERIFIED 或阶段完成。主区保留任务要求、正式原文、历史、导出、成果与 USER 决定；直接编辑正式原文作为折叠非 AI 路径保留。没有声称本人接受或交付就绪。

## 分层结果

| 层 | 结果 | 实际证据与限制 |
|---|---|---|
| IMPLEMENTED | PASS | 新会话/API/DTO、0025、队列用途、正式保存衔接、两种页面入口与历史恢复 |
| Unit/contract | PASS | 最终 156；包括原 review、规划预算、Known Invalid JSON 回归与真实额外字段 fixture |
| Fake/MockTransport | PASS | 两种模式各初稿→追问→改稿，真实 adapter/ledger/普通 owned Worker；6 次本地 Fake HTTP，产品调用 0 |
| Owned PG/API | PASS | 最终 34；普通 app-role/RLS、scope、幂等、CAS、lease/取消/unknown、独立 submission 合同、回执恢复 |
| 前端规则/build | PASS | 51（24 新助手 +27 既有）；build 67 modules |
| Edge 非收费闭环 | PASS | 实际 PG/API，两种模式、明确保存、主区刷新、CAS、恢复、断连、旧路线只读、无模型保存、760×860 抽屉与 Escape 焦点返回 |
| 原生 owned 备份恢复 / RC 前进 | PASS | 新 owned 恢复，逐表行哈希精确；旧 RC 副本 0024→0025，旧行保持 |
| 免费 binding/DNS/guard/TLS | PASS | 部署 `deepseek-flash`，单轮 output cap4096、max_requests1，TLS1.3；无凭据 HTTP，无模型请求 |
| PAID VERIFIED | FAIL | 第2条真实回复多出 `message_id`，严格拒绝；已停止，后4次 NOT RUN |
| USER ACCEPTED / DEPLOYED | NOT RUN | 本人新规划、本人体验接受、正式库/入口/Worker/部署均未操作；F17/RAG仍 NOT RUN |

**不能标 `LEARNING_ASSISTANT_CORE_PASS`。当前结论：非收费 PASS / 真实代表 FAIL / STOP；整体 STAGING_BLOCKED / NOT_READY。**

## 数据与调用合同

- 5张最小附表：`assistant_conversations/messages/turns/receipts/formal_saves`。冻结 owner/project、Plan版本、stage/task、评审依据 hash、精确工作稿与触发消息；消息、turn、幂等回执不可变，RLS 强制作用域。
- 新用途 `assistant.coach` / `assistant-coaching-v1`，单条发送最多1请求；不继承规划 repair2，不自动 retry/repair。输出唯一字段 `reply`，非空且有界；extra fields 严格拒绝。
- 复用个人/部署模型配置解析、`PgAttemptLLM`、ai_runs/jobs、标准 Worker、短 review graph、budget/claim/fence、原 Summary/Prompt 保存服务。未伪装为旧正式 attempt 或 planning Run。
- 每轮入队冻结当前完整工作稿、消息意图、白名单教学要求与最多6个已完成问答轮次；去除重复稿件，42000字符上限在派发前拒绝；不静默截短，不发其他会话/项目/私有全文。
- 明确 consent 后发送；绑定或预算不可用时仍保存精确原文，不建不完整 Run。每会话一个活动回复，纳入已有 actor/project 上限；同目标 unknown/过期 dispatched 阻止换会话重发。
- 正式保存先持久化 reservation，调用原服务 CAS/幂等，关联失败返回“已保存、关联待核对”；同一键回查同一正式修订。409保留本地稿，显式 GET 核对后才解除保存冲突；自动轮询不解除、不 POST。
- provider回执已存而回复落库中断：保留 fence/队列，恢复只读旧回执，1 HTTP /1成功回复。queued cancel0请求；可能已派发则待核对，迟到旧 lease 不得落库。旧版会话可读，不能向新 Plan 误发/误存。
- 旧 OpenAPI paths/components 逐项语义比对 PASS；大 JSON diff 包含生成器重排。旧 payload/fingerprint、canonical、pack、任务、完成规则、planning repair2保持。

## 非收费端到端事实

主 Fake owned：`studyplan_test_assistant_v1_business_fe5c3e04` / checkpoint `studyplan_test_assistant_v1_checkpoint_ecc5d4c9`。合成 Draft 经原发布服务明确确认；没有本人或旧 paid Draft确认。

summary初稿“输入直接等于执行、超时算成功”→追问→完整改稿→明确正式总结；practice“只返回答案”→追问验收→完整改稿→明确正式 Prompt。原文、所评稿件 ID、正式文本独立核对。两种正式结果均经真实 API/PG在主区显示。另一个真实 API writer 保存v2，原v1侧栏保存409，本地精确稿保留；显式读取后确认v3，不自动覆盖。

额外消费：收起/展开未发送缓冲保持；导航不换会话scope；刷新与退出/重登录只读恢复；owned API停机时读取失败保留文字，重启后GET恢复；窄屏抽屉/Escape焦点返回，viewport最终恢复；新合成Plan3发布后Plan2会话只读；模型binding不可用时原文持久化、Run0，并可明确正式保存。阶段仍0/1，任务pending。

原生备份恢复覆盖2会话/12消息/6turn/2正式关联，以及原服务1summary/1prompt。目标 `studyplan_test_assistant_v1_restore_assistant_95cd6bc6` 精确普通app-role回读；`studyplan_test_assistant_v1_restore_rc_e2f1b08b` 从旧owned RC源 `studyplan_test_rc_p2_native_f482d3a3` 原生恢复后前进0025，所有旧表行哈希保持。源备份事务只读，不写原产品库。

## 唯一真实助手验收与 STOP

新 Acceptance：`assistant-v1-synthetic-bdeb680f4573`。新 owned business `studyplan_test_assistant_v1_business_20db51db`、checkpoint `studyplan_test_assistant_v1_checkpoint_918a5f47`，全新合成账号及已确认合成Plan。新会话 summary `aconv_728a7dab39d645a4bc17aaa424228c0a`、practice `aconv_9a7711a991d44613aa9345e4b223ca0e`。不是本人规划Run；旧failed/unknown未恢复。

| 序号 | 内容 | Input | Output | Finish | 真实结果 |
|---|---|---:|---:|---|---|
| 161 | 总结初稿评价 | 587 | 665 | stop | PASS：指出输入/执行及超时/成功误解，具体举例，不增正式任务或声称掌握 |
| 162 | 对同一稿的追问 | 1297 | 887 | stop | FAIL：JSON包含额外message_id；provider receipt succeeded，但应用Run assistant_reply_invalid，未写成功回复 |
| 其余4条 | 总结改稿、实践三轮 | — | — | — | NOT RUN：按known失败停止批次，不补用额度 |

第一条观察脚本误查不存在的 `finish_reason` 列；从既有 `response_payload`/GET只读恢复证据，未再发送或执行Worker。第二条原 body、请求、LLM回执、PG回执和失败Run都保留，3条会话消息（2用户+1助手），正式summary/prompt0、任务pending。原body SHA：见已提交 `backend/tests/fixtures/assistant_v1/known_extra_message_id.json`。

已证明的原因是 provider 增加了唯一reply合同以外的字段，不是截断、无回执或unknown。输入含绑定标识是否诱发复制仅为推断，未把它宣称成已证因果。原system已要求唯一reply；追加了不复制/生成message/conversation/run/role字段的明确禁令，未删extra字段让坏响应通过。保留真实fixture经MockTransport→ledger→Worker再次证明fail-closed/无repair/无正式写入。更明确提示的**真实效果 NOT RUN**，不会把离线回归当收费复验。

受控无Worker/无provider凭据的真实回执消费页实际Edge显示第1条成功评价、第2条失败原文及恢复列表；刷新新增请求0。失败文案改为可理解的“回复不符合要求，原文保留”。

## 用量、保全、风险

- 本次授权仅登记一次：previous_cap200、additional80、新累计cap280、授权前实际used160、余120；历史160 request/result和`.env`哈希保持。
- 本轮2产品请求，repair0、unknown0；累计 **162/280，余118**。总实报1884 input +1552 output =3436 tokens；金额 NOT OBSERVABLE。两笔请求/结果均append-only，provider receipts与PG与保留raw body一致PASS；应用失败另外记completion，不改写provider成功回执。
- 新增真实搜索/RAG0。未改cap/model/temperature，未改全局配置；没有原产品写入/迁移、正式入口/Worker、deploy/push/merge。`.workbuddy/`、`design-preview/`未操作。
- 风险：真实模型仍可能违反单字段输出合同，当前严拒会使回复失败。提示澄清不能证明任意用户输入都可靠；summary改稿和实践真实三轮尚未验证，不能正式发布本功能。
- 回滚：本地提交可审阅后增量revert，保留所有证据/owned库；0025有会话历史时拒绝downgrade，不能用删表丢失原文作为回滚。正式库0025上线须另行授权和备份/迁移门禁，本轮未执行。

## 可复现命令与证据

后端命令（工作目录D:\studyplan，PYTHONUTF8=1）：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest backend/tests/unit/test_assistant_v1.py backend/tests/unit/test_b3_provider.py backend/tests/unit/test_batched_budget.py backend/tests/unit/test_known_json_repair.py backend/tests/unit/test_rc_runtime_budget.py backend/tests/unit/test_prompts_v2.py backend/tests/unit/test_summaries_v2.py backend/tests/unit/test_stage_summaries.py backend/tests/contract -q --tb=short
.venv\Scripts\python.exe -X utf8 -m pytest backend/tests/integration/test_assistant_http_pg.py backend/tests/integration/test_assistant_protocol_pg.py backend/tests/integration/test_summary_http_pg.py backend/tests/integration/test_prompt_http_pg.py -q --tb=short
```

两命令exit0，最终156/34 PASS，前次154/33有效记录与初轮fixture/composition FAIL保留，不累加重复运行次数。frontend目录：`node --test src/features/learning/assistant.test.mjs src/features/learning/assistantRestore.test.mjs tests/*.test.mjs` 51PASS、`npm run build` PASS，exit0。

证据根 `D:\studyplan\var\learning-assistant-v1-20261005`：baseline、evidence-packet、unit-contract-closure.xml、pg-closure.xml、fake-pg-bindings、edge-checks/截图、native-restore、free-preflight、final-audit、runtime-ownership；paid目录保留原body/receipt/turn/content-check/stop/真实Edge。初轮非收费gate记录对应收费前源码，最终提示同因改动由closure证据覆盖，未覆盖原gate。请求模型root/关键复核Sol6.1 xhigh、实现Sol6.1 medium、机械库存Luna low；实际解析均 NOT OBSERVABLE。

## owned体验入口与停止方式

本批临时API/Worker/UI **均已停止**；只停止确证本批归属的8041/8042/5198/5199进程，原5194等服务未触碰。库与备份保留。

可在两个本机终端重启无Worker、无真实provider凭据的保留回执体验入口：

```powershell
Set-Location D:\studyplan
.venv\Scripts\python.exe -X utf8 var\learning-assistant-v1-20261005\view.py
```

```powershell
Set-Location D:\studyplan\frontend
$env:STUDYPLAN_API_URL='http://127.0.0.1:8042'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5199 --strictPort
```

访问 `http://127.0.0.1:5199/`；合成账号 `变更用户c2be026d57f8`，合成密码 `isolatepass1`。此入口只消费保留真实回复；助手发送binding不可用，不能继续收费。两个终端Ctrl+C停止，勿杀其他服务。私人DSN/密钥不写报告；private文件只留本机。

下一安全动作：审阅本批差异与失败fixture，评审提示澄清的后续新有界真实助手验收；本批不继续用118余额。本人新规划仍须本人明确提交；正式发布需对应原库迁移、入口/Worker/部署授权及本人接受；RAG另批。STOP。
