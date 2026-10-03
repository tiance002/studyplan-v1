# Cloud Services Engineering：章节级学习模板

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

## 课程目标与持续项目

**目标**：能把一个小型网络服务从可测试的本地代码，逐步变成可部署、可观察、可自动交付、可恢复的服务，并能解释每一步解决的实际问题。

**Default Starter Project / 默认贯穿项目候选**：Task Service（任务CRUD API，SQLite入门、PostgreSQL按目标）。用户有合适服务时优先沿其纵切面；下面命令/增量用Task Service示范。保留问题、API契约、测试、数据与运行证据，允许重构、换实现或换仓库，新增能力应有可检查的效果。不要先把它切成微服务，也不要因为教程提到就默认增加 Redis、Kafka、service mesh、Helm 或多云。

**入门契约（Just-in-time）**：

- 已有：基础 HTTP 请求/响应、端口、Git/命令行、任意一种后端语言、SQL CRUD、能在本机运行服务、可执行测试。
- 若用户缺少这些能力，只补继续本阶段所需的部分：例如容器端口映射前回顾监听地址/端口；首次云部署前学 CIDR/子网/安全组和身份；首次 CI 秘密注入前学 secret 不进日志/仓库。不要预先安排完整网络课程、Kubernetes 课程或云认证。
- 每次迁移运行同一组可重复检查：单元/集成测试、readiness 请求、一次带数据库写入的 smoke test。保存命令和结果，不能只凭“页面打开了”判定完成。

### 阶段 -1：没有 API 时，先做最小 Task Service 基线

