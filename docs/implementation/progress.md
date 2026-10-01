# V2.0实施进度（唯一当前检查点）

日期：2026-10-01。整体 **NOT_READY**；目标仍为F01–F18、G0–G6、Q01–Q12和用户实际验收。G1技术纵向链已实测，继续G2。

## 基线与归属

正式目录D:\studyplan；origin=tiance002/studyplan-v1。起点develop及远端为aa37e4bfa33a41aadb4cb689557e2c7d491d550f；工作分支feat/v2-g1-user-slice。V2入口本地提交54c7d3e48c2e3fae1d8f099cb11a01f3a9017119；G1代码提交be802e27dfa131ee232d07d40d9650dbd9d5ac21，待推送。本轮G1改动已归档，模型冻结边界独立只读review无可证实P0/P1/P2；未提交文件属于检查点文档及下一批G2。既有.workbuddy/和design-preview/禁止操作/提交。

原后端8000、PG5432、Ollama11434未重启。原业务库迁移0010，13账号/18项目/26Run，盘点只读；旧waiting_user、unknown、Acceptance09及live journal未处理。原文哈希保持：指导7531B8DA74B043D169E8AE6DFEB1BB738747A0BE936E15B1934C53416D974F35，Goal D4DBCF0FD8F72CDE53385C307F1CCED02F81DC9D7E4449A1A17C4731A350E13B。文件专属whitespace规则保留CRLF及Markdown双空格，不改原文。

## 路由与外部条件

root实际turn_context为gpt-6.1-sol/high；认证/Seed请求SolMedium，短生成请求SolHigh。工具接受派发但实际解析值 **NOT OBSERVABLE**，不把请求参数当运行证明；未改全局配置。

用户授权累计模型50请求、Tavily1000请求：**模型20/50，搜索1/1000（1credit）**，下一切片不重置。20模型请求均有结果、unknown0。Tavily三项配置已存在，HTTP200预检PASS，与用户官网观察一致；产品搜索适配器/API/页面仍待G2。RAG地址/契约/凭证缺失，只阻塞其实际调用；公网部署未授权。GitHub浏览器授权需求已记录，尚未注册App或安装MCP。见[外部服务](external-services.md)。

模型沿用DeepSeek Flash/cap8000，专用验收structure/repair目标8000，不提升cap、不改私有.env。免费预检先因缺dotenv和预算不一致FAIL；复用加载语义、限制目标后PASS。派发前append-only计量：.git/v2-paid-quota-20261001/request-01..20.json及result；搜索.git/v2-search-quota-20261001/request-0001.json及result。未知结果阻断继续，禁止修改记录或重跑同AcceptanceId。

## G1已实测事实

用户可注册/登录、使用DB发布的Agent v2 Seed提交202任务，真实模型生成9阶段草案后计算结束，编辑保存、业务发布再重登录读回。完整项目管理、三Blueprint和学习闭环仍未完成。见[G1报告](../acceptance/G1-v2-user-slice-2026-10-01.md)。

- 新密码15–128 Unicode码点及旧密码兼容；真实隔离PG认证7项PASS。部署模型冻结/轮换拒绝3单元PASS。
- Seed预SQL校验、0011完整payload发布/DB只读目录、重复幂等/异体回滚：16规则+PG PASS，bootstrap选择1 PASS。保留v1章节原文，新增v2修正，不冒充新内容审核。
- 0012窄原子worker领取，保留scope/RLS/unknown排除；锁后时间/token/owner检查，新旧job47实际PG PASS。
- short-v2保存草案后END，succeeded+none/result_ref稳定；确认不resume旧Graph。同事务catalog/draft/Run fence、锁后expiry、基础版本、并发发布、崩溃复用已存草案定向实测。较宽命令FAIL：112通过/1旧异常类型失败；修复后原失败及相关4项PASS，不冒称全组合重跑。
- 父级真实PG业务纵向1 PASS（provider明确Fake）；最终离线unit+contract 453 PASS/2 skipped（NOT RUN），exit0；Ruff/diff/OpenAPI PASS。
- frontend 4单元及build PASS；auth/progress/short-generation mock浏览器PASS，覆盖终态停止轮询、opaque ID和刷新/409保留编辑。
- 真实AcceptanceId v2-g1-20261001-01，Project lpr_3b0829d7c2ce490798db5b300ae87d0a，Run run_5abb9605a32b40e3ba243fe2cda8e279：20云模型请求含1repair，27/27必需节点、9阶段、succeeded。
- Chrome+真实HTTP+PG编辑/保存/发布revision1/退出重登录PASS，模型仍20。第一次FAIL在已发布后的退出按钮accessible name，补aria-label；第二次FAIL为测试提前断言，改等实际草案标题，从保留发布结果续测PASS，无再生成/付费。只批准新隔离测试账号自己的草案，负责人体验NOT RUN。

## 服务、证据与下一步

本轮保留专用库studyplan_test_v2g1real_2f6ac462及checkpoint库studyplan_test_v2g1cp_e6270f82，无额外worker运行。工具会话96940后端8021/PID27364，45314前端5175/PID41308，24837前端5174为mock测试。续接先确认监听/归属，只操作本轮进程，不承诺跨会话后台持续。

忽略目录var/v2-g1包含三代理report、短生成日志、真实report/browser JSON、published PNG、Tavily预检。*-browser-private.json有测试账号秘密，禁止打印/提交。保留收费证据和专用库，复用未失效检查。

下一条安全动作：正常提交G1代码与验收检查点，按已有授权推送feature分支，不宣称master里程碑接受。G2先实现真实Tavily未核验候选、原子私有资源选取、单元绑定，再补Exposure/进度、局部偏好/六角色及GitHub连接。RAG缺契约仅暂停对应真实调用。每批固定契约/归属，不重复G0审计。
