import Foundation

public enum ContextScope: String, Codable, CaseIterable, Identifiable, Sendable {
    case currentOnly = "current_only"
    case currentWithHistory = "current_with_history"

    public var id: String { rawValue }
}

public struct SpaceResponse: Codable, Equatable, Identifiable, Sendable {
    public let spaceId: String
    public let name: String
    public let createdAt: String

    public var id: String { spaceId }
}

public struct RecordingCreateRequest: Codable, Equatable, Sendable {
    public let spaceId: String
    public let title: String?
    public let startedAt: String?
    public let clientRecordingId: String?

    public init(spaceId: String, title: String? = nil, startedAt: String? = nil, clientRecordingId: String? = nil) {
        self.spaceId = spaceId
        self.title = title
        self.startedAt = startedAt
        self.clientRecordingId = clientRecordingId
    }
}

public struct RecordingResponse: Codable, Equatable, Identifiable, Sendable {
    public let recordingId: String
    public let spaceId: String
    public let clientRecordingId: String?
    public let title: String
    public let status: String
    public let startedAt: String
    public let createdAt: String
    public let transcript: TranscriptMetadata?
    public let summaryArtifact: SummaryArtifact?
    public let audioObject: AudioObject?
    public let expertAdviceJobIds: [String]

    public var id: String { recordingId }
}

public struct TranscriptMetadata: Codable, Equatable, Sendable {
    public let title: String
    public let createdAtText: String
    public let durationText: String
    public let segmentCount: Int
}

public struct AudioObject: Codable, Equatable, Sendable {
    public let objectKey: String
    public let mimeType: String
    public let byteSize: Int?
    public let checksumSha256: String?
}

public struct AudioUploadAuthorizationRequest: Codable, Equatable, Sendable {
    public let mimeType: String
    public let byteSize: Int?
    public let checksumSha256: String?

    public init(mimeType: String = "audio/mpeg", byteSize: Int? = nil, checksumSha256: String? = nil) {
        self.mimeType = mimeType
        self.byteSize = byteSize
        self.checksumSha256 = checksumSha256
    }
}

public struct AudioUploadAuthorizationResponse: Codable, Equatable, Sendable {
    public let uploadId: String
    public let recordingId: String
    public let objectKey: String
    public let mimeType: String
    public let byteSize: Int?
    public let checksumSha256: String?
    public let method: String
    public let uploadUrl: String?
    public let status: String
    public let note: String?
}

public struct AudioTranscriptionRequest: Codable, Equatable, Sendable {
    public let audioBase64: String
    public let mimeType: String
    public let title: String?
    public let createdAtText: String
    public let durationText: String

    public init(
        audioBase64: String,
        mimeType: String = "audio/x-caf",
        title: String? = nil,
        createdAtText: String = "",
        durationText: String = ""
    ) {
        self.audioBase64 = audioBase64
        self.mimeType = mimeType
        self.title = title
        self.createdAtText = createdAtText
        self.durationText = durationText
    }
}

public struct ASRSessionRequest: Codable, Equatable, Sendable {
    public let spaceId: String
    public let recordingId: String
    public let provider: String
    public let model: String

    public init(
        spaceId: String,
        recordingId: String,
        provider: String = "paraformer",
        model: String = "paraformer-realtime-8k-v2"
    ) {
        self.spaceId = spaceId
        self.recordingId = recordingId
        self.provider = provider
        self.model = model
    }
}

public struct ASRSessionResponse: Codable, Equatable, Sendable {
    public let asrSessionId: String
    public let spaceId: String
    public let recordingId: String
    public let provider: String
    public let model: String
    public let credentialMode: String
    public let expiresAt: String?
    public let sdkConfig: ASRSDKConfig
    public let status: String
    public let note: String?
}

public struct ASRSDKConfig: Codable, Equatable, Sendable {
    public let provider: String
    public let model: String
    public let temporaryApiKey: String?
}

