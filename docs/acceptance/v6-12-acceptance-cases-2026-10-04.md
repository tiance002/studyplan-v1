# v6.12 逐项教学验收与层次

状态只用 PASS / FAIL / NOT RUN。所需层未运行的用例不因局部检查通过而报告完整PASS。

| 案例 | 要求 | 状态 | 已完成证据与缺口 |

|---|---|---|---|

| B01 | 当前本机HEAD与远端ff3b6c4不同 | PASS | 本机最新HEAD与已有v6.11未提交候选复用；未reset。 |

| B02 | 导出Agent当前公共包与v6.10失败Run冻结内容 | PASS | 公共61阶段/失败私有7阶段及三次A2 parsed原响应实际导出；历史wire缺失明确。 |

| U01 | 有明确A2 canonical目录，生成若干范围内单元 | NOT RUN | UNIT/Fake/PG PASS：A2三单元同canonical，一任务；实际PG样本Edge NOT RUN。 |

| U02 | 新units合同输出包含nodes或relations | PASS | 越权nodes/relations/rubric等拒绝；原响应与规范化entry分开。 |

| U03 | unit引用未知node、其他stage或伪造focus | PASS | 陌生key/跨stage/伪造focus的UNIT拒绝及规范化checkpoint PG篡改拒绝PASS；不覆盖顶层投影漏洞。 |

| U04 | unit的key合法但文本要求范围外K8s训练或新增强制任务 | FAIL | 简单越界UNIT PASS；真实W6排除文本误作许可，合法ref仍能携带强制Kubernetes部署。 |

| U05 | 保存v6.10 A2三次真实失败响应作离线fixture | PASS | 原fixture字节保持，旧合同三次仍失败；错误数1/9/1。 |

| U06 | reviewed_units_v1 repair收到partial对象 | FAIL | 完整四字段repair正常/partial UNIT PASS；较长合法长度失败对象被同输入上限拦截，消耗repair次数。 |

| U07 | 旧无marker及已存在新outline marker的Run | FAIL | legacy wire/hash golden UNIT PASS；同时删除新structure marker+hash的直接批次派发门禁有缺口，最终恢复投影也有漏洞。 |

| U08 | search_only或无固定知识目录的通用/旧Python路径 | NOT RUN | search_only/混合eligibility UNIT与既有generic Fake PASS；本轮generic旧Python新PG验收NOT RUN。 |

| U09 | 生成后保存含多unit与教学说明的Plan | FAIL | 正常多单元PG确认/读取PASS；最终checkpoint顶层rubric篡改仍被保存；实际PG样本Edge NOT RUN。 |

| U10 | 当前stage结构生成及repair | FAIL | 局部正常wire Mock PASS；repair完整失败对象预算存在已复现缺口。 |

| R01 | 从零系统学习Agent应用开发，专项暂未选 | NOT RUN | 新A0–A8/Framework/MCP/专项待选UNIT/Fake/PG PASS；实际Plan Edge NOT RUN。 |

| R02 | 系统学Agent，主目标知识问答，希望深入RAG并学习成熟工程 | NOT RUN | 实际18阶段顺序/章节/两个替代成熟候选一任务/迁移UNIT/Fake/PG PASS；Edge/REAL NOT RUN。 |

| R03 | 我只想学习MCP；我已有/没有Tool与JSON基础两种输入 | NOT RUN | 两种Tool起点定向UNIT及已有Tool四阶段Fake/PG PASS；实际Plan Edge NOT RUN。 |

| R04 | 已会一个框架，希望系统提升Agent能力 | PASS | 已知框架自述仅REVIEW、主框架一深多浅、Workflow新增replay/idempotency定向UNIT与内容审查PASS。 |

| R05 | 希望系统学Browser Agent，以browser-use为小型核心参考 | NOT RUN | Browser B0/B1/B2入场在browser-use A8前的UNIT/离线选择PASS；此新路线完整Fake持久化NOT RUN。 |

| R06 | 希望学Coding Agent，先理解Pi核心再深入工程 | NOT RUN | Pi入口前置/语言缺口诚实表达UNIT/内容审查PASS；完整Coding Fake持久化NOT RUN。 |

| R07 | 已有旅行Agent；主学可恢复Workflow，辅以Browser/RAG | NOT RUN | 主Workflow辅Browser/RAG不生成三全套UNIT PASS；本轮该组合新PG NOT RUN。 |

| R08 | 系统学习Agent但明确不学RAG、只重点工作流 | PASS | 显式不学RAG保留Framework/MCP/Workflow、开放recipe排除定向UNIT及既有Fake回填PASS。 |

| R09 | 希望学Voice Agent，目前无已审Voice recipe | NOT RUN | Voice缺口与已审公共核心保留UNIT/既有Fake PASS；新版本Voice PG NOT RUN。 |

| R10 | 已有React电商后台，希望增加AI商品文案/客服 | NOT RUN | React电商用户项目语义与F4→FS、成熟切片内容UNIT/离线选择PASS；AI4该目标新PG NOT RUN。 |

| R11 | 已有Node API，学习部署、监控、自动发布和恢复 | NOT RUN | Node自身载体11阶段及Compose/可观测教程/成熟Telemetry分段UNIT/Fake/PG PASS；实际Plan Edge NOT RUN。 |

| P01 | 同stage两个可替换候选，长guidance多续片 | NOT RUN | 既有组件Edge多候选/长guidance续片回归PASS、新RAG替代案例PG PASS；两者未合成同一实际PG Edge测试。 |

| P02 | 小型核心和成熟切片各一份Prompt | NOT RUN | 小型whole_core/成熟targeted_slice的冻结Prompt与不同职责内容检查PASS；实际Plan Edge NOT RUN。 |

| P03 | 同一个Pi/browser-use在两个学习段出现 | PASS | 重复框架/同源码在不同学习段的REVIEW/COMPARE/DEEPEN问题和身份复用UNIT及内容检查PASS。 |

| V01 | 新Pack发布与旧v6.8/v6.10数据同时存在 | NOT RUN | 旧源/旧Plan证据/原账保护hash PASS，继承源资格UNIT PASS，新catalog PG PASS；旧v68与v610 owned PG全版本消费本轮NOT RUN。 |

| V02 | 一个阶段多units和附加建议练习 | PASS | A2三单元同canonical不增正式任务、18阶段18任务及canonical完成条件PG精确读取PASS。 |

| C01 | 最终Stage数改变 | PASS | Fake实际冻结18stage、37normal+2repair=39、output 241664；45+39=84≤100；真实binding预检NOT RUN。 |

| C02 | 所有非收费门禁通过后单一全新Agent+RAG代表 | NOT RUN | 非收费门禁未完成且有结构性FAIL，未创建本轮paid Acceptance/Run。 |

| C03 | paid异常或预算/未知状态 | NOT RUN | 预算/unknown/failed保护UNIT覆盖、账本45对回执保持；本轮REAL异常门禁NOT RUN，未收费。 |
