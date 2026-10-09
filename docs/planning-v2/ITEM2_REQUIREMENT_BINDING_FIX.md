# Item 2 需求引用最终定向收口

任务：`PLANNING_V2_ITEM2_REQUIREMENT_BINDING_FIX_V1`。日期：2026-10-10。

**`ITEM2_REQUIREMENT_BINDING_OFFLINE_PASS`**

**`ITEM2_REAL_SEMANTIC_RETEST_NOT_RUN`**

现有合同可以合理表达六条冻结需求。仅在 Item 2 专用 Prompt 增加输出前逐稳定 ID 的语义覆盖核对；新定向测试、合成合法 witness 和独立审查通过。原186响应仍为失败，未修正或升级历史结果。离线通过不证明 DeepSeek 会一次正确生成，也不代表教材、课程或完整产品验收通过。

## 1. 基线和修改范围

- Start/source HEAD：`1b4e056faa5ddac7a20b43d4e3eee1e93b43821b`，与参考一致；branch `feat/n1-resource-discovery`。
- 起始 tracked tree clean，只有既存 `.workbuddy/`、`design-preview/` untracked，未操作。
- Final HEAD 为本报告所属本地 tag `checkpoint-planning-v2-item2-requirement-binding-20261010^{commit}`；准确 SHA 保存 ignored delivery receipt，避免提交文档自引用。
- 权威仍为 [冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)，复用 [原186复测报告](ITEM2_REAL_SEMANTIC_RETEST.md) 及 [先前离线修复](ITEM2_REAL_FAILURE_FIX.md)。未重做已通过的能力选择、MCP政策或约束作用域修复。
- 共享证据目录：`var/planning-v2-item2-requirement-binding-fix-20261010/`。

修改文件共五个：

1. `backend/app/infrastructure/providers/capability_planning_contract.py`：仅 `CAPABILITY_SYSTEM` 新增10行指导，唯一生产源码变化。
2. `backend/tests/unit/test_item2_requirement_binding_contract.py`：18个定向案例，复用原 Profile 和独立合成 factory。
3. `backend/tests/fixtures/planning_v2/item2_requirement_binding_failure.json`：第186次原 payload 副本、来源 hash；明确当前 freeze_head 与历史实际 request start HEAD，不改旧 fixture。
4. 本报告。
5. `docs/implementation/progress.md`：前置新记录，原历史字节保留。

未改 Item1 Profile、Policy v2、field shape、Schema、Validator、hash、约束版本、Provider 流程、Run/Worker/预算/Receipt、数据库、配置、前端和公开生成权限。没有自动补引用、repair、重试或第二套 Planner。

## 2. F0：真实输入及失败原样核对

从原184 HTTP response解析模型JSON，以原GoalSpec和原GoalRequirementProfileValidator重建，Profile全文及source_refs/constraint_id与历史记录相同。hash保持：

`b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348`

原184响应SHA256 `5df5001e08e9bdc6d57ebdbc3876b264e95780d67049e5351029a7afd7a69a76`；原186响应SHA256 `8b0726363d90fae713d761209c7bdef600e2349ef2b628ca1472247f163af320`。新增fixture与原186 Provider payload及响应内容完全一致。

原186 JSON未经修改重放仍首拒 `required_requirement_coverage`，缺少 R4 项目应用目标、R6 learn 用途。其余四条有引用；Policy、前置、Python和约束效果原正确事实保持。详细矩阵在 `baseline.json`，不修改历史 request/result 或失败诊断。

当前 Validator 的确切机械责任：引用必须存在；`learning_target_refs` 是该能力 `requirement_refs` 的子集且源 requirement 的 origin 必须 explicit；定义及真实前置精确匹配；ready 结果的 requirement_refs 并集必须覆盖全部冻结 required_requirements。它不证明 explicit 文本必然是技术学习目标，也不证明每条引用与能力的语义相关性。

因此本轮继续分开证明：合法引用和完整性由原 Validator 检查；技术目标、项目应用和规划条件的合理归因由 Prompt 指导及独立语义审查判断。没有以模型自报覆盖取代服务器校验。

## 3. 六条实际需求追溯矩阵

下表描述本场景的一个独立合成合法 witness，能力集合与186相同：python.core、llm.api、structured.output、tool.calling、mcp。它不是固定能力选取模板，也不是修改过的历史模型输出。

