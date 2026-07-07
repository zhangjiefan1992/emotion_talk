# Decision: 倾听 Skill / Plugin 第一桶金路径

Date: 2026-07-07
Status: proposed

## Context

这里讨论的不是 App，也不是人工代交付服务。

真正的产品形态是：

```text
倾听 Skill / Plugin = 集成在 Claude Code、OpenClaw、Qoder、Cursor 或其他 agent 容器里的领域工作流插件
```

用户已经有 agent。多 agent 编排、工具调用、上下文读写、文件生成，都会被宿主 agent 平台逐步 commoditize。所以不能把“多 agent 讨论”当核心卖点。

核心问题变成：

```text
当用户已经有强大的 agent，为什么还要为这个倾听 skill 付费？
```

## One-Line Verdict

卖判断标准。

不是卖 agent 数量，不是卖 prompt，不是卖 App。

## What Is Actually Valuable

用户为 skill/plugin 付费，买的不是“能不能调用 LLM”，而是这四件事：

1. 领域工作流：把混乱倾诉稳定处理成可交付报告。
2. 安全边界：不诊断、不治疗、不越界建议，有拒答和转介规则。
3. 交付格式：固定产出 HTML/PDF/Markdown 报告，能直接发给自己或客户。
4. 持续更新：新模板、新评测样例、新平台适配、新安全规则。

这就是付费点。

## Product Shape

第一版做成一个可安装 skill 包：

```text
listening-skill/
  SKILL.md
  templates/
    listening-report.md
    expert-timeline.md
    seven-day-action-card.md
  rubrics/
    safety-boundary.md
    evidence-rules.md
    report-quality-check.md
  examples/
    anonymized-input.md
    anonymized-output.html
  scripts/
    render-report.py
```

它不负责底层 agent 能力。它只负责把 agent 驱动到一个稳定、可复用、可审查的倾听交付流程。

## Core Features

### Free / Trial

- 倾诉材料整理。
- 单次 Markdown 报告。
- 基础总-过程-总结构。
- 简单 7 天行动卡。
- 不含长期画像。
- 不含高级安全检查。
- 不含商业使用授权。

目的：让用户在 10 分钟内跑出第一份报告。

### Pro

- 完整倾听复盘报告模板。
- 专家团时间线模板。
- 原话证据绑定规则。
- 裁判结论 rubric。
- 安全边界和拒答规则。
- HTML/PDF 渲染脚本。
- 私人使用授权。
- 每月模板更新。

目的：让个人用户稳定自用，也能给亲友做少量报告。

### Commercial

- 商业使用授权。
- 批量报告模板。
- 品牌化输出。
- 客户交付免责声明。
- 质量评估 checklist。
- 客户反馈表。
- 案例库和更新订阅。

目的：让咨询师、教练、知识付费作者、社群主拿它做付费服务。

## Pricing Standard

不要按 token 收费。宿主 agent 已经有模型和 token 成本。

收费按“使用权 + 更新 + 商业交付权”定价。

| 版本 | 价格 | 付费锚点 |
|---|---:|---|
| Free | 0 元 | 试用和传播 |
| Pro | 99-199 元一次性 | 个人工作流包 + 3 个月更新 |
| Pro Update | 29 元/月 | 持续模板、案例和平台适配 |
| Commercial | 699-1999 元/年 | 商业交付权 + 品牌化模板 + 质检标准 |
| Studio Setup | 2999-9999 元一次性 | 帮小团队接入私有 agent 工作台 |

第一桶金最短路径：

```text
卖 20 份 Pro x 149 元 = 2980 元
```

更好的路径：

```text
卖 3 份 Commercial x 999 元 = 2997 元
```

如果想走量，Pro 是主力。如果想快赚钱，Commercial 更快。

## Why People Pay

### 个人用户

他付费是为了少折腾。

他不想自己写 prompt，不想反复改报告结构，不想担心 AI 输出越界。他要一个可安装、可复用、会不断更新的倾听工作流。

### 教练 / 咨询顾问 / 社群主

他付费是为了交付标准化。

他已经有客户、社群或私域流量，但每次倾听、复盘、整理都耗时间。这个 skill 让他把一次沟通变成标准报告，节省交付时间。

