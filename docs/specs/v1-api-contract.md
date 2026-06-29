# V1 API Contract

Status: accepted for iOS spike

## 目标

这份契约让 iOS 侧可以开始实现第一条闭环：

```text
创建 Space
-> 创建 Recording
-> 请求 ASR 临时会话配置
-> 手机本地录音 + SDK 实时转写
-> 提交最终 transcript
-> 创建自动 AI 摘要
-> 用户主动创建专家团建议
-> 展示专家团事件时间轴与裁判结论
```

机器可读契约：

```text
packages/contracts/emotion-talk-api.openapi.json
```

## 核心判断

当前已经明确：专家团建议不能默认声称“结合所有历史”。接口必须显式表达上下文范围。

默认策略：

```text
contextScope = current_only
```

用户触发专家团建议时，可以选择：

```text
contextScope = current_with_history
```

服务端会在 `contextUsage` 中返回本次到底引用了哪些历史记录。iOS 应该把这个信息展示给用户，至少在详情页或“生成依据”区域可见。

## 资源

### Space

倾诉空间。第一版可以先只有一个默认空间，但服务端资源模型按多空间设计。

```http
POST /spaces
GET  /spaces/{space_id}
```

### Recording

一次对话记录。iOS 点开始对话后创建。

```http
POST /recordings
GET  /recordings/{recording_id}
```

关键状态：

```text
recording
transcribed
summarized
```

### ASR Session

iOS 请求实时语音识别会话配置。

```http
POST /asr-sessions
```

当前实现返回 `dev_stub`，正式实现时这里由服务端用永久密钥换取 Bailian/DashScope 临时凭证。iOS 不持有长期密钥。

### Audio Upload Authorization

iOS 结束录音后上传音频文件前请求授权。

```http
POST /recordings/{recording_id}/audio-upload-authorizations
```

当前实现返回 OSS object key 和 dev stub。正式实现时返回私有 OSS presigned upload URL。

### Transcript

iOS 提交最终转写。第一版支持两种形态：

- `markdown`: 兼容钉钉听记导出的 markdown。
- `segments`: iOS 实时 ASR SDK 产生的分段结果。

```http
POST /recordings/{recording_id}/transcript
```

### Summary Job

自动 AI 摘要。它是结束录音后的自动流程，不需要用户额外点击。

```http
POST /recordings/{recording_id}/summary-jobs
```

当前实现是 `dev_summary_stub`，用于稳定接口形状；后续替换为 LLM summary worker。

### Expert Advice Job

用户主动触发专家团建议。

```http
POST /recordings/{recording_id}/expert-advice-jobs
GET  /expert-advice-jobs/{job_id}
GET  /expert-advice-jobs/{job_id}/events
GET  /expert-advice-jobs/{job_id}/artifact
```

创建请求中的关键字段：

```json
{
  "contextScope": "current_only",
  "historyLimit": 5,
  "includeProfile": false
}
```

如果用户选择结合历史：

```json
{
  "contextScope": "current_with_history",
  "historyLimit": 5,
  "includeProfile": true
}
```

也可以由客户端显式传入用户选择的历史：

```json
{
  "contextScope": "current_with_history",
  "historicalContext": [
    {
      "sourceType": "recording",
      "sourceId": "rec_123",
      "title": "06-10 职业焦虑复盘",
      "createdAtText": "2026-06-10 22:00",
      "summary": "用户反复提到稳定收入和长期热爱之间的拉扯。",
      "keyPoints": ["外贸提供安全感", "普拉提代表长期理想"],
      "relevance": "user_selected"
    }
  ]
}
```

返回体必须包含：

```json
{
  "contextUsage": {
    "scope": "current_with_history",
    "primary": "current_recording",
    "historyCount": 1,
    "historySources": [
      {
        "sourceType": "recording",
        "sourceId": "rec_123",
        "title": "06-10 职业焦虑复盘",
        "relevance": "same_space_recent"
      }
    ],
    "profileIncluded": false
  }
}
```

## iOS 对接顺序

1. App 首次进入或调试时创建一个 Space。
2. 用户点击开始对话，调用 `POST /recordings`。
3. iOS 调用 `POST /asr-sessions`，拿实时 ASR SDK 配置。
4. iOS 本地录音，同时展示实时转写。
5. 用户点击结束，iOS 请求音频上传授权并上传音频。
6. iOS 调用 `POST /recordings/{recording_id}/transcript` 提交最终分段文本。
7. iOS 调用 `POST /recordings/{recording_id}/summary-jobs`，展示处理中/完成状态。
8. 用户点击专家团建议，iOS 调用 `POST /recordings/{recording_id}/expert-advice-jobs`。
9. iOS 拉取 `events` 渲染三轮专家时间轴，拉取 `artifact` 渲染裁判结论。

## 不变量

- 自动摘要和专家团建议是两个不同 job。
- 专家团建议必须由用户主动触发。
- 默认只使用当前对话。
- 结合历史时必须返回 `contextUsage`。
- iOS 不直接传模型名、专家 prompt 或 runtime 名。
- iOS 不持有长期 ASR、OSS、LLM 密钥。

## 当前实现边界

- 默认 app 使用 SQLite 仓库，适合本地研发、H5 验证和单机 Docker 部署。
- 单元测试默认仍使用内存仓库，避免测试相互污染。
- ASR 临时凭证和 OSS 上传授权是 dev stub。
- Summary 是 dev stub。
- Expert Advice 已经是真实多轮专家团状态机，可使用 DeepSeek provider 或 heuristic provider。
- 下一步替换内存仓库为数据库，替换 dev stub 为真实 Bailian/DashScope 与 OSS 适配器。