| 需求 | 原文本/来源与性质 | 186已有绑定 | 合法 witness 的 requirement_refs | learning_target_refs |
|---|---|---|---|---|
| R1 | 现有Python待办CLI、JSON任务存储及增量Agent背景；project_context | python.core | python.core：已有Python实现载体背景，结合原learner_claim接受已知基础 | 不进入；不据此断言完整json.cli掌握或补学 |
| R2 | “系统学习 Agent 的结构化输出”；goal.target、scope[0]/[2]；技术目标 | llm.api、structured.output | structured.output承担目标；llm.api承担真实交互先修 | 仅structured.output |
| R3 | “系统学习 Agent 的受限工具调用”；goal.target、scope[1]/[2]；技术目标 | llm.api、tool.calling | tool.calling承担目标；llm.api承担真实交互先修 | 仅tool.calling |
| R4 | “把这些能力加入我现有的待办事项 CLI”；goal.target、project_context；项目应用目标 | **遗漏** | structured.output、tool.calling：实际将两项所学能力用于原CLI；project_usage不能替代此原需求ID | 本场景不作为新增技术目标 |
| R5 | “学习深度为应用级”；goal.desired_depth；深度条件 | structured.output、tool.calling | structured.output、tool.calling：applied学习及应用的真实规划条件 | 不进入 |
| R6 | “学习成果用途是学习”；goal.outcome_purpose；用途条件 | **遗漏** | structured.output、tool.calling：两项实际学习能力的规划用途，不创建课程专项 | 不进入；不挪给政策引入的MCP凑覆盖 |

稳定ID逐项保留：

- R1：`req_87dccf132ded659d3d39e74922a217e974b04e6a3c1e40724005e0d6269251fe`
- R2：`req_1a84f4f5e7b28835281d1d3c4798bd224754621434f7fd4e55284e96058a49f5`
- R3：`req_8c998f59c8d9e240523f9aa6c16bf61f978b01d5ad7979db46f1ba811df36387`
- R4：`req_31f0e2d9e8cedf68a82afaa4d2a24a69caca334d808b1d3e2428501284b89121`
- R5：`req_79489f4dae497d8f4b1db68f175e24b5d13f6103db9371aeb33bb7f5e22602e8`
- R6：`req_ef9a96e06fdb82a3b722992b257e488669318f9820ae438c433808b60b87491a`

MCP仍由系统性路线Policy引入：学习required、项目optional，原wire只复制自身Policy定义引用；服务端现有规则加入系统性MCP政策来源。它不借用普通learn来伪造明确技术目标。Python仍accepted_known，唯一真实claim及约束引用不变，只有B类进入学习集合。

## 4. F1：最小 Prompt 增量

原Prompt已经有“所有required_requirements需语义真实覆盖”的泛化说明，但186仍遗漏两个非技术需求。本轮保留旧规则，增量提供明确输出前步骤与本次易漏角色的引用示例：

- 遍历 profile.required_requirements 的每个稳定requirement_id；ready输出前，每条须在至少一个语义相关能力的requirement_refs中出现。
- 区分技术学习目标、项目应用需求、用途/深度条件和已有背景，只有真实技术学习目标进入learning_target_refs。
- 应用目标由实际承担能力关联，保留project_context或声明project_usage不能替代原需求引用；已选结构化输出/工具调用的示例只说明引用方法。
- learn作为实际适用学习能力的规划条件，不创建技术能力、不转移给MCP凑覆盖或伪造用户MCP目标。
- 禁止所有ID复制到所有能力、因漏引用增加无关能力、自报覆盖字段；内部覆盖核对不证明语义正确、不替代Validator。

这没有改变模型决策职责、输出字段或Policy定义。模型仍仅进行原一次语义选择，服务器继续严格校验。Prompt文件新SHA256 `030d3d4e4c9dfb199adbdff5fff76498a18a30d59d844be824aaae21aeffce78`；field shape与原HEAD的AST字面量完全相同。

## 5. F2：RED、GREEN与反例

正式测试环境：`D:/studyplan/.venv/Scripts/python.exe`，PYTHONUTF8=1、PYTHONPATH=backend;.

| 验证 | 实际结果及证据 |
|---|---|
| 修复前新测试RED | **5 FAIL / 13 PASS**，仅新增Prompt步骤断言失败；red.txt。首次日志未独立捕获native退出码，如实保留NOT OBSERVABLE |
| 修复后定向GREEN | **38 PASS**：新18＋旧20相关测试；green-confirmed.txt、pytest-exit.json，native exit0 |
| Ruff | Prompt和新测试 **PASS**，ruff-confirmed.txt、ruff-exit.json，native exit0；仅format新测试 |
| 原186重放 | 仍required_requirement_coverage拒绝，输入及fixture不变 |
| 合成合法witness | 原Validator完整PASS、五能力/六需求/原claim/三约束/Policy前置及确定性hash稳定；明确非真实输出 |
| 缺失R4/R6/同时缺两项 | 均拒绝required_requirement_coverage |
| 错Policy/真实前置/Profile来源 | 均被原Validator拒绝；旧网络/隐私/不合法领域证据保护保持 |
| 实际Provider＋MockTransport | 更新Prompt/原Profile/shape正确，4096、thinking disabled；完整messages **18,933 bytes**，≤32,768；完整request19,061 bytes |

