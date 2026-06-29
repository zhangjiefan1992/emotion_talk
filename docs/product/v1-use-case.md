# V1 Use Case: Live Conversation Capture

## Primary User Flow

The core V1 scenario is a live in-app conversation, not importing an existing long recording file.

```text
User taps Start Conversation
-> iPhone microphone starts recording
-> ASR SDK starts realtime speech-to-text
-> app shows live transcript while the user is speaking
-> user may speak for about 45 minutes
-> user taps End
-> recording task ends
-> app enters automatic final transcription and AI summary processing
-> audio file is stored for later traceability and regeneration
-> user can intentionally request Expert Advice
```

## In Scope

- One obvious Start Conversation action.
- Microphone capture from the phone.
- Realtime ASR text shown in the app during the conversation.
- A realistic live session target around 45 minutes.
- User-controlled End action.
- Automatic final transcript generation after End.
- Automatic AI summary after final transcript is available.
- Recording file storage for later review, reprocessing, and traceability.
- User-triggered Expert Advice after the record exists.

## Out of Scope For The First Pass

- Importing arbitrary existing long audio files.
- Batch-only transcription as the main experience.
- User-facing ASR provider or model selection.
- Automatically generating Expert Advice without an explicit user action.
- Building full voice-agent / duplex AI conversation.

## Product Principle

Realtime transcript is live feedback. The final saved record is the product artifact.

The app should feel like AI 听记 during recording, then like a calm reflection workspace after recording.
