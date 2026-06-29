import EmotionTalkCore
import Foundation

enum AppConfiguration {
    static var apiBaseURL: URL? {
        URL(string: ProcessInfo.processInfo.environment["EMOTION_TALK_API_BASE_URL"] ?? "http://127.0.0.1:8000")
    }

    static func makeAPIClient() -> any EmotionTalkAPI {
        guard let url = apiBaseURL else {
            return PreviewEmotionTalkAPIClient()
        }
        return EmotionTalkHTTPClient(baseURL: url)
    }

    static var realtimeASRURL: URL? {
        realtimeASRURL(for: apiBaseURL)
    }

    static func realtimeASRURL(for apiBaseURL: URL?) -> URL? {
        guard var components = apiBaseURL.flatMap({ URLComponents(url: $0, resolvingAgainstBaseURL: false) }) else {
            return nil
        }
        components.scheme = components.scheme == "https" ? "wss" : "ws"
        let basePath = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = "/" + [basePath, "asr/realtime"].filter { !$0.isEmpty }.joined(separator: "/")
        return components.url
    }

    static var startOptions: ConversationStartOptions {
        let environment = ProcessInfo.processInfo.environment
        return ConversationStartOptions(
            testAudioURL: environment.urlValue(for: "EMOTION_TALK_TEST_AUDIO_URL"),
            testTranscriptURL: environment.urlValue(for: "EMOTION_TALK_TEST_TRANSCRIPT_URL"),
            autoFinish: environment.boolValue(for: "EMOTION_TALK_AUTO_FINISH_TEST_AUDIO"),
            autoRequestAdvice: environment.boolValue(for: "EMOTION_TALK_AUTO_REQUEST_ADVICE")
        )
    }
}

private extension Dictionary where Key == String, Value == String {
    func urlValue(for key: String) -> URL? {
        guard let value = self[key], !value.isEmpty else { return nil }
        if let url = URL(string: value), url.scheme != nil {
            return url
        }
        return URL(fileURLWithPath: value)
    }

    func boolValue(for key: String) -> Bool {
        guard let value = self[key]?.lowercased() else { return false }
        return ["1", "true", "yes"].contains(value)
    }
}
