# Learning Assistant — User Acceptance Prep

## 用户现在新增能做什么

“我的会话”详情尚未读取或读取失败时保留卡片、标题、类型与时间，业务状态位置留空；成功读取后才展示已保存、待确认、未保存。用户可以在隔离体验入口浏览既有合成会话，并从当前路线“开始总结 / 开始实践”亲自体验新的会话。

状态：`PRE_USER_ACCEPTANCE_READY / STOP`。本人接受 `NOT RUN`，整体 `STAGING_BLOCKED / NOT_READY`。

## 代码范围与基线

- 开始 HEAD：`bd6912268cfe33f545b62105c2c7d1f829368d4e`，分支 `feat/n1-resource-discovery`；保留后继，不回退。最终本地后继 SHA 见 `var/assistant-user-acceptance-prep-20261005/final-audit.json` 和最终答复。
- UI 只修改 `frontend/src/features/learning/assistantState.ts`、`SupportingPages.tsx`；测试只修改同目录 `assistant.test.mjs`、`assistantRestore.test.mjs`。
- `assistantListStatus()` 返回三态或 `null`，完整详情缺失时先返回 `null`，不根据 summary 的保存提示猜状态。卡片条件渲染状态；未读取的最近消息位置留空。
- 原 bounded 当前页 detail hydration 保持，未修改 `useAssistant.ts`，没有 N+1 优化或新服务搜索。
- 后端 application/domain/infrastructure、迁移、公开 API/DTO/OpenAPI 差异均为 0。来源与 owned DB migration head 均 `0025`；未运行 backend 全套。
- `.workbuddy/`、`design-preview/` 未操作。650 个历史/config/reference 文件 SHA 保持；原历史 Run/receipt/Plan 与源 owned 库的 12 类核心表内容在隔离副本中精确一致，未改旧结论。

## 免费验证

| 验收 | 结果与证据 |
|---|---|
| 失败复现 | PASS：新状态边界测试先 FAIL，旧逻辑返回未加载或根据 summary 提前已保存；`frontend-red.log` 保留 |
| 前端定向 | PASS：51；summary 初始无业务状态，GET 失败保留字段、后续成功恢复三态；搜索、选中、只读、助手及长候选共享回归 |
| 原 frontend suite | PASS：27，`npm test` |
| TypeScript / build | PASS：`npm run build` |
| Edge + owned API | PASS：安装的 Microsoft Edge 154.0.4258.53，经现有 Playwright-core 驱动；真实 API 提供合成数据，仅一条 detail GET 的 HTTP 503 由浏览器验收拦截模拟。初屏 6 卡业务状态 0；单条失败时状态 5，失败卡保留；恢复后 6 卡、三态齐全；搜索/分类/选中/助手/旧路线只读 PASS |
| 截图人工检查 | PASS：当前信息层级、卡片和 Chat 保持，没有新增内部控件或大 banner |
| 免费 binding / DNS / TLS / guards | PASS：无 provider HTTP 请求；非 assistant purpose、历史 Run、未由用户提交的 Run 被派发门禁拒绝 |
| 产品真实模型 | NOT RUN：准备期间新增 0，账本保持 174/280，余 106 |
| 本人产品验收 | NOT RUN：等待用户，不标 USER_ACCEPTED |

全部新证据：`D:\studyplan\var\assistant-user-acceptance-prep-20261005\`。

最终截图：`edge-my-conversations-final.png`；首屏和单条失败分别 `edge-hydrating.png`、`edge-detail-failure.png`。

Edge 扩展的连接清单连续返回通信失败，未将该连接冒称恢复；页面验证使用本机 Edge 浏览器程序完成，没有替换为 Chromium mock 页面。

## 本人体验环境

- UI：`http://127.0.0.1:5205/`；owned API：`http://127.0.0.1:8050/`。
- business：`studyplan_test_assistant_user_business_a5c03344`；checkpoint：`studyplan_test_assistant_user_checkpoint_36c74c9c`，由既有 owned 合成库复制，无迁移、seed 或内容生成。
- 6 个既有会话含阶段总结、实践辅导及三种状态。它们属于旧路线，保持只读；当前批准合成路线为 revision 3，可由本人开始新 Summary/Practice。准备过程不创建新聊天内容。
- API/UI/owned normal Worker 运行；真实 provider 配置仅存在于该服务进程，未修改 `.env` 或全局设置。服务启动队列可派发数为 0。
- 仅页面明确 Send POST 对应的当前 actor/project、启动后新 turn 可派发 assistant.coach。历史 Run、其它模型 purpose 不派发。每笔用户实际请求沿既有账本 append-only 记录 request/result/provider body/receipt，累计 cap 280；unknown 停止该 Worker，不自动 retry/repair。
- 合成账号由 `private/account.json` 保存，用户答复单独提供；不在此报告写入 DSN/API key。
- 停止：`powershell -File D:\studyplan\var\assistant-user-acceptance-prep-20261005\stop-services.ps1`。脚本只终止记录且命令行仍一致的本批进程，不删除库或证据。
- 点击发送会实际消费产品模型请求；仅浏览、展开、恢复、保存已有可编辑候选不会新增 assistant 请求。旧路线候选保存仍禁用。

## 本人检查路径与下一安全动作

1. 我的会话：搜索、两类筛选、三态、打开历史会话、旧路线只读。
2. 当前路线阶段总结：开始总结、欢迎、亲自聊天、候选展开/收起、采用或改稿保存。
3. 当前路线实践：开始实践、亲自聊天、最终 Prompt 候选、采用或改稿保存。
4. 恢复：收起/重开助手、刷新、退出/登录、我的会话恢复。
5. 视觉：桌面、长 Prompt；窄屏可选。

此处 STOP，等待本人审查。没有 push/merge/deploy，没有操作原产品库、正式入口/Worker、RAG/WeKnora。回滚仅需停本批进程并撤销这项前端后继差异，历史和数据库证据保持。

开发路由偏好：有界前端修复 Sol6.1 medium，费用/派发门禁 Sol6.1 xhigh；实际解析 `NOT OBSERVABLE`，没有修改全局配置或派发子代理。
