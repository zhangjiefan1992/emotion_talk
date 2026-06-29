# Decision: V1 关键技术选型

Date: 2026-06-15
Status: accepted

## 背景

V1 的主流程是一个实时开麦的倾诉听记产品：

```text
用户点击「开始对话」
-> iPhone 麦克风开始录音
-> 百炼移动端 SDK 实时语音转文字
-> App 展示实时转写内容
-> 用户说话约 45 分钟
-> 用户点击「结束」
-> 保存本次 MP3 录音文件
-> 上传 MP3 到 OSS
-> 服务端关联 OSS 音频与本次纪要
-> 服务端基于文字生成 AI 图文纪要
-> 用户主动点击「专家团建议」
-> 服务端进入多 Agent 专家团流程
```

关键边界：

- iOS 端负责采集、实时显示、结束动作和上传。
- 服务端负责数据、纪要、历史关联、画像、专家团和重新生成。
- 数据以服务端为准；iOS 是采集和展示端，不承担长期记忆。
- 录音文件必须持久保存，未来可追溯、可重新转写、可重新生成纪要。

## 选型总览

```text
iOS: SwiftUI + AVFoundation + 百炼移动端 SDK
服务端: API + Job Worker + 多 Agent Runtime
音频存储: 阿里云 OSS
数据库: PostgreSQL 候选优先
缓存/队列/Agent 消息: Redis 候选优先
AI 纪要: DeepSeek / Qwen / Claude 等 LLM Provider 可插拔
专家团: AgentScope 前置 spike；自研轻量 / CrewAI Flow 作为 fallback
接口契约: OpenAPI 优先，iOS 端后续生成 Swift client
```

## iOS 端

V1 选型：

- Native iOS App。
- SwiftUI。
- Swift Concurrency。
- iOS 17+ 作为工程基线，除非后续用户覆盖要求降低版本。
- AVFoundation 负责本地麦克风采集、MP3/AAC 文件生成和播放。
- 百炼移动端 SDK 负责实时语音识别。
- `RecordingService` 管理本地录音文件生命周期。
- `RealtimeASRService` 封装百炼 SDK，不让 UI 直接接触供应商细节。

iOS 端输出两类数据：

- 实时转写文字：录音过程中展示，并持续上报/结束后提交给服务端。
- 录音文件：结束后生成 MP3/AAC，并上传到 OSS。

设计原则：

- 本地录音不能因为 ASR 失败而中断。
- 实时转写是过程反馈，最终纪要以服务端保存的文字和音频为准。
- App 不暴露模型选择、ASR provider、LLM provider 等技术选项。

## 实时语音转写

V1 选型：

- Provider family: 阿里云百炼 / DashScope Paraformer realtime ASR。
- 集成方式：百炼移动端 SDK。
- 凭证方式：服务端签发临时凭证或短时 token，iOS 不内置长期 key。
- Realtime proxy：仅作为 fallback，不作为默认链路。

待实测模型：

```text
paraformer-realtime-v2
paraformer-realtime-8k-v2
```

原因：

- 之前倾向 `paraformer-realtime-8k-v2`，但 V1 输入是 iPhone 麦克风，不是电话 8k 音频。
- 需要用真实 iPhone 录音环境比较准确率、延迟、断句和噪声表现。

必须做的 ASR spike：

- 45 分钟前台录音。
- 实时转写显示。
- 临时凭证续期或 ASR 分段。
- ASR 中断后本地录音不中断。
- `realtime-v2` vs `realtime-8k-v2` 实测对比。

## 服务端

服务端是产品核心，不只是一个转发 API。

V1 服务端职责：

- 账号、Space、权限。
- Recording Session 生命周期。
- 签发百炼 SDK 所需临时凭证。
- 签发 OSS 上传授权。
- 保存 transcript、音频对象、AI 纪要、章节、历史关联、画像和专家团结果。
- 执行自动 AI 纪要生成。
- 执行用户主动触发的专家团多 Agent 任务。
- 记录 AI 输入边界、输出版本、失败状态和重新生成历史。

推荐服务端形态：

```text
API Service
Job Worker
Agent Runtime
PostgreSQL
Redis
OSS
```

语言/框架候选：

- Python + FastAPI：更贴近 AgentScope / 多 Agent runtime / 后台任务生态。
- TypeScript + Hono/Node：更轻、更适合 API，但接 AgentScope 会变成跨语言服务。

当前建议：

- 如果专家团确定要走 AgentScope 方向，服务端主栈优先考虑 Python + FastAPI。
- 如果专家团先自研轻量编排，TypeScript 或 Python 都可以，但仍建议以 OpenAPI 作为 iOS 契约边界。
- Cloudflare 可以保留为 CDN、DNS、边缘防护、静态资源或轻量 webhook 候选，不再默认作为核心计算/数据中心。

## 音频存储

V1 选型：

- 阿里云 OSS 作为音频对象存储优先候选。
- iOS 端结束录音后上传 MP3/AAC 到 OSS。
- 服务端保存 `ossBucket`、`ossObjectKey`、`durationMs`、`mimeType`、`sizeBytes`、`checksum` 等元数据。
- OSS 对象默认私有，不暴露公共 URL。
- 下载、回放、重新生成都通过服务端鉴权后获得短时访问能力。

