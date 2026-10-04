# StudyPlan 正式运行收口与唯一正式操作授权包（2026-10-05）

P1/P2/P3 技术准备已完成，P4 授权包已准备并 STOP。技术 PASS 不表示本人接受，也不表示正式操作已获批准。

后续本人普通生成已执行到已知JSON失败并STOP；当前累计160/200、剩40，没有完整Draft/Plan。本文125/200是技术准备时点，最新结果见 [本人RC生成记录](rc-user-plan-2026-10-05.md) 与唯一progress，不能据本文旧时点再次自动派发。

## 用户现在新增能做什么

可以通过 `http://127.0.0.1:5194/` 登录本轮最新原库恢复副本，读取本人旧项目/历史，使用已有学习页面。副本有 AI4、Agent8、Cloud4 当前课程和3条已确认合成技术路线。普通规划提交接口保持，Worker 当前停止，不自动收费生成；本人真实目标、一次计量生成及体验接受仍需本人参与。

## 执行边界

- 顺序 P1 → P2 → P3 → P4，活动 Goal 为 `docs/implementation/STUDYPLAN_RC_RUNTIME_CLOSURE_GOAL_2026-10-05.md`。
- 原库只读 native backup；所有迁移、导入、合成确认和应用写入仅在新 owned 副本。
- 原库写入、正式入口、正式 Worker、部署、push/merge、全局配置、历史 failed/unknown 重派未执行。
- 既有 Agent8、canonical、来源资格、教学结构、practice、旧 Run/Draft/Plan/账本不改。

## P1 合同与普通 Worker

状态：PASS。实现提交 `954242a6e783cf5645cf477f6a11610081b57055`。

已保存两项 RED FAIL：普通 factory 不接受 manifest；allowlist planning claim 会重新领取 unresolved attempt。最小变更：从独立冻结 submission 传 manifest，factory 校验 hash/model_ref 后深拷贝；ledger 检查实际 purpose 输出 cap、attempt purpose、全 Run repair2；modern 新 dispatch 缺 manifest 拒绝，retained legacy 兼容；allowlist 与已有 trusted_server 一样排除 dispatched/reconciliation_required。

| 门禁 | 状态 | 实际证明 |
|---|---|---|
| 1 request manifest绑定 | PASS | 普通factory/实际Worker ledger对照独立PG submission |
| 2 output manifest绑定 | PASS | purpose/key一致性及实际max_tokens合法上界 |
| 3 第N次允许 | PASS | 已持久化N−1后仅登记最后合法请求一次 |
| 4 N+1拒绝 | PASS | 新runtime读取计量，provider不增加 |
| 5 output overflow拒绝 | PASS | 请求数未到限而输出预留超限，provider0 |
| 6 repair2 | PASS | 跨batch第三次拒绝，runtime重建后有效 |
| 7 unknown不claim/重派 | PASS | allowlist/trusted_server、expired lease/dispatched/unknown |
| 8 failed不自动生成 | PASS | terminal failed不claim |
| 9 retained known replay | PASS | 新lease/runtime读PG结果，无额外派发/收费 |
| 10 lease/fence/cancel | PASS | 替换/失效租约、终态、取消锁及迟到结果 |
| 11 admission | PASS | 未授权actor/foreign scope拒绝，RLS/单Worker锁 |
| 12 普通authorized Worker | PASS | Worker/PlanService/factory/ledger/真实PostgresSaver→非空Draft，19次Fake |
| 13 restart预算保持 | PASS | 对真实PG重建runtime/ledger，request/repair/replay保持 |

组合unit/contract与owned PG27 PASS、受影响fence/budget33 PASS、个人模型真实adapter/MockTransport1 PASS，共61 PASS；另deployment binding3 PASS。证据 `var/rc-runtime-20261005/review/p1-gate.json`，SHA256 `d0ed7c3486f5b0efc73615bc347525c64f2807cb4dd76d75cdf55f729148df0d`。

个人模型测试只修旧MockTransport wire/source fixture，生产来源资格未放宽。旧RED/fixture/诊断FAIL保留。restart是runtime/ledger重建，OS kill/restart本批NOT RUN；Fake/MockTransport不证明真实provider网络。旧大套和无输入变化UI build本批NOT RUN，复用前批有效证据。

