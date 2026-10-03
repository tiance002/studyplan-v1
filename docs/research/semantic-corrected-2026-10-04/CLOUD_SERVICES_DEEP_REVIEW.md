# 云服务工程：深审与教学编排建议

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

核查日期：2026-10-03。本文把云服务方向规划为一条能交付、部署、观察并恢复的服务工程路线，不是 Docker、Kubernetes、Terraform 名词清单。主成果沿用持续项目 **Task Service**（任务 CRUD API + PostgreSQL）；小实践负责理解，Task Service 负责积累可展示的运维经验，开源项目负责建立真实系统心智模型。

## 核心判断

推荐的连续顺序是：

> Service Development → DB / config / test / health → Docker 单容器 → Compose 多容器 → 第一次云部署 → 有真实需求时再拆第二个服务 → Kubernetes Basics → 云原生配置与运行边界 → OpenTelemetry → GitHub Actions → Terraform → 平台能力 → Backup / Restore。

云服务不能从编排器开课。服务的 HTTP 行为、配置来源、数据边界和验证命令先清楚，容器与云平台才有可检查的对象。第一处云部署也应尽早出现：云网络、身份、持久化和账单边界需要真实反馈；但应以一项资源、一项服务和账单告警/预算为起点，避免把云厂商认证或网络大全变成前置。

Task Service 适合贯穿全程：它既能很小地开始，又能自然承载数据库持久化、健康检查、容器、部署、可观测性、自动发布和备份恢复。无需为了“多服务”强行引入 Kafka、Redis、微服务或服务网格；若确有异步通知需求，可后来加一个 worker，并明确说明它解决什么业务问题。首个云部署优先让应用连托管数据库或已有外部数据库；不要把 Postgres StatefulSet 作为 K8s 初学者的第一个集群练习。

## 资料审查范围与结论

