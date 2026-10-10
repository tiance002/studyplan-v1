# Scenario A 真实产品验收：Capability 用量审计门禁停止

任务：`STUDYPLAN_SCENARIO_A_REAL_ACCEPTANCE_AFTER_W5`。执行日期：2026-10-10。

本批真实 Goal 的程序和独立语义验收 **PASS**。唯一 Capability 请求返回 HTTP 200，随后 W5 外部审计边界以 `usage_untrusted` 停止。原 Run 已为 `failed / none`，没有形成可供下游消费的 CapabilityPlan。教材研究、Reader、Curriculum、Compiler、Draft 和 React 均 **NOT RUN**。本报告不宣称课程或完整产品通过。

## 基线与授权

- Start HEAD / 外部执行 HEAD：`1890e228c1a8d00661e3eec38a2a900163a6e42e`，分支 `feat/n1-resource-discovery`。
- 提交报告前执行源码 HEAD 不变；Final 文档 checkpoint SHA 以本次 Git 提交回执为准，避免将执行后文档提交误认为模型输入基线。
- 开始时 tracked tree clean；既有 untracked `.workbuddy/`、`design-preview/` 未操作。
- Owner 明确批准此新 acceptance 的 9 次产品模型（Goal 1 / Capability 1 / Reader 6 / Curriculum 1）、搜索 6、正文操作 6 / HTTP 12、官方元数据 2；接受本批无严格人民币数学现金上限的残余风险。
- 不充值、不更换模型、不重试、不 repair、不扩额、不创建第二 root。未使用旧批次剩余额度。
- 本轮仅新增本报告和 progress；生产源码、Prompt、Schema、Policy、正式配置、架构合同及 migration 未修改。

执行使用 tracked `scripts/planning_v2_scenario_a.py`，顺序为 `prepare → external-request → preflight → price-review-request → approve-price → submit → tick → review → decide → tick`。没有复制旧 ignored 真实执行脚本。准备时的 import/PYTHONPATH 与本轮新证据目录 ACL 问题均发生在任何外部请求之前；修正进程环境和本轮目录继承后，才创建授权和预检收据，不属于 Provider 重试。

## 冻结身份与一次性本地准备

| 身份 | 实际值 |
|---|---|
| Acceptance | `scenario-a-6e3381407e834860b7b462b5cbfe0ccd` |
| 唯一 Run / 预算 root | `run_b2312d08890145e2ad27445711225a70` |
| owned Project | `lpr_276b5b5702af4123a15cf443a625bd36` |
| Packet hash | `b49f1d467f349313acd5d9a50f6f74dd95c5bdff1afb7187b1938190c42695cb` |
| Manifest hash | `d31c687bccec1929ade0036b8b918fbd6bfa0bb258d1c8a9bc8364dadb88affc` |
| SourceFacts hash | `c09a2c52d8c53e091accef4f5c01bf0210f6b98cbc9354aa16e210855afd65e7` |
| Provider 配置身份 | `acceptance-deployment:d92631a8f5d0b65bb5aed3c95ae48488e6927bd26d41c8092186d89793852da5` |
| 产品语义 / 审查门禁 | `planning-v2-product-v2` / `scenario-a-review-v1` |

实际 Provider 为 `OpenAICompatibleLLM → DeepSeek deepseek-flash`，thinking disabled。owned 进程显式装配基础输出 4096，Reader 1024，正式 `.env` 未修改。完整消息序列化后、全局 request intent 和 HTTP 前检查 32 KiB；这不是 Token 或现金硬保证。

完整 SourceFacts 先冻结到本批 ignored 目录，再建立 manifest。进程 A PID 40892 与冷进程 B PID 36808 解码出的**完整内容**相同，重新计算的 hash 与 manifest 相同，PASS。未仅复制旧 hash 或重新生成 created_at。受控同机 Worker 读取同一快照；不声称已证明多机器部署。

