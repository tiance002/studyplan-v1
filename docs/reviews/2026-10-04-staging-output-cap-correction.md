# 正式 staging 输出上限修正与绑定验证

用户现在新增能做什么：下一次获批启动正式 staging 时，从正式启动链读取8192上限；structure/repair不再因部署cap8000而预算冲突。当前没有切入口、启动Worker或调用真实模型。

结果：配置修正 **PASS**；隔离预算/绑定 **PASS**；实际端点完整绑定 **FAIL**（DNS非公网）。当前 **STAGING_BLOCKED / NOT_READY**，本授权结束后停止。

## 授权与唯一事实源

用户明确批准仅将正式staging模型输出上限8000→8192及必要只读/隔离验证，禁止其它参数、原产品migration/Seed、正式入口切换、正式Worker、收费、RAG、master/develop合并和推送。

唯一持久配置源为 `D:\studyplan\.env` 的单一 `LLM_MAX_OUTPUT_TOKENS` 行。正式链 `scripts/b3f1-dev.ps1` 按脚本目录的父目录定位该文件，API/Worker共享同一加载语句；无Demo开关。`app.core.config.get_settings()`只读取进程环境并缓存，不自行读取另一份dotenv。源码默认8192和.env.example均未修改；历史受控验收wrapper的replace设置不是正式源，copy_server也不是正式启动器。

进入HEAD `3f302346da02829a10480163a6096cf9aa254c84`，feat/n1-resource-discovery；tracked clean，两禁目录未操作。正式API/Worker未启动；已有只读副本8024/5179仍为同一进程。改动是原.env中相同字节长度的一个数值：8000→8192，换行/引号/其它行保留；其它行SHA256前后相同。未复制含秘密的整份.env，未修改provider/model/temperature/逐purpose预算/额度/计量策略。

## Runtime与门禁

隔离新PowerShell进程通过AST从实际正式脚本提取并执行原样环境加载语句，只执行该语句，不执行启动分支。随后工程.venv新Python进程读取真实get_settings、build_llm和PersonalPlanningRuntimeFactory；禁止socket连接、HTTP send、psycopg连接，允许公开端点DNS查询。没有用Settings replace构造8192候选冒充生效值。该证据是启动链配置消费验证，**不是已运行正式API/Worker更新**。

| 验证 | 状态 | 实际值/边界 |
|---|---|---|
| 修改前runtime | PASS | cap8000；structure/repair budget原始FAIL均重现 |
| 修改后runtime | PASS | cap8192；其它Settings摘要前后一致 |
| structure budget / 隔离binding | PASS | target8192，provider request_options.max_tokens8192 |
| repair budget / 隔离binding | PASS | target8192，provider request_options.max_tokens8192 |
| outline/practice未改变 | PASS | 各4096 |
| 单请求预算 | PASS | 四purpose均≤deployment8192且≤现有模型cap；没有clamp或扩大purpose目标 |
| 累计Run预算 | PASS | 6阶段合成manifest仍max15请求、94208输出、repair最多2；第16请求或94209输出拒绝 |
| 真实endpoint deployment binding | FAIL | api.deepseek.com当前DNS含非公网地址；现有ModelEndpointPolicy拒绝，未绕过/修改代理 |
| 隔离完整预算binding | PASS | 相同Settings、实际bind_submission；仅DNS为明确synthetic公网fixture，与上一行真实结果分开 |
| 原库/归档保全最终只读 | PASS | 原库snapshot、backup SHA、原函数owner/security/ACL/definition保持 |

完整实际binding在DNS边界停止；不能将预算PASS写成真实服务绑定全部PASS。部署绑定指纹包含预算；已有冻结Run仍受原引用校验，不恢复/重派unknown或旧Acceptance。

## 50次额度及计量

`.git/v2-paid-quota-20261001`实际23个请求记录，记录limit均50；全部request/result文件哈希前后相同，未追加/覆盖/重置。该账本未决0与历史另行记录unknown1不是同一统计范围；历史unknown未恢复。

