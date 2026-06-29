# H5 + API Docker Deployment

Date: 2026-06-24
Status: runnable

## 部署形态

当前推荐先用单机 Docker Compose：

```text
Browser / Mobile Safari
-> web container, Nginx, port 8080 by default
-> /api reverse proxy
-> api container, FastAPI
-> SQLite volume /data/emotion_talk.sqlite3
```

这个形态足够验证 H5 产品闭环，也方便后续迁移到 MySQL/PostgreSQL。

## 本地或服务器启动

```bash
cd /Users/jeff/Documents/emotion_talk
cp .env.example .env
docker compose up --build -d
```

打开：

```text
http://<server-ip>:8080/
```

如果想直接占用 80 端口：

```bash
WEB_PORT=80 docker compose up --build -d
```

如果本机或服务器上 8080 已经被占用：

```bash
WEB_PORT=8081 docker compose up --build -d
```

## 配置

默认使用离线 heuristic provider，方便无密钥部署验证：

```env
EMOTION_TALK_LLM_PROVIDER=heuristic
```

切到 DeepSeek：

```env
EMOTION_TALK_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=...
```

不要把真实 API key 提交到 git。

## 数据

SQLite 数据保存在 Docker volume `emotion_talk_api_data` 内：

```text
/data/emotion_talk.sqlite3
```

查看容器状态：

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f web
```

## 验证链路

1. 打开 H5 首页。
2. 点击右下角麦克风按钮开始录音。
3. 点击「结束并处理」。
4. H5 进入详情页并展示 AI 摘要。
5. 点击「请求专家团建议」。
6. 等待专家团生成完成，页面展示三轮讨论和裁判收敛。

当前服务端链路：

```text
POST /spaces
POST /recordings
POST /asr-sessions
POST /recordings/{id}/transcript
POST /recordings/{id}/summary-jobs
POST /recordings/{id}/expert-advice-jobs
```

## 当前边界

- H5 的实时转写仍是模拟层，真实语音识别后续接百炼移动端 SDK 或 Web 可用方案。
- 音频上传授权仍是 OSS dev stub。
- SQLite 适合第一阶段单机验证；多人生产化后迁移到 MySQL/PostgreSQL。
- 如果手机端需要真实麦克风录音，远端必须使用 HTTPS。可以先用 Cloudflare Tunnel、Caddy、Nginx + TLS 或云厂商证书。
