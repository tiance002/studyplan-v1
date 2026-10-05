# Learning Assistant Final Closure — 分层验收与 STOP

## 用户现在新增能做什么

正式 React 的“我的会话”按阶段总结/实践辅导查找与恢复会话，卡片统一显示已保存/待确认/未保存、最近消息、时间与选中态；右侧简洁 Chat 以 Header → Timeline → Proposal → Composer 为中心。候选可展开/收起、采用或轻量改稿后通过原服务保存；历史路线只读保持。

Practice 两轮后有 remaining 时，新 turn 冻结 `practice_teach_with_proposal`；必须只教学精确 remaining 并返回完整非空候选，成功由服务器投影 `ready_to_draft`。第171笔原结果在新合同下明确拒绝，但历史 provider/application 成功及教学 FAIL 均保持。

## 基线与实际代码

- branch：`feat/n1-resource-discovery`。
- 启动 HEAD：`31e739f5d395c312042bf9799ddfa37523e8f94d`，保留当前成果，未 reset/切分支。
- 最终 actual HEAD 与 clean tracked 状态见 `var/assistant-core-closure-20261005/git-final.json`，本批仅本地普通提交，不 push/merge。
- migration source/owned business head：`0025`，没有新增或修改迁移、公开 API/DTO、conversation schema。
- reference：`D:\studyplan\var\prototypes\conversation-assistant-review-20261005\index.html`。
- SHA256：`8c889d939cd63d93207d6609c4c8a46428cb88787455aadb4bda09ad2158984d`。
- 已批准桌面 reference：同目录 `desktop-final.png`；HTML和原图未改。

正式 UI：`frontend/src/components/LearningAssistantPanel.tsx`、`assistantProposalScroll.ts`、`frontend/src/features/learning/SupportingPages.tsx`、`assistantState.ts`、`useAssistant.ts`、`frontend/src/style.css`；相应 assistant/restore/proposal scroll 测试。

后端：`backend/app/domain/assistant_teaching.py`、`assistant.py`、`backend/app/application/assistant.py`、`backend/app/infrastructure/db/assistant.py`、`backend/app/infrastructure/providers/openai_compatible.py`。新增171派生不可变fixture、final Practice unit反例矩阵和 owned PG integration 文件。原171 body/receipt文件与SHA保持。

## 合同验收

| 要求 | 结果 / 直接证据 |
|---|---|
| 派发前 expected kind | PASS：新Practice build_input冻结，submission event独立比对，kind或event缺失/篡改0派发；真正legacy无字段保持原读取 |
| exact remaining / resolved / new issue | PASS：精确ID集合、数量/重复/遗漏校验；resolved和unknown拒绝；真实174仅i1/i3/i4，i2不复教 |
| 禁止第三轮 / followup | PASS：final shape只reply/teaching/proposal；phase/status兼容字段不得降级；followup、question、第三轮phase拒绝；解释含问号拒绝；真实无第三轮问题 |
| 必须 proposal | PASS：171/null/empty/blank明确missing_required_practice_proposal；wrong type、20001、NUL、surrogate拒绝；正例ready_to_draft，最多20000 |
| 原任务与执行声明保护 | PASS：已知部署/付款/训练/K8s/任意命令/新增任务和已执行声明反例；同子句否定与新正向义务分开。真实772字候选逐项人工对照冻结目标/范围/验收，无额外当前任务或已执行结论 |
| extra非权威 | PASS：额外type/业务ID不成为渲染、状态、保存权威；真实174 type=json_object无流程权限 |
| JSON/unknown/truncation/security/budget | PASS：严格JSON、失败或unknown不变成功；无repair/HTTP retry；cap/六个正整数/类型/哈希/endpoint guard不放宽 |
| 历史171 | PASS：旧合同仍continue/null，新合同拒绝；旧Run不改状态、不恢复、不重派；555历史/config/reference hashes精确保持 |
| Summary | PASS：共享unit/PG及Fake4轮回归；本批真实Summary NOT RUN，既有165–168真实PASS原结论保留 |

确定性范围检查覆盖明确的已知能力逃逸模式；本次真实候选另外逐项人工核对，不宣称任意自然语言的通用语义证明。

## 非收费与正式 UI