合成正例为独立factory构造，没有先修改186 JSON再称真实通过。原Profile和输入对象保持不变，合成Plan hash与先前同一合法witness一致；实际DeepSeek复测NOT RUN。

四个负向合成示例刻意通过机械Validator，但独立语义审查均FAIL：

1. learn用途作为MCP明确技术learning_target。
2. 项目应用目标从实际承担能力移走，只关联optional MCP。
3. 每个能力复制全部requirement_id。
4. 仅因已有JSON项目新增required json.cli学习。

其原JSON和身份在 synthetic-negative-*.json；正例在synthetic-valid-binding.json。测试只暴露现有机械校验局限，未增加生产NLP规则或语义审核器。独立审查不能把这些Validator PASS当语义PASS。

原初GREEN/Ruff日志只保留进度/文本，未单独捕获native退出码；本轮为关闭该证据缺口，仅补一次同38项及Ruff并立即保存LASTEXITCODE，没有扩大矩阵。初次系统Python缺pytest/3.13拒绝异常的工具环境失败记录在runtime-attempts.txt；未修改生产runtime。正式venv原Validator拒绝与GREEN正常。启动器旧路径提示保留，不操作受保护目录。

## 6. F3：独立审查五项结论

独审复用共享证据包，检查实际diff、原Validator/Policy、架构Item2及Producer/Consumer Matrix、正负witness、Provider wire与定向日志。请求gpt-6.1-sol/xhigh，实际NOT OBSERVABLE；实施worker为gpt-6.1-sol/medium，实际NOT OBSERVABLE。审查不代替真实模型验收。

1. **针对性PASS**：从泛化要求增加逐ID输出前核对、明确project_context/project_usage不能替代应用目标引用，直接针对186两遗漏。
2. **语义关联PASS**：六条映射有真实作用；技术目标、应用目标、规划条件分开，没有单为覆盖挪给MCP。正例语义PASS，四负例语义FAIL，与机械判断分开。
3. **边界PASS**：保持五能力、Python已知、MCP政策、先修、约束及原来源；不扩大外部权限，不强制json.cli或原项目MCP集成。防止“挪给MCP凑覆盖”的规则不禁止窄MCP真实学习目标的合法learn/depth条件引用。
4. **合同表达PASS**：Item1将深度/用途放入required_requirements虽与顶层字段有冗余，当前requirement_refs可以表达其规划条件角色。架构明确Item1生产稳定需求、Item2消费refs、Item7/8检查完整性；没有当前必须改Schema/Validator的矛盾。合成可表达不等于模型可靠生成。
5. **职责建议，未实施**：如真实请求再次遗漏，应停止继续堆Prompt，由Owner单独审议Item1的需求角色与顶层planning conditions，以及Item2模型语义归因/服务端条件消费、Item7/8完整性责任和新版本兼容。不得直接删历史req、机械补ID或重解释旧Profile；不在本Goal先改权威职责。

最终独审 **PASS，无未关闭blocker**。详细证据在independent-review.json/md；审查仅进行必要局部验证，没有重复全量suite、真实外部请求或账本写入。

## 7. 保护、未运行项与下一步

保护核对PASS：原184/185/186请求、响应、诊断、unknown177/183及所有旧账本文件hash不变；账本仍186，没有新增文件。搜索账本、.env和全部非授权生产源码、冻结合同、Policy/Validator均保持。公开generate保护及正式装配未改，沿用原503证据；本轮HTTP/浏览器探测NOT RUN。

真实模型、搜索、Reader、正文、账户预检 **全部0**。PG、Backend全量、Worker、React/浏览器及后续教材/课程验证NOT RUN，没有数据库、migration、历史Run或Receipt变更，没有push/merge/deploy。

仅从输入冻结、当前Provider可构造请求、严格合同和独审角度，适合申请一次新的Item2真实复测；这不是调用授权、成功保证或现金门禁PASS。本轮不消费旧186以外额度、不重派历史identity。若后续Owner批准，仍使用原真实184 Profile、新一次性身份、原Validator和独立语义审查。

`existing_carrier`与`local_tool_scope`仍是未验证实际满足的条件：后续Curriculum缺少可信载体/工具权限证据继续pending/incomplete。正例Plan合法不等于最终Draft可确认。

**`ITEM2_REQUIREMENT_BINDING_OFFLINE_PASS`**

**`ITEM2_REAL_SEMANTIC_RETEST_NOT_RUN`**

**STOP。**
