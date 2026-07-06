# Real LLM Summary and Expert Team Task List

Date: 2026-07-06
Status: h5_remote_passed_ios_build_passed_client_manual_pending

## Goal

把当前“录音、实时转写已跑通”的版本补齐为可验收闭环：

```text
录音 -> 实时/最终转写 -> 真实 AI 纪要 -> 真实专家团多轮讨论 -> iOS/H5 一致展示
```

## Current Service Capability

已完成：

- `GET /health`: 服务健康检查。
- `POST /spaces`: 创建倾诉空间。
- `GET /users/{owner_id}/spaces`: 获取用户空间列表，并自动确保默认空间。
- `POST /users/{owner_id}/current-space`: 切换当前空间。
- `GET /spaces/{space_id}/recordings`: 获取当前空间下的记录列表。
- `POST /recordings`: 创建录音记录。
- `POST /recordings/{recording_id}/transcript`: iOS 提交实时转写最终文本。
- `POST /recordings/{recording_id}/audio-transcriptions`: 服务端可用百炼对音频做补偿转写。
- `POST /recordings/{recording_id}/summary-jobs`: 使用 LLM 生成“总-过程-总”纪要。
- `POST /recordings/{recording_id}/expert-advice-jobs`: 创建异步专家团任务，后台逐步写入 events，最终产出 artifact。
- `GET /recordings/{recording_id}`: 获取记录详情。
- `GET /expert-advice-jobs/{job_id}`、`/events`、`/artifact`: 查询专家团结果。

仍需验收：

- iOS 真机完整链路还需要用户再次点击录音、结束、查看 `纪要 / 转写 / 专家团`。
- H5 录音链路仍受浏览器录音权限和部署协议影响，需要单独验证。
- 远程服务器当前使用热更新容器完成验证；Docker Hub 超时导致镜像 rebuild 暂未完成。

## Tasks

### Task 1: 服务端 LLM 配置必须显式可验收

Status: remote_passed

Files:

- Modify: `services/api/src/emotion_talk_api/providers.py`
- Modify: `services/api/src/emotion_talk_api/app.py`
- Test: `services/api/tests/test_deliberation_service.py`
- Docs: `services/api/README.md`

Done when:

- 默认 provider 是 `deepseek`。
- `heuristic` 只允许 `EMOTION_TALK_ALLOW_HEURISTIC=true` 时启用。
- 缺 `DEEPSEEK_API_KEY` 时，纪要和专家团接口返回明确 503，不返回固定内容。
- 远程验收环境不再配置 `EMOTION_TALK_LLM_PROVIDER=heuristic`。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py
curl -i http://121.41.92.161/api/health
```

Needs human:

- 如果远程没有可用 DeepSeek key，需要提供或确认使用当前已给过的 key 配置到服务器环境变量。

### Task 2: 纪要改成真实 LLM “总-过程-总”

Status: remote_passed

Files:

- Modify: `services/api/src/emotion_talk_api/app.py`
- Test: `services/api/tests/test_deliberation_service.py`
- Contract: `packages/contracts/emotion-talk-api.openapi.json`

Done when:

- `POST /recordings/{recording_id}/summary-jobs` 调用 LLM。
- 输出结构仍兼容 `SummaryArtifact`：`overview` 是第一个总，`chapters` 是过程，`keyPoints`/末尾章节承接最后的总。
- `modelTrace.runtime` 不再是 `dev_summary_stub`。
- LLM JSON 解析失败时返回 502，不写入假纪要。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py
```

### Task 3: 专家团改成真实异步任务

Status: remote_passed

Files:

- Modify: `services/api/src/emotion_talk_api/models.py`
- Modify: `services/api/src/emotion_talk_api/deliberation.py`
- Modify: `services/api/src/emotion_talk_api/app.py`
- Test: `services/api/tests/test_deliberation_service.py`

Done when:

- `POST /recordings/{recording_id}/expert-advice-jobs` 只创建 job 并返回 `status=running`。
- 服务端后台逐步写入事件：创建、上下文冻结、第一轮、第二轮、第三轮、裁判收敛、完成。
- `GET /expert-advice-jobs/{job_id}` 可看到中间态和最终态。
- 失败时 `status=failed`，事件里有失败原因，不返回假建议。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py
```

### Task 4: iOS 三 tab 重排

Status: local_build_passed_manual_pending

Files:

- Modify: `apps/ios/Sources/EmotionTalkCore/EmotionTalkModels.swift`
- Modify: `apps/ios/Sources/EmotionTalkApp/RecordingDetailView.swift`
- Modify: `apps/ios/Sources/EmotionTalkApp/ExpertAdviceTimelineView.swift`
- Modify: `apps/ios/Sources/EmotionTalkApp/ConversationSession.swift`

Done when:

- `纪要` tab 只展示 AI 纪要。
- `转写` tab 展示逐句转写、时间戳、说话人和录音元信息。
- `专家团` tab 展示任务进度、多轮讨论、裁判结论。
- 没有结果时展示明确 loading/empty/error，不展示假内容。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk/apps/ios
xcodebuild -scheme EmotionTalk -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```

Needs human:

- 真机验收时需要用户携带数据线或保持 Xcode 可连接设备。

### Task 5: H5 与 iOS 页面一致

Status: remote_h5_entry_passed_recording_manual_pending

Files:

- Modify: `apps/web/src/pages/index/index.vue`
- Modify: `apps/web/src/api.ts`
- Modify: `apps/web/src/types.ts`

Done when:

- H5 也有 `纪要 / 转写 / 专家团` 三 tab。
- H5 不再展示假 summary/advice。
- H5 与 iOS 使用同一套 API 字段和状态语义。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk/apps/web
npm run build
```

### Task 6: 部署同步与完整验收

Status: backend_remote_smoke_passed_client_manual_pending

Files:

- Modify: `docs/status/2026-07-06-real-llm-summary-and-expert-team-verification.md`

Done when:

- 本地测试通过。
- 远程服务器代码、镜像、环境变量与本地一致。
- 远程 `/api/health` 通过。
- 远程真实接口完成一次：录音记录、转写、LLM 纪要、专家团 job、events、artifact。
- iOS 真机和 H5 都完成同一条链路验收。

Verify:

```bash
curl -fsS http://121.41.92.161/api/health
```

Needs human:

- 真机点录音、结束、查看三个 tab。
- 如果域名/HTTPS 没完成，H5 录音能力以 localhost 或真机 iOS 优先验收。

### Task 7: H5 点击可用与空间管理闭环

Status: remote_passed_recording_permission_manual_pending

Files:

- Modify: `services/api/src/emotion_talk_api/app.py`
- Modify: `services/api/tests/test_deliberation_service.py`
- Modify: `apps/web/src/api.ts`
- Modify: `apps/web/src/types.ts`
- Modify: `apps/web/src/pages/index/index.vue`

Done when:

- H5 底部 `空间 / 记录 / 主题 / 我的` 可点击并切换当前页面状态。
- 每个用户默认有一个空间。
- `我的` 里可以查看空间、创建空间、切换当前空间。
- 当前不支持删除空间。
- 同一用户最多 5 个空间。
- 同一用户下空间不可重名。
- 切换空间后，首页记录列表显示当前空间的记录。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk
.venv/bin/python -m unittest services/api/tests/test_deliberation_service.py
cd apps/web && npm run build
```

Needs human:

- H5 麦克风权限仍需要用户在浏览器里授权。

### Task 8: iOS 空间管理与当前空间录音对齐

Status: local_build_passed_manual_pending

Files:

- Modify: `apps/ios/Sources/EmotionTalkCore/EmotionTalkModels.swift`
- Modify: `apps/ios/Sources/EmotionTalkCore/EmotionTalkAPI.swift`
- Modify: `apps/ios/Sources/EmotionTalkCore/PreviewEmotionTalkAPI.swift`
- Modify: `apps/ios/Sources/EmotionTalkApp/AppView.swift`
- Modify: `apps/ios/Sources/EmotionTalkApp/ConversationHomeView.swift`
- Modify: `apps/ios/Sources/EmotionTalkApp/ConversationSession.swift`
- Modify: `apps/ios/Sources/EmotionTalkAPISmoke/main.swift`

Done when:

- iOS 不再在每次开始录音时创建默认空间。
- iOS 录音、记录列表、空间切换都使用同一个当前空间。
- iOS 有 `空间 / 记录 / 主题 / 我的` 四个入口，与 H5 的核心语义一致。
- `我的` 里可以查看空间、创建空间、切换当前空间。
- iOS build 通过。

Verify:

```bash
cd /Users/jeff/Documents/emotion_talk/apps/ios
xcodebuild -scheme EmotionTalk -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```
