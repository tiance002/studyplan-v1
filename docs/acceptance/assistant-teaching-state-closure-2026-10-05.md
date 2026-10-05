# Learning Assistant V1.1 Teaching State Closure — 非收费 PASS / 真实教学 FAIL / STOP

## 用户现在新增能做什么

未来新自然会话使用冻结 `issue-ledger-v1`：服务器分配问题 ID，从精确成功 turn/receipt 重建教学状态；第二轮只展示未解决问题，两轮后只解释未解决问题。总结教学后本地提示重新表达，候选仍由用户明确采用或修改后交给原正式保存服务。界面保持自然聊天，没有新增 DTO/API、迁移或前端渲染结构。

本轮实际真实总结四轮与明确保存 PASS；真实实践第三轮虽正确直接教学，但没有最终 Prompt 候选，因此完整助手核心验收 **FAIL**，不能标 `LEARNING_ASSISTANT_CORE_PASS`。整体 **STAGING_BLOCKED / NOT_READY**。

## 基线与实现

- 分支 `feat/n1-resource-discovery`；保留基线 `09c8242b1df64f9dc641f67981d2ff967162b210`，本批实现为后继提交。最终 SHA 见最终答复和 `var/assistant-teaching-closure-20261005/git-final.json`。
- Migration head `0025`，没有修改任何 migration。
- 新模块 `backend/app/domain/assistant_teaching.py`；原 Application、PgAssistant、provider adapter 和 build_input 接入新 marker，真正 legacy turn 保持原路径。
- 同一调用链闭合 frozen binding/state/hash、独立 submission event、触发原文、成功 result_ref/attempt/schema/protocol、保存消息内容。破链 fail-closed；分页和 fresh composition 读取时从历史来源重建，不使用客户端或模型业务身份。
- 初轮按顺序生成 i1..iN，最多 5 问；保留“不制造缺口”的现有规则，实际少于 3 可接受，初稿正确可直接给候选。真实代表分别形成 3/4 问。
- 全 ledger 每轮精确评价一次；resolved 单调不回退；本次新 resolved 的原问题也不能挂在另一 unresolved ID 下复问。自由 reply 为回执事实，不渲染具体问题，避免其绕过服务器问题集合。
- Summary 首次直接教学后可再纠正一次；随后下次 Send 在派发前拒绝，仍保留主区非 AI 正式保存和菜单新会话。没有每问题计数器、额外 judge 或多模型调用。
- Practice teach 的非空 proposal 会投影为 ready_to_draft；**目前仍接受 proposal=null 的 continue 分支**。真实第171笔落入该分支，这是本次最终 Prompt 收口失败的明确合同缺口。STOP 后没有继续修改该合同或补发第8次。

## 分层验收

| 层次/内容 | 状态 | 实际证据 |
|---|---|---|
| request163/164 原响应 fixture | PASS | 原 body SHA 保留；手工主题映射与派生结构反例单独标记，非历史 wire；分别隔离已解决复问、第二轮提前 teach |
| 新 unit/合同边界 | PASS | 51 项，`unit-teaching-final.xml` |
| 相邻 unit/contract | PASS | 最终 183 项，`unit-contract-final.xml`；原 planning known-invalid-json/预算保护不变 |
| 新 owned PG/API/普通 Worker | PASS | 11 项，`pg-teaching-final.xml`；精确来源重建、6破链、分页、legacy、unknown不重发、纠正上限、原正式保存 |
| 相邻 owned PG/API | PASS | 47 项，`pg-adjacent-first.xml`；3条 Windows subprocess reader UTF-8 线程 warning 保留，测试/migration退出0 |
| actual owned API + MockTransport | PASS | Summary4/Practice3，7 Fake HTTP，两模式采用/改稿/幂等/默认恢复，`fake-api.json` |
| 前端/build | PASS | 61 项及 build 的原有效证据，输入 SHA 核对后复用；前端/DTO/OpenAPI源码未改 |
| Edge actual Plan/API | PASS | 剩余问题、无内部ID、Summary本地重新表达、Practice候选、两模式采用/改稿、主区正式版本、我的会话、刷新/退出/重登录；恢复/保存新增请求0 |
| 原生备份/新库恢复/forward | PASS | 只读 snapshot，dump343009 bytes；14消息/7turn/8正式保存/4Summary/4Prompt精确恢复；服务重建与全部 ledger/public view 一致；0025 |
| free binding/DNS/TLS/security | PASS | 无授权HTTP/provider调用，manifest每Send1次/output4096，repair2全局不变 |
| 真实 provider/JSON/应用 | PASS | 7笔均HTTP200、stop、严格JSON、7 Run succeeded，unknown0；不能改成 failed |
| 真实 Summary 四轮+正式保存 | PASS | 第165–168笔，所有原issue重新表达后resolved，原服务保存1次/幂等/PG回读，保存0请求 |
| 真实 Practice 剩余保护 | PASS | 第169–171笔，i1 resolved后不复问；第三回复只teach i2/i3/i4，无第三轮盘问或范围扩大 |
| 真实 Practice 完整候选链 | FAIL | 第171笔 `phase=teach, proposal=null, status=continue`，没有最终Prompt |
| 真实 Practice 正式保存 / paid Edge | NOT RUN | 失败后STOP，没有候选可保存，不继续收费或后续验收 |
| native beforeunload | NOT RUN | 用户明确留到本人体验验收；未阻塞核心修复 |

