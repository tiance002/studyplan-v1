# Agentic RL：可选专项的完整教学编排

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 类型：Optional Training Specialization。只有参数训练/训练系统目标才展开；普通应用者可停止于轨迹、奖励与评估直觉，不将训练数学/GPU作为应用开发门槛。

研究日期：2026-10-03。本轮阅读资料并静态检查示例，未进行参数训练、GPU租用或API实验。

## 两种出口

应用开发者走R0–R4：能区分模型学习与运行时重试，解释轨迹/奖励/rollout，完成一个奖励漏洞实验，会判断何时先优化检索、工具或workflow。做到这里可以停止，不要求PyTorch、PPO推导或GPU。

训练研究者再走R5–R9：具备Python数组运算与基础概率、可复现评估后，按需学训练机制、SFT、GRPO工具使用与长期任务。真正训练是可选最后一步。系统评估在RL之前；高级训练评估在RL之后深化。

## Spine 与当前资料风险

连续主线是 Hello-Agents 第11章建立应用背景 → Hugging Face Deep RL Unit1解释交互 → Hugging Face LLM Course第12章2→3→4→5建立语言模型后训练与实现。PPO Unit8作为插入的直觉课，不先学整套游戏RL。进入工具使用时接当前TRL文档；Agent Lightning只作为较重的训练系统项目。

