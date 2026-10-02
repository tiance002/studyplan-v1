export type CurriculumStage = {key:string;title:string;objective:string;prerequisites:string[];notes:string[];optional?:boolean;branch?:boolean};
export const curriculumSources = [
  {title:'OpenAI · Agent evals',url:'https://developers.openai.com/api/docs/guides/evals'},
  {title:'Anthropic · Agent 评估实践',url:'https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents'},
  {title:'OpenAI · Reinforcement fine-tuning',url:'https://developers.openai.com/api/docs/guides/reinforcement-fine-tuning'},
  {title:'Spinning Up · PPO',url:'https://spinningup.openai.com/en/latest/algorithms/ppo.html'},
  {title:'Hugging Face · GRPO',url:'https://huggingface.co/docs/trl/grpo_trainer'},
  {title:'MCP · Architecture',url:'https://modelcontextprotocol.io/docs/learn/architecture'},
  {title:'MCP · Transports',url:'https://modelcontextprotocol.io/specification/latest/basic/transports'},
];
export const agentCurriculum:CurriculumStage[] = [
  {key:'python',title:'Python 与开发环境',objective:'具备可运行、可调试和可复现的最小开发环境。',prerequisites:[],notes:['Python 数据结构、函数、异常处理与依赖管理；用一个小脚本确认环境。']},
  {key:'llm',title:'LLM 与 Prompt 基础',objective:'理解模型输入输出、消息、结构化结果与调用限制。',prerequisites:['python'],notes:['用固定输入比较 Prompt；记录失败、延迟与费用，不把流畅回答当成可靠结果。']},
  {key:'tools',title:'工具调用与结构化输出',objective:'让模型调用有限、明确的工具，并校验结果。',prerequisites:['llm'],notes:['定义 schema、输入校验、权限范围与失败处理；先使用可检查的工具。']},
  {key:'minAgent',title:'最小可运行 Agent 与 Eval-Lite',objective:'跑通模型、工具和环境结果，建立早期评测习惯。',prerequisites:['tools'],notes:['为贯穿项目保留 10–20 个固定案例、预期行为、trace、简单 grader 与费用记录。','在日常练习中积累这些记录，并按正式任务验收要求检查成果。']},
  {key:'eval',title:'Eval 基础与 Reward 设计',objective:'把任务成功、grader 分数和模型自述分开检查。',prerequisites:['minAgent'],notes:['先定义任务的 success / failure，再构造 benchmark dataset，区分开发集与保留测试集。','success rate = 成功任务数 / 有效测试任务数；事先声明错误、超时及重复运行如何计入。','用 deterministic grader 核对结构、数值或工具结果；用 LLM judge 评价难以机械判定的内容，并用人工标注样本检查评分偏差。','保存 trajectory / trace，包括观察、动作、工具参数、结果与错误；同时测量 baseline、cost / latency。','区分任务验收与训练 reward。分析稀疏奖励、奖励代理失真及 Agent 钻评分规则空子的情形。','实践建议：复用最小 Agent 的固定案例，编写一个确定性评分脚本，输出成功率、耗时与失败 trace；再为同一案例设计 reward，展示一个高分但任务失败的反例。']},
  {key:'rag',title:'RAG 与检索质量',objective:'为项目增加来源可追溯的知识检索，定位检索和回答的错误。',prerequisites:['tools','minAgent'],branch:true,notes:['知识应用目标优先：文档处理、检索、引用与无答案处理。','用固定案例检查检索覆盖与答案依据，再决定是否增加复杂检索。']},
  {key:'workflow',title:'Workflow、状态与恢复',objective:'把多步任务的状态、停止条件和恢复路径显式化。',prerequisites:['tools','minAgent'],branch:true,notes:['调试与自动化目标优先：确定性流程、状态、工具失败、重试与恢复。','区分可重复的读取与产生副作用的操作；保留失败轨迹。']},
  {key:'memory',title:'记忆与上下文管理',objective:'检查信息保留、遗忘和来源边界，保留原始会话。',prerequisites:['minAgent'],notes:['按项目需要结合 RAG 或 Workflow 分支；区分会话状态、摘要与长期记忆。','摘要不替代原文；用固定问题检查遗漏、误记与上下文预算。']},
  {key:'mcp',title:'MCP 工具接入',objective:'按项目需要接入明确范围的工具协议。',prerequisites:['tools'],optional:true,notes:['理解 client、server、能力发现与工具 schema；MCP 接入不替代 Agent 决策逻辑。','理解 stdio 与 Streamable HTTP；HTTP 响应可用 JSON 或请求范围内的 SSE。先接入只读工具并检查断连与错误。']},
  {key:'rlBasics',title:'Agentic RL 基础与受控实验',objective:'理解 Agent 作为 policy，如何在 environment 中根据 observation 选择 action。',prerequisites:['eval'],notes:['理解 rollout、trajectory reward 与 RLVR（由可验证结果给出奖励）；区分最终任务成功与每一步的反馈。','理解 PPO / GRPO 的直觉，再分析 long-horizon credit assignment、sparse reward 与训练稳定性，不要求初学者先推导完整公式。','讨论 tool-use RL：工具结果如何进入观察、失败动作怎样影响后续决策、奖励是否诱导无效调用或 reward hacking。','实践建议：在无需云模型的确定性工具环境中生成轨迹，对比规则策略的奖励和真实任务成功率；打印一次长轨迹，指出哪些动作促成或阻碍了最终结果。','轨迹模拟与奖励分析用于理解机制；只有真正更新 policy 参数的实验才记为 RL 训练。']},
  {key:'rlTraining',title:'可选进阶：完整 RL 训练',objective:'在具备理论、工具与算力条件后开展参数训练。',prerequisites:['rlBasics'],optional:true,notes:['补足概率、梯度与 PyTorch，理解 SFT、LoRA 与 TRL；单独规划算力、费用和数据。','保留训练前后对比、未见案例与失败证据；训练前明确数据与算力预算。']},
  {key:'advancedEval',title:'高级评估、诊断与优化',objective:'按 trace 定位失败，用 ablation、泛化与回归验证改进。',prerequisites:['eval'],notes:['无需先完成 RL 训练；按目标从 Eval 基础直接进入系统诊断。','做 trajectory / trace grading，按检索、工具选择、参数、handoff、状态恢复、输出与评分器建立 failure taxonomy。','检查 robustness、generalization 与 regression eval；用保留案例和扰动输入验证改进，避免只适应开发集。','用 ablation 一次改变一个关键变量，比较 cost-quality tradeoff；加入权限、提示注入及副作用边界的 safety eval。','若做过 RL，用同一保留测试集对比训练前后，并检查 reward hacking：奖励升高是否伴随真实任务质量提升。','实践建议：选三条失败 trace 分类，修复一种失败原因，提交同一测试集的前后结果、一次消融对照，以及耗时和费用变化。']},
  {key:'capstone',title:'综合实践：当前主项目成果',objective:'交付可复现的项目、评测记录、架构说明与失败复盘。',prerequisites:['advancedEval'],notes:['根据当前主项目组合所需的 RAG、Workflow、记忆或 MCP 能力，不要求每个项目使用全部分支。','成果包括启动说明、固定演示与评测、失败案例、权限范围、费用与已知限制。']},
];
