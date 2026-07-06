<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { emotionTalkApi, makeClientId } from "../../api";
import { formatDuration } from "../../sampleData";
import type {
  ContextScope,
  ConversationRecord,
  ExpertAdviceJobResponse,
  RecordingStatus,
  SummaryArtifact,
  TranscriptSegment,
} from "../../types";

type ScreenName = "home" | "detail" | "advice";
type DetailTab = "summary" | "transcript";
type BackendMode = "checking" | "connected" | "offline";
type CaptureMode = "none" | "microphone";
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<{
    0?: { transcript?: string };
    isFinal: boolean;
  }>;
};

const participantNames: Record<string, string> = {
  life_coach: "人生教练",
  counselor: "心理咨询",
  reality_strategist: "现实行动",
  judge: "裁判",
};

const backendMode = ref<BackendMode>("checking");
const screen = ref<ScreenName>("home");
const detailTab = ref<DetailTab>("summary");
const status = ref<RecordingStatus>("idle");
const elapsed = ref(0);
const spaceId = ref("");
const recordingId = ref("");
const segments = ref<TranscriptSegment[]>([]);
const records = ref<ConversationRecord[]>([]);
const selectedRecordId = ref("");
const summary = ref<SummaryArtifact>();
const advice = ref<ExpertAdviceJobResponse>();
const captureMode = ref<CaptureMode>("none");
const errorText = ref("");
const contextScope: ContextScope = "current_with_history";

let clockTimer: ReturnType<typeof setInterval> | undefined;
let transcriptTimer: ReturnType<typeof setInterval> | undefined;
let mediaRecorder: MediaRecorder | undefined;
let mediaStream: MediaStream | undefined;
let recordedChunks: Blob[] = [];
let speechRecognition: SpeechRecognitionLike | undefined;

const activeRecord = computed(() => records.value.find((record) => record.localId === selectedRecordId.value) ?? records.value[0]);
const isLive = computed(() => status.value === "recording" || status.value === "processing");
const detailSegments = computed(() => (isLive.value ? segments.value : activeRecord.value?.segments ?? []));
const detailRecord = computed<ConversationRecord>(() => {
  if (!isLive.value && activeRecord.value) return activeRecord.value;
  return {
    localId: "live-recording",
    recordingId: recordingId.value || undefined,
    title: status.value === "processing" ? "正在生成纪要" : "正在录音",
    createdAt: "刚刚",
    durationText: formatDuration(elapsed.value),
    status: status.value,
    segments: segments.value,
  };
});
const visibleSummary = computed(() => summary.value ?? activeRecord.value?.summary ?? emptySummary(detailRecord.value.title));
const visibleAdvice = computed(() => advice.value ?? emptyAdvice(contextScope));
const visibleAdviceEvents = computed(() =>
  visibleAdvice.value.events.filter((event) => event.payload.content && event.round && event.participant),
);
const backendText = computed(() => (backendMode.value === "connected" ? "服务端已连接" : backendMode.value === "offline" ? "服务端未连接" : "连接中"));
const spaceSubtitle = computed(() => `${records.value.length} 条真实记录`);
const portraitStatusText = computed(() => (records.value.length ? "基于真实记录" : "等待录音"));
const captureText = computed(() => {
  if (captureMode.value === "microphone") return "麦克风录音中";
  return backendText.value;
});

onMounted(async () => {
  try {
    await emotionTalkApi.health();
    backendMode.value = "connected";
  } catch {
    backendMode.value = "offline";
  }
});

onBeforeUnmount(() => {
  stopTimers();
  stopSpeechRecognition();
  stopMediaTracks();
});

function nowTitle() {
  return `${new Date().toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })} 晚间倾诉`;
}

function stopTimers() {
  if (clockTimer) clearInterval(clockTimer);
  if (transcriptTimer) clearInterval(transcriptTimer);
  clockTimer = undefined;
  transcriptTimer = undefined;
}

