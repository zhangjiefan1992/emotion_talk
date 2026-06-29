import XCTest
@testable import EmotionTalkCore

final class EmotionTalkModelTests: XCTestCase {
    func testHTTPClientKeepsBasePathWhenBuildingNestedRequests() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [URLCaptureProtocol.self]
        let session = URLSession(configuration: configuration)
        URLCaptureProtocol.responseData = Data("[]".utf8)
        URLCaptureProtocol.lastURL = nil

        let client = EmotionTalkHTTPClient(
            baseURL: URL(string: "http://example.com/api")!,
            session: session
        )

        _ = try await client.fetchExpertAdviceEvents(jobId: "job_1")

        XCTAssertEqual(
            URLCaptureProtocol.lastURL?.absoluteString,
            "http://example.com/api/expert-advice-jobs/job_1/events"
        )
    }

    func testExpertAdviceDecodesContextUsageAndTimelineEvents() throws {
        let json = """
        {
          "jobId": "job_1",
          "sourceType": "recording",
          "sourceId": "rec_1",
          "template": "emotion_talk_expert_team_v1",
          "status": "completed",
          "contextUsage": {
            "scope": "current_with_history",
            "primary": "current_recording",
            "historyCount": 1,
            "historySources": [
              {
                "sourceType": "recording",
                "sourceId": "rec_history",
                "title": "上一次复盘",
                "relevance": "same_space_recent"
              }
            ],
            "profileIncluded": true
          },
          "events": [
            {
              "eventId": "evt_1",
              "jobId": "job_1",
              "seq": 1,
              "type": "expert_message_added",
              "visibility": "user_visible",
              "payload": {"title": "初判", "content": "先稳定主线。"},
              "participant": "life_coach",
              "round": 1
            }
          ],
          "artifact": {
            "overview": "裁判结论",
            "processSummary": [
              {"round": 1, "title": "初判", "summary": "初步判断"}
            ],
            "suggestions": [
              {"title": "建议一", "body": "保持小步验证。", "confidence": "medium", "evidence": ["对话证据"]}
            ],
            "keyUncertainties": ["不确定性"],
            "safetyBoundary": "不是医疗或职业承诺。"
          }
        }
        """.data(using: .utf8)!

        let job = try JSONDecoder().decode(ExpertAdviceJobResponse.self, from: json)

        XCTAssertEqual(job.contextUsage.scope, .currentWithHistory)
        XCTAssertEqual(job.contextUsage.historySources.first?.sourceId, "rec_history")
        XCTAssertEqual(job.events.first?.payload.content, "先稳定主线。")
        XCTAssertEqual(job.artifact.suggestions.first?.title, "建议一")
    }

    func testPreviewClientCreatesCurrentOnlyAdviceByDefault() async throws {
        let client = PreviewEmotionTalkAPIClient()

        let job = try await client.createExpertAdviceJob(
            recordingId: "rec_preview",
            request: ExpertAdviceJobRequest(contextScope: .currentOnly)
        )

        XCTAssertEqual(job.contextUsage.scope, .currentOnly)
        XCTAssertEqual(job.contextUsage.historyCount, 0)
        XCTAssertEqual(job.events.count, 9)
    }
}

private final class URLCaptureProtocol: URLProtocol {
    static var lastURL: URL?
    static var responseData = Data()

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        Self.lastURL = request.url
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Self.responseData)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}
