import EmotionTalkCore
import SwiftUI

struct AppView: View {
    @Environment(\.emotionTalkAPI) private var api
    @State private var selectedTab: AppTab = .space
    @State private var spaceStore = SpaceStore()

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                ConversationHomeView(spaceStore: spaceStore)
            }
            .tabItem { Label("空间", systemImage: "house") }
            .tag(AppTab.space)

            NavigationStack {
                LibraryView(spaceStore: spaceStore)
            }
            .tabItem { Label("记录", systemImage: "doc.text") }
            .tag(AppTab.records)

            NavigationStack {
                TopicsView()
            }
            .tabItem { Label("主题", systemImage: "list.bullet") }
            .tag(AppTab.topics)

            NavigationStack {
                MySpacesView(spaceStore: spaceStore)
            }
            .tabItem { Label("我的", systemImage: "line.3.horizontal") }
            .tag(AppTab.mine)
        }
        .task {
            if spaceStore.spaces.isEmpty {
                await spaceStore.load(api: api)
            }
        }
    }
}

private enum AppTab: Hashable {
    case space
    case records
    case topics
    case mine
}

private struct LibraryView: View {
    let spaceStore: SpaceStore

    var body: some View {
        List {
            if spaceStore.records.isEmpty {
                ContentUnavailableView("暂无记录", systemImage: "doc.text.magnifyingglass")
            } else {
                ForEach(spaceStore.records) { record in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(record.title)
                            .font(.headline)
                        Text(record.transcript?.durationText.isEmpty == false ? record.transcript?.durationText ?? "" : record.status)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
            .navigationTitle("记录")
    }
}

private struct TopicsView: View {
    var body: some View {
        ContentUnavailableView("还没有主题", systemImage: "list.bullet", description: Text("完成几次真实倾诉后，再从纪要里沉淀反复出现的主题。"))
            .navigationTitle("主题")
    }
}

private struct MySpacesView: View {
    @Environment(\.emotionTalkAPI) private var api
    let spaceStore: SpaceStore
    @State private var newSpaceName = ""

    var body: some View {
        List {
            Section("空间管理") {
                ForEach(spaceStore.spaces) { space in
                    Button {
                        Task { await spaceStore.selectSpace(api: api, spaceId: space.spaceId) }
                    } label: {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(space.name)
                                Text(space.spaceId)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text(space.spaceId == spaceStore.currentSpaceId ? "当前" : "切换")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(space.spaceId == spaceStore.currentSpaceId ? .blue : .secondary)
                        }
                    }
                }
            }

            Section("创建空间") {
                TextField("新空间名称", text: $newSpaceName)
                Button("创建") {
                    let name = newSpaceName
                    newSpaceName = ""
                    Task { await spaceStore.createSpace(api: api, name: name) }
                }
                .disabled(spaceStore.spaces.count >= 5 || newSpaceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }

            if let error = spaceStore.errorMessage {
                Section {
                    Text(error)
                        .foregroundStyle(.red)
                }
            }
        }
        .navigationTitle("我的")
    }
}

@MainActor
@Observable
final class SpaceStore {
    var spaces: [SpaceResponse] = []
    var currentSpaceId: String?
    var records: [RecordingResponse] = []
    var errorMessage: String?
    var isLoading = false

    let ownerId: String

    init(ownerId: String? = nil) {
        self.ownerId = ownerId ?? Self.defaultOwnerId()
    }

    var currentSpace: SpaceResponse? {
        spaces.first { $0.spaceId == currentSpaceId } ?? spaces.first
    }

    func load(api: any EmotionTalkAPI) async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await api.listSpaces(ownerId: ownerId)
            apply(response)
            try await loadRecords(api: api)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createSpace(api: any EmotionTalkAPI, name: String) async {
        let clean = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return }
        do {
            _ = try await api.createSpace(name: clean, ownerId: ownerId)
            await load(api: api)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func selectSpace(api: any EmotionTalkAPI, spaceId: String) async {
        guard spaceId != currentSpaceId else { return }
        do {
            apply(try await api.setCurrentSpace(ownerId: ownerId, spaceId: spaceId))
            try await loadRecords(api: api)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadRecords(api: any EmotionTalkAPI) async throws {
        guard let currentSpaceId else { return }
        records = try await api.listRecordings(spaceId: currentSpaceId)
    }

    private func apply(_ response: SpacesResponse) {
        spaces = response.spaces
        currentSpaceId = response.currentSpaceId
    }

    private static func defaultOwnerId() -> String {
        let key = "emotion_talk_owner_id"
        if let existing = UserDefaults.standard.string(forKey: key) {
            return existing
        }
        let created = "ios_user_\(UUID().uuidString)"
        UserDefaults.standard.set(created, forKey: key)
        return created
    }
}