新隔离业务库 `studyplan_test_afterw5_4d1dcec6`、checkpoint 库 `studyplan_test_afterw5_checkpoint_3740364b` 经最终 `_owned_pair` 保护后的合法连接正向检查 PASS，实际角色为 `studyplan_app`。标准迁移只在新测试库运行，没有新增 migration 文件或正式库写入。新 actor 为合成 owned 测试账号；没有执行课程确认操作。

冻结 ResearchBudget 为：总 durable 请求 27、输出预约 18,432、正文 393,216 bytes、候选 8、Reader 6、搜索 6、内部 cost_micros 186,000。内部预算单位不是人民币。purpose 次数、全局 append-only 账本、父预约、fence、CAS、checkpoint 和独立阶段审查实际装配。

原始证据根：`var/planning-v2-after-w5-20261010/`。准备、授权、完整来源、原始响应、价目和审查证据保留于其下；凭据/session 不进入报告，教材正文没有持久化。关键文件包括 `local-preflight.json`、`acceptance/prepared.json`、`acceptance/source-facts.json`、`acceptance/submission.json`、`owned-final-state.json`、`final-evidence.json`。

## 冻结 Scenario A

目标原文：“我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。”

scope：结构化输出、受限工具调用、系统性 Agent 应用学习。desired_depth：applied；starting_point：“已经会 Python。”；outcome_purpose：learn。

三条约束原文：

1. 保留现有 CLI 和 JSON 任务文件作为持续实践载体
2. 不重新创建演示项目
3. 工具仅操作用户明确允许的本地任务范围

项目背景原文：“我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。”

与本批准备前冻结输入相同；未因失败改写输入，也未把第184 / 187次历史结果移植为新 Run 回执。

## 官方预检与独立价格审查

两次 GET 均成功，未重取或追加账户请求：

1. `https://api-docs.deepseek.com/zh-cn/quick_start/pricing/`
2. `https://api.deepseek.com/user/balance`

保存的官方价目中，deepseek-flash 高峰缓存未命中输入为 **CNY 2 / 百万 tokens**，输出为 **CNY 8 / 百万 tokens**。本批预检余额 is_available=true，总余额 CNY 3.91，赠送 0.00、充值 3.91。这里只记录当时读取结果，不作为未来账户余额。

独立价格审查 PASS，绑定实际两笔元数据 request/result、artifact/response hash、prepared、manifest、model_ref、HEAD 与 Owner 授权；审查文件 SHA-256 `2e267b11fa5207aebd0c8d475d1b97c3dc67c0a7ed1730b4cc78d84303ad4cc2`。`approve-price` 已登记 `estimate_only` 结果后才 submit / 派发。

## 实际请求与阶段结果

| 阶段 | 程序结果 | 独立真实语义 | 实际执行 |
|---|---|---|---|
| 准备 / 来源 / owned DSN | PASS | 不适用 | 新来源全文冷进程一致、合法两库连接 |
| 官方预检 / 价格审查 | PASS | 不适用 | 两次 GET、独立价目审查 |
| Goal Analysis | PASS | PASS | global 190，原生 Goal checkpoint，独立 CAS approve |
| Capability Planning | FAIL | NOT RUN（正常阶段验收） | global 191，`usage_untrusted`，无合法运行态 Plan / hash |
| Coverage / Gap | NOT RUN | NOT RUN | 未越过 Capability 失败 |
| 搜索 / 正文 / Reader | NOT RUN | NOT RUN | 实际新增均 0 |
| Curriculum / Compiler | NOT RUN | NOT RUN | 无课程、无 complete 判断 |
| Draft / HTTP / React / 确认 / Revision | NOT RUN | NOT RUN | 未进入产品读回；owned DB 确认不存在草案/版本 |

| 全局编号 | Purpose | HTTP / finish | messages bytes | Provider input / output | 延迟 | 正常账本费用估算 |
|---|---|---|---:|---:|---:|---|
| 190 | Goal Analysis | 200 / stop | 5,692 | 1,239 / 324 | 3,805 ms | CNY 0.005070 |
| 191 | Capability Planning | 200 / Provider stop | 18,847 | Provider 4,620 / 1,312；审计层 usage=null | 6,367 ms | null；不得以 Provider 数字覆盖失败账本 |

