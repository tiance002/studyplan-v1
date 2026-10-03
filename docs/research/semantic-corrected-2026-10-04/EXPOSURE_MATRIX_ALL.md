# 三方向重复暴露矩阵

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

REVIEW：同一心智模型已会，做一道诊断/速读后通过。COMPARE：同一问题的不同实现必须并列比较。DEEPEN：新增工程边界，安排失败实践。VERSION_CONTEXT：版本造成命名/API差异，查当前官方与代码。NEW：此前未教。每条映射须说明旧能力证据，不能以“看过章节”冒充掌握。

| 旧→新 | 关系 | 保留阅读 | 缩短重复 | 必须产生的新证据 |
|---|---|---|---|---|
| Hello ch4→LCC s01/02 | REVIEW + COMPARE | 原生tool_use/result消息与handler map | ReAct定义不重讲 | 文本解析式与结构化调用轨迹各一张 |
| Hello ch7→LCC s03/04/05/06/07 | DEEPEN | 权限闸门、hook事件、TODO、委派、按需加载 | Agent/Tool/LLM抽象速查 | 拒绝操作未执行；子消息隔离但文件共享 |
| Hello ch8→LCC s09 | COMPARE + DEEPEN | 文件记忆索引、选择、临时指令过滤 | 保存/检索基本定义 | 跨会话事实可召回，临时要求不永久写入 |
| Hello ch9→LCC s08 | COMPARE + DEEPEN | 确定性转存到摘要的顺序、配对保护 | context窗口定义 | 大日志可恢复；摘要保留当前约束 |
| Hello ch10→LCC s14 | COMPARE | transport与mock tool pool分别标注 | MCP定义速读 | 不把mock验收成真实transport互通 |
| LCC旧docs→新版根目录 | VERSION_CONTEXT | README旧新映射；当前code.py | 不按旧号推断新内容 | 新s05=旧Todo；新s08=旧compact；新增permission/memory等 |
| Hello ch8 RAG→All-in-RAG ch1 | REVIEW | 四步最小pipeline与输入输出 | RAG是何物不重讲 | 能查看检索块，而不只看答案 |
| Hello ch8/9→All-in-RAG ch2–4 | DEEPEN | 解析、分块、索引、检索诊断 | Memory背景速查 | 改分块/召回方法产生可比较证据 |
| All-in-RAG hybrid→BM25补课 | NEW + COMPARE | BM25词项计分与BGE learned sparse差别 | dense定义速查 | 精确词/同义/编号三类查询成绩 |
| All-in-RAG RRF→cross-encoder | COMPARE | rank融合与query-document打分差别 | rerank泛称不反复讲 | 同一候选池排序变化与耗时 |
| All-in-RAG ch5→provider Structured Output | DEEPEN + VERSION_CONTEXT | schema/拒绝/截断与服务端校验 | JSON格式回顾 | 返回合法JSON但业务错误也能被拒绝 |
| Hello ch6 LangGraph→Workflow | DEEPEN | state、checkpoint、interrupt、replay边界 | 最小node/edge速读 | 故障恢复不重复副作用 |
| LCC s10→s16 | COMPARE | 任务依赖图与workflow journal | 状态枚举速查 | 持久任务记录≠外部操作exactly-once |
| Browser Playwright→browser-use | COMPARE | 固定locators与模型观测/行动决策 | DOM/等待基础速查 | 统一终态grader下对比成功率与开销 |
| Eval-Lite→系统Eval→RL | DEEPEN | held-out、回归、reward和judge不同用途 | tool正确性定义速查 | 调参/训练/eval隔离；reward高不等于任务真实成功 |
| Agent tool schema→全栈API schema | COMPARE | HTTP边界、授权、用户错误 | JSON类型速查 | 401/403/422等业务契约与owner过滤 |
| JS事件→React交互 | COMPARE + NEW | 状态驱动UI、表单、列表keys | 函数/object/map REVIEW | 不直接改DOM仍能正确更新界面 |
| React state→服务端持久化 | DEEPEN | 请求状态、DB主键与授权 | 列表渲染不重讲 | 刷新/重启后数据还在，错误不假成功 |
| FastAPI模型→数据库实体 | COMPARE | 请求/响应/ORM生命周期不同 | 字段类型速查 | 敏感字段不序列化、事务回滚 |
| 全栈部署→云服务部署 | DEEPEN | TLS、日志、恢复、容量、成本 | HTTP/端口REVIEW | 端到端访问、故障演练、清理资源 |
| service /health→Docker HEALTHCHECK | DEEPEN | 进程可用与依赖可用区别 | health handler REVIEW | 容器运行但health不通过的反例 |
| HTTP/port→Docker Network | DEEPEN | host与container边界、服务DNS | port语义REVIEW | 容器内localhost为何不能连另一服务 |
| 单容器→Compose | DEEPEN | 多服务声明、volume/network、启动依赖 | Image/Dockerfile REVIEW | DB重启保留数据；启动顺序不代表就绪 |
| Compose→K8s | REVIEW + COMPARE + NEW | Image REVIEW；service DNS COMPARE；desired state/控制器 NEW | 不重装语言基础 | Pod替换不丢持久数据；readiness与liveness区分 |
| 日志→OTel | DEEPEN | trace/span/context propagation、metrics关联 | stdout日志REVIEW | 失败请求跨服务定位；不用全Demo作为入门 |
| 本机test→GitHub Actions | DEEPEN | trigger/job/step/cache/artifact/secrets | 测试断言REVIEW | PR失败阻止发布、secret不进输出 |
| 手工cloud资源→Terraform | COMPARE + DEEPEN | plan/state/drift/change/destroy | 云资源名词REVIEW | 预览变更、辨认破坏性动作、销毁确认 |
| DB CRUD→Backup/Restore | DEEPEN | 一致性、RPO/RTO、恢复演练 | INSERT/SELECT REVIEW | 新环境恢复并验证，备份存在不代表可恢复 |

## 编排策略

每阶段写previous_evidence、exposure_type、novel_boundary、practice_delta。一个主题可多类型，但必须拆清楚对象，例如“RAG定义REVIEW；引用失效DEEPEN”。通过REVIEW诊断可折叠，不删后续必要工程边界。版本冲突列待核查点，不在两套教程之间盲目择一。一次只改一个变量的COMPARE便于解释因果。
