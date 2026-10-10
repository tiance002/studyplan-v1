# W5 HTTP 压缩响应解码与用量审计修复

任务：`STUDYPLAN_W5_RESPONSE_DECODING_FIX_V1`；日期：2026-10-10。

## 结果与范围

`W5_RESPONSE_DECODING_OFFLINE_PASS`

`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`

Start HEAD：`f07f6f6b1616eb5bd88806c5f41cba1b713bd375`，分支 `feat/n1-resource-discovery`。本报告与代码同一份本地 checkpoint 的 SHA 以 Git 提交记录为准，避免在被提交文件内自引用提交 SHA。开始时 tracked tree clean；既有未跟踪 `.workbuddy/`、`design-preview/` 保持不动。

仅修改以下文件：

- `scripts/planning_v2_acceptance_external.py`：owned W5 响应捕获、受限解码、共享字节与审计。
- `backend/tests/unit/test_w5_response_decoding.py`：真实 Provider + MockTransport 反例与私有证据 opt-in 重放。
- `backend/tests/integration/test_w5_response_decoding_pg.py`：新隔离 owned PG 的正常/已知解码失败回执。
- 本报告及 `docs/implementation/progress.md`。

未修改正常 Provider、Domain/Runtime、架构合同、Policy、Prompt、Schema、hash 算法、预算、迁移、正式配置或前端。未重新实施 F01–F08。

## 根因与历史现场

复用 [上一轮报告](STUDYPLAN_SCENARIO_A_REAL_ACCEPTANCE_AFTER_W5.md)。第191次收到 HTTP200，保留的 wire body 为1236 bytes、完整 Zstandard 数据；正常 HTTPX Provider 可以解码，解析得到 `deepseek-flash`、`finish_reason=stop`、input4620/output1312/total5932。W5 `_ModelWire.handle_request` 却对压缩 wire bytes 直接 JSON 解析，得到空 envelope，故审计拒绝 `usage_untrusted`。这不能据此认定能力规划 JSON 本身非法。

旧捕获未保存 Content-Encoding 头。因此此次重放明确使用人工声明的 Mock `Content-Encoding: zstd`，不是补造历史 HTTP 头或成功回执。原始第190/191次响应原样只读使用，不修改业务 JSON。

旧 Run `run_b2312d08890145e2ad27445711225a70`、第191次 failed receipt、usage=null、STOP 与历史全局账本不改写、不恢复。新测试的成功回执只属于独立合成身份和临时测试账本。

## 修复数据流

`原精确请求检查/预约 → HTTP transport → 有界 wire bytes → 按 Content-Encoding 解码一次 → 同一 decoded bytes → W5 严格 envelope 审计 + 正常 Provider JSON/Schema 解析 → 原生 PG 与全局回执`

`_decode_model_response` 复用当前安装的 HTTPX 所用 codec 后端 zlib/zstandard，不创建第二套 HTTP 客户端。wire 与解码内容均上限524288 bytes。HTTPX 的 `iter_bytes(chunk_size=...)` 只控制输出分块，不能独自限制 codec 在分块前的内存分配，故增加薄的有界解码适配。

- 无编码/identity、gzip、deflate（含 HTTPX 接受的 raw deflate）、Zstandard 完整单帧可用。
- gzip/deflate 使用 `decompress(..., limit+1)`，检查 EOF、未消费数据与尾随数据。
- Zstandard 已声明长度先检查；未知长度通过 `max_output_size=limit+1` 限制输出；window 上限8 MiB，拒绝 extra data。
- 独审发现 zstandard0.25.0 对声明长度为0的帧可能提前返回空内容，忽略截断或尾随数据；text-only JSON 边界直接拒绝此类帧，补完整空帧/截断/尾随/串联四个反例。
- 不根据 magic bytes 选择编码；未声明编码的压缩体仍被正常 Provider 拒绝。
- 解码后移除 Content-Encoding、原 Content-Length/Transfer-Encoding，并设置正确长度，再交给 Provider，避免重复解压。

这是受控 text-only 单编码/单帧边界，并非对 HTTPX 所有协议组合的通用兼容实现。多重编码、串联压缩帧、尾随数据拒绝；当前环境未安装 brotli/brotlicffi，br 拒绝。未下载或新增依赖。

捕获元数据通过同一请求记录的 canonical SHA 绑定：`request_sha256`、`http_status`、`response_complete`、编码枚举及编码头 SHA、wire `response_sha256/response_bytes`、`decoded_sha256/decoded_bytes`。新增字段为新回执的附加审计事实，不重新解释旧记录。异常编码头只持久化摘要与 `unsupported`，不回显任意头文本。

用量检查继续要求三个 Token 字段均为非负整数（拒绝 bool/string），total 等于 input+output、output 不超过冻结 cap；审计 model 与 Provider model 相等，finishReason 和 Provider 用量交叉核对。缺失或不可信 usage 保留 null 并拒绝，不默认为0。

## 错误与 Reader 边界

完整收到但本地拒绝的编码/解码/容量/凭据回显错误使用 `_ModelResponseRejected`：全局 known failed、unknown=false、usage=null，原生返回明确 LLMFailure、STOP，不伪装未派发。底层 transport unknown/部分响应读取中断保持 reconciliation_required，不再派发新身份。

非 Reader 的合法 wire 原文只在大小与敏感检查后保留于 ignored 证据。Reader 不写 `.response.body`，不持久化完整 envelope/正文/Provider payload；仅记录身份、摘要、用量和结果状态。压缩前后均检查凭据回显，日志和错误信息不携带响应文本。Reader 正常链路与敏感回显反例都通过真实 Provider + MockTransport 验证，PgV2Calls 原有最终投影保护保留。