function addSegment(text: string) {
  const clean = text.trim();
  if (!clean) return;
  const last = segments.value[segments.value.length - 1];
  if (last?.text === clean) return;
  segments.value = [
    ...segments.value,
    {
      speaker: "我",
      timestamp: formatDuration(elapsed.value),
      text: clean,
      startMs: elapsed.value * 1000,
    },
  ];
}

async function startBrowserCapture() {
  if (typeof window === "undefined" || typeof navigator === "undefined") throw new Error("当前环境不支持浏览器录音。");
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("当前浏览器没有开放麦克风录音能力。通常需要 HTTPS、localhost/127.0.0.1，或浏览器把当前地址视为安全来源。");
  }
  if (typeof MediaRecorder === "undefined") throw new Error("当前浏览器不支持 MediaRecorder 录音。");

  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  recordedChunks = [];
  const mimeType = selectAudioMimeType();
  mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordedChunks.push(event.data);
  };
  mediaRecorder.start(1000);
  captureMode.value = "microphone";
  startSpeechRecognition();
}

function selectAudioMimeType() {
  return ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((item) => MediaRecorder.isTypeSupported(item));
}

function startSpeechRecognition() {
  if (typeof window === "undefined") return false;
  const recognitionCtor = (
    window as typeof window & {
      SpeechRecognition?: SpeechRecognitionCtor;
      webkitSpeechRecognition?: SpeechRecognitionCtor;
    }
  ).SpeechRecognition ?? (
    window as typeof window & {
      webkitSpeechRecognition?: SpeechRecognitionCtor;
    }
  ).webkitSpeechRecognition;
  if (!recognitionCtor) return false;
  speechRecognition = new recognitionCtor();
  speechRecognition.lang = "zh-CN";
  speechRecognition.continuous = true;
  speechRecognition.interimResults = true;
  speechRecognition.onresult = (event) => {
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      const text = result[0]?.transcript ?? "";
      if (result.isFinal) addSegment(text);
    }
  };
  speechRecognition.onerror = () => undefined;
  speechRecognition.onend = () => {
    if (status.value === "recording") {
      try {
        speechRecognition?.start();
      } catch {
        // ponytail: Chrome may auto-end recognition; retry only while recording.
      }
    }
  };
  try {
    speechRecognition.start();
    return true;
  } catch {
    return false;
  }
}

function stopSpeechRecognition() {
  const current = speechRecognition;
  speechRecognition = undefined;
  try {
    current?.stop();
  } catch {
    // ignore browser cleanup races
  }
}

function stopMediaTracks() {
  mediaStream?.getTracks().forEach((track) => track.stop());
  mediaStream = undefined;
}

function stopBrowserCapture(): Promise<Blob | undefined> {
  stopSpeechRecognition();
  const recorder = mediaRecorder;
  if (!recorder) {
    stopMediaTracks();
    return Promise.resolve(undefined);
  }
  mediaRecorder = undefined;
  return new Promise((resolve) => {
    recorder.onstop = () => {
      stopMediaTracks();
      const type = recorder.mimeType || recordedChunks[0]?.type || "audio/webm";
      resolve(recordedChunks.length ? new Blob(recordedChunks, { type }) : undefined);
      recordedChunks = [];
    };
    if (recorder.state === "inactive") {
      recorder.onstop?.(new Event("stop"));
      return;
    }
    recorder.stop();
  });
}

function emptySummary(title: string): SummaryArtifact {
  return {
    status: "idle",
    title,
    overview: "录音完成后会在这里生成 AI 纪要。",
    keyPoints: [],
    chapters: [],
  };
}

