import EmotionTalkCore
import AVFoundation
import Foundation

struct ConversationStartOptions: Equatable {
    var testAudioURL: URL?
    var testTranscriptURL: URL?
    var autoFinish: Bool
    var autoRequestAdvice: Bool

    static let liveMicrophone = ConversationStartOptions(
        testAudioURL: nil,
        testTranscriptURL: nil,
        autoFinish: false,
        autoRequestAdvice: false
    )
}

@MainActor
@Observable
final class ConversationSession {
    var phase: ConversationPhase = .idle
    var space: SpaceResponse?
    var recording: RecordingResponse?
    var asrSession: ASRSessionResponse?
    var liveSegments: [TranscriptSegmentRequest] = []
    var summary: SummaryArtifact?
    var expertAdvice: ExpertAdviceJobResponse?
    var advicePhase: AdvicePhase = .idle
    var startedAt: Date?
    var clockNow: Date = .now
    var errorMessage: String?
    var recorderStatus: String = "等待开始"
    var audioFileURL: URL?
    private let recorder = LiveSpeechRecorder()
    private var clockTask: Task<Void, Never>?

    func start(api: any EmotionTalkAPI, options: ConversationStartOptions = .liveMicrophone) async {
        phase = .starting
        errorMessage = nil
        do {
            let space = try await api.createSpace(name: "默认倾诉空间")
            let recording = try await api.createRecording(
                RecordingCreateRequest(
                    spaceId: space.spaceId,
                    title: Date.now.formatted(date: .numeric, time: .shortened)
                )
            )
            let asrSession = try await api.createASRSession(
                ASRSessionRequest(spaceId: space.spaceId, recordingId: recording.recordingId)
            )
            self.space = space
            self.recording = recording
            self.asrSession = asrSession
            self.startedAt = .now
            self.clockNow = .now
            self.liveSegments = []
            self.summary = nil
            self.expertAdvice = nil
            self.advicePhase = .idle
            self.audioFileURL = nil
            self.recorderStatus = options.testTranscriptURL == nil ? "正在请求麦克风权限" : "正在读取真实转写材料"

            try await recorder.start(
                realtimeASRURL: options.testTranscriptURL == nil ? AppConfiguration.realtimeASRURL : nil,
                testAudioURL: options.testAudioURL,
                testTranscriptURL: options.testTranscriptURL,
                onSegment: { [weak self] segment in
                    Task { @MainActor in
                        self?.appendLiveSegment(segment)
                    }
                },
                onTranscript: { [weak self] text in
                    Task { @MainActor in
                        self?.replaceLiveTranscript(with: text)
                    }
                },
                onFinished: { [weak self] result in
                    Task { @MainActor in
                        await self?.handleRecorderFinished(result, api: api, options: options)
                    }
                }
            )

            self.audioFileURL = recorder.audioFileURL
            self.recorderStatus = options.testTranscriptURL == nil ? "麦克风录音中，正在实时转写" : "真实音频转写回放中"
            startClock()
            phase = .recording
        } catch {
            recorder.stop()
            fail(error)
        }
    }

