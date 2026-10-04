# v6.8 单一真实收费代表：PAID_REPRESENTATIVE_PATCH_PASS，STOP

用户现在新增能做什么：已有一个完整生成并合成确认的 Agent5 Plan，可据真实 provider、owned PG 和获准 Edge 刷新/重登录证据评审内容与体验。这里只通过本次单一代表门禁；全产品仍 **STAGING_BLOCKED / NOT_READY**，正式入口、原产品库和正式 Worker 未启用。

依据：[批准 Goal 原文](../implementation/STUDYPLAN_V6_8_PAID_PROJECTION_GOAL_2026-10-04.md)，附件逐字节归档。用户随后明确“允许改用 Edge”，替代本轮 Chrome 指定浏览器条件；Chrome 本轮 **NOT RUN**，不能称 Chrome PASS。旧 v6.5 Acceptance/Run 永不复用。

## Baseline 与范围

- 分支 `feat/n1-resource-discovery`，起始 HEAD `2ed6485e3cb1b52e199e9c8aeb04f99e3f3cc2b1`；受跟踪工作区干净，两受保护目录未操作。
- v6.7 代码提交 `d2d162fad6466f6f8a46c43af7d90cab25156752` 在祖先链，生产源码、UI、API、DTO、迁移、Seed、模型/cap/prompt_version/.env 本轮无修改。
- 唯一新 Acceptance：`v68-agent5-synthetic-67ca1224a56f`；唯一新 Run：`run_3170cfe33c3f4b71b9dd7746b228443f`。
- 新 owned 业务库 `studyplan_test_v68_business_f064eec7`、独立 checkpoint 库 `studyplan_test_v68_checkpoint_a598073d`。仅在这两个新库迁移现有 schema、导入公共审核 Agent5、创建合成账号；复用已有角色，无全局角色改变。保留两库及证据，原产品库读写0。
- 合成目标精确为“零基础系统学习 Agent 应用开发，先做一个最小应用。”，默认偏好，无私人资料/已有用户项目/面试 overlay/RL 训练或 RAG 专项强制深化。当前 provider 请求及返回 model 均 `deepseek-flash`。

## 收费前预检

17 项硬条件 **PASS** 后才发第一笔：分支/HEAD/clean、patch ancestry、新提交实际 marker、hash 绑定、禁止全文字段、六阶段结构大小、非legacy、实际公网DNS/endpoint guard/TLS、purpose caps、quota24/50、受控quota unresolved0、key SET、冻结publication digest、synthetic范围及13+2预算。

实际 submission 冻结 `outline_input_format=stage_skeleton_v1`，删除marker后hash校验失败，实际manifest与免费预检相等。生产adapter MockTransport捕获4112messages chars/5239HTTP bytes，低于6500chars/14000bytes fixture上限；第一笔实际出站 body 再核对同口径尺寸。没有完整resources、publication/review evidence、practice、extensions、guidance或未选目录全文。

实际DNS为119.188.175.46、123.125.246.121，均公网；未硬编码到产品配置。原 endpoint security guard PASS；与产品trust_env=False相同直接TLS1.3、证书链/hostname PASS。outline/practice4096、structure/repair8192，normal13+repair2=15；原累计24，最终硬上限39。Agent5 digest仍 `eeff800d60e332772045d32db8ff143a254b24d72d32462b35e7620842be0565`。免费预检第一次是隔离脚本默认编码的UnicodeDecodeError，尚未完成硬门禁判定、收费0；显式UTF-8后全部PASS，原错误记录保留。

## 第一门：真实 outline 改善

| 指标 | v6.5 | v6.8 |
| --- | ---: | ---: |
| provider input tokens | 209998 | 1351 |
| provider output tokens | 4097 | 603 |
| finish_reason | length | stop |
| adapter latency ms | 16222 | 3020 |

真实 input 减少208647 tokens，下降 **99.35666054%**。两次latency均取实际持久化记录，单次比较不承诺未来性能。没有用char/4或本机tokenizer代替provider usage；不声称历史wire逐字节相同。

v6.8 HTTP200、provider envelope PASS，content1292字符、total1954tokens、cached0/cache-hit0/cache-miss1351。adapter返回LLMResult；JSON/shape、六个冻结stage keys及顺序、无越权字段PASS。先保存request25/result25，再在首次structure派发前检查PG outline receipt、token匹配、finish_reason与unknown，并写入 `outline-gate.json`，通过后继续。outline无length/truncation；本轮全部15响应finish_reason均stop。

## Structure、practice 与 local repair

| Purpose | 请求数 | input tokens | output tokens | latency ms合计 |
| --- | ---: | ---: | ---: | ---: |
| outline | 1 | 1351 | 603 | 3020 |
| structure | 6 | 10114 | 4336 | 21875 |
| practice | 6 | 10956 | 6815 | 33156 |
| local repair | 2 | 6929 | 1737 | 6283 |
| 合计 | 15 | 29350 | 13491 | 64334 |

总provider tokens **42841**。normal13、repair2，未追加请求。每笔purpose/attempt/stage/input/output/total/cache/finish/状态/latency及repair linkage均保留在本机 `final-after-browser.json` 与39次累计受控账本中；provider没有返回美元费用，**NOT OBSERVABLE**。

stage A1首个structure是可解析JSON但缺nodes/units/relations；首次local repair又引入六个未声明子知识键。两个均为有完整provider/PG回执的known局部schema/域校验失败，修复绑定同一A1structure原attempt。第二次repair通过；原失败内容和校验错误保留。无人工重发、第二Run或unknown修复。repair额度随后耗尽，其余structure/practice正常完成。