function emptyAdvice(scope: ContextScope): ExpertAdviceJobResponse {
  return {
    jobId: "pending-job",
    sourceType: "recording",
    sourceId: "pending-recording",
    template: "expert_team_v1",
    status: "pending",
    contextUsage: {
      scope,
      primary: "current_recording",
      historyCount: 0,
      historySources: [],
      profileIncluded: false,
    },
    events: [],
    artifact: {
      overview: "完成一次真实录音和 AI 纪要后，专家团会在这里生成多轮讨论和裁判结论。",
      processSummary: [],
      suggestions: [],
      keyUncertainties: [],
      safetyBoundary: "建议仅供参考，最终决定权在你手中。",
    },
  };
}

async function ensureSpace() {
  if (spaceId.value) return spaceId.value;
  const space = await emotionTalkApi.createSpace("家的倾诉空间");
  spaceId.value = space.spaceId;
  return space.spaceId;
}

async function startRecording() {
  errorText.value = "";
  status.value = "starting";
  elapsed.value = 0;
  segments.value = [];
  summary.value = undefined;
  advice.value = undefined;
  screen.value = "detail";
  detailTab.value = "transcript";
  captureMode.value = "none";

  try {
    if (backendMode.value !== "connected") throw new Error("服务端未连接，不能开始真实录音。");
    if (backendMode.value === "connected") {
      const currentSpaceId = await ensureSpace();
      const recording = await emotionTalkApi.createRecording(currentSpaceId, nowTitle());
      recordingId.value = recording.recordingId;
      await emotionTalkApi.createAsrSession(currentSpaceId, recording.recordingId);
    }
    await startBrowserCapture();
    status.value = "recording";
    clockTimer = setInterval(() => (elapsed.value += 1), 1000);
  } catch {
    status.value = "failed";
    errorText.value = "真实录音启动失败：当前浏览器没有开放麦克风能力，或用户未授权麦克风。";
    recordingId.value = "";
  }
}

async function finishRecording() {
  if (status.value !== "recording") return;
  status.value = "processing";
  stopTimers();
  const audioBlob = await stopBrowserCapture();
  const title = "刚刚的倾诉记录";
  const durationText = formatDuration(elapsed.value);
  let finalSegments = segments.value;
  let finalSummary: SummaryArtifact | undefined;

  try {
    if (!recordingId.value || backendMode.value !== "connected") throw new Error("服务端未连接。");
    if (!audioBlob) throw new Error("没有拿到真实录音文件。");
    await emotionTalkApi.createAudioUploadAuthorization(recordingId.value, audioBlob.type || "audio/webm", audioBlob.size);
    const audioTranscript = await emotionTalkApi.transcribeAudio(recordingId.value, audioBlob, title, durationText);
    finalSegments = audioTranscript.transcript?.segments ?? [];
    if (!finalSegments.length) throw new Error("百炼没有返回转写文本。");
    finalSummary = await emotionTalkApi.createSummaryJob(recordingId.value);
  } catch (error) {
    status.value = "failed";
    errorText.value = error instanceof Error ? error.message : "真实录音转写失败。";
    captureMode.value = "none";
    detailTab.value = "transcript";
    return;
  }

  const localId = recordingId.value || makeClientId("local_recording");
  summary.value = finalSummary;
  records.value = [{ localId, recordingId: recordingId.value || undefined, title, createdAt: "刚刚", durationText, status: "completed", segments: finalSegments, summary: finalSummary }, ...records.value];
  selectedRecordId.value = localId;
  status.value = "completed";
  captureMode.value = "none";
  detailTab.value = "summary";
}

function openRecord(record: ConversationRecord) {
  selectedRecordId.value = record.localId;
  screen.value = "detail";
  detailTab.value = "summary";
}

async function openAdvice() {
  errorText.value = "";
  try {
    const record = activeRecord.value;
    if (!record?.recordingId || backendMode.value !== "connected") throw new Error("请先完成一次真实录音和纪要。");
    screen.value = "advice";
    advice.value =
      await emotionTalkApi.createExpertAdviceJob(record.recordingId, contextScope);
  } catch (error) {
    screen.value = "detail";
    errorText.value = error instanceof Error ? error.message : "专家团建议生成失败。";
  }
}
</script>

