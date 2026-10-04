# Codex Goal v6.13 — F1–F4合同缺口修复与v6.12验收续接

日期：2026-10-04。正式工程：`D:\studyplan`。

## 0. 授权更新与唯一目标

本文件经用户转发并要求执行后，授权继续处理v6.12已复现的四项合同缺口及同一调用链的同类变体；替代v6.12对此四项的STOP状态，不替代其产品语义、历史保护、预算与正式操作边界。

本轮不重新设计课程。保留Agent7/AI4/Cloud4候选、A5/A6、A8小型核心、详细专项、成熟切片、迁移、LearningUnit多对多、canonical保护与既有页面改动。

流程：N0保护工作树 → RED四反例 → 局部修复 → 非收费真实PG/Edge补证 → 条件满足后使用既有授权至多一个新paid Run → STOP。

不得每修完F1/F2/F3/F4单独等批准；上述同类变体属于已知范围。出现独立的新结构根因、缺少可信冻结基准、必须新增公开契约/迁移或触及红线时，停止相关阶段并报告，禁止靠删测试或静默降级续跑。

开发模型遵守本机最新AGENTS及用户授权；不改全局配置、不猜实际解析型号。共享manifest、normalizer、save、publisher仅一个负责人写；只读复核和独立测试可并行。开始时提醒本轮将消耗Codex开发额度。

## 1. N0：保护未提交工作，不能以HEAD代替候选基线

最近报告HEAD为 `1a3262e85296c95d3dfb4349d0d4ef83438f17da`，分支 `feat/n1-resource-discovery`。当前实现还包含v6.11/v6.12未提交候选。以实际状态为准，禁止reset/整树restore/清理未知目录/回到远端旧代码。

先保存：

- 当前HEAD/branch/status、tracked diff、staged diff；必要时使用支持二进制的patch。
- 本轮相关新增文件白名单、文件hash、保护过的本地副本；只读确认ignored证据位置。
- 起点v6.11与v6.12候选边界；不能可靠分离时保存组合基线，不声称已准确拆分来源。
- 335份历史保护清单的最新实际值；发现用户后续合法变化时解释差异，不覆盖它们以求hash一致。

本地证据放D盘既有受限/ignored目录。不得提交.env、密钥、DSN、合成密码、私人正文；`.workbuddy/`、`design-preview/`及用户保护目录不动。不git add -A，不用stash/reset替代审阅。

读取实际当前：

1. v6.12完整审计、31项验收、Fake Plan、progress；
2. `var/v612/contract-review.md`、`.json`与`review-repro.py`；
3. 当前 `planning_structure.py`、`planning_batches.py`、`nodes.py`、`planning_executor.py`、`plan_service.py`、provider adapter与相关测试；
4. 当前Run/Job冻结输入和hash的独立存放/读取路径、原始presentation/receipt与normalized batch关系；
5. 真正历史marker组合、合法用户编辑/确认/未来路线变更路径。

报告给出的代码位置只作入口，不假设行号未变。只审查上述调用链，不再全仓大研究。

## 2. 固化四个真实反例，不以脚本exit0代替防护通过

将现有review-repro中的反例转换成可重复测试。保留原脚本、旧错误及原始失败响应字节。区分：

- “复现成功”：证明bug仍在；
- “保护通过”：篡改被阻止、合法请求能正常完成。

F1原证据是compiled graph+InMemorySaver+Fake保存回调，尚不是PG越权写入；F4是直接批次派发缺口，正式恢复/merge仍拒绝。不得扩大已证明范围。

至少先有4条RED及正常对照，再做修复。未经批准不对原产品库或保留历史Run注入篡改。

## 3. 统一可信来源与派生投影

### 3.1 权威不能来自同一份待校验checkpoint的自证

优先复用服务端已有Run/Job持久化的冻结输入、publication/pack digest、合同/调用身份和原始响应绑定作为独立基准。

