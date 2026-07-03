# Emotion Talk 当前进展与模块边界

Date: 2026-06-28
Status: active validation

## 当前结论

项目已经具备“服务端 + iOS + H5”的第一版闭环骨架。远程服务端到百炼实时 ASR 已打通，iOS Simulator 通过本地 SSH tunnel 已完成真实麦克风录音、实时转写、自动纪要闭环。真机因为当前没有数据线，本轮未重新验收。

远程公网入口：

```text
API base: http://121.41.92.161/api
Health:   http://121.41.92.161/api/health
```

`emotalk.xyz` 已购买并配置 A 记录，但大陆 ECS 使用域名访问会被 ICP 备案拦截；域名不作为当前真机验收路径。

当前模拟器验收入口使用本地 tunnel：

```text
Local API base: http://127.0.0.1:8002/api
Tunnel:         127.0.0.1:8002 -> 121.41.92.161:80
```

2026-06-29 更新：

- 设计目标仍然是 iOS 通过百炼/DashScope iOS SDK 直连实时 ASR，服务端签发临时凭证。
- 当前代码不是该最终设计；当前代码使用 iOS -> 本服务端 WebSocket -> 服务端 DashScope Python SDK -> 百炼 ASR 的 realtime proxy 方案。
- 这个 proxy 方案只作为真机链路 spike/兜底路径，不应被误认为最终 iOS SDK 直连方案。
- 已修复当前 proxy 链路的两个连接问题：Nginx WebSocket Upgrade 代理头、API 容器缺少 `websockets` 依赖。
- 远端已验证 `ws://121.41.92.161/api/asr/realtime` 可以建立 WebSocket 连接。

2026-07-03 更新：

- 服务端 `WS /asr/realtime` 已支持 `model`、`sample_rate` 参数，默认使用 `paraformer-realtime-v2` 和 16k PCM。
- 已用真实百炼/DashScope 调用验证远程实时 ASR：`ws://121.41.92.161/api/asr/realtime?sample_rate=16000&model=paraformer-realtime-v2` 可返回 transcript event。
- 当前 Mac 的 Foundation/URLSession 访问公网 HTTP/HTTPS 会出现 `NSURLErrorDomain -1005 The network connection was lost`；`curl`、Python 正常。这会导致 iOS Simulator/App 直接访问 `http://121.41.92.161/api` 失败。
- 临时验收路径改为 SSH tunnel：`127.0.0.1:8002 -> 121.41.92.161:80`，App 访问 `http://127.0.0.1:8002/api`。
- 在 iPhone 17 Pro Simulator 上已完成真实麦克风验收：开始录音后，Mac 麦克风采集系统播放语音，iOS App 将 16k PCM 通过 WebSocket 发送到服务端，服务端调用百炼实时 ASR，App 实时展示转写，点击结束后提交 transcript 并生成自动纪要，进入详情页可看到转写片段。
- `testLiveMicrophoneRecordingCreatesSummary` 作为真实麦克风验收测试保留，但默认跳过；需要手动打开时要保证 tunnel 已启动，并临时开启测试。

## 服务端已支持

代码位置：

```text
services/api/
```

已实现能力：

- `GET /health`: 服务健康检查。
- `POST /spaces`: 创建倾诉空间。
- `GET /spaces/{space_id}`: 读取空间。
- `POST /recordings`: 创建录音记录。
- `GET /recordings/{recording_id}`: 读取录音记录。
- `POST /recordings/{recording_id}/transcript`: 提交客户端已有转写文本。
- `POST /recordings/{recording_id}/audio-upload-authorizations`: 生成音频上传授权占位，并关联 `audioObject`。
- `POST /recordings/{recording_id}/audio-transcriptions`: 接收 base64 音频，调用 DashScope/百炼批量 ASR，生成 transcript。
- `POST /asr-sessions`: 创建 ASR 会话占位。
- `WS /asr/realtime`: 接收 iOS 发送的 16k PCM，调用 DashScope/百炼实时 ASR，并通过 WebSocket 返回转写事件。
- `POST /recordings/{recording_id}/summary-jobs`: 基于 transcript 生成自动纪要。
- `POST /recordings/{recording_id}/expert-advice-jobs`: 基于 transcript + 历史上下文生成专家团建议。
- `GET /expert-advice-jobs/{job_id}`、`/events`、`/artifact`: 返回专家团过程和最终产物。

服务端部署：

- 使用 `docker-compose.yml` 部署 `api` 和 `web` 两个容器。
- 远程服务器公网 IP：`121.41.92.161`。
- API 通过 Web 容器的 `/api` 反向代理暴露。
- 服务端容器内使用 SQLite 文件存储开发数据。
- 远程已配置 `BAILIAN_API_KEY`，用于百炼/DashScope ASR。

当前服务端边界：

- 服务端负责数据、AI 处理、ASR provider 调用、专家团过程和 artifact。
- 客户端不直接理解 AgentScope、DashScope task、存储实现等内部细节。
- 生产 OSS 上传还没有接入，目前 `audio-upload-authorizations` 是 dev stub。
- 没有账号、权限、空间成员、多用户隔离。
- 没有 HTTPS。
- 当前 realtime proxy 已具备 WebSocket 代理能力，但不是最终推荐的 V1 iOS ASR 形态。
- `/asr-sessions` 仍是 dev stub，没有真正签发百炼/DashScope 临时凭证。

## iOS 已支持

代码位置：

```text
apps/ios/
```

已实现能力：

