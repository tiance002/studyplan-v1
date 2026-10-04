# 本人 RC 正常生成：已知 JSON 失败并 STOP（2026-10-05）

## 用户现在新增能做什么

账号 `tiance7` 的实际普通提交已经由单次 owned Worker 执行；可在 RC 页面刷新运行状态查看失败历史。没有生成完整 Draft/Plan，当前不能进入这条新路线学习。API/UI入口保留，Worker已退出。

## 范围与基线

- 产品源码不改；执行基线 `003423da16aabb0feaf119f7f5d0ce3fd8b2104f`，普通Worker修复仍为954242a。
- 复用已通过的P1预算/admission、P2今日native恢复/forward/import、P3三路线真实Edge技术证据，没有重跑大套。
- 本人通过普通UI注册并提交唯一新Run；不是第二个synthetic代表，也没有另发生成POST。
- Run `run_ba6527a948294cf0bbe9aab1ebc8c729`；新Acceptance `rc-user-tiance7-cebbca03153c`。
- owned业务 `studyplan_test_rc_p2_native_f482d3a3`、checkpoint `studyplan_test_rc_p2_checkpoint_123aace8`；实际DSN数据库名精确核对。
- 冻结Agent8、18阶段、manifest hash `7f13c2379b6328f90a1299581cecc87b378571d68a8c3bbc8ee53e44c067236c`，37normal+2repair≤39，output上界241664，repair上限未改。

## 非收费准备

- 实际冻结模型binding、免费公网DNS/TLS PASS，模型调用0。
- 当前单Run计量的原函数AST提取+MockTransport离线8 PASS：成功单请求/receipt、transportunknown停止并禁止再发、local拒绝零派发/零计量、normal37/repair2上界、前序unknown、foreign scope、wire cap错误。
- 初轮6 PASS/1fixture FAIL保留，LLMResult mock缺model/provider参数，仅修fixture。
- 安全/费用/执行范围13项只读复核PASS。复核修正两个新harness问题：实际DSN名验证；最后stage首task按已有冻结GoalSpec添加purpose_requirements，与生产合同精确一致。没有修改生产权威。
- root/安全复核请求Sol6.1/xhigh，实际解析NOT OBSERVABLE；没有修改全局配置。

## 实际执行与首笔门禁

一次精确claim本人project/Run，标准生产factory传manifest，标准Worker._process，不运行polling loop。临时PID56024/session95343，已exit1退出；没有常驻Worker。

首outline PASS：input3671/output1319/finish_reason stop，合法JSON/冻结stage keys/实际PG账本通过后才继续structure。相对v6.5 input209998下降98.25188811%，无length截断。

18个structure全部通过canonical知识核对；15个已成功practice通过reviewed task身份/数量/目标/acceptance/links核对。G6失败，剩余GR/GT practice NOT RUN；不能把已完成33项保护描述为全部生成通过。

## 已知失败与 repair0

第35笔真实请求（累计编号160）是G6 practice：

- HTTP200，finish_reason stop。
- 实报input2581/output1534；原message content4177字符。
- 原内容严格JSON解析FAIL：`Expecting ',' delimiter`，line113/column5/offset3506。
- adapter `provider_invalid_json`，PG该attempt为failed，结果已知；不是transport unknown，不是length截断。

现有 `generate_practice_batch` 在LLMFailure后追加generation_errors，没有存入已解析practice batch；local repair通道处理已解析批次的校验target，因此本次repair0，直接终止。额度允许“最多2”并不表示可以恢复已failed Run去补派。

所有35份provider原body、receipt、checkpoint、failed Run及首次反例保留。没有修补原body追绿、恢复/retry/resubmit、另建第二用户Run、Draft确认或Plan发布。

## 用量与 reconciliation

| 项目 | 实际 |
|---|---:|
| normal | 35 |
| repair | 0 |
| 已知成功 / 已知失败 | 34 / 1 |
| unknown | 0 |
| 本次真实请求 | 35 |
| 累计 | 125 → 160 / 200 |
| 剩余 | 40 |
| provider input / output | 75617 / 32927 |
| token总计 | 108544 |
| Draft / Plan | 0 / 0 |

126–160连续编号、request/result身份、原body hash与PG计量一致，reconciliation PASS；历史125份计量内容及1217保护文件/.env不变。completion以FAIL追加到同一费用账本，不覆盖旧记录。没有金额/货币实报，费用金额NOT OBSERVABLE，不由token数臆测。

## 证据、边界和下一动作

本机证据 `var/rc-user-20261005/`：preflight.json、meter-offline.xml（8 PASS）、meter-offline-first-fail.xml、safety-review.json、outline-gate.json、run-report.json、failure-completion.json、stage-checks、execution-state.json。私人submission/Draft/provider bodies留在限制ACL的private目录，不提交Git。

独立失败分类/费用复核PASS：final-failure-review.json，SHA256 `82448ded17b52f63e95b09d353e237cc26c53bf476bfdd126271250a7c83fd6e`。原160响应7068bytes，SHA256 `ffffffa319a2217bd889dca2f4c9416d21fc37d78903cbf4a090ccb3bf8d901c`，读取前后不变。final-readonly.json确认旧9月30日unknown未变、本人只有1个Run且failed。

用户旧 `tiance` 的9月30日unknown与旧F2/所有历史failed保持，不重派。原库写入、正式入口、正式Worker、RAG/产品搜索、push/merge、全局配置均NOT RUN。

当前结果 **USER_RC_GENERATION_FAIL / STOP**。本人主观接受NOT RUN；整体STAGING_BLOCKED / NOT_READY。源码与此前非收费门禁未退化，但这次本人完整生成没有通过。

下一安全动作：保留这份真实invalid JSON作为离线fixture，评审严格解析拒绝与已知JSON失败的有界repair衔接。需要新的定向实施范围后再修改合同；旧failed Run永不恢复或重派。本批不自动消耗剩余40次，不把未使用的repair预算补发到已终止Run，也不创建第二本人Plan。