禁止只从待检查state读取pack、manifest、expected_hash，再重算自比后声称可信。普通hash能发现内容变化，不自动证明来源；预期值应来自独立绑定的原提交。

若本机没有可复用独立基准，先明确缺口和最小适配方案并STOP，不自行引入签名平台/新数据库或伪造权威。

### 3.2 使用一个共享纯重建/比对实现

语义示意（不是指定新API或函数名）：

```
服务端独立绑定的冻结Run输入
  + 绑定本Run/本阶段/本attempt的已保存原始presentation
  + 已有practice原始结果及合法用户修订依据（适用时）
    ↓
合同识别/完整性检查
    ↓
按所选focus重新校验presentation
    ↓
由冻结canonical与已验证presentation重建normalized batches
    ↓
既有确定性merge
    ↓
与checkpoint顶层拟保存投影比较
    ↓
一致才把同一已验证副本交给已有保存事务
```

normalized batches也是派生数据，不能直接作为绝对权威；必须能追到原始presentation和冻结事实。原始模型输出也不是canonical，只能贡献合同允许的呈现字段。

不要新增第二套planner、第二套publisher或层层互不一致的guard。可由同一纯函数在恢复与保存边界调用，I/O继续留在既有应用层。

## 4. F4优先：严格识别新/旧/混合合同，派发前拒绝降级

以服务端原冻结合同为准检查完整组合：outer structure marker、focus marker、per-batch marker、manifest hash、pack hash、outline关联、batch eligibility与运行身份。

兼容表必须从现有真实历史得出，至少区分：

- 真正历史无新structure/focus marker的legacy；
- 合法 `stage_skeleton_v1` outline + 旧structure；
- 已存在的 `reviewed_structure_v1`（有无focus须按当时冻结格式）；
- 新focus合同；
- mixed reviewed/search_only/no-canonical批次，按冻结eligibility决定，不按文本猜测。

任何残留新structure/focus/per-batch信号都不能因外层字段缺失而降级。未知版本、null/空值、标记不一致应拒绝。只存在旧outline标记不等于新structure。

即使测试删除checkpoint全部新marker/hash，只要独立Run记录表明是新合同，仍应拒绝，不能进入legacy。

检查必须覆盖直接generate_structure_batch、repair、executor恢复与最终保存的实际入口；在provider/Fake派发前生效。失败时provider/Fake计数均为0。真正历史fixture保持旧payload/fingerprint/恢复语义，不给旧manifest回填marker。

## 5. F1核心：最终投影不能绕过保存保护

### 5.1 覆盖实际持久化内容，不只比较structure_batches

从实际materialize/save路径列出会落库的字段，至少包括：

- nodes的身份、title/objectives、scope/acceptance、parent/prerequisites；
- units的身份、阶段归属、顺序、node links、模型呈现字段；
- `rubric.canonical_knowledge`及`rubric.teaching`全部受控字段/focus_refs/intent；
- relations；
- practice_proposal、任务身份/数量/目标/范围/验收/knowledge links；
- outline中实际进入持久化的stage顺序、资源身份/章节/roles、guidance、extensions/项目卡；
- 会影响完成门槛、owner/plan关联的其他持久化字段。

通用状态的日志/时间戳等非内容字段不用硬做逐字比较。JSON归一化只解决既有tuple/list或合法序列化差异，不排序吞掉教学顺序错误、重复或丢失。数目相同不等于内容相同。

### 5.2 默认差异拒绝，不静默覆盖后报成功

在恢复到post-merge/pre-save状态发现受保护或派生字段与重建值不同：记录准确字段路径与脱敏摘要，确定性失败，保存回调0次，Draft/Plan/catalog业务内容写入0。允许按已有契约记失败状态和审计；禁止模型repair该篡改、禁止新派发。

正常生成期间的canonical回填仍保留；区别在于：模型在职责外不能决定canonical，而已经规范化/合并完成的checkpoint异常不能被静默掩盖。

