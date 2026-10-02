# GitHub公开教程发现预检

日期：2026-10-02。基线为本地 `feat/v2-g1-user-slice` 的 `3d8ba67`，沿用用户已提交的第4版测试课程及学习前端。此报告仅记录公开接口准备与最新资料要求，不表示软件已实现GitHub搜索、MCP或账号连接。完整V2仍为NOT_READY。

## 用户最新资料要求

资料搜集优先寻找与学习目标、阶段水平相符的教学性来源，如连续教程、循序解释、配套示例和练习。官方身份与教学性是两个维度；官方教程也可作主线，纯API/协议参考主要作为补充。仓库名中的learn/tutorial及README的教程说明是候选信号，须进一步检查目录、实际章节与示例，不能单凭名称、Star、可访问性或模型判断宣称教学质量。

用户举例的 `datawhalechina/hello-agents` 与 `shareAI-lab/learn-claude-code` 已在线读取README。前者明确介绍系统性智能体学习教程与章节，后者当前README明确说明逐章教程及配套代码，并区分当前路线与历史路线。实际章节选择应读取当时版本，不能盲目沿用旧链接。

## 当前实现差距

- Tavily通用搜索及私有候选选择已实现。`TavilyResourceIndex`只取标题和网址，所有结果标TEXT/und/未核验，没有保留摘要或读取README，也未识别教学结构。
- `rank_resources`按可用性、媒体、语言、官方出处和标题排序，没有教学性维度；没有保留搜索引擎的相关性评分。
- 手动GitHub URL仅保存未核验元数据；GitHub专用索引、README/章节抓取、MCP宿主及账号OAuth均未实现。
- 第4版课程的27项资料安排使用19个官方URL，尚未按本次教程优先要求重新审核和发布。用户第4版结构与前端保留，不能把本次接口预检当作新路线发布。

## 只读真实接口证据

新预检ID `github-tutorial-preflight-20261002-01`。无认证GET GitHub REST `/search/repositories`，一次查询 `agent tutorial in:name,description,readme archived:false`，最多5候选；随后两次GET指定公开仓库的 `/readme`。固定api.github.com、TLS、无自动重定向、单请求15秒超时、响应256KiB上限；不执行仓库代码，不调用模型、Tavily、RAG或产品业务写接口。

| 检查 | 状态 | 界限 |
| --- | --- | --- |
| 匿名公开仓库搜索 | PASS | HTTP200，incomplete_results=false，5候选 |
| Hello-Agents README读取 | PASS | HTTP200，20,119字节，真实README blob SHA已记录 |
| learn-claude-code README读取 | PASS | HTTP200，25,596字节，真实README blob SHA已记录 |
| 教程信号检查 | PASS | 两README有教学/章节信号；不代表课程质量验收 |
| 产品GitHub搜索、账号授权、MCP与浏览器完整流程 | NOT RUN | 尚未实现本次薄适配 |
| 模型调用、仓库运行、测试课程再发布 | NOT RUN | 本次不调用、不执行、不发布 |

搜索返回InternLM/Tutorial、sshlog/agent、NirDiamant/agents-towards-production、laravel/laravel、patchy631/ai-engineering-hub；出现SSH和通用Web框架噪声，说明宽关键词不足以确认阶段适配或教学性。两个用户示例的README是按已知仓库单独读取，不能宣称它们被本次搜索自动召回。

累计授权搜索计数从2变为3/1000：Tavily2、GitHub公开搜索1；两次README读取另记为页面读取。模型仍23/50。新请求/回执以独占追加保存 `.git/v2-search-quota-20261001/request-0003.json` 和 `result-0003.json`，unknown=false；不改旧记录。ignored证据 `var/github-discovery/github-tutorial-preflight-20261002-01.json` 保存时间、状态、候选、README路径/blob SHA/内容hash及信号，不保存秘密。

首次预检本地FAIL：Windows默认GBK读取已有UTF-8回执，发生UnicodeDecodeError，尚未预约或发送请求。明确指定UTF-8后一次真实搜索及两次读取PASS，没有重复外部调用。

## 后续有界实现依据

沿用已授权F08与现有资源Port，优先增加公开GitHub REST薄适配和教程证据展示，不为公开资料发现引入通用MCP Runtime。默认每个缺口一次查询、五候选、至多三次页面读取；未读取候选应明确标记。先按阶段相关性筛选，再依据真实README/目录/示例识别教学候选，官方细节作补充，保留显式资料选择与版本化替换。限流/无结果/读取失败明确展示，原历史不覆盖。

软件依赖优先复用现有httpx；链接/有限索引与复制外部代码分开，涉及代码或正文复用前核对相应仓库许可证。搜索计量、幂等、未知结果不重派、受限读取和服务端归属规则继续适用。浏览器账号连接是独立需求，公开仓库接口可无认证使用，不能把本次匿名搜索称为账号已连接。

来源：[GitHub仓库搜索API](https://docs.github.com/en/rest/search/search#search-repositories)、[GitHub README接口](https://docs.github.com/en/rest/repos/contents#get-a-repository-readme)、[Hello-Agents](https://github.com/datawhalechina/hello-agents)、[learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)。
