# G2学习记录与局部偏好验收

2026-10-01，完整V2仍NOT_READY。本批在已有项目/计划/单元/知识/资源上增加出现位置学习记录和偏好设置；不重建项目，不把自述完成、跳过或选用资料当知识掌握核验。

## Goal / Constraints / Allowed changes / Non-goals

Goal：project/plan/stage/unit出现位置独立四态进度，跳过、返回、不可变操作与来源快照历史；project/unit/node整组偏好、优先级、恢复继承与CAS。工作区和新生成/搜索接入实际设置。

Allowed changes：0014 Exposure与历史事件、0015 preferences.deleted_at增量迁移；领域/Port/服务/PG/API/容器/组合根、契约、现有工作区中的两个面板及针对测试。根协调和两名后端代理、随后根协调和一名前端代理，最多两名业务写入者。请求路由遵循V2入口；代理实际解析仍NOT OBSERVABLE。

Constraints：服务端会话scope与active owner/RLS；current写入先共享plan-decision advisory，后owner行，再重读approved与成员归属。历史版本GET与同键原成功receipt可回读；新键旧版本禁止写入。来源快照只说明当时安排的公开资料/私有选择，不代表阅读证据。每次操作保留知识内容版本、稳定键、pack引用与当时来源，事件不可更新/删除。

Non-goals：旧unit_progress改写/迁移、原数据库写入、历史Run/Draft/checkpoint恢复、模型/搜索新增调用、公共资料升级、完整稳定逻辑身份重构、六角色/主线替换、GitHub账号OAuth及真实RAG。这些未完成项继续属于完整Goal，不据此结束Goal。

## 实现与集成证据

Exposure由服务器根据完整出现位置生成UUID5；GET只产生version0虚拟视图，不记录学习。首次显式动作0→1，严格CAS、请求幂等及异体409；完成不传播相同KnowledgeNode的其它位置或新计划。工作区单元显示当前Exposure；旧单元进度另列legacy_progress，不静默完成新位置。KnowledgeNode进度仍为null，不推算掌握。

偏好按node>unit>project>system选择最具体完整设置；删除覆盖保留tombstone及递增版本，不把null覆盖当version0。旧invalid设置通过invalid_scopes+effective:null及各层版本如实显示，可逐项保存/恢复；实际resolve拒绝无效值，禁止静默降级。省略生成请求prefs_snapshot时冻结项目默认，之后设置改变不影响已入队快照；显式请求偏好保留。显式搜索把有效偏好传到ResourceQuery并排序；Tavily仅添加形式/语言/官方优先查询提示，不发送内部node ID。候选语言标und及“语言未核验”，不把语言偏好当检验结果。

浏览器网络结果不明时可明确重试原进度操作，保持body/key；409保留动作/偏好输入并要求显式读回版本。整位置key防止跨单元/节点迟到结果污染；偏好node只允许选定单元的成员。页面加载只有GET，不发起学习变化、模型或搜索。

## Tests / Evidence

全部Python命令使用D:\studyplan\.venv\Scripts\python.exe。规则/接口及PG测试使用自动新建studyplan_test_*，真实外部provider明确不运行；独立真实浏览器沿用本轮新隔离账号和自己的已发布计划。

| 验证 | 状态 | 范围与退出码 |
|---|---|---|
| prefs worker最终unit+PG | PASS | 23项，exit0；随后root增加双层invalid恢复性质 |
| Exposure worker组合 | FAIL | 30通过/1旧记录夹具未实际INSERT；补夹具后原失败定向PASS1 exit0，不改写组合结果 |
| root偏好/Exposure/真实HTTP组合 | PASS | 34项exit0；含版本切换后原receipt重放、双层invalid修复、真实HTTP/session/PG投影及冻结偏好 |
| Tavily adapter+契约+HTTP组合 | PASS | 83项exit0；全离线/本地PG，非新增外部搜索 |
| 最终受影响后端组合 | PASS | 139项，exit0，78.73s；Exposure/偏好规则、Tavily、契约、各PG位置/偏好/资源/真实fence竞争、HTTP及G1纵向回归 |
| frontend unit/build/mock控件与资料选取 | PASS | 4单元、TypeScript/Vite、两个Chrome mock；包含两个旧invalid层修复、跨位置迟到响应与同位置初始GET/新GET/写入乱序。最终控件mock根级复核exit0 |
| Chrome真实HTTP+PG控件 | PASS | AcceptanceId v2-g2-20261001-02；4次进度/不可变来源历史、project/unit设置、恢复tombstone version2、刷新回读，exit0 |
| root新增与改动Python Ruff | PASS | exit0 |
| 负责人体验 / 完整V2门禁 | NOT RUN | 技术切片证据不代替最终用户接受 |

并发审查发现既有资源project→advisory与真实生成advisory→job/run/project的P1死锁。root初判断错误，经实际调用证据纠正；两个真实PG用例先DeadlockDetected FAIL，再统一advisory-first PASS。独立复审发现旧plan原receipt与双层旧偏好修复两个P2，均先语义FAIL后阶段内修复，不延期。页面复审另发现同一位置的旧初始GET可覆盖新操作，先延迟GET复现FAIL，再加读取序号/写入与卸载失效/编辑序号及旧错误丢弃，最终Chrome mock PASS；不重复有效的真实收费验收。

首个root HTTP测试FAIL为路由未接入，接入后进到测试错误字段input_payload；改读取真实ai_run_events.detail后通过。扩展偏好搜索测试首次FAIL为测试adapter缺必填ResourceRecord字段，补明确未核验来源后通过。契约首次FAIL为新API尚未导出；更新OpenAPI和生成客户端后通过。不存在把这些失败改标PASS的合并记录。

专用真实业务库studyplan_test_v2g1real_2f6ac462只增量0013→0014→0015；原用户数据库/8000/PG/Ollama不改，checkpoint库不写入。新自有server使用8021，无模型worker。截图与回执var/v2-g2/learning-controls-real.png/json；代理日志/report、mock截图同目录。测试账号private JSON和.env均忽略且不打印/提交。收费journal不修改，累计模型20/50、Tavily2/1000，结果unknown0；本批新增外部调用0。

## Rollback / 后续

普通revert保留业务数据及收费回执；0014非空进度/历史与0015tombstone/version历史拒绝丢失数据的downgrade，旧迁移不重写。本批没有master/develop集成或milestone接受。代码9c1d85abf8987c4434af1ba10fa944e20428f2fd已在GitHub功能分支，ls-remote与本地相等；功能分支后续文档提交由[唯一检查点](../implementation/progress.md)记录。

继续G2六种资料角色/连续章节/受控替换，GitHub连接和RAG各按实际App配置/接口条件推进；继续后续G3–G6的总结、Prompt、实践证据、版本历史、Outcome与交付。F01–F18/Q01–Q12完整验收仍未完成。
