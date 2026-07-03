# Decision: Unified Client Framework

Date: 2026-07-01
Status: accepted

## Context

项目需要同时覆盖 H5、iOS、Android、小程序，继续维护 SwiftUI iOS 与 React H5 两套客户端会放大返工成本。

## Options

- uni-app + Vue3: 一套代码覆盖 H5、App、小程序，国内生态成熟。
- Taro: 小程序和 H5 强，App 侧通常还要引入 React Native 链路。
- Flutter / Capacitor: App 或 Web 强，但小程序不是主能力。

## Recommendation

使用 uni-app + Vue3 + TypeScript 作为主客户端框架，服务端继续保留 FastAPI。

## Advisor Lenses

- Musk lens: 删除多客户端重复实现，先让一个 H5 版本跑通。
- Karpathy lens: AI、ASR、专家团留在服务端，客户端只承载采集和呈现。
- Taste lens: 迁移时保留现有移动端交互方向，不重新发明视觉系统。
- Platform lens: H5 先部署验证，后续用同一代码产出小程序和 App 包。

## Decision

`apps/web` 已从 React/Vite 切换为 uni-app H5 项目。原生 iOS 目录暂时保留为历史验证稿，不再作为第一主线继续堆功能。

## Revisit Trigger

当 uni-app 无法稳定接入真实录音、实时 ASR、App Store 打包或微信小程序审核能力时，重新评估 Taro/原生/Flutter。
