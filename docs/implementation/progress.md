# V2.0实施进度（唯一当前检查点）

日期：2026-10-01。Goal：F01–F18完整产品、G0–G6连续切片、Q01–Q12与用户实际验收。整体NOT_READY，不以本轮可完成的小范围重新定义终点。

## 当前基线与服务

- 正式目录D:\studyplan；origin为tiance002/studyplan-v1；起点develop `aa37e4bfa33a41aadb4cb689557e2c7d491d550f`，与origin/develop对齐；工作分支feat/v2-g1-user-slice。
- 起点已跟踪文件无dirty；只有既有.workbuddy/与design-preview/未跟踪，禁止操作。已有M1.1无登录分支不覆盖或集成。
- 服务监听：127.0.0.1:8000后端、127.0.0.1/::1:5432 PG、11434 Ollama。未发现5173前端监听。不终止/重启用户现有服务。
- 实际业务库迁移0010；13账号、18项目、2领域包、16草案、12正式版本、26Run、9job。1条waiting_user有有效草案，1条reconciliation_required。只读盘点，不批准/恢复/重派/删除历史。
- 锁/环境：frontend/package-lock.json，pyproject.toml；Python3.13.14、Node24.18.0、npm11.16.0。迁移命令应从backend工作目录运行。已有pg_harness共享实例安全preflight PASS，无需创建/改全局角色。

## 路由与外部条件

- 当前root会话turn_context记录实际model=`gpt-6.1-sol`、effort=`high`；global config默认medium不是当前实际路由证据。未修改全局配置。
- g1_credentials与g1_seed派发显式model/effort=`gpt-6.1-sol/medium`；g1_short_generation=`gpt-6.1-sol/high`。工具接受派发，但返回未提供实际解析值；不把请求参数当运行解析证明。未使用Sol xhigh/max。
- .env存在业务/迁移/checkpoint DSN、模型endpoint/key/id、加密key；只记录存在性，不打印秘密。配置provider=openai_compatible；有凭证不表示本轮真调用授权/成功。
- 用户最新授权：已配置模型累计最多50次请求，Tavily搜索累计最多1000次；当前实际模型0/50，搜索0/1000。不得把次数额度重置到下一切片。RAG地址/凭证、Tavily密钥仍缺；公网部署目标/权限尚未授权。配置见external-services.md。
- 免费provider preflight PASS：api.deepseek.com / deepseek-flash，DNS和冻结预算校验；现有部署cap8000，专用验收将structure/repair目标限定8000而不提升cap，不修改私有.env。首次预检因缺dotenv包FAIL（不安装，复用现有加载语义），第二次因8192目标超过8000 FAIL，限定目标后PASS。没有发请求。

## G0与G1

G0已执行一次差异核查，保存两份原文与哈希、ADR0010、功能矩阵及AGENTS简短入口。原文SHA256：指导 `7531B8DA74B043D169E8AE6DFEB1BB738747A0BE936E15B1934C53416D974F35`；Goal `D4DBCF0FD8F72CDE53385C307F1CCED02F81DC9D7E4449A1A17C4731A350E13B`。

G1 Goal：注册/登录→真实可导入Seed→目标→持久202任务→真模型生成→草案编辑→业务事务确认→PG版本→刷新/重登录回读。Allowed：现有backend/frontend/contracts/scripts/测试/Seed；Non-goals：重搭、旧库迁移、平台MCP/沙箱、多Agent系统、付费未知重试。Tests：规则→真实PG→外部→浏览器；Evidence按命令/exit/基线记录；Rollback采用可逆代码提交与新迁移，不默认downgrade。

当前实现分工：

- Medium认证：新注册15–128码点、旧短密码登录兼容、独立DTO/UI。预期RED：FAIL exit1；GREEN：51单元/领域测试PASS exit0；4真实隔离PG认证测试PASS exit0（128emoji、旧6字符hash、归属/Origin/CSRF/限流/脱敏保留）。报告var/v2-g1/credentials-report.md；浏览器尚NOT RUN。
- Medium Seed：0011新增完整发布payload、预SQL校验、幂等/冲突事务导入、真实DB目录读取。v1 capstone章节[9,8]违反原顺序，保留v1新增v2修正，不削弱校验、不假称重新网页审核。16 focused unit+PG PASS，bootstrap定向1 PASS；报告var/v2-g1/seed-report.md。
- High短生成：新b3f2-short-v2图在草案持久化后END；计算succeeded+none/draft result_ref；legacy确认业务事务不resume旧Graph。补取消/编辑事务内hash/version检查与发布版本锁。报告待回。
- Medium新用户worker：0012 narrow SECURITY DEFINER claim_next，固定search_path/迁移owner/PUBLIC revoke，scope-less普通RLS仍拒；trusted_server单project活动任务锁/五字段claim/token，新用户无需名单。39真实PG PASS。独立review找到锁等待后lease时间重检查缺口，正在修正并添加锁等待RED/GREEN；报告var/v2-g1/worker-admission-report.md。
- 主协调：OpenAPI/typedclient重新生成，9契约PASS。status_url已包含project_id；DB Seed组合根已接入；新部署模型冻结binding及配置轮换拒绝3单元PASS（RED2 FAIL）。新用户真实PG纵向链1 PASS：注册→无名单202→status_url直接200→活动第二提交409→Fake生成短终态→编辑/重复确认→新应用重登录回读及跨账号403。此PG测试不证明真实模型成功。
- 浏览器mock层：short-generation RED（旧终态不载草案）→PASS，涵盖opaque result_ref、终态停止轮询、刷新/409保留输入、主动reload恢复。auth Unicode128/129边界与错误处理PASS；progress轮询/去重业务投影PASS。仅本轮独立5174开发进程，无重启用户8000；真实HTTP+PG浏览器仍NOT RUN。frontend 4单元PASS、build PASS。
- 测试rollout：按D11更新新Run成功语义/固定draftref/不resume Graph；真实PG+Graph14 PASS，取消历史legacy定向5 PASS；保留真实失败阶段断言，High修复后该测试+owned83 PASS。Broad offline448 PASS/2 skipped(NOT RUN)/1旧契约FAIL，重新导出后契约9 PASS；最终业务fencing输入已变化，需定向新验证。

## 下一条安全动作

High修完同事务catalog materialization fence、锁后clock_timestamp与save-node checkpoint gap幂等恢复；Medium修job锁后时间检查并验证。随后用新AcceptanceId和专用隔离Project执行已授权真模型（累计50上限），再做真实PG浏览器回读。不恢复旧live状态。尚无本V2提交；当前headaa37e4b及同名远端分支已推送，G1未提交归属按代理报告/本条记录。

## 本轮问题与证据限制

早期批量读取输出过长，改为聚焦文件；首次alembic在根目录执行因相对script_location失败，改backend工作目录后head可读。首次audit相对.venv在backend工作目录无法解析，改绝对路径后PASS。所有错误为离线路径问题，未安装/重搭或修改用户服务。

上一目标回合完成远端推送，是已有授权动作的progress；本V2.0从实际HEAD开始，未复用旧测试数作新验收。缺凭证/额度是局部BLOCKED，整个Goal保持active。每次续接读取本文件与实际status，复用未失效证据，不重新全仓探索。
