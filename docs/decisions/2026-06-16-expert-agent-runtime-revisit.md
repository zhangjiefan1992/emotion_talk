# Decision: 专家团 Runtime 重新判断

Date: 2026-06-16
Status: accepted

## Context

2026-06-15 的初版判断偏向“自研轻量多 Agent 编排，AgentScope 后置 spike”。经过进一步研究 CrewAI、Qoder CLI/SDK、Claude Code CLI/SDK/Agent Teams，以及重新核对 AgentScope Agent Team / Agent Service / Message & Event 官方文档后，需要修正这个判断。

用户强调的核心不是“多个专家名字”，而是：

- 专家团内部有多轮讨论。
- 专家之间需要互相质疑、修正、收敛。
- 过程本身是重要交付物。
- 用户可以离开页面，完成后回来查看。
- 服务端要支持多用户、多空间、任务状态、过程回放和最终 artifact。

这已经超过“几次 LLM call 的轻量状态机”。

2026-06-16 追加背景：作者本人是多年 Java 研发，熟悉服务器部署、Docker、Redis、MySQL 等基础设施。对本项目而言，引入 Redis / 数据库 / Docker Compose 不应被高估为主要成本；它更像可接受的服务器资源占用和部署编排问题。后续评估 AgentScope 时，重点应放在流程可控性、事件映射、权限隔离、资源消耗和失败恢复，而不是泛泛地把“多一个 Redis 或数据库”视为阻碍。

## Options

### Option A: 自研轻量状态机

优点：

- 最快起步。
- 输出 schema 最好控制。
- 没有框架学习成本。

问题：

- 如果要做独立 worker、消息路由、事件流、回放、恢复、并发和过程展示，很快会重造半个 AgentScope。
- 初期看似轻，后期维护成本可能更高。

### Option B: CrewAI

优点：

- Flow / Crew / Task 抽象清楚。
- 适合 Python AI workflow。
- 有 checkpoint、logs、callbacks、structured output。

问题：

- 更像任务编排框架，不是一等公民的多用户 agent service。
- 没有天然的 worker session、inbox、wakeup、Redis message bus 和 SSE replay 模型。
- 适合作为 fallback 或非专家团 workflow，不适合作为专家团首选 runtime。

### Option C: Claude Code CLI / Claude Agent SDK

优点：

- Agent SDK 强，工具执行、subagents、MCP、sessions、permissions 完整。
- Agent Teams 支持独立 Claude Code sessions、lead、mailbox、shared task list。
- 很适合内部研发、代码审查、prompt 离线评测。

问题：

- Agent Teams 仍是 experimental，默认关闭。
- 官方明确存在 session resumption、task coordination、shutdown behavior 等限制。
- team state 存在本机 `~/.claude/teams` 和 `~/.claude/tasks`。
- 核心心智仍是 coding sessions，不是产品内 `space/recording/job` 多租户 runtime。

### Option D: Qoder CLI / Qoder Agent SDK

优点：

- CLI 和 SDK 都支持 coding agent、MCP、worktree、stream-json、工具权限。
- SDK 支持 TypeScript/Python、subagents、custom MCP tools、streaming output。

问题：

- 本机 `qodercli 0.1.11` 与官方文档有能力差异。
- 本地状态和日志依赖 `~/.qoder`。
- 认证依赖 Qoder PAT 或本地 qodercli 登录。
- 更适合研发工具链，不适合用户生产专家团 runtime。

### Option E: AgentScope Agent Team

优点：

- Agent Team 建在 Agent Service 之上。
- Leader 是用户会话，Worker 是独立 session。
- Worker 有自己的状态、工作区绑定和事件流。
- Team Message 经 Redis-backed message bus 路由。
- Message bus 支撑 session lock、replay log、inbox queue、wakeup signal。
- Session stream 可用于前端过程展示和回放。
- 更贴近“专家团会议过程”这个产品交付物。

问题：

- 引入 FastAPI + Redis + AgentScope runtime，但在作者当前能力模型下，这不是主要阻碍。
- 默认鉴权和 workspace 隔离需要改造。
- 最终 schema、安全复检、裁判收敛仍要我们自己做。

## Recommendation

接受修正后的路线：

```text
V1 专家团 runtime: AgentScope 前置 spike
Fallback: 自研轻量状态机 / CrewAI Flow
Internal tools: Claude Code CLI, Qoder CLI
```

具体含义：

- 不再把 AgentScope 放到 Post-V1。
- 在正式开发专家团生产能力前，先做 1-2 天 AgentScope spike。
- Spike 成功，则专家团 runtime 主线转向 AgentScope。
- Spike 失败，退回自研轻量状态机，并可局部参考 CrewAI Flow。
- Claude Code/Qoder CLI 只作为内部研发和离线评测工具，不直接接用户数据和生产任务。

## Advisor Lenses

- Musk lens: 不要重造已经存在的复杂机制。如果我们需要消息总线、worker session、事件流和回放，自研“轻量”很快变成自研框架。先用最小 spike 验证 AgentScope，不要先承诺长期自研。
- Karpathy lens: 真正难点不是让 3 个专家说话，而是 deployment reliability：会话隔离、事件恢复、失败样例、过程可重建、输出 schema、人工控制点。AgentScope 在这些基础设施上更接近可部署系统。
- Taste lens: 用户看到的是“专家团过程是否可信”，不是框架名。框架选择必须服务可读过程和慎重建议。
- Platform lens: AgentScope 仍需嵌入我们自己的账号、Space、Recording、Job、业务数据库、审计和权限体系；不能让框架资源模型反过来主导产品资源模型。Docker/Redis/MySQL 这类基础设施不是作者的主要成本，真正要验证的是运行时边界、资源占用、观测性和可恢复性。

## Decision

V1 执行顺序调整为：

```text
1. 先做 AgentScope Expert Team spike
2. 验证 team/session/message/event/replay/落库
3. 成功后接入正式 ExpertAdviceJob
4. 失败再退回自研状态机或 CrewAI Flow fallback
```

## Revisit Trigger

重新评估条件：

- AgentScope 无法稳定映射 `space -> recording -> expert_advice_job`。
- AgentScope 事件流难以转成 iOS 可读过程。
- Worker 隔离或鉴权改造成本过高。
- AgentScope 运行时资源占用、失败恢复或权限隔离超过 V1 承受范围。
- AgentScope 输出 schema 和 safety guardrail 不可控。

## Research

详见：

```text
docs/research/2026-06-16-agent-runtime-tooling-comparison.md
```