- **为什么现在学**：云工程学习需要一个真实服务作为承载；如果用户还没有 API，从容器开始只会把编排工具变成孤立练习。已会开发 API 的用户不必重学，直接跑本阶段出口诊断后跳过。
- **前置**：基本 Python 语法、函数、类型标注、异常、虚拟环境和命令行；若这些也不熟，只补能完成 FastAPI 样例的 Python 基础，不要求先学完整全栈路线。SQL 概念在需要表、主键、CRUD 时即时引入。
- **Primary 顺序**：FastAPI [First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/)（path operation、交互式文档、OpenAPI）→ [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/) 和必要的 [Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/) → [Request Body](https://fastapi.tiangolo.com/tutorial/body/) → [Response Model](https://fastapi.tiangolo.com/tutorial/response-model/) → [Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) → [Testing](https://fastapi.tiangolo.com/tutorial/testing/)；第一次引入环境配置时按需读 [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/) 的 Pydantic Settings、环境变量、`.env` 和 testing 部分。
- **DB 的 Just-in-time 顺序**：只有要持久化 Task 时，复用 AI 全栈方向已深审的 FastAPI User Guide **SQL (Relational) Databases** 连续示例：数据库连接/Engine 与 model → session dependency → CRUD path operations → 测试；这是 Task Service 首次接数据库的 Primary，不要求先学完整 SQL 课程。先用 SQLite 做小型 CRUD，后续 Compose 阶段迁移到 PostgreSQL。若读者需要 ORM 对照，再选读 [SQLModel FastAPI tutorial](https://sqlmodel.tiangolo.com/tutorial/fastapi/) 或 [Create a Table with SQLModel](https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/)；本次仅核查 SQLModel 教程目录、FastAPI intro 与建表页代表性正文，不将 SQLModel 全站课程列为云服务 Primary。无论工具如何，`create_all()` 是入门建表例子，不是生产 schema migration 策略。
- **已会者诊断/略过**：用现有项目自测 GET/POST/PATCH/DELETE、请求验证、响应字段过滤、错误码、配置外置、持久化和自动化测试；已通过者跳到阶段 0，只补云路线首次使用但此前未学的运维边界。
- **重复处理**：HTTP 与 Python 已会部分 `REVIEW`；FastAPI 参数绑定、Pydantic 请求/响应校验 `NEW`；普通数据模型 vs SQL 表模型 `COMPARE`；把同一套 API 测试带入容器/CI `DEEPEN`。FastAPI SQL 数据库 CRUD 教程复用 AI 全栈 Primary，不在 Cloud 方向重复造一条 ORM 课程。
- **小实践**：建立 tasks 的最小数据模型（id、title、completed、created_at）；完成创建、按 id 查询、列表过滤、更新、删除；用无效输入和不存在 id 验证 validation error 与 404；重启进程后检查数据是否仍在；用 TestClient 测成功与失败路径。
- **Task Service 增量**：生成最小 API + 数据库 + 自动化测试；加入 `/health/live` 和依赖 DB 的 `/health/ready`，但不要提前部署或加可观测性栈。
- **出口**：能演示 CRUD、请求校验、response model、错误处理与自动化测试；能解释服务监听端口、环境配置来源、API 进程与数据库的数据边界；已有项目达到同等标准即可跳过本阶段。

## 教学顺序与项目卡

### 阶段 0：服务基线、配置与健康边界

- **为什么现在学**：容器或云环境会把本地偶然成立的假设暴露出来；先固定服务正常行为，后面才知道部署是否改变了它。
- **前置**：Task Service 可本地启动；掌握基础 HTTP、SQL CRUD 和 Git。测试工具按项目既有语言使用，不另开语言课程。
- **主读/主做**：在现有代码中确认 API 路由、数据库 schema/migration、配置来源、启动命令、测试命令与日志输出。将 `live`（进程能工作）和 `ready`（可以接请求，必要依赖已连通）区分；健康端点可以返回最少状态，不能泄漏 DSN/密码。
- **略读/略过**：还不必引入分布式 tracing、服务网格、复杂指标栈；无需追求完整 twelve-factor 文档，只解释本项目眼下的环境变量与进程边界。
- **重复处理**：API/SQL/异常/测试属于 `REVIEW`；把 DB 可达性纳入 readiness 是 `DEEPEN`。
- **小实践**：本地杀停 Postgres，确认 readiness 反映不可服务而 liveness 不导致错误重启；恢复数据库后验证服务恢复。测试配置缺失时能给出可理解错误。
- **Task Service 增量**：README 加一页“本地运行与验证”，列启动、测试、`/health/live`、`/health/ready` 和预期响应；记录一次依赖故障行为。
- **出口**：能从全新进程开始运行同一组测试；能解释两个健康端点的使用者和失败条件；日志/响应不包含秘密。

### 阶段 1：Docker Image、Container、Dockerfile 和端口

- **为什么现在学**：服务基线稳定后，用不可变镜像描述交付物，再检验“我的机器能跑”能否变成可重建的运行环境。
- **前置**：阶段 0 通过；理解应用监听端口与 HTTP。
- **Primary 顺序**：[Docker Run an app](https://docs.docker.com/get-started/tutorials/run-an-app/) 按 `Before you start → Run a container → Run an application stack → Build an image → Share the image → Clean up → What you learned/Next` 连续完成。随后读 [What is a container?](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/) 与 [Writing a Dockerfile](https://docs.docker.com/get-started/docker-concepts/building-images/writing-a-dockerfile/) 中对应基础示例。
- **推荐章节/本轮任务**：先用官方样例区分 image、container、pull/run；再为 Task Service 写最小 Dockerfile，知道 `FROM/WORKDIR/COPY/RUN/EXPOSE/USER/CMD` 各自影响什么。验证 `docker run -p host:container`；用 `/health/ready` 而不是只看容器处于 running。
- **跳过/后移**：多阶段构建、镜像签名、buildx 多架构与复杂缓存策略放到生产硬化按需深化。Docker 官方基础 Dockerfile 示例未标为生产 ready，不能无检查照搬到公网。
- **重复处理**：程序启动命令是 `REVIEW`；镜像层和容器的生命周期是 `NEW`；`EXPOSE` 不是主机端口发布，和 HTTP 监听的关系是 `COMPARE`。
- **小实践**：改一行响应内容，重建镜像并运行两个 tag；确认未重新构建的旧容器仍使用旧镜像；对外只发布需要的端口。每一步记录 `docker images`、`docker ps`、日志和停止/删除操作。
- **Task Service 增量**：生成可重建的 Task Service 镜像，README 记录 tag、端口映射、测试命令和非 root 运行状态；不要把 `.env`/凭证复制进镜像。
- **出口**：换一台干净环境只靠代码和构建说明就能构建运行；解释镜像、容器、进程、容器端口与宿主机端口的区别；知道标签不是不可变版本证明。

### 阶段 2：Compose、多容器网络、卷与依赖健康

- **为什么现在学**：单个 API 容器不能自动提供数据库；需要一个本地可重复的多服务开发拓扑，并看清容器间如何寻址和保存数据。
- **前置**：阶段 1 有自己的镜像；了解 DB host/port 与连接串。
- **Primary 顺序**：[Docker Compose Getting Started](https://docs.docker.com/compose/gettingstarted/) 七步连续读：1 项目 / Flask / Dockerfile / `.env` / `.dockerignore`；2 Web+Redis 两服务；3 Redis healthcheck 与 `depends_on: condition: service_healthy`；4 Compose Watch（可选）；5 named volume；6 多文件/include；7 `docker compose config/logs/exec` 调试。
- **Task Service 应用章节**：将样例 Redis 替换为 PostgreSQL；Compose service 名作为容器网络 DNS 主机名，宿主机程序再使用不同连接地址；将数据库文件放 named volume。用故障/启动延迟验证应用能重试，而不是相信 `depends_on` 消除了所有竞态。
- **跳过/后移**：Compose Watch 按开发体验需求做；include/多文件属于组织扩展，可快速阅读示例后略过。不要把 `down -v` 用在需保留数据的栈上；`.env` 插值文件不是生产 secret store。
- **重复处理**：端口发布 `REVIEW`；服务名 DNS 与容器网络 `NEW`；Dockerfile vs Compose `COMPARE`；named volume vs 容器可写层 `DEEPEN`；健康检查 vs `depends_on` `COMPARE`。
- **小实践**：依次制造 API 容器启动早于 DB、数据库容器重建、宿主机端口冲突。用 `config`、`ps`、`logs -f`、`exec` 定位；分别比较 `down` 与 `down -v` 对 DB 数据的影响。
- **Task Service 增量**：Compose 一条命令启动 API+Postgres；配置由环境变量注入；测试等待 readiness；明确卷何时保留、何时删除。加一份可供代码审查的拓扑图或服务表。
- **出口**：能从容器网络内解释 API 如何连接 DB；能定位 DNS/端口/启动/卷问题；能指出 named volume 不是备份。

### 阶段 3：第一次云部署——一个服务、一个数据边界

- **为什么现在学**：在加入集群和流水线之前验证云网络、身份、DNS/TLS、外部数据库和账单是真实可行的。保持故障面小，先得出可访问的端点。
- **前置**：阶段 2 通过；理解监听端口、容器入口、DB 连接串。只在此时补目标云商的最小概念：account/project、region、subnet/CIDR、安全组/防火墙、身份凭证/role、public vs private endpoint。
- **Primary**：选一个用户可访问且可设置预算/账单告警的云商。使用官方当前“部署容器服务/部署 VM”最短路径；先只部署一个 Task Service 实例，DB 用托管 Postgres或继续用已管理的外部 DB。第一遍允许手工部署，以熟悉真实依赖和销毁路径。
- **略过/后移**：不先搭高可用多区、K8s 集群、NAT 网关、私有镜像仓库或自建数据库集群；除非项目需求明确，不引入公网数据库。云厂商具体产品名和命令因用户选择而定，计划必须在执行前查当前官方教程/价格页。
- **重复处理**：Docker publish 端口 `REVIEW`；容器端口→云安全组/LB/域名映射 `DEEPEN`；本地 `.env`→托管 secret 与工作负载身份 `NEW`。
- **小实践**：先测试可访问性、TLS、日志和数据库持久性；手动阻断入站端口观察失败；预算/告警设好；用临时数据演示一次 dump 与独立环境恢复，再开放真实用户数据。
- **Task Service 增量**：上线一个小流量环境，写出 region/资源类型/服务 URL、配置位置、销毁方法和当前费用检查入口。密码只放在 secret 管理处，API 通过健康端点验证 DB。第一次启用任何有价值的持久数据前，启用最低限度 DB 备份或 dump，并完成一次隔离环境恢复验证。
- **出口**：能说明请求到进程和 DB 的网络路径；知道哪些云资源计费、如何停机/销毁、哪里查账单；从公网无法访问管理数据库；持久数据已有一次可验证恢复记录。后期阶段 13 再把该方案深化成 RPO/RTO、保留周期与自动化演练。

### 阶段 4：真实多服务与服务间边界（按需求选择）

- **为什么现在学**：项目出现异步通知、耗时工作或独立伸缩需求时，理解 API、worker、DB 之间的部署/故障边界；没有真实需求时停留在 API+托管 DB 即可。
- **前置**：已有云端单服务；理解 HTTP/队列的基本输入输出；能描述为什么同步请求不能满足目标。
- **Primary**：Task Service 保持 Compose 多容器模型；如确有异步任务，把最小 `worker` 与现有 API/DB 对照。用真实 queue 才能教授 broker；不因路线名称强加 Kafka。
- **跳过/后移**：service mesh、分布式事务、复杂 saga、自动扩缩容、跨区域部署只有在观测到需求时出现。
- **重复处理**：Compose service DNS `REVIEW`；跨服务重试、超时、重复投递、幂等键 `NEW/DEEPEN`；一个容器一个职责 `COMPARE`，但不等于每个模块都必须独立服务。
- **小实践**：令 worker 关闭或延迟，API 是否能给出明确结果；模拟同一任务重投，检查幂等；记录一个端到端请求 ID。
- **Task Service 增量**：可选增加“任务完成后通知”的 worker；文档写出触发者、队列、重试/死信或等效恢复方案。若无业务理由则保持一服务并写下不拆分的决策。
- **出口**：能解释边界如何降低/增加复杂度；有超时、重试和幂等的业务行为验证；会在请求链路定位是哪一服务失败。

### 阶段 5：Kubernetes Basics 六模块

- **为什么现在学**：已会部署单服务与多容器，能把“声明目标状态，由控制器反复调谐”的价值与 Compose/手工 VM 比较。
- **前置**：有可运行容器镜像；基本掌握 Service/Pod 不是应用代码本身。不会 Kubernetes 的用户直接从官方 Basics 开始，无需先修集群管理员课程。
- **Primary**：[Kubernetes Basics](https://kubernetes.io/zh-cn/docs/tutorials/kubernetes-basics/) 按原序六模块：① create cluster（Minikube）；② deploy app（Deployment/desired replicas）；③ explore（Pod、Node、kubectl get/describe/logs/exec）；④ expose（Service、labels/selectors、NodePort）；⑤ scale；⑥ update / observe rollout / rollback。
- **命令和陷阱**：从 imperatively 创建 Deployment 开始可以降低 YAML 负担；学习概念后再把自己的服务写成 YAML。Minikube 本地环境不要无意中创建云 `LoadBalancer`；从 `minikube service --url` 或 port-forward 做本地访问。教程 shell 示例常用 POSIX 语法，Windows PowerShell 用户用 WSL/Git Bash 或改写命令。
- **跳过/后移**：不在此阶段读所有 API reference、网络插件、调度器、etcd、K8s 内部源码；官方六模块未系统教 probes、Secret、资源请求限制、PV/PVC，后续按 Task Service 需求补。
- **重复处理**：镜像与 Registry `REVIEW`；Pod/Deployment/控制器/自愈 `NEW`；Compose service vs K8s Service `COMPARE`；Compose volume vs PV/PVC `COMPARE/DEEPEN`；`depends_on` vs reconciliation `COMPARE`；scale/rollout 在实际 controller 层 `DEEPEN`。
- **小实践**：把 Task Service 镜像部署成 1 个副本，expose 后 curl；scale 到 3，删一个 Pod 看控制器补回；滚动更新到新标签，故意使用不存在的标签后 rollback。检查端点与日志，不只看命令成功。
- **Task Service 增量**：保留一组最小 Deployment + ClusterIP Service（或仅本地 port-forward），把现有 readiness endpoint 接到 readiness probe；DB 使用现有托管服务，不放入此阶段集群。
- **出口**：可以画出 Deployment→ReplicaSet→Pod 和 Service→selector→Pod 流量；能观察 rollout/rollback；能解释本地集群的访问方式与云负载均衡计费区别。

### 阶段 6：云原生运行配置、安全与数据选择

- **为什么现在学**：K8s Basics 让应用能运行，但真实服务还需要安全配置、资源边界、探针和持久数据的决策。
- **前置**：阶段 5 的 Deployment/Service/Pod 心智模型。
- **Primary/选读**：[Kubernetes probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)、[ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)、[Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)、[resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)、[Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) 只学 Task Service 当前要用的章节；阿里云中文公开课 8–14 节可作中文词汇补充，但需登录且实际正文未核。
- **略过/后移**：StatefulSet、volume snapshot/topology、NetworkPolicy、CNI、DaemonSet 只在确有学习目标时选读；不把厂商课未打开的内容当已教会。
- **重复处理**：Compose healthcheck `COMPARE`，K8s readiness/liveness/startup 的分工 `DEEPEN`；`.env`→ConfigMap/Secret `DEEPEN`；Compose volume→PV/PVC/StorageClass `COMPARE`，但 Task Service 初期外置 DB 时可不部署卷。
- **小实践**：将配置值注入 ConfigMap、敏感值放 Secret/外部密钥管理；人为令依赖不可用，观察 readiness 从流量端点移除但 liveness 不不断重启；设置合理 requests/limits 并观察 Pod 状态。
- **Task Service 增量**：补 K8s 运行配置与 threat boundary 说明，确保镜像非 root、配置不硬编码、探针对应语义；只在自建数据库确有目标时考虑 PVC。
- **出口**：能选择 probe 语义和资源界限；能说清 Secret 的 base64 不代表加密、需要 RBAC/加密存储；知道 K8s 本身不会替代应用级事务/备份。

### 阶段 7：Task Service 可观测性基础与 OTel 入门

- **为什么现在学**：服务已经跨容器/网络运行，单看本地日志无法解释跨边界请求和慢请求。
- **前置**：理解服务入口、请求和数据库调用；已有日志、live/ready 与最小 smoke test。
- **Primary**：[OpenTelemetry Python Getting Started](https://opentelemetry.io/docs/languages/python/getting-started/) 先走 automatic instrumentation；再阅读 manual traces/metrics 的部分，在需要业务 span 时补；按照文档配置 OTLP exporter/Collector，核对 4317/4318 协议差异和当前依赖版本。
- **略过/后移**：先不加所有 signals、tail sampling、复杂 processor、自托管全栈 Grafana；不在日志中写任务标题、token、密码等敏感或高基数字段。
- **重复处理**：原有日志/指标/健康端点 `REVIEW`；context propagation、span 属性、跨 API→DB trace `NEW`；从已有 trace id 回查日志为 `DEEPEN`。
- **小实践**：执行一次创建任务请求，确认有 service name、HTTP server span、DB/下游调用边界；制造数据库慢查询或错误，判断 trace 是否帮助定位。先用 Collector debug exporter，确认收到再换后端。
- **Task Service 增量**：给本地 Compose 加一个轻量 Collector/验证配置，记录一个正常请求和一个故障请求的 trace；设置不含敏感数据的属性。
- **出口**：能讲解 trace/span/上下文传播和 Collector 的位置；能用 Collector debug output 区分应用没发出与 exporter 后端没收到。

### 阶段 8：OpenTelemetry Demo 大型真实系统切片

- **为什么现在学**：先有自己的最小仪表化服务，再用成熟多语言系统观察 Collector、后端、业务故障和诊断闭环；反过来从大型 Demo 学所有概念会造成负担。
- **前置**：阶段 7 至少能阅读一条 trace；本机有足够 RAM 和磁盘。文档给 full mode 约 6 GB RAM / 14 GB disk、minimal 约 3 GB RAM。
- **主资料**：[Demo Architecture](https://opentelemetry.io/docs/demo/requirements/architecture/) → [Telemetry Features](https://opentelemetry.io/docs/demo/telemetry-features/) → [Docker Deployment](https://opentelemetry.io/docs/demo/docker-deployment/) → [feature flags / memory leak](https://opentelemetry.io/docs/demo/feature-flags/recommendation-cache/)；按目标选一个 scenario。默认用 Compose minimal/full 文档路径，不默认上 Helm。
- **选 3–8 切片**：系统地图；单条请求 trace；Collector receiver/processor/exporter；recommendation cache fault 的 metrics→trace 诊断；Task Service 的 OTel 移植；telemetry sanity tests；有 K8s 前置后再看 Helm 与 Compose 映射。一次只读一个切片；小项目先整体地图、大项目绝不整体通读。
- **跳过**：逐个服务的所有语言代码、Kafka 和 fraud detection（当前场景不涉及）、agentic/profile extras、一次部署全部 K8s 资源。
- **重复处理**：基础 span `REVIEW`；Collector pipeline `NEW`；metrics 与 trace 联合诊断 `DEEPEN`；Demo Compose 与 Helm `COMPARE`。文档在 2026-09-11 更新 Compose 命令，复现旧教程命令时先核对当前文档/版本。
- **小实践**：打开一个故障 flag，先提出会观察到什么的假设，再看 latency/error dashboard 和 Jaeger；记录事实（图表）、解释（可能关系）、推断（根因）三类证据。
- **Task Service 增量**：只吸收 1–2 项：请求 trace 与结构化日志关联；明确 SLIs（请求成功率/延迟）和一个报警草案。不要复制 Demo 全量 stack。
- **出口**：能追一条分布式请求；解释为何 Compose 裸启动不含观测后端；不依赖固定源码路径，能从当前仓库地图动态定位相应实现。

### 阶段 9：GitHub Actions CI——先自动化已能手工做对的事

- **为什么现在学**：本地验证命令稳定后，PR 可以在一致 runner 上自动重跑，及早阻止坏镜像交付。
- **前置**：Git/GitHub 基础、测试命令和 Docker build 命令都已手工验证；了解 YAML 缩进。
- **Primary**：[Understand GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions) → [example workflow](https://docs.github.com/en/actions/tutorials/create-an-example-workflow) 理解 event/job/runner/step → [Python build & test](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) 对应依赖/版本/测试章节；不是 Python 项目则替换成 Task Service 语言的官方 action/setup 指南。
- **略过/后移**：matrix、release 自动发布、cache 策略、self-hosted runner、复杂 reusable workflows 按重复需要选读。
- **重复处理**：本地 `pytest` / build `REVIEW`；workflow runner 是隔离的新环境 `NEW`；运行环境差异/依赖锁定 `DEEPEN`。
- **小实践**：在 pull_request 和 push 上执行 lint、tests、Docker build；让一条测试失败，检查状态检查阻止合并；只上传有必要的报告 artifact。
- **Task Service 增量**：加入可复制的 CI 流程；使用锁定依赖；标记构建产物的 commit/tag；README 说明 artifact 和缓存如何清理。
- **出口**：PR 流程能验证测试+构建；能解释 artifact 和 cache 不同；Action 使用版本与 runner image 会变化，部署前核对官方当前文档。

### 阶段 10：容器交付、受控部署与身份

- **为什么现在学**：CI 已证明代码和镜像构建成功，下一步才有依据将镜像送到 staging；deploy 是有副作用的操作，需要环境保护和最小身份。
- **前置**：阶段 3 有目标环境；阶段 9 CI 成功；准备好预算、镜像仓库和 staging 数据。
- **Primary**：[GitHub deployments/control](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)、[workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)、[secure use](https://docs.github.com/en/actions/reference/security/secure-use)。选定云商时补读 GitHub 的对应 [OIDC cloud provider](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers) 章节和该云商 trust policy 官方正文。
- **略过/后移**：生产多环境审批流程只需展示一条；无条件自动 deploy 每个 branch、以 repo secret 长期保存云管理员 key、来自 fork 的不可信代码访问 deploy secret 均跳过。
- **重复处理**：本地 deploy 命令 `REVIEW`；Environment protection/concurrency/OIDC `NEW`；Action 固定到完整 commit SHA `DEEPEN`（安全使用指南建议）。
- **小实践**：仅向 staging 部署；deployment job 经 environment protection；模拟并发 workflow 与失败回滚；使用短期身份（如该云商支持 OIDC），确认 workflow 条件限制到预期仓库/分支/environment。
- **Task Service 增量**：PR 自动 build/test；仅匹配用户批准的发布来源/分支时可部署staging（main仅为示例，不绑定用户分支）；生产手工批准或保持不设置生产环境。保留上个可回滚镜像并记录迁移策略。
- **出口**：可以追踪谁/什么事件可部署、拿到什么权限、部署到何环境、失败如何回退；已查看当前账户的 Actions 配额与账单入口。

### 阶段 11：Terraform 本地 IaC 基础

- **为什么现在学**：服务运行和部署步骤有了，再将基础设施写成可 review、可重复执行的目标状态。
- **前置**：Docker 可用；手工部署中理解至少一项网络/主机/容器服务资源。
- **Primary**：[Terraform Docker getting started](https://developer.hashicorp.com/terraform/tutorials/docker-get-started) 按 IaC → Install → Build → Change → Destroy → Variables → Outputs 原序读完；每次执行都先读 plan。关注 `terraform init/fmt/validate/plan/apply/show/output/destroy` 和 `.terraform.lock.hcl`/state。
- **略过/后移**：module registry、复杂 provider aliases、远端协作 state 与策略即使在教程目录中出现，也不是第一份配置的前置。
- **重复处理**：手工 run 服务 `REVIEW`；Terraform plan/apply `NEW`；配置的声明式 desired state 与 Compose reconciliation `COMPARE`；state 与业务 DB 内容 `COMPARE`（完全不同备份对象）。
- **小实践**：用 Docker provider 创建一个无持久数据容器；修改端口后读 plan，判断 in-place/update/replacement；输出访问地址并销毁；将 state 加入本地忽略规则，检查是否泄漏。
- **Task Service 增量**：先为本地/临时环境创建一小块可逆资源；不把生产账号状态与练习目录混用；README 给出 fmt/validate/plan/apply/destroy 顺序。
- **出口**：能解释 provider/resource/state 和 plan 的关系；能先读破坏性替换；能销毁所有练习资源；知道本地 state 不适合多人生产协作。

### 阶段 12：Terraform 云商资源（可选）与平台化信号

- **为什么现在学**：Terraform 的本地资源模型掌握后，才把它映射到目标云商资源；跨环境重复、多人协作和审计需要出现时才引入远端 state/modules。
- **前置**：阶段 11 通过；云账户已设预算与 alert；理解 Terraform apply 实际会创建收费资源。
- **Primary/选读**：HashiCorp [AWS getting started](https://developer.hashicorp.com/terraform/tutorials/aws-get-started) 或用户现用云商的当前官方教程；AWS 页 create/manage/destroy 顺序包含 EC2/VPC/security group、变量输出、模块和销毁，官方明确提醒符合 Free Tier 条件也可能发生费用。任何 apply 前核对 region、资源规格、流量/公网费用和 plan。
- **平台扩展门槛**：当两套以上环境/团队重复同类部署，或共享模块/远端 state/review 审计已成痛点，再学 HCP Terraform/远端后端、module、policy、Helm；不要为了“平台工程”提前建 Internal Developer Platform。
- **重复处理**：阶段 3 手工云拓扑 `REVIEW`；Terraform state/plan/apply `DEEPEN`；GitHub Actions deploy 与 IaC apply `COMPARE`，将应用交付与基础设施变更分成不同权限/审批。
- **小实践**：只创建一组极小 staging 资源；将 plan 保存/审阅，apply 后验证，再 destroy；通过账单和资源列表确认清零。适当时先用 HashiCorp hosted interactive lab，但确认是否会调用真实账号资源。
- **Task Service 增量**：将可以安全重复的 staging 基础设施写为 Terraform，state 使用合适的远端加密/锁定方案；为生产部署预设人工 review，而不是将任意 PR 的 plan/apply 凭证开放。
- **出口**：能解释 plan 的所有新增/修改/删除；云资源清理与账单核查有记录；知道何时使用远端 state、何时不需要平台产品。

### 阶段 13：备份、恢复与可运维交付（最终验收）

- **为什么现在学**：服务已能部署和被观察，最终证明数据故障、误删和发布失败后仍能恢复。第一笔持久生产数据写入之前就要有最小备份/恢复方案；本阶段把方案自动化并完整演练。
- **前置**：Task Service 确有持久数据；已知道 PostgreSQL 连接、对象存储/托管 DB backup 选项和账单位置。
- **Primary**：以 PostgreSQL 官方 `pg_dump/pg_restore` 或所选云数据库官方 backup/PITR 文档为主，按当前版本确认命令、角色权限、加密、保留周期和一致性语义。再结合 Terraform state backup/locking 文档与应用数据备份严格区分。
- **略过/后移**：没有业务 RPO/RTO 要求，不做多区域灾备演习；但绝不能把容器 volume 或 Terraform state 当数据库备份。
- **重复处理**：Compose named volume `REVIEW`；数据库 backup/restore `NEW/DEEPEN`；健康检查 `COMPARE`，健康不等于数据已备份/可恢复。
- **小实践**：在隔离环境 dump 一次、恢复到空 DB、运行完整迁移和业务 smoke tests，记录耗时与行数校验；对云备份检查一次实际恢复演习，而不是只截图“备份成功”。
- **Task Service 增量**：形成 runbook：RPO/RTO 假设、备份频率/保留、加密和访问权限、告警、恢复步骤、验收查询、责任人/演习时间、销毁/费用清理。敏感数据不得写进研究报告。
- **出口**：能在时间预算内从备份恢复可验证的数据；写出已测恢复时间、未验证风险和下一次演习日期；能解释一次部署失败和一次数据恢复的实际过程。

## 曝光、前置与迁移摘要

| 第一次出现 | 内容 | 与前后重复的处理 | 必须产出 |
|---|---|---|---|
| Service 基线 | HTTP/SQL/config/test/live/ready | 已学 API 与 SQL `REVIEW`；云可用性语义 `DEEPEN` | 本地可重现验证 |
| Docker | image/container/Dockerfile/port | HTTP 端口 `COMPARE`；镜像生命周期 `NEW` | 可复建镜像 |
| Compose | service DNS/network/volume/healthcheck | Docker 继续 `REVIEW`；K8s 对比后再深化 | 可调试的 API+DB 栈 |
| Cloud | VPC/subnet/firewall/IAM/managed DB/bill | JIT 新前置，不先学整门网络 | 一处 staging 部署及清理 |
| Kubernetes | Pod/Deployment/Service/scale/rollout | Compose `COMPARE`，reconciliation `NEW` | 自有服务 YAML 和更新回滚 |
| OTel | traces/metrics/logs/Collector | 既有日志和健康 `REVIEW`，分布式上下文 `DEEPEN` | 一条故障可诊断请求 |
| GitHub Actions | CI/build/artifact/environment/OIDC | 本地命令 `REVIEW`，受控身份 `NEW` | 可阻止坏发布的流水线 |
| Terraform | provider/resource/state/plan/apply | 手工 deploy `REVIEW`，IaC `NEW` | 可审阅且能销毁的资源计划 |
| Backup/Restore | 恢复、保留、验证 | volume `COMPARE`；数据库灾备 `NEW` | 实测恢复 runbook |

## 项目学习模式：开源参考卡

### 小型参考：Docker Getting Started Todo App

- `repo_url`: https://github.com/docker/getting-started-todo-app
- `why_now`: Compose 已会启动自有应用后，观察一个成熟教学样例如何组织前端/后端、Dockerfile、Compose、tests 与 Actions。
- `prerequisites`: Compose 多容器和镜像 build；CI 仅作为后期研究切片的前置，不妨碍先读 Dockerfile/Compose。
- `known_knowledge`: 容器、服务名网络、Watch、测试、push/pull image。
- `study_mode`: 小项目先快速阅读 README/项目树/Compose 的服务地图；按 Dockerfile、Compose/开发 watch、测试与 CI 三片逐个学习。
- `learning_focus`: 前端与 API 服务拆分仅为开发/构建需要；Compose 如何统一运行；测试如何在 CI 复用；`down` 是否删除数据。
- `desired_depth`: 先整体地图，再 2–3 个关键切片，不完整读客户端业务。
- `important_questions`: 各 service 是开发还是部署边界？生产 image 如何产生？端口、卷、配置和 DB 如何设置？测试能发现什么？
- `avoid_scope`: 不将该项目当云商部署、TLS 或 Kubernetes 教程；不照抄样例秘密、数据库、watch 设定；不锁 commit 和文件路径。
- `expected_outputs`: 一张拓扑图、一份命令/健康检查观察记录、一个 CI 思路说明。
- `migration_candidates`: 从样例迁移 1 项 Dockerfile 构建卫生、1 项 Compose 开发流程；独立验证当前版本兼容性。
- `review_depth`: `selected_sections_read`；本次未本地运行、未逐文件审阅。

### 大型参考：OpenTelemetry Demo

- `repo_url`: https://github.com/open-telemetry/opentelemetry-demo
- `why_now`: Task Service 已接入 OTel 后，观察大型跨语言服务如何产生和汇总遥测，并练习由故障证据而非代码猜测定位问题。
- `prerequisites`: Docker Compose；理解一条 HTTP 请求和 trace/span；机器能承受所选部署模式。
- `known_knowledge`: Collector 是 telemetry pipeline；已见 Task Service 的一个 trace；知道指标和日志的基础含义。
- `study_mode`: 当前仓库整体架构地图，拆成 3–8 个专项切片；每次只读一个。使用当前源码，不靠固定路径。
- `learning_focus`: 服务调用图、Collector receiver/processor/exporter、各后端映射、业务故障旗标、telemetry sanity tests。
- `desired_depth`: 以理解端到端数据流和 1 个诊断情景为主；只按目标深入对应语言服务。
- `important_questions`: 哪个组件发出 signal？在哪里处理/丢失？metric 说明了什么而不能说明什么？trace 具体证实哪个因果边？测试验证 signal 到达哪些 backend？
- `avoid_scope`: 不克隆即读全部服务，不默认启 Kafka/K8s 全栈，不将 Demo 直接当生产 blueprint；K8s/Helm 只在已会基础对象后学习。
- `expected_outputs`: 架构图、单条 trace 解读、fault→metrics→trace 诊断报告、一次 Task Service 迁移建议。
- `migration_candidates`: 迁移一项 span/context 关联模式和一项可观测性验证测试。
- `资源门槛`: Full Compose 约 6 GB RAM / 14 GB disk；minimal 约 3 GB RAM；K8s chart 另需集群约 6 GB 应用内存。
- `review_depth`: `selected_sections_read`；范围限架构、遥测、Docker/Helm 部署和诊断文档；仓库源码未整体深读。

## 退出标准与作品呈现

已选能力的成果应包含对应项（不要求全栈清单全做）：服务拓扑、API/DB 配置边界、容器构建与清理命令、云部署与费用核查方式、健康检查语义、K8s rollout/rollback 实验记录、可观察性故障诊断证据、CI/CD 权限链、Terraform plan/销毁记录、数据库恢复演习。持久数据首次上线前就要有基本备份与恢复验证；平台阶段再深化 RPO/RTO 和自动化。能讲清某个故障如何被发现、如何诊断、怎样恢复，比堆叠更多平台名词更能证明工程理解。


## 可替换与可裁剪规则

云方向不绑定Task Service、Python、PostgreSQL、某云商或Kubernetes。用户已有HTTP服务时复用其语言和数据层；没有服务时才用阶段-1默认候选。没有拆服务/K8s/平台需求时，相关章级单元可作为独立本地实验或暂不展开，不能为了课程制造业务。已经保存有价值数据的载体仍须验证必要备份/恢复。默认教学示例里的main/staging是CI触发情景，实际用用户当前分支与发布策略，不要求checkout或绑定同名分支。公开学习案例不固定commit/path；实际交付物可保留其自身构建版本供回滚。