若处于“尚未生成派生字段”的合法中间阶段，可按阶段规则构造；不得把保存前关键字段突然消失伪装为正常缺省值。

### 5.3 应用保存入口是最后一道边界

不只依赖executor入口。实际应用保存/物化入口在写任何业务内容前调用共享验证，防止直接服务调用绕过graph。

复用现有owner/RLS、lease/cancel、锁顺序和幂等事务。对同一受验证不可变副本执行写入，避免检查后又从可变state取另一份数据。不要引入新的全局锁。

确认/发布继续使用已有draft hash与同版本绑定；不要额外resume已终态的short graph。若现有确认路径能绕过保存基准，按同一信任链修其薄接线，不重建发布器。

### 5.4 合法编辑和历史兼容

不能把用户经正式编辑/资源替换/任务调整/未来路线变更产生的新版本恢复回最初模型结果。合法编辑的权威是已有操作记录与不可变修订，而非checkpoint自填的`edited`布尔值。

测试至少包含初始生成、已批准合法编辑、未来路线变更保留前缀、原已发布历史读回、取消、幂等确认。缺少合法依据的所谓edit状态不能绕过保护。

## 6. F2：正向教学权限与排除文本分开

保留units四字段合同及canonical保护。focus refs需精确关联本阶段、所引用node与本次所选项。

禁止拼接全stage所有focus/文档后用主题出现来授予实现权限。建立或复用有界的内部focus投影，分别表达：

- 正向允许解释/比较/实践的能力；
- 该ref允许的教学意图与深度；
- 明确排除/只作比较的技术；
- 对应受审范围与来源；
- 用户明确范围约束。

优先用已有明确结构字段；只有自然语言时，不以“提到该词”自动生成positive permission。必要时对已有受审条目做少量显式内部映射，内容来源与改动可审阅，不重写全课程。

W6“课程不默认学Kubernetes/队列全部实现”不能授权部署集群；Cloud合法Kubernetes阶段仍能安排其已审核实践。允许解释“为何此阶段不部署K8s”，不允许把比较/否定变成强制实现。

自然语言检查只对明确范围和覆盖案例声明有效，不宣称通用语义安全。未覆盖/冲突意图应拒绝或留为不参与任务门槛的待审建议，不静默加必修。所有正式任务/费用/操作授权独立于模型措辞，模型不能通过一段目标文字扩权。

真实代表生成后，对全部阶段的单元目标与任务进行有界教学审阅；ID合法不替代内容审核。

## 7. F3：分离普通输入、输出对象与repair消息的结构上界

使用实际序列化器和字段上限给出三组上界，不用同一个ceiling：

```
normal_input = system + schema + 本阶段局部context + envelope
output_object = 最大unit数 × 合法字段/字符串上限 + JSON开销
repair_input = repair_system/schema/envelope
             + 本阶段局部context
             + 完整但受output边界约束的失败对象
             + 有界字段级errors
```

计算应覆盖JSON转义等开销，字符数与UTF-8字节分别记录；现有token估计不是provider精确分词。不得为通过而把结构上界设成失去意义的整包大小。

必须用现有A2反例验证：11058字符失败对象只有额外acceptance错误，进入有界repair后应能到达MockTransport，完整失败对象与字段错误可见；不能被旧14034普通上界提前拒绝。

仍不发全DomainPack、不把审计材料挪进repair、不删原证据。真正超过允许输出边界的对象应先明确本地失败，不得发送任意大对象。不能以放宽provider输出cap、context window或总预算替代修复。

本地派发预检失败：真实请求数0，不伪装provider已调用、不追加收费receipt、不消耗一次实际模型repair；保留明确preflight失败并终止，不能无界本地重试。

在实际派发边界按现有请求预约与unknown规则计数。实际已发、明确失败、unknown仍计量；不回退历史repair/收费记录，不新增第三次repair，不以HTTP0为由盲目重发可能已派发的attempt。

