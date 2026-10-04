# Codex Goal v6.12 — 教学单元合同与分段项目路线一次性对齐

日期：2026-10-04。工程 `D:\studyplan`。目标是满足最新教学预期并解除当前真实 structure blocker，不是扩建平台。

## 0. 执行与优先级

先读 01_PRODUCT_DECISIONS.md、02_SOURCE_REVIEW.md、04_ROUTE_AND_UNIT_EXAMPLES.md、05_ACCEPTANCE_CASES.json。最新用户决定优先于旧 A5/A6 可略、万能 A8、禁止教学细分等说法。

保留 v6.10 已完成的方向路由、完整/窄范围、显式排除、起点、用户项目适配、A8 内容、多候选及续片修复。如果 v6.11 已实施一部分，先映射复用，不重复新增另一个 structure formatter。

普通范围内连续完成 N0→合同/内容→整合→非收费验收。不得每改一个小字段就停等授权；遇到明确红线、资料不足不能满足必修目标或新的结构性问题才 STOP。

开发模型遵守本机最新 AGENTS/用户授权。只读审查与独立内容/前端可并行；共享合同、manifest、merge、publisher 只由一个整合负责人写。实际模型不可观测就如实记录，不修改全局配置。

## 1. N0：本机事实与冻结范围导出

记录 git status、branch、HEAD、最近提交、与远端 ff3b6c4 的祖先关系。本机 HEAD 优先，不 reset、不 merge、不清理 `.workbuddy/` 和 `design-preview/`。

读取：

- v6.10 验收报告、samples 和唯一 progress。
- 当前 CURRENT_PACKS/发布目录中的 Agent6、AI3、Cloud3 或真实后继版本。
- 当前 select/adapt/freeze、provider system/shape、structure/repair、validator/merge、unit persistence/DTO/workspace 的实际调用链。
- v6.10 唯一失败 Run `run_9c00403807ee4ccb817529611e44efa6` 的已保存合成请求、三次 A2 响应及错误；不 claim、不 resume、不重发。
- 现有100总额度的唯一追加账本，最近报告45已消费。核对实际已消费值，不强行改为45。

生成可读 `FROZEN_SCOPE_REVIEW.md` 与机器 `frozen-scope-review.json`：分别导出公共 Pack canonical 与该失败 Run 私有适配后实际冻结范围，列每阶段名称/key、知识key/title/objectives/scope/acceptance、前置、资料章节、任务、主框架、项目角色和来源证据等级。A2 六个新增 key/标题逐项摘录并标记：范围内教学细分／可能新增能力／证据不足；不要仅凭名字自动归类为合理。

只导出本轮合成目标与公开教材内容；不含用户秘密、密码、DSN、API key、私人原文。无法取得某原始值就明确缺失，不用旧 Agent5 或手写示例冒充 Agent6 冻结原文。

N0 同时列 `ALREADY_DONE / CHANGE / NEEDS_VERIFICATION / BLOCKED`，不再启动全仓大审计。

## 2. 阶段一：受控知识与教学单元的合同修复

### 2.1 复用实体，不重建图谱

用现有 KnowledgeNode、LearningUnit、UnitNodeLink。受控 canonical 节点可保持当前粗粒度，允许同一节点关联多个 LearningUnit；阶段、节点、单元、任务数量不再互相硬等同。

本轮不因模型新增六个 key 就把它们全部加入公共知识，也不把全部知识拆成几百个新节点。

### 2.2 新合同只适用于有明确节点目录的受控批次

新 Run 冻结一个与现有规范一致的内部 structure 格式标记（示例 `reviewed_units_v1`）。复用既有 manifest JSON/hash/fingerprint。旧缺标记 Run 保持旧请求、解释与恢复语义，不改旧记录、旧结果或旧失败状态。

`search_only`、没有冻结节点目录的 Python/通用路径继续使用原受控 AI 草稿机制，不让公共内容池变成所有目标的封闭白名单。混合批次按冻结事实决定适用合同，不仅依据标题或整个 Pack 的 reviewed 字符串。

### 2.3 新 reviewed structure 输入

仅当前阶段：目标、起点/限制、stage key、exact allowed node keys、简短 canonical objectives 与 scope、允许教学重点及已有资源范围引用、review/compare/deepen 意图、明确不允许改的验收与依赖边界。

