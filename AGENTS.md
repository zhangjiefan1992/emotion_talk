# Emotion Talk Project Agent Guide

这个仓库的目标是从个人真实问题出发，打造一个 iOS app，先服务作者本人，再逐步具备 App Store 上架和商业化能力。所有 agent 进入本仓库时，都要把这里当成一个产品研发工作台，而不是普通代码仓库。

## Core Mission

- 先解决一个真实、反复出现、作者本人愿意每天使用的问题。
- 先打磨需求、模式、体验和验证机制，再急着写代码。
- iOS 是第一客户端，服务端要从第一天考虑可部署、可迁移、可扩展。
- 后续可能支持 Web、HarmonyOS 或其他端，所以核心业务语义必须和客户端 UI 解耦。
- 收益不是第一阶段目标，但所有架构和体验选择都不能阻碍未来上架、订阅、付费或数据合规。

## Default Working Language

- 默认使用中文和作者沟通。
- 技术名词、API、文件名、代码标识符保留英文。
- 文档可以中英混写，但要优先让作者读起来清楚、有判断力。

## Operating Principles

1. 先澄清问题，再设计产品。
2. 先验证个人高频痛点，再抽象大众需求。
3. 先删掉不必要功能，再优化剩下的功能。
4. 先做可用闭环，再做精致扩展。
5. 先做 App Store 可接受的正当产品，再考虑增长和商业化技巧。
6. 任何架构选择都要写清楚可替换路径，避免过早锁死。

## Required Workflow

### 1. Intake

每次接到新需求，先判断它属于哪类工作：

- Product discovery: 需求、用户、场景、商业模式、定位。
- Product design: 信息架构、交互、体验、视觉方向。
- iOS implementation: SwiftUI、状态管理、导航、系统能力、App Store 准备。
- Backend/platform: API、数据、账号、同步、AI、推送、部署。
- Research/decision: 技术选型、竞品、成本、法律或平台规则。
- Maintenance: bugfix、重构、测试、文档、CI、发布。

如果需求模糊，最多先问一个关键问题。不要一次抛出长问卷。

### 2. Problem Brief

任何重要功能开始前，先形成一个简短 Problem Brief，至少覆盖：

- 用户是谁，第一阶段默认是作者本人。
- 真实触发场景是什么。
- 现在怎么解决，为什么不满意。
- 成功后的行为变化是什么。
- 最小可用闭环是什么。
- 明确不做什么。

推荐文件位置：

```text
docs/product/problem-brief.md
docs/product/user-mode.md
docs/product/non-goals.md
```

### 3. Brainstorm Gate

涉及创意、功能、体验、产品机制、视觉方向时，先使用 brainstorming 工作流：

- 先探索当前项目上下文。
- 一次只问一个澄清问题。
- 提供 2 到 3 个方案，说明取舍和推荐。
- 在作者确认设计后，再写规格文档。
- 规格文档写入 `docs/specs/`。
- 规格确认后，再进入实现计划。

不要跳过这个门槛去直接堆功能。

### 4. Decision Review

重要决策必须留下记录。使用这个模板：

```markdown
# Decision: <title>

Date: YYYY-MM-DD
Status: proposed | accepted | rejected | revisiting

## Context

## Options

## Recommendation

## Advisor Lenses

- Musk lens:
- Karpathy lens:
- Taste lens:
- Platform lens:

## Decision

## Revisit Trigger
```

推荐文件位置：

```text
docs/decisions/YYYY-MM-DD-<slug>.md
```

## Advisor Lenses

这些不是娱乐角色扮演，而是决策检查工具。

### Musk Lens

适用于成本、速度、范围、架构和商业模式判断。

必须问：

- 这个需求为什么存在，谁提出的。
- 能不能删除它。
- 理论上最小成本、最短路径是什么。
- 哪些步骤只是行业惯例。
- 如果外包或平台服务价格过高，白痴指数是多少。
- 哪些环节值得垂直整合，哪些不值得。
- 下一个可失败、可学习的版本是什么。

