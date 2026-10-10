# R01–R05 真实课程验收前集中修复

任务日期：2026-10-10。本轮只修复附件审查中已经定位的章节选择、章节审核范围、研究结果聚合及 W5 响应分类问题。真实教材和课程验收未运行。

## 基线与证据

- Start HEAD：`7a6f9d0c9db80adc75412d557b5b3be6aef0a5cf`，分支 `feat/n1-resource-discovery`。
- 实现 checkpoint：`7622b020599c6b7e220f57cd7b04e20067ca8f99`（16 份源码/脚本/测试文件）。本报告与 progress 另作文档提交；最终本地状态以 `checkpoint-r01-r05-concentrated-fix-20261010` annotated tag 为准。
- 起始 tracked tree clean；原有未跟踪 `.workbuddy/` 和 `design-preview/` 保留未操作。
- 审查包 `STUDYPLAN_AUDIT_SCOPE_7a6f9d0.zip` SHA-256：`06ab045c7d93a3070a043bfe44b2c9a913a0865b5b6d474da058667c3728525f`。安全解包至 ignored `var/r01-r05-fix/audit/`，未执行其中的探针脚本。附件是反例证据；实施范围和权限以本次 Owner Goal 为准。
- 原始 RED、修复过程、最终测试及 owned PG 证据保留在 `var/r01-r05-fix/`。不将教材正文、响应秘密或账户信息写入本报告。

## 修改与原反例

| 问题 | 原反例 | 修复职责与边界 |
|---|---|---|
| R01 | “结构化输出”“工具调用”中文短章节标题无法匹配 Policy 的中文长 outcome | `GitHubTeachingBody._selection_terms` 将精确 Policy outcome 文本绑定到有限中文发现别名；`_select_chapter` 仍只排名真实 README 允许路径。行政文件、外链、路径穿越和未消歧的相同分数候选不获得读取资格。标题命中不改变 reviewed/coverage。 |
| R02 | 单章不支持被当作整个仓库已审；七个 outcomes 永远只问前六个 | 新研究规则区分章级审读范围、支持证据、已尝试不支持范围、选中但不可读章节和仓库范围耗尽。新 scope 从剩余目标推进；六项限制仍是单次 Reader 限制。合法的 sibling 或新 outcome 范围使用新的有界操作身份，仍消耗同一预算。 |
| R03 | 后续联合审读支持早期能力，但早期 ResearchEntry 保持 unresolved | 在新结果冻结前，按来源/版本、冻结 discovery、深度和精确 outcome/章节引用重新归并会话证据，重算 covered/missing/status。原 Gap/Capability 不变；失败与有限比较不足保留为可解释事实，URL 相同不能升级覆盖。 |
| R04 | 合法 Content-Length 主动拒绝被 W5 partial-close 判 unknown；实际超额分类/计量不一致 | 经过 MIME/encoding/数值格式校验后的 header-only 容量拒绝有专用终止事实，计为 known unread/consumed；非法响应与实际 streamed 超额计为 known failed/STOP。真实连接中断保留 unknown。HTTPX 会复制 extensions，audit 明确绑定实际 adapter 可见的响应映射。正文最终超额 chunk 先计量、再拒绝，不进入解析缓冲。 |
| R05 | 完整 JSON 中 finish_reason 为 dict/list 导致未捕获 TypeError | `_ModelBatch.generate_structured` 在枚举判断前检查字段类型，完整但非法字段返回 `finish_reason_invalid`，记 known failed；usage 不被置零。Reader 落盘投影的 finish/model 只保留核验过的标量，不持久化任意对象或正文。 |

## 版本、身份与旧回执

修改前先记录了 `var/r01-r05-fix/research-identity-delta.md`，随后仅对明确冻结 `research_rules_version=research_chapter_v3` 的新 Run 启用新行为。W5 新 prepare 会冻结该 marker；旧 prepare/manifest 的加载和恢复不补 marker。

