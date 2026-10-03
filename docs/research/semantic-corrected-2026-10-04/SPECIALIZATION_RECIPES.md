# 首批专项Recipe与组合规则

这些是首批经过深审的冷启动Recipe，作为planner参考骨架，可组合、裁剪、扩展。当前目录不是AgentBranch enum，不限制Agent应用开发的目标。详细章级正文继续随包保留，不能用此索引取代正文。

| 引用标签（开放） | 类型 | 目标触发 | 保留的章级能力链 | 详细入口 |
|---|---|---|---|---|
| rag | Reviewed Specialization Recipe | 资料检索与证据回答需要深化 | ingestion→chunk/provenance→embedding/index→baseline与eval→hybrid/query变换→rerank/context/citation→回归→按需生产项目/Agentic RAG | [AGENT_SPECIALIZATION_RAG.md](AGENT_SPECIALIZATION_RAG.md) |
| coding | Reviewed Specialization Recipe | 软件任务、工作区操作或harness工程 | loop/tools→filesystem/shell→permission/hooks→context→task/memory→long-running/cancel→按需collaboration→coding eval→隔离/service | [AGENT_SPECIALIZATION_CODING.md](AGENT_SPECIALIZATION_CODING.md) |
| workflow | Reviewed Specialization Recipe | 需要确定流程、持久状态或恢复 | deterministic flow→state/branch/loop→retry→checkpoint→interrupt→idempotent effects→测试→按需background/service/multi-agent | [AGENT_SPECIALIZATION_WORKFLOW.md](AGENT_SPECIALIZATION_WORKFLOW.md) |
| browser | Reviewed Specialization Recipe | 需要动态网页观测或可验证浏览器行动 | deterministic automation→locator/actionability→wait/navigation→dynamic state→Browser Agent→auth/session/safety→任务eval→项目切片 | [AGENT_SPECIALIZATION_BROWSER.md](AGENT_SPECIALIZATION_BROWSER.md) |
| evaluation | Cross-cutting Capability Path | 每次新增工具、检索、状态或模型能力 | 第一次tool后Eval-Lite→系统/单步→轨迹与judge校准→RAG/Coding/Workflow/Browser专项→回归/消融/费用→训练后高级eval | [AGENT_EVALUATION_PATH.md](AGENT_EVALUATION_PATH.md) |
| agentic_rl | Optional Training Specialization | 用户目标涉及模型参数训练 | trajectory→state/observation/action/reward→reward hacking→rollout/train-eval隔离→离线小实验→SFT/PPO/GRPO→tool-use环境→long-horizon→可选参数训练 | [AGENTIC_RL_PATH.md](AGENTIC_RL_PATH.md) |

## 可组合情景

| 用户目标 | 组合参考 | 当前阶段的聚焦示例 | 载体 |
|---|---|---|---|
| 已有旅行规划Agent | Workflow+Browser+按需RAG；Tool/API作为能力；Evaluation贯穿 | 先验证行程生成与确认的状态，再学浏览器信息核查；有知识缺口再加RAG | 用户旅行Agent的纵切面 |
| 研究Agent | RAG+Browser+Evaluation | 先证据问答，再扩动态页面取资料 | 用户研究项目；无项目才用默认候选 |
| 企业知识助手 | RAG+Workflow+Auth/permission+Evaluation | 检索来源隔离先成立，再展开审批恢复 | 用户企业项目或合成私有知识实验 |
| 无法归入上述Recipe的语音任务 | Common Core+目标capabilities；现有合适资源部分复用 | 找出语音输入/输出缺口 | 不因未命中Recipe而拒绝规划；资料不足明确需补审 |

这些情景只是组合说明，未新增旅行/语音/企业课程的研究。Auth/permission、Tool/API是能力标签，不需要先创建职业分支或完整专项。

## Recipe消费契约

选中Recipe后保留why now、JIT prerequisite、primary chapters、supplement/comparison、exposure relation、small practice、continuous outcome increment和exit gate。裁剪依据是目标/已会证据/必要依赖；不把详细chapter任务压成能力名。增量列优先映射用户载体，无法自然承载时用micro exercise。一个阶段优先一个主要能力问题；总体目标可有多个Recipe，Evaluation挂到各阶段而不增加一次独占分支选择。

未命中时：拆能力→查前置→从已审资源池挑局部连续Spine→设计正常/失败实践和证据→排列阶段。证据不足则标需要补充搜索/审核，不捏造教程章节。新Recipe先作为用户私有草案，人工审查后才提议公共扩充；当前标签不作为closed enum，新增不应要求改变职业路由。

项目选择独立于Recipe选择：RAG可以学用户自己的知识库，Coding可学用户软件仓库；换项目不必换Recipe。具体教程和项目候选也允许替换，但替代材料需相应审读，不能继承旧材料的review_depth。
