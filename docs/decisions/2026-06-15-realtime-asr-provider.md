# Decision: Realtime ASR Provider

Date: 2026-06-15
Status: accepted

## Context

The product needs live or near-live transcription during a recording session. This is different from the batch ASR path used in `paike-helper`, where the client records audio, uploads the finished file, and the backend polls DashScope for a transcription result.

For Emotion Talk, realtime transcription matters because:

- It makes the recording feel like AI 听记 rather than a passive recorder.
- It lets users see whether the capture is working before the conversation ends.
- It creates earlier text artifacts for progressive summary and chapter generation.
- It reduces the feeling that the app is a black box after recording.

## Options

### Option A: Bailian/DashScope Paraformer Realtime

Use Alibaba Cloud Bailian/DashScope Paraformer realtime speech recognition as the default realtime ASR path.

Initial model candidates:

```text
paraformer-realtime-v2
paraformer-realtime-8k-v2
```

Why this is the default:

- It matches the current intended vendor direction.
- Paraformer is already familiar from the `paike-helper` implementation family.
- The final model choice must be validated against real iPhone microphone audio.
- `paraformer-realtime-8k-v2` remains a candidate, but 8k audio may be better suited to telephone-style input than native phone microphone capture.
- It should provide a clearer migration path from local prototypes to a production iOS flow than a fully self-hosted model.

### Option B: Fun-ASR

Use Fun-ASR as a fallback or comparison path.

Why keep it:

- It gives us a second ASR candidate for accuracy and latency evaluation.
- It is useful if Paraformer performs poorly on a specific voice, environment, or cost envelope.
- It keeps the ASR boundary honest: the product depends on an `ASRProvider`, not one hard-coded vendor call.

## Reference From paike-helper

Relevant local reference:

```text
/Users/jeff/WeChatProjects/paike-helper/server/src/services/asr.js
/Users/jeff/WeChatProjects/paike-helper/server/src/worker.js
/Users/jeff/WeChatProjects/paike-helper/miniprogram/utils/speechRecognizer.js
```

Reusable ideas:

- Keep ASR model selection behind a whitelist.
- Use environment configuration for the default model.
- Return `rawText`, `asrModel`, and elapsed time for observability.
- Separate voice capture from downstream parsing/summarization.
- Preserve fallback paths and meaningful error messages.

Important difference:

- `paike-helper` is mostly a batch transcription flow: record first, upload audio, then poll for a final result.
- Emotion Talk V1 needs a live in-app ASR session: the phone microphone streams audio, the app shows realtime text while the user speaks, and the final transcript/audio are persisted after the user taps End.

## Recommendation

Adopt Paraformer realtime as the default ASR provider, with Fun-ASR retained as an internal fallback/evaluation provider.

The user-facing iOS app should not expose ASR model selection in V1. Users should only see recording, live transcript, and processing states.

## Implementation Direction

Use an internal provider boundary:

```text
ASRProvider
-> startSession(spaceId, recordingId)
-> sendAudioFrame(bytes, timestamp)
-> receivePartialTranscript()
-> finishSession()
-> return finalTranscript + timing + provider metadata
```

Initial provider config:

```text
ASR_PROVIDER=paraformer
ASR_MODEL=<selected-after-ios-asr-spike>
ASR_MODEL_CANDIDATES=paraformer-realtime-v2,paraformer-realtime-8k-v2
ASR_FALLBACK_PROVIDER=fun-asr
```

Provider credentials must live on the server side. The iOS app must not embed long-lived DashScope/Bailian API keys.

Official Bailian/DashScope documentation supports a temporary API Key path for untrusted environments such as browsers and mobile apps. The backend should use the permanent `DASHSCOPE_API_KEY` to create temporary API Keys and return only temporary credentials to the iOS app.

The iOS SDK can then initialize realtime ASR with:

```json
{
  "url": "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
  "apikey": "st-****",
  "device_id": "<app-user-or-device-id>",
  "service_mode": "1"
}
```

