# Planning V2 Item 9 — HTML 原型评审

日期：2026-10-09。基线：`feat/n1-resource-discovery` / `8c578d404a9b6337ede9c0c2e7fd70deb01f3ef4`。

这是对已有首版原型的增量补齐，沿用现有 StudyPlan 的浅色布局、左导航、浅蓝按钮及学习工作区层级。正式 React 尚未实施。本文件不将原型体验认定为产品真实验收。

## 页面结构与演示状态

[打开独立 HTML](prototypes/planning-v2-ui.html)。所有 CSS、图标、数据和 JavaScript 内嵌，可直接在本地浏览器打开；无 CDN 或后端依赖。演示切换器只用于评审，不是正式产品需求。

| 状态 | 主要内容与交互 |
|---|---|
| A 初始规划 | 目标输入、可选补充信息弹窗、生成按钮。已有基础、范围、深度、用途、约束和项目背景全部可留空；无固定方向选择器。 |
| B 需要澄清 | 两项离线 / 实时联网冲突问题；填写并暂存答案后，可继续查看独立生成演示。保留冲突事实，不宣称答案已经通过真实语义分析。 |
| C 生成过程 | 五步用户语言进度，可暂停、继续和返回，不展示内部运行标识或技术预算。 |
| D 完整草案 | 合成 Agent 路线、已有 Python 起点、能力和最终成果概览。五阶段可折叠，默认只展开一阶段；摘要显示安排理由、知识、核心教材及实践。展开显示前置、单元顺序、学习重点、阅读范围、增量和验收。 |
| E 未完成草案 | 保留已确定范围，分别呈现教材示例、缺少正文 / 教学证据及免费访问限制；确认禁用，允许查看缺口、返回修改约束。 |
| F 调整与历史 | 只开放未来阶段说明及一项先修合法的顺序调整。前后差异预览后明确确认；再次修改使旧预览失效。旧版本学习记录保留。目标变化返回目标输入重新规划。 |

## 教学内容与 Item 1～8 语义

- Python 已知声明保留，不安排 Python 复习、补测或相关搜索；没有固定学习日期。
- 贯穿实践使用已有 JSON 待办 CLI，说明目标、功能增量、保留的原功能 / 数据、交付物与验收。MCP 接入是独立 Micro Exercise，不强迫该 CLI 采用 MCP。
- Primary 对应具体章节；Supplement 和 Reference 只补充所需范围。可选 Case Study 独立展示源码工程切片、正常输入输出、失败路径、设计取舍及学习产物，区别于自己的持续实践项目。
- 所有教材、源码案例和历史记录均为合成演示，明确没有真实审核资格、可用教程链接或真实仓库。页面不因标题、目录或 URL 宣称资料已覆盖。
- 局部修改不增加或删除学习要求、教材或任务。任意教材替换 / 实践编辑没有假装可用；目标或方向变化进入重新规划演示。
- 依 Item 7 / 8 现有实施报告，正式能力包含当前草案确认、版本来源、CAS、历史和受控重规划；本页只模拟呈现，不执行上述服务。默认正式 generate 保持原 fail-closed 实现。真实模型语义与完整产品端到端仍待另行验收。

未发现需要修改 Item 1～8 合同或业务实现的设计阻塞。原型不能证明任意自然语言输入已得到正确规划，不能代替真实课程质量、持久化或用户接受验收。

## 验证与独立复核

本轮仅检查新增教学呈现与受影响交互，不重复 Backend、PG、Worker、模型或完整旧浏览器矩阵。首版已通过的 22 项 Edge 定向证据和三项独审修复记录保留于 `var/planning-v2-item9-20261009/`，不冒充本轮新测试。

新证据目录：`var/planning-v2-item9-update-20261009/`。

| 验证 | 实际结果 |
|---|---|
| Microsoft Edge headless `154.0.4258.62`，1440×1000 / 390×844 | PASS，20 项新增呈现 / 交互 / 布局断言；六状态手机布局、长文本换行、弹窗、阶段折叠均覆盖。 |
| 独立调整演示隔离与已采用路线兼容 | PASS，3 项受影响检查；未采用草案不被示例顺带采用或改序，已采用路线仍同步。 |
| 实际截图视觉核看 | PASS；主协调核看清理后的桌面完整草案、阶段、项目案例及手机摘要、实践和最终调整流程。独立审查核看新增教学呈现，最终隔离修复只复核源码 / 浏览器证据。 |
| 内嵌脚本语法、无外部依赖、CSP / 页面请求 | PASS；脚本错误和页面外发请求均为空。 |
| 独立设计复核 | 首次 FAIL，发现独立调整示例共享草案采用状态；修正后关闭复核 PASS。独立代理没有重复运行浏览器。 |
| Backend / PG / Worker / Receipt / 正式浏览器产品端到端 | NOT RUN。产品模型、搜索、Reader、数据库及产品 API 调用均为 0。 |

首个检查脚本将“为何学习”误判为缺失“为什么”，收窄文案匹配导致 FAIL；修正同义文案断言后继续，未为测试修改产品文案。独立隔离修复前的受影响脚本因缺少返回未采用草案入口超时 FAIL；随后添加最小内存快照隔离、返回入口及定向验证，不把该超时冒充生产业务反例。原失败记录保留。

实现和独立审查均请求 `gpt-6.1-sol / medium`；实际解析模型 / effort 为 NOT OBSERVABLE，主会话亦未通过工具切换或核实，不修改全局配置。

本轮只修改原型、评审文档与唯一 progress；全部其他已跟踪文件哈希保持，旧报告、Git checkpoint、账本和受保护目录保留。HTML、说明和截图按授权本地提交，精确 SHA 见最终交付；不 push / merge / deploy。

## 截图

本轮 14 张截图位于 [独立截图目录](prototypes/screenshots/item9-review-v2/)。历史首版截图保留。主要入口：

- 桌面：[初始规划](prototypes/screenshots/item9-review-v2/desktop-initial.png)、[完整草案](prototypes/screenshots/item9-review-v2/desktop-draft.png)、[详细阶段](prototypes/screenshots/item9-review-v2/desktop-stage-detail.png)、[项目拆解](prototypes/screenshots/item9-review-v2/desktop-project-study.png)、[未完成草案](prototypes/screenshots/item9-review-v2/desktop-incomplete.png)、[调整计划](prototypes/screenshots/item9-review-v2/desktop-revision.png)。
- 手机：[初始规划](prototypes/screenshots/item9-review-v2/mobile-initial.png)、[补充信息](prototypes/screenshots/item9-review-v2/mobile-supplement.png)、[阶段摘要](prototypes/screenshots/item9-review-v2/mobile-stage-summary.png)、[详细阶段](prototypes/screenshots/item9-review-v2/mobile-stage-detail.png)、[项目实践](prototypes/screenshots/item9-review-v2/mobile-practice-detail.png)、[调整计划](prototypes/screenshots/item9-review-v2/mobile-revision.png)。

## 待用户决定

1. 折叠阶段中的理由 / 教材 / 实践摘要是否够用，以及展开内容的阅读密度。
2. Primary 与次要资料的层级，自己项目增量与可选源码案例的区分是否清楚。
3. 修改前后差异、保留历史与明确确认的表达是否符合预期。

这些是设计反馈点，不要求用户先回答才能查看原型。用户明确批准前不开始 React 实施。

`ITEM9_HTML_PROTOTYPE_READY_FOR_USER_REVIEW`

`ITEM9_REACT_NOT_STARTED`

`REAL_PRODUCT_ACCEPTANCE_PENDING`

`STOP`
