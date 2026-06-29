# Decision: 多 Agent 讨论服务端方案模式

Date: 2026-06-17
Status: accepted

## Context

这次 AgentScope spike 不是一次孤立实验。未来会有一类项目都需要：

- 多个 agent 从不同视角讨论。
- 讨论有多轮，有质疑、修正和收敛。
- 过程本身要给用户看。
- 最终由裁判或收敛器给出结果。
- 结果要通过 iOS、H5、Android、小程序等多端展示。
- 服务端要可部署、可回放、可审计、可替换 runtime。

因此要把当前调研沉淀成通用方案，而不是只写在 Emotion Talk 的专家团实现里。

## Options

### Option A: 每个项目单独写 agent 流程

优点：

- 起步快。
- 每个项目可高度定制。

问题：

- 很快重复实现 job、event、artifact、重试、取消、回放、成本控制。
- 多端 API 容易不一致。
- 后续切换 AgentScope、CrewAI、自研状态机时成本高。

### Option B: 客户端直接接多 Agent runtime

优点：

- 看似少一层服务端 wrapper。

问题：

- 客户端会被 AgentScope session、team、raw event、worker id 等概念污染。
- iOS/H5/Android/小程序很难保持一致。
- runtime 替换会影响所有端。
- 鉴权、权限、审计和安全边界不清晰。

### Option C: 抽象 Deliberation Job Service

优点：

- 产品 API 稳定。
- 多端只消费 job/event/artifact。
- AgentScope、CrewAI、自研状态机都被包在 adapter 后面。
- 过程展示、回放、成本、重试和安全边界统一。

问题：

- 需要多写一层产品服务。
- 需要认真设计 normalized event 和 artifact schema。

## Recommendation

采用 Option C：

```text
Product API
-> Deliberation Job Service
-> Runtime Adapter
-> Multi-Agent Runtime
```

当前默认 runtime adapter：

```text
AgentScopeAdapter
```

Fallback：

```text
LightweightStateMachineAdapter
CrewAIFlowAdapter
```

Claude Code CLI / Qoder CLI 继续作为内部研发、离线评估和代码实现工具，不直接进入用户生产 runtime。

## Advisor Lenses

- Musk lens: 不要每个项目重造 job/event/replay/cost 控制。把可复用的服务端骨架抽出来，具体项目只换输入、专家、轮次和 artifact。
- Karpathy lens: 真正难点不是让多个 agent 说话，而是可部署系统的边界：失败恢复、事件回放、锯齿状模型失败、人工控制点、成本上限和可审计输出。
- Taste lens: 用户看到的应该是清楚可信的讨论过程和克制结果，而不是 runtime 噪音。产品事件要被设计，不是直接转发 raw event。
- Platform lens: 多端复用 API contract，runtime 放在服务端内部。Redis、数据库、Docker 是可接受基础设施，核心风险是隔离、观测、恢复和成本。

## Decision

把“多 Agent 讨论给结果”定义为一类通用服务端方案，正式沉淀到：

```text
docs/architecture/multi-agent-deliberation-service-pattern.md
```

Emotion Talk 的专家团建议是该模式的第一个落地实例：

```text
recording
-> expert_advice_job
-> AgentScopeAdapter
-> normalized events
-> final advice artifact
```

未来类似项目优先复用同一套 server-side pattern，只替换：

- 输入快照构造器。
- 专家模板。
- 轮次计划。
- 裁判 prompt。
- safety policy。
- artifact schema。
- 客户端 renderer。

## Revisit Trigger

重新评估条件：

- AgentScope 无法稳定生产 normalized events。
- 多端事件恢复复杂度超过预期。
- 单 job 成本或时长不可控。
- 产品层 wrapper 变得比自研状态机更复杂。
- 未来出现更成熟的多用户 agent service，能直接满足 job/event/artifact 边界。