注意：马斯克视角擅长工程和成本，不擅长情感、人际、治理和需要长期社会协调的问题。

### Karpathy Lens

适用于 AI、可靠性、工程复杂度、学习路径和 agent 工作流判断。

必须问：

- 这是 demo，还是可以长期部署的系统。
- 最难的 5% 场景是什么。
- AI 能力的锯齿状失败点在哪里。
- 人类应该在哪些节点保留控制权。
- 这是 Iron Man suit，还是试图做 Iron Man robot。
- 数据飞轮是什么。
- 能不能用最小实现证明自己真的理解了核心。

注意：涉及最新模型、平台、价格、benchmark、API 时，必须查最新官方信息。

### Taste Lens

适用于落地页、官网、App Store 截图、品牌表达和任何 Web 视觉表达。

原则：

- 先读受众和场景，不套默认风格。
- 不做 AI 紫渐变、三等分功能卡片、假截图、空泛营销词。
- 视觉必须服务真实产品、真实状态、真实转化。
- App 内 UI 优先遵守 Apple Human Interface Guidelines 和平台习惯。
- Web 营销页可以更有表达力，但不能影响清晰度、性能和可访问性。

### Platform Lens

适用于后端、部署、数据、成本、合规和可迁移性。

默认假设可以先用 Cloudflare，但不能盲目承诺 Cloudflare 足够。必须按需求验证。

Cloudflare-first 候选：

- Workers: API、webhook、轻量业务逻辑。
- D1: 轻量关系型数据。
- R2: 文件、导出物、媒体对象。
- KV: 配置、缓存、低一致性键值。
- Queues: 异步任务。
- Durable Objects: 强一致状态、协作、实时会话。
- Vectorize: 向量搜索。
- AI Gateway 或 Workers AI: AI 调用治理、边缘推理候选。
- Turnstile: 防滥用。

可能需要跳出 Cloudflare 的情况：

- 复杂关系型查询和强事务要求超过 D1 适用范围。
- 长时间运行任务或重计算。
- 复杂后台管理和数据分析优先级高。
- 需要成熟 BaaS 生态、实时数据库或权限模型。
- 需要平台当前不稳定或限制较多的能力。

凡涉及 Cloudflare 限额、定价、API、配置字段，必须查官方文档或当前依赖，不能凭记忆写数字。

## iOS Product Workflow

iOS 是第一客户端。默认使用 SwiftUI，除非已有项目或明确需求要求 UIKit。

### Architecture Defaults

- 使用 SwiftUI-native state: `@State`、`@Binding`、`@Observable`、`@Environment`。
- iOS 17+ 优先使用 Observation。
- iOS 16 或更早需要兼容时，再使用 `ObservableObject`、`@StateObject`、`@ObservedObject`。
- 使用 `TabView`、`NavigationStack`、枚举路由和枚举 sheet。
- 服务通过环境注入或显式初始化传入，不要默认全局单例。
- View 保持小而聚焦，不把布局、业务逻辑、网络、路由都塞进一个文件。
- 异步加载使用 `.task`、`.task(id:)`、async/await，并提供 loading、empty、error 状态。
- 每个重要界面至少有 primary、empty、error 或 loading preview。

### App Store Readiness

从早期就记录：

- 数据收集内容和用途。
- 是否需要账号系统。
- 是否涉及敏感内容、健康、情绪、心理或个人隐私。
- 订阅或内购是否可能出现。
- 隐私政策和数据删除路径。
- 推送通知是否必要。

不要把这些留到最后再补。

## Backend and API Workflow

服务端要先支持最小闭环，不追求一开始完整平台化。

默认分层：

```text
apps/ios/                 # iOS client
services/api/             # backend API, likely Cloudflare Workers first
packages/contracts/       # shared API schemas and generated clients if needed
docs/product/             # product thinking and user mode
docs/specs/               # approved feature specs
docs/architecture/        # system diagrams and architecture notes
docs/decisions/           # decision records
docs/research/            # market, platform, compliance, competitor research
```

