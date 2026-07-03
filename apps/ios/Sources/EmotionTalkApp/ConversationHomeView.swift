import EmotionTalkCore
import SwiftUI

struct ConversationHomeView: View {
    @Environment(\.emotionTalkAPI) private var api
    @State private var session = ConversationSession()

    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                switch session.phase {
                case .idle:
                    IdleConversationView {
                        Task { await session.start(api: api, options: AppConfiguration.startOptions) }
                    }
                case .starting:
                    ProgressPanel(title: "创建对话", subtitle: "正在准备录音空间")
                case .recording:
                    RecordingLiveView(
                        elapsedText: session.elapsedText,
                        statusText: session.recorderStatus,
                        segments: session.liveSegments,
                        onFinish: { Task { await session.finish(api: api) } }
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
        }
        .background(Color.appGroupedBackground)
        .navigationTitle("倾诉")
    }
}

private struct IdleConversationView: View {
    let onStart: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 10) {
                Text("开始对话")
                    .font(.largeTitle.bold())
                Text("录音、实时转写、自动纪要和专家团建议会围绕同一次记录沉淀。")
                    .font(.body)
                    .foregroundStyle(.secondary)
            }

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
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
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
