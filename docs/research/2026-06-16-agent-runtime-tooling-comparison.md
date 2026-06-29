# 技术调研：CrewAI、Qoder CLI、Claude Code CLI 与专家团 Runtime

Date: 2026-06-16
Status: completed

## 结论先行

对 Emotion Talk 的“专家团建议”生产 runtime，我的建议是：

```text
第一选择：前置验证 AgentScope Agent Team
第二选择：自研轻量状态机 / CrewAI Flow 作为 fallback
不建议：把 Claude Code CLI 或 Qoder CLI 直接作为用户生产 runtime
```

原因：

- 我们要的不是“代码仓库里的几个 coding agent”，而是产品内的 `space -> recording -> expert_advice_job -> rounds/artifacts`。
- 专家团的交付物包含“过程”，所以 runtime 需要事件流、消息记录、角色隔离、任务恢复和可回放。
- Claude Code CLI 和 Qoder CLI 都很强，但核心是 terminal / coding agent 工作流，天然围绕工作目录、本机会话、工具权限和开发者账号。
- CrewAI 更接近业务编排框架，适合 Flow、Crew、Task、checkpoint，但不是天然的多用户会话服务和 agent message bus。
- AgentScope 的 Agent Service / Agent Team 更贴近“多 worker 独立会话 + 消息总线 + 事件流 + session replay”的产品需求。

## 调研对象

本次重点看：

- CrewAI
- Qoder CLI / Qoder Agent SDK
- Claude Code CLI / Claude Agent SDK / Agent Teams

同时把 AgentScope 作为当前专家团 runtime 基线参与比较。

## 本地验证结果

### 本机环境

```text
Python default: 3.14.3
Python 3.12: 3.12.12
Node: 24.6.0
npm: 11.5.1
uv: 0.8.0
Claude Code: 2.1.143
Qoder CLI: 0.1.11
CrewAI CLI: not installed
```

### Claude Code CLI

已安装，可运行：

```text
claude -v
-> 2.1.143 (Claude Code)
```

认证状态：

```text
API key: ANTHROPIC_API_KEY
Anthropic base URL: https://idealab.alibaba-inc.com/api/code
```

本地可见能力：

- `claude -p` 非交互模式。
- `--output-format text/json/stream-json`。
- `--json-schema` 结构化输出。
- `--max-budget-usd`、`--max-turns` 成本/轮次限制。
- `--tools`、`--allowed-tools`、`--disallowed-tools` 权限控制。
- `--agents` 自定义 subagents。
- `claude agents` background agent view。
- `--worktree` 隔离工作目录。

观察：

- `claude agents --json` 在本机版本中不可用，虽然官方 CLI reference 提到过相关 JSON 输出能力；实际以本机版本为准。
- `claude daemon status` 显示 supervisor 当前未运行。
- 命令启动有明显初始化耗时，作为高并发后端 runtime 时需要特别评估冷启动和进程管理。

### Qoder CLI

官方命令名是 `qodercli`，不是 `qoder`。

已安装：

```text
qodercli --version
-> 0.1.11
```

本地可见能力：

- TUI 模式。
- `-p/--print` 非交互模式。
- `-f/--output-format text/json/stream-json`。
- `--allowed-tools`、`--disallowed-tools`。
- `--max-turns`。
- `--worktree` 并发 job。
- `qodercli jobs`。
- `qodercli mcp add/get/list/remove`。

观察：

- 官方文档提到的 `qodercli --list-models` 在本机 `0.1.11` 不存在。
- 官方文档提到的 `qodercli agents list` 在本机 `0.1.11` 不存在。
- `qodercli jobs` 会尝试写 `~/.qoder/logs`，在当前沙箱中因权限报错，但仍返回 job 列表。
- 这说明 Qoder CLI 有较强本机状态依赖，作为服务端 runtime 需要额外隔离 home、logs、workspace、token 和权限。

### CrewAI

本机未安装 `crewai`。

官方安装要求：

```text
Python >=3.10 and <3.14
uv tool install crewai
```

本机默认 `python3` 是 `3.14.3`，不符合 CrewAI 官方要求；但本机存在 `python3.12`，理论上可以指定兼容 Python 运行。

尝试用 `uvx --from crewai crewai --version` 做临时下载执行时被安全审核拦截。原因是该动作会联网下载并执行第三方代码，可能读取本地文件和环境变量。这个限制合理，本次没有绕过。

## 官方能力对比

### CrewAI

官方定位：

- 生产级 multi-agent systems。
- 核心概念是 Agents、Crews、Tasks、Processes、Flows。
- 官方 Quickstart 强调：Flows 是生产 app 的推荐结构，Flow 拥有状态和执行顺序，agent 在 crew step 内工作。

关键能力：

- YAML 或代码定义 agents/tasks。
- Crew 支持 sequential、hierarchical 等流程。
- Flow 支持 `@start()`、`@listen`、状态对象。
- 支持 task callback、step callback、human-in-the-loop、guardrails。
- 支持 checkpoint，可在 task 完成后保存状态并恢复。
- 支持 output log、usage metrics、Pydantic/JSON output。
- 有 Enterprise AMP SaaS 和 Factory self-hosted。