Summary第二轮只回答了“输入是数据”，未说明首轮复合问题中的校验位置，所以3个完整issue仍unresolved。这笔不能计作 resolved 消失正例。该正例由 Fake/PG 和真实 Practice 第二轮提供；真实 Summary第三輪解释这3个remaining、第四轮重新表达后全resolved。

原 RED import FAIL 保留。新PG初次夹具缺 proposal_message_id、immutable fault injection和public DTO比较错误只修夹具；首轮仅工具输出，无落盘文件，最终完整11项XML与日志留存。owned harness 首建private目录错误留下两空库，复用同两库续接；没有重复建第二份代表。最终只读审计首次Cursor取值错误无写入，修正观察脚本后完整核对PASS。

## 唯一真实代表与用量

- Acceptance `assistant-teaching-closure-synthetic-94c37d3ce90a`，新 owned business `studyplan_test_assistant_teaching_business_db1cb8ba`、checkpoint `studyplan_test_assistant_teaching_checkpoint_51dac9a8`。没有 planner generation 或本人 Run。
- 累计 **164→171/280**，剩余 **109**；本轮 **7 normal assistant.coach、repair0、unknown0**。未追加额度，280授权只一次。
- 实报 **13648 input + 1960 output = 15608 tokens**；金额 `NOT OBSERVABLE`。每Send恰好1请求，保存/恢复0请求；全部 finish_reason=stop，无length/truncation。
- request/result165–171、raw wire/body/receipt、PG精确attempt/usage/成功Run对齐 PASS。全局新增 completion append-only，407个旧文件及.env SHA保持，163/164原结论保持。
- 新paid库14消息7turn，仅1正式Summary、0 Prompt，task仍pending。聊天/保存不写学习完成或认证事实。
- 产品搜索/外部RAG0，原产品库写入0，正式入口/正式Worker/部署/push/merge/全局配置 NOT RUN。

## STOP、风险与下一安全动作

本轮已到 FAIL 并 STOP。没有第8笔、重试、repair、第二Acceptance、旧failed/unknown恢复，余额不自动消费。非收费成果可审阅，真实 Practice 提示词收口仍未Verified。

后续仅有界合同 Goal：保留第171笔原响应作为失败fixture，评审将新格式 Practice在两轮后teach必须产生完整非空proposal/ready_to_draft（空候选拒绝），覆盖同因正反例及PG/API，再决定是否授权下一真实代表。不能只加催促指令、补第8次或静默把空候选转成正式稿。未实施这些后续变化。

回滚：本批未进入原产品库或正式入口，关闭本批临时 owned API8045/Worker和UI5202并保留所有库/备份/证据。原8034/5194不操作。后续若回退源码，须保留新marker读取兼容，不得把新冻结数据降级成legacy或重写历史。

开发路由请求root关键逻辑Sol6.1/xhigh、有界测试Sol6.1/medium、fixture提取Luna/medium；实际解析均 NOT OBSERVABLE，不修改全局配置。子任务边界独立、无同文件并行改动，整合同问题反例/复核。

证据目录：`var/assistant-teaching-closure-20261005/`；完整分层/每笔SHA与token见 `final-audit.json`。私人DSN/账户/dump仅本机private目录，不输出到报告。
