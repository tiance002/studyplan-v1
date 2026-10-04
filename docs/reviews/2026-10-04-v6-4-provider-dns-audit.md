# v6.4 Provider Network Gate — DNS 审计、修复与 STOP

用户现在新增能做什么：正式配置加载链的DeepSeek endpoint可以通过公网DNS、安全guard与真实部署绑定，并完成免费TLS握手；本轮没有开启生成服务或消费模型请求。

结论：**PROVIDER_NETWORK_READY**。全产品仍 **STAGING_BLOCKED / NOT_READY**；原库、正式入口、Worker、收费、RAG继续独立门禁。本轮在[v6.4 Goal](../implementation/STUDYPLAN_V6_4_PROVIDER_NETWORK_GATE_2026-10-04.md)规定的STOP结束。

## Baseline

- branch：feat/n1-resource-discovery；进入HEAD `0d65a1e647b9d19496bc45ad94c24c956cfede40`。
- tracked clean，仅两禁止操作目录未跟踪；没有reset、历史改写、master/develop集成或推送。
- `.env` runtime上限8192已通过上一单项授权修正；本轮整份.env SHA前后一致，未修改任何模型/provider/temperature/purpose预算参数。
- 正式provider运行链是Windows脚本→工程.venv Python；Docker只在过去提供PG客户端，本轮Docker DNS NOT RUN，不将容器解析当正式provider。

## Phase A/B：真实解析链与根因

| 事实 | 修前结果 |
|---|---|
| Windows Resolve-DnsName | A198.18.0.161、AAAA2001:2::9a |
| 正式Python getaddrinfo | 同上；两个地址is_global=false，属于benchmark-or-fake-IP-like |
| hosts | 没有api.deepseek.com条目；文件hash最终不变 |
| Windows系统代理 | 开启，127.0.0.1:7900；无代理URL凭据，PAC未设置 |
| WinHTTP proxy | Direct access，无WinHTTP代理 |
| HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY | 父进程均未设置；正式HTTPX另会读取Windows代理注册表 |
| TUN/DNS | Meta Tunnel Up；IPv4 DNS198.18.0.2、IPv6 DNS fdfe:dcba:9876::2；active core tun.enable=true |
| 代理软件 | clash-verge.exe PID2096、service PID9252、verge-mihomo.exe PID12392；本机控制接口GET/version返回v1.19.32 |
| 真实生效DNS | fake-ip；fake-ip-filter缺失，IPv4 range198.18.0.1/16，IPv6 range2001:2::0/64 |
| 编辑但未消费的配置 | dns_config.yaml已有DeepSeek/GitHub，但verge.yaml enable_dns_settings=false；其编辑值不能冒充运行事实 |
| 核心上游查询 | 本机/dns/query A给出真实公网119.188.175.46、123.125.246.121，AAAA无地址；说明上游解析可用，fake映射是本地输出环节 |

根因确定为 **B1 LOCAL_PROXY_FAKE_IP**，不是凭代理软件名称猜测。OS与Python一致、TUN和实际core配置及上游查询相互支持；guard正确拒绝非公网结果。没有证据支持B2 hosts覆盖、B3 Docker/宿主差异或B4 provider原始解析异常。

系统接口/服务器的完整安全元数据保存在ignored network-audit-before.json，未输出API key、订阅URL、代理节点凭据或私人业务正文。

## Phase C：单一域名级修正

持久配置：

`C:\Users\22088\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\profiles\mxAo9JFl7Wm5.yaml`

通过profiles.yaml的current→option.merge→merge.file实际映射确认这是当前订阅覆写，原文件仅注释、YAML为空。仅追加：

```yaml
dns:
  fake-ip-filter:
    - api.deepseek.com
```

同时将这一字段写入当前生成的clash-verge.yaml，完整YAML对象比较确认删除新字段后与原配置完全相同。没有启用整套GUI DNS覆写，也没有改TUN/mode/nameserver/IPv6范围/路由/全局fake-IP/其它域名。

