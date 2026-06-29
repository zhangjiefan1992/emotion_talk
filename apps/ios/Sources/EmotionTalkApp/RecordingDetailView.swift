import EmotionTalkCore
import SwiftUI

struct RecordingDetailView: View {
    let recording: RecordingResponse
    let summary: SummaryArtifact
    let expertAdvice: ExpertAdviceJobResponse?
    let advicePhase: AdvicePhase
    let onRequestAdvice: (ContextScope) -> Void
    let onReset: () -> Void

    @State private var selectedTab: DetailTab = .summary
    @State private var contextScope: ContextScope = .currentOnly

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HeaderCard(recording: recording)

            Picker("详情", selection: $selectedTab) {
                ForEach(DetailTab.allCases) { tab in
                    Text(tab.title).tag(tab)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityIdentifier("recordingDetailTabs")

            switch selectedTab {
            case .summary:
                SummaryView(summary: summary)
            case .transcript:
                TranscriptMetadataView(recording: recording)
            case .advice:
                AdviceRequestView(
                    expertAdvice: expertAdvice,
                    advicePhase: advicePhase,
                    contextScope: $contextScope,
                    onRequestAdvice: onRequestAdvice
                )
            }

            Button(action: onReset) {
                Label("新的对话", systemImage: "plus.circle")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
        }
    }
}

private enum DetailTab: String, CaseIterable, Identifiable {
    case summary
    case transcript
    case advice

    var id: String { rawValue }

    var title: String {
        switch self {
        case .summary: "纪要"
        case .transcript: "转写"
        case .advice: "专家团"
        }
    }
}

private struct HeaderCard: View {
    let recording: RecordingResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(recording.title)
                .font(.title.bold())
            HStack {
                Label(recording.status, systemImage: "checkmark.circle")
                Spacer()
                Text(recording.recordingId)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct SummaryView: View {
    let summary: SummaryArtifact

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(summary.overview)
                .font(.body)

            VStack(alignment: .leading, spacing: 10) {
                ForEach(summary.keyPoints, id: \.self) { point in
                    Label(point, systemImage: "checkmark")
                        .font(.subheadline)
                }
            }

            ForEach(summary.chapters) { chapter in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(chapter.title).font(.headline)
                        Spacer()
                        Text(chapter.startTimestamp).font(.caption).foregroundStyle(.secondary)
                    }
                    Text(chapter.summary)
                        .foregroundStyle(.secondary)
                }
                .padding(14)
                .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct TranscriptMetadataView: View {
    let recording: RecordingResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let transcript = recording.transcript {
                MetadataRow(title: "标题", value: transcript.title)
                MetadataRow(title: "创建时间", value: transcript.createdAtText)
                MetadataRow(title: "时长", value: transcript.durationText)
                MetadataRow(title: "片段", value: "\(transcript.segmentCount)")
                if let audioObject = recording.audioObject {
                    MetadataRow(title: "录音文件", value: audioObject.mimeType)
                    MetadataRow(title: "对象键", value: audioObject.objectKey)
                }
            } else {
                ContentUnavailableView("暂无转写", systemImage: "text.bubble")
            }
        }
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct AdviceRequestView: View {
    let expertAdvice: ExpertAdviceJobResponse?
    let advicePhase: AdvicePhase
    @Binding var contextScope: ContextScope
    let onRequestAdvice: (ContextScope) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Picker("上下文", selection: $contextScope) {
                Text("本次").tag(ContextScope.currentOnly)
                Text("结合历史").tag(ContextScope.currentWithHistory)
            }
            .pickerStyle(.segmented)

            switch advicePhase {
            case .idle:
                Button {
                    onRequestAdvice(contextScope)
                } label: {
                    Label("生成专家团建议", systemImage: "person.3.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("requestExpertAdviceButton")
            case .loading:
                ProgressView("专家团讨论中")
                    .frame(maxWidth: .infinity)
            case .loaded:
                if let expertAdvice {
                    ExpertAdviceTimelineView(job: expertAdvice)
                }
            case .failed(let message):
                Label(message, systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.orange)
            }
        }
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct MetadataRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack {
            Text(title).foregroundStyle(.secondary)
            Spacer()
            Text(value).fontWeight(.semibold)
        }
    }
}
