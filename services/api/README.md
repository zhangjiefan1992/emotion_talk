# API Service

Backend service for Spaces, recordings, processing jobs, and AI orchestration.

The backend is the product's source of truth. iOS captures audio and live transcript, but long-term data, minutes artifacts, history, profiles, and expert advice all live on the server side.

## Selected Stack

- API Service + Job Worker + Agent Runtime.
- Python + FastAPI is the preferred candidate if AgentScope becomes part of the expert-team runtime.
- PostgreSQL is the preferred relational metadata store.
- Redis is the preferred queue/message-bus candidate.
- Alibaba Cloud OSS is the preferred audio object store.
- OpenAPI is the iOS/server contract boundary.

Initial responsibility:

- Manage Spaces, members, sessions, and permissions.
- Accept audio uploads and create processing jobs.
- Store transcripts, summaries, chapters, history links, profiles, and advice artifacts.
- Orchestrate STT, summarization, profile updates, and user-triggered Expert Advice.
- Enforce safety boundaries and audit AI inputs/outputs.

## Realtime ASR Default

Default realtime speech recognition:

```text
ASR_PROVIDER=paraformer
ASR_MODEL=<selected-after-ios-asr-spike>
ASR_MODEL_CANDIDATES=paraformer-realtime-v2,paraformer-realtime-8k-v2
ASR_FALLBACK_PROVIDER=fun-asr
```

Reference implementation patterns come from `paike-helper`, especially its ASR whitelist, model config, elapsed-time metadata, and error handling.

Important product difference: `paike-helper` mainly records first and transcribes afterward. This product should support a live in-app microphone session: realtime transcription while the user speaks, then final audio/transcript persistence after the user taps End.

Do not expose ASR model selection to end users in V1. Keep it as server-side configuration and evaluation tooling.

Provider credentials must stay server-side. The preferred V1 path is:

```text
iOS requests ASR session
-> API creates Recording Session
-> API calls DashScope/Bailian credential endpoint with server secret
-> API returns temporary ASR config to iOS
-> iOS SDK connects directly to Bailian/DashScope realtime ASR
-> iOS receives realtime text and displays it
-> iOS submits transcript text/segments to API
```

Temporary API Keys are suitable for mobile apps, but they inherit the permissions of the generating key and have bounded TTL. Use a narrow permanent key where possible, short TTL, server-side session ownership checks, and per-user rate limits.

Long live conversations are the normal case, not an edge case. The API must support about 45-minute in-app microphone sessions through:

- rolling ASR credential issuance;
- ASR segment records with `startMs`, `endMs`, `chunkIndex`, provider metadata, and retry state;
- deterministic transcript stitching;
- final audio storage in OSS for traceability, regeneration, gap repair, and fallback transcription;
- rate limits scoped to Space, member, recording, and provider session.

After the client ends a session, the API starts automatic final transcription and AI summary jobs. Expert Advice is a separate user-triggered job, not part of automatic finalization.

Realtime proxy remains a fallback when direct temporary-key mode is insufficient for privacy, auditing, long-session renewal, or network reliability.

Bailian's multimodal iOS SDK also supports server-issued short-lived tokens and `AudioOnly` over `WebSocket`, but it is a broader realtime dialog stack. Keep it as a future candidate for voice-agent and duplex interactions instead of making it the default V1 transcription path.

## AI Providers

- Keep LLM calls behind provider interfaces.
- Default candidate: Bailian/Qwen for Chinese summary and advice workflows.
- Keep OpenAI-compatible provider support as a secondary path.
- Separate model configuration for summary, history linking, profile update, expert advice, and safety review.

## Storage Defaults

- Store audio in private OSS objects.
- Store metadata and artifact records in PostgreSQL.
- Do not expose public audio URLs.
- API should issue upload/download authorization scoped to Space membership.

## Expert Agent Runtime

- Start with a lightweight server-side multi-agent orchestrator: fixed roles, fixed rounds, judge convergence, safety review, structured output.
- Spike AgentScope because its Agent Team model maps well to leader/worker expert discussion.
- Do not use cloud-deployed Claude Code CLI as the default product runtime; Claude Code is stronger for coding agents than for a narrow, auditable emotional-reflection expert workflow.

## Current Runnable Capability

The first product-side backend slice is implemented under:

```text
services/api/src/emotion_talk_api/
```

It provides:

- Dev resources for iOS/H5 spike:
  - `Space`
  - `Recording`
  - `Transcript`
  - `SummaryJob`
  - `ExpertAdviceJob`
- SQLite persistence for local and single-server Docker deployment:
  - default app path: `.data/emotion_talk.sqlite3`
  - Docker path: `/data/emotion_talk.sqlite3`
- Dev-stub contracts for:
  - ASR temporary session configuration
  - OSS audio upload authorization
- DingTalk-style markdown transcript parsing.
- `DeliberationJob` service with fixed participants:
  - `life_coach`
  - `counselor`
  - `reality_strategist`
  - judge synthesis
- Normalized job events.
- Final advice artifact.
- History-aware expert advice context:
  - default `contextScope=current_only`
  - optional `contextScope=current_with_history`
  - returned `contextUsage` records exactly which history sources were used
- FastAPI endpoints:

```text
POST /spaces
GET  /spaces/{space_id}

POST /recordings
GET  /recordings/{recording_id}
POST /recordings/{recording_id}/transcript
POST /recordings/{recording_id}/audio-upload-authorizations

POST /asr-sessions
POST /recordings/{recording_id}/summary-jobs
POST /recordings/{recording_id}/expert-advice-jobs

GET  /expert-advice-jobs/{job_id}
GET  /expert-advice-jobs/{job_id}/events
GET  /expert-advice-jobs/{job_id}/artifact

POST /deliberation-jobs/from-markdown
```

OpenAPI contract:

```text
packages/contracts/emotion-talk-api.openapi.json
```

Human-readable iOS contract:

```text
docs/specs/v1-api-contract.md
```

- CLI runner:

```bash
PYTHONPATH=services/api/src \
.venv/bin/python -m emotion_talk_api.cli \
  "/path/to/transcript.md" \
  --output-dir outputs/deliberation/latest \
  --provider deepseek
```

Provider options:

```text
deepseek   # requires DEEPSEEK_API_KEY
heuristic  # offline wiring fallback; requires EMOTION_TALK_ALLOW_HEURISTIC=true
```

Generated files:

```text
job.json
advice.md
test-report.md
```

Run unit tests:

```bash
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py
```

Run with local SQLite:

```bash
PYTHONPATH=services/api/src \
EMOTION_TALK_LLM_PROVIDER=heuristic \
EMOTION_TALK_ALLOW_HEURISTIC=true \
EMOTION_TALK_DB_PATH=.data/local-dev.sqlite3 \
.venv/bin/python -m uvicorn emotion_talk_api.app:app --host 127.0.0.1 --port 8000
```