允许为教学重点建立确定性局部 focus refs，取自本地受控范围，不发全包、发布审计文档或未选章节。字数/字节上界按实际字段与阶段规模检查，不宣称 char/4 是真实 tokenizer。

### 2.4 新 reviewed structure 输出

模型只返回完整 `units` 对象及被明确允许的呈现字段。例如单元标题、学习目标、原有 node_keys、受控 focus_refs、简短教学组织说明。不要求它重新生成 canonical nodes/relations，也不把结构范例里的伪造子 key 当输出建议。

单元身份由现有策略或服务端从当前阶段和序号确定，限长、唯一、顺序可复现；不允许跨阶段偷偷新增正式知识关系。

先校验模型的单元输出，再由本地 canonical authority 重建旧下游需要的 nodes/relations/units 规范结构；现有完整 schema/graph/canonical/hold/任务门禁继续执行。禁止简单关闭 validate_structure_batch。

### 2.5 质量与越权边界

- 每个单元关联当前 allowed node，所有必需节点得到覆盖；单元可以多对多，不要求一节点一个unit。
- 单元允许细讲原范围，不等于可以加入新必修能力。超范围主题给明确 error 或私人待审建议，不自动进入门槛。
- 新合同额外输出 canonical nodes、relations、acceptance、资源发布资格等越权字段时应拒绝，不能悄悄吞掉再报“模型完全符合合同”。
- 保留原响应与规范化结果的分层证据；本地回填不冒充模型正确生成。
- ID、shape 检查不能证明自然语言教学正确；对 A2 代表单元进行内容审阅，检查没有隐含额外强制任务/越权实践。
- LearningUnit 在生成前可变；生成/确认后随 Plan 快照持久化。GET、刷新、重登录不改课、不调模型。

### 2.6 Repair 同步

repair 使用原批次的新合同、exact allowed keys/focus、当前失败对象、具体字段错误，返回完整合法 units 对象，不返回局部 diff 或旧 nodes/relations 合同。

整 Run 最多两次 repair；不增加次数，不新建隐形补全调用，不换模型撞结果。已知失败可按现有规则修复，unknown 不重发。

### 2.7 持久化与呈现细节

当前 merge 会写 canonical rubric：保留必要的受限 teaching 呈现命名空间，canonical_* 只能服务端写。不要写进 rubric 后又在 merge 丢失，也不要仅保存字段却不通过实际 API消费。

优先使用现有 UnitView title/objectives/node_ids/rubric 等真实可用字段。确实缺一个必要展示字段时，先证明现有结构无法表达，给出最小向后兼容只读字段补充方案并STOP请求批准；不能未经批准新增公开DTO/API。不要为教学展示新建业务endpoint、数据库表或替代publisher。

## 3. 阶段二：真实项目与专项教程分段

### 3.1 完整主线

明确 Agent 系统学习目标默认包含 A5 Framework 和 A6 MCP。使用一个主要框架到可完成小型实际应用的程度，其他仅比较；MCP 使用现成受控 server、最小 server 示例和权限边界。复用现有受审章节，不能只加标题。

已有基础使用简短复习/等价能力检查，不标已验证掌握。只学 MCP 等窄目标保留必要闭包，不强塞完整 A5/RAG/小大项目。

A1起 Eval-Lite 贯穿；A7是系统评价入门，后续专项与迁移再深化，不为了排序把所有评价拖到末尾。RL非所有应用开发者硬前置。

### 3.2 持续实践不是第三个强制毕业项目

用户项目从基础阶段就承接练习；无项目才给可替换 Starter。不要再要求做一个全新的平台 Demo 才能进入 Pi/browser-use。进入源码前可检查已有最小链路与必要语言/工具知识。

### 3.3 小型真实源码学习

复用/演进 A8 为 whole_core（或真正适合的 whole_system）阶段：实际候选地址、明确核心边界、正常链、失败链、前置、比较、产物和 Prompt。

Pi/browser-use 属于这类学习对象的候选，不新增“中型工程对比必修层”。根据目标选择一个即可。browser-use 先补必要 Playwright/async 的入场单元；不是先强迫完成全套 Browser 高级专题。