## RED/GREEN 与定向验证

原始日志均保存在 ignored `var/codex-goals/w5-response-decoding-20261010/`，不提交真实响应或教材全文。

| 验证 | 结果 | 实际证据与限制 |
|---|---|---|
| 首轮新用例 RED | FAIL | `red.log`：22 failed / 5 passed，未修复解码链 |
| 第一轮 GREEN | FAIL | 25 passed / 2 failed；Reader 测试以旧输入装配新输出 schema，被原准入拒绝，已修正 fixture |
| 新27项 + 旧 W5 37项 | PASS | `unit-final.log`：64 passed / 172.56s；在随后新增空帧与边界用例之前 |
| 最终40项新边界矩阵 | PASS | `boundary-final.log` 39 passed / 1 failed；唯一错误是无编码压缩体的预期分类写成 usage_untrusted，实际正确为 provider_invalid_envelope。修正断言后 `identity-final.log` 3 passed / 37 deselected；其余39项不重复运行 |
| 最小 owned PG | PASS | `pg-final.log`：2 passed / 43.68s；成功 zstd 与已知损坏压缩体，使用新业务/checkpoint 两库 |
| 私有190/191原样离线重放 | PASS | 已包含最终矩阵；`OFFLINE_REPLAY_FIXTURE_PASS`，业务 Run 创建=false，真实请求=0 |
| Ruff 三个 Python 文件 | PASS | 首次仅 import 排序问题，修正后 all checks passed |
| git diff --check | PASS | 提交前检查 |
| 533个历史文件 SHA | PASS | `history-final.json`：0变化，含历史证据、账本与 .env |
| 真实模型/搜索/Reader/正文/价格余额 | NOT RUN | 本轮全部0，未进行外部预检 |
| 全量 Backend、374接缝、React/浏览器 | NOT RUN | 未重复，与当前修改无关 |

上述单位测试共77个不同用例（40新 + 37既有），不将复跑次数累计成更多测试。最终矩阵包括精确容量边界、编码损坏/截断/声明不符、解压膨胀、usage 反例、model/length、Reader 敏感生命周期、部分 transport unknown 与禁止重派。

PG 首次2 FAIL为新测试误把 receipt `identity` 哈希字符串当作字典；修正为现有 `manifest_hash` 字段比较后新 owned 库两项 PASS。首次失败库与日志保留，未修失败业务数据。离线重放最初 test path 错误引用不存在的 `ext.ROOT`，修正测试目录定位后通过；原 FAIL 日志保留。

正常 PG 路径证明 durable 预约与全局 request 在 Mock HTTP 前存在、原生与全局 input20/output16/stop一致、来源 manifest 一致，Goal review 停止点不续派。损坏路径证明两层均 failed/unknown=false/usage=null、Run failed、冷恢复拒绝；每案只1次 Mock 请求，无 Draft。测试 fixture 禁止非 loopback 网络；真实 PG 仅隔离新 owned 库。

重放使用冻结 Scenario A 与真实190 Profile，得到相同 Profile：`2c81d45be4bec2607cb6e419cac768561b2a6c44e6d509bd7eb1f2e8f3947a28`；原 CapabilityPlanValidator 接受正常解码的191候选，Plan：`fa5bea88e0701834691af682e677104eb1464ac55a1b2a3c9ea1deb01e8cc993`。这只证明接缝修复与历史输出可消费，不标记旧 Run 成功，也不是新真实语义验收。

## 独立审查与保护

独立审查代理读取实际源码/diff、原 Provider 解码路径、测试与证据，不使用实施者自报 PASS 替代审查。按当前关键边界路由请求 `gpt-6.1-sol/xhigh`；实际解析 model/effort 为 NOT OBSERVABLE，未修改全局配置。零长度 Zstandard 帧绕过检查由独审发现并关闭；Reader 内容泄露、已知/unknown 分类、bounded 解码与历史保护纳入最终复核。最终独审 PASS、未关闭阻塞0；记录位于 ignored `independent-review.json`，SHA-256 `10d353e4996fb07b37b6d5f886af61dedacf0db9c314e9c00780d5b40aceec7f`。Ruff 由主协调执行并留存 `ruff.log/ruff.exit`；独审未重复运行 Ruff，也未重复扫描历史原文，明确区分源码复核与主协调的机械验证证据。

全局模型仍191，搜索仍6；旧 unknown177/183、第184–191记录与失败 Run 证据保持。旧 owned 数据库不写入；本轮仅新测试库。公开 `/plans/generate` 503 保护复用已有证据，相关正式路由未改、未启动正式入口。没有 push/merge/deploy，没有恢复真实验收。

## 下一轮前置与剩余风险

W5 helper SHA 已变化，旧 prepared/grant 绑定不得复用或继续失败 Run。未来须 Owner 单独决定新的真实 acceptance 与请求/费用授权，重新冻结当前 helper/SourceFacts/身份和预算，按现有 W5 流程完成新价格余额 preflight及独立价格审查后才能派发；本轮不执行这些步骤。

此修复不证明真实免费教材、Reader 教学质量、Curriculum 或完整产品 E2E 通过。严格人民币现金数学硬上限仍未证明。压缩响应后端依赖当前安装版本；其他 Content-Encoding 或多帧响应会明确 fail-closed，不自动换协议或重试。旧191未保存编码头造成的历史审计缺口保留，不补造旧事实。

STOP。
