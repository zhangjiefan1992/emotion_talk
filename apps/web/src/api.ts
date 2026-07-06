import type {
  ContextScope,
  ExpertAdviceJobResponse,
  RecordingResponse,
  SpaceResponse,
  SpacesResponse,
  SummaryArtifact,
  TranscriptSegment,
} from "./types";

const configuredBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
const API_BASE = configuredBase?.replace(/\/$/, "") ?? "/api";

export function makeClientId(prefix: string) {
  return globalThis.crypto?.randomUUID?.() ?? `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

type ApiRequestOptions = {
  method?: UniApp.RequestOptions["method"];
  body?: Record<string, unknown>;
};

function request<T>(path: string, init: ApiRequestOptions = {}): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method: init.method ?? "GET",
      data: init.body,
      header: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
      },
      success: (response) => {
        const status = response.statusCode;
        if (status < 200 || status >= 300) {
          reject(new Error(`API ${status}: ${typeof response.data === "string" ? response.data : JSON.stringify(response.data)}`));
          return;
        }
        resolve(response.data as T);
      },
      fail: reject,
    });
  });
}

export const emotionTalkApi = {
  health() {
    return request<{ status: string }>("/health");
  },

  listSpaces(ownerId: string) {
    return request<SpacesResponse>(`/users/${encodeURIComponent(ownerId)}/spaces`);
  },

  createSpace(name: string, ownerId: string) {
    return request<SpaceResponse>("/spaces", {
      method: "POST",
      body: { name, ownerId },
    });
  },

  setCurrentSpace(ownerId: string, spaceId: string) {
    return request<SpacesResponse>(`/users/${encodeURIComponent(ownerId)}/current-space`, {
      method: "POST",
      body: { spaceId },
    });
  },

  listRecordings(spaceId: string) {
    return request<RecordingResponse[]>(`/spaces/${spaceId}/recordings`);
  },

  createRecording(spaceId: string, title: string) {
    return request<RecordingResponse>("/recordings", {
      method: "POST",
      body: {
        spaceId,
        title,
        startedAt: new Date().toISOString(),
        clientRecordingId: makeClientId("client_recording"),
      },
    });
  },

  createAsrSession(spaceId: string, recordingId: string) {
    return request("/asr-sessions", {
      method: "POST",
      body: {
        spaceId,
        recordingId,
        provider: "paraformer",
        model: "paraformer-realtime-8k-v2",
      },
    });
  },

  createAudioUploadAuthorization(recordingId: string, mimeType: string, byteSize?: number) {
    return request(`/recordings/${recordingId}/audio-upload-authorizations`, {
      method: "POST",
      body: {
        mimeType,
        byteSize,
      },
    });
  },

  async transcribeAudio(recordingId: string, audio: Blob, title: string, durationText: string) {
    return request<RecordingResponse>(`/recordings/${recordingId}/audio-transcriptions`, {
      method: "POST",
      body: {
        audioBase64: await blobToBase64(audio),
        mimeType: audio.type || "audio/webm",
        title,
        createdAtText: new Date().toLocaleString("zh-CN", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }),
        durationText,
      },
    });
  },

  submitTranscript(recordingId: string, title: string, durationText: string, segments: TranscriptSegment[]) {
    return request<RecordingResponse>(`/recordings/${recordingId}/transcript`, {
      method: "POST",
      body: {
        title,
        createdAtText: new Date().toLocaleString("zh-CN", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }),
        durationText,
        segments,
      },
    });
  },

  createSummaryJob(recordingId: string) {
    return request<SummaryArtifact>(`/recordings/${recordingId}/summary-jobs`, {
      method: "POST",
      body: { force: true },
    });
  },

  createExpertAdviceJob(recordingId: string, contextScope: ContextScope) {
    return request<ExpertAdviceJobResponse>(`/recordings/${recordingId}/expert-advice-jobs`, {
      method: "POST",
      body: {
        contextScope,
        historyLimit: contextScope === "current_with_history" ? 5 : 0,
        includeProfile: contextScope === "current_with_history",
      },
    });
  },

  fetchExpertAdviceJob(jobId: string) {
    return request<ExpertAdviceJobResponse>(`/expert-advice-jobs/${jobId}`);
  },
};

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
