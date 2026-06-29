import SwiftUI

struct AppView: View {
    @State private var selectedTab: AppTab = .conversation

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                ConversationHomeView()
            }
            .tabItem { Label("对话", systemImage: "waveform") }
            .tag(AppTab.conversation)

            NavigationStack {
                LibraryView()
            }
            .tabItem { Label("记录", systemImage: "doc.text") }
            .tag(AppTab.library)
        }
    }
}

private enum AppTab: Hashable {
    case conversation
    case library
}

private struct LibraryView: View {
    var body: some View {
        ContentUnavailableView("暂无记录", systemImage: "doc.text.magnifyingglass")
            .navigationTitle("记录")
    }
}
