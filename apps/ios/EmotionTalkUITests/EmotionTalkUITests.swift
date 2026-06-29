import XCTest

final class EmotionTalkUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLiveMicrophoneRecordingCreatesSummary() throws {
        try XCTSkipUnless(
            ProcessInfo.processInfo.environment["EMOTION_TALK_RUN_LIVE_MIC_TEST"] == "1",
            "Set EMOTION_TALK_RUN_LIVE_MIC_TEST=1 to run the live microphone acceptance test."
        )

        let app = XCUIApplication()
        app.launchEnvironment["EMOTION_TALK_API_BASE_URL"] = ProcessInfo.processInfo.environment["EMOTION_TALK_API_BASE_URL"] ?? "http://127.0.0.1:8000"
        app.launch()

        XCTAssertTrue(app.buttons["startConversationButton"].waitForExistence(timeout: 8))
        app.buttons["startConversationButton"].tap()

        XCTAssertTrue(app.staticTexts["录音中"].waitForExistence(timeout: 12))
        Thread.sleep(forTimeInterval: 12)
        XCTAssertTrue(app.buttons["finishConversationButton"].waitForExistence(timeout: 8))
        app.buttons["finishConversationButton"].tap()

        let detailTabs = app.segmentedControls["recordingDetailTabs"]
        XCTAssertTrue(detailTabs.waitForExistence(timeout: 120), app.debugDescription)
        detailTabs.buttons["转写"].tap()
        XCTAssertTrue(app.staticTexts["片段"].waitForExistence(timeout: 8))
    }

    func testRecordingSummaryAndExpertAdviceFlow() throws {
        let app = XCUIApplication()
        app.launchEnvironment["EMOTION_TALK_API_BASE_URL"] = ProcessInfo.processInfo.environment["EMOTION_TALK_API_BASE_URL"] ?? "http://127.0.0.1:8000"
        app.launchEnvironment["EMOTION_TALK_TEST_AUDIO_URL"] = ProcessInfo.processInfo.environment["EMOTION_TALK_TEST_AUDIO_URL"] ?? "/Users/jeff/Downloads/06-13 职业转型与长期规划.mp3"
        app.launchEnvironment["EMOTION_TALK_TEST_TRANSCRIPT_URL"] = ProcessInfo.processInfo.environment["EMOTION_TALK_TEST_TRANSCRIPT_URL"] ?? "http://127.0.0.1:8000/dev-fixtures/career-transition-transcript"
        app.launchEnvironment["EMOTION_TALK_AUTO_FINISH_TEST_AUDIO"] = "1"
        app.launchEnvironment["EMOTION_TALK_AUTO_REQUEST_ADVICE"] = "1"
        app.launch()

        XCTAssertTrue(app.buttons["startConversationButton"].waitForExistence(timeout: 8))
        app.buttons["startConversationButton"].tap()

        XCTAssertTrue(app.staticTexts["录音中"].waitForExistence(timeout: 12))
        XCTAssertFalse(app.buttons["模拟转写"].exists)

        let detailTabs = app.segmentedControls["recordingDetailTabs"]
        XCTAssertTrue(detailTabs.waitForExistence(timeout: 60), app.debugDescription)
        detailTabs.buttons["转写"].tap()
        XCTAssertTrue(app.staticTexts["录音文件"].waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts["片段"].exists)
        detailTabs.buttons["专家团"].tap()

        XCTAssertTrue(app.staticTexts["裁判结论"].waitForExistence(timeout: 60), app.debugDescription)
    }
}