    func finish(api: any EmotionTalkAPI, autoRequestAdvice: Bool = false) async {
        guard let recording else { return }
        let recoveredText = await recorder.stopAndFinalizeTranscript()
        clockTask?.cancel()
        phase = .processing
        errorMessage = nil
        do {
            let createdAtText = Date.now.formatted(date: .numeric, time: .shortened)
            let durationText = elapsedText
            var finalSegments = liveSegments.filter { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            if finalSegments.isEmpty, let recoveredText, !recoveredText.isEmpty {
                finalSegments.append(
                    TranscriptSegmentRequest(
                        speaker: "我",
                        timestamp: elapsedText,
                        text: recoveredText,
                        startMs: nil
                    )
                )
            }
            if finalSegments.isEmpty {
                guard let audioFileURL else {
                    throw LiveSpeechRecorderError.emptyTranscript
                }
                recorderStatus = "正在用百炼识别录音"
                let updatedRecording = try await api.transcribeAudio(
                    recordingId: recording.recordingId,
                    request: AudioTranscriptionRequest(
                        audioBase64: try Data(contentsOf: audioFileURL).base64EncodedString(),
                        mimeType: audioMimeType(for: audioFileURL),
                        title: recording.title,
                        createdAtText: createdAtText,
                        durationText: durationText
                    )
                )
                let summary = try await api.createSummaryJob(recordingId: recording.recordingId)
                self.recording = updatedRecording
                self.summary = summary
                phase = .completed
                if autoRequestAdvice {
                    await requestAdvice(api: api, scope: .currentOnly)
                }
                return
            }
            try await authorizeAudioIfNeeded(recordingId: recording.recordingId, api: api)
            let updatedRecording = try await api.submitTranscript(
                recordingId: recording.recordingId,
                request: TranscriptSubmitRequest(
                    title: recording.title,
                    createdAtText: createdAtText,
                    durationText: durationText,
                    segments: finalSegments
                )
            )
            let summary = try await api.createSummaryJob(recordingId: recording.recordingId)
            self.recording = updatedRecording
            self.summary = summary
            phase = .completed
            if autoRequestAdvice {
                await requestAdvice(api: api, scope: .currentOnly)
            }
        } catch {
            fail(error)
        }
    }

    func requestAdvice(api: any EmotionTalkAPI, scope: ContextScope) async {
        guard let recording else { return }
        advicePhase = .loading
        do {
            expertAdvice = try await api.createExpertAdviceJob(
                recordingId: recording.recordingId,
                request: ExpertAdviceJobRequest(
                    contextScope: scope,
                    historyLimit: scope == .currentWithHistory ? 5 : 0,
                    includeProfile: scope == .currentWithHistory
                )
            )
            advicePhase = .loaded
        } catch {
            advicePhase = .failed(error.localizedDescription)
        }
    }

    func reset() {
        recorder.stop()
        clockTask?.cancel()
        phase = .idle
        recording = nil
        asrSession = nil
        liveSegments = []
        summary = nil
        expertAdvice = nil
        advicePhase = .idle
        startedAt = nil
        clockNow = .now
        errorMessage = nil
        recorderStatus = "等待开始"
        audioFileURL = nil
    }

    var elapsedText: String {
        guard let startedAt else { return "00:00" }
        let seconds = max(0, Int(clockNow.timeIntervalSince(startedAt)))
        return String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }

    private func handleRecorderFinished(
        _ result: Result<Void, Error>,
        api: any EmotionTalkAPI,
        options: ConversationStartOptions
    ) async {
        guard phase == .recording else { return }
        switch result {
        case .success:
            guard options.autoFinish else { return }
            await finish(api: api, autoRequestAdvice: options.autoRequestAdvice)
        case .failure(let error):
            fail(error)
        }
    }

    private func fail(_ error: Error) {
        errorMessage = error.localizedDescription
        phase = .failed
    }

    private func appendLiveSegment(_ segment: TranscriptSegmentRequest) {
        guard !segment.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        liveSegments.append(segment)
    }

    private func replaceLiveTranscript(with text: String) {
        let cleanText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanText.isEmpty else { return }
        let segment = TranscriptSegmentRequest(
            speaker: "我",
            timestamp: elapsedText,
            text: cleanText,
            startMs: nil
        )
        if liveSegments.isEmpty {
            liveSegments.append(segment)
        } else {
            liveSegments[liveSegments.count - 1] = segment
        }
    }

    private func authorizeAudioIfNeeded(recordingId: String, api: any EmotionTalkAPI) async throws {
        guard let audioFileURL else { return }
        let byteSize = try? audioFileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize
        _ = try await api.createAudioUploadAuthorization(
            recordingId: recordingId,
            request: AudioUploadAuthorizationRequest(
                mimeType: audioMimeType(for: audioFileURL),
                byteSize: byteSize,
                checksumSha256: nil
            )
        )
    }

    private func audioMimeType(for url: URL) -> String {
        switch url.pathExtension.lowercased() {
        case "mp3":
            "audio/mpeg"
        case "m4a":
            "audio/mp4"
        case "wav":
            "audio/wav"
        default:
            "audio/x-caf"
        }
    }

    private func startClock() {
        clockTask?.cancel()
        clockTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1))
                self?.clockNow = .now
            }
        }
    }
}

