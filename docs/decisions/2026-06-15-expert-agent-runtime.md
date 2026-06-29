# Decision: 专家团 Agent Runtime 选型

Date: 2026-06-15
Status: revisiting

> 2026-06-16 update: 本决策已被重新评估。新的接受决策见 `docs/decisions/2026-06-16-expert-agent-runtime-revisit.md`。

## Context

专家团是 V1 的用户主动触发能力。它不是自动摘要，也不是普通聊天。

输入：

- 当前这次 Recording 的最终转写。
- AI 图文纪要。
- 少量相关历史记录。
- Space Profile。
- 用户本次点击专家团时的输入快照。

输出：

- 总览。
- 多轮专家讨论过程。
- 裁判收敛。
- 1-3 条克制建议。
- 关键原话依据。
- 不确定性和安全边界。

专家团需要可审计、可恢复、可展示过程，而不是只追求 agent 自由发挥。

本次决策只决定 V1 生产路径：用户点击“专家团建议”后，服务端到底用什么 runtime 生成多轮讨论和最终建议。

## 方案 A: 云端部署 Claude Code / Claude Agent SDK

### 你当前设想的形态

```text
准备一台机器
-> 安装 Claude Code
-> 为专家团准备工作目录
-> 服务端把任务写入目录或调用 CLI/SDK
-> Claude Code 产出专家团结果
```

这个方案的吸引力很强：落地快、心智简单、开发体验好，尤其适合单人 dogfooding。

### 适合点

- Claude Code 官方定位是 agentic coding tool，擅长读代码库、改文件、跑命令、接 MCP、自动化开发任务。
- Claude Agent SDK 把 Claude Code 的 agent loop、工具执行、上下文管理作为 Python/TypeScript library 暴露。
- 支持 built-in tools、subagents、MCP、streaming、structured output、hooks、observability 等能力。
- 如果专家团未来需要大量工具调用、文件读取、外部系统操作，Claude Agent SDK 有吸引力。
- 用于内部实验、prompt 迭代、离线评测和开发助手时，落地成本最低。

### 问题

- Claude Code CLI 的核心心智是 coding agent，不是窄领域产品内专家建议 runtime。
- 默认工具能力偏重文件、命令、代码库，作为情绪倾诉专家团会显得过重。
- 供应商绑定更强，模型/provider 灵活性较弱。
- 如果直接把 CLI 当云端服务跑，需要额外处理隔离、权限、审计、成本、会话和多租户。
- 对我们固定角色、固定流程、强审计的专家团来说，可能“能力过剩但控制成本高”。

你担心的两个点是关键风险：

- 多用户隔离：Claude Code 的自然边界是工作目录和工具权限，不是产品里的 `user -> space -> recording -> job` 资源模型。要做到真正隔离，需要我们在外层自己做目录隔离、凭证隔离、进程隔离、日志隔离和清理策略。
- 并发控制：直接跑 CLI/工作目录模式时，并发、排队、取消、超时、重试、成本限额都要自己包一层。否则多个专家团任务同时跑时，很容易出现资源争用、上下文串扰或不可预测的失败。

如果这条路进入用户生产链路，还要补：

- 每个 job 的独立 workspace。
- 每个 Space 的输入/输出权限边界。
- 任务队列和 worker 池。
- 超时、取消、重试和幂等。
- stdout/stderr/文件产物的脱敏和持久化。
- 费用和 token 使用记录。
- 失败后可恢复的 job 状态。
- 禁止不必要的文件、shell、网络工具。

### 判断

不建议作为 V1 默认产品 runtime。

可以保留两个用途：

- 开发期帮助我们写代码、审查提示词和生成测试样例。
- 单用户内部 dogfood：可以用一台机器跑离线专家团实验，但不要把它暴露成面向用户的正式服务。
- 后续评估 Claude Agent SDK 是否适合某些高阶研究/工具型专家。

## 方案 B: AgentScope Agent Team

### 从官方文档确认到的能力

AgentScope 的 Agent Team 构建在 Agent Service 上：

- Leader 智能体可以派生 worker 智能体。
- 每个 worker 是独立会话，有自己的状态、工作区绑定和事件流。
- 团队通信通过内置 team tools 完成。
- 内置工具包括 `TeamCreate`、`AgentCreate`、`TeamSay`、`TeamDelete`。
- Worker 在自己的会话里并发运行。
- Leader 通过读取 worker 输出和发送消息来协调团队。
- 团队通信由 Redis 支撑的消息总线转发。
- Agent Service 基于 FastAPI，提供多租户、多会话、持久化、调度、后台任务卸载、SSE session stream。
- 分布式部署能力仍标注为 WIP，但设计上依赖 Redis 存储和消息总线，适合横向扩展。

### 适合点

- 和“专家团”概念天然贴近：Leader / Worker / Team Message。
- 有独立事件流，适合展示过程。
- 有会话持久化和 replay，适合用户离开后回来查看。
- 有后台任务卸载，适合耗时专家团流程。
- 支持自定义子智能体模板，适合人生教练、心理咨询、现实行动等角色隔离。

### 问题

- 引入 Python FastAPI + Redis + AgentScope runtime，部署复杂度明显上升。
- 框架心智较重，V1 可能还没证明专家团真的值得这么重。
- 分布式部署标注 WIP，需要谨慎验证生产可靠性。
- 如果我们专家团流程固定，AgentScope 的动态团队能力可能用不上太多。