如果实现中的repair_count含不同语义，先明确“构建/预检”与“实际派发”，用最小当前结构表达，不新建计费系统或修改旧记录。

## 8. 四项修复后的定向验证

按 `03_REGRESSION_CASES.json` 实施。四项已知反例是必过项，不能以完整unit通过代替。

关键链：

1. 原InMemorySaver复现修复后save callback=0，model/Fake新增=0；正常对照仍成功。
2. 新owned业务PG + 真正Postgres checkpoint + 当前compiled graph：在pre-save边界注入相同顶层篡改；恢复拒绝且相关业务表无污染。只能篡改新测试fixture。
3. 直接应用保存入口同样拒绝；错误路径无部分catalog/draft写入。
4. 同一阶段normalized batch与顶层一起伪造、原presentation被换、其他stage/run数据替换时，均不能靠自报hash通过。
5. 合法用户编辑/新版本、取消/lease/幂等与旧legacy不回退。
6. F2中英文反例、同词否定/比较/合法Cloud正例、未选focus不能授权。
7. F3近边界有效repair、partial返回、真正超大对象、本地零HTTP计量、最多两次实际repair。
8. F4直接派发/repair/恢复、单字段和组合缺失、全部marker删除、unknown版本、mixed eligibility。

受影响定向测试先跑，整合后完整unit/contract和受影响PG跑一轮；前端未变可复用字节未变的build，但必须补实际Plan的Edge端到端。

## 9. 补齐实际Plan消费与31项矩阵，不改成新一轮教学设计

安全合同通过后，使用新owned合成样本或确认兼容的既有Fake样本，经普通Auth→真实API→owned PG→Edge，至少验证：

- Agent+RAG：A5/A6、A8、G0–G6、GR、GT实际独立存在；
- A2：3个真实持久化单元能在普通学习主区显示；仍1个任务/原完成门槛；
- GR多项目候选、长guidance与两类Prompt完整消费；可替换不变成每仓必做；
- 窄MCP、已有Node API两条主代表；
- 刷新/退出/重登录回读同一Plan，模型请求增量0。

不得拦截workspace/plan API返回fixture冒充此端到端，不能手工往库插最终投影跳过新合同。Mock组件证据保留其原标签。

v6.12的31项按原要求层级补证：不要求每项都上浏览器/真实模型，但必须在对应UNIT/PG/EDGE层测试受影响路径，不能改写所需层使NOT RUN变PASS。对search_only/旧Python以及修改过的Browser、Coding、旅行组合、Voice、AI和Node至少补必要的非收费持久化/兼容代表；共享执行器可参数化复用，别复制多套harness。

样本来源继续标Fake。实际Edge链通过也不等于本人教学体验已接受。

教学结构不再改变。A7目标重复标题、A8审核范围与当前源码阅读措辞分开记录为非阻塞展示项；不得原位改已冻结Plan。若只是无语义变化的显示去重可做；新权威内容须遵守现有新版本规则，不因此改Stage数或降低验收。

## 10. 提交、复核与非收费门

代码复核必须由没有同时改共享链的只读reviewer检查，明确覆盖F1–F4与同源变体。不要求无止境复核；四个RED→GREEN、合法对照、PG保存边界和Edge链齐备后作出门禁结论。

默认无migration、公开DTO/API、model/provider/cap、课程来源资格变化。不为了版本整齐升级包，也不改所有历史格式；若运行语义改变确需新的内部冻结版本，只影响未来Run并有明确兼容表，不凭一个空marker兜底。

提交只用明确白名单。继承的v6.11/v6.12未提交候选如果需要一起提交，明确说明包含范围及基线，不称只有v6.13改动；保存原diff、来源证据，保证可定向回滚。未通过部分可保留本地但不能标已接受。禁止push/merge。