<template>
  <view class="page">
    <view v-if="screen === 'home'" class="screen">
      <view class="home-status">
        <text>14:42</text>
        <view class="status-icons">
          <view class="signal"><text></text><text></text><text></text><text></text></view>
          <view class="battery"></view>
        </view>
      </view>
      <scroll-view scroll-y class="content">
        <view class="topbar">
          <view class="title-area">
            <text class="space-title">家的倾诉空间</text>
            <text class="space-subtitle">{{ spaceSubtitle }}</text>
          </view>
          <button class="icon-button">⌕</button>
          <button class="icon-button">···</button>
        </view>
        <view class="search"><text class="search-icon">⌕</text><text>搜索记录、原话、主题</text></view>
        <view class="portrait">
          <view class="portrait-head">
            <view>
              <text class="portrait-title">空间画像</text>
              <text class="portrait-subtitle">只基于真实转写和纪要生成</text>
            </view>
            <text class="small-pill">{{ portraitStatusText }}</text>
          </view>
          <view v-if="records.length" class="portrait-grid">
            <view><text class="metric">{{ records.length }}</text><text>真实记录</text></view>
            <view><text class="metric">已生成</text><text>AI 纪要</text></view>
            <view><text class="metric">可追溯</text><text>转写原文</text></view>
            <view><text class="metric">待触发</text><text>专家团</text></view>
          </view>
          <view v-else class="empty-line">完成第一次真实录音后，空间画像会从转写和纪要中生成。</view>
        </view>
        <view class="tabs"><text class="active-tab">最近</text><text>我的</text><text>共享</text><text>收藏</text></view>
        <view class="list-head"><text class="list-title">最近记录</text><button class="filter-button">筛选</button></view>
        <view class="record-list">
          <view v-if="!records.length" class="empty-line">还没有真实记录。点击右下角麦克风开始第一次倾诉。</view>
          <button v-for="record in records" :key="record.localId" class="record-row" @tap="openRecord(record)">
            <view class="doc-icon"><text></text><text></text><text></text><text></text></view>
            <view class="record-main">
              <text class="record-title">{{ record.title }}</text>
              <text class="record-meta">{{ record.createdAt }} · {{ record.durationText }} · 已摘要</text>
            </view>
            <text class="chevron">···</text>
          </button>
        </view>
      </scroll-view>
      <view class="floating-actions">
        <button class="float-add">＋</button>
        <button class="float-record" @tap="startRecording">
          <view class="mic-bars"><text></text><text></text><text></text><text></text></view>
        </button>
      </view>
      <view class="tabbar">
        <button class="active"><text class="tab-icon">⌂</text><text>空间</text></button>
        <button><text class="tab-icon">▱</text><text>记录</text></button>
        <button><text class="tab-icon">≡</text><text>主题</text></button>
        <button><text class="tab-icon">☰</text><text>我的</text></button>
      </view>
    </view>

    <view v-else-if="screen === 'detail'" class="screen">
      <view class="status"><button @tap="screen = 'home'">‹ 返回</button><text>{{ detailRecord.durationText }}</text></view>
      <view class="detail-head">
        <text class="title">{{ detailRecord.title }}</text>
        <text class="subtle">{{ detailRecord.createdAt }}</text>
      </view>
      <view v-if="errorText" class="error-card">{{ errorText }}</view>
      <view v-if="status === 'recording' || status === 'processing'" class="live-card">
        <view class="live-top"><text>{{ status === "processing" ? "生成纪要中" : captureText }}</text><text>{{ formatDuration(elapsed) }}</text></view>
        <button class="finish-button" :disabled="status === 'processing'" @tap="finishRecording">结束并生成纪要</button>
      </view>
      <view class="tabs"><button :class="{ 'active-tab': detailTab === 'summary' }" @tap="detailTab = 'summary'">纪要</button><button :class="{ 'active-tab': detailTab === 'transcript' }" @tap="detailTab = 'transcript'">转写</button></view>
      <scroll-view scroll-y class="detail-scroll">
        <view v-if="detailTab === 'summary'" class="summary-card">
          <text class="section-label">AI 纪要</text>
          <text class="summary-title">{{ visibleSummary.title }}</text>
          <text class="paragraph">{{ visibleSummary.overview }}</text>
          <view v-for="point in visibleSummary.keyPoints" :key="point" class="bullet">{{ point }}</view>
          <view v-for="chapter in visibleSummary.chapters" :key="chapter.title" class="chapter">
            <text class="chapter-time">{{ chapter.startTimestamp }}</text>
            <view><text class="chapter-title">{{ chapter.title }}</text><text class="paragraph">{{ chapter.summary }}</text></view>
          </view>
          <button class="primary" @tap="openAdvice">专家团建议</button>
        </view>
        <view v-else class="transcript">
          <view v-if="!detailSegments.length" class="empty-line">正在等待实时转写。如果浏览器不支持实时识别，结束后会用录音生成最终文本。</view>
          <view v-for="segment in detailSegments" :key="`${segment.timestamp}-${segment.text}`" class="segment">
            <text class="speaker">{{ segment.speaker }} · {{ segment.timestamp }}</text>
            <text class="segment-text">{{ segment.text }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <view v-else class="screen">
      <view class="status"><button @tap="screen = 'detail'">‹ 详情</button><text>专家团</text></view>
      <scroll-view scroll-y class="detail-scroll">
        <view class="summary-card">
          <text class="section-label">裁判结论</text>
          <text class="summary-title">{{ visibleAdvice.artifact.overview }}</text>
          <view v-for="suggestion in visibleAdvice.artifact.suggestions" :key="suggestion.title" class="advice">
            <text class="chapter-title">{{ suggestion.title }}</text>
            <text class="paragraph">{{ suggestion.body }}</text>
          </view>
        </view>
        <view class="timeline">
          <view v-for="event in visibleAdviceEvents" :key="event.eventId" class="event">
            <text class="speaker">第 {{ event.round }} 轮 · {{ participantNames[event.participant || ''] || event.participant }}</text>
            <text class="segment-text">{{ event.payload.content }}</text>
          </view>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100dvh;
  display: flex;
  justify-content: center;
  background:
    radial-gradient(circle at 8% 10%, rgba(23, 120, 255, 0.13), transparent 30%),
    radial-gradient(circle at 92% 18%, rgba(130, 118, 255, 0.13), transparent 28%),
    linear-gradient(135deg, #f7f9fd 0%, #edf1f7 100%);
}

.screen {
  width: min(100vw, 430px);
  min-height: 100dvh;
  padding: 0;
  background: linear-gradient(180deg, #fbfdff, #f5f7fb);
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
}

.status,
.home-status {
  height: 56px;
  padding: 18px 24px 0;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 700;
}

.home-status {
  color: #0f172a;
}

.status-icons {
  display: flex;
  gap: 7px;
  align-items: center;
  color: #111827;
}

.signal {
  width: 22px;
  height: 15px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  align-items: end;
  gap: 2px;
}

.signal text {
  display: block;
  border-radius: 999px;
  background: currentColor;
}

.signal text:nth-child(1) {
  height: 5px;
}

.signal text:nth-child(2) {
  height: 8px;
}

.signal text:nth-child(3) {
  height: 11px;
}

.signal text:nth-child(4) {
  height: 14px;
}

.battery {
  width: 26px;
  height: 13px;
  border: 2px solid currentColor;
  border-radius: 5px;
  position: relative;
  box-sizing: border-box;
}

.battery::after {
  content: "";
  position: absolute;
  right: -5px;
  top: 3px;
  width: 3px;
  height: 5px;
  border-radius: 0 2px 2px 0;
  background: currentColor;
}

.battery::before {
  content: "";
  position: absolute;
  inset: 2px 7px 2px 2px;
  border-radius: 2px;
  background: currentColor;
}

.content {
  height: calc(100dvh - 56px);
  padding: 0 22px 116px;
  box-sizing: border-box;
  scrollbar-width: none;
}

.content::-webkit-scrollbar {
  width: 0;
  height: 0;
}

:deep(.uni-scroll-view) {
  scrollbar-width: none;
}

:deep(.uni-scroll-view)::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0 24px;
}

.title-area {
  flex: 1;
  min-width: 0;
}

.space-title {
  display: block;
  color: #111827;
  font-size: 28px;
  font-weight: 780;
  line-height: 1.08;
  letter-spacing: 0;
}

.space-subtitle {
  display: block;
  margin-top: 8px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 650;
}

.icon-button {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  color: #111827;
  font-size: 20px;
  font-weight: 800;
  box-shadow: 0 8px 24px rgba(31, 45, 68, 0.08);
}

.portrait,
.summary-card,
.live-card {
  background: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 22px;
  box-shadow: 0 12px 32px rgba(31, 45, 68, 0.11);
}

.eyebrow,
.section-label,
.subtle,
.record-meta,
.speaker,
.chapter-time {
  color: #7b8494;
  font-size: 13px;
}

.title {
  display: block;
  margin-top: 10px;
  color: #111827;
  font-size: 34px;
  font-weight: 900;
  line-height: 1.12;
}

.search,
.tabs {
  border-radius: 999px;
  background: #e9eef6;
  color: #7b8494;
  font-size: 14px;
  font-weight: 700;
}

.search {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
  height: 42px;
  padding: 0 14px;
  margin-bottom: 18px;
  box-sizing: border-box;
}

.search-icon {
  font-size: 20px;
}

.portrait {
  padding: 18px;
  margin-bottom: 18px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(239, 246, 255, 0.95)),
    #ffffff;
}