## P2 原库 native restore 与 forward/import

状态：PASS。

今日源库0023，61表/1517行：13用户、18项目、12 Plan、16 Draft、26 Run，已发布仅Agent1/Python1。源PG16.4/native pg_dump16.15兼容PASS。repeatable-read exported snapshot/custom dump，源连接READ ONLY。

- 备份 `D:/studyplan/var/rc-runtime-20261005/p2/private/source-20261005.dump`，485041 bytes；SHA256 `a321631380f9dd1af32fbad0a09d3e77f4d9e68dcf80a25514e45aaa91d0a88d`。含私人数据，限制本机ACL，不上传。
- 新业务库 `studyplan_test_rc_p2_native_f482d3a3`；checkpoint `studyplan_test_rc_p2_checkpoint_123aace8`。
- **迁移前** native restore与源精确相等：全表行hash、columns/indexes/sequences、ACL/RLS/policies/schema ACL及6关键函数owner/security/定义。
- 仅已有0024 forward。旧列私人业务/catalog行保持；新counter function非SECURITY DEFINER，旧6函数保持。
- 原库没有Agent7，副本先按原不可变文件添加7，再添加8；1/Python1仍在，7/8共存。CURRENT导入AI4/Agent8/Cloud4/Python2及agent.knowledge_rag/coding/workflow_automation各v1。MCP10.1 source/version2正确；重复导入幂等、异体冲突拒绝/rollback/无半发布PASS。
- AI4 seed digest `577d114e8a35fd80fffaba39ed5469a40c0800990b967a5175f27d7c64b9216f`；Agent8 `8bdd3f561a9743cde70b98869b514256ace20ec3398c6ff78169bb30f3094a41`；Cloud4 `a055a82da15b32d019f602943d15182f72c03f03fab4a2668059eb20f9d4e39f`。完整file hash/dependency digest见p2/prepared.json。

| 路线 | 当前包/阶段 | Fake calls | 普通auth、owned PG/checkpoint、Draft/确认/Plan/workspace、fresh login |
|---|---|---:|---|
| Agent＋RAG课程 | Agent8/18 | 37 | PASS |
| 用户电商项目AI | AI4/8 | 17 | PASS |
| 用户Node.js API Cloud | Cloud4/11 | 23 | PASS |

未授权allowlist403、app-role无scope不可读/本人scope可读、终态再次tick不派发PASS。仅确认3个新owned synthetic Draft，没有确认旧F2或前批paid Draft。

消费后副本63表/2922行，新增3个合成用户/项目/Plan；每个旧私人业务/catalog行保持。副本1个旧auth throttle临时行按正常认证策略过期，源全快照不变；不是导入覆盖。源最终仍0023/61表/1517行，原库写入0/全局角色修改0。

证据p2/restore-exact.json、copy-import-result.json、consumer-result.json、final-readback.json。harness原FAIL为UTC格式及JSON tuple/list比较，修脚本后从既有副本续接，未重复dump/restore/migration，原FAIL保留。

## P3 本人 RC 技术入口

状态：PASS（技术准备）；本人实际接受NOT RUN。

仅latest restored owned RC；实际UI `http://127.0.0.1:5194/`，API `http://127.0.0.1:8034/healthz`。启动前端口无listener，健康均HTTP200。API PID34332/parent40660/session52961；UI PID36476/parent45904/session73794；两进程实际Windows账号 `天策\22088`，完整命令见p3/owned-processes.json。服务保留供本人进入，Worker held。

真实Edge/HTTP/PG三场景PASS：exact Plan/workspace/catalog，全guidance，A2实际3单元/1canonical/1task，A5/A6/A8与small/specialty/mature/transfer，A6 V2/10.1非fallback，GR2候选卡、完整Prompt，Node连续项目，刷新/退出重登内容保持。原AI FAIL为DOM空白规范化；保存attempt1证据，只改新harness比较，继续AI/Cloud，Agent不重复，生产/内容不改。p3/execution-report.json与edge/checks.json记录最终PASS；所有外部/provider/生成/Worker dispatch0。

