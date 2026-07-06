import EmotionTalkCore
import SwiftUI

struct ConversationHomeView: View {
    @Environment(\.emotionTalkAPI) private var api
    let spaceStore: SpaceStore
    @State private var session = ConversationSession()

    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                switch session.phase {
                case .idle:
                    if let currentSpace = spaceStore.currentSpace {
                        IdleConversationView(
                            spaceCount: spaceStore.spaces.count,
                            recordCount: spaceStore.records.count,
                            records: Array(spaceStore.records.prefix(3))
                        ) {
                            Task {
                                await session.start(api: api, space: currentSpace, options: AppConfiguration.startOptions)
                            }
                        }
                    } else if let error = spaceStore.errorMessage {
                        FailurePanel(message: "空间加载失败：\(error)") {
                            Task { await spaceStore.load(api: api) }
                        }
                    } else {
                        ProgressPanel(title: "加载空间", subtitle: "正在准备当前倾诉空间")
                    }
                case .starting:
                    ProgressPanel(title: "创建对话", subtitle: "正在准备录音空间")
                case .recording:
                    RecordingLiveView(
                        elapsedText: session.elapsedText,
                        statusText: session.recorderStatus,
                        segments: session.liveSegments,
                        onFinish: {
                            Task {
                                await session.finish(api: api)
                                try? await spaceStore.loadRecords(api: api)
                            }
                        }
                    )
                case .processing:
                    ProgressPanel(title: "生成纪要", subtitle: "正在整理转写和摘要")
                case .completed:
                    if let recording = session.recording, let summary = session.summary {
                        RecordingDetailView(
                            recording: recording,
                            summary: summary,
                            expertAdvice: session.expertAdvice,
                            advicePhase: session.advicePhase,
                            onRequestAdvice: { scope in
                                Task { await session.requestAdvice(api: api, scope: scope) }
                            },
                            onReset: session.reset
                        )
                    }
                case .failed:
                    FailurePanel(message: session.errorMessage ?? "操作失败") {
                        session.reset()
                    }
                }
            }
            .padding(20)
            .padding(.bottom, 96)
        }
        .background(Color.appGroupedBackground)
        .navigationTitle(spaceStore.currentSpace?.name ?? "倾诉")
    }
}

private struct IdleConversationView: View {
    let spaceCount: Int
    let recordCount: Int
    let records: [RecordingResponse]
    let onStart: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("\(max(spaceCount, 1)) 个空间 · \(recordCount) 条真实记录")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer()
            }

            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass")
                Text("搜索记录、原话、主题")
                Spacer()
            }
            .foregroundStyle(.secondary)
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
            .background(Color.appSecondaryGroupedBackground, in: Capsule())

            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("空间画像")
                            .font(.headline)
                        Text("只基于真实转写和纪要生成")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(recordCount > 0 ? "基于真实记录" : "等待录音")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Color.appSecondaryGroupedBackground, in: Capsule())
                }

                if recordCount == 0 {
                    Text("完成第一次真实录音后，空间画像会从转写和纪要中生成。")
                        .font(.body)
                        .foregroundStyle(.secondary)
                } else {
                    HStack(spacing: 12) {
                        MetricTile(value: "\(recordCount)", label: "真实记录")
                        MetricTile(value: "待生成", label: "反复主题")
                    }
                }
            }
            .padding(20)
            .background(.background, in: RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Text("最近记录")
                        .font(.title2.bold())
                    Spacer()
                    Label("筛选", systemImage: "line.3.horizontal.decrease")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 22) {
                    Text("最近").fontWeight(.semibold)
                    Text("我的")
                    Text("共享")
                    Text("收藏")
                }
                .font(.subheadline)
                .foregroundStyle(.secondary)

                if records.isEmpty {
                    Text("还没有真实记录。点击下方按钮开始第一次倾诉。")
                        .font(.body)
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(records) { record in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(record.title)
                                .font(.headline)
                            Text(record.transcript?.durationText ?? record.status)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
                    }
                }
            }
            .padding(20)
            .background(.background, in: RoundedRectangle(cornerRadius: 8))

            Button(action: onStart) {
                Label("开始", systemImage: "mic.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("startConversationButton")

            VStack(spacing: 12) {
                CapabilityRow(symbol: "waveform", title: "实时转写", value: "真实麦克风")
                CapabilityRow(symbol: "doc.text", title: "自动纪要", value: "结束后生成")
                CapabilityRow(symbol: "person.3", title: "专家团", value: "用户主动触发")
            }
            .padding(20)
            .background(.background, in: RoundedRectangle(cornerRadius: 8))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct MetricTile: View {
    let value: String
    let label: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.title.bold())
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct RecordingLiveView: View {
    let elapsedText: String
    let statusText: String
    let segments: [TranscriptSegmentRequest]
    let onFinish: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Label("录音中", systemImage: "record.circle")
                    .font(.headline)
                    .foregroundStyle(.red)
                Spacer()
                Text(elapsedText)
                    .font(.system(.title3, design: .monospaced).weight(.semibold))
            }

            Text(statusText)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            VStack(alignment: .leading, spacing: 12) {
                if segments.isEmpty {
                    ContentUnavailableView(
                        "正在听",
                        systemImage: "waveform",
                        description: Text("对着麦克风说话后，这里会出现实时转写。")
                    )
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 24)
                } else {
                    ForEach(segments) { segment in
                        TranscriptLineView(segment: segment)
                    }
                }
            }

            Button(role: .destructive, action: onFinish) {
                Label("结束", systemImage: "stop.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("finishConversationButton")
        }
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
        .accessibilityIdentifier("recordingLivePanel")
    }
}

private struct TranscriptLineView: View {
    let segment: TranscriptSegmentRequest

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text(segment.speaker)
                    .font(.subheadline.weight(.semibold))
                Text(segment.timestamp)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Text(segment.text)
                .font(.body)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct CapabilityRow: View {
    let symbol: String
    let title: String
    let value: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: symbol)
                .frame(width: 28, height: 28)
                .foregroundStyle(.green)
            Text(title)
            Spacer()
            Text(value)
                .foregroundStyle(.secondary)
        }
        .font(.subheadline)
    }
}

private struct ProgressPanel: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(spacing: 14) {
            ProgressView()
            Text(title).font(.headline)
            Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(28)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct FailurePanel: View {
    let message: String
    let onReset: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "exclamationmark.triangle")
                .font(.title)
                .foregroundStyle(.orange)
            Text(message)
                .multilineTextAlignment(.center)
            Button("重来", action: onReset)
                .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity)
        .padding(28)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}
