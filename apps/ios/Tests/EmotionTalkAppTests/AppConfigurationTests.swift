import XCTest
@testable import EmotionTalkCore
@testable import EmotionTalkApp

final class AppConfigurationTests: XCTestCase {
    func testRealtimeASRURLKeepsAPIBasePath() {
        XCTAssertEqual(
            AppConfiguration.realtimeASRURL(for: URL(string: "http://121.41.92.161/api"))?.absoluteString,
            "ws://121.41.92.161/api/asr/realtime"
        )
    }

    @MainActor
    func testSpaceStoreRejectsDuplicateSpaceNameBeforeCallingAPI() async {
        let api = SpaceAPIStub()
        let store = SpaceStore(ownerId: "test_user")
        store.spaces = [
            SpaceResponse(spaceId: "space_1", ownerId: "test_user", name: "家的倾诉空间", isCurrent: true, createdAt: "2026-07-07T00:00:00Z")
        ]
        store.currentSpaceId = "space_1"

        await store.createSpace(api: api, name: " 家的倾诉空间 ")

        XCTAssertEqual(api.createdNames, [])
        XCTAssertEqual(store.errorMessage, "同一个用户下的空间不可重名。")
    }
}

private final class SpaceAPIStub: EmotionTalkAPI {
    var createdNames: [String] = []

    func listSpaces(ownerId: String) async throws -> SpacesResponse {
        SpacesResponse(
            ownerId: ownerId,
            currentSpaceId: "space_1",
            spaces: [SpaceResponse(spaceId: "space_1", ownerId: ownerId, name: "家的倾诉空间", isCurrent: true, createdAt: "2026-07-07T00:00:00Z")]
        )
    }

    func createSpace(name: String, ownerId: String) async throws -> SpaceResponse {
        createdNames.append(name)
        return SpaceResponse(spaceId: "space_new", ownerId: ownerId, name: name, isCurrent: false, createdAt: "2026-07-07T00:00:00Z")
    }

    func setCurrentSpace(ownerId: String, spaceId: String) async throws -> SpacesResponse { try await listSpaces(ownerId: ownerId) }
    func listRecordings(spaceId: String) async throws -> [RecordingResponse] { [] }
    func createRecording(_ request: RecordingCreateRequest) async throws -> RecordingResponse { fatalError("unused") }
    func createASRSession(_ request: ASRSessionRequest) async throws -> ASRSessionResponse { fatalError("unused") }
    func createAudioUploadAuthorization(recordingId: String, request: AudioUploadAuthorizationRequest) async throws -> AudioUploadAuthorizationResponse { fatalError("unused") }
    func transcribeAudio(recordingId: String, request: AudioTranscriptionRequest) async throws -> RecordingResponse { fatalError("unused") }
    func submitTranscript(recordingId: String, request: TranscriptSubmitRequest) async throws -> RecordingResponse { fatalError("unused") }
    func createSummaryJob(recordingId: String) async throws -> SummaryArtifact { fatalError("unused") }
    func createExpertAdviceJob(recordingId: String, request: ExpertAdviceJobRequest) async throws -> ExpertAdviceJobResponse { fatalError("unused") }
    func fetchExpertAdviceJob(jobId: String) async throws -> ExpertAdviceJobResponse { fatalError("unused") }
    func fetchExpertAdviceEvents(jobId: String) async throws -> [DeliberationEvent] { fatalError("unused") }
    func fetchExpertAdviceArtifact(jobId: String) async throws -> DeliberationArtifact { fatalError("unused") }
}
