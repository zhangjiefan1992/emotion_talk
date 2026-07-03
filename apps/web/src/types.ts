export type RecordingStatus =
  | "idle"
  | "starting"
  | "recording"
  | "processing"
  | "completed"
  | "failed";

export type ContextScope = "current_only" | "current_with_history";

export interface SpaceResponse {
  spaceId: string;
  name: string;
  createdAt: string;
}

export interface RecordingResponse {
  recordingId: string;
  spaceId: string;
  clientRecordingId?: string | null;
  title: string;
  status: string;
  startedAt: string;
  createdAt: string;
  transcript?: TranscriptMetadata | null;
  summaryArtifact?: SummaryArtifact | null;
  audioObject?: AudioObject | null;
  expertAdviceJobIds: string[];
}

export interface TranscriptMetadata {
  title: string;
  createdAtText: string;
  durationText: string;
  segmentCount: number;
  segments?: TranscriptSegment[];
}

export interface AudioObject {
  objectKey: string;
  mimeType: string;
  byteSize?: number | null;
  checksumSha256?: string | null;
}

export interface TranscriptSegment {
  speaker: string;
  timestamp: string;
  text: string;
  startMs?: number;
  endMs?: number;
}

export interface SummaryArtifact {
  summaryJobId?: string | null;
  recordingId?: string | null;
  status: string;
  title: string;
  overview: string;
  keyPoints: string[];
  chapters: SummaryChapter[];
  modelTrace?: Record<string, unknown>;
}

export interface SummaryChapter {
  title: string;
  startTimestamp: string;
  summary: string;
}

export interface ExpertAdviceJobResponse {
  jobId: string;
  sourceType: string;
  sourceId: string;
  template: string;
  status: string;
  events: DeliberationEvent[];
  artifact: DeliberationArtifact;
  contextUsage: ContextUsage;
}

export interface ContextUsage {
  scope?: ContextScope | null;
  primary?: string | null;
  historyCount: number;
  historySources: HistorySource[];
  profileIncluded: boolean;
}

export interface HistorySource {
  sourceType: string;
  sourceId: string;
  title: string;
  relevance: string;
}

export interface DeliberationEvent {
  eventId: string;
  jobId: string;
  seq: number;
  type: string;
  visibility: string;
  payload: {
    title?: string | null;
    content?: string | null;
    status?: string | null;
  };
  participant?: string | null;
  round?: number | null;
}

export interface DeliberationArtifact {
  overview: string;
  processSummary: ProcessSummary[];
  suggestions: Suggestion[];
  keyUncertainties: string[];
  safetyBoundary: string;
}

export interface ProcessSummary {
  round: number;
  title: string;
  summary: string;
}

export interface Suggestion {
  title: string;
  body: string;
  confidence: string;
  evidence: string[];
}

export interface ConversationRecord {
  localId: string;
  recordingId?: string;
  title: string;
  createdAt: string;
  durationText: string;
  status: RecordingStatus;
  segments: TranscriptSegment[];
  summary?: SummaryArtifact;
  expertAdvice?: ExpertAdviceJobResponse;
}