- legacy 和 `research_comparison_v2` 保持原 input/result/snapshot 编码；旧 snapshot 不增加新的章节字段。旧 completed 结果不重新聚合或改变 hash。
- v3 的会话保存内容无正文的 `chapter_reviews` 和 `unread_chapters`。审核记录绑定 resource/url/version、chunk hash/location 和尝试 outcome 范围。不可读章节只记录允许目录中的路径和范围，不编造正文版本或覆盖。
- v3 正文协议为 `V2TransientBodyV2`；新操作身份绑定范围和排除章节集合，旧 `V2TransientBodyV1` 身份保持不变。Reader wire 仍为 `ResearchReaderV2`，保留原六 outcome/1024 输出上限和原审核合同。
- 成功 Reader 的 exact identity 从真实 durable Receipt 恢复，不再读取正文或再次派发。body-only success、unknown 仍拒绝盲目重派；不同章节/范围的新操作继续受原 root 预算、fence 和父预约保护。
- `TransientBody.attempted_path` 是内容无正文的瞬态事实，只有 v3 回执保留该字段；它不授予覆盖，也不改变旧 V1 编码。
- Policy、CapabilityPlan、原 Gap、教材质量标准、hash 算法、预算单位和 Planning V2 上位架构均未修改。没有 migration。

## 验证

程序测试均使用合成公开教材、Mock HTTP/Provider，网络保护禁止真实 DNS/外部 socket。owned PG 使用全新隔离测试数据库；不操作正式库。

| 检查 | 最终结果 | 实际证据 |
|---|---|---|
| 章节、聚合、V2/legacy、durable seams、manifest 和 preparation 定向单元 | PASS（124） | `research-unit-final2.log/.exit`，exit 0。仅七个受影响模块，没有全 Backend 回归。 |
| 中文选章、容量、W5 完整链路分类组合 | PASS（31） | `focused-corrected.log`。其中正文 20 项，外部 11 项；后续外部新增反例单独复测。 |
| 最终 W5 非法 finish/容量/损坏/真实中断 | PASS（13） | `external-final2.log/.xml`，exit 0，0 failure/error/skip。 |
| 新 owned PG 章节范围与 cold Receipt 回放 | PASS（2） | `research-pg-final.log/.exit`；`research-pg/negative.json`、`capacity.json`。实际 claim/预约/收据读回；恢复 HTTP/Reader 增量 0。 |
| 新 owned PG 非法 finish 的 native/global 结算 | PASS（1） | `pg-tests.log`、`owned-pg/`；known failed/unknown=false，1 请求、0 redispatch、无 Draft。 |
| 公共生成仍 fail-closed，存储访问 0 | PASS（1） | `failclosed.log/.xml`，原 API 测试 HTTP503。 |
| 全部修改 Python 的统一 Ruff、git diff --check | PASS | 本地命令 exit 0。 |
| 既有回执/证据/配置文件额外完整性抽查 | PASS | 任务中段建立 hash 清单，结束时对其中 2565 个既有文件重算，0 变化；`history-integrity-before/after.json`。不将其冒称起始时点全部历史备份。 |

这些组有重复，不相加为“唯一测试总数”。所有模型/Reader 结果均是明确标注的 synthetic fixture，不宣称新真实模型或真实教材通过。`.venv` launcher 提示过旧 Python-home，但上述 pytest/Ruff 实际完成并返回 exit 0。

RED 和中间失败未删除：R01/R04 最小反例 4 FAIL/8 PASS；章节排除新增反例 8 FAIL；研究核心反例 3 FAIL/2 PASS；selected-unread 反例 1 FAIL/7 PASS；W5 非法 dict/list finish 的 TypeError 与 header unread 错判均原样捕获。后续扩展暴露 HTTPX extensions 复制、真实流量计数前过早抛异常和 selected-unread 被整仓库耗尽三个实际问题，均已修复并复测。