- 完整 unit/contract：**1356 PASS / 2 NOT RUN**。2条为 Windows 无提权目录symlink创建不可用的既有安全检查，未以放宽权限追绿。定向助手/预算/安全/import矩阵 **177 PASS**（已包含于完整套件，不相加）。XML：`unit-contract-full-final.xml` / `unit-contract-final.xml`。
- owned PG/API/standard Worker：**74 PASS**，含本批13条和相邻61条；冻结state/event、remaining、持久化、successful receipt恢复无重复、正式采用/改稿、RLS/scope、idem/CAS、queued/dispatched取消与unknown protection。XML：`pg-combined-final.xml`。
- Fake API +标准Worker：**PASS**，Summary4 +Practice3、采用/自定保存/幂等/恢复；provider仅MockTransport，新增真实请求0。`fake-api.json` / `fake-wire.jsonl`。
- frontend：**52 PASS**助手/恢复/scroll检查，原前端套件**27 PASS**，tsc+Vite build **PASS**。无新增框架。`frontend-checks.json` / `frontend-targeted.log` / `frontend-suite.log` / `frontend-build.log`。
- Edge：**PASS**，正式React+实际owned API+Fake provider；搜索title/recent/type与筛选、选中、全部三态、Chat/候选、采用/改稿、refresh/logout/relogin、close/reopen缓冲、133/2000/19960字、inline known/unknown、旧Plan只读、390px既有全屏/关闭行为。
- 长内容实际修正两个布局问题：展开/收起保持卡片底部锚定；收起仅重置当前正文scrollTop为0。composer测量高度+24px预留，长候选按钮bottom540.42 < composerTop617.8，末行内滚动可达。相关RED/最终日志与实际截图保留。
- 截图结构人工对照 **PASS**：列表层级与Chat中心保持、无intent/consent/内部ID控件、候选操作明确、错误小型inline、响应式与历史只读未重新设计。
- 初轮unit依赖检查 FAIL（domain导入Application预算类）已以相同六个正整数/cap校验解除反向依赖，预算值不变；首次owned测试fixture取消幂等key复用FAIL已修正测试输入。原RED/FAIL日志保留，最终门禁以以上当前XML为准。

## 唯一真实 Practice 代表

Acceptance：`assistant-core-closure-synthetic-f95d70a84a6c`。
新owned business：`studyplan_test_assistant_core_business_f1af4a11`。
新checkpoint：`studyplan_test_assistant_core_checkpoint_ab386e2c`。
新合成账号/Plan/Practice会话，仅3条 assistant.coach Run；没有规划Run、第二Acceptance、Summary真实调用、repair、retry。

非收费 gate与source hashes固定后，免费binding/public DNS/原endpoint guard/TLS **PASS**，产品请求0；权威账本171/280复核后才派发。

| global request | input tokens | output tokens | finish_reason | provider | application | teaching |
|---|---:|---:|---|---|---|---|
|172|1237|209|stop|PASS|PASS|PASS：集中4问，均属于冻结范围|
|173|1998|290|stop|PASS|PASS|PASS：i2 resolved，仅追问i1/i3/i4|
|174|2511|1171|stop|PASS|PASS|PASS：只teach remaining，772字完整候选，server ready_to_draft|

原正式Prompt保存 **PASS**，formal version1，PG与API精确readback；幂等再次读取没有新版本或费用。Edge实际新owned API消费主区正式原文/我的会话已保存 **PASS**，消费入口无provider binding、无Worker，新增请求0。

累计 **171→174 / 280，remaining106**；本批3次、unknown0、duplicate0、repair0、保存新增0。provider报告5746 input +1670 output=7416 tokens；实际金额 NOT OBSERVABLE。request/result/receipt/body均append-only，原171等历史事实不改。

## 截图与关键证据（绝对目录 D:\studyplan\var\assistant-core-closure-20261005\）

1. `edge-desktop.png`：非收费正式我的会话+助手。
2. `edge-long-expanded.png`：19960字展开末尾与操作。
3. `edge-inline-error.png`：known失败小型聊天inline。
4. `edge-narrow.png`：390×844既有窄屏。
5. `edge-history-readonly.png`：旧路线标签、保存/发送禁用。
6. `edge-paid-saved.png`：真实三轮后会话已保存及候选。
7. `edge-paid-formal-prompt.png`：主区正式第1版与右侧候选。

`baseline.json`、`nonpaid-gate.json`、`free-preflight.json`、`edge-checks.json`、`paid-edge-consumption.json`、`paid/final-validation.json`、`paid/content-check-{0,1,2}.json`、`paid/responses/172–174.*`、`.git/v2-paid-quota-20261001/request/result-172–174.json`。private内仅合成账号/DSN，报告不输出密钥或DSN。

## 最终状态、风险、回滚与本人事项

**LEARNING_ASSISTANT_CORE_PASS / STOP**。整体仍 **STAGING_BLOCKED / NOT_READY**，不把本批核心PASS当完整产品交付。

学习完成事实保护 PASS：实践pending，unit_progress没有新增verified，页面0/1阶段完成；教学/候选/正式保存未生成完成或执行证据。原产品库写入0；正式入口/正式Worker/RAG/启动数据/部署/push/merge均NOT RUN。受保护目录仅git状态仍列为untracked，不操作。

本轮临时owned API8046/8047及Vite5203/5204现已无监听/对应进程；库与证据保留。Edge连接在消费证据保存后断开，后续重新连接/临时viewport reset为NOT RUN，此清理限制不回改已完成的浏览器验收事实。

回滚仅限本批增量源码撤回与关闭owned服务；新冻结kind的兼容读取必须保留，不能通过回写旧turn/receipt或删除证据回滚。正式部署与原产品数据处理另需授权。

本人下一安全动作：审查上述正式React截图，随后在合成环境亲自确认列表、长Prompt、保存和窄屏体验；是否接受产品核心仍由本人决定。本批停止，不再消费余额，不进入发布或其它开发阶段。

开发路由：root关键合同/预算请求Sol6.1 xhigh；独立有界前端/PG Sol6.1 medium；实际解析均NOT OBSERVABLE。没有max/Astra或全局配置修改。