适合：

- 后端内部的确定性 AI workflow。
- 自动纪要 pipeline。
- 可拆成 task 的研究、报告、审核、数据处理流程。
- 想用 Python 快速写 AI 编排，并且不需要 worker 之间真实 peer-to-peer 消息的场景。

不适合直接做我们 V1 专家团主 runtime 的原因：

- 没有看到类似 AgentScope 那样的一等公民 `session + inbox + wakeup + Redis message bus + SSE replay` 服务模型。
- 多 agent 更像“任务编排”，不是“多用户产品内专家会议”。
- 如果要做专家互相发言、可回放过程、用户离开后恢复、iOS 订阅事件流，很多服务层能力仍要自己补。

### Claude Code CLI / Claude Agent SDK

官方定位：

- Claude Code 是 agentic coding tool。
- 能读代码库、改文件、跑命令、接 MCP，覆盖 terminal、IDE、desktop、browser。
- Claude Agent SDK 将 Claude Code 的 agent loop、工具执行、subagents、MCP、sessions、permissions 等暴露给 Python/TypeScript。

关键能力：

- CLI 非交互 `-p`。
- JSON / stream-json 输出。
- JSON schema 结构化输出。
- 工具 allow/deny。
- max turns / max budget。
- subagents。
- background agents / agent view。
- Agent Teams：多个独立 Claude Code session，由 lead 协调，带 shared task list 和 mailbox。

Agent Teams 很强，但目前不适合直接进用户生产链路：

- 官方标注 experimental，默认关闭。
- 官方明确有 session resumption、task coordination、shutdown behavior 等限制。
- Team state 存在本机 `~/.claude/teams/{team-name}` 和 `~/.claude/tasks/{team-name}`。
- Team config 只在运行时存在，清理后移除，不是项目级可配置资源。
- 目标场景仍是 Claude Code sessions 协同处理开发任务。
- token 成本随 teammate 数量线性或更高增长。
- 作为多租户产品 runtime，还要自己补 user/space/recording/job 隔离、审计、成本、事件映射和数据落库。

适合：

- 内部研发助手。
- prompt/专家角色样例生成。
- 对专家团输出做离线评审。
- 让多个 coding/review agent 帮我们实现产品。
- Claude Agent SDK 可用于内部工具型 agent，但不应先承担 V1 面向用户的情绪倾诉专家团 runtime。

### Qoder CLI / Qoder Agent SDK

官方定位：

- Qoder 是 agentic coding platform。
- CLI 支持 terminal-based AI assistant、代码分析、MCP、worktree、非交互 print mode。
- SDK 支持 TypeScript/Python 调 Qoder AI 能力，能读写文件、搜索代码、执行命令，并嵌入应用或脚本。

关键能力：

- TUI。
- print mode。
- text/json/stream-json。
- worktree 并发 job。
- MCP 管理。
- AGENTS.md memory。
- 工具 allow/deny。
- Qoder Agent SDK：`query()`、长会话 client、streaming output。
- SDK 支持 custom tools，经 MCP server 暴露。
- SDK 支持 built-in/custom subagents。
- 模型体系是 Qoder tier / frontier / custom model。
- 认证依赖 Qoder PAT 或复用本地 qodercli 登录。

问题：

- 本机版本 `0.1.11` 与官方文档存在差异，`--list-models` 和 `agents list` 不可用。
- CLI 有本地 `~/.qoder` 状态和日志依赖。
- SDK 认证依赖 PAT；官方说明 SDK 不自动刷新 PAT，需要 host app 自己处理过期。
- 能力仍以代码项目工作流为中心，不是产品内多用户 agent service。

适合：

- 内部 coding agent。
- 代码审查、自动化脚本、Qoder 生态试验。
- 如果未来团队深度使用 Qoder，可作为研发侧工具链。

不建议：

- 不建议把 Qoder CLI 直接作为 Emotion Talk 用户生产 runtime。
- 不建议在 V1 专家团上依赖 Qoder PAT / CLI 本机状态 / `~/.qoder` 日志路径。

### AgentScope 基线

AgentScope 官方文档确认的核心能力：

- Agent Team 构建在 Agent Service 之上。
- Leader 是用户对话会话。
- Worker 是派生出的独立 session，有自己的状态、工作区绑定和事件流。
- Team Message 通过 Redis-backed message bus 路由，以 `HintBlock` 投递。
- Message bus 管 session lock、replay log、inbox queue、wakeup signal。
- 任意 wakeup dispatcher 可以认领唤醒并驱动对应 session 运行。
- Session stream 通过 SSE 暴露 AgentEvent，后接入者可重放缓冲历史。
- `HintBlockEvent` 可追加到消息内容，支持 team message 持久化和重放。

适合：

- Emotion Talk 的“专家团过程可展示”。
- 多角色、独立会话、互相发消息、裁判收敛。
- 用户离开后回来查看过程。
- 服务端长期运行而非本机 CLI session。

风险：

