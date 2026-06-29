import type {
  ContextScope,
  ExpertAdviceJobResponse,
  RecordingResponse,
  SpaceResponse,
  SummaryArtifact,
  TranscriptSegment,
} from "./types";

const configuredBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
const API_BASE = configuredBase?.replace(/\/$/, "") ?? "/api";

export function makeClientId(prefix: string) {
  return globalThis.crypto?.randomUUID?.() ?? `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail || response.statusText}`);
  }

  return (await response.json()) as T;
}

export const emotionTalkApi = {
  health() {
    return request<{ status: string }>("/health");
  },

  createSpace(name: string) {
    return request<SpaceResponse>("/spaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  createRecording(spaceId: string, title: string) {
    return request<RecordingResponse>("/recordings", {
      method: "POST",
      body: JSON.stringify({
        spaceId,
        title,
        startedAt: new Date().toISOString(),
        clientRecordingId: makeClientId("client_recording"),
      }),
    });
  },

  createAsrSession(spaceId: string, recordingId: string) {
    return request("/asr-sessions", {
      method: "POST",
      body: JSON.stringify({
        spaceId,
        recordingId,
        provider: "paraformer",
        model: "paraformer-realtime-8k-v2",
      }),
    });
  },

  createAudioUploadAuthorization(recordingId: string, mimeType: string, byteSize?: number) {
    return request(`/recordings/${recordingId}/audio-upload-authorizations`, {
      method: "POST",
      body: JSON.stringify({
        mimeType,
        byteSize,
      }),
    });
  },

  submitTranscript(recordingId: string, title: string, durationText: string, segments: TranscriptSegment[]) {
    return request<RecordingResponse>(`/recordings/${recordingId}/transcript`, {
      method: "POST",
      body: JSON.stringify({
        title,
        createdAtText: new Date().toLocaleString("zh-CN", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }),
        durationText,
        segments,
      }),
    });
  },

  createSummaryJob(recordingId: string) {
    return request<SummaryArtifact>(`/recordings/${recordingId}/summary-jobs`, {
      method: "POST",
      body: JSON.stringify({ force: true }),
    });
  },

  createExpertAdviceJob(recordingId: string, contextScope: ContextScope) {
    return request<ExpertAdviceJobResponse>(`/recordings/${recordingId}/expert-advice-jobs`, {
      method: "POST",
      body: JSON.stringify({
        contextScope,
        historyLimit: contextScope === "current_with_history" ? 5 : 0,
        includeProfile: contextScope === "current_with_history",
      }),
    });
  },
};
