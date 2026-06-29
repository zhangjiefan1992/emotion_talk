# AgentScope Spike Implementation Log

Date: 2026-06-16
Status: validated spike

## What Was Implemented

Added a local AgentScope spike under:

```text
services/api/spikes/agentscope_expert_team/
```

Files:

- `docker-compose.yml`: Redis + MySQL local infrastructure.
- `main.py`: AgentScope FastAPI service using RedisStorage, RedisMessageBus, LocalWorkspaceManager, and three Emotion Talk expert templates.
- `prompts.py`: leader/judge prompt and expert worker prompt.
- `run_spike.py`: HTTP driver for creating credential, leader agent, session, and optionally triggering chat.
- `sample_job.json`: anonymized sample job.
- `requirements.txt`: pinned local spike dependencies.
- `.env.example`: local configuration reference.

## Infrastructure

Docker Compose successfully started:

```text
emotion-talk-agentscope-redis  -> 127.0.0.1:16379
emotion-talk-agentscope-mysql  -> 127.0.0.1:13306
```

Redis uses `16379` because local `6379` was already occupied.

## Python Environment

Created and used only:

```text
/Users/jeff/Documents/emotion_talk/.venv
```

Installed:

```text
agentscope[full]==2.0.2
uvicorn==0.49.0
httpx==0.28.1
```

## Verification

Passed:

- Python compile check for spike files.
- `main.py` imports and creates the FastAPI app.
- API starts when allowed to access local Docker Redis.
- `GET /healthz` returns configured Redis/workspace/templates.
- `GET /credential/schemas` returns AgentScope provider schemas.
- `GET /agent/` returns an empty agent list initially.
- `run_spike.py` setup-only mode creates:
  - credential
  - leader agent
  - leader session
- `GET /sessions/?agent_id=...` confirms the session persisted to Redis.

Not yet run:

- Nothing blocking the local spike. A real DeepSeek-backed run completed after the initial setup-only verification.

## DeepSeek Verification

2026-06-16 晚上用临时环境变量注入 DeepSeek key，完成了一次端到端真实调用。key 没有写入仓库文件。

Run result:

- Provider: `deepseek-chat`
- AgentScope API: `http://127.0.0.1:18000`
- Redis-backed session persisted successfully.
- SSE event stream saved to `services/api/spikes/agentscope_expert_team/.tmp/last-events.json`.
- Event file size: about 1.28 MB.
- Event count: 4433.

Observed event counts:

```text
CUSTOM: 8
EXCEED_MAX_ITERS: 1
HINT_BLOCK: 13
MODEL_CALL_END: 31
MODEL_CALL_START: 31
REPLY_END: 3
REPLY_START: 3
TEXT_BLOCK_DELTA: 1647
TEXT_BLOCK_END: 17
TEXT_BLOCK_START: 17
TOOL_CALL_DELTA: 2502
TOOL_CALL_END: 32
TOOL_CALL_START: 32
TOOL_RESULT_END: 32
TOOL_RESULT_START: 32
TOOL_RESULT_TEXT_DELTA: 32
```

What this proves:

- AgentScope can serve as the local multi-agent runtime foundation.
- DeepSeek can drive AgentScope's tool-calling loop well enough for the current spike.
- The event stream is rich enough to map into product-side progress UI: started, model thinking, tool call, expert hint/process, result, exceeded iteration, done.
- The final session context includes a judge synthesis with overview, restrained suggestions, uncertainty, and safety boundary.

What this also exposes:

- The default loop can run too long and produced one `EXCEED_MAX_ITERS`, so production must cap rounds and cost explicitly.
- The first script waited for lowercase `reply_end`, while AgentScope emits uppercase `REPLY_END`; this was fixed.
- Default raw event logging was too noisy; `run_spike.py` now prints milestones and a final event summary by default, with `AGENTSCOPE_SPIKE_VERBOSE_EVENTS=1` available for deep debugging.

## Next Step

Turn the spike into a thin product-side service:

- define `expert_advice_job`, `expert_advice_job_event`, and `expert_advice_result`;
- map AgentScope raw events into stable product events;
- enforce max rounds, max runtime, max token/cost budget, and idle timeout;
- persist the final judge result separately from raw events;
- add a Docker image for the AgentScope service after the product event contract is stable.

## Generalized Pattern

This spike has been promoted from a one-off Emotion Talk experiment into a reusable server-side pattern for future products that need multi-agent deliberation and multi-client delivery.

Reference architecture:

```text
docs/architecture/multi-agent-deliberation-service-pattern.md
```

Accepted decision:

```text
docs/decisions/2026-06-17-multi-agent-deliberation-service-pattern.md
```