6次structure和6次practice各阶段校验后，调用当前生产pure merge作确定性保护核对，任何保护差异都会阻止后续派发。12项阶段保护PASS：知识stable_key/title/objectives/scope/acceptance/parent/prerequisites与冻结权威相等；practice身份/数量/goal/scope默认/交付物声明/acceptance/required/optional及知识links遵守reviewed blueprint。模型知识标题/目标等实际差异被本地恢复；补充模型任务没有进入completion gate。

## 完整内容、持久化与确认

完整草案门禁 **PASS** 后才执行唯一synthetic approve：6stage、6required knowledge、18资源安排、35精确章节refs、13extensions及全部冻结guidance。资源role/source/version/order/知识归属/section_refs与stored draft JSON、最终发布PG表逐项相等，extension全部字段按现有可选order默认语义精确相等，非仅数量比较。

知识实体title/objectives及完整canonical rubric与本地blueprint相等；scope/acceptance/parent/prerequisites在现有rubric JSONB保留。最终PG读取5条canonical依赖/parent边、6条task-knowledge links、6个completion task gates，全部精确相等，额外task gates0、required extensions0。实践实体goal/in_scope/out_scope/acceptance及canonical rubric一致，无额外强制Starter或冲突acceptance。

Common Core semantic_context仍starter_candidate、binding optional、replacement_allowed、Recipe refs空；“持续成果载体与可组合专项”保留可替换默认候选与独立Micro Exercise，不强制迁入。Evaluation每阶段横切，未要求RL；hold来源排除。当前场景没有project-study/case-study安排，不编造该内容。其他用户项目优先/开放Recipe/RL optional/needs_research_or_review及显式optional canonical task fail-closed，复用源码未变的v6.7五场景/contract证据；本轮不为这些变体额外收费。

owned PG最终1Run、15attempt、1approved Draft、1PlanRevision、unresolved0。唯一合成approve使用该Draft hash/version/idempotency key；原始Run成功后不再执行Worker。新容器登录、Plan/workspace精确回读、退出/重登录再回读PASS。

## 浏览器与成功后零调用

用户明确同意Edge替代后，使用受控API8028/前端5188、仅本轮owned库，Worker OFF，API仅允许登录/退出和读取，所有生成/业务写均拒绝。浏览器 **PASS**：登录、六阶段路线、35章节链接、展开学习指导、extensions/可替换载体、canonical practice scope/acceptance/知识链接、刷新、退出、重新登录后同一路线和资料。

没有打开GitHub或其他外部资源链接，没有点击模型反馈或生成按钮；Project Study安排本场景不存在，**NOT RUN**。浏览器HTTP元数据包含一次登录401和一次注册403，其来源未作推断；注册在受控guard前拒绝，无额外账号/Run或模型派发。成功登录200两次、退出200一次，受控消费实际成功POST只有auth。截图/DOM及元数据保留，不以一次401替代最终成功结果，也不删除失败记录。

本轮隔离核对脚本曾误用API省略的resource order_index、未处理optional extension order默认值、沿用旧项目候选topic断言、把Run元数据放进fresh login JSON；只修本机审计方法，分别核对stored draft字段、现有projection默认与冻结semantic context、登录契约。另有本机read-only脚本缩进错误与消费guard断言过宽，修正后最终审计PASS，失败日志保留。未改业务源码掩盖，未重新创建Run或重复confirm。后台Start-Process命令曾被自动审批策略拒绝，改用工具管理的前台会话启动受控服务。前端启动一次相对路径错误保留。

模型生成后新增真实请求 **0**，累计request/result仍39对，PG仍15attempt；确认、PG和浏览器均未触发新模型。两受控监听进程经命令行/端口身份核对后关闭，8028/5188无监听；原服务与入口保持。

## 用量、安全、证据与STOP

累计quota **24/50→39/50**，失败/局部无效请求照常计量，本輪unknown0。起始48份quota文件哈希、全部旧Acceptance哈希、9份v6.5既有evidence与正式.env保持；旧其他Acceptance unknown保留，不重派。GitHub/Tavily新增0，搜索最新6/1000。原产品库写NO、真实用户资料外发NO、RAG触碰NO、正式Worker/入口NO、AI2/Cloud2代表NOT RUN、merge/pushNO。

本机证据：`var/v68/free-preflight.json`、`preflight-complete.json`、`frozen-submission.json`、`outline-first-response.json`、`outline-gate.json`、`stage-protection.json`、`run-report.json`、`content-protection.json`、`canonical-pg.json`、`exact-published-facts.json`、`paid-and-pg.json`、`browser-ui-evidence.json`、`browser-http.jsonl`、`edge-*.png/txt`、`final-after-browser.json`。秘密与DSN仅在ACL隔离private目录，ignored本机证据不提交。

状态分别记录：免费/实际freeze/payload/DNS/guard/TLS **PASS**；真实provider/本轮protected Draft/confirm/owned PG **PASS**；获准Edge refresh/relogin **PASS**；Chrome/frontend build/本轮宽unit **NOT RUN**，复用v6.7相关unit/contract PASS878与NOT RUN2，不重复宽套件。模型路由root请求gpt-6.1-sol/high，实际解析NOT OBSERVABLE，无子代理/全局设置改变。

费用不可回滚、不清零、不改历史回执。合成数据仅在owned两库保留，不进入原产品库；代码未变，仅本轮文档可普通revert。一个样本需要用满两次repair，不能据此宣称普遍成功率或全部产品门禁满足。

最终 **PAID_REPRESENTATIVE_PATCH_PASS，STOP**。用户已批准Edge替代，Chrome本轮NOT RUN；全产品 **STAGING_BLOCKED / NOT_READY**。唯一下一最小动作：用户验收本轮合成Plan的内容与学习体验。任何新收费/正式部署仍需新的对应授权。最终本地SHA交付时动态读取，无GitHub SHA声明。