另有 fixture/环境失败：默认 pytest temp 权限、旧 prepare marker 断言、`context.payload` 拼写、PG 查询不存在的 `receipt` 列，以及期望未经当前 scope 审核的能力借用第二资源。均与生产缺陷区分记录；更正为合法 fixture 后通过原校验。最终 124 项批次和两项 PG 回放全部 PASS，没有修改真实旧证据追绿。

## 独立审查

独立 `fix_review` 代理对实际 diff、源码、版本边界及共享测试证据复核。请求档位 `gpt-6.1-sol/xhigh`，实际解析 NOT OBSERVABLE。审查记录 `var/r01-r05-fix/independent-review.md` 绑定所读源码/测试 SHA。

审查关闭的重点问题：

1. 实际超额被 W5 当作 unknown：明确区分流量拒绝与连接中断。
2. audit 在 native 字节计量前抛异常：由正文适配器先计数再拒绝；262145-byte 反例核对 native/wire 字节一致。durable 最坏预约原本就不释放，本轮未改其算法。
3. selected-but-unread 曾排除整仓库：用路径及 outcome 范围记录 unread，合法 sibling 可以继续，不给未读正文造版本或覆盖。

最终有界独审 PASS，无未关闭的 blocking finding。独审首次使用不完整解释器的测试尝试为 NOT RUN（缺 pytest/psycopg），未算成产品 FAIL 或 PASS；其后共享实际测试证据与源码复核分别记录。

## 修改文件与消费者

核心修改：

- `backend/app/infrastructure/resources/teaching_body.py`：中文发现别名、受控章节排除、选中路径事实及主动响应拒绝标记。
- `backend/app/application/teaching_resource_research.py`：新范围推进、精确章级缓存、最终聚合。
- `backend/app/domain/planning/research_reader.py`、`resource_research.py`：瞬态路径事实、新版本章级内容无正文的会话记录及旧编码隔离。
- `backend/app/domain/planning/v2_runtime.py`：新 manifest marker 校验。
- `backend/app/infrastructure/checkpointer/v2_planning_runtime.py`、`providers/v2_attempts.py`：新正文身份、章级 Reader Receipt 和恢复绑定；旧协议不切换。
- `backend/app/infrastructure/providers/runtime_factory.py`、`scripts/planning_v2_scenario_a.py`：显式 owned 新版本装配。
- `scripts/planning_v2_acceptance_external.py`：W5 finish 类型、响应终止分类、计量和 Reader 元数据保护。

测试修改：新增 `test_teaching_body_r01_r04.py`、`test_r01_r05_external.py`、`test_research_chapter_v3.py`、`test_r01_r05_external_pg.py`、`test_research_chapter_pg.py`；既有 `test_scenario_a_preparation.py` 仅更新新 prepare marker 断言。报告和 progress 随本地 checkpoint 提交，不提交 ignored 原始证据。

## 未运行与剩余限制

- 真实 DeepSeek、Tavily、GitHub网络、Reader、正文及官方价格/余额请求：全部 0。
- 真实教材语义、免费访问资格、Reader 真实质量、Curriculum complete 和产品 React 闭环：NOT RUN。合成教材的算法 PASS 不证明真实教材支持 outcomes。
- 通用 Web/Notebook/HTML/PDF 正文支持未新增；中文别名仅覆盖本次已定位的有限 Policy 主题，不宣称任意中文语义检索能力。
- 候选歧义继续返回 unread；来源不足或预算不足保留实际缺口，比较不足不宣称全局最佳教材。每次新章/新范围仍消耗现有预算，没有追加外部额度。
- 正文不长期保存；恢复只复用合法内容无正文的证据。未知网络结果不能通过改身份重派。
- 开发代理使用用户要求的 Sol6.1 medium/xhigh 请求档位；实际模型解析为 NOT OBSERVABLE，未修改全局模型设置。
- 未 push、merge、deploy，未开放公共生成，未恢复旧失败 Run 或付费验收。

`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`

`R01_R05_CONCENTRATED_OFFLINE_PASS`

完成本地 checkpoint 后 STOP。下一次真实验收仍需 Owner 新授权并重新冻结源码、来源、身份和预算。
