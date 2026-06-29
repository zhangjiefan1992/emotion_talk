# 调研：AgentScope 官方示例可复用性

Date: 2026-06-16
Status: completed

## 结论

AgentScope 官方最接近 Emotion Talk 专家团的示例就是：

```text
https://github.com/agentscope-ai/agentscope/tree/main/examples/agent_service
```

它不是一个“情绪咨询专家团”业务示例，但基础设施形态非常接近：

```text
FastAPI Agent Service
-> RedisStorage
-> RedisMessageBus
-> LocalWorkspaceManager
-> TeamCreate / AgentCreate / TeamSay / TeamDelete
-> worker 独立 session
-> /sessions/{id}/stream SSE
-> Web UI 展示 leader / members / worker stream
```

我的判断：**可以基于这个官方 example 做 spike，但不要原样用于产品。**

我们应该从它复制服务启动骨架，然后删掉不需要的默认 MCP/browser 工具，换成 Emotion Talk 的专家模板、只读上下文工具和 `expert_advice_job` 适配层。

作者本人熟悉 Java 服务端、Docker 部署、Redis、MySQL 和数据库迁移，因此本项目不应把 Docker/Redis/数据库引入视为主要落地成本。AgentScope spike 的核心风险不是“多部署几个组件”，而是：

- 专家团流程能否被稳定约束。
- AgentScope 原生事件能否转成产品可读过程。
- 权限和工具边界能否收紧。
- 多用户、多空间、多任务是否能清晰隔离。
- 长任务失败、取消、重试和资源占用是否可控。

## 官方示例目录

本次浅克隆了官方仓库到临时目录：

```text
/private/tmp/agentscope-research
```

官方 `examples` 目录当前主要包含：

```text
examples/agent_service/README.md
examples/agent_service/main.py
examples/web_ui/
```

也就是说，官方没有另一个更贴近“专家会议”的单独业务 example。Agent Team 能力主要通过 `agent_service` 示例、官方 docs、service 源码和 web_ui 的 team 展示一起体现。

## examples/agent_service/main.py 做了什么

官方后端示例核心结构：

```python
from agentscope.app import create_app, SubAgentTemplate
from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import RedisStorage
from agentscope.app.workspace_manager import LocalWorkspaceManager
from agentscope.permission import PermissionContext, PermissionMode

app = create_app(
    storage=RedisStorage(host="localhost", port=6379),
    message_bus=RedisMessageBus(host="localhost", port=6379),
    workspace_manager=LocalWorkspaceManager(...),
    custom_subagent_templates=[...],
)
```

它默认加了：

- Redis 存储。
- Redis 消息总线。
- 本地 workspace。
- 一个 `explorer` 子智能体模板。
- 默认 `browser-use` MCP。
- 可选 AMap MCP。
- CORS。
- `uvicorn.run(..., port=8000, reload=True)`。

对我们有价值的是：

- `create_app` 服务骨架。
- `RedisMessageBus`。
- `SubAgentTemplate`。
- `PermissionContext` / `PermissionMode`。
- Team tools 的自动注入机制。

对我们 V1 spike 应该先删掉的是：

- `browser-use` MCP。
- AMap MCP。
- 文件/浏览器/搜索类工具。
- Web UI 依赖。

## Agent Team 官方机制

官方文档和源码确认：

- Agent Team 构建在 Agent Service 上。
- Leader 是用户对话会话。
- Worker 是独立 session，有自己的状态、工作区绑定与事件流。
- `TeamCreate` 创建 team，并把当前 session 标记为 leader。
- `AgentCreate` 创建 worker agent + worker session，并立即投递首个任务。
- `TeamSay` 把消息包装成 `HintBlock`，推入接收方 inbox，并 enqueue wakeup。
- `InboxMiddleware` 在下一次推理前清空 inbox，把 `HintBlock` 注入上下文，同时产出 `HintBlockEvent`。
- `GET /sessions/{session_id}/stream` 是 SSE，先 replay 缓冲事件，再订阅 live event。
- `POST /chat` 是 fire-and-forget，真正事件通过 SSE 回来。

这个机制和我们“用户可以离开页面，回来看到过程”的需求吻合。

## Web UI 给我们的启发

官方 Web UI 不需要复用，但它验证了前端消费模型：

- `GET /sessions/?agent_id=...` 返回 `SessionView[]`。
- 每个 `SessionView` 里可包含 `team`。
- `team` 内含：
  - `team.team.session_id`: leader session id。
  - `team.leader_agent`。
  - `team.members[]`。
  - 每个 member 包含 `agent` 和 `session_id`。
- 前端对每个 `(agentId, sessionId)`：
  - 先 `GET /sessions/{id}/messages` 拉历史。
  - 再 `GET /sessions/{id}/stream?agent_id=...` 订阅 SSE。
  - 发消息用 `POST /chat`，事件仍然通过 SSE 回来。

这对 iOS 的启发是：iOS 不需要理解 AgentScope 内部，只需要服务端把 AgentScope 的 session/member/event 映射成我们的 `expert_advice_job` 过程节点。

## 和 Emotion Talk 的映射

建议映射：

| Emotion Talk | AgentScope |
|---|---|
| `expert_advice_job` | leader session + team |
| `expert_round` | 一批 worker `HintBlockEvent` / reply events |
| Life Coach | `SubAgentTemplate(type="life_coach")` |
| Counselor | `SubAgentTemplate(type="counselor")` |
| Reality Strategist | `SubAgentTemplate(type="reality_strategist")` |
| Judge | leader agent 的最终收敛，或单独 `judge` worker |
| 过程展示 | session event stream + messages 落库 |
| 用户离开后回来 | messages + replay + 我们自己的 job event 表 |

我倾向于 spike 第一版让 **leader 扮演 Judge**：