private final class LiveSpeechRecorder {
    private let audioEngine = AVAudioEngine()
    private let realtimeASR = RealtimeASRClient()
    private let targetPCMFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true)!
    private var pcmConverter: AVAudioConverter?
    private var audioFile: AVAudioFile?
    private var fixtureTask: Task<Void, Never>?
    private var lastTranscript: String?
    private(set) var audioFileURL: URL?

    func start(
        realtimeASRURL: URL?,
        testAudioURL: URL?,
        testTranscriptURL: URL?,
        onSegment: @escaping (TranscriptSegmentRequest) -> Void,
        onTranscript: @escaping (String) -> Void,
        onFinished: @escaping (Result<Void, Error>) -> Void
    ) async throws {
        stop()
        audioFileURL = nil
        lastTranscript = nil
        if let testTranscriptURL {
            try await startTranscriptFixture(
                audioURL: testAudioURL,
                transcriptURL: testTranscriptURL,
                onSegment: onSegment,
                onFinished: onFinished
            )
            return
        }

        try await requestPermissions()
        try configureAudioSession()

        let inputNode = audioEngine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)
        guard inputFormat.sampleRate > 0, inputFormat.channelCount > 0 else {
            throw LiveSpeechRecorderError.microphoneUnavailable
        }

        if let realtimeASRURL {
            realtimeASR.start(url: realtimeASRURL) { [weak self] text in
                self?.lastTranscript = text
                onTranscript(text)
            }
        }

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("emotion-talk-\(UUID().uuidString)")
            .appendingPathExtension("caf")
        audioFile = try AVAudioFile(forWriting: url, settings: inputFormat.settings)
        audioFileURL = url

        inputNode.removeTap(onBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, _ in
            guard let self else { return }
            try? self.audioFile?.write(from: buffer)
            if let data = self.pcm16Data(from: buffer, inputFormat: inputFormat) {
                self.realtimeASR.send(data)
            }
        }

        audioEngine.prepare()
        try audioEngine.start()
    }

    func stop() {
        fixtureTask?.cancel()
        fixtureTask = nil
        stopLiveAudio()
        realtimeASR.stop()
        audioFile = nil
        deactivateAudioSession()
    }

    func stopAndFinalizeTranscript() async -> String? {
        fixtureTask?.cancel()
        fixtureTask = nil
        stopLiveAudio()
        realtimeASR.stop()
        audioFile = nil
        try? await Task.sleep(for: .milliseconds(1200))

        let liveText = lastTranscript?.trimmingCharacters(in: .whitespacesAndNewlines)
        deactivateAudioSession()

        if let liveText, !liveText.isEmpty {
            return liveText
        }
        return nil
    }

    private func stopLiveAudio() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
    }

    private func startTranscriptFixture(
        audioURL: URL?,
        transcriptURL: URL,
        onSegment: @escaping (TranscriptSegmentRequest) -> Void,
        onFinished: @escaping (Result<Void, Error>) -> Void
    ) async throws {
        let markdown = try await TranscriptFixtureLoader.load(from: transcriptURL)
        let segments = DingTalkTranscriptParser.parse(markdown: markdown)
        guard !segments.isEmpty else {
            throw LiveSpeechRecorderError.emptyTranscript
        }
        audioFileURL = audioURL
        fixtureTask = Task {
            for segment in segments {
                guard !Task.isCancelled else { return }
                onSegment(segment)
                try? await Task.sleep(for: .milliseconds(8))
            }
            guard !Task.isCancelled else { return }
            onFinished(.success(()))
        }
    }

    private func requestPermissions() async throws {
        let microphoneGranted = await requestMicrophonePermission()
        guard microphoneGranted else {
            throw LiveSpeechRecorderError.microphonePermissionDenied
        }
    }

    private func configureAudioSession() throws {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: [.allowBluetoothHFP])
        try session.setActive(true, options: .notifyOthersOnDeactivation)
        #endif
    }

    private func deactivateAudioSession() {
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        #endif
    }

    private func requestMicrophonePermission() async -> Bool {
        #if os(iOS)
        if #available(iOS 17.0, *) {
            await withCheckedContinuation { continuation in
                AVAudioApplication.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        } else {
            await withCheckedContinuation { continuation in
                AVAudioSession.sharedInstance().requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        }
        #else
            true
        #endif
    }

    private func pcm16Data(from buffer: AVAudioPCMBuffer, inputFormat: AVAudioFormat) -> Data? {
        if pcmConverter == nil {
            pcmConverter = AVAudioConverter(from: inputFormat, to: targetPCMFormat)
        }
        guard let converter = pcmConverter else { return nil }
        let ratio = targetPCMFormat.sampleRate / inputFormat.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 1
        guard let output = AVAudioPCMBuffer(pcmFormat: targetPCMFormat, frameCapacity: capacity) else { return nil }
        var didProvideInput = false
        var error: NSError?
        let status = converter.convert(to: output, error: &error) { _, outStatus in
            if didProvideInput {
                outStatus.pointee = .noDataNow
                return nil
            }
            didProvideInput = true
            outStatus.pointee = .haveData
            return buffer
        }
        guard status != .error, let channel = output.int16ChannelData else { return nil }
        return Data(bytes: channel[0], count: Int(output.frameLength) * MemoryLayout<Int16>.size)
    }
}

private final class RealtimeASRClient {
    private var task: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?

