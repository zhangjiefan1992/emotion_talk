# iOS Backend Smoke Report

Date: 2026-06-24
Status: Swift client to local backend passed; Simulator install blocked by local Xcode setup

## Goal Checked

验证 iOS 侧契约 client 是否能真实打通服务端第一条链路：

```text
Space
-> Recording
-> ASR Session
-> Transcript
-> Summary
-> Expert Advice Job
-> Events
-> Artifact
```

## Backend Command

```bash
PYTHONPATH=services/api/src \
EMOTION_TALK_LLM_PROVIDER=heuristic \
.venv/bin/python -m uvicorn emotion_talk_api.app:app \
  --host 127.0.0.1 \
  --port 8000
```

## Swift Client Command

```bash
cd apps/ios
EMOTION_TALK_API_BASE_URL=http://127.0.0.1:8000 \
swift run EmotionTalkAPISmoke
```

## Result

```text
spaceId=space_f6a952d16166494e
recordingId=rec_9e77792b0a434ab1
asrSessionId=asr_75611d5dd9a643f8
recordingStatus=transcribed
summaryStatus=completed
adviceStatus=completed
contextScope=current_only
eventCount=20
suggestionCount=2
```

## Backend Evidence

```text
POST /spaces
POST /recordings
POST /asr-sessions
POST /recordings/{recordingId}/transcript
POST /recordings/{recordingId}/summary-jobs
POST /recordings/{recordingId}/expert-advice-jobs
GET  /expert-advice-jobs/{jobId}/events
GET  /expert-advice-jobs/{jobId}/artifact
```

All returned `200 OK`.

## Build Evidence

Passed:

```bash
cd apps/ios
swift build
```

Also passed:

```bash
PYTHONPATH=services/api/src .venv/bin/python -m unittest discover services/api/tests
```

## Simulator Blocker

Current machine has only CommandLineTools selected:

```text
/Library/Developer/CommandLineTools
```

Blocked commands:

```text
xcodebuild -list -project apps/ios/EmotionTalk.xcodeproj
```

Error:

```text
xcode-select: error: tool 'xcodebuild' requires Xcode,
but active developer directory '/Library/Developer/CommandLineTools'
is a command line tools instance
```

```text
xcrun simctl list devices available
```

Error:

```text
xcrun: error: unable to find utility "simctl", not a developer tool or in PATH
```

## Next Verification After Xcode Is Available

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcodebuild -list -project apps/ios/EmotionTalk.xcodeproj
xcrun simctl list devices available
```

Then build for Simulator:

```bash
xcodebuild \
  -project apps/ios/EmotionTalk.xcodeproj \
  -scheme EmotionTalk \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  build
```

Then install and launch:

```bash
APP_PATH="$(find ~/Library/Developer/Xcode/DerivedData -path '*Build/Products/Debug-iphonesimulator/EmotionTalk.app' -print -quit)"
xcrun simctl bootstatus booted
xcrun simctl install booted "$APP_PATH"
xcrun simctl launch booted com.jeff.emotiontalk
```

Automated script:

```bash
apps/ios/Scripts/verify-simulator.sh
```

This script starts the local backend, builds the app, installs it into the selected Simulator, launches it, captures a first-screen screenshot, and runs the UI test:

```text
EmotionTalkUITests/testRecordingSummaryAndExpertAdviceFlow
```

Current environment result:

```text
Full Xcode is required for Simulator verification.
Current developer directory: /Library/Developer/CommandLineTools
```

Expected first screen:

```text
Tab: 倾诉
Primary button: 开始
```

Expected flow with local backend running:

```text
开始
-> 录音中
-> 模拟转写
-> 结束
-> 纪要详情
-> 专家团
-> 生成专家团建议
-> 裁判结论 + 三轮专家时间轴
```
