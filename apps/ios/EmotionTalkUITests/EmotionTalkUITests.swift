import XCTest

final class EmotionTalkUITests: XCTestCase {
    private var testAPIBaseURL: String {
        ProcessInfo.processInfo.environment["EMOTION_TALK_UI_TEST_API_BASE_URL"]
            ?? ProcessInfo.processInfo.environment["EMOTION_TALK_API_BASE_URL"]
            ?? "http://127.0.0.1:8000"
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLiveMicrophoneRecordingCreatesSummary() throws {
        try XCTSkipUnless(
            ProcessInfo.processInfo.environment["EMOTION_TALK_RUN_LIVE_MIC_TEST"] == "1",
            "Set EMOTION_TALK_RUN_LIVE_MIC_TEST=1 to run the live microphone acceptance test."
        )

        let app = XCUIApplication()
        app.launchEnvironment["EMOTION_TALK_API_BASE_URL"] = testAPIBaseURL
        app.launch()
        addUIInterruptionMonitor(withDescription: "Microphone Permission") { alert in
            for title in ["允许", "Allow"] where alert.buttons[title].exists {
                alert.buttons[title].tap()
                return true
            }
            return false
        }

        XCTAssertTrue(app.buttons["startConversationButton"].waitForExistence(timeout: 8))
        app.buttons["startConversationButton"].tap()
        app.tap()

        XCTAssertTrue(app.staticTexts["录音中"].waitForExistence(timeout: 12), app.debugDescription)
        Thread.sleep(forTimeInterval: 12)
        XCTAssertTrue(app.buttons["结束"].waitForExistence(timeout: 8), app.debugDescription)
        app.buttons["结束"].tap()

        let detailTabs = app.segmentedControls["recordingDetailTabs"]
        XCTAssertTrue(detailTabs.waitForExistence(timeout: 120), app.debugDescription)
        detailTabs.buttons["转写"].tap()
        XCTAssertTrue(app.staticTexts["片段"].waitForExistence(timeout: 8))
    }

    func testRecordingSummaryAndExpertAdviceFlow() throws {
        let app = XCUIApplication()
        app.launchEnvironment["EMOTION_TALK_API_BASE_URL"] = testAPIBaseURL
        app.launchEnvironment["EMOTION_TALK_TEST_AUDIO_URL"] = ProcessInfo.processInfo.environment["EMOTION_TALK_TEST_AUDIO_URL"] ?? "/Users/jeff/Downloads/06-13 职业转型与长期规划.mp3"
        app.launchEnvironment["EMOTION_TALK_TEST_TRANSCRIPT_URL"] = ProcessInfo.processInfo.environment["EMOTION_TALK_TEST_TRANSCRIPT_URL"] ?? "http://127.0.0.1:8000/dev-fixtures/career-transition-transcript"
        app.launchEnvironment["EMOTION_TALK_AUTO_FINISH_TEST_AUDIO"] = "1"
        app.launchEnvironment["EMOTION_TALK_AUTO_REQUEST_ADVICE"] = "1"
        app.launch()

        XCTAssertTrue(app.buttons["startConversationButton"].waitForExistence(timeout: 8))
        app.buttons["startConversationButton"].tap()

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