.portrait-head,
.live-top,
.chapter,
.event {
  display: flex;
  align-items: center;
}

.portrait-head,
.live-top {
  justify-content: space-between;
}

.portrait-title {
  display: block;
  color: #111827;
  font-size: 21px;
  font-weight: 760;
  line-height: 1.16;
}

.portrait-subtitle {
  display: block;
  margin-top: 8px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}

.small-pill {
  min-height: 28px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #edf3fb;
  color: #334155;
  font-size: 12px;
  font-weight: 680;
  white-space: nowrap;
}

.portrait-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
  margin-top: 14px;
}

.portrait-grid view {
  min-height: 54px;
  padding: 11px 12px;
  border-radius: 15px;
  background: rgba(241, 245, 251, 0.82);
  color: #334155;
  font-size: 12px;
  line-height: 1.35;
}

.metric {
  display: block;
  color: #111827;
  font-size: 15px;
  font-weight: 760;
  margin-bottom: 4px;
}

.tabs {
  display: flex;
  justify-content: space-around;
  height: 45px;
  margin: 10px 0 20px;
  padding: 4px;
  box-sizing: border-box;
  background: rgba(224, 231, 242, 0.72);
}

.tabs text,
.tabs button {
  flex: 1;
  height: 37px;
  display: grid;
  place-items: center;
  border-radius: 999px;
}

