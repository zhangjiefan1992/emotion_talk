import EmotionTalkCore
import SwiftUI

@main
struct EmotionTalkApp: App {
    var body: some Scene {
        WindowGroup {
            AppView()
                .environment(\.emotionTalkAPI, AppConfiguration.makeAPIClient())
        }
    }
}