两笔消息均低于 32,768 bytes，max_tokens=4096、thinking disabled，实际响应模型 `deepseek-flash`。第190次 total_tokens=1,563。第191次原始压缩响应及 Provider 解析结果均保留；诊断不能修改其原始失败用量记录。

第190次 attempt：`run_b2312d08890145e2ad27445711225a70:v2:goal-analysis:18867d4fad6840fce6a37cb5`。

第191次 attempt：`run_b2312d08890145e2ad27445711225a70:v2:capability-planning:054266d1430057068b941ed3`。

实际产品模型 2/9，Goal 1/1、Capability 1/1、Reader 0/6、Curriculum 0/1；搜索 0/6，正文 0/6 / HTTP 0/12，官方元数据 2/2。全局模型 189→191 / 280，搜索保持 6 / 1000；本批 unknown=0。剩余授权不是继续失败 Run 或另建 Run 的授权。

PG 中两笔派发前预约各为 output_tokens 4096 / total_requests 1 / cost_micros 20,000；总冻结预约为输出 8,192、请求 2、内部 cost 40,000。原请求身份及失败预约均保留；未修改账本或补造现金结算。现金硬门禁仍未证明；正常第190次费用为高峰未命中估算，不是实际扣款。

## Goal 的实际验收

Profile hash：`2c81d45be4bec2607cb6e419cac768561b2a6c44e6d509bd7eb1f2e8f3947a28`。status=ready，四条必要需求：系统学习结构化输出、系统学习受限工具调用、将能力加入原 CLI、基于已有项目继续实践。三条 hard_constraints、Python learner claim、项目背景均完整保留；未生成 Python 复习、新项目或无依据技术路线。

独立代理以原始第190次响应和冻结 Goal 运行原生 GoalRequirementProfileValidator，结果与实际 checkpoint 逐字段相同；profile / state / review seal、来源及稳定 ID/hash 和 Run/version 绑定均 PASS。独立审查文件 SHA-256 `0ccdf225907fe90529b3de834e3745a42334639d646aeeee43fe50a8734b9d64`，依据文件 SHA-256 `763df86b036434d668efb88ab87b5a0975b72c2f158739a978e57bdb809b34eb`。

`decide` 使用可信独立文件及其 SHA，通过原生 expected_version=3 的 CAS 在同一 Run/root 批准 Goal；下一次 Worker 才派发 Capability。并非模型自评或主协调自签 PASS。开发审查请求沿用 Sol6.1 xhigh；实际解析模型 / 档位 NOT OBSERVABLE，未修改全局设置。

## Capability 停止与原始证据

`acceptance/STOP.json` 在 Capability 之后记录：phase=`planning.capability_planning`、error_class=`usage_untrusted`、unknown=false、retry=false。global result-191 为 failed / usage=null / peak_cash_estimate=null。后续 `review` CLI 因 `batch_stopped` 拒绝；没有创建 Capability 审查模板或通过的冻结 Plan。

W5 保存的第191次原始 HTTP response.body 为 1,236 bytes，开头为 Zstandard magic `28b52ffd`；Provider 却正常解析出 Capability JSON 和整数 usage。受影响接缝为 `scripts/planning_v2_acceptance_external.py::_ModelWire.handle_request` 在 transport 层读取原 stream bytes，并直接尝试 JSON decode；捕获失败后将 envelope 置空。`_ModelBatch.generate_structured` 随后从该 envelope 读取 usage，触发 `usage_untrusted`。正常 httpx Client 的响应内容解码与该审计读取层不同，已确认存在压缩响应解码不一致。

