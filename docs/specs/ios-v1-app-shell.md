# iOS V1 App Shell

Status: implemented as SwiftPM buildable shell

## Goal

Create the first iOS-facing product shell that matches the V1 API contract:

```text
Start Conversation
-> live recording state
-> transcript capture
-> automatic summary
-> user-triggered expert advice
-> expert timeline + judge result
```

## Scope

In scope for this slice:

- SwiftUI app shell.
- Native state flow for idle, starting, recording, processing, completed, and failed states.
- API contract models matching `docs/specs/v1-api-contract.md`.
- HTTP client shape for backend integration.
- Preview client for UI iteration.
- Expert advice timeline UI that displays `contextUsage`, three expert rounds, and judge artifact.

Out of scope for this slice:

- Real microphone recording.
- Real Paraformer SDK integration.
- Real OSS upload.
- Real backend persistence.
- App Store metadata.

## Files

```text
apps/ios/Package.swift
apps/ios/Sources/EmotionTalkCore/
apps/ios/Sources/EmotionTalkApp/
apps/ios/Tests/EmotionTalkCoreTests/
```

## Architecture

```text
EmotionTalkApp
-> SwiftUI screens
-> ConversationSession state
-> EmotionTalkAPI protocol
-> EmotionTalkHTTPClient or PreviewEmotionTalkAPIClient
-> services/api OpenAPI contract
```

UI depends on product concepts, not storage or provider internals.

## Context Rule

Expert advice starts with:

```text
contextScope = current_only
```

When the user chooses history:

```text
contextScope = current_with_history
```

The timeline must render `contextUsage`, so the user can see whether the advice used only the current recording or also historical records.

## Verification

Passed:

```bash
cd apps/ios
swift build
```

Blocked locally:

```bash
swift test
```

Reason: the current CommandLineTools/XCTest setup cannot resolve macOS SDK `PlatformPath`. The tests are present and should be run after selecting a full Xcode toolchain.

## Next Step

The Xcode project wrapper is now present. Next, select a full Xcode developer directory, run the shell on Simulator, start the local FastAPI backend, and replace preview ASR with an AVFoundation recording service.
