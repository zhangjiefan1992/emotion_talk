import Foundation

public struct PreviewEmotionTalkAPIClient: EmotionTalkAPI {
    public init() {}

    public func listSpaces(ownerId: String) async throws -> SpacesResponse {
        SpacesResponse(
            ownerId: ownerId,
            currentSpaceId: "space_preview",
            spaces: [
                SpaceResponse(spaceId: "space_preview", ownerId: ownerId, name: "家的倾诉空间", isCurrent: true, createdAt: "2026-06-24T10:00:00Z")
            ]
        )
    }

    public func createSpace(name: String, ownerId: String) async throws -> SpaceResponse {
        SpaceResponse(spaceId: "space_preview_new", ownerId: ownerId, name: name, isCurrent: false, createdAt: "2026-06-24T10:00:00Z")
    }

    public func setCurrentSpace(ownerId: String, spaceId: String) async throws -> SpacesResponse {
        SpacesResponse(
            ownerId: ownerId,
            currentSpaceId: spaceId,
            spaces: [
                SpaceResponse(spaceId: spaceId, ownerId: ownerId, name: "家的倾诉空间", isCurrent: true, createdAt: "2026-06-24T10:00:00Z")
            ]
        )
    }

    public func listRecordings(spaceId: String) async throws -> [RecordingResponse] {
        []
    }

    public func createRecording(_ request: RecordingCreateRequest) async throws -> RecordingResponse {
        RecordingResponse(
            recordingId: "rec_preview",
            spaceId: request.spaceId,
            clientRecordingId: request.clientRecordingId,
            title: request.title ?? "今天的对话",
            status: "recording",
            startedAt: request.startedAt ?? "2026-06-24T10:00:00Z",
            createdAt: "2026-06-24T10:00:00Z",
            transcript: nil,
            summaryArtifact: nil,
            audioObject: nil,
            expertAdviceJobIds: []
        )
    }

    public func createASRSession(_ request: ASRSessionRequest) async throws -> ASRSessionResponse {
        ASRSessionResponse(
            asrSessionId: "asr_preview",
            spaceId: request.spaceId,
            recordingId: request.recordingId,
            provider: request.provider,
            model: request.model,
            credentialMode: "temporary_api_key",
            expiresAt: nil,
            sdkConfig: ASRSDKConfig(provider: request.provider, model: request.model, temporaryApiKey: nil),
            status: "dev_stub",
            note: "Preview ASR session"
        )
    }

    public func createAudioUploadAuthorization(recordingId: String, request: AudioUploadAuthorizationRequest) async throws -> AudioUploadAuthorizationResponse {
        AudioUploadAuthorizationResponse(
            uploadId: "upload_preview",
            recordingId: recordingId,
            objectKey: "preview/source.mp3",
            mimeType: request.mimeType,
            byteSize: request.byteSize,
            checksumSha256: request.checksumSha256,
            method: "PUT",
            uploadUrl: nil,
            status: "dev_stub",
            note: "preview"
        )
    }

    public func transcribeAudio(recordingId: String, request: AudioTranscriptionRequest) async throws -> RecordingResponse {
        RecordingResponse(
            recordingId: recordingId,
            spaceId: "space_preview",
            clientRecordingId: nil,
            title: request.title ?? "今天的对话",
            status: "transcribed",
            startedAt: "2026-06-24T10:00:00Z",
            createdAt: "2026-06-24T10:00:00Z",
            transcript: TranscriptMetadata(
                title: request.title ?? "今天的对话",
                createdAtText: request.createdAtText,
                durationText: request.durationText,
                segmentCount: 1,
                segments: [
                    TranscriptSegmentRequest(speaker: "我", timestamp: "00:01", text: "今天测试真实录音识别。")
                ]
            ),
            summaryArtifact: nil,
            audioObject: AudioObject(objectKey: "preview/source.caf", mimeType: request.mimeType, byteSize: nil, checksumSha256: nil),
            expertAdviceJobIds: []
        )
    }

    public func submitTranscript(recordingId: String, request: TranscriptSubmitRequest) async throws -> RecordingResponse {
        RecordingResponse(
            recordingId: recordingId,
            spaceId: "space_preview",
            clientRecordingId: nil,
            title: request.title ?? "今天的对话",
            status: "transcribed",
            startedAt: "2026-06-24T10:00:00Z",
            createdAt: "2026-06-24T10:00:00Z",
            transcript: TranscriptMetadata(
                title: request.title ?? "今天的对话",
                createdAtText: request.createdAtText,
                durationText: request.durationText,
                segmentCount: request.segments.count,
                segments: request.segments
            ),
            summaryArtifact: nil,
            audioObject: nil,
            expertAdviceJobIds: []
        )
    }

    public func createSummaryJob(recordingId: String) async throws -> SummaryArtifact {
        SummaryArtifact(
            summaryJobId: "summary_preview",
            recordingId: recordingId,
            status: "completed",
            title: "今天的对话",
            overview: "这次对话围绕职业转型中的安全感、时间安排和长期方向展开。当前更适合先保留现实主线，再给理想方向留出低成本验证空间。",
            keyPoints: [
                "七月的主要精力放在语言恢复和身体节奏稳定上。",
                "外贸方向可以作为短期收入验证，不要把它等同于最终人生选择。",
                "普拉提方向需要先量化时间、费用和回本路径。"
            ],
            chapters: [
                SummaryChapter(title: "职业方向", startTimestamp: "00:00", summary: "讨论外贸和普拉提之间的优先级。"),
                SummaryChapter(title: "现实约束", startTimestamp: "08:30", summary: "整理课程、家庭、收入和体力限制。")
            ]
        )
    }

