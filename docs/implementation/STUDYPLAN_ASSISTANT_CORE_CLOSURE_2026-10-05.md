# Learning Assistant Final Closure — 用户批准范围

用户于2026-10-05批准此批连续执行。唯一当前进度仍为 `progress.md`。

## Goal / 基线

以已批准“我的会话 + 学习助手”独立 HTML 为唯一 UI reference，使用现有 React 结构落实页面；关闭 request171 暴露的 Practice 两轮后 teach 无最终候选分支。不重新设计教学、课程、issue ledger、Summary、正式保存或鉴权。

- branch `feat/n1-resource-discovery`，启动 HEAD `31e739f5d395c312042bf9799ddfa37523e8f94d`；保留后继与工作树，不 reset/回退。
- migration head `0025`；本批不得自动新增 migration。
- 权威费用基线171/280，余109；授权不重复登记或清零。
- HTML：`D:\studyplan\var\prototypes\conversation-assistant-review-20261005\index.html`。
- SHA256：`8c889d939cd63d93207d6609c4c8a46428cb88787455aadb4bda09ad2158984d`。
- 已批准桌面参考：同目录 `desktop-final.png`。原 HTML/截图保持不变。

## Allowed changes / Constraints

只改我的会话、学习助手、直接相关前端样式/测试及 Practice 最终响应合同调用链。复用当前 API/DTO、0025 JSON payload/event、队列/预算/回执/RLS和正式 Summary/Prompt 保存服务；不以平行 HTML 页面替代正式 React，不装框架，不改全站导航。

列表与助手状态为已保存/待确认/未保存；轻量本地 title/recent/type 搜索，时间今天/昨天/具体日期，卡片层级对齐 reference。Header/Timeline/Proposal/Composer；无意图 selector、逐消息 consent、内部ID/Worker/技术错误。固定欢迎0请求。Proposal默认6行、可展开/收起、有界内滚动，composer预留测量高度+安全间距；轻量采用/修改后保存。普通错误 inline，unknown核对只能读，禁止自动收费重发。响应式与历史只读只做回归。

新 Practice turn 在派发前由服务器冻结 expected_response_kind。两轮后还有 remaining 时为 `practice_teach_with_proposal`，只解释精确未解决集合，不新增/复问/第三轮；必须完整非空有界proposal，成功由服务器投影ready_to_draft。模型不得降级continue，不repair/retry，不拼接或历史补稿。覆盖范围扩大/已执行声明反例，真实候选逐项人工核对。旧无新字段的冻结turn保持原合同读取；171原provider/application成功和教学FAIL都保持。

## Tests / Gates

全部开发产品真实请求0。顺序：unit/contract（171不可变fixture、正反例、Summary共享、extra/JSON/unknown/截断/预算/安全）→owned PG/API/standard Worker（冻结集合、候选、回执恢复、原正式保存、RLS/scope/idem/CAS/unknown）→Fake完整Practice链/采用/改稿→frontend/build→实际owned API + Fake provider Edge→五类截图人工结构对照。

所有非收费门禁PASS后才可免费binding/DNS/TLS和唯一新Acceptance/新owned business/checkpoint/synthetic Plan/Practice会话。最多3次新的真实assistant.coach：集中提问→部分解决只问remaining→remaining直接teach+完整proposal；无真实Summary。然后原正式保存与PG/API/主区/会话已保存读回，保存增量0请求。

真实任一步unknown、truncation、invalid JSON、复问、第三轮提问、无候选、扩大范围、重复收费、污染、RLS/scope或保存异常立即STOP；无第二Acceptance、额外“试一下”、repair或retry。全部UI/后端/真实/历史及完成保护PASS才允许 `LEARNING_ASSISTANT_CORE_PASS`；整体产品状态另报，不能代替本人/发布接受。

## Evidence / Rollback / Non-goals

本机新证据 `var/assistant-core-closure-20261005/`；启动保护哈希555份历史/config/账本/reference。最终列实际SHA/branch/migration/reference/sourcefiles、分层结果、五类截图、每笔全局号/token/finish/provider/application/teaching、累计/剩余及本人接受事项。

不碰 `.workbuddy/`、`design-preview/`、旧163–171 body/receipt/Run；不写原产品库、不切正式入口/启正式Worker、不RAG/WeKnora/启动数据/部署/push/merge/全局配置。只owned验证Worker。回滚为关闭新owned服务并保留库/证据；源码可增量撤回，不重写新冻结或历史记录。完成立即STOP。

## 执行结果

LEARNING_ASSISTANT_CORE_PASS / STOP。最终[逐项验收报告](../acceptance/assistant-core-closure-2026-10-05.md)；累计174/280余106，唯一新真实Practice3次，保存/消费0新增。整体STAGING_BLOCKED / NOT_READY。
