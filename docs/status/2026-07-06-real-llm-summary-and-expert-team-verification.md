# Real LLM Summary and Expert Team Verification

Date: 2026-07-06
Status: backend_remote_passed_client_manual_pending

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
Ran 14 tests in 0.142s
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
- H5 需要再用浏览器验收页面入口和视觉一致性；录音能力取决于浏览器权限和协议环境。
- 远程容器已热更新并通过接口验证，但 Docker Hub 拉取基础镜像超时，正式镜像 rebuild 尚未成功。若后续执行 `docker compose up --force-recreate --build`，需要先完成镜像 rebuild。