独立代理对原始字节内存解压，验证为完整帧（eof=true / unused_data 空）；解压后的 4,043 bytes JSON 的 SHA-256 为 `354113b27048b77137ed1c52b5574b3bbde58a096267b0cdf643e0cba059a4de`。model=deepseek-flash、finish=stop、usage=4,620 /1,312 /5,932，与 Provider payload 逐字段相同。原始 Content-Encoding header 未单独保存；使用 zstd header 的本地 HTTPX 解码复现相同结果，但不冒称独立观察到了原 header。

纯本地原 CapabilityPlanValidator 重放及候选语义诊断 **PASS**：Python accepted_known；llm.api 为必要前置；structured.output、tool.calling 为 required 学习和项目应用；MCP 为系统性 Agent 的 required 学习、optional 项目使用；四条需求有真实引用；未加入 json.cli 或新演示项目。三条约束的 not_applicable 是能力排除分类，不代表已满足项目约束或授予权限。

该诊断不是正常运行态的 Item 2 验收批准。原账本、Run、Receipt 仍是 FAIL，不冻结该离线 Plan、不建立其审查 checkpoint、不执行 Coverage / Research。以恢复后的真实 usage 和独审高峰价得出的**离线诊断费用估算**为 CNY 0.019736，连同190的估算为 CNY 0.024806；不回填失败账本，不作为实际扣款或硬上限。

## 数据库、历史及边界

新 owned PG 只读 fresh readback：Run `failed`、next_action=`none`、version=6、error_class=`v2_validation_failed`、result_ref=null；唯一 Job `failed`、attempts=2。两次 Worker claim 分别执行 Goal 和 Capability，并非同请求重试。

实际 project 范围行计数：plan_drafts=0、plan_revisions=0、plan_publications=0。这里是本轮新 owned 业务库实际读取结果；没有冒称正式库行数。未进行合成课程确认，更未代表 Owner 批准课程。

459 份既有文件 hash 全部不变，包括 `.env`、旧授权/请求/响应、unknown177 /183 和原失败来源 Run 证据。原失败 Run 和历史数据库未改；只在新的 owned 两库创建本批身份/运行。未知保护未消耗新身份补发；全局 append-only 账本仅追加190 /191。

公开 `/plans/generate` 503 保护与既有 85 unit /6 owned PG、SourceFacts、CAS/fence/unknown 测试直接复用；本轮没有改源代码，不重复283/374项或完整 Backend/React 矩阵，也未以静态保护替代一次真实公开接口验收。公开 generate 运行时抽查 **NOT RUN**，入口没有开放。

## 独立诊断收口与下一步

独立 STOP 证据：`acceptance/independent-capability-stop-evidence.json`，SHA-256 `e1fb9c7c3ba977d56cc2f818a3a6327fe4a206e98333c28d71f4f194f45c144c`。实际程序 **FAIL**、保护行为 **PASS**；内存解压、原 Validator 与候选语义仅作为离线诊断 **PASS**。审查代理外部请求 / 数据库修改 / 源码修改 / 原始响应及账本修改均 0，只保存独立证据。

新增验证仅为本轮 owned 合法连接、来源冷进程全文一致、两笔真实调用、Goal checkpoint/CAS、failed Run fresh PG readback 和上述保存字节的离线复现；没有重跑旧宽范围测试。文档 diff 检查 PASS；Ruff、全套 Backend/PG/UI 回归 **NOT RUN**（无源码改动且复用既有有效证据）。

下一处最小工作是修正 W5 model transport 对已支持 HTTP Content-Encoding 的解码审计，让审计与 Provider 采用一致的解码路径，保留原 wire hash、解码后 hash、encoding 元数据，并限制解码后大小。需要压缩完整响应、usage 缺失、解码失败及 Reader 不持久化正文的有界 Mock 反例，再独立审查。本轮依遇到 usage 不可信立即 STOP 的明确要求，不继续源码修复或真实派发。任何后续真实验收须取得新的明确授权，不沿用本批未用额度，也不恢复失败191身份。

最终状态：`SCENARIO_A_CAPABILITY_USAGE_GATE_FAIL`；`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`；`SCENARIO_A_OWNED_PRODUCT_E2E_NOT_RUN`；**STOP**。
