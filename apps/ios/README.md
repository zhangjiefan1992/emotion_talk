# iOS App

Legacy SwiftUI spike for the first product surface.

Status: as of 2026-07-01, the primary client line has moved to the uni-app implementation in `apps/web` so one codebase can target H5, iOS App, Android App, and mini programs. Keep this native SwiftUI target as a reference prototype and API smoke-test surface until it is explicitly revived.

## Selected Stack

- Native iOS app.
- SwiftUI.
- Swift Concurrency.
- iOS 17+ engineering baseline unless reach requirements force lower support.
- Observation for shared state where suitable.
- AVFoundation for microphone capture, local recording, and playback.
- Bailian/DashScope Paraformer iOS SDK behind a `RealtimeASRService`.

Initial responsibility:

- Start a live conversation recording from one obvious action.
- Capture microphone audio inside a trusted Space.
- Show realtime transcript while the user is speaking when the ASR session is healthy.
- Let the user end the session.
- Show final transcript, AI summary, chapters, and history links after automatic processing.
- Let the user view and correct the Space Profile.
- Let the user intentionally request Expert Advice.

Do not put backend storage assumptions directly in the UI. The app should depend on API contracts and local state models.

Realtime ASR notes:

- User-facing default is automatic realtime transcription.
- Default V1 live session target is about 45 minutes of in-app microphone recording.
- Do not expose Paraformer/Fun-ASR model selection in V1.
- Do not embed long-lived DashScope/Bailian API keys in the app.
- Preferred path: use the Bailian/DashScope iOS SDK with temporary API Keys issued by the API service.
- Prefer the narrower Paraformer realtime ASR SDK for V1 transcription.
- Treat Bailian's multimodal iOS SDK as a future option for voice-agent, full-duplex, TTS, image, or video interactions.
- Realtime proxy is a fallback, not the default.
- Temporary key TTL must be handled with rolling credentials or ASR segmentation.
- Local microphone recording is authoritative; realtime ASR can fail, reconnect, or restart without stopping recording.
- Transcript chunks need stable timestamp offsets so segmented ASR output can be stitched.
- When the user taps End, upload the MP3/AAC file to OSS through server-issued authorization, then start automatic final transcription + AI summary.
- If realtime transcription fails, keep recording and fall back to final-audio transcription.

First implementation spike:

- 45-minute foreground recording.
- Realtime transcript display.
- Temporary credential renewal or ASR segmentation.
- Final audio storage handoff.

## Current App Shell

The first SwiftUI shell lives in this Swift package:

```text
apps/ios/Package.swift
```

Targets:

```text
EmotionTalkCore  # API contract models, HTTP client, preview client
EmotionTalkApp   # SwiftUI app shell
```

Implemented V1 screens:

- Conversation tab with one primary Start action.
- Recording live state with timer, transcript rows, and End action.
- Completed recording detail with segmented tabs:
  - AI summary
  - Transcript metadata
  - Expert team
- Expert team timeline rendering:
  - context usage
  - judge conclusion
  - three rounds of expert output

Current app entry uses `EmotionTalkHTTPClient` by default and points to:

```text
http://127.0.0.1:8000
```

The shared Xcode scheme also sets:

```text
EMOTION_TALK_API_BASE_URL=http://127.0.0.1:8000
```

`PreviewEmotionTalkAPIClient` remains available for previews, isolated UI work, and tests.

Build:

```bash
cd apps/ios
swift build
```

Swift-to-backend smoke:

```bash
PYTHONPATH=services/api/src \
EMOTION_TALK_LLM_PROVIDER=heuristic \
.venv/bin/python -m uvicorn emotion_talk_api.app:app \
  --host 127.0.0.1 \
  --port 8000
```

In another terminal:

```bash
cd apps/ios
EMOTION_TALK_API_BASE_URL=http://127.0.0.1:8000 \
swift run EmotionTalkAPISmoke
```

Simulator verification after full Xcode is selected:

```bash
apps/ios/Scripts/verify-simulator.sh
```

The simulator script builds, installs, launches, captures a screenshot, and runs the UI flow test.

Known local verification note:

- `swift build` passes on this workspace after allowing SwiftPM user-cache access.
- `swift test` is currently blocked by the local CommandLineTools/XCTest setup: `xcrun --sdk macosx --show-sdk-platform-path` cannot resolve `PlatformPath`.
- Once Xcode command line tools are fixed with a full Xcode install/selection, run `swift test` to execute `EmotionTalkCoreTests`.
- Simulator install and launch require full Xcode because `xcodebuild` and `simctl` are not available from CommandLineTools alone.

Next implementation steps:

1. Select a full Xcode developer directory so `xcodebuild` and `simctl` are available.
2. Build and install `EmotionTalk.xcodeproj` on Simulator.
3. Start `services/api` locally and run through Start -> End -> Summary -> Expert Advice.
4. Add AVFoundation recording service behind a protocol.
5. Add Paraformer realtime ASR adapter behind a protocol.
6. Persist local draft session state so recording survives transient view reloads.