正常产品API/runtime/admission/currentpacks和正式本机settings复用，仅ownedDSN/localhost端口/origin及禁用旧本地直通身份；技术进程阻止provider/search/RAG与Worker派发。runtime输出8192，purpose4096/8192/4096/8192；model ceiling0代表未指定，不是输出cap0。实际trusted_server，0 allowlist actors正常。

本人用副本正常账号，凭据本人私下输入；目标和提交不由synthetic替代。当前Worker held，正常提交后不会自动生成。本人新Run标识确定后，再核对实际frozen manifest、既有累计账本、free binding/DNS/TLS，并只对该新owned Run启用计量临时Worker。一个新Acceptance/Run normal≤37、repair≤2、总≤39已获本Goal授权，无需重复收费审批；unknown立即STOP/不重发，不为证据开第二本人Plan。目前真实用户生成NOT RUN。

本人需要体验：正常登录→真实目标→提交/进度→非空Draft→阶段/单元/知识→免费章节→完整guidance→Framework/MCP/Project Study→Prompt→总结→实践成果→一次既有受控变更→旧历史→刷新→退出/重登，再亲自判断是否接受。自动Edge不能代替。

## 用量与复用

累计125/200，剩75；本批新增真实模型0。日常 ledger 的预算是独立冻结的单 Run request/output 上界；它不等于验收 wrapper 的累计授权账本。持续正式 Worker 的费用操作边界必须在最终批准中明确，不能将单 Run PASS 描述为无限新 Run 调用授权。

上一批 A6/46 slots/74 refs、Agent8、38原响应 replay、学习闭环/GR/Prompt/总结/成果/完成/变更/历史以及37请求收费代表证据有效，未无输入变化重复大套/重复收费。

## RAG 与 OAuth

F17 BLOCKED：StudyPlan 未配置 RAG endpoint/credential；实际本机 Personal RAG frontend/DB 所属 `E:/RAG quention/deploy/compose.yml`，未观察到其 API container，静态 OpenAPI 没有 pure retrieve/auth security contract。没有检索、embedding、RAG修改。8085 listener属于GitHub MCP，不是RAG。

GitHub OAuth真实登录NOT RUN；当前配置/路由未见完整实现，普通用户名密码PASS不能代表OAuth PASS。两条支线不阻断P1/P2/P3。root/预算安全复核请求Sol6.1/xhigh，有界P2/P3 Sol6.1/medium，实际解析均NOT OBSERVABLE；不改全局配置。

## P4 唯一待批准的精确正式操作 — STOP

以下正式动作本批全部NOT RUN。先本人RC接受，再一次明确批准需要的正式操作；不逐项追加普通开发授权询问。

### Git

当前feat/n1-resource-discovery。入场8a28b17，实现954242a；最终文档提交SHA在progress/final-invariants。跟踪origin同名ref为此前核实9fef887，本批没有联网重查。拟同步精确范围 `9fef887af21dd5ff2a60aef306a6b9b02d176f5f..本批最终文档提交`，含c0237d2/859db09/8a28b17/954242a及报告提交。执行前必须只读核对真实远端是否更新。

远端仍9fef时需要push才能同步；当前未授权。需要整合的目标develop/no-ff，分支保留；merge未授权。master/milestone不在默认动作中，仍需里程碑接受。最终受跟踪工作树干净，保护未跟踪目录保留。

### DB及回滚

正式原库0023；backup/hash见P2。正式操作前设停写窗口，核对原库是否仍匹配；若已变化，重新只读备份，不用旧快照覆盖新数据。

预计写入：已有0024给resource_search_requests增加source/context_snapshot/node_id及约束；新增resource_read_usage_counter/resource_inspection_requests、guard/policy/grants。immutable导入写domain_packs/public_resource_sources/public_resource_sections，先Agent7，再CURRENT各包，精确文件/digest见prepared.json。

