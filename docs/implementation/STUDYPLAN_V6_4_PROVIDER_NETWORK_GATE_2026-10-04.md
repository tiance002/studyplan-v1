# Codex Goal — StudyPlan v6.4 Provider Network Gate

日期：2026-10-04
正式工程：`D:\studyplan`

## 0. 本轮唯一目标

解除真实模型 provider 的网络解析门禁：

`api.deepseek.com` 当前 DNS 结果包含非公网地址，因此被现有安全检查拒绝。

本轮只解决：provider endpoint 能否在**不削弱 SSRF / 私网访问保护**的前提下，被正式运行链安全访问。

当前仍为 `STAGING_BLOCKED / NOT_READY`。

## 1. 已知前提

上一轮已经完成：

- `LLM_MAX_OUTPUT_TOKENS` 8000 → 8192
- runtime 实际读取 8192
- structure gate PASS
- repair gate PASS
- budget gate PASS
- 50 次受控验收额度未放宽
- 真实收费调用仍为 0
- 原产品数据库未写
- 正式 API / Worker 未切换
- RAG 未操作

当前 blocker：

`api.deepseek.com DNS 含非公网地址 → 现有 endpoint 安全检查拒绝`

## 2. 绝对禁止

不得：

- 关闭 endpoint 安全检查
- 将私网/保留地址加入 allowlist
- 为 DeepSeek 域名写死 IP
- 绕过 DNS rebinding / SSRF 检查
- 修改 provider URL 为未经官方确认的镜像
- 修改模型、provider、temperature、token budgets
- 启动正式 Worker
- 写原产品数据库
- 执行真实收费模型请求
- 修改 RAG
- 为测试方便给所有外部域名放宽策略

如果唯一办法需要降低安全边界，停止并报告。

## 3. Phase A — 只读网络事实审计

确认正式运行环境的网络链：

1. Windows DNS resolver
2. hosts 文件
3. 系统代理
4. WinHTTP proxy
5. `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY`
6. 本机代理软件 / TUN / fake-IP（如果存在）
7. Docker DNS（仅当正式 provider 请求在容器中运行）
8. Python 进程实际 `getaddrinfo()` 结果

对 `api.deepseek.com` 至少记录：

- OS resolver 返回值
- Python runtime resolver 返回值
- 地址类别：public / private / loopback / link-local / reserved / benchmark-or-fake-IP-like
- 是否经过代理
- endpoint guard 为什么拒绝

不要打印任何 API key。

输出：
`docs/reviews/2026-10-04-v6-4-provider-dns-audit.md`

## 4. Phase B — 根因分类

只能归入以下之一：

### B1. LOCAL_PROXY_FAKE_IP
本机代理 / TUN / fake-IP DNS 返回保留地址，真实 HTTPS 流量由代理转发。

### B2. HOSTS_OR_LOCAL_DNS_OVERRIDE
hosts 或本地 DNS 显式覆盖。

### B3. DOCKER_OR_RUNTIME_DNS_MISMATCH
宿主解析正常，但正式 Python / Docker runtime 解析异常。

### B4. PROVIDER_OR_NETWORK_ANOMALY
正常解析链本身返回异常地址。

### B5. UNKNOWN
证据不足。

不得凭经验直接写 B1；必须给运行证据。

## 5. Phase C — 修复策略优先级

### C1. 修正本地 DNS / proxy 域名规则

如果确认是 fake-IP / TUN：

优先让 `api.deepseek.com` 在正式运行进程所用解析链中返回真实公网地址，而不是让应用接受 fake/private/reserved 地址。

如果代理软件支持：

- fake-ip-filter
- direct DNS exception
- real-ip/domain exclusion
- equivalent domain-level DNS mode

只做**最小域名级**调整。

不能：

- 全局关闭 fake-IP
- 关闭代理安全功能
- 放开整个私网段

修改前保存原配置和 rollback。

### C2. 修正 runtime DNS / proxy 配置

如果宿主解析正常、Python/容器异常：

只修正式 runtime 实际使用的 DNS/proxy 链。

### C3. 环境无法安全修复

若当前网络必须使用非公网 fake-IP 且应用安全模型无法在不降级 SSRF 防护下区分：

停止并报告：
`BLOCKED_BY_NETWORK_ENVIRONMENT`

不要改 endpoint guard。

## 6. 安全验收

修复后必须证明：

### 6.1 DNS
`api.deepseek.com` 在正式 runtime 中最终解析为可接受公网地址。

### 6.2 SSRF 保护仍然有效

至少验证以下仍被拒绝：

- `127.0.0.1`
- `localhost`
- RFC1918 私网地址
- link-local
- metadata-style local endpoint
- 原安全检查覆盖的 reserved/private 类别

不得只验证 DeepSeek 成功。

### 6.3 HTTPS / TLS

只执行**不产生模型费用**的最小网络层验证。

优先：

- DNS
- TCP/TLS handshake
- provider 官方无费用 health/model metadata endpoint（仅当前契约明确支持时）

如果没有明确无费用 endpoint：

不要发送 completion/chat 请求。

允许结论：
`DNS PASS / TLS PASS / endpoint guard PASS / paid request NOT RUN`

## 7. Budget / secret 验收

确认：

- `.env` API key 未输出
- 现有受控验收账本仍 23/50
- 没有新增真实收费 request/result
- unknown 不增加
- 8192 配置仍生效
- structure/repair/budget gate 不回退

## 8. 回归

至少运行：

- endpoint URL/security unit tests
- provider binding tests
- structure/repair budget tests
- 最小相关回归

如果修改的是外部代理/DNS配置而非 repo，不要制造业务代码提交。

## 9. STOP 条件

完成后必须停止，只允许以下结论之一：

### PROVIDER_NETWORK_READY

条件：

- 正式 runtime DNS 为公网
- SSRF/private guard 仍 PASS
- TLS/网络层 PASS
- 8192/budget PASS
- 收费调用仍 0

### BLOCKED_BY_NETWORK_ENVIRONMENT

说明准确根因和最小人工操作。

### BLOCKED_PROVIDER_RESOLUTION_ANOMALY

网络环境正常但 provider 域名仍异常。

不要自行进入：

- 真实收费模型验证
- 原库升级
- 正式入口切换
- Worker 启动

## 10. 最终报告格式

输出：

### Baseline
- branch
- HEAD
- working tree

### Resolver facts
- OS DNS
- Python runtime DNS
- proxy/TUN/fake-IP status
- root-cause class

### Change
- changed file/config
- exact semantic change
- rollback
- whether repo code changed

### Security
- DeepSeek public resolution PASS/FAIL
- private/loopback/link-local/reserved rejection PASS/FAIL
- endpoint guard unchanged YES/NO

### Network
- TLS PASS/FAIL/NOT RUN
- paid request count = 0

### Budget
- runtime max output
- structure
- repair
- quota ledger

### Final
- PROVIDER_NETWORK_READY
- BLOCKED_BY_NETWORK_ENVIRONMENT
- BLOCKED_PROVIDER_RESOLUTION_ANOMALY

只给一个下一最小动作。
