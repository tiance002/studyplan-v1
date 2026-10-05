# Learning Assistant V1.1 — 当前验收证据

## 当前结果

用户现在新增能做什么：阶段总结或具体任务的开始按钮默认恢复同一冻结位置的最近会话；在简洁学习助手中自然发送初稿、问题和改稿；本地固定欢迎不调用模型；收到候选总结/Prompt后明确采用保存或修改后保存。主区仍消费原正式服务保存的结果，聊天不修改完成事实。

当前实际基线：`feat/n1-resource-discovery`，`91750cbb345c7f428dd17809affcf4b50da2865b`。本批已 STOP：非收费与免费预检 PASS，真实教学代表 FAIL，不能标 `LEARNING_ASSISTANT_CORE_PASS`。实际提交 SHA 见最终答复和 `var/learning-assistant-v11-20261005/git-final.json`。源码迁移与旧 owned 库均为 `0025`；本批没有迁移。

## 合同及持久化

- 仅助手协议投影 `reply/status/proposal`。额外字段保留在原 provider receipt，API不消费其ID、role或任意metadata。旧reply-only显式兼容为continue/null；显式现代status/proposal残缺或冲突仍拒绝。
- 严格JSON解析、unknown、truncation、claim/fence、预算和鉴权门禁保持，没有助手repair或HTTP重试。原第162笔failed Run、body和receipt不改、不重派。
- 自然消息通过既有持久化的内部work_draft标记保存原文；冻结输入增加`natural-chat-v11`及全会话completed_rounds。模型按自然语言理解，不把内部标记当成用户选择。没有问题ID或逐问题状态机。
- 候选稿从服务端assistant消息、turn触发/原稿关联、成功Run的result_ref、精确`:assistant_reply:1`成功回执及schema/protocol重建；回复原文不一致则不展示候选且拒绝保存。
- 既有`assistant_formal_saves.draft_message_id`外键本来允许同会话任意消息角色。新保存请求明确使用`proposal_message_id`，服务端只接受本会话成功ready消息，并复用此FK存储候选来源。API回读新增proposal_message_id；旧用户原稿保存兼容，不改`0025`或历史行。
- 采用或用户修改均由明确HTTP保存操作调用原Summary/Prompt服务，CAS、幂等、正式关联恢复保持。保存0模型调用，不写完成、VERIFIED、Practice通过或Plan。
- 默认恢复按actor/project/plan/revision/stage/mode/task精确匹配，按最新消息时间选取；`force_new=true`仅用户菜单新建。未知请求仍阻止同位置新派发。

## 已完成的非收费证据

证据根：`D:\studyplan\var\learning-assistant-v11-20261005`。

| 层 | 状态 | 证据与实际边界 |
|---|---|---|
| Unit/contract | PASS | 183；助手投影/旧真实fixture/注入数据边界/JSON与截断/原review/规划repair及budget合同；`unit-contract-final.xml` |
| PG/API | PASS | 53唯一有效：46组合PASS、唯一fixture错误修复后定向1PASS、相邻Summary/Prompt6PASS；原FAIL保留，`pg-final.json`给出来源，不假称同次全跑 |
| Frontend/build | PASS | 61唯一有效：57既有+1新20,000/20,001候选边界+3焦点恢复；两既有静态渲染项定向复验PASS；最新build PASS |
| 真实owned HTTP + Fake provider | PASS | 总结4轮、实践3轮；两mode候选采用+改稿正式保存各2次；幂等与精确默认恢复，7次MockTransport、产品请求0；fake-api.json |
| Native owned backup/restore | PASS | 新owned业务库read-only snapshot/custom backup→新owned恢复；14消息/7turn/4正式关联及原Summary/Prompt回读，全部行hash保持；head0025；native-restore.json |
| Edge | PASS | 实际新owned Plan经普通API消费：总结4轮/实践3轮、两mode采用+改稿、CAS409不覆盖、close/reopen缓冲、刷新/退出/重登录/我的会话、430px桌面/760px全屏焦点循环、旧Plan只读、known失败原文与synthetic unknown禁重发；edge-checks.json。原异步打开Escape焦点FAIL保留并最小修复/实际复验PASS。刷新确认正式记录与聊天恢复；原生beforeunload弹窗工具无法触发，NOT RUN，不将其声称实测PASS。 |
| 免费binding/DNS/TLS | PASS | 完整非收费源文件hash绑定、公开DNS、原endpoint guard、TLS；provider请求0；free-preflight.json |
| 真实provider代表 | FAIL | 唯一新Acceptance两次真实summary；provider/JSON/回执及应用Run均PASS，但第二轮重复已答对问题并提前讲解，教学FAIL；立即STOP，余5回复/真实候选保存/Practice均NOT RUN |

PG/API最终反例组合由定向证据包登记，保留旧fixture错误，不以测试总数代替权威反例。受影响保存服务与Worker的既有安全验证同时保留。

## 费用与历史

本批只使用既有280累计授权，不新增授权事实。非收费及free PASS后唯一新Acceptance `assistant-v11-synthetic-c133125757c9`，新owned业务/checkpoint两库和合成账号/Plan/两会话。请求163–164均append-only，累计162→164/280，余116；repair0、unknown0，金额NOT OBSERVABLE。全局账、PG receipt、原HTTP body实报usage精确一致，final-audit.json及唯一completion追加已保存。

| 全局请求 | 模式/轮次 | input | output | finish_reason | provider/应用 | 教学 |
|---|---|---:|---:|---|---|---|
| 163 | Summary 初稿 | 1016 | 401 | stop | PASS | PASS：4项批量诊断与集中问题，continue/null |
| 164 | Summary 部分回答 | 1507 | 617 | stop | PASS | FAIL：确认输入是数据已理解后，末尾仍要求再答“用户输入和工具执行的区别是什么”；第二轮提前教学 |

合计2523 input +1018 output =3541 tokens；没有length/truncation。正确completed_rounds=1与“只问尚未解决的重要问题，不重复已解决问题”的system原文确实进入第164笔请求。不能把Fake教学脚本PASS当成真实模型遵守。两应用Run仍succeeded，不倒改业务/provider成功记录；教学验收单独FAIL。原162失败证据不改。当前新paid库4消息/2turn/0正式保存，Summary/Prompt正式产物0，practice pending/学习进度保持，正式污染门禁PASS。其余真实链NOT RUN，不重发、不第二Acceptance。

baseline.json冻结391份历史/配置文件hash，包含上一批response/receipt及旧费用记录。`.workbuddy/`、`design-preview/`未操作。原库、正式入口/Worker、RAG、部署、push/merge、旧failed/unknown恢复均NOT RUN。

## 下一动作和回滚

下一安全动作需要下一份有界Goal：保留163/164原request/body/receipt，离线定位模型为何未遵守第二轮剩余问题语义，以真实fixture与正反边界一起验证。当前Goal STOP，余额不自动派发，不继续改合同或增加收费。本人最终体验/原生离开提示仍需用户验收，真实Summary后续与Practice链尚未通过。

本批无DB schema变化；可停止本批8043/5200 owned进程，保留历史库及证据，通过新增Git修订回退助手代码，禁止整树restore或覆盖已有成果。整体仍`STAGING_BLOCKED / NOT_READY`；本人内容/体验接受和正式操作仍未授权完成。
