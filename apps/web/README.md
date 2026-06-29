# Emotion Talk H5

这是 Emotion Talk 的移动端优先 H5 验证版本，用来在暂时无法本地编译 iOS 26.5 真机包时，先跑通产品闭环。

## 能力范围

- 首页开始对话。
- 浏览器能力允许时尝试麦克风录音。
- 不满足安全上下文或测试模式时，自动降级为转写模拟。
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
PYTHONPATH=services/api/src EMOTION_TALK_LLM_PROVIDER=heuristic .venv/bin/python -m uvicorn emotion_talk_api.app:app --host 127.0.0.1 --port 8000
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

自动化验证或不想弹麦克风权限时：

```text
http://localhost:5173/?mockAudio=1
```

## 手机访问

Vite 会输出类似这样的局域网地址：

```text
http://<你的 Mac 局域网 IP>:5173/
```

iPhone 和 Mac 在同一 Wi-Fi 下时，可以直接在 Safari 打开。注意：iPhone Safari 的麦克风真录音通常要求 HTTPS 安全上下文，本地 HTTP 局域网地址会自动降级为转写模拟。要验证真实麦克风录音，可以后续使用 Cloudflare Tunnel、ngrok、Tailscale Serve 或正式 HTTPS 域名。

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

- H5 的实时转写仍是模拟层，未来替换为百炼移动端 SDK 或 Web 端可用的 ASR 方案。
- 浏览器录音只在安全上下文中可用，iPhone 局域网 HTTP 会降级。
- 当前服务端默认使用 SQLite 持久化，Docker 部署时保存在 `/data/emotion_talk.sqlite3` volume。
- 音频上传目前只打到服务端授权 stub，还没有真实 OSS PUT。
