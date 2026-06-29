# Spec: AgentScope Expert Team Spike

Date: 2026-06-16
Status: accepted

## Goal

用 1-2 天验证 AgentScope Agent Team 是否适合作为 Emotion Talk V1 的专家团 runtime。

本 spike 不接真实用户数据，只使用脱敏样例，目标是验证 runtime 能否支撑“多轮专家讨论过程可展示、可落库、可恢复”的产品交付物。

## Background

专家团不是自动摘要，也不是普通聊天。它是用户主动点击后启动的慢思考流程：

```text
current recording snapshot
-> related history and space profile
-> expert team multi-round discussion
-> judge synthesis
-> final restrained advice
```

核心价值之一是过程：用户应该能看到专家如何互相质疑、修正和收敛。

官方基线参考 `examples/agent_service/main.py`，但 spike 只复用服务骨架：

- 保留 `create_app`、`RedisStorage`、`RedisMessageBus`、`LocalWorkspaceManager`。
- 删除官方示例默认的 browser / AMap MCP。
- 注册 Emotion Talk 自己的 3 个专家 `SubAgentTemplate`。
- 通过产品 wrapper 把 AgentScope session/event 映射成 `expert_advice_job`。

示例调研见：

```text
docs/research/2026-06-16-agentscope-official-examples-review.md
```

## Scope

本 spike 只验证：

- 一个 `expert_advice_job` 映射到一个 AgentScope team/session。
- 3 个 worker 专家独立运行。
- 专家之间能通过 Team Message 互相传递观点。
- Leader/Judge 能收敛最终结论。
- session event stream 能转换成 iOS 可展示的过程节点。
- team messages、worker outputs、judge result 能保存到我们自己的数据结构。
- 用户离开后，过程可以通过 replay 或本地落库重新展示。

## Non-Goals

- 不接真实用户音频、真实转写或真实画像。
- 不实现完整 iOS 页面。
- 不做正式鉴权系统。
- 不做生产部署。
- 不允许 shell/file write/network browsing 等高风险工具进入专家 worker。
- 不承诺 AgentScope 必然进入正式架构。

## Python Environment

本 spike 涉及 Python 时，必须使用当前工作区虚拟环境：

```text
/Users/jeff/Documents/emotion_talk/.venv
```

不得使用系统 Python 全局安装依赖。AgentScope、FastAPI、Redis client、测试依赖都应安装在该 `.venv` 内。

## Local Infrastructure

作者熟悉 Docker、Redis、MySQL 和服务端部署，因此本 spike 可以直接使用 Docker Compose 管理本地基础设施。Redis/数据库不是主要决策阻碍。

推荐分两步：

```text
Step 1: AgentScope API + Redis
Step 2: AgentScope API + Redis + MySQL/PostgreSQL event mirror
```

Step 1 只验证 AgentScope 原生 team/session/message/event/replay。Step 2 再验证我们的 `expert_advice_job_event` 产品落库。

## Test Scenario

使用一个脱敏倾诉样例：

```text
用户最近对职业转型、家庭沟通和长期规划产生困惑，希望获得克制但有帮助的建议。
```

固定 3 个专家：

- Life Coach: 聚焦目标、行动、节奏。
- Counselor: 聚焦情绪承接、心理安全、表达边界。
- Reality Strategist: 聚焦现实约束、资源、下一步实验。

固定 1 个 Judge：

- Judge: 只收敛，不强行制造结论；必须保留不确定性和安全边界。

## Expected Flow

```text
1. API 创建 expert_advice_job
2. AgentScope 创建 team/session
3. Leader 分发输入快照
4. Round 1: 三个专家分别初判
5. Round 2: 三个专家互相质疑
6. Round 3: 三个专家修正观点
7. Judge 汇总过程并生成最终建议
8. Safety pass 检查危险建议、诊断化表达和过度确定性
9. 保存过程和最终 artifact
```

## Output Contract

Spike 至少产出一个 JSON artifact：

```json
{
  "jobId": "sample-job-001",
  "status": "completed",
  "rounds": [
    {
      "round": 1,
      "title": "初判",
      "messages": [
        {
          "agent": "life_coach",
          "content": "..."
        }
      ]
    }
  ],
  "judge": {
    "summary": "...",
    "advice": ["..."],
    "uncertainties": ["..."],
    "safetyNotes": ["..."]
  }
}
```

## Success Criteria

AgentScope spike 成功的标准：

- 能稳定跑完 3 轮专家讨论和 Judge 汇总。
- 每一轮过程都能转换为结构化事件。
- 事件能按顺序保存并重放。
- 单个 worker 失败时，job 能记录失败原因，而不是静默丢失。
- 能清楚限制 worker 可用工具。
- 能把框架 session 映射回我们的 `space/recording/expert_advice_job`。
- 实现者能用不超过 30 分钟解释整个运行链路和失败路径。

## Failure Criteria

满足任一条件则回退到自研轻量状态机或 CrewAI Flow：

- AgentScope session/team 模型难以映射到业务资源。
- 事件流无法稳定重放。
- Team Message 难以落库或难以转成用户可读过程。
- 鉴权、隔离或部署成本明显超过 V1 承受范围。
- 框架隐藏了太多 prompt、状态或工具调用，导致输出不可审计。

## Safety Rules

- 不给医疗诊断。
- 不宣称心理治疗效果。
- 不输出极端行动建议。
- 遇到自伤、伤人、虐待、严重精神危机等信号时，只输出安全边界和求助建议。
- 最终建议必须克制、可撤回、可由用户自己判断。

## Decision After Spike

Spike 完成后写入：

```text
docs/research/agent-scope-spike-result.md
docs/decisions/YYYY-MM-DD-expert-agent-runtime-final.md
```

结论只允许三种：

- `accept AgentScope`
- `fallback to lightweight state machine`
- `fallback to CrewAI Flow`
