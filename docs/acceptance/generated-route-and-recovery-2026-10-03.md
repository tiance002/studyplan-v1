# 有限生成路线变更与恢复：2026-10-03

用户现在新增能做什么：从当前批准路线请求修改目标，或重新生成尚未开始的未来阶段；现有 Worker 保存受保护的差异草案，展示原目标、原阶段内容、新阶段内容及保留前缀，经用户明确确认后创建新版本。刷新读取持久运行和预览。未知状态、旧待确认及 reconciliation 运行保留原编号，阻止新生成和自动重派。

分支 `feat/n1-resource-discovery`，本批基线 `a60bac510b645663a8a664d552299dc845b79929`，本地代码 SHA `a616838c327ab724916be59618bcc0e3d68acaa4`。整体 **NOT_READY**，本批没有将实现部署到原产品库，也没有推送或核实远端新 SHA。

## 实现及边界

- 复用现有冻结 manifest、短生成协议、Worker、PlanDraft、唯一 publisher 和路线确认事务。新增代码只有薄适配、纯组合算法和可选 DTO/JSONB 元数据，没有新迁移、依赖、框架或许可证负担。
- `change_goal` 仅使用可用的已发布受控课程版本。目标正文与 GoalSpec.target 分别表达详细目标和显式模板路由；不凭字符串相似度合并知识或历史。目标/上下文没有变化时拒绝；未知模板明确拒绝正式全路线变更。
- `regenerate_future_plan` 固定原课程版本、目标和 GoalSpec，保持当前阶段顺序及已开始前缀。原课程中已移除的可选阶段不会自动加回。旧前缀阶段、单元、任务、指导、资料快照保持原内容；未来使用本次生成并校验的单元/任务快照，内容变化派生新ID，相同内容可幂等复用。同一精确受控知识键通过冻结的节点ID/content_version复用规范身份，不改旧节点或旧单元关联。
- 当前仍运行现有有界**完整课程**生成，然后由服务器丢弃保留阶段候选。它不是只派发未来批次的费用优化；界面说明请求上限含修复。修改目标的上限以新的冻结 manifest 为准。真实收费验证本批 NOT RUN。
- 提交幂等键派生 actor/project 范围内的 Run ID，完整输入 hash 防同键异体；重复请求返回原持久运行，包括成功或 unknown，不重新绑定设置或派发。
- server 元数据 hash 进入 manifest；原阶段差异与节点映射留在内部提交/checkpoint中，不传模型。模型输入没有旧 Summary/Prompt/Outcome、私人资料正文、旧 Plan ID或节点映射。
- 派发前、结果保存及确认时核对当前路线版本和学习/任务/知识/私人资料 basis。确认/取消回执、新 PlanVersion、同包私人选择 lineage 在同一事务；目标改变时不自动复制旧私人选择。通用草案写入拒绝绕过。
- 曝光、总结、Prompt、成果、私人资料写者与路线确认共用 `plan-decision` 项目锁。窄审查提出的并发插入风险，经实际写入路径核对没有成立；不以两次读取替代事务锁。
- 旧路线及原文/成果/证据永久保留；新版学习记录不自动继承完成/accepted。保留前缀内容也不等于继承完成状态。
- 七种有限操作中，`add_topic` 尚未实现；移除仍为受控 optional 阶段粒度。三正式 Blueprint/免费正文审核、真实 provider/GitHub、常态恢复全部门禁、备份恢复与用户实际接受仍待收口。

## 验证与证据

所有 PG 测试只创建并清理 `studyplan_test_*` owned 隔离库，应用角色保留 RLS；未修改原产品库、全局角色、旧 unknown 或账本。Fake 模型不代表真实外部验收。

| 层次 | 状态 | 证据 |
| --- | --- | --- |
| 规则/契约 | PASS | unit/contract 688；2 skipped为 NOT RUN。`var/oct6-guidance/generated-route-unit-contract.xml` |
| 新纯组合 + 真实PG/HTTP/Worker，模型Fake | PASS | 29规则 + 4PG，33；`generated-route-full-pg.xml`。前缀/精确知识复用、普通确认防绕过、刷新/容器重建、输入冻结、隐私、unknown不重派 |
| 目标无变化/模板不足和隐私定向 | PASS | 1PG；`generated-route-goal-pg.xml` |
| 手动有限变化及短生成/checkpoint回归 | PASS | 25PG，1浏览器 deselected为 NOT RUN；`generated-route-recovery-regression.xml` |
| Chrome Fake | PASS | 生成路线、手动有限调整、恢复、进度4个脚本；含202后首GET503保留新编号、手动读回且不第二次POST |
| 正常Chrome + 真HTTP/Worker/ownedPG，模型Fake | PASS | 1；`generated-route-browser-pg.xml`、`generated-route-browser-pg.json`、`generated-route-real-pg.png`。正常登录、前缀、刷新、专用差异确认、新版零继承、重登录、修改目标后取消、390px检查 |
| Frontend unit/build | PASS | 11单元；TypeScript和Vite生产构建 |
| Ruff/mypy/diff | PASS | 受影响文件 Ruff、4个入口及导入依赖 mypy、diff；最终 UI 后再检查差异 |
| 真实收费模型、Tavily、公开GitHub | NOT RUN | 新增外部请求0；用户DNS未配置，当前不做访问 |

早期 FAIL 保留：首个测试误用曝光 POST（实际 PUT），修正测试后得到缺少生成端点的预期 RED；mypy 暴露新 kwargs/联合类型注解，经定向修正；第一次真实浏览器验证发现前端未来重生成携带当前 goal，后端正确拒绝400，前端改为不携带目标。随后业务链完成但测试在关闭浏览器时有未完成route.fetch，退出FAIL；改为等待路由回调结束后关闭，最终PASS。`generated-route-browser-red.xml`、`generated-route-browser-teardown-fail.xml`保留；截图最初受滚动容器裁切，最终改为可读桌面视口并复验。Fake进度脚本默认5173连接失败，显式指定5178后PASS。不能把这些失败隐藏为一次全通过。

## 用量、风险、回滚与下一动作

本批外部模型/搜索/GitHub请求0。累计账本保持模型预约23/50、搜索预约4/1000（unknown1，历史README读取2），没有清空或重置。开发代理请求参数为 Sol/medium（纯组合）、Luna/high（UI与只读审查），实际解析 NOT OBSERVABLE；主模型及快速服务模式无可核实切换工具，未声称切换或修改全局配置。最多2名业务写者，公共契约/事务由主协调整合。

回滚：普通 revert 本批代码提交；保留旧库、原文、版本、checkpoint、账本及新 JSONB 数据，不做数据库降级或删除。已有 `route_change` 受保护草案应保留相应专用确认代码，勿在仍有待确认草案时将保护入口降到不识别元数据的旧版本。没有 master/no-ff/milestone 操作。

下一安全动作：继续受控 `add_topic` 与常态 Worker恢复；10月3日不批量扩内容。只有进入真实公共GitHub验证时才请用户配置 fake-ip-filter；缺独立RAG契约仅暂停该支线。临时验收API与测试Worker已停，隔离库已清理；5178为当前StudyPlan Vite，PG5432不变。保护的V2原指导/Goal原文哈希未变，25个变更代码/测试文件的密钥模式扫描0命中，最终diff/Ruff/mypy PASS。