- 引入 FastAPI + Redis + AgentScope runtime。
- 默认 `X-User-ID` 不是生产鉴权，需要替换。
- workspace 默认隔离策略未必符合 `space/recording/job`，需要定制。
- 最终输出 schema、safety、裁判收敛仍要我们自己约束。

## 决策矩阵

| 维度 | CrewAI | Claude Code CLI/SDK | Qoder CLI/SDK | AgentScope |
|---|---:|---:|---:|---:|
| 产品内多用户 runtime | 中 | 低 | 低 | 高 |
| 多 agent 过程展示 | 中 | 中高 | 中 | 高 |
| peer-to-peer agent message | 低 | 高但 experimental | 低/中 | 高 |
| 事件流 / replay | 中 | 中 | 中 | 高 |
| 与业务资源模型集成 | 中 | 低 | 低 | 中高 |
| 部署复杂度 | 中 | 中 | 中 | 中高 |
| 供应商绑定 | 中 | 高 | 高 | 中 |
| 适合 coding agent | 中 | 高 | 高 | 中 |
| 适合倾诉专家团 | 中 | 低/中 | 低/中 | 高 |

## 推荐路线

### V1 专家团 runtime

```text
先做 AgentScope spike。
```

验证目标：

1. 一个 `expert_advice_job` 能否映射为一个 AgentScope team/session。
2. 3 个专家 worker 是否能独立会话运行并互发 Team Message。
3. iOS 是否能消费 event stream 并展示“总-过程-总”。
4. 所有 team messages、worker outputs、judge result 是否能落到我们自己的 PostgreSQL。
5. 是否能替换鉴权并隔离 `space/recording/job`。
6. 是否能限制工具，只允许 LLM / read-only context / safe internal APIs。
7. 失败、取消、超时、重试是否可控。

### Claude Code / Qoder 的位置

```text
内部研发工具，不进用户生产 runtime。
```

可用于：

- 帮我们写代码。
- 跑内部 code review。
- 生成专家团 prompt 候选。
- 离线比较不同专家角色配置。
- 帮我们审查 AgentScope spike 结果。

不建议用于：

- 直接接收用户倾诉数据。
- 直接作为多租户后端 job worker。
- 直接暴露给 iOS 生产链路。

### CrewAI 的位置

```text
AI workflow fallback / 非专家团流程候选。
```

可用于：

- 自动纪要 pipeline。
- 结构化报告生成。
- 内部研究自动化。
- 如果 AgentScope 过重，用 CrewAI Flow + 我们自己的 DB/Queue/Event 层做折中。

但不作为第一选择，因为它没有天然解决 expert team 所需的消息总线和独立 session 事件流问题。

## 下一步建议

1. 把现有 `docs/decisions/2026-06-15-expert-agent-runtime.md` 从“自研轻量优先”修正为“AgentScope 前置 spike 优先”。
2. 新增 `docs/specs/agent-scope-spike.md`，定义 1-2 天 spike 的完成标准。
3. Spike 不接真实用户数据，只用脱敏样例。
4. Spike 只允许 read-only 工具，不接 shell/file write。
5. Spike 成功后再决定是否将 `services/api` 主栈确定为 Python + FastAPI。

## 资料来源

- CrewAI Documentation: https://docs.crewai.com/
- CrewAI Installation: https://docs.crewai.com/en/installation
- CrewAI Quickstart: https://docs.crewai.com/en/quickstart
- CrewAI Crews: https://docs.crewai.com/en/concepts/crews
- CrewAI Flows: https://docs.crewai.com/en/concepts/flows
- Claude Code Overview: https://code.claude.com/docs/en/overview
- Claude Code CLI Reference: https://code.claude.com/docs/en/cli-reference
- Claude Agent SDK: https://code.claude.com/docs/en/sdk
- Claude Code Subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code Agent Teams: https://code.claude.com/docs/en/agent-teams
- Claude Code Parallel Agents: https://code.claude.com/docs/en/agents
- Qoder Documentation: https://docs.qoder.com/
- Qoder CLI Quick Start: https://docs.qoder.com/en/cli/quick-start
- Qoder CLI Usage: https://docs.qoder.com/en/cli/using-cli
- Qoder Agent SDK Quick Start: https://docs.qoder.com/en/cli/sdk/quick-start
- Qoder Agent SDK Python Quick Start: https://docs.qoder.com/en/cli/sdk/python/quick-start
- Qoder SDK Authentication: https://docs.qoder.com/en/cli/sdk/authentication
- Qoder SDK Subagents: https://docs.qoder.com/en/cli/sdk/agents
- Qoder SDK Tools: https://docs.qoder.com/en/cli/sdk/tools
- Qoder Streaming Output: https://docs.qoder.com/en/cli/sdk/streaming-output
- AgentScope Agent Team: https://docs.agentscope.io/zh/v2/deploy/agent-team
- AgentScope Agent Service: https://docs.agentscope.io/zh/v2/deploy/agent-service
- AgentScope Message & Event: https://docs.agentscope.io/zh/v2/building-blocks/message-and-event
