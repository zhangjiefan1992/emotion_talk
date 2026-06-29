import EmotionTalkCore
import SwiftUI

struct ExpertAdviceTimelineView: View {
    let job: ExpertAdviceJobResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            ContextUsageView(context: job.contextUsage)
            JudgeView(artifact: job.artifact)

            ForEach(rounds, id: \.number) { round in
                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(String(format: "%02d", round.number))
                            .font(.headline.monospacedDigit())
                            .foregroundStyle(.green)
                        Text(round.title)
                            .font(.headline)
                    }

                    ForEach(round.events) { event in
                        ExpertEventCard(event: event)
                    }
                }
                .padding(.top, 4)
            }
        }
    }

    private var rounds: [(number: Int, title: String, events: [DeliberationEvent])] {
        let grouped = Dictionary(grouping: job.events.filter { $0.round != nil }) { $0.round ?? 0 }
        return grouped.keys.sorted().map { round in
            (round, title(for: round), grouped[round, default: []].sorted { $0.seq < $1.seq })
        }
    }

    private func title(for round: Int) -> String {
        switch round {
        case 1: "第一轮：初判"
        case 2: "第二轮：互评"
        case 3: "第三轮：修正"
        default: "第 \(round) 轮"
        }
    }
}

private struct ContextUsageView: View {
    let context: ContextUsage

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("上下文")
                .font(.headline)
            HStack {
                Label(context.scope?.rawValue ?? "current_only", systemImage: "scope")
                Spacer()
                Text("历史 \(context.historyCount)")
                    .foregroundStyle(.secondary)
            }
            .font(.subheadline)

            ForEach(context.historySources) { source in
                VStack(alignment: .leading, spacing: 4) {
                    Text(source.title).font(.subheadline.weight(.semibold))
                    Text(source.relevance).font(.caption).foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
            }
        }
    }
}

private struct JudgeView: View {
    let artifact: DeliberationArtifact

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("裁判结论")
                .font(.headline)
            Text(artifact.overview)
            ForEach(artifact.suggestions) { suggestion in
                VStack(alignment: .leading, spacing: 6) {
                    Text(suggestion.title)
                        .font(.subheadline.weight(.semibold))
                    Text(suggestion.body)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
            }
        }
        .accessibilityIdentifier("judgeConclusionSection")
    }
}

private struct ExpertEventCard: View {
    let event: DeliberationEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(participantName)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(event.participant ?? "unknown")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
            }
            Text(event.payload.content ?? "")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.appSecondaryGroupedBackground, in: RoundedRectangle(cornerRadius: 8))
    }

    private var participantName: String {
        switch event.participant {
        case "life_coach": "人生教练"
        case "counselor": "心理咨询视角"
        case "reality_strategist": "现实行动视角"
        default: "专家"
        }
    }
}