Mihomo的默认blacklist过滤会对匹配域名返回真实解析，保持其他域名的fake-IP模式；依据[官方DNS文档](https://github.com/MetaCubeX/Meta-Docs/blob/main/docs/config/dns/index.md)。采用当前订阅扩展而非修改下载的订阅原文，依据[Clash Verge官方扩展链说明](https://github.com/clash-verge-rev/clash-verge-rev.github.io/blob/main/docs/guide/extend.md)。

原覆写和原生成配置已逐字节备份至本机ignored `var/v64/private`；目录ACL限制当前用户/SYSTEM/Administrators，继承关闭、3条规则，备份hash核对PASS。完整生成配置含本机代理秘密，仅本机受限备份，不入Git、不输出。

运行重载使用已发现的实际production named pipe与现有本机controller secret；GET/version和GET/configs先核对。按[官方API](https://wiki.metacubex.one/api/)的PUT/configs?force=true通过payload发送同一配置加唯一字段，HTTP204。未开放新TCP controller、修改SAFE_PATHS/ACL权限或重启代理服务。重载前后GET/configs全部基本字段完全相同，PASS。

生成配置里的sidecar pipe并非实际运行的production pipe；首轮对sidecar读取FileNotFound，随后只读枚举发现实际pipe并成功认证。ProgramData目录只读检查AccessDenied，未提升权限或更改其ACL。一次临时Python raw string语法检查FAIL已修正；这些操作错误保留，不影响最终门禁结果。

此持久修正只覆盖当前订阅；切换订阅需重新核对。GUI未来重新生成后的自动消费本轮NOT RUN；当前运行配置的域名规则通过真实OS/Python解析变化证实，不能只凭文件文本声明。

## 安全、TLS及预算

正式启动脚本scripts/b3f1-dev.ps1的原环境加载语句在新隔离PowerShell执行，不执行启动分支。工程新Python读取get_settings/构造真实provider及bind_submission，没有Settings replace、Fake DNS或安全guard替换用于实际成功路径。

| 验收 | 状态 | 证据 |
|---|---|---|
| 修后OS/Python DNS | PASS | 119.188.175.46、123.125.246.121；全部is_global=true，无IPv6 fake地址 |
| 真实endpoint guard | PASS | 真实DNS下validate正式.env endpoint |
| 真实部署binding | PASS | 实际bind_submission，policy与配置一致，无私人模型仓储/数据库访问 |
| unsafe URL拒绝 | PASS | 14项含127.0.0.1/localhost/三RFC1918/169.254/metadata/benchmark/reserved/IPv6loopback与ULA |
| 混合公网+非公网DNS拒绝 | PASS | 14项，允许域名返回混合DNS也拒绝；含CGNAT、IPv6benchmark/documentation |
| endpoint guard源码/allowlist | PASS | 源文件hash未改变；正式.env原样，未加私网/保留地址 |
| TLS | PASS | 按安装HTTPX实际代理发现结果经127.0.0.1:7900 CONNECT官方api.deepseek.com:443，HTTP200后TLS1.3；certifi信任链及hostname严格验证 |
| provider HTTP/收费请求 | NOT RUN | 未发provider HTTP请求或chat/completion，API key未发送；真实收费0 |
| runtime max output | PASS | 实际get_settings8192；其它Settings摘要与上轮相同 |
| structure / repair / budget | PASS | validate_all与build_llm/request_options分别8192；outline/practice4096；已有累计Run门禁证据按相同代码/.env复用 |
| 受控额度及旧unknown记录 | PASS | 23/50 request/result全部hash未变；旧controlled-live journal/evidence全部hash未变，unknown增量0 |

TLS只发送本机代理CONNECT及TLS协议，不发送provider HTTP报文或任何模型正文。SSRF域名及地址检查先执行并在连接前重新核对；没有硬编码DeepSeek IP用于连接，以上公网地址仅为当时观测。IPv4/IPv6拒绝用例是隔离DNS fixture，明确与真实DeepSeek成功路径分开。

HTTPX在Windows会从注册表发现代理，不能把环境变量未设置误记为直连。网络验收使用相同proxy目的地和certifi证书信任源；CONNECT只验证网络层，不冒充正式API已启动或真实生成已验收。

## 最小回归与证据

- endpoint URL/private DNS/rebinding-before-key、deployment binding、purpose budgets、provider HTTP Mock测试：**PASS24**、0FAIL、0NOT RUN，1.09s。
- 28项运行探针安全拒绝检查PASS，单列于pytest，不叠加测试数量。
- 8192累计Run/50次边界/unknown保护复用上一配置批的有效证据；代码与.env未变化，本轮没有重新执行PG或受控收费wrapper。
- 私人产品数据库、正式API/Worker、RAG、收费模型：**NOT RUN**。
- 后端/脚本/.env.example diff为空，没有业务代码、测试源码、依赖或安全策略修改。文档/Goal精确归档/progress更新不构成业务实现提交。

| ignored artifact | SHA256 |
|---|---|
| network-audit-before.json | 162de741dcc2fa69d30abfb621a4fbeef8dc8c519459ac7ccf4e357d826586be |
| proxy-domain-change.json | 00b5f82e45fc767de8fc33efc0a9922986e6a2073f1a8da8c2f3b6d029c7956f |
| runtime-security-tls.json | 2ff56642827b066f6d41c7de0421f5614eac5d2b438c512d5e9aafd41a76ec5a |
| endpoint-binding-budget.xml | cf21deeb3e6ab8d96566d362b1f4815de8d6c27e0dce2bde8fd6b53d6ae02df7 |
| final-invariants.json | 19110fccac7500b2d16bab7d378c7488d1f32a7723ae470dac05e2a5a7d94ea6 |

本轮不派子代理；请求主协调Sol6.1/high，实际model/effort NOT OBSERVABLE。免费外部动作仅官方资料查询、DNS与一次TLS握手；本机controller GET/一次授权PUT用于解析修正。产品模型/搜索账本未追加，不将文档浏览记为产品收费验证。

## Rollback、风险与 STOP

回滚命令（本輪未执行）：

```powershell
& 'D:\studyplan\.venv\Scripts\python.exe' 'D:\studyplan\var\v64\proxy_domain_fix.py' rollback
```

脚本先核对两个当前文件与本次修改后hash，以及备份原hash；出现后续代理修改则拒绝覆盖。恢复当前订阅merge和生成配置原字节，再经同一本机控制接口重载。回滚会恢复原fake-IP解析/endpoint阻塞；不会修改StudyPlan.env或放宽应用guard。

网络环境会随订阅、代理规则或上游DNS改变；本次READY是本机当前运行链的有界证据，不是长期保证或真实模型输出验收。全产品仍有非空真实用户历史、RAG契约、收费代表及完整用户接受门禁，原库/入口/Worker继续STOP。

最终 **PROVIDER_NETWORK_READY**，本轮STOP。下一唯一最小动作：另行审阅并批准已准备的[收费代表验证方案](2026-10-04-v6-3-paid-representative-plan.md)；此报告不自动授予收费或正式部署权限。
