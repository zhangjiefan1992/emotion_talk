# Emotion Talk H5

这是 Emotion Talk 的移动端优先 H5 验证版本，用来在暂时无法本地编译 iOS 26.5 真机包时，先跑通产品闭环。

## 能力范围

- 首页开始对话。
- 浏览器暴露 `navigator.mediaDevices.getUserMedia` 时尝试真实麦克风录音。
- 不满足真实录音条件时明确报错，不再降级为模拟数据。
- 实时展示转写片段。
- 结束后调用服务端生成 AI 纪要。
- 用户点击后调用专家团建议。
- 专家团展示三轮专家讨论、裁判结论、建议和安全边界。
- 当前 H5 默认请求 `current_with_history`，服务端返回 `contextUsage` 用来说明实际引用了哪些历史。
- 生产构建包含基础 PWA manifest 和 service worker，可用于手机添加到主屏幕测试。

## 本地运行

先启动服务端：

```bash
cd /Users/jeff/Documents/emotion_talk
PYTHONPATH=services/api/src EMOTION_TALK_LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=... .venv/bin/python -m uvicorn emotion_talk_api.app:app --host 127.0.0.1 --port 8000
```

再启动 H5：

```bash
cd /Users/jeff/Documents/emotion_talk/apps/web
npm install
npm run dev
```

浏览器打开：

```text
http://localhost:5173/
```

## 手机访问

Vite 会输出类似这样的局域网地址：

```text
http://<你的 Mac 局域网 IP>:5173/
```

iPhone 和 Mac 在同一 Wi-Fi 下时，可以直接在 Safari 打开。注意：手机浏览器是否允许 HTTP 地址录音，取决于它是否把当前地址视为安全来源。`localhost` / `127.0.0.1` 往往可用，公网 HTTP IP 通常不可用；局域网 IP 在不同浏览器和版本上可能不一致。H5 会以真实能力检测为准，能拿到 `getUserMedia` 就尝试录音，拿不到就报错。

## 构建

```bash
cd /Users/jeff/Documents/emotion_talk/apps/web
npm run build
```

## Docker 运行

推荐从仓库根目录启动完整 H5 + API：

```bash
cd /Users/jeff/Documents/emotion_talk
cp .env.example .env
docker compose up --build -d
```

默认打开：

```text
http://localhost:8080/
```

## API 地址

默认通过 Vite `/api` 代理到：

```text
http://127.0.0.1:8000
```

也可以设置：

```bash
VITE_API_BASE_URL=https://your-api.example.com npm run build
```

## 当前限制

- H5 的实时转写依赖浏览器 `SpeechRecognition` 能力；不支持时，结束后用录音文件请求服务端转写。
- 浏览器录音以 `getUserMedia` 能力检测为准；公网 HTTP IP 通常拿不到该能力。
- 当前服务端默认使用 SQLite 持久化，Docker 部署时保存在 `/data/emotion_talk.sqlite3` volume。
- 音频上传目前只打到服务端授权 stub，还没有真实 OSS PUT。