为什么不是只存文字：

- 未来可以重新转写。
- 未来可以换模型重新生成纪要。
- 用户可以追溯 AI 结论对应的原始表达。
- 出现转写错误时可以修复。

## 数据库

V1 推荐 PostgreSQL 优先。

原因：

- Recording、Transcript、Summary、Profile、ExpertAdvice 都是关系型资源。
- 专家团任务、状态机、重试、版本记录更适合成熟关系型数据库。
- 后续管理后台、审计、数据导出会更自然。

核心表候选：

- `users`
- `spaces`
- `space_members`
- `recording_sessions`
- `audio_objects`
- `transcript_segments`
- `minutes_artifacts`
- `chapters`
- `history_links`
- `space_profile_items`
- `expert_advice_jobs`
- `expert_advice_rounds`
- `expert_advice_artifacts`
- `model_runs`

Redis 候选用途：

- Job queue。
- AgentScope message bus。
- 专家团任务状态缓存。
- SSE / 进度流事件缓冲。

## AI 图文纪要

输入：

- 当前 recording 的最终转写文字。
- 说话人/时间戳片段。
- 少量 Space 历史上下文。
- 可选：当前 Space Profile。

输出：

- 总览摘要。
- 章节。
- 关键原话。
- 情绪/主题关键词。
- 历史关联。
- 可视化卡片数据结构，支持 App 端展示类似钉钉 AI 纪要的图文效果。

模型策略：

- DeepSeek、Qwen、Claude、OpenAI-compatible provider 都通过 `LLMProvider` 接口接入。
- V1 不在用户界面暴露模型选择。
- 自动纪要和专家团建议使用不同 prompt、不同输出 schema、不同风控策略。

## 专家团多 Agent

专家团是服务端能力，不在 iOS 端执行。

V1 专家团固定角色：

- 人生教练。
- 心理咨询视角。
- 现实行动视角。
- 裁判/收敛器。
- Safety guardrail 隐藏执行。

任务特征：

- 用户主动触发。
- 输入快照冻结。
- 多轮讨论。
- 过程可读展示。
- 最终由裁判收敛。
- 输出绑定证据、原话和不确定性。

## 专家团 Runtime 选型结论

当前不建议直接把「云端 Claude Code CLI」作为产品运行时。它可以做开发期和单用户内部实验，但不要进入用户生产链路。

接受的路线已在 2026-06-16 修正：

```text
短期：AgentScope Expert Team spike
fallback：自研轻量多 Agent 编排 / CrewAI Flow
内部工具：Claude Code CLI / Qoder CLI
```

原因：

- 我们的专家团需要多轮讨论、过程展示、消息记录、用户离开后可回看，已经不只是几次 LLM call。
- AgentScope 的 Agent Team / Agent Service / Message Event 模型更贴近“专家团过程交付”。
- 自研轻量编排仍保留为 fallback，但不再作为第一主线。
- CrewAI 更适合 Flow / Task 类 AI workflow，可作为 fallback 或非专家团流程候选。
- Claude Code/Qoder CLI 适合作为内部研发和离线评测工具，不直接进入用户生产链路。

## Advisor Lenses

- Musk lens: 如果需要消息总线、worker session、事件流、回放和恢复，不要重造半个框架，先验证现成的 AgentScope。
- Karpathy lens: 最难的是部署可靠性和边界，不是能不能让 3 个 agent 说话。要验证 session、event、replay、schema、失败样例和人工控制点。
- Taste lens: 用户不关心用了 AgentScope 还是 Claude Code。用户只关心过程是否可信、建议是否克制、页面是否清楚。
- Platform lens: 如果专家团成为核心差异，服务端要允许从轻量编排平滑迁移到 AgentScope 这类完整 runtime。

## Decision

V1 开始实现时采用：

```text
iOS: SwiftUI + AVFoundation + 百炼移动端 SDK
ASR: 百炼 Paraformer realtime，模型待 iPhone 实测
音频: iOS 生成 MP3/AAC，上传阿里云 OSS
服务端: API + Job Worker + 多 Agent Runtime
数据库: PostgreSQL 优先
队列/Agent bus: Redis 优先
AI 纪要: LLMProvider 接 DeepSeek / Qwen / Claude 等
专家团: AgentScope 前置 spike；自研轻量 / CrewAI Flow fallback
接口: OpenAPI 作为 iOS/服务端契约
```

## 必须验证

1. 百炼移动端 SDK 在 45 分钟实时开麦场景下是否稳定。
2. iOS 录音文件格式、体积、上传耗时和失败恢复。
3. OSS 上传授权和服务端关联流程。
4. DeepSeek/Qwen/Claude 对中文倾诉纪要的质量差异。
5. AgentScope 是否能稳定映射专家团任务。
6. 自研轻量 / CrewAI Flow fallback 是否需要保留。

## Revisit Trigger

重新评估选型的触发条件：

- 百炼移动端 SDK 无法稳定支持实时转写。
- OSS 上传/回放/权限链路复杂度过高。
- PostgreSQL + Redis 部署成本超过个人项目承受范围。
- AgentScope 无法稳定支持权限隔离、过程展示或任务恢复。
- AgentScope 部署成本超过 V1 承受范围。