使用已有 `app.tools.import_seed --file ...` / `seed_reviewed_pack`，不运行创建演示项目的seed_b3.main。单包事务，相同幂等、异体拒绝/回滚，不覆盖旧版本。导入不修改auth_users、learning_projects、Plan/Draft/Run/attempt/历史、进度、Prompt/summary/submission/outcome、用户模型设置等私人表；迁移仅为既有resource_search_requests增加默认列，不删除历史。

回滚：停止新写入/Worker，保留异常DB与receipt；custom backup恢复到**新DB**，核对行/ACL/RLS/functions后再批准切连接。禁止downgrade/整库覆写/丢弃新历史。切换后新增写入需单独保留评审，备份不是自动回放这些新写入的方案。

### Services / Worker

当前owned入口的命令：

```powershell
# D:\studyplan，managed session52961
$env:STUDYPLAN_P3_P2_GREEN='1'
.venv/Scripts/python.exe var/rc-runtime-20261005/p3/rc_api.py
# D:\studyplan\frontend，managed session73794
$env:STUDYPLAN_API_URL='http://127.0.0.1:8034'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5194 --strictPort
```

停止优先向这两个session发送Ctrl+C；若使用PID停止，先核对34332/36476的listener、命令、Windows用户、parent未变，再仅停止本批PID，禁止按进程名/端口批量杀。停止后验证两端口无本批listener。

正式拟继续localhost8034/5194；先停止owned进程并核对空闲，使用原产品app/checkpoint角色配置，session/encryption/provider/security/caps不变。已有正式命令如下，**待批准，本批未执行**：

```powershell
./scripts/b3f1-dev.ps1 -ApiPort 8034 -FrontendPort 5194
./scripts/b3f1-dev.ps1 -Frontend -ApiPort 8034 -FrontendPort 5194
# 常驻Worker只有明确实际费用/actor/Run范围后才能启动
./scripts/b3f1-dev.ps1 -Worker -ApiPort 8034 -FrontendPort 5194
```

未来正式PID必须启动后记录，当前owned PID不冒充正式PID。当前Worker无PID/未运行；本人单Run临时执行另记录唯一actor/project/Run与session/PID，不让队列其它Run获得额外授权。

正式admission trusted_server：已有窄数据库claim函数与app-role；随后actor/project RLS。worker_id与Windows现有账号为服务身份，不改全局roles。failed终态及dispatched/unknown不领取；lease/claimtoken/fence/cancel由P1证明；request/output由独立submission manifest到ledger，repair2。单Run预算不等于无限常驻费用授权。

健康检查API `/healthz`、UI `/`，再正常auth/projectscope/catalog读取；health200不等于paid/RAG PASS。精确停止本批session/PID，不影响其它服务。

### External / 用户接受 / 一次批准点

现有endpoint `https://api.deepseek.com`，模型/temperature不变，SSRF/私网/endpointguard保留，不固定DNSIP。累计125/200剩75，单个本人新Run最多39，实际manifest/freepreflight后才dispatch；每笔append-only计量，unknownSTOP。不承诺全产品费用已由单Run机制自动封顶200。

F17仍BLOCKED，缺可信已有pure retrieve/auth/scope契约和运行API；不建设第二RAG。OAuth真实验收仍NOT RUN。

**唯一正式批准点**：本人RC接受后，明确是否批准原库forward0024+不可变导入、正式API/UI连接切换、指定Worker费用范围，以及是否批准同名分支push/develop整合。授权前上述正式动作STOP。

| 层级 | 状态 |
|---|---|
| 普通Worker合同 | PASS |
| native恢复/forward/import/owned应用 | PASS |
| 三路线真实Edge技术消费 | PASS |
| 本人新Plan真实生成/主观接受 | NOT RUN |
| 前批唯一synthetic收费代表 | PASS，复用不重跑 |
| RAG检索/OAuth真实验收 | NOT RUN；F17 BLOCKED |
| 正式原库/入口/Worker/push/merge | NOT RUN，待一次批准 |
| 整体产品 | STAGING_BLOCKED / NOT_READY |

整体产品仍 STAGING_BLOCKED / NOT_READY；合同 PASS、非收费教学 PASS、本人接受和正式交付分别报告。