```text
leader/judge
-> TeamCreate
-> AgentCreate(life_coach)
-> AgentCreate(counselor)
-> AgentCreate(reality_strategist)
-> 收集三位专家 report
-> TeamSay 发 round 2 互评
-> 收集修正
-> Judge 输出最终建议
```

原因是少一个 worker，链路更容易验证。等过程稳定后，再把 Judge 拆成独立模板。

## Spike 服务建议

建议新增一个最小 spike 服务：

```text
services/api/spikes/agentscope_expert_team/
  main.py
  prompts.py
  sample_job.json
  README.md
```

`main.py` 基于官方 `examples/agent_service/main.py` 改：

- 保留 `create_app`。
- 保留 `RedisStorage`。
- 保留 `RedisMessageBus`。
- 保留 `LocalWorkspaceManager`，但 workspace 目录放到本项目 `.tmp/agentscope-workspaces` 或 `/tmp`。
- 删除默认 MCP。
- 注册 3 个 `SubAgentTemplate`。
- 所有专家模板使用低权限模式。
- 覆盖 `get_current_user_id`，spike 阶段固定为 `local-dev-user`。
- 加一个我们自己的 API wrapper：`POST /expert-advice-jobs/spike`。

本地运行建议直接使用 Docker Compose 管理基础设施：

```text
agentscope api container
redis container
mysql or postgres container, if spike needs product-side event mirror
```

Spike 第一阶段只需要 Redis 即可跑通 AgentScope 原生链路；如果要同时验证 `expert_advice_job_event` 产品落库，可以加 MySQL 或 PostgreSQL。数据库选择不是本次 spike 的核心风险。

注意：当前源码 `create_app()` 参数名是 `custom_subagent_templates`，官方中文文档片段里出现过 `sub_agent_templates`。实现时以官方 example 和源码签名为准。

## 最小运行链路

不接 iOS，先用 REST/curl 验证：

```text
1. 启动 Redis
2. 启动 AgentScope spike backend
3. 创建 credential
4. 创建 leader agent
5. 创建 leader session
6. 打开 leader session SSE
7. POST /chat 触发专家团任务
8. 观察 leader/member session 创建
9. 分别订阅 worker session stream
10. 把事件转换为 ExpertAdviceJobEvent
```

如果用官方 API 原生走法：

```text
POST /credential
POST /agent
POST /sessions
GET  /sessions/{session_id}/stream?agent_id=...
POST /chat
GET  /sessions/?agent_id=...
GET  /sessions/{session_id}/messages?agent_id=...
```

如果用我们自己的产品 wrapper：

```text
POST /expert-advice-jobs/spike
GET  /expert-advice-jobs/{job_id}
GET  /expert-advice-jobs/{job_id}/events
```

wrapper 内部再调用 AgentScope 的 storage/service。

## 关键不确定性

### 1. Leader 是否能稳定按我们的固定流程跑

官方 Team 模式默认是让 leader 自己判断何时创建团队、创建谁、如何协调。我们的产品更适合“固定流程 + LLM 填内容”。

Spike 要验证：

- leader system prompt 能否稳定执行固定 3 轮。
- 是否需要我们在外层分阶段多次 `POST /chat` 驱动，而不是完全交给 leader 自主。

### 2. 过程事件能否干净转换为产品事件

AgentScope 原生事件粒度偏底层，包括 text block、tool call、hint block、custom event 等。

我们要转换为：

```text
expert_job_started
round_started
expert_message_added
judge_summary_started
final_advice_completed
expert_job_failed
```

### 3. Storage 是否先用 Redis，还是接业务数据库

官方文档说可以实现 `StorageBase` 替换为其他数据库。Spike 第一版不建议上来就写 MySQL/PostgreSQL 版 `StorageBase`，因为那会把框架验证和存储适配耦合在一起。

建议：

```text
Spike 1: RedisStorage 跑通 AgentScope 原生链路
Spike 2: RedisStorage + 我们自己的 job event mirror
Spike 3: 再判断是否实现 MySQL/PostgreSQL StorageBase 或双写
```

### 4. 工具权限边界

官方 example 默认有 workspace builtins、planning tools、schedule tools、team tools、MCP、skills。Emotion Talk 专家 worker 不应有文件写、shell、浏览器。

Spike 要验证：

- 是否能通过 workspace manager / permission context / extra_agent_tools 把专家工具限制到只读上下文。
- Team tools 必须保留。
- 其他工具尽量禁用。

## 现在是否值得直接用

值得。

但不是“直接把官方 service 当产品服务”。更准确是：

```text
复制官方 agent_service 的 service skeleton
-> 删除通用 coding/browser 工具
-> 注册 Emotion Talk 专家模板
-> 写 ExpertAdviceJob wrapper
-> 把 AgentScope event 转成产品 event
-> 跑 1-2 天 spike
```

如果 spike 成功，AgentScope 就是专家团 runtime 主线。

如果 spike 失败，失败也会很具体：要么是流程控制不稳，要么是事件映射太脏，要么是权限/隔离成本太高。那时再退回轻量状态机就更有底气。

## 资料来源

- AgentScope `examples/agent_service`: https://github.com/agentscope-ai/agentscope/tree/main/examples/agent_service
- AgentScope `examples/agent_service/main.py`: https://github.com/agentscope-ai/agentscope/blob/main/examples/agent_service/main.py
- AgentScope Agent Service docs: https://docs.agentscope.io/zh/v2/deploy/agent-service
- AgentScope Agent Team docs: https://docs.agentscope.io/zh/v2/deploy/agent-team
- AgentScope README: https://github.com/agentscope-ai/agentscope
- AgentScope Web UI example: https://github.com/agentscope-ai/agentscope/tree/main/examples/web_ui
