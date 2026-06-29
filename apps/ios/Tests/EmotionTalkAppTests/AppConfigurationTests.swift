import XCTest
@testable import EmotionTalkApp

final class AppConfigurationTests: XCTestCase {
    func testRealtimeASRURLKeepsAPIBasePath() {
        XCTAssertEqual(
            AppConfiguration.realtimeASRURL(for: URL(string: "http://121.41.92.161/api"))?.absoluteString,
            "ws://121.41.92.161/api/asr/realtime"
        )
    }
}
