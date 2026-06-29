# API Contracts

Shared schema boundary between the iOS app and backend.

Current exported contract:

```text
packages/contracts/emotion-talk-api.openapi.json
```

Human-readable contract:

```text
docs/specs/v1-api-contract.md
```

Selected direction:

- Use OpenAPI as the iOS/server contract boundary.
- If the backend is Python/FastAPI, use Pydantic models to produce OpenAPI.
- Generate a Swift client only after the first API shape is stable enough to avoid churn.

Use this package when the first API shapes are stable enough to define:

- Resources: Space, Recording Session, Transcript, Summary, Chapter, Space Profile, Expert Advice Job.
- Realtime resources: ASR Session, Partial Transcript Event, Final Transcript Artifact.
- Request and response schemas.
- Error codes and retry semantics.
- Generated clients, if they become useful.

ASR contract should hide provider details from most app surfaces. The low-level iOS ASR adapter may know that it is using Bailian/DashScope iOS SDK and temporary API Keys, but product UI and recording state should only depend on project-level concepts:

- ASR Session.
- Partial Transcript Event.
- Final Transcript Artifact.
- ASR failure and fallback state.