| 资料 | 本轮实际检查 | 自己教授什么 | 不能当作已教授什么 |
|---|---|---|---|
| [Deep RL Unit1 RL framework](https://huggingface.co/learn/deep-rl-course/en/unit1/rl-framework) | state/observation/action/discount正文 | RL交互与return直觉 | 不教Agent工具轨迹、LLM训练或工程奖励审计 |
| [Unit8 clipped objective](https://huggingface.co/learn/deep-rl-course/en/unit8/clipped-surrogate-objective) | ratio、advantage、clip正文 | 策略更新幅度与保守目标 | 单节依赖policy gradient背景；不是从零PPO实现课程 |
| [LLM Course ch12/2](https://huggingface.co/learn/llm-course/en/chapter12/2)、[3](https://huggingface.co/learn/llm-course/en/chapter12/3)、[4](https://huggingface.co/learn/llm-course/en/chapter12/4)、[5](https://huggingface.co/learn/llm-course/en/chapter12/5) | 全部四页正文，reward函数、config、LoRA与训练示例 | 后训练背景、GRPO组相对直觉、最小trainer和长度奖励练习 | 主要是单次生成，不等于多轮工具任务；不能仅凭reward曲线判任务能力 |
| [TRL GRPO Trainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) | 当前目录、工具/环境正文与示例、日志指标、配置接口 | 工具接入与每rollout独立环境 | `main`是开发版，执行前必须核对稳定版支持；不是无GPU的低门槛教程 |
| [Agent Lightning stable文档](https://microsoft.github.io/agent-lightning/stable/) | 目录，Quick Start、Basics、Calc-X正文与启动示例 | 训练、rollout控制与代理网关的系统边界 | quick start要求A100与Linux环境；不是每个初学者都应执行的练习 |

教程可公开免费阅读；GPU、模型调用、托管监控与云服务成本单独判断。官方例子中的发布Hub、远程记录不是本课程默认动作，练习可只保存本机产物。

### 必须纠正的教学细节

ch12/4示例有 `num_generation` 拼写，当前TRL采用 `num_generations`；不要复制配置后才发现接口不一致。ch12/5 prose写50 token，但reward对字符串使用 `len`，不是token计数；实际还取决于completions的字符串/对话结构。页面文字模型系列与代码ID也不一致。保留这些例子来理解概念，执行前核对类型、tokenizer、模型ID和稳定依赖。

ch12/3把GRPO引入归于R1并不精确：[DeepSeek-R1论文2.2.1](https://arxiv.org/html/2501.12948v1)明确引用既有GRPO（DeepSeekMath）。课程关于loss增长的说明不可推广为“loss增长证明学习成功”；以独立评估、reward构成与当前loss定义判断。

当前Agent Lightning `/stable/`返回v1.0文档但仍出现development提示，存在站点标签不一致；不据URL承诺发布稳定性。旧0.3.x教程的Trainer/APO流程不能直接与当前v1.0 Gateway/Controller/Trainer拼接。它们归VERSION_CONTEXT。无需升级模型便可由一手文档确认这些差异。

## R0：把已会的 Agent 执行记录变成 trajectory

**为什么现在**：先知道要改进什么行为。前置是工具Agent和E0–E2，不是深度学习。

主读Hello-Agents第11章的Agent与RL连接概念；第4章loop、第8章memory、第9章context作为REVIEW。画一条请求→检索→查看→回答轨迹，标注模型决策、程序控制、工具结果、最终环境状态。只记录实际消息/动作，不要求提取不可见内部思维。

小实践：给两条完成同一任务的路径记录step_id、observation、action、tool_result、terminated、task_outcome。持续助手增量是统一trace和终止原因。退出：区分“应用有记忆”“规则重试”“模型参数被训练”，三者不互相替代。

## R1：state / observation / action / reward

主读Unit1整页（Process→Markov→State/Observation→Action→Rewards），ch12/2同主题快速回顾，关系COMPARE。前置只有轨迹与数字求和。

小实践：本地模拟资料库只公开部分文档；动作read/search/answer、每次工具结果构成新observation，真正世界state包含未读取事实。讨论仅最后一句消息通常不足以满足Markov性质。给一个5步任务手算累计与折扣reward，不做完整概率推导。

持续增量：每条轨迹保存可复位环境和任务身份。退出：能解释为什么工具结果是环境观察、模型动作与程序重试不是同一东西。

## R2：reward design 与 reward hacking

主读ch12/4 Reward Function Design，ch12/5 Define the reward function；另读R1论文2.2.2的可验证奖励与限制。NEW是把成功要求转为可检验反馈；DEEPEN是E1的grader参与优化后会被利用。

小实践：设计三个候选奖励——长度、工具调用次数、最终事实正确。构造“长而错”“无意义重复调用”“猜对但没有引用”的反例。正确性/权限/终态必须独立检查；辅助格式奖励不应压过任务成功。奖励数值不是 universally valid，用项目约束解释权重或分层判据。

持续增量：奖励规格、反例集、人工审计。退出：能展示reward高但任务失败的具体轨迹，提出可验证修正。无需GPU。

## R3：rollout 与 train/eval separation

主读ch12/3 Group Formation与伪代码；ch12/4 Dataset Format。前置E1的数据划分。任务实例与一次rollout分开：同一输入多次采样是多条轨迹，不是多个独立测试题。

小实践：用规则或预录轨迹为同一任务产生4种路径，计算奖励与组均值，碰到全0/全1要记录缺乏区分信号，不用除零。把开发任务族与封存任务族分开；同一模板的仅数字替换不要冒充泛化评估。

持续增量：task_id/rollout_id/seed/policy_version与数据划分。退出：能说明多采样提高挑选结果不等于参数学习，并区分训练reward、validation选配置、test报告结论。

## R4：真正可执行的离线小实验（应用开发者出口）

这是本路线原创练习，不声称来自官方课程，也不声称本轮已经执行。

用Python标准库创建3个合成任务、每题4条候选轨迹：正确且引用；正确但违规；格式漂亮但错；工具失败后安全停止。先封存一组未参与规则调试的任务。写纯函数reward(task, trajectory)与独立success(task, final_state)。打印逐条reward/success，排序后选最高reward，计算“最高reward轨迹成功数/任务数”。

下一轮只修改reward，再测同一开发组和封存组；明确这属于奖励审计/候选筛选，**不是GRPO或参数训练**。若希望做真正无GPU的RL入门，可在小离散状态环境中用tabular Q-learning，但也不能称LLM Agentic RL。

退出产物：一份反例报告、奖励版本比较、两条失败解释和何时值得训练的决策。应用开发者能讲清这些，足够进入项目中的训练方案讨论。

## R5：SFT / post-training 与参数训练必要前置

仅训练目标触发。先诊断：工具没有正确schema、资料没召回或业务状态错误，通常先修应用；要改变模型稳定行为且有数据、可验证奖励和算力时再训练。

主读ch12/2 post-training背景；它对SFT/LoRA只是引用而未系统教授。因而临时补HF ch11/2 Chat Templates → ch11/3 SFT → ch11/4 LoRA（本轮已检查所选三节正文与示例，按selected_sections_read记录），以及tensor/梯度/optimizer的最小练习。不要提前整套机器学习课。

小实践：画base→SFT→RL→独立评估，解释各自数据/目标差异；检查chat template与tool call格式。持续增量是训练数据审计而非改线上助手。退出：能解释loss、训练/推理模式、checkpoint、可训练参数和显存来源。

## R6：PPO / GRPO 直觉及组信号

主读PPO Unit8的ratio与clipped objective，前置补[Unit4 policy-gradient](https://huggingface.co/learn/deep-rl-course/en/unit4/policy-gradient)的Getting the big picture → Objective → Reinforce关键段落（正文已读；证明选读）；再连续读ch12/3 GRPO算法部分与ch12/4实现。

练习：奖励[0,1,1,0]手算相对优势方向；同一动作新旧概率0.2与0.3，解释ratio=1.5及clip的作用。clip不是所有概率变化的绝对硬上限，不保证每次更新安全；零方差组的具体实现按当前库核对。GRPO不使用同样的critic结构不代表不需基线或任何额外开销。

项目增量：训练配置说明书，涵盖group size、sampling、batch、长度、reward与KL设置。退出：能指出组内全成功/失败为什么缺信号，不能背“GRPO必优于PPO”。

## R7：tool-use RL 与可复位环境

主读当前TRL Tools / Environments / Logged metrics，按稳定版本能力决定是否实现environment_factory；若稳定版尚无该API就先用stateless calculator工具和独立任务fixture，不退到开发版盲装。前置会普通tool calling、R5–R6与隔离环境。

小实践：先只运行环境reset→工具动作→reward，不训练。用加法或计数器任务，每rollout独立状态；检查工具输出只作为反馈而非需模仿的模型token，限制工具调用轮次、超时、非法参数和终止。成功必须由环境state判定，不能由模型声明。

持续增量：可复位的训练适配层，线上运行与训练分离。退出：同任务多个rollout不互相污染，奖励不泄露答案，类型与模板正确，能说明调用错误与训练信号如何记录。

## R8：long-horizon credit assignment 与训练系统项目

主读[Agent Lightning论文](https://arxiv.org/html/2508.03680v1)3.1–3.3的接口与credit assignment；当前v1.0 Basics作为VERSION_CONTEXT，Calc-X作为项目参考。前置多轮轨迹、GRPO、独立评估；不是要求云服务工程整条路线。

小实践：5步轨迹最后才成功，把同一终局回报均分、归给每个模型决策、增加过程奖励三种方案比较，构造“前期错误但后期补救”与“早期正确但环境失败”。指出可验证中间步骤奖励也可能扭曲目标，不能假设reward越密越好。

项目学习深度：3–5切片——rollout生命周期、模型请求与logprob采集、环境隔离、reward→advantage、validation；不要部署完整K8s训练平台。当前Quick Start明确A100/Linux要求，Calc-X Minikube另有内存要求；没有相应条件只读与模拟，不把“单GPU”写成普通笔记本可运行。

退出：解释为什么终局成功不自动告诉每一步贡献；区分论文原架构、当前v1.0工程实现和自己推断。

## R9：真正参数训练（可选）与训练后高级评估

主读ch12/5完整实践，只用于理解dataset→model/LoRA→reward→config→train→evaluate/save；它的长度奖励不是工具能力提升的验收任务。ch12/6 Unsloth暂不作为第二套必读，避免混入另一训练栈。

训练前执行依赖与硬件dry-run，核对模型/许可证、稳定API、数据访问、时间与预算；模型下载及GPU运行由学习时明确授权。先用微型可验证算术/工具数据少量更新，保留base结果，必要SFT基线。保存checkpoint不默认发布。

评估：训练reward与独立success分列，base/SFT/RL保持相同推理预算；报告tool args正确、非法调用、任务成功、未见任务族、长度/工具次数/成本、失败样例和多seed条件。reward上升但test下降要作为失败讨论，不调低grader掩盖。

退出：实际更新参数并有配置/日志/checkpoint/独立测试证据才写TRAINED；未运行写NOT RUN。一次小实验不能支持普遍性能或费用结论。进一步研究再按目标学习PPO实现、value/advantage估计、off-policy correction、异步rollout与分布式，不设为应用开发者毕业条件。

## 前置补充课的具体编排与静态问题

HF ch11/2先读Base vs Instruct、apply_chat_template和Hands-on；手写特殊token快速了解，不能把示意表格当成所有模型的协议事实。练习用两条合成messages格式化并核对tokenizer配置，公开smoltalk示例字段必须检查实际schema，不能假定总有input/output列。ch11/3按When to Use SFT→Dataset Preparation→Training Configuration→Implementation→Monitoring顺序主读；packing等真的需要长短样本混装再深化。其完整示例缺AutoModelForCausalLM、AutoTokenizer、setup_chat_format的导入，prose与model ID也不一致，应作为修复静态依赖的小练习而非拷贝即跑。

ch11/4按Understanding LoRA→LoraConfig→SFTTrainer with PEFT→merge/save主读，远程adapter切换选读。手算小矩阵W与AB的参数数，再检查哪些参数requires_grad；已有ch12/5 LoRA只是REVIEW，冻结权重、target_modules和恢复推理是DEEPEN。页面“仅adapter存GPU”表述过简：训练仍需基础权重、激活与相应运行内存，不能据此估算显存。教材片段中的未定义变量与max_seq_length接口按当前稳定TRL核对。小练习产物是模型/adapter/tokenizer关联说明和资源估算，不要求训练已成功。