没有合适公开候选时保留待选择信息，不能编造URL；用户指定仓库则标来源资格。给出用户可替换的候选，不强制 Pi。

### 3.4 专项教程

选定 RAG/Coding/Workflow/Browser 等目标后，复用已有详细 recipe，按能力深度生成多个真正阶段，保留具体章节、为什么现在学、REVIEW/COMPARE/DEEPEN、实践增量与验收。

共同知识不反复从零学。这里的“去重”不是删除资料，而是清楚区分对照阅读与新增目标。同一框架/仓库二次出现必须给新增问题，不能把 A5、whole_core、Workflow 复制三遍。

### 3.5 大型成熟项目切片

把混在 G6/C10/W5/W7 等教程阶段的 mature case 学习职责分离出来；保留原教材章节在教程阶段。未来新 Pack 使用独立“成熟工程：目标问题”阶段与学习单元。

大型项目提供3–8个候选切片的提示词是组织建议，不要求都读完。选定的1–2个实质问题可以各自一阶段，内部按需要细分；不要用“源码学习”一个大阶段吞掉所有专项。

公共数据仍不锁 commit/path/function，外部 AI 阅读当前源码。不得部署clone backend、Repo RAG、AST/call graph平台。

若同一阶段提供多个项目作为替代，正式任务验收必须是“任选一个可替换案例完成相同能力证明”，不能每张可选项目卡都生成一个必做任务。

### 3.6 完整/待选范围

对完整且明确专项目标，真实 Plan 必须包含公共核心、小型源码、专项教程、大型切片和迁移验证，不得只用扩展说明写“以后可学”。

对专项未定的系统目标，公共核心+whole_core是本次实际计划；显式显示后续专项待选，不虚称全部高级能力已交付。未选所有recipe不需要生成一堆无用阶段。

## 4. 内容版本与其他方向

从本机当前 Agent6/AI3/Cloud3 或最新合法版本增量构建下一版，只改确有内容变化的方向，不能为整齐无意义升版。保持旧公开包、失败 manifest、v6.8 Plan 原样。

资源URL、章节身份和审核深度沿用受审事实；重绑定不代表新正文已审。新scope需要资料而当前无证据时明确 needs_research_or_review，不借新命名伪造资格。

AI Fullstack：对应 Web/API/GenAI 教程先于相应真实AI源码；持续项目、规模可控参考、专项深化和成熟产品切片分开。不能又把GenAI当所有Agent固定前置。

Cloud：有Node/Go/Java服务直接复用；Linux/网络/DB按需补；容器/手工部署→CI/IaC等按目标；小型服务参考与成熟平台切片分开。K8s不成为所有上线目标必修。未选云商/DB的实际操作保持待选，不假装全部可立即执行。

不在本轮重做三方向资料研究，不新建所有概念节点。

## 5. 最小页面修改

核对 v6.10 已修 ProjectStudyCard；不要重写其多候选/分片算法。

普通学习主区展示当前阶段的 LearningUnit 顺序、标题、目标、所关联受控知识。至少以真实 A2 多单元样本在普通页面展示，不只在偏好对话框下拉框里出现。没有新单元进度门禁、不恢复旧每日总结/节点打分。

整体路线让用户看到“小型源码学习”“专项教程若干阶段”“成熟工程目标切片”是独立内容。可以用现有阶段名、分组视图或guidance，不需要新Roadmap服务。

项目卡明确实践载体与参考源码是不同对象；复制Prompt包含学习重点、已学不等于掌握、当前源码定位、正常/失败链、跳过范围、少量迁移；不发送任何请求。

## 6. 非收费验收：必须先完成

将05案例映射到实际测试，保持SOURCE/REPORT/UNIT/FAKE/PG/EDGE/REAL分层。

关键要求：

- v6.10 A2 原响应在旧合同仍复现越键拒绝；不得篡改原fixture求绿。
- 新units-only正常、坏格式、跨stage、陌生node、越权fields、范围外教学都覆盖。
- 多units→一个canonical的PG持久化/正式确认/普通Edge读回成立。
- 旧marker/manifest/fingerprint/checkpoint、unknown和failed不重派。
- practice合同能消费多units，canonical任务与完成条件不增加。
- 完整Agent含Framework/MCP，窄MCP不扩全课；基线语义不回退。
- 显式RAG路线按顺序出现小型核心、G组教程、大型目标切片，不是只是卡片文案。
- 用户项目/Starter/参考项目可替换；比较框架不增加多个强制实现。
- unit/contract、受影响owned PG、frontend/build、Edge普通页面通过。

