import EmotionTalkCore
import SwiftUI

private struct EmotionTalkAPIKey: EnvironmentKey {
    static let defaultValue: any EmotionTalkAPI = PreviewEmotionTalkAPIClient()
}

extension EnvironmentValues {
    var emotionTalkAPI: any EmotionTalkAPI {
        get { self[EmotionTalkAPIKey.self] }
        set { self[EmotionTalkAPIKey.self] = newValue }
    }
}