public struct TranscriptSegmentRequest: Codable, Equatable, Identifiable, Sendable {
    public var id: String { "\(timestamp)-\(speaker)-\(text.prefix(12))" }

    public let speaker: String
    public let timestamp: String
    public let text: String
    public let startMs: Int?
    public let endMs: Int?

    public init(speaker: String, timestamp: String, text: String, startMs: Int? = nil, endMs: Int? = nil) {
        self.speaker = speaker
        self.timestamp = timestamp
        self.text = text
        self.startMs = startMs
        self.endMs = endMs
    }
}

public struct TranscriptSubmitRequest: Codable, Equatable, Sendable {
    public let markdown: String?
    public let title: String?
    public let createdAtText: String
    public let durationText: String
    public let segments: [TranscriptSegmentRequest]

    public init(
        markdown: String? = nil,
        title: String? = nil,
        createdAtText: String = "",
        durationText: String = "",
        segments: [TranscriptSegmentRequest] = []
    ) {
        self.markdown = markdown
        self.title = title
        self.createdAtText = createdAtText
        self.durationText = durationText
        self.segments = segments
    }
}

public struct SummaryArtifact: Codable, Equatable, Identifiable, Sendable {
    public let summaryJobId: String?
    public let recordingId: String?
    public let status: String
    public let title: String
    public let overview: String
    public let keyPoints: [String]
    public let chapters: [SummaryChapter]

    public var id: String { summaryJobId ?? recordingId ?? title }
}

public struct SummaryChapter: Codable, Equatable, Identifiable, Sendable {
    public var id: String { "\(startTimestamp)-\(title)" }

    public let title: String
    public let startTimestamp: String
    public let summary: String
}

public struct ExpertAdviceJobRequest: Codable, Equatable, Sendable {
    public let contextScope: ContextScope
    public let historyLimit: Int
    public let includeProfile: Bool

    public init(contextScope: ContextScope = .currentOnly, historyLimit: Int = 5, includeProfile: Bool = false) {
        self.contextScope = contextScope
        self.historyLimit = historyLimit
        self.includeProfile = includeProfile
    }
}

public struct ExpertAdviceJobResponse: Codable, Equatable, Identifiable, Sendable {
    public let jobId: String
    public let sourceType: String
    public let sourceId: String
    public let template: String
    public let status: String
    public let events: [DeliberationEvent]
    public let artifact: DeliberationArtifact
    public let contextUsage: ContextUsage

    public var id: String { jobId }
}

public struct ContextUsage: Codable, Equatable, Sendable {
    public let scope: ContextScope?
    public let primary: String?
    public let historyCount: Int
    public let historySources: [HistorySource]
    public let profileIncluded: Bool
}

public struct HistorySource: Codable, Equatable, Identifiable, Sendable {
    public var id: String { sourceId }

    public let sourceType: String
    public let sourceId: String
    public let title: String
    public let relevance: String
}

public struct DeliberationEvent: Codable, Equatable, Identifiable, Sendable {
    public let eventId: String
    public let jobId: String
    public let seq: Int
    public let type: String
    public let visibility: String
    public let payload: DeliberationEventPayload
    public let participant: String?
    public let round: Int?

    public var id: String { eventId }
}

public struct DeliberationEventPayload: Codable, Equatable, Sendable {
    public let title: String?
    public let content: String?
    public let status: String?
}

public struct DeliberationArtifact: Codable, Equatable, Sendable {
    public let overview: String
    public let processSummary: [ProcessSummary]
    public let suggestions: [Suggestion]
    public let keyUncertainties: [String]
    public let safetyBoundary: String
}

public struct ProcessSummary: Codable, Equatable, Identifiable, Sendable {
    public var id: Int { round }

    public let round: Int
    public let title: String
    public let summary: String
}

public struct Suggestion: Codable, Equatable, Identifiable, Sendable {
    public var id: String { title }

    public let title: String
    public let body: String
    public let confidence: String
    public let evidence: [String]
}
