# H5 V1 App Shell

Date: 2026-06-24
Status: implemented

## Goal

在 iOS 真机构建受系统/Xcode 限制时，先用 H5 跑通 Emotion Talk 的产品闭环，让作者可以在手机浏览器中验证核心体验。

## Scope

H5 V1 覆盖：

- 开始对话。
- 实时转写展示。
- 结束对话。
- 自动生成 AI 纪要。
- 用户点击后生成专家团建议。
- 专家团按三轮讨论时间线展示。
- 裁判结论置顶。
- 默认只使用本次对话，用户可选择补充历史。

## Non-goals

- 不在本期实现百炼实时 ASR Web SDK。
- 不在本期实现账号、空间成员邀请和权限体系。
- 不在本期实现真实 OSS 音频上传。
- 不把专家团建议自动推给用户。
- 不把产品包装成心理治疗或医疗建议。

## Interaction Model

```text
Trigger -> Capture -> Process -> Reflect -> Next Action
```

- Trigger: 用户点击“开始”。
- Capture: 浏览器录音可用时录音，否则模拟转写；页面持续展示文本。
- Process: 用户点击“结束并生成 AI 纪要”后，提交转写并生成纪要。
- Reflect: 用户查看“总览、过程、收束”结构。
- Next Action: 用户主动点击“生成专家团建议”，查看多轮讨论和裁判结论。

## Backend Integration

H5 使用现有 API：

- `GET /health`
- `POST /spaces`
- `POST /recordings`
- `POST /asr-sessions`
- `POST /recordings/{recordingId}/transcript`
- `POST /recordings/{recordingId}/summary-jobs`
- `POST /recordings/{recordingId}/expert-advice-jobs`

开发环境通过 Vite `/api` proxy 转发到 `http://127.0.0.1:8000`，避免浏览器 CORS 问题。

## UX Notes

- 首页直接是产品工作台，不做 landing page。
- 视觉参考钉钉 AI 听记的信息结构，但产品语气更私密、更安静。
- 专家团默认不自动生成，避免用户刚倾诉完就被建议打断。
- 专家团输出必须展示过程，不只给最终答案。
- 高风险表达用安全边界收束，不做诊断承诺。

## Verification

本次验证记录见：

```text
outputs/h5-smoke/test-report.md
```