### 判断

适合做 spike，不建议未验证前直接作为 V1 默认。

如果 spike 证明它能明显提升：

- 多轮过程可观测性；
- 任务恢复；
- 角色隔离；
- 事件流展示；
- 后续扩展；

则可以把专家团 runtime 切换到 AgentScope。

## 方案 C: 自研轻量多 Agent 编排

### 形态

服务端实现一个固定状态机：

```text
冻结输入快照
-> Safety 预检
-> Round 1: 三个专家初判
-> Round 2: 互相质疑
-> Round 3: 修正观点
-> Judge: 收敛结论
-> Safety 复检
-> 结构化输出
```

每个专家不是独立服务，而是同一个后端 job 中的 role prompt + LLM call。

### 适合点

- 最快实现。
- 最容易审计。
- 输出结构最可控。
- 最适合当前固定 3 专家 + 裁判模式。
- 便于记录每轮输入、输出、模型、成本和失败原因。
- 不需要一开始引入 AgentScope/Claude Agent SDK 的运行时复杂度。

### 问题

- 不如 AgentScope 那样天然支持独立会话、事件流和分布式 team。
- 后续如果专家增多、工具增多、过程更复杂，状态机会变重。
- 需要我们自己实现 job 状态、进度、恢复和可观测性。

### 判断

推荐作为 V1 默认。

## Recommendation

硬结论：

```text
V1 生产 runtime：自研轻量多 Agent 编排
Claude Code：只用于开发期、离线实验和 prompt 调试，不进入用户生产链路
AgentScope：不进 V1 主线，只保留为后置 spike
```

理由：

- V1 最重要的是验证专家团建议是否真的有价值，不是验证 agent framework。
- 当前专家团角色固定、流程固定、输出强结构化，自研轻量编排更合适。
- AgentScope 很贴近长期方向，但应该在轻量编排证明价值后再验证部署、事件流、恢复和成本。
- Claude Code/Agent SDK 很强，但更适合 coding/tool agent，不是当前倾诉纪要专家团的默认解。

## Advisor Lenses

- Musk lens: 先删复杂度。Claude Code 上生产看起来快，但隔离、并发、权限、审计和成本控制都会回到我们自己身上；AgentScope 看起来专业，但 V1 还没证明专家团值得一套完整 agent runtime。先造最小可工作的机器。
- Karpathy lens: demo 里让三个 agent 互相说话很容易，部署级可靠性难在输入快照、状态机、可恢复、结构化输出、失败样例和评估。轻量编排更容易看到每一次 LLM call 的输入、输出和锯齿状失败点。
- Taste lens: 用户不关心 runtime 名字，只关心过程是否可信、建议是否克制、最终交付是否清楚。V1 的体验重点是“总-过程-总”的可读性，不是技术炫技。
- Platform lens: runtime 必须嵌入 `user -> space -> recording -> job -> artifact` 的资源模型。先把资源边界和审计链路做扎实，再考虑替换底层 agent 框架。

## Practical Decision

当前最稳的工程路径：

```text
生产路径：自研轻量多 Agent 编排
实验路径：Claude Code 单机离线实验
框架验证：AgentScope 后置 spike
```

也就是说：

- 不把 Claude Code 当正式 backend runtime。
- 可以用 Claude Code 快速生成/评估专家团样例，帮助我们调 prompt 和输出结构。
- 正式服务端仍由自己的 API、DB、Queue、Job state 和权限体系承接用户请求。
- AgentScope 只有在轻量编排无法满足过程流、恢复、并发或角色隔离时再接入。

## Spike Plan

### 轻量编排 Spike

- 用 1 条真实或脱敏倾诉记录。
- 固定 3 个专家 + 裁判。
- 产出“总-过程-总”结构。
- 记录每一轮模型输入输出。
- 检查是否比单 prompt 更有价值。

### AgentScope Spike

- 部署最小 AgentScope Agent Service。
- 定义三个 SubAgentTemplate。
- Leader 创建团队并收敛结果。
- 观察事件流是否能自然映射到 App 的“过程”展示。
- 验证 Redis、session、stream、job resume 的复杂度。

这个 spike 不阻塞 V1。只有当 Slice 8 的轻量专家团已经跑通，并且真实使用暴露出过程流、恢复或角色隔离问题时，再启动。

## Decision

V1 不把专家团 runtime 绑定到任何大框架。

接受决策：

```text
ExpertAdviceRuntimeV1 = deterministic job state machine + role prompts + LLMProvider
```

Claude Code CLI 不作为用户生产 runtime。

AgentScope 不作为 V1 主线依赖。

服务端需要把专家团抽象成接口：

```text
ExpertAdviceRuntime
-> createJob(inputSnapshot)
-> runRounds(jobId)
-> streamProgress(jobId)
-> getArtifact(jobId)
-> cancelJob(jobId)
```

这样可以先用轻量编排实现，后续切换 AgentScope。

## Revisit Trigger

重新评估的触发条件：

- 自研编排难以恢复失败任务。
- 用户明显重视“过程流”，轻量编排展示不够自然。
- 专家角色需要自己的长期会话状态。
- 专家团需要使用复杂工具或外部资料。
- AgentScope spike 能明显降低长期维护成本。