保留三条新非收费样本：完整Agent+RAG目标、窄MCP、已有NodeAPI部署。另用Browser/框架已有基础场景做定向验证。新样本标明Fake，不修改旧真实Plan。

完成后输出非收费门禁 `PEDAGOGY_AND_UNITS_READY` 或 `BLOCKED`。普通成功可继续下面唯一真实代表，不要求每个子门都向用户重新审批。

## 7. 唯一真实代表与费用

本包不新增费用额度。沿用用户已授权100总上限，最近报告45/100；实际账本为准。产品搜索与课程外部搜索本轮0，GitHub开发只读不是产品搜索运行。

只有非收费和教学样本验收全部通过，才允许一个全新的真实合成Run。先输出选定路线、真实阶段列表、purpose数、输出上界与剩余额度，自动做派发前预算检查。

目标选择必须一次覆盖本轮关键行为，例如：“从零系统学习Agent应用开发，主要做资料问答，先学通用核心（含Framework/MCP），再看小型开源核心，然后系统深化RAG，最后学习成熟RAG项目相关部分；不做RL/Browser/Coding完整专项。”只用公开内容与虚构需求。

在当前每stage一structure和一practice机制下，若 S=P=N，则：

- 正常请求 `1 + 2N`；
- 最多两次repair，全Run上界 `2N + 3`；
- 输出上界为 `outline_cap + N*structure_cap + N*practice_cap + 2*repair_cap`。

以真实冻结manifest计算，不写死以前7阶段17次。必须满足当前已用+本Run最大请求<=100，以及既有单请求/总token门禁。不能为了容纳预算删A5/A6/专项/成熟项目。无法容纳时STOP报告完整预算，不自行扩大额度或拆成多个paid Run。

保持原provider/model/temperature/caps/SSRF/TLS/账本；失败和unknown保守计量。unknown或回执不一致立即停止，按现有规则核对，不重新派发。同类structure合同失败在既有repair后仍未解决时STOP，不用剩余额度开第二Run碰碰运气。

正常完成后才可合成confirm→PG→Edge→刷新/退出重登录；全部读取不得新增模型请求。报告每purpose用量、repair原因、模型原输出和本地恢复的区别。一个成功样本不等于普遍成功率。

旧v6.10失败Acceptance/Run永不复用；新的业务/ checkpoint库隔离，不访问原产品库和私人资料。

## 8. 红线

不 reset/历史改写、不覆盖旧Pack/Plan，不提升审核证据，不放宽canonical/schema/权限/完成标准，不增加repair，不做新框架/worker/数据库体系，不修改RAG，不切正式入口/启动正式Worker，不push/merge。

默认无migration和公开DTO/API变化。确需新增公开契约或迁移时STOP；不把复用现有字段的安全小改动也拆成审批轮次。

## 9. 交付与停止

建议以独立可回滚切片提交：合同与单元、内容编排、页面与证据。不要重跑无变化的大量测试来堆数字；关键受影响测试必须真实运行。

交付至少包括：

1. 本机基线/差异与冻结范围可读导出；
2. 新合同、marker、兼容及具体改动文件；
3. 三方向哪些包改变/哪些复用，实际阶段和来源映射；
4. 用户要求逐条对应测试与页面位置；
5. 非收费样本地址/来源/账号交付采用受控私下渠道；
6. 唯一真实Run的请求、token、repair、确认与Edge证据或精确失败点；
7. 原账/旧Plan/旧scope保全、新总账、回滚和剩余blocker。

只有“教学编排非收费完整通过＋唯一完整真实代表＋普通页面多单元与项目链可见”才报告 `TARGETED_PLANNING_ALIGNMENT_PASS`。否则报告 `BLOCKED`，说明哪个层未满足。全产品仍按正式部署、用户接受、RAG等独立门禁判定，不随本任务PASS自动改为READY。

结束 STOP。只给一个下一最小动作：用户审阅这条来源明确的新完整计划；不得自动正式上线。
