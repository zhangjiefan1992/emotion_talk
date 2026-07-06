# Real LLM Summary and Expert Team Verification

Date: 2026-07-06
Status: h5_local_remote_passed_ios_build_passed_remote_synced_client_manual_pending

## Scope

本次验证针对用户反馈的两个核心疑问：

- 纪要是否还只是快速拼接或固定模板。
- 专家团是否还在秒回 mock 数据。

## Fresh Verification Evidence

### Backend Unit Tests

Command:

```bash
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py
```

Result:

```text
Ran 18 tests in 0.184s
OK
```

### H5 Build

Command:

```bash
cd apps/web
npm run build
```

Result:

```text
DONE  Build complete.
```

### iOS Simulator Build

Command:

```bash
cd apps/ios
xcodebuild -scheme EmotionTalk -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```

Result:

```text
** BUILD SUCCEEDED **
```

### Remote Backend Smoke

Target:

```text
http://121.41.92.161/api
```

Flow:

```text
health -> create space -> create recording -> submit transcript
-> create summary -> create expert job -> poll expert job
```

Observed output:

```text
health 200 {'status': 'ok'}
transcript transcribed 3
summary completed llm_summary 用户发起远程验收测试，要求系统基于其输入生成纪要，并让专家团逐步讨论后给出结论。伴侣强调关注真实链路、过程展示及建议贴合度。
job-created running job_48009d12b4864858
job running 5
job running 6
job running 7
job running 9
job running 10
job running 11
job running 13
job running 14
job running 15
job running 17
job completed 20
artifact 本次对话为远程验收测试，用户与伴侣共同验证系统是否具备非模板化、动态推理能力。核心诉求是展示贴合输入的思考过程，而非获取结论。
```

### Remote H5 Entry

Target:

```text
http://121.41.92.161/
```

Observed via Chrome extension:

```text
title Emotion Talk
text  家的倾诉空间 / 0 条真实记录 / 还没有真实记录。点击右下角麦克风开始第一次倾诉。
bundle http://121.41.92.161/assets/pages-index-index.Bkaf9Aig.js
has_纪要=yes has_转写=yes has_专家团=yes has_running=yes has_api=yes
```

## Conclusion

- 服务端纪要已从 `dev_summary_stub` 改为真实 LLM 输出，`modelTrace.runtime=llm_summary`。
- 专家团接口已从同步秒回改为异步任务，创建时返回 `running`，随后逐步写入 events，最终 `completed`。
- 本次远程 smoke 的纪要和专家团 overview 都贴合测试输入，没有复用之前“人生方向”的固定建议。
- 远程 H5 入口加载正常，页面 chunk 已包含 `纪要 / 转写 / 专家团` 三 tab 和专家团轮询 API。

## Remaining Risks

- iOS 真机还需要用户再次人工验收录音、结束、三个 tab 展示。
- H5 页面入口、底部点击、空间管理入口已通过 Chrome 验证；录音能力仍取决于浏览器麦克风权限和协议环境。
- 远程容器已热更新并通过接口验证，但 Docker Hub 拉取基础镜像超时，正式镜像 rebuild 尚未成功。若后续执行 `docker compose up --force-recreate --build`，需要先完成镜像 rebuild。
- 本地 API 必须以 `PYTHONPATH=services/api/src` 启动；否则会加载旧安装包并导致空间接口 404。

## 2026-07-06 H5 Clickability And Space Management Addendum

### Remote Space API Smoke

Observed output:

```text
health {'status': 'ok'}
default 200 space_3bc10a2231034634 家的倾诉空间
duplicate 409
created 4
limit 409
current space_2a86b2329eb447aa ['健康']
recordings 1 空间切换验收记录
```

### Remote H5 Click Smoke

Target:

```text
http://121.41.92.161/
```

Evidence:

```text
initial: 家的倾诉空间 / 1 个空间 · 0 条真实记录
click 我的: 显示 空间管理 / 创建空间 / 当前
click 记录: 显示 最近记录
click 主题: 显示 还没有主题
console errors: []
```

## 2026-07-06 iOS Space Alignment Addendum

### iOS Build

Command:

```bash
cd apps/ios
xcodebuild -scheme EmotionTalk -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```

Result:

```text
** BUILD SUCCEEDED **
```

### Swift API Smoke Compile

Command:

```bash
cd apps/ios
swift build --product EmotionTalkAPISmoke
```

Result:

```text
Build of product 'EmotionTalkAPISmoke' complete!
```

### H5 Bottom Tab Click Verification

Observed via Codex Chrome Extension against:

```text
http://121.41.92.161/
```

Evidence:

```text
tabbar buttons: 4
click 我的: active=我的, visible=空间管理
click 记录: active=记录, visible=最近记录
click 主题: active=主题, visible=还没有主题
click 空间: active=空间, visible=空间画像
console errors: []
```

### Product Boundary Confirmed

- 每个用户会自动拥有一个默认空间。
- 用户可在 `我的` 管理空间、创建空间、切换当前空间。
- 当前不支持删除空间。
- 同一用户最多 5 个空间。
- 同一用户下空间不可重名。
- iOS 开始录音时使用当前空间，不再每次创建默认空间。