Temporary API Key facts from official docs:

- Default validity is 60 seconds.
- `expire_in_seconds` can set TTL in the range `[1, 1800]` seconds.
- Temporary API Keys inherit the full permissions of the permanent key that generated them.
- Temporary API Keys cannot be manually deleted; they expire automatically.

Important iOS SDK nuance:

- The general temporary API Key API documents configurable TTL up to 1800 seconds.
- The Paraformer iOS SDK quickstart describes temporary API Keys as having a fixed 60-second validity and says they must be reacquired after expiry.
- The iOS SDK `nui_dialog_start` parameters allow passing an updated temporary API Key when the configured `apikey` has expired.
- This does not prove that one uninterrupted realtime ASR task can run for an about 45-minute live conversation without renewal, reconnect, or segmentation.

Therefore the V1 implementation must not depend on a single temporary credential or a single uninterrupted provider connection for the whole live conversation.

## V1 Live Conversation Requirement

The core V1 use case is live recording inside the app. A user taps Start Conversation, speaks into the phone microphone, sees realtime ASR text in the app, speaks for about 45 minutes, taps End, and then the app enters automatic final transcription and AI summary processing.

A 1800-second credential ceiling is not an acceptable product ceiling for this live session.

Required V1 behavior:

- Local microphone recording is the source of truth for the saved record.
- Realtime ASR is live feedback for the user and an early transcript source.
- The app must continue recording even when realtime ASR credentials expire, the WebSocket drops, or the provider task fails.
- The ASR layer must support rolling temporary credentials and task segmentation.
- Transcript segments must carry `recordingId`, `asrSegmentId`, `chunkIndex`, `startMs`, `endMs`, provider metadata, and retry state so the final transcript can be stitched deterministically.
- The iOS SDK config should enable heartbeat/long-connection behavior where supported, but still assume mobile network interruption.
- After the user taps End, the audio file must be stored and automatic final transcription + AI summary must start.
- If live ASR cannot be recovered cleanly, the stored audio must trigger post-recording transcription.
- Expert Advice starts only after the user explicitly requests it.

Preferred implementation shape:

```text
User taps Start Conversation
-> iOS microphone recording starts
-> API creates Recording Session
-> API issues short-lived ASR credential
-> iOS starts ASR segment 1 while local recording continues
-> app shows realtime transcript text
-> before expiry or on ASR error, iOS requests a fresh credential
-> iOS starts ASR segment N with timestamp offset
-> user taps End
-> iOS uploads/stores final audio
-> API stores segment transcripts and stitches final transcript by offset
-> API starts AI summary job
-> final audio remains available for traceability, regeneration, and fallback transcription
```

Validation required before production:

- Whether the iOS SDK can update the temporary API Key during a running task or only before starting a new task.
- Whether the provider has a maximum realtime task duration independent of credential TTL.
- How much transcript gap appears when closing one ASR task and starting the next.
- Whether a small overlap window improves stitching accuracy.
- Battery, thermal, memory, and background-mode behavior for about 45 minutes of foreground recording on real iPhones.

## Multimodal iOS SDK Check

Aliyun Bailian also provides a mobile iOS SDK for realtime multimodal interaction. It is useful, but it is a broader product surface than V1 transcription.

Confirmed capabilities from the official iOS SDK documentation:

- `MultiModalDialog` supports audio/video end-to-end realtime interaction.
- It supports `WebSocket` and `RTC` links.
- It supports `AudioOnly` and `AudioAndVideo` modes.
- For audio interaction, the documentation recommends `WebSocket` because it connects faster and has lower performance requirements.
- Upstream audio supports `pcm` and `opus` for speech recognition.
- Interaction modes include `Push2Talk`, `Tap2Talk`, and `Duplex`.
- Mobile clients can use a short-lived Token issued by the server instead of embedding a long-lived API Key.

Interpretation:

