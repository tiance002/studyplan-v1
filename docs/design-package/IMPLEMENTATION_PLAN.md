# V1 实施路线：M0–M4.5

2026-10-01 / S0。上位输入为 [补充规格](supplements/studyplan_requirements_design_supplement_2026-10-01.md) 与 [Gap Analysis](../reviews/2026-10-01-v1-gap-analysis.md)。不重新从零实现B0–B3，不迁旧E盘数据/API，不一次启动全部阶段。

## 1. 已有基础和映射

| 历史批次 | 复用内容 / 证据 | 新里程碑 |
|---|---|---|
| B0/B1 | 独立工程、分层、契约、DB角色、Run/恢复骨架；ADR0001–0005及B1报告 | M0已用；M1继续复用 |
| B2-C/B2-V | 节点/单元/实践关系、PlanRevision、单事务发布/幂等/历史；B2报告 | M1基础，非稳定逻辑ID/六态全部完成 |
| B3/模型设置 | LLMPort、个人模型/预算/ledger、Run和worker | M1/M2/M4基础 |
| B3-F1 | React正式入口/只读workspace/注册登录/布局 | 布局复用；账号产品范围由ADR0007取代 |
| B3-F2/Hardening/Acceptance09 | 真实分批、有限repair、待审批Draft；20请求成功已核对 | M1生成部分Verified；本次真实批准/发布NOT RUN |
| 原B4/B5/B6 | 资源/总结/实践/前端闭环的历史任务意图 | 重新按M2/M3/M4/M4.5剩余缺口安排 |

历史报告保留为当时事实，不能用文件名/测试数声称整个阶段完成。

## 2. 阶段与停止点

| 阶段 | 交付 / Gap主责任 | 必须验收 |
|---|---|---|
| M0/S0 | 五类Gap、9份契约、架构入口、ADR、AGENTS与路线 | 文档一致、来源/链接/哈希、无业务改码/DB写/provider |
| M1.1 | 本地个人入口/安全身份装配；D1/E1，复用LOCAL配置 | 原actor Project/模型/Run可达；伪造/错归属/缺绑定/非本地/错误Origin拒绝 |
| M1.2 | 稳定知识逻辑身份+不可变内容映射；B1/E4 | 局部变更两版未变节点逻辑ID一致；历史ID/FK/内容/成果保留；冲突映射fail closed |
| M1.3 | 最小确定性调整Proposal/用户确认/新版本、跳过/顺序；C5 | S2/S8，依赖正确，重复提交幂等，未批准不改计划 |
| M1.4 | 有界State候选引用、安全错误分类；B2/A3 | 新Run新版本；旧waiting_user恢复不生成、不重复发布；分类安全可定位 |
| M2 | LearningSession/原事件/Reflection/Feedback/节点六态；A1/B3/C1–C3 | S5/S7，一节点学习纵向切片，异步回答不串节点，旧版本上下文正确 |
| M3 | 资源偏好/检索Adapter/Context/许可/路径外Proposal；A2/A4/B4/C7 | S3/S4；来源/版本、缺证据明确、禁云0请求、无静默外发 |
| M4 | 同一主项目方案/导出/外部实现/成果/证据/核验/进度；C4 | S6，证据门、覆盖目标/版本、支持VERIFIED |
| M4.5 | 八场景+真实全链路，P0/P1清零、P2/P3确认 | V1可交付，冻结契约/模型/内容/验收证据，负责人接受后tag |

C6由M1用户审核现有Draft和正式读回、M4.5完整场景验收解决。State收缩不得阻塞已验证旧图用户决定，先为新Run做协议边界；M2优先完成纵向闭环，避免把M1.4扩大为全框架重构。

## 3. 第一个实现 Goal：M1.1 本地入口

**Goal:** 为原本机actor提供无注册登录的本地学习入口，保持原Project/模型/Run可达和server scope。

**Constraints:** ADR0007；复用 STUDYPLAN_LOCAL_ACTOR_ID 等既有配置；不得自动选首账号/创建替代actor，不改历史Run/数据库迁移，不禁用RLS/项目约束，不调用真实模型。

**Allowed changes:** `backend/app/core/config.py`、`composition.py`、`application/sessions.py`、`ports/sessions.py`、`api/v1/deps.py`/`session_routes.py`/schemas；`frontend/src/main.tsx`及auth入口/client/generated；匹配的单元/HTTP/PG/浏览器测试与必要文档。先读现有实现再定最小签名；保留现有受控CLI身份流程直到单独完成其衔接，不能静默破坏下一次preflight。

**Non-goals:** 删除auth表/口令记录、云端认证、RBAC、账号数据迁移、自动批准Acceptance09、改图/模型配置。

**Tests:** 缺/无效actor绑定拒绝；原归属读回；客户端actor/project伪造拒绝；非loopback/Host/Origin拒绝；本地页面无需注册；服务重启归属不变；旧waiting_user读/决定Fake证明provider请求0。定向Unit→API/PG→浏览器关键路径，真实验收单独授权。

**Evidence:** 命令/exit code/结果、配置名无值、OpenAPI与截图、原历史哈希和actor绑定证明（不打印秘密）。

**Rollback:** 撤销该分支代码/本地模式配置回到原认证入口；不得回滚已发布数据或删身份。代码实现前写小范围实现计划，按TDD执行。

## 4. 后续切片细化与验收

M1.2先冻结逻辑身份映射/FK及歧义策略，追加0010之后迁移，测试两版内容变化和历史读回；M2先复用SummaryAttempt/Review，增加plan/node/content/session来源，一节点端到端后再扩范围。各Goal均写 Goal/Constraints/Allowed changes/Non-goals/Tests/Evidence/Rollback。

现有Acceptance09可由用户先人工审核/批准并验证正式路线；该业务决定与新付费授权不同，本S0不代为执行、不再生成。后续付费测试每次新ID、免费preflight、新明确授权，历史unknown不replay。

## 5. 验证和范围控制

按 [验收契约](EVALUATION_ACCEPTANCE.md) 执行；日常不重复大型suite，只有相关输入改变才重验；Milestone冻结时组合实际存在的验证脚本/命令，不声称`make verify-mX`已存在。

P0/P1阶段内修；P2负责人确认延期；P3 backlog。新增复杂度必须直接帮助完整学习闭环。Reuse→Adapter→Extend→Build；个人RAG能力/License/版本接入前核对，不自动抓取/执行外部项目。

## 6. S0 状态

S0规格与Gap已收口；文档检查/最终审核/Git结果见 [S0验收记录](../acceptance/S0-spec-freeze-report.md)。M1.1之后的业务实现未启动，业务/大型测试、付费调用均NOT RUN。
