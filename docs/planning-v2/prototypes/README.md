# Planning V2 Item 9 — HTML 原型评审

日期：2026-10-09。状态：等待用户评审；正式 React 实施尚未开始。

打开 [planning-v2-ui.html](planning-v2-ui.html) 即可操作。它是一个自包含文件，CSS、脚本、图标与演示数据全部内嵌，不需要安装依赖、启动产品后端或连接网络。页面上方的“演示场景”可以切换 A–F。刷新后全部演示状态重置。

首版评审曾启动仅监听本机的静态预览：[打开交互原型](http://127.0.0.1:8679/planning-v2-ui.html)，首版 HTTP 200 检查 PASS；该进程当前已退出，不再作为可用入口。它只服务本原型目录，不是产品 API，也没有公网部署。本次直接打开独立 HTML 进行离线浏览器验收，无需启动预览服务。

最新增量评审与最终交付见 [Item 9 评审报告](../ITEM9_HTML_PROTOTYPE_REVIEW.md)。新增截图位于 `screenshots/item9-review-v2/`；下文首版检查历史保留，不当作本次新执行。

## 基线与范围

- Branch：`feat/n1-resource-discovery`。
- 首版 Start / Final HEAD：`8c578d404a9b6337ede9c0c2e7fd70deb01f3ef4`。首版未提交。本次按追加授权进行本地提交，精确 SHA 见最终交付；未 push / merge / deploy。
- 权威：[Planning V2 架构合同](../PLANNING_V2_ARCHITECTURE_CONTRACT.md)。Item 8 边界参考 [实施报告](../ITEM8_REPLANNING_REVISION.md)。
- 新增文件仅本目录的 HTML、评审说明和截图；本地测试脚本与执行证据保存在 Git 忽略的 `var/planning-v2-item9-20261009/`。
- 沿用现有全站的白色左导航、灰蓝背景、浅蓝主按钮和简洁章节层级。手机使用可关闭的导航弹窗。没有另建聊天或 Learning Assistant。
- 正式 PlanningPage、学习工作区、后端、Schema、Prompt、合同、数据库、迁移和发布配置均未修改。受保护目录未操作。
- 起止核对 872 个已跟踪文件 SHA256 全部一致；`git diff --check` 及新增文本空白检查 PASS。

## 页面与交互

| 场景 | 可评审内容与实际响应 |
|---|---|
| A 初始规划 | 目标输入、补充信息、生成按钮。空目标提示；补充弹窗按需填写已有基础、范围、深度、用途、硬约束与项目背景。保存仅暂存于本页，取消不保存。 |
| B 需要澄清 | 独立的“完全离线且实时读 GitHub”冲突示例，两个问题；提交后保留答案，明确尚未进行真实冲突判断。无需重新输入目标。 |
| C 生成过程 | 五步用户语言进度，可暂停、继续、返回；完成后由用户打开草案。定时刷新保持键盘操作焦点。 |
| D 完整草案 | 五阶段合成 Agent 路线；已有 Python 不再复习，以现有 JSON 待办 CLI 贯穿实践。默认展开第二阶段，包含知识单元、章节范围、指导、Primary / Supplement / Reference、实践增量、产物及验收。教材按钮打开本地摘要，阶段与单元可折叠。采用需要明确勾选确认。 |
| E 未完成草案 | 区分已确定目标与缺教材、正文审核、免费访问依据；说明不能正式确认的原因。确认按钮禁用，无跳过门禁操作。 |
| F 调整与历史 | 编辑未来阶段说明、选择一项预设合法顺序调整，预览前后差异后明确确认。编辑预览后再次改动会使预览失效；已开始阶段不移动。确认后的课程顺序与说明同步到完整路线，版本1记录保留。目标变化带回 A 重新规划；新生成草案必须再次确认。 |

弹窗支持关闭按钮、取消、Escape 和点击遮罩外部关闭；Tab 焦点保持在弹窗内。导航中不属于本原型的入口会说明其范围。原型不提供任意任务、教材或项目自由编辑。

## 演示数据与正式能力的区别

**本文件不执行 Planning V2 业务。** 输入不会发送、分析或正式保存；生成展示固定的 Agent 合成示例。B、D、E 是分别设计的场景，切换场景不表示澄清已解决或不完整草案已补齐。

全部教材、章节摘要、项目源码案例和学习历史均为演示数据，页面逐处标明。没有可用教材链接、真实仓库、已审核资格或真实学员成果。完整草案的“采用”只改变内存中的演示状态，不能证明业务完整性门禁或正式持久化通过。

| 基线后端能力（依现有实施记录） | 本轮 HTML 与尚待正式 UI 工作 |
|---|---|
| Item 1–6 目标分析、能力规划、审核覆盖、缺口、资源研究与课程组成 | 演示用户可读内容组织；没有调用任何分析器、资料服务或模型。正式表单接线、错误传播与真实语义仍需后续验收。 |
| Item 7 编译、Draft / Revision 持久化与有界恢复 | 本页不创建 Draft、Plan、Run 或 Job；正式保存、刷新读回、取消与恢复 UI 尚未接入。 |
| Item 8 受控未来说明 / 合法顺序修改及版本保护 | 只模拟此修改范围和明确确认。后台默认关闭的真实外部语义重规划能力没有因原型而开放；任意教材 / 任务编辑未作为可用功能。 |
| 正式公开 generate 继续 fail-closed | 原型独立运行，无产品 API 接线；其确认按钮不能绕过正式门禁。正式 React 页面仍保留原占位状态。 |

本轮没有重新验证前述后端能力，也没有把原型体验标记为整个产品真实验收通过。

## 检查、修正与证据

| 检查 | 结果与范围 |
|---|---|
| HTML 内嵌脚本语法、无外部脚本 / 样式依赖、禁止连接的 CSP | PASS |
| 本机 Microsoft Edge headless `154.0.4258.62`，1440×1000 与 390×844 | PASS；22 项定向断言，手机覆盖全部六个状态，无水平溢出。 |
| 弹窗、折叠、生成暂停 / 继续、确认门禁、历史、输入转义及刷新重置 | PASS；无页面脚本错误、意外弹窗或页面外发请求。 |
| 截图人工核看 | PASS；检查首页、展开阶段、教材层级、手机弹窗、项目实践和版本差异；这是布局判断，不代表用户已批准设计。 |
| 独立设计复核 | 初次 FAIL；三项交互问题修正后关闭复核 PASS。独立代理读取源码及测试证据，未独立重跑浏览器。 |
| 正式 React / Backend / PG / Worker / 真实产品端到端 | NOT RUN；本轮不需要。 |
| 真实产品模型、搜索、Reader、数据库和产品 API 调用 | 0 |

首次浏览器在执行沙箱中未能启动，属于环境限制；在获准的本机 Edge 环境执行。首次交互检查发现弹窗 Tab 循环脱离内容，已添加首尾焦点循环，随后通过。

独立审查主动发现并促成修复：

1. 版本2的顺序和说明未同步到完整课程页：课程页现在读取当前演示版本，同时保持教材对应关系。
2. 重新生成继承旧的“已采用”状态：每次新生成清除草案采用状态，保留旧路线的版本与历史；新草案需要再次明确确认。
3. 进度整段刷新移走键盘焦点：刷新后恢复对应操作控件焦点。

对应定向断言已加入并通过。审查请求模型为 `gpt-6.1-sol / medium`；实际解析模型与 effort 为 NOT OBSERVABLE。主会话模型亦无法通过当前工具切换或核实，未修改全局配置。

截图重拍前回到页顶、移除临时 toast 与键盘焦点干扰；手机长阶段同时提供开头与实践区域截图。截图是实际浏览器渲染，非视觉生成图。

本地执行证据：`var/planning-v2-item9-20261009/browser-check.json`、`prototype-check.cjs`、`review-screenshots.cjs`、`baseline.json`、`scope-check.json`。前述初次失败保留在执行记录中，最终 PASS 不抹去失败。

## 截图

- 桌面：[初始规划](screenshots/desktop-initial.png)、[完整草案](screenshots/desktop-draft.png)、[展开阶段](screenshots/desktop-stage-detail.png)、[未完成草案](screenshots/desktop-incomplete.png)、[修改预览](screenshots/desktop-revision.png)。
- 手机：[初始规划](screenshots/mobile-initial.png)、[补充信息](screenshots/mobile-supplement.png)、[完整草案](screenshots/mobile-draft.png)、[展开阶段](screenshots/mobile-stage-detail.png)、[项目实践](screenshots/mobile-practice-detail.png)、[未完成草案](screenshots/mobile-incomplete.png)。

## 待用户评审

重点评审首页的简洁程度、展开阶段的信息顺序、教材与项目实践的可发现性，以及修改差异和确认的表达。用户批准前不开始正式 React 实施。

`ITEM9_HTML_PROTOTYPE_READY_FOR_USER_REVIEW`

`ITEM9_REACT_NOT_STARTED`

`REAL_PRODUCT_ACCEPTANCE_PENDING`

`STOP`