### Agent Power User

他付费是为了拿到高质量领域资产。

这类人不会为“多 agent”付费，但会为好模板、好 rubric、好样例、好输出格式付费。

## Musk Lens

### 质疑需求

“多 agent 体系”为什么存在？

如果 Claude Code / OpenClaw 已经提供 agent 能力，那你再卖多 agent，就是卖别人正在免费补齐的东西。

删掉它。

### 白痴指数

一个 prompt 文件的复制成本接近 0。卖文件很难长期收费，因为复制太容易。

所以付费不能锚定在文件本身，要锚定在：

- 更新权。
- 商业授权。
- 私有案例库。
- 质量标准。
- 接入支持。

文件是载体，不是商品。

### 垂直整合

不要重做 agent runtime。

垂直整合的对象不是模型、不是 agent 容器，而是“倾听报告的交付标准”。

你控制标准，宿主 agent 提供执行力。

### 加速

先发布一个可安装 zip / GitHub private repo。

不要等 marketplace。

第一版付款方式可以是微信转账 + 手动发下载链接。丑，但快。

## Delivery Flow

第一版交易路径：

```text
用户看到样例报告
-> 购买 Pro / Commercial
-> 收到 private repo 或 zip
-> 按 README 安装到 Claude Code / OpenClaw
-> 用自己的 agent 跑一次倾听报告
-> 加入更新群或邮件列表
```

交付物必须包含：

- 安装说明。
- 3 个真实脱敏样例。
- 一份可直接展示的 HTML 报告。
- 一份安全边界说明。
- 一份商业使用边界说明。

## First 7 Days

Day 1:

- 做出 `listening-skill` 文件夹。
- 写 1 个完整脱敏样例。
- 产出 1 份 HTML 样例报告。

Day 2:

- 写 README：Claude Code / OpenClaw 安装方式。
- 写 Pro 和 Commercial 权益。

Day 3:

- 发招募：只找 agent power user、教练、咨询顾问、社群主。
- 不找泛情绪用户。

Day 4-5:

- 送 5 个 Pro 试用码，换公开反馈。
- 问一个问题：这个 skill 是否能让你省下 30 分钟交付时间？

Day 6-7:

- 开卖 Pro 149 元。
- 对有商业交付意图的人卖 Commercial 999 元。

通过标准：

```text
7 天内卖出 3 份 Pro，或 1 份 Commercial。
```

不通过就说明 skill 形态的付费意愿不足，回到服务交付或 App 路径。

## Non-Goals

第一阶段不做：

- 自建 agent runtime。
- 自建多 agent 框架。
- 自建 marketplace。
- 自建支付系统。
- 自建账号体系。
- 强行绑定 iOS App。
- 承诺心理咨询、治疗或诊断。

## Safety Boundary

这个 skill 只能定位为：

- 倾诉整理。
- 复盘报告。
- 情绪记录。
- 自我观察。
- 低风险行动建议。

不能定位为：

- 心理治疗。
- 医疗诊断。
- 危机干预。
- 人格分析。
- 关系裁判。

遇到自伤/他伤、未成年人敏感问题、药物医疗法律问题，必须拒绝继续生成建议，并提示寻求专业帮助或紧急帮助。

## Decision

建议接受：

```text
第一桶金路径 = 倾听 Skill / Plugin Pro + Commercial 授权
```

先卖可安装、可复用、可更新、可商业交付的领域工作流包。

App、H5、服务端不是第一商品。它们是后续承接更大规模用户的基础设施。

## Revisit Trigger

满足任一条件后重新评估是否做 hosted backend 或 App：

- Pro 用户超过 50。
- Commercial 用户超过 5。
- 用户开始要求团队协作、报告管理、历史空间。
- 盗版/复制导致一次性售卖不可持续。
- 用户愿意为 hosted API 或私有部署付费。

## Sources

- Claude Code Skills Documentation: https://code.claude.com/docs/en/skills
- Claude Code Overview: https://docs.anthropic.com/en/docs/claude-code/overview
- OpenClaw Documentation: https://openclaw.ai/docs
- Agent37 on monetizing Claude Code skills: https://www.agent37.com/blog/monetize-claude-code-skills
