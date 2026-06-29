import EmotionTalkCore
import Foundation

@main
struct EmotionTalkAPISmoke {
    static func main() async throws {
        let baseURLValue = ProcessInfo.processInfo.environment["EMOTION_TALK_API_BASE_URL"] ?? "http://127.0.0.1:8000"
        guard let baseURL = URL(string: baseURLValue) else {
            throw SmokeError.invalidBaseURL(baseURLValue)
        }

        let client = EmotionTalkHTTPClient(baseURL: baseURL)
        let space = try await client.createSpace(name: "Swift 联调空间")
        let recording = try await client.createRecording(
            RecordingCreateRequest(spaceId: space.spaceId, title: "Swift API smoke")
        )
        let asrSession = try await client.createASRSession(
            ASRSessionRequest(spaceId: space.spaceId, recordingId: recording.recordingId)
        )
        let updatedRecording = try await client.submitTranscript(
            recordingId: recording.recordingId,
            request: TranscriptSubmitRequest(
                title: "Swift API smoke",
                createdAtText: "2026-06-24 10:00",
                durationText: "00:42",
                segments: [
                    TranscriptSegmentRequest(
                        speaker: "我",
                        timestamp: "00:00",
                        text: "我想先走通 iOS 到服务端的真实链路。",
                        startMs: 0,
                        endMs: 4200
                    ),
                    TranscriptSegmentRequest(
                        speaker: "伴侣",
                        timestamp: "00:05",
                        text: "先把记录、摘要和专家团流程稳定下来。",
                        startMs: 5000,
                        endMs: 8600
                    )
                ]
            )
        )
        let summary = try await client.createSummaryJob(recordingId: recording.recordingId)
        let advice = try await client.createExpertAdviceJob(
            recordingId: recording.recordingId,
            request: ExpertAdviceJobRequest(contextScope: .currentOnly, historyLimit: 0, includeProfile: false)
        )
        let events = try await client.fetchExpertAdviceEvents(jobId: advice.jobId)
        let artifact = try await client.fetchExpertAdviceArtifact(jobId: advice.jobId)

        print("spaceId=\(space.spaceId)")
        print("recordingId=\(recording.recordingId)")
        print("asrSessionId=\(asrSession.asrSessionId)")
        print("recordingStatus=\(updatedRecording.status)")
        print("summaryStatus=\(summary.status)")
        print("adviceStatus=\(advice.status)")
        print("contextScope=\(advice.contextUsage.scope?.rawValue ?? "nil")")
        print("eventCount=\(events.count)")
        print("suggestionCount=\(artifact.suggestions.count)")

        guard updatedRecording.status == "transcribed",
              summary.status == "completed",
              advice.status == "completed",
              events.count >= 10,
              !artifact.suggestions.isEmpty
        else {
            throw SmokeError.unexpectedResponse
        }
    }
}

enum SmokeError: Error {
    case invalidBaseURL(String)
    case unexpectedResponse
}