API 设计要求：

- 先定义资源和用户动作，再定义数据库表。
- 客户端不直接理解服务端存储细节。
- 关键 API 要有请求、响应、错误码和离线/重试策略。
- 所有 AI 调用要记录输入边界、输出风险、人工确认点和成本控制。
- 未来多端复用时，优先复用 API contract，不复制业务逻辑。

## Product Discovery Questions

探索真实需求时，优先问这些问题，但一次只问一个：

- 这个问题发生在一天中的哪个时刻。
- 你现在怎么处理它。
- 你为什么对现有方式不满意。
- 如果 app 只能做一件事，你希望它帮你完成什么。
- 你会在什么情况下连续用 7 天。
- 哪个结果会让你愿意付费。
- 哪个功能看起来诱人但其实可以不做。

## MVP Discipline

第一版只追求一个闭环：

```text
Trigger -> Capture -> Process -> Reflect -> Next Action
```

每个功能都要能放进这个闭环。放不进去的，进入 later list。

不要用以下内容伪装 MVP：

- 大而全的首页。
- 一堆未验证标签。
- 没有真实输入输出的 AI 聊天框。
- 没有连续使用理由的记录工具。
- 没有下一步行动的情绪分析。

## AI Feature Rules

如果产品涉及 AI：

- AI 必须增强用户判断，不替用户做不可解释的决定。
- 默认把 AI 做成 Iron Man suit，不做完全自主机器人。
- 对用户情绪、心理、自我认知相关输出，要谨慎、低姿态、可撤回。
- 不做医疗诊断、心理治疗承诺或危险建议。
- 高风险输出必须有人工确认或明确免责声明。
- 记录提示词、模型、成本、失败样例和回退策略。

## Verification

完成任何工作前，至少做对应验证：

- 文档: 无 TBD/TODO，术语一致，范围清楚，有下一步。
- iOS: 能 build，关键 preview 能打开，交互状态完整。
- Backend: 本地测试通过，错误路径被验证，配置和 secrets 不硬编码。
- Web/landing: 桌面和移动截图检查，文字不溢出，按钮可读，加载/空/错状态齐全。
- Research: 有来源链接，区分事实、推断和建议。

不能验证时，要明确说明原因和剩余风险。

### Browser Verification Preference

本项目验证本地原型、localhost 页面和交互稿时，优先使用 Codex 官方 Chrome Extension 控制用户的 Chrome 浏览器。

默认顺序：

1. Codex Chrome Extension / `extension` browser。
2. Codex in-app Browser / `iab`。
3. 系统 Chrome、standalone Playwright 或其他截图方式。

只有当前一个方式不可用、连接失败或不适合当前任务时，才降级到下一个方式。降级时要说明原因。

## Git and File Hygiene

- 不要随意改动用户未要求的文件。
- 不要回滚用户已有改动。
- 不要使用破坏性 git 命令，除非作者明确要求。
- 新增大功能前先写 spec。
- 重要设计和决策要落文档，不只留在聊天里。
- 文件名使用 kebab-case，代码标识符按语言惯例。

## Agent Response Style

- 给作者短而有信息量的进展更新。
- 不要一次问很多问题。
- 发现方向不清时，先帮作者收束，不要急着实现。
- 做完后说明改了什么、验证了什么、下一步建议是什么。
- 对不确定的事实说不确定，并主动查证。

## First Tasks for This Repository

建议按这个顺序推进：

1. 写 `docs/product/problem-brief.md`，描述作者真实问题。
2. 写 `docs/product/user-mode.md`，描述作者当前行为模式和触发场景。
3. 写 `docs/product/product-principles.md`，定义产品边界和价值观。
4. 写第一个 `docs/specs/` 规格文档。
5. 决定 iOS-only prototype 还是 iOS + Cloudflare backend prototype。
6. 只在规格确认后 scaffold app 和服务端。