    public func createExpertAdviceJob(recordingId: String, request: ExpertAdviceJobRequest) async throws -> ExpertAdviceJobResponse {
        ExpertAdviceJobResponse(
            jobId: "job_preview",
            sourceType: "recording",
            sourceId: recordingId,
            template: "emotion_talk_expert_team_v1",
            status: "completed",
            events: Self.previewEvents,
            artifact: Self.previewArtifact,
            contextUsage: ContextUsage(
                scope: request.contextScope,
                primary: "current_recording",
                historyCount: request.contextScope == .currentWithHistory ? 1 : 0,
                historySources: request.contextScope == .currentWithHistory
                    ? [HistorySource(sourceType: "recording", sourceId: "rec_history", title: "上一次职业焦虑复盘", relevance: "same_space_recent")]
                    : [],
                profileIncluded: request.includeProfile
            )
        )
    }

    public func fetchExpertAdviceEvents(jobId: String) async throws -> [DeliberationEvent] {
        Self.previewEvents
    }

    public func fetchExpertAdviceJob(jobId: String) async throws -> ExpertAdviceJobResponse {
        ExpertAdviceJobResponse(
            jobId: jobId,
            sourceType: "recording",
            sourceId: "rec_preview",
            template: "emotion_talk_expert_team_v1",
            status: "completed",
            events: Self.previewEvents,
            artifact: Self.previewArtifact,
            contextUsage: ContextUsage(
                scope: .currentOnly,
                primary: "current_recording",
                historyCount: 0,
                historySources: [],
                profileIncluded: false
            )
        )
    }

    public func fetchExpertAdviceArtifact(jobId: String) async throws -> DeliberationArtifact {
        Self.previewArtifact
    }

    public static let previewArtifact = DeliberationArtifact(
        overview: "裁判认为当前不需要逼出唯一答案，而是把职业恢复拆成一个月内可执行、可观察、可撤回的实验。",
        processSummary: [
            ProcessSummary(round: 1, title: "初判", summary: "三位专家分别识别目标、情绪和现实约束。"),
            ProcessSummary(round: 2, title: "互评", summary: "主要挑战是避免只学习不验证，也避免把备选路径变成失败标签。"),
            ProcessSummary(round: 3, title: "修正", summary: "收敛为主线学习、轻量验证、保留恢复窗口。")
        ],
        suggestions: [
            Suggestion(title: "七月只设一个主目标", body: "把语言恢复作为主线，其他任务只保留低消耗验证。", confidence: "high", evidence: ["对话中多次提到课程和作业压力。"]),
            Suggestion(title: "每周做一个职业验证", body: "看岗位、问从业者、改一条简历 bullet，控制在一小时内。", confidence: "medium", evidence: ["外贸岗位仍是现实收入路径。"])
        ],
        keyUncertainties: ["课程真实强度未知。", "家庭节奏和收入压力仍需持续观察。"],
        safetyBoundary: "这不是心理治疗或职业承诺，只是基于对话记录的反思建议。"
    )

    public static let previewEvents: [DeliberationEvent] = [
        .preview(seq: 1, type: "expert_message_added", participant: "life_coach", round: 1, content: "先把七月定义成恢复主动权的窗口，不要一边学习一边再加高消耗赚钱任务。"),
        .preview(seq: 2, type: "expert_message_added", participant: "counselor", round: 1, content: "迷茫本身不是失败信号，它更像长期压力后的停顿。计划需要降低自责感。"),
        .preview(seq: 3, type: "expert_message_added", participant: "reality_strategist", round: 1, content: "外贸、课程、家庭和普拉提要拆成不同约束，不能都按满分方案安排。"),
        .preview(seq: 4, type: "expert_challenge_added", participant: "life_coach", round: 2, content: "挑战点：如果只说先学语言，职业验证会被推迟到看不见。需要一个轻量动作。"),
        .preview(seq: 5, type: "expert_challenge_added", participant: "counselor", round: 2, content: "挑战点：不要把普拉提放在失败后才启动，否则它会变成压力源。"),
        .preview(seq: 6, type: "expert_challenge_added", participant: "reality_strategist", round: 2, content: "挑战点：普拉提路径要量化费用、时间和回本周期。"),
        .preview(seq: 7, type: "expert_revision_added", participant: "life_coach", round: 3, content: "修正为七月主线学习，每周一个职业验证，不用马上决定最终身份。"),
        .preview(seq: 8, type: "expert_revision_added", participant: "counselor", round: 3, content: "修正为用小胜任感恢复自我评价，不用把每一步都当成人生考试。"),
        .preview(seq: 9, type: "expert_revision_added", participant: "reality_strategist", round: 3, content: "修正为外贸做收入验证，普拉提做并行信息收集，八月再判断资源投入。")
    ]
}

private extension DeliberationEvent {
    static func preview(seq: Int, type: String, participant: String, round: Int, content: String) -> DeliberationEvent {
        DeliberationEvent(
            eventId: "evt_preview_\(seq)",
            jobId: "job_preview",
            seq: seq,
            type: type,
            visibility: "user_visible",
            payload: DeliberationEventPayload(title: nil, content: content, status: nil),
            participant: participant,
            round: round
        )
    }
}