| 资料 | 实际查看的正文和例子 | 深度 | 教学用途与边界 |
|---|---|---|---|
| [Docker: Run an app](https://docs.docker.com/get-started/tutorials/run-an-app/) | 按作者顺序核查 Before you start、Run a container、Run an application stack、Build an image、Share the image、Clean up、What you learned、What’s next；检查 `docker pull`、`docker run -d --publish 8080:80`、`docker compose up --build --detach`、Dockerfile build/tag/push 与清理命令 | `deep_reviewed`（教程页面完整顺序） | 让 image、container、发布端口、compose stack、构建和镜像分发串起来。清理时 `docker compose down --volumes` 会删卷，需显式讨论数据是否可丢。它是 Docker 入门，不等于生产部署指南。 |
| [Docker Compose Getting Started](https://docs.docker.com/compose/gettingstarted/) | 核查 7 步 Flask + Redis：项目/Dockerfile/.env/.dockerignore；双服务；Redis readiness 与 `depends_on: condition: service_healthy`；Compose Watch；named volume；多 Compose 文件/include；`config`、`logs`、`exec` 调试。查看各步示例配置和故障场景 | `deep_reviewed`（七步主教程） | 连续性好：从一个服务变成应用栈，再处理启动竞态、开发反馈、持久化、扩展和诊断。Include 属于后段扩展，可按需跳过。示例使用 Redis，Task Service 需要迁移到 PostgreSQL；Compose 仅适合作为本地/开发栈学习入口。 |
| [Docker: publish ports](https://docs.docker.com/get-started/docker-concepts/running-containers/publishing-ports/) 与 [Dockerfile](https://docs.docker.com/get-started/docker-concepts/building-images/writing-a-dockerfile/) | 查看端口映射、`EXPOSE` 的说明以及 `FROM/WORKDIR/COPY/RUN/EXPOSE/USER/CMD` 示例；官方示例自己标注未达到生产级 | `selected_sections_read` | 用来纠正“EXPOSE 就对外开放端口”的误解；对比 Dockerfile（构建镜像）和 Compose（运行服务）。随后按需深化非 root、缓存、multi-stage 与 digest 固定。 |
| [Kubernetes Basics](https://kubernetes.io/zh-cn/docs/tutorials/kubernetes-basics/) | 顺序核查六个模块标题/目标，选读集群启动、Deployment、Pod/Node、Service 暴露、扩缩容和 rollout/rollback 代表性正文及命令 | `selected_sections_read` | 官方材料按集群→Deployment→Pod/Node→Service→副本→升级组织，适合作为 K8s 入门主线。多数步骤通过命令操作现有示例应用，不是让学习者从零编写 manifest 的完整练习；教程不负责教应用配置、探针、资源请求/限制、Secret、存储类等生产边界。 |
| [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/) 文档组：Architecture、Telemetry Features、Docker deployment、Kubernetes deployment、feature-flag memory leak 场景、Collector troubleshooting | 选读架构、Collector 数据流、后端映射与 Docker/Helm 部署正文；查看前端入口、Jaeger/Grafana、Collector 配置层叠、fault flag 到延迟/错误率/trace 的诊断路径，以及遥测 sanity test 说明 | `selected_sections_read`；Demo 仓库源码未全量审查 | 极好的多语言分布式观测参考，而非入门主教程。Docker 完整模式需约 6 GB RAM/14 GB 磁盘，minimal 约 3 GB；K8s 页写明应用 6 GB RAM、Kubernetes 1.24+、Helm 3.14+。文档提醒裸 `docker compose up` 不会加载观测后端；应依文档选 compose 文件或 `make start`。Chart 不支持原地跨版本升级，需删除再安装，说明示例部署不能直接当生产升级范式。 |
| [GitHub Actions overview](https://docs.github.com/en/actions/get-started/understand-github-actions)、[example workflow](https://docs.github.com/en/actions/tutorials/create-an-example-workflow)、[Python CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)、[deployment controls](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)、[secure use](https://docs.github.com/en/actions/reference/security/secure-use) | 选读 workflow/event/job/runner/step 心智模型、可执行 YAML、Python 版本与依赖/测试章节、Environment/concurrency/保护规则，以及 Action 固定到完整 SHA 的安全建议 | `selected_sections_read` | 先复用本地 test 命令，再 build/test，之后才加镜像推送与部署。官方示例有 Node 与 Python 差异，应按项目语言替换；Action 版本、runner 镜像和免费额度会变，不能把教程样例中的版本当长期固定事实。密钥环境、OIDC 信任条件和 runner 安全应在首次部署阶段按所选云商补充。 |
| [Terraform Docker tutorial](https://developer.hashicorp.com/terraform/tutorials/docker-get-started) | 核查完整七段顺序：IaC 概念、安装、Build、Change、Destroy、Variables、Outputs；查看 Docker image/container 资源示例、`terraform init/fmt/validate/plan/apply/show/output/destroy` 操作和 state/lockfile 说明 | `deep_reviewed`（七课教学链） | 适合零云账单地学 plan→apply→改配置→读 state→destroy。Change 课强调 Terraform 计算“达到目标状态所需的更改”；生产建议版本控制配置并使用远端 state。`terraform.tfstate`/provider 数据不是应用数据备份；state 含资源属性，应保护。 |
| [Terraform AWS getting started](https://developer.hashicorp.com/terraform/tutorials/aws-get-started) | 查看 AWS create/manage/destroy 教程顺序、EC2/VPC/security group、credentials 环境变量、模块和销毁步骤；AWS create 页明确提示 Free Tier 资格资源也可能收费 | `selected_sections_read` | 只作可选云商实例，不当作免费必修。Apply 前读完整 plan，完成练习后 destroy 并在账单页核实资源；没有具体账号、区域、实例规格、时长和流量时不能给可靠价格。 |
| [阿里云 CNCF x Alibaba 云原生技术公开课](https://developer.aliyun.com/learning/roadmap/cloudnative) | 核查公开路线页和模块目录：云原生概念、容器/镜像/卷、K8s 核心对象/Service、Pod pattern、Label/Selector/controller、Deployment 扩缩与回滚、Job/CronJob/DaemonSet、ConfigMap/安全上下文/资源/Secret、PV/PVC、snapshot/topology、探针/日志/调试、监控日志、网络/CNI/NetworkPolicy、Service；尝试逐节打开课程 | `toc_checked`（目录已核；逐课正文无法核） | 路线页宣称免费且免注册，但本次打开具体课时均跳转登录；依委托要求标为 `free_login_required`。只作中文补充/词汇参考，不列 Primary，不宣称已深审或能确认登录后课程仍免费。个别练习标“即将上线”，实际可操作性未确认。 |
| [FastAPI User Guide](https://fastapi.tiangolo.com/tutorial/first-steps/) 与 [SQLModel Tutorial](https://sqlmodel.tiangolo.com/tutorial/fastapi/) | 查看 FastAPI First Steps、Path Parameters、Request Body、Response Model、Handling Errors、Testing、Settings 页面目录与代表性正文/示例；查看 SQLModel 建表/Engine 正文及 CRUD、FastAPI 组合章节顺序 | `selected_sections_read` | 供无 API 用户在云路线入口快速产出 Task Service；会 API 的用户应诊断跳过。FastAPI 示例能教参数/请求响应与测试；SQLModel 教程用 SQLite 建表/CRUD，不能替代 SQL 原理、生产 migration 或完整后台架构。 |
| [Docker Getting Started Todo App](https://github.com/docker/getting-started-todo-app) | 查看 README、架构说明和 compose 启动/清理入口；README 称 React 前端 + Node 后端，开发时前后端为不同服务，并含 Dockerfile、Compose、测试和 GitHub Actions | `selected_sections_read` | 可作为规模可控的 Compose/镜像/CI 参考项目卡，不作为云部署教程。未本地运行或逐文件审阅；仓库 issue 中出现过启动兼容性问题，学习时须以当前代码与 issue 为准，不能保证所有平台一条命令成功。 |

### 章节映射与重复处理

| 已有基础 / 前课 | 云路线再次出现时 | 处理方式 |
|---|---|---|
| HTTP 请求/响应、端口、DNS、环境变量 | Docker publish、Compose network、云安全组、K8s Service | `REVIEW → COMPARE → DEEPEN`：先复述监听地址/目标端口，再区分容器端口、主机映射、集群服务和云入口。`localhost` 在宿主机、容器、Pod 内指向不同网络命名空间。 |
| API handler、SQL CRUD、配置、pytest、异常、日志 | 容器化与云部署 | `REVIEW`：不重教 Web/SQL；验证同一测试和健康端点在本地、容器、部署环境中行为一致。 |
| Docker Image、Dockerfile、Container、Registry | K8s | `REVIEW` 镜像/OCI 与运行容器；Kubernetes 调度 Pod 和控制器，容器运行时通常为 containerd/CRI-O，不要求 Docker Engine。 |
| Compose 服务发现、网络、卷、健康检查、depends_on | K8s Service、集群 DNS、PV/PVC、probe、reconciliation | `COMPARE / DEEPEN`：同名 Service 不是同一对象；Compose healthcheck 与 K8s readiness/liveness/startup probe 目的不同；Compose `depends_on` 启动顺序不能替代程序重试和控制器持续调谐。 |
| `/health` 或 smoke test | readiness/liveness/startup | `DEEPEN`：区分进程活着、可接流量、启动未完成；不要让 liveness 检查短暂数据库故障后反复重启。 |
| 手动部署/运行命令 | GitHub Actions、Terraform | `DEEPEN`：把已经验证的同一构建/部署步骤自动化；CI workflow 是代码交付过程，Terraform 是基础设施状态声明，两者不是替代关系。 |
| 手工 `.env` 与云凭证 | Environment secret / OIDC / provider credentials | `NEW`：云端工作负载身份、CI 身份信任和最小权限；仅在首次自动部署云资源时前置讲解。 |
| 指标、日志、trace 的日常观察 | OTel SDK/Collector/后端 | `REVIEW → DEEPEN`：先解释业务请求，再学习跨进程传播、Collector pipeline、采样、标签基数与故障诊断。 |

### 开源参考项目卡候选

**规模可控参考：Docker Getting Started Todo App**（[仓库](https://github.com/docker/getting-started-todo-app)）。适合学完 Compose 后，一次读项目地图，再选 Dockerfile / Compose / CI 测试三个切片。它的目标是 Docker 体验，前后端 Node/React 栈与 Task Service 不同；迁移容器健康检查、配置边界、CI 验证的 1–2 个模式即可。README 建议 `docker compose up --watch`，实际运行可能受 Docker Desktop、Compose 版本和仓库近期兼容问题影响。本次只读文档与目录入口，未运行，因此不能承诺启动成功。

**大型 cloud-native 参考：OpenTelemetry Demo**（[文档](https://opentelemetry.io/docs/demo/)，[仓库](https://github.com/open-telemetry/opentelemetry-demo)）。按照用户目标生成 3–8 个切片，一次只做一个：

1. **系统地图**：服务角色、HTTP/gRPC 调用、Collector、backends；不逐个读所有语言服务。
2. **一条请求的 trace**：从 web store 触发请求，在 Jaeger 找 span 父子关系与服务边界。
3. **Collector 路由**：看 receiver→processor→exporter；用 debug exporter 或数据流仪表盘确认遥测经过 Collector。
4. **故障诊断**：仅启用 recommendation cache fault，观察 latency/error metrics 后定位 trace；区分文档事实和诊断推断。
5. **把模式迁移到 Task Service**：给一个 Python API 加自动 instrumentation，导出至 Collector；暂不移植全套 demo 后端。
6. **测试与部署对照**：读 telemetry sanity tests；只有在掌握 K8s 且本机资源足够时，才比较 Compose 与 Helm chart 的组件映射。

Demo 本地完整约需 6 GB RAM、14 GB 磁盘，minimal 约 3 GB；K8s 部署另外需要集群内存。先确认机器余量再运行。源码规模很大，不得要求初学者整体通读。

真实项目学习卡应继续遵守：`repo_url`、`why_now`、`prerequisites`、`known_knowledge`、`study_mode`、`learning_focus`、`desired_depth`、`important_questions`、`avoid_scope`、`expected_outputs`、`migration_candidates`；外部 Coding Agent 需先检查当前仓库结构、动态定位实现、区分事实/解释/推断，小项目先画整体地图，大项目按 3–8 切片且一次只学一个，最终迁移 1–2 项，不锁 commit 或路径。

## 费用与无法核实的边界

- Docker、Kubernetes Basics、Terraform Docker 本地练习的资料免费；本地耗费磁盘、RAM、CPU 和镜像下载流量。OTel Demo 完整栈有明显本机资源门槛。
- GitHub Actions 的费用取决于仓库公开/私有、计划、runner 类型、分钟数、artifact/cache 存储量和当期配额。官方账单说明标准 hosted runner 在公开仓库的费用政策与私有仓库不同，实际额度需登录当前账户的 Billing 页面检查。本报告不写可能过时的美元数。
- 第一次云部署可能涉及 VM/容器计算、托管 DB、负载均衡/NAT、公网 IPv4、块存储/快照、镜像仓库、日志指标留存和出站流量；Free Tier 资格也不能视为账单必为零。未选择厂商、区域、规格、运行时长、流量和保留周期之前，任何具体总价都是假精确。学习计划应给“先预算/告警、按小时部署、结束后销毁、回到账单核对”的退出步骤。
- 阿里云路线页的免费说明与课程具体页的登录墙同时记录；内容访问以 `free_login_required` 保守标注。未登录验证课程视频、作业或账号地区限制。
- 本次没有创建云账号、运行付费服务、登录厂商课程或在本机实跑参考仓库；涉及执行、资源现状、当前 SKU 费率的结论均不作保证。

章节级模板见 [CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md](CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md)。本方向资源对象会整合进 `RESOURCE_CATALOG_NORMALIZED_DRAFT.json`，逐页证据会整合进 `RESEARCH_LOG.md`。
