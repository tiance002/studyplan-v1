# 三方向前置矩阵：只在首次真正阻塞时补齐

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

这是编排规则，不是要求初学者先修所有条目。测评通过→直接跳过；Primary首次使用前会教→留在主线；用户不会且教材不教且缺它无法继续→安排外部小节。补完立刻回到原章节。资源具体章节由各方向模板给出。

| 能力 | 首次需要处 | 最小诊断任务 | 何时外补 | 补到什么程度 / 不提前扩展 |
|---|---|---|---|---|
| Python函数/字典/列表 | Agent工具；FastAPI handler；Task Service | 写lookup(query)返回字典，缺键有错误 | 不会且Spine默认已会 | 输入/返回/键访问；先不学元类/复杂继承 |
| JSON与schema | tool参数、API请求、作业状态 | JSON字符串→对象→校验→错误 | 不会读写/类型 | JSON不等于Python字面量；知道必需字段 |
| 异常/文件 | tool失败、文档导入、配置 | 文件缺失返回明确错误 | 无法处理失败 | try/except、Path、UTF-8；不先修完整文件系统课程 |
| 最小测试 | 第一项实践 | 正常/错误各一断言 | 不会验证 | mock固定响应与真实外部调用区别；不用先读全部测试理论 |
| 环境/依赖/密钥 | 首次运行教程 | 建独立环境、读环境变量 | 用户尚不会 | 一个管理工具即可；不叠conda/uv/venv三套 |
| HTTP/URL/端口/状态码 | Web第一阶段；cloud service；MCP远程 | 用请求解释method/path/body/response | Primary没教且已用API | 200/201/202/400/401/403/404/422/429/500概念，具体API契约优先；不背完整RFC |
| HTML/CSS/DOM | React之前；browser locator | 表单label/button/状态块 | 没有最小页面基础 | 语义元素、布局/表单；不先学动画/全部CSS |
| JS函数/对象/数组/模块 | React首次组件 | map数据生成项、import函数 | React默认读者会JS | 解构、map/filter、事件；高级原型链后置 |
| Promise/await/fetch | Web API；Pi SDK；browser | 请求→等待→成功/失败/取消 | 无法理解异步链 | 调用状态与异常；不先修所有事件循环细节 |
| React state | 表单与加载状态 | 点击更新列表，解释重新渲染 | React主教程自己教 | 保持原教程顺序，不另开重复state课程 |
| SQL键/查询/事务 | 保存首次数据库实体；云Task DB | 增查改删、唯一键和回滚 | ORM教材只展示代码不教SQL | SELECT/WHERE/INSERT/UPDATE/DELETE、PK/FK、最小transaction；复杂窗口函数后置 |
| 身份认证与授权 | 第一项用户私有数据 | 用户A不能读B记录 | 不懂两者区别 | 服务端校验与owner过滤；不能把CORS当权限 |
| 向量与相似度 | RAG embedding首次 | 计算三个短向量相似度 | 无法理解召回排序 | 相似度/维度/归一化；训练数学不是硬前置 |
| 词项统计/BM25 | RAG sparse对比 | 精确编号与同义查询分别检索 | dense已会但稀疏不懂 | 分词、TF/IDF直觉；不用先学整个信息检索学位课程 |
| 线程/进程/取消 | Coding后台；云worker | 占位结果与最终通知分开 | 分不清任务运行位置 | timeout与信号、资源清理；分布式系统理论按需 |
| 状态/幂等/副作用 | workflow恢复；API重试 | 同一请求重放两次只写一次 | 断点只会记录位置 | 幂等key、提交边界、重复投递；checkpoint不保证exactly-once |
| Linux文件/权限/进程 | 首次服务器部署 | 定位进程、端口、日志 | 本机能开发但不会运维 | 当前部署必要命令；不先学完整Linux管理 |
| Docker image/container | 云Docker；Coding隔离 | 解释镜像与运行容器区别 | Docker主教程自己教 | 保留连续教程；不先讲K8s |
| Git最小协作 | 第一项项目学习 | 读status/diff/log，建立独立分支 | 无法区分本地改动/提交 | 不强制push；worktree只在并行修改需要时 |
| 基础概率/梯度/KL | RL真正参数训练 | 解释策略概率和优化目标 | 目标仅应用开发无需外补 | 应用者先学trajectory/reward/eval；训练者再补数学 |

## 防止三方向串成无限先修

Agent主线不硬依赖React、K8s、Terraform。全栈的简单AI功能不硬依赖LangGraph、RL、向量DB。云主线先部署普通服务，不硬依赖AI。选两个方向时共享HTTP、SQL、测试等已经通过的诊断证据；语言/框架不同部分按COMPARE处理。

## 阶段准入的证据格式

knowledge_id、首次使用阶段、诊断输入、预期输出、用户当前证据、处理（skip/primary/just-in-time）、需要的小节、恢复原主线位置。学习进度只能由用户完成证据更新，不能因打开链接自动判定掌握。失败时缩小补课范围，不把整门教程追加成前置。