- SwiftUI 原生 App 壳。
- `EmotionTalkHTTPClient` 调用服务端 REST API。
- API client 已验证能保留 base path，例如 `http://121.41.92.161/api`。
- Xcode scheme 当前设置：

```text
EMOTION_TALK_API_BASE_URL=http://127.0.0.1:8002/api
```

- `AppConfiguration.realtimeASRURL(for:)` 已把 REST base 转换为：

```text
ws://121.41.92.161/api/asr/realtime
```

- `Info.plist` 已配置麦克风权限说明。
- `Info.plist` 已为 `121.41.92.161`、`127.0.0.1`、`localhost` 配置 HTTP ATS 例外。
- 真机麦克风录音使用 `AVAudioEngine`。
- 录音过程中写本地 `.caf` 文件。
- 录音过程中把音频转换为 16k PCM，发送给实时 ASR WebSocket。
- 如果实时转写没有产出文本，结束录音后会把本地音频 base64 发给服务端批量 ASR 兜底。
- 结束后提交 transcript，生成 summary。
- 用户可主动触发专家团建议。

已验证：

- `swift test` 通过。
- 新增测试覆盖 `http://121.41.92.161/api -> ws://121.41.92.161/api/asr/realtime`。
- iPhone 17 Pro Simulator 真实麦克风 + 百炼实时转写 + 自动纪要 UI 验收通过。
- Xcode 真机签名、开发者模式、信任开发者已经由用户推进完成。

当前 iOS 风险：

- `AppConfiguration.apiBaseURL` 当前默认指向 `http://121.41.92.161/api`，这是为了真机 IP 验收的开发期默认值；备案/HTTPS 完成后应替换为正式配置。
- `RealtimeASRClient` 当前吞掉 WebSocket 接收和发送错误，UI 上不容易区分 REST 失败、WebSocket 失败、ASR provider 失败。
- Mac/iOS Simulator 直接访问公网 IP 的 URLSession 当前会失败；本地模拟器验收需通过 `127.0.0.1:8002` tunnel，真机验收应优先使用 HTTPS 域名或继续定位当前网络环境下的 Foundation 连接问题。
- 真机 `failed to connect` 的服务端 WebSocket 代理层已修复并验证；下一步如果仍失败，应查看 App 实际错误和手机网络访问。

## H5 已支持

代码位置：

```text
apps/web/
```

已实现能力：

- React/Vite H5 原型。
- 首页、记录详情、转写、纪要、专家团建议等主要交互壳。
- 通过 `/api` 调用服务端：
  - health
  - space
  - recording
  - ASR session
  - submit transcript
  - summary job
  - expert advice job
- Docker 镜像使用 Nginx 托管静态页面，并反向代理 `/api` 到服务端。
- 浏览器支持 `getUserMedia` 和 `MediaRecorder` 时可尝试录音。

当前 H5 边界：

- H5 在 HTTP/IP 环境下不是当前真实录音验收路径；浏览器会因非安全上下文限制麦克风。
- H5 当前没有接入实时 ASR WebSocket。
- H5 当前会在不满足真实录音条件时进入模拟转写。
- H5 主要用于交互稿、信息架构和产品流程验证，不作为本轮真机录音主路径。

## 当前真机失败的正确排查顺序

不要再从签名、信任、开发者模式反复猜。下一轮按下面顺序查：

1. 在 iPhone Safari 打开 `http://121.41.92.161/api/health`。
   - 能看到 `{"status":"ok"}`，说明手机网络到服务器通。
   - 不能打开，先查手机网络、ECS 安全组、防火墙、运营商网络。

2. 确认 App 实际启动时使用的 base URL。
   - 目标值必须是 `http://121.41.92.161/api`。
   - 不能只依赖 Xcode scheme；如果需要手机桌面手动启动，也要把 Debug 默认值改成公网 IP 或做可见配置。

3. 在 iOS 启动阶段拆分 REST 连接。
   - 先单独请求 `/health`。
   - 再请求 `/spaces`。
   - 再请求 `/recordings`。
   - 不要一上来就把麦克风、WebSocket、ASR 混在一起。

4. 修正并验证 WebSocket 代理。
   - 如果走 `ws://121.41.92.161/api/asr/realtime`，Nginx 必须转发 `Upgrade` 和 `Connection`。
   - 或者临时让 iOS WebSocket 直接连 `ws://121.41.92.161:8000/asr/realtime`，但这需要开放 8000 端口，不推荐作为长期路径。

5. 实时 ASR 单独验收。
   - WebSocket 能连上。
   - iOS 能发送 PCM。
   - 服务端能收到音频帧。
   - 百炼能返回 transcript event。

6. 录音结束兜底链路单独验收。
   - `.caf` 文件存在。
   - 上传 base64 到 `/audio-transcriptions`。
   - 服务端 ffmpeg 转 wav。
   - DashScope 批量 ASR 返回 transcript。
   - summary job 成功。

## 下一轮最小修复建议

只做三件小事，先把 `failed to connect` 变成可定位错误：

1. iOS 增加一个开发期诊断状态，显示当前 `apiBaseURL` 和 `realtimeASRURL`。
2. iOS 启动录音前先请求 `/health`，失败时显示具体 URL 和错误。
3. Nginx `/api/` 代理加 WebSocket Upgrade 头。

暂时不做：

- 不改产品交互。
- 不引入账号系统。
- 不重构服务端。
- 不继续纠结域名和备案。
- 不把 H5 当成本轮真实录音验收路径。