## 2026-07-06 Space List Normalization And Local H5 Retest

### Root Cause

本地 H5 “能点但空间数据不对”的根因不是前端点击失效，而是本地 `uvicorn emotion_talk_api.app:app` 进程加载了虚拟环境里的旧安装包，没有走当前源码目录 `services/api/src`，导致：

```text
GET /users/default_user/spaces -> 404
```

正确启动方式：

```bash
PYTHONPATH=services/api/src \
EMOTION_TALK_LLM_PROVIDER=deepseek \
.venv/bin/python -m uvicorn emotion_talk_api.app:app --host 127.0.0.1 --port 8000
```

### API Rule Verification

After restarting local API from current source:

```text
GET /users/default_user/spaces
count: 5
currentFirst: true
names: Swift 联调空间 / 默认倾诉空间 / 本地验收空间 / 家的倾诉空间 / test
```

The API now normalizes legacy polluted data at the response boundary:

- At most 5 visible spaces per user.
- Duplicate legacy space names are hidden from the product response.
- Current space is kept visible and sorted first.
- New creation still rejects duplicate names and rejects creation once 5 visible spaces exist.

### Local And Remote H5 Click Verification

Observed via Codex Chrome Extension:

```text
remote http://121.41.92.161/
click 我的 -> 空间管理 / 创建空间 / 当前
console errors: []

local http://localhost:5173/
click 我的 -> 空间管理 / 创建空间
console errors: []
```

Note:

- H5 uses browser-local `emotion_talk_owner_id`, not `default_user`; a fresh browser user correctly receives one default space.
- `default_user` data is mainly legacy smoke-test data and is now normalized before being returned.

### Current Build Verification

```text
services/api: Ran 18 tests ... OK
apps/web: DONE Build complete
apps/ios: ** BUILD SUCCEEDED **
```

### Remote Sync Verification

Docker Hub metadata lookup still timed out during image rebuild:

```text
python:3.12-slim: failed to resolve source metadata ... i/o timeout
```

Fallback used for the current acceptance server:

```text
docker cp services/api/src/emotion_talk_api/app.py emotion_talk-api-1:/app/src/emotion_talk_api/app.py
docker restart emotion_talk-api-1
```

Remote checks after restart:

```text
GET /api/health -> {"status":"ok"}

GET /api/users/default_user/spaces
count: 5
currentFirst: true
names:
- 家庭倾诉空间-公网验证
- 家的倾诉空间
- iOS smoke
- curl verbose
- 默认倾诉空间

GET /api/users/qa_space_<timestamp>/spaces
count: 1
name: 家的倾诉空间
current: true
```

Remote H5 after sync:

```text
click 我的 -> 空间管理 / 创建空间 / 当前
console errors: []
```

### Local H5 Space Interaction Regression

User-reported issue:

```text
H5 controls looked unclickable; space management was not obvious enough.
```

Root cause found:

- Local H5 did accept bottom-tab clicks.
- The failing path was `创建空间`: local API on `127.0.0.1:8000` was not running, so H5 entered `服务端未连接` and correctly blocked creation.
- The old create interaction used `window.prompt`, which is fragile across H5 / app / mini-program targets.

Fix:

- Start local API with current source path: `PYTHONPATH=services/api/src`.
- Replace `window.prompt` with an in-product inline create form under `我的 -> 空间管理`.
- Remove the H5 fake `emptySummary` fallback; summary tab now shows real summary or a true empty state.

Verification:

```text
services/api: Ran 18 tests ... OK
apps/web: DONE Build complete
H5 API proxy: GET /api/health -> {"status":"ok"}
Local API: PID 81714, GET /health -> {"status":"ok"}
```

Playwright browser verification:

```text
Flow: http://127.0.0.1:5173 -> 我的 -> 创建空间 -> 保存 -> 切换空间
Initial rows: 1
Rows after create: 2
New row count: 1
New row has switch action: true
Top title after switch: QA空间76644
Subtitle after switch: 2 个空间 · 0 条真实记录
Console issues: []
Screenshot: /tmp/emotion_talk_h5_space_qa.png
```

Remote sync and verification:

```text
Static H5 deployed to emotion_talk-web-1:/usr/share/nginx/html
GET http://121.41.92.161/api/health -> {"status":"ok"}

Flow: http://121.41.92.161 -> 我的 -> 创建空间 -> 保存 -> 切换空间
Initial rows: 1
Rows after create: 2
New row has switch action: true
Top title after switch: 远程空间46295
Subtitle after switch: 2 个空间 · 0 条真实记录
Console issues: []
Screenshot: /tmp/emotion_talk_remote_h5_space_qa.png
```

## 2026-07-06 LLM Key Failure Regression

Added backend regression coverage:

```text
POST /recordings/{recording_id}/summary-jobs without DEEPSEEK_API_KEY -> 503
POST /recordings/{recording_id}/expert-advice-jobs without DEEPSEEK_API_KEY -> 503
expertAdviceJobIds remains []
```

Result:

```text
Ran 18 tests in 0.184s
OK
```

## 2026-07-07 Remote Real LLM Runtime Check

Remote container configuration:

```text
provider=deepseek
heuristic_flag=UNSET
deepseek_key=SET
provider_class=DeepSeekProvider
GET /api/health -> {"status":"ok"}
```

Remote flow:

```text
health -> create space -> create recording -> submit transcript
-> create summary -> create expert job -> poll expert job
```

Observed result:

```text
summary status=200, duration=3.13s
summary modelTrace.runtime=llm_summary
summary chapters=4, keyPoints=4

expert job create status=200, duration=0.03s
expert job initial status=running, initial events=1
poll events grew: 5 -> 6 -> 7 -> 9 -> 10 -> 11 -> 13 -> 14 -> 15 -> 17 -> 20
expert final status=completed
expert final rounds=[1, 2, 3]
expert final suggestions=3
expert final artifact.modelTrace.runtime=lightweight_state_machine
recordingId=rec_56a8fe46a8c3493d
jobId=job_a342f0c6496145b7
```

Conclusion:

- Remote acceptance runtime is not using heuristic.
- Missing-key failure is covered by tests; configured remote runtime has a real DeepSeek key.
- Summary is generated by real LLM path.
- Expert advice is a real async job: create returns `running`, events increase over time, final artifact appears after polling.

## 2026-07-07 H5 Space Management Clickability Fix

Root cause:

- H5 renders uni-app `<button>` as `<uni-button>`, but several style and test selectors only targeted native `button`.
- The home segmented row had a static `我的` text, while the bottom tab also had `我的`, creating a confusing non-clickable target.
- The space row used a whole-row button with `设置当前空间` as inner text, making the action less explicit.
- Floating record/create actions overlapped the space management card on `我的`.

Fix:

- Converted the home segmented `我的` entry into a real button that opens space management.
- Added explicit space management affordances: current space, `n/5` quota, `创建空间`, and `设置当前空间`.
- Kept users on `我的` after changing the current space.
- Added stable test ids for H5 QA and extended CSS resets/selectors to `uni-button`.
- Hid floating actions on `我的` to avoid blocking the space management card.

Verification:

```text
GET http://localhost:5173/ -> page rendered
Click 我的 -> space-management-panel visible
Click 创建空间 -> input visible
Save new space -> rows 1 -> 2
Click 设置当前空间 -> current space updated, panel still visible
Console issues: none
Screenshots: /tmp/emotion-talk-h5-space-qa

npm run type-check -> OK
npm run build:h5 -> OK
python -m unittest services/api/tests/test_deliberation_service.py -> 18 tests OK
```

Remote sync:

```text
Static H5 deployed to emotion_talk-web-1:/usr/share/nginx/html
GET http://121.41.92.161/api/health -> {"status":"ok"}
GET http://121.41.92.161/ -> current built H5 shell

Flow: http://121.41.92.161 -> 我的 -> 创建空间 -> 保存 -> 设置当前空间
New space visible: true
Current space switched: true
Console issues: none
Screenshots: /tmp/emotion-talk-h5-space-qa/remote-*.png
```

## 2026-07-07 iOS Space Management Alignment

Fix:

- `我的` tab now explicitly shows current space, `n/5` quota, and the data scope explanation.
- Space rows use `当前空间` / `设置当前空间`, matching the H5 product wording.
- Creating a space uses `创建空间` wording and keeps the same max-5/no-delete boundary visible.
- `SpaceStore.createSpace` rejects duplicate names before calling the API; the server remains the source of truth.

Verification:

```text
swift test -> 5 tests, 0 failures
xcodebuild -project EmotionTalk.xcodeproj -scheme EmotionTalk -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build -> BUILD SUCCEEDED
```

## 2026-07-07 Expert Judge Failure Guard

Fix:

- Expert-team judge output must be valid JSON.
- Invalid judge output now fails the job through the existing `status=failed` path instead of being wrapped into a fake completed artifact.

Verification:

```text
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py -> 19 tests, OK
Remote http://121.41.92.161/api/health -> {"status":"ok"}
Remote container in-memory bad judge smoke -> {"status":"failed","message":"judge output must be valid JSON","overview":""}
```

## 2026-07-07 H5 Expert Timeline and Transcript Parser Guard

Fix:

- H5 expert tab now shows task progress and visible expert events while the job is still running.
- Completed H5 expert tab shows judge conclusion, process summary, and event timeline.
- Markdown transcript parser now accepts `00:00` minute-second timestamps, not only `00:00:00`.
- Empty transcript submissions now fail with 422 instead of allowing LLM summary/expert jobs to hallucinate from an empty input.

Verification:

```text
npm run type-check -> passed
npm run build:h5 -> DONE Build complete
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py -> 21 tests, OK
Chrome Extension local H5 flow:
  http://localhost:5174 -> existing real LLM summary record -> Expert tab -> Generate expert advice
  Running state showed: "讨论中 · 已生成 2 条过程"
  Completed state showed: "已完成 · 16 条过程", 裁判结论, 过程总结, and event timeline
  Console errors/warnings: none
```