.active-tab {
  color: #111827;
  font-weight: 900;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(31, 45, 68, 0.08);
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 24px 0 12px;
}

.list-title {
  font-size: 21px;
  line-height: 1.16;
  font-weight: 760;
}

.filter-button {
  padding: 8px 14px;
  border-radius: 999px;
  background: #eef4ff;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 94px;
}

.record-row {
  width: 100%;
  display: grid;
  grid-template-columns: 46px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 11px 4px;
  text-align: left;
  border-radius: 18px;
}

.doc-icon {
  width: 44px;
  height: 52px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  padding: 9px 8px;
  box-sizing: border-box;
  border-radius: 13px;
  background: linear-gradient(180deg, #ffffff, #e9eef6);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18), 0 6px 14px rgba(31, 45, 68, 0.1);
}

.doc-icon text {
  display: block;
  height: 4px;
  border-radius: 999px;
}

.doc-icon text:nth-child(1) {
  background: #a9c6ff;
}

.doc-icon text:nth-child(2) {
  background: #b8a8ff;
}

.doc-icon text:nth-child(3) {
  background: #bce8d1;
}

.doc-icon text:nth-child(4) {
  width: 54%;
  background: #ffd6e2;
}

.record-main {
  flex: 1;
}

.record-title,
.summary-title,
.chapter-title,
.segment-text {
  display: block;
  color: #111827;
  font-weight: 800;
}

.record-title {
  font-size: 17px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-meta {
  display: block;
  margin-top: 7px;
  font-size: 12px;
}

.chevron {
  color: #94a3b8;
  font-size: 24px;
  font-weight: 900;
  line-height: 1;
  padding-bottom: 14px;
}

.floating-actions {
  position: absolute;
  right: 22px;
  bottom: 92px;
  z-index: 12;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.float-add,
.float-record {
  z-index: 5;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: #111827;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(31, 45, 68, 0.14);
}

.float-add {
  width: 58px;
  height: 58px;
  font-size: 28px;
}

.float-record {
  width: 66px;
  height: 66px;
  color: #ffffff;
  background: linear-gradient(180deg, #158bff, #0f6fe8);
}

.tabbar {
  position: absolute;
  left: 20px;
  right: 20px;
  bottom: 18px;
  z-index: 10;
  height: 68px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  padding: 7px;
  box-sizing: border-box;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.74);
  box-shadow: 0 16px 42px rgba(31, 45, 68, 0.13);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.tabbar button {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-radius: 22px;
  color: #6b7280;
  background: transparent;
  font-size: 11px;
  font-weight: 650;
}

.tabbar button.active {
  background: rgba(232, 238, 247, 0.86);
  color: #111827;
}

.tab-icon {
  font-size: 17px;
  line-height: 1;
}

.mic-bars {
  height: 30px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.mic-bars text {
  width: 4px;
  border-radius: 999px;
  background: #ffffff;
}

.mic-bars text:nth-child(1) {
  height: 14px;
}

.mic-bars text:nth-child(2) {
  height: 25px;
}

.mic-bars text:nth-child(3) {
  height: 30px;
}

.mic-bars text:nth-child(4) {
  height: 18px;
}

.detail-head {
  margin: 22px 22px;
}

.live-card {
  padding: 18px;
  margin: 0 22px;
}

.error-card {
  margin: 0 22px 14px;
  padding: 14px 16px;
  border-radius: 16px;
  color: #991b1b;
  background: #fee2e2;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
}

.finish-button,
.primary {
  width: 100%;
  margin-top: 18px;
  padding: 15px 18px;
  border-radius: 999px;
  color: white;
  background: #1778ff;
  font-weight: 900;
}

.detail-scroll {
  width: calc(100% - 44px);
  height: calc(100dvh - 190px);
  margin: 18px 22px 0;
  box-sizing: border-box;
}

.screen > .tabs {
  margin: 18px 22px 0;
}

.summary-card,
.transcript,
.timeline {
  padding: 20px;
}

.summary-title {
  margin: 10px 0;
  font-size: 22px;
  line-height: 1.25;
}

.paragraph,
.bullet,
.empty-line {
  display: block;
  color: #5f6b7a;
  font-size: 14px;
  line-height: 1.7;
}

.bullet {
  margin-top: 10px;
  padding: 12px;
  border-radius: 14px;
  background: #f3f6fb;
}

.chapter,
.event,
.advice {
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e7ecf4;
}

.segment {
  padding: 18px 0;
  border-bottom: 1px solid #e7ecf4;
}

.speaker {
  display: block;
  margin-bottom: 8px;
}
</style>