仅提取现有 `var/v2-g1/real_acceptance.py` 的exclusive_json/reserve_request函数AST，不导入会创建库/启动服务的验收脚本，在新临时目录执行合成边界：第50允许、第51拒绝且不写request51、failed仍计量、unknown/缺失回执阻止后续请求，全部PASS。临时目录已清理，live账本不变，收费0。

**范围限制：现有50次总额度是受控收费验收的追加账本保护，不是普通API自动全局计数器。** 本次保持该门禁并测试其边界，不新增计量系统。正式Worker保持STOP；任何后续收费启动需重新确认相同全局账本/额度封装进入dispatch路径。此次不能声明普通API全局50保护已集成或被真实收费验证。

## 最小相关回归

| 范围 | 状态 | 结果 |
|---|---|---|
| 预算/模型冻结/实际HTTP Mock输出参数/repair上限/付费默认拒绝等 | PASS65 / NOT RUN2 | 原测试67项；2项目录symlink缺提升权限，不请求提升 |
| 原run_budget_pg | PASS3 / FAIL2 | 旧fixture固定stage.tools及21请求，当前注册表为新阶段；原FAIL保留 |
| 当前manifest隔离PG预算/replay/unknown/tamper检查 | PASS5 | 原测试复制到ignored var，只将target stage和预算数改为实际manifest取值；原测试/业务代码未改 |
| 真实服务收费/正式API、Worker启动/浏览器写流程 | NOT RUN | 授权范围禁止；本次没有UI或业务改动，不跑无关宽套件 |

PG写入只在现有harness新建的studyplan_test_*临时库中，fixture正常drop；无原库migration/Seed。CountingProvider为本地Fake计数，不是收费HTTP。backend/scripts/.env.example diff为空，生产源码和原测试未修改。

## 本机证据

所有操作证据在ignored `var/v63`，不提交.env/凭据/私人正文。

| artifact | SHA256 |
|---|---|
| staging-cap-change.json | 37cc163847310e92023aeb9f5c57e06fce9eb4ddc503d9d8f917ad11f29ececb |
| staging-runtime-before.json | d2285ac092776aaffb1463e04b9eba273baec8d176a766012a325b90c80d779a |
| staging-runtime-after.json | 6849573b08313350e6cffbb8dacccacf9c6ab779d45b418d232195b03f0d0659 |
| staging-quota-isolation.json | d936bcabd9677a5d1c8fb5124cee66f00a6e859c8b3900209c0049204a352af8 |
| staging-cap-unit.xml | bf5b70ab2ba9785fb49551c62f76d5682773f2ba4912a26dabb9015d7671db9f |
| staging-cap-pg.xml | a02a49cfb140c5ea491e2bafafedb8fc6815401e0feda68be9f40892985f3496 |
| staging-cap-pg-current.xml | 3ade300c82864dd71a4e2880f6152ac976626d0d837c800c3b983b0eea53002e |

本次不派代理；开发请求主协调Sol6.1/high，实际model/effort解析NOT OBSERVABLE。收费与外部HTTP新增0；无全局配置、服务模式切换、RAG操作或推送。

## Rollback与STOP

原值8000已保存在staging-cap-change.json。需要回滚时在D:\studyplan执行：

```powershell
.\.venv\Scripts\python.exe .\var\v63\staging-cap-change.py rollback
```

脚本只允许8192→8000，先校验唯一key及所有非目标行哈希，发现后来其它.env修改则拒绝覆盖；不会还原整份秘密文件或重写其它参数。回滚会重新触发原structure/repair预算冲突。未运行回滚、未重启正式进程。

没有变为STAGING_READY。已解除cap8000阻塞，但仍存在：实际provider DNS非公网导致真实端点绑定FAIL；非空原账号历史消费缺样本；RAG实例/纯检索/身份scope/citation/error-timeout契约未定；真实模型代表验证及完整用户接受未执行。正式原库升级、入口、Worker、费用仍有独立授权门禁。

本次配置修正及必要验证结束，停止在当前门禁，不自动开展下一项。
