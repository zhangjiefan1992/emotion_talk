# V1 构建顺序

Status: working plan

## Goal

把当前产品和技术选型变成第一条可用闭环的实现顺序：

```text
Start Conversation
-> live transcript
-> End
-> store audio
-> final transcript
-> AI summary
-> user-triggered Expert Advice
```

## Slice 0: Project Skeleton

- Create `services/api` as a FastAPI project candidate.
- Add OpenAPI generation.
- Add health check.
- Add local/dev environment config.
- Create `packages/contracts` as contract documentation / generated client target.
- Keep deployment config minimal.

Done when:

- API runs locally.
- `/health` returns a stable response.
- OpenAPI document can be generated.

## Slice 1: Core Resources

- Define Space.
- Define Recording Session.
- Define Recording status lifecycle.
- Define Audio Object metadata.
- Define ASR Segment metadata.
- Define Summary artifact.
- Define Expert Advice Job artifact.

Done when:

- API can create a dev Space.
- API can create a Recording Session.
- API can return Recording detail with empty artifacts.

## Slice 2: Audio Storage Path

- Add private OSS audio object layout.
- Add API endpoint for upload authorization.
- Add API endpoint to finalize audio upload.
- Store duration, size, mime type, object key, and checksum if available.

Done when:

- A client can create a recording session.
- A local test file can be uploaded and attached to the recording.
- No public audio URL is exposed.

## Slice 3: ASR Credential Path

- Add endpoint to create an ASR session credential.
- Backend uses permanent DashScope/Bailian key.
- iOS receives only temporary ASR config.
- Store ASR session metadata without exposing permanent secrets.

Done when:

- API can mint a temporary ASR credential in dev.
- Credential response shape is stable enough for iOS spike.

## Slice 4: iOS Recording Spike

- Create SwiftUI app shell.
- Add Start Conversation / End flow.
- Record local microphone audio.
- Show recording timer and basic state.
- Save local audio file.

Done when:

- A 45-minute foreground recording can complete on a real iPhone.
- The app remains responsive.
- The file can be handed off for upload.

## Slice 5: Realtime ASR Spike

- Integrate Paraformer iOS SDK behind `RealtimeASRService`.
- Show live transcript text.
- Test temporary credential renewal or ASR segmentation.
- Compare `paraformer-realtime-v2` and `paraformer-realtime-8k-v2` on iPhone microphone audio.

Done when:

- Live transcript appears during recording.
- ASR interruptions do not stop local recording.
- We can choose the first production ASR model.

## Slice 6: Automatic Processing

- Add post-recording job.
- Stitch ASR segments into final transcript.
- Run automatic AI summary.
- Store summary and chapters.
- Return processing status to iOS.

Done when:

- Ending a recording eventually produces transcript + summary.
- iOS can display processing, success, and failure states.

## Slice 7: Recording Detail UI

- Build native detail screen inspired by AI 听记 patterns.
- Tabs: transcript, AI summary, chapters.
- Audio playback.
- Timestamp-to-transcript linkage candidate.

Done when:

- A completed recording is useful to review without Expert Advice.

## Slice 8: AgentScope Expert Team Spike

- Deploy minimal AgentScope Agent Service.
- Create one Leader and three Worker expert roles.
- Pass one脱敏 recording transcript + AI summary as input snapshot.
- Let workers exchange Team Messages for at least two rounds.
- Let Judge/Leader converge into final advice.
- Subscribe to event stream and map events to a product-readable process log.
- Persist raw events and normalized expert rounds into our database shape.

Done when:

- Worker sessions, Team Messages, event stream, and replay are verified.
- We know whether AgentScope can become the expert-team runtime.
- We know what custom auth, workspace isolation, and persistence work remains.

## Slice 9: Expert Advice Job

- Add user-triggered Expert Advice endpoint.
- Freeze input snapshot.
- Use the selected runtime from Slice 8.
- Store process and final advice artifact.
- iOS shows job progress and completed result.

Done when:

- Expert Advice is clearly separate from automatic summary.
- User can leave and return to the completed artifact.
- Fallback path is documented if AgentScope is not selected.

## First Spike Priority

Start with Slice 0, Slice 3, Slice 4, and Slice 5 in tight loop.

Reason: the biggest unknown is whether realtime ASR can support the intended live iPhone session cleanly. Backend metadata can evolve, but the product fails if live capture feels unreliable.