    func start(url: URL, onTranscript: @escaping (String) -> Void) {
        stop()
        let task = URLSession.shared.webSocketTask(with: url)
        self.task = task
        task.resume()
        receiveTask = Task {
            while !Task.isCancelled {
                do {
                    let message = try await task.receive()
                    guard case .string(let text) = message,
                          let data = text.data(using: .utf8),
                          let event = try? JSONDecoder().decode(RealtimeASREvent.self, from: data),
                          event.type == "transcript",
                          !event.text.isEmpty else {
                        continue
                    }
                    onTranscript(event.text)
                } catch {
                    return
                }
            }
        }
    }

    func send(_ data: Data) {
        guard let task else { return }
        Task { try? await task.send(.data(data)) }
    }

    func stop() {
        receiveTask?.cancel()
        receiveTask = nil
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
    }
}

private struct RealtimeASREvent: Decodable {
    let type: String
    let text: String
}

private enum TranscriptFixtureLoader {
    static func load(from url: URL) async throws -> String {
        if url.isFileURL {
            return try String(contentsOf: url, encoding: .utf8)
        }
        let (data, response) = try await URLSession.shared.data(from: url)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw LiveSpeechRecorderError.fixtureUnavailable(http.statusCode)
        }
        guard let text = String(data: data, encoding: .utf8) else {
            throw LiveSpeechRecorderError.fixtureDecodingFailed
        }
        return text
    }
}

private enum DingTalkTranscriptParser {
    private static let speakerLinePattern = try! NSRegularExpression(
        pattern: #"^(.+)\s+(\d{2}:\d{2}(?::\d{2})?)$"#
    )

    static func parse(markdown: String) -> [TranscriptSegmentRequest] {
        var segments: [TranscriptSegmentRequest] = []
        var currentSpeaker: String?
        var currentTimestamp: String?
        var currentLines: [String] = []

        func flush() {
            guard let currentSpeaker, let currentTimestamp else { return }
            let text = currentLines
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
                .joined(separator: "\n")
            guard !text.isEmpty else { return }
            segments.append(
                TranscriptSegmentRequest(
                    speaker: currentSpeaker,
                    timestamp: normalizeTimestamp(currentTimestamp),
                    text: text,
                    startMs: nil
                )
            )
        }

        for rawLine in markdown.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            if line.isEmpty || line.hasPrefix("#") || line.hasPrefix(">") {
                continue
            }
            if let (speaker, timestamp) = matchSpeakerLine(line) {
                flush()
                currentSpeaker = speaker
                currentTimestamp = timestamp
                currentLines = []
            } else if currentSpeaker != nil {
                currentLines.append(line)
            }
        }
        flush()
        return segments
    }

    private static func matchSpeakerLine(_ line: String) -> (String, String)? {
        let range = NSRange(line.startIndex..<line.endIndex, in: line)
        guard let match = speakerLinePattern.firstMatch(in: line, range: range),
              match.numberOfRanges == 3,
              let speakerRange = Range(match.range(at: 1), in: line),
              let timestampRange = Range(match.range(at: 2), in: line) else {
            return nil
        }
        let speaker = String(line[speakerRange]).trimmingCharacters(in: .whitespacesAndNewlines)
        let timestamp = String(line[timestampRange]).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !speaker.isEmpty else { return nil }
        return (speaker, timestamp)
    }

    private static func normalizeTimestamp(_ timestamp: String) -> String {
        let parts = timestamp.split(separator: ":").map(String.init)
        if parts.count == 3 {
            return "\(parts[1]):\(parts[2])"
        }
        return timestamp
    }
}

enum LiveSpeechRecorderError: LocalizedError {
    case speechPermissionDenied
    case microphonePermissionDenied
    case speechUnavailable
    case microphoneUnavailable
    case emptyTranscript
    case fixtureUnavailable(Int)
    case fixtureDecodingFailed

    var errorDescription: String? {
        switch self {
        case .speechPermissionDenied:
            "需要允许语音识别权限，才能实时转写。"
        case .microphonePermissionDenied:
            "需要允许麦克风权限，才能开始录音。"
        case .speechUnavailable:
            "当前设备暂时无法使用系统语音识别。"
        case .microphoneUnavailable:
            "没有检测到可用麦克风。"
        case .emptyTranscript:
            "云端语音识别没有返回文字。请确认麦克风输入，录音 5 秒以上后再结束。"
        case .fixtureUnavailable(let statusCode):
            "测试转写材料读取失败，HTTP 状态码 \(statusCode)。"
        case .fixtureDecodingFailed:
            "测试转写材料不是有效的 UTF-8 文本。"
        }
    }
}

enum ConversationPhase: Equatable {
    case idle
    case starting
    case recording
    case processing
    case completed
    case failed
}

enum AdvicePhase: Equatable {
    case idle
    case loading
    case loaded
    case failed(String)
}