非收费全部满足可报：`CONTRACT_CLOSURE_READY`，并确认v6.12 `PEDAGOGY_AND_UNITS_READY`所需层是否真正完成。任一关键层未完成继续BLOCKED，不执行收费。

## 11. 条件满足后至多一个新真实代表；沿用现有100上限

这不是新增额度。最近报告累计45/100、该scope unknown0、剩余55。重新只读核对实际账本；有合法后续消费则按真实值计算，不强行回写45。

仅在第8–10节门禁通过、复核没有未解F1–F4/同源阻塞、实际Plan Edge完成后，才可在原预授权中执行一个全新Agent+RAG合成完整Run，不需因第一笔收费再申请。

使用新AcceptanceId、新Run、新owned业务与checkpoint库；历史failed/unknown与v6.12诊断样本不复用派发。沿用同一受控账本，无真实用户数据。

收费前必须实际加载provider binding、DNS/SSRF/TLS、输出caps、局部输入/repair上限与总预算，并输出真实冻结阶段/批次数。若仍18阶段且S=P=18：

- normal=1+18+18=37；repair≤2；最多39；
- output上界=4096+18×8192+18×4096+2×8192=241664；
- 起始45时最坏累计84/100，余16。

以上是计划算术，不是实际usage或真实binding已通过。以当前manifest重算；不足就STOP，不能删课程、缩教学范围或加额度。所有隐形SDK重试仍禁止。

第一笔outline通过真实shape、冻结顺序、receipt与账本才进入structure；A2多单元、A5/A6、项目/专项阶段逐段核对新合同与canonical；阶段practice不增加强制案例和额外门槛。

最多2次整Run repair；known格式错按现有机制，unknown立即停止并核对，禁止重发。修复耗尽、结构性新问题或账不一致则STOP，不开第二Run追绿。

成功后：完整Draft精确比对→一次合成确认→真实PG→Edge→刷新/退出/重登录；生成后的读取与确认新模型请求0。区分模型原输出、canonical回填与内容审核结论。单一样本不证明普遍成功率。

## 12. 红线与STOP

始终禁止：原产品库写入/升级、正式入口切换、正式Worker daemon、RAG修改、新外部搜索、跨scope配额转移、旧failed/unknown重派、提交秘密、reset/强推/merge/push、放松Auth/RLS/SSRF/TLS/证据或完成门禁。

F1–F4同链同类问题在本轮继续修；无法在现有可信来源/存储边界内完成、需要新的公开API/迁移、发现独立未授权结构根因、费用状态未知或预算不足时必须STOP。

完成唯一真实代表后也STOP，只交付用户可审阅计划与证据，不自动正式上线。

## 13. 交付报告

必须给出：

- 实际HEAD/branch/工作树基线，继承与新增候选范围、提交SHA；
- F1–F4逐项：原RED、最小改动、合法对照、UNIT/compiled graph/PG/Edge层证据；
- 可信来源及完整marker兼容表、保存前比对字段、合法编辑路径；
- 普通输入/输出/repair实际字符/bytes上界及零HTTP计量规则；
- 新31项矩阵；NOT RUN保留具体原因，不用总测试数代替；
- 实际Plan Edge是否真走owned API/PG；
- 起始/最终配额、normal/repair/known failure/unknown、usage若可观察；
- 335项历史保护的最新清单与差异解释、回滚与未完成门禁。

结果分开列：

1. `CONTRACT_CLOSURE_READY` / `BLOCKED`；
2. `PEDAGOGY_AND_UNITS_READY` / `BLOCKED`；
3. `TARGETED_PLANNING_ALIGNMENT_PASS` / `FAIL` / `STOP_UNKNOWN` / `NOT_RUN`（REAL必须完整成功才PASS）；
4. 整体产品继续独立判定，不能把本轮PASS自动变成整体READY。

下一最小动作仅给一个，不泛泛写“继续优化”。