- This SDK is attractive for future voice-agent, coach conversation, full-duplex interruption, LiveAI, TTS, image, or video interactions.
- It is not the cleanest default for V1 AI 听记, where the core artifact is transcript-first recording plus downstream summary, chapters, history links, and intentional advice.
- V1 should keep the narrower Paraformer realtime ASR SDK as the primary path, then revisit the multimodal SDK when the product needs actual AI voice conversation instead of recording and transcription.

## Advisor Lenses

- Musk lens: Do not build our own ASR. Delete user-facing model choice. Start with one default provider and keep only one fallback path.
- Karpathy lens: The hard part is not the happy path demo, but partial-result stability, long conversation drift, noisy rooms, diarization, and recovery after network drops.
- Taste lens: The user should see a calm live transcript, not technical ASR controls.
- Platform lens: Token/session creation belongs on the server. Cloudflare can still be a candidate for edge/API pieces, but the current V1 direction favors a server-centered architecture with OSS, database, jobs, and agent runtime.

## Decision

Accepted:

- Default realtime ASR: Bailian/DashScope Paraformer realtime speech recognition.
- Default model: pending iPhone microphone ASR spike. Compare `paraformer-realtime-v2` and `paraformer-realtime-8k-v2` before hardcoding.
- Fallback/evaluation: Fun-ASR.
- No user-facing model picker in V1.
- Keep ASR behind a provider interface.
- Preferred iOS realtime path: iOS SDK connects directly to Bailian/DashScope using backend-issued temporary API Keys.
- Realtime proxy is a fallback path, not the default.
- Multimodal iOS SDK is a future candidate for voice-agent and duplex conversation, not the V1 transcription default.
- V1 must support about 45 minutes of live in-app microphone recording with realtime ASR display, rolling credentials/segmentation as needed, and stored-audio fallback transcription.

## iOS Realtime ASR Architecture

Preferred V1 path:

```text
iOS App
-> POST /api/asr-sessions
-> API creates Recording Session and initial temporary DashScope API Key
-> iOS SDK connects directly to wss://dashscope.aliyuncs.com/api-ws/v1/inference
-> iOS streams audio for ASR segment 1 while local recording continues
-> app displays realtime transcript text
-> iOS renews credential or starts ASR segment N when needed
-> iOS receives partial/final transcript events per segment
-> user taps End
-> iOS uploads/stores final audio
-> iOS sends segment transcript metadata to API
-> API stitches final transcript and starts summary/history/profile jobs
-> final uploaded audio remains available for traceability, regeneration, and fallback transcription
```

Why this is preferred:

- Lowest latency path for realtime transcription.
- Avoids running our own long-lived audio WebSocket proxy in V1.
- Keeps permanent provider secret off the device.
- Matches official iOS SDK guidance.

Proxy fallback path:

```text
iOS App
-> API realtime proxy
-> Bailian/DashScope WebSocket
```

Use proxy only if direct temporary-key mode fails product or compliance needs, for example:

- We need server-side access to every audio frame for audit, filtering, storage, or speaker processing.
- Token TTL and long-recording renewal cannot be handled cleanly in iOS.
- Provider direct connection is unstable on real mobile networks.
- App Store, enterprise policy, or privacy review requires all AI traffic to go through our backend.
- We need to hide provider metadata or enforce stricter per-session quota controls.

Open implementation detail: the general temporary API Key API supports up to 1800 seconds, while the iOS SDK quickstart describes 60-second temporary API Keys. Treat both as implementation constraints, not product limits. A 45-minute live conversation requires renewal or segmentation, and this must be tested with the iOS SDK before final implementation.

## Revisit Trigger

Revisit this decision if:

- Paraformer realtime latency or accuracy is poor in real family conversation recordings.
- Provider pricing changes materially.
- The provider cannot support the required iOS credential model safely.
- 8k audio loses too much detail for the product's real recording environment.
- Fun-ASR or another provider clearly outperforms Paraformer on our evaluation set.
