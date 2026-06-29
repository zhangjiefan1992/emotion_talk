# AgentScope Expert Team Spike

This spike validates whether AgentScope Agent Team can power Emotion Talk's expert advice flow.

## Local Infrastructure

Start Redis and MySQL:

```bash
docker compose -f services/api/spikes/agentscope_expert_team/docker-compose.yml up -d
```

Redis is used by AgentScope for storage and message bus in the first spike.
It is exposed on `127.0.0.1:16379` to avoid conflicting with an existing local Redis on `6379`.

MySQL is reserved for the product-side `expert_advice_job_event` mirror. It is intentionally started early because local Docker/database operations are not a major cost for this project.

## Python

Use only the workspace virtual environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install "agentscope[full]" uvicorn
```

Do not install Python dependencies globally.

## Start API

```bash
.venv/bin/python services/api/spikes/agentscope_expert_team/main.py
```

The API listens on:

```text
http://127.0.0.1:18000
```

Check health:

```bash
curl -s http://127.0.0.1:18000/healthz
```

## Setup-Only Verification

This creates an AgentScope credential, leader agent, and session without calling an LLM:

```bash
DASHSCOPE_API_KEY=dummy \
AGENTSCOPE_SPIKE_SETUP_ONLY=1 \
.venv/bin/python services/api/spikes/agentscope_expert_team/run_spike.py
```

## Full Expert Team Run

Set one real provider key:

```bash
export DASHSCOPE_API_KEY=...
# or DEEPSEEK_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY
```

Then run:

```bash
.venv/bin/python services/api/spikes/agentscope_expert_team/run_spike.py
```

Useful knobs:

```bash
AGENTSCOPE_SPIKE_TIMEOUT_SECONDS=180
AGENTSCOPE_SPIKE_IDLE_AFTER_REPLY_SECONDS=10
AGENTSCOPE_SPIKE_VERBOSE_EVENTS=1
```

Events are written to:

```text
services/api/spikes/agentscope_expert_team/.tmp/last-events.json
```

## Verified Provider

2026-06-16: `deepseek-chat` completed an end-to-end local run through AgentScope's HTTP API, Redis-backed storage, Redis message bus, and SSE event stream.

The run proved:

- leader agent, credential, and session creation work;
- DeepSeek can drive AgentScope tool calls;
- the flow emits product-usable event types such as `REPLY_START`, `HINT_BLOCK`, `TOOL_CALL_*`, `TOOL_RESULT_*`, `EXCEED_MAX_ITERS`, and `REPLY_END`;
- raw events can be persisted into `.tmp/last-events.json` for later mapping into `expert_advice_job_event`.

The run also exposed one product risk: unconstrained multi-agent discussion can run long and hit `EXCEED_MAX_ITERS`. Production needs explicit round limits, idle timeout, cost ceiling, and a judge-level completeness check.

## Next

The first runnable target should prove:

- create a leader session;
- create three expert workers through AgentScope team tools;
- exchange team messages;
- subscribe to session events;
- map raw AgentScope events into product-level expert job events.
