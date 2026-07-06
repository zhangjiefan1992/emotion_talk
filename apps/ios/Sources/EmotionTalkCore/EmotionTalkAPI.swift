import Foundation

public protocol EmotionTalkAPI {
    func createSpace(name: String) async throws -> SpaceResponse
    func createRecording(_ request: RecordingCreateRequest) async throws -> RecordingResponse
    func createASRSession(_ request: ASRSessionRequest) async throws -> ASRSessionResponse
    func createAudioUploadAuthorization(recordingId: String, request: AudioUploadAuthorizationRequest) async throws -> AudioUploadAuthorizationResponse
    func transcribeAudio(recordingId: String, request: AudioTranscriptionRequest) async throws -> RecordingResponse
    func submitTranscript(recordingId: String, request: TranscriptSubmitRequest) async throws -> RecordingResponse
    func createSummaryJob(recordingId: String) async throws -> SummaryArtifact
    func createExpertAdviceJob(recordingId: String, request: ExpertAdviceJobRequest) async throws -> ExpertAdviceJobResponse
    func fetchExpertAdviceJob(jobId: String) async throws -> ExpertAdviceJobResponse
    func fetchExpertAdviceEvents(jobId: String) async throws -> [DeliberationEvent]
    func fetchExpertAdviceArtifact(jobId: String) async throws -> DeliberationArtifact
}

public enum EmotionTalkAPIError: Error, Equatable {
    case invalidURL(String)
    case badStatus(Int)
    case emptyResponse
}

public struct EmotionTalkHTTPClient: EmotionTalkAPI {
    private let baseURL: URL
    private let session: URLSession
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(baseURL: URL = URL(string: "http://127.0.0.1:8000")!, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
    }

    public func createSpace(name: String) async throws -> SpaceResponse {
        try await send(path: "/spaces", method: "POST", body: ["name": name])
    }

    public func createRecording(_ request: RecordingCreateRequest) async throws -> RecordingResponse {
        try await send(path: "/recordings", method: "POST", body: request)
    }

    public func createASRSession(_ request: ASRSessionRequest) async throws -> ASRSessionResponse {
        try await send(path: "/asr-sessions", method: "POST", body: request)
    }

    public func createAudioUploadAuthorization(recordingId: String, request: AudioUploadAuthorizationRequest) async throws -> AudioUploadAuthorizationResponse {
        try await send(path: "/recordings/\(recordingId)/audio-upload-authorizations", method: "POST", body: request)
    }

    public func transcribeAudio(recordingId: String, request: AudioTranscriptionRequest) async throws -> RecordingResponse {
        try await send(path: "/recordings/\(recordingId)/audio-transcriptions", method: "POST", body: request)
    }

    public func submitTranscript(recordingId: String, request: TranscriptSubmitRequest) async throws -> RecordingResponse {
        try await send(path: "/recordings/\(recordingId)/transcript", method: "POST", body: request)
    }

    public func createSummaryJob(recordingId: String) async throws -> SummaryArtifact {
        try await send(path: "/recordings/\(recordingId)/summary-jobs", method: "POST", body: EmptyRequest())
    }

    public func createExpertAdviceJob(recordingId: String, request: ExpertAdviceJobRequest) async throws -> ExpertAdviceJobResponse {
        try await send(path: "/recordings/\(recordingId)/expert-advice-jobs", method: "POST", body: request)
    }

    public func fetchExpertAdviceJob(jobId: String) async throws -> ExpertAdviceJobResponse {
        try await send(path: "/expert-advice-jobs/\(jobId)", method: "GET", body: Optional<EmptyRequest>.none)
    }

    public func fetchExpertAdviceEvents(jobId: String) async throws -> [DeliberationEvent] {
        try await send(path: "/expert-advice-jobs/\(jobId)/events", method: "GET", body: Optional<EmptyRequest>.none)
    }

    public func fetchExpertAdviceArtifact(jobId: String) async throws -> DeliberationArtifact {
        try await send(path: "/expert-advice-jobs/\(jobId)/artifact", method: "GET", body: Optional<EmptyRequest>.none)
    }

    private func send<Response: Decodable, Body: Encodable>(
        path: String,
        method: String,
        body: Body?
    ) async throws -> Response {
        let normalizedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard !normalizedPath.isEmpty else {
            throw EmotionTalkAPIError.invalidURL(path)
        }
        let url = normalizedPath
            .split(separator: "/")
            .reduce(baseURL) { partial, component in
                partial.appendingPathComponent(String(component))
            }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw EmotionTalkAPIError.emptyResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw EmotionTalkAPIError.badStatus(http.statusCode)
        }
        guard !data.isEmpty else {
            throw EmotionTalkAPIError.emptyResponse
        }
        return try decoder.decode(Response.self, from: data)
    }
}

private struct EmptyRequest: Encodable {}
