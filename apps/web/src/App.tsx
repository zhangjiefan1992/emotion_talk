import {
  ArrowLeft,
  BookmarkSimple,
  Check,
  Copy,
  DotsThree,
  FunnelSimple,
  House,
  MagnifyingGlass,
  Microphone,
  PaperPlaneRight,
  Play,
  Plus,
  ShareFat,
  SlidersHorizontal,
  Sparkle,
  UserCircle,
  Waveform,
  X,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";

import { emotionTalkApi, makeClientId } from "./api";
import { formatDuration, liveTranscriptSeed, recentRecords } from "./sampleData";
import type {
  ContextScope,
  ConversationRecord,
  DeliberationEvent,
  ExpertAdviceJobResponse,
  RecordingStatus,
  SummaryArtifact,
  TranscriptSegment,
} from "./types";

type ScreenName = "home" | "detail" | "advice" | "profile";
type DetailTab = "transcript" | "summary" | "chapters";
type BackendMode = "checking" | "connected" | "demo";
type AdvicePhase = "idle" | "history" | "experts" | "done";

const participantNames: Record<string, string> = {
  life_coach: "人生教练",
  counselor: "心理咨询",
  reality_strategist: "现实行动",
  judge: "裁判",
};

function nowTitle() {
  return `${new Date().toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })} 晚间倾诉`;
}

function makeLocalSummary(title: string, segments: TranscriptSegment[]): SummaryArtifact {
  return {
    summaryJobId: "local-summary",
    recordingId: "local-recording",
    status: "completed",
    title,
    overview: "这次对话的核心不是马上解决整个人生方向，而是把迷茫、比较感和下一步行动拆开。",
    keyPoints: segments.slice(0, 4).map((segment) => segment.text),
    chapters: [
      { title: "迷茫的核心", startTimestamp: "00:00", summary: "围绕当前状态是否是真实想要的生活展开。" },
      { title: "对选择的担心", startTimestamp: "00:42", summary: "担心别人往前走，自己却不知道下一步。" },
      { title: "先拆开问题", startTimestamp: "01:10", summary: "将人生问题降到一个可验证的小动作。" },
    ],
  };
}

function makeLocalAdvice(contextScope: ContextScope): ExpertAdviceJobResponse {
  const events: DeliberationEvent[] = [
    {
      eventId: "local-1",
      jobId: "local-job",
      seq: 1,
      type: "expert_message_added",
      visibility: "user_visible",
      participant: "life_coach",
      round: 1,
      payload: { title: "初判", content: "核心不是选哪条路，而是先看她希望哪种生活方式继续出现。" },
    },
    {
      eventId: "local-2",
      jobId: "local-job",
      seq: 2,
      type: "expert_message_added",
      visibility: "user_visible",
      participant: "counselor",
      round: 1,
      payload: { title: "初判", content: "迷茫和比较感是真实压力信号，但只能作为线索，不能下判断。" },
    },
    {
      eventId: "local-3",
      jobId: "local-job",
      seq: 3,
      type: "expert_message_added",
      visibility: "user_visible",
      participant: "reality_strategist",
      round: 1,
      payload: { title: "初判", content: "现在不适合做大计划，先把担心拆成事实和想象两类。" },
    },
    {
      eventId: "local-4",
      jobId: "local-job",
      seq: 4,
      type: "expert_challenge_added",
      visibility: "user_visible",
      participant: "counselor",
      round: 2,
      payload: { title: "互评", content: "提醒人生教练不要过早谈价值排序，她现在可能更需要情绪被安放。" },
    },
    {
      eventId: "local-5",
      jobId: "local-job",
      seq: 5,
      type: "expert_challenge_added",
      visibility: "user_visible",
      participant: "reality_strategist",
      round: 2,
      payload: { title: "互评", content: "提醒心理咨询视角避免抽象解释太多，用户需要一个不会增加压力的小动作。" },
    },
    {
      eventId: "local-6",
      jobId: "local-job",
      seq: 6,
      type: "expert_challenge_added",
      visibility: "user_visible",
      participant: "life_coach",
      round: 2,
      payload: { title: "互评", content: "同意降低抽象度，先不要求她回答“我是谁”这种大问题。" },
    },
    {
      eventId: "local-7",
      jobId: "local-job",
      seq: 7,
      type: "expert_revision_added",
      visibility: "user_visible",
      participant: "life_coach",
      round: 3,
      payload: { title: "修正", content: "把“价值排序”降级为“想保护什么”，问题更小，也更适合当下。" },
    },
    {
      eventId: "local-8",
      jobId: "local-job",
      seq: 8,
      type: "expert_revision_added",
      visibility: "user_visible",
      participant: "counselor",
      round: 3,
      payload: { title: "修正", content: "保留“失控感”这个可能性，但必须标注不确定，不做诊断。" },
    },
    {
      eventId: "local-9",
      jobId: "local-job",
      seq: 9,
      type: "expert_revision_added",
      visibility: "user_visible",
      participant: "reality_strategist",
      round: 3,
      payload: { title: "修正", content: "最终行动只保留一个：写下三个担心失去的东西，不排序，不决策。" },
    },
  ];

  return {
    jobId: "local-job",
    sourceType: "recording",
    sourceId: "local-recording",
    template: "expert_team_v1",
    status: "completed",
    events,
    contextUsage: {
      scope: contextScope,
      primary: "current_recording",
      historyCount: contextScope === "current_with_history" ? 3 : 0,
      historySources: [],
      profileIncluded: contextScope === "current_with_history",
    },
    artifact: {
      overview: "本次不是缺答案，而是需要先把焦虑、价值和现实约束分开。",
      processSummary: [
        { round: 1, title: "第一轮讨论", summary: "三位专家分别初判。" },
        { round: 2, title: "第二轮讨论", summary: "互相质疑和压缩风险。" },
        { round: 3, title: "第三轮讨论", summary: "根据质疑修正结论。" },
      ],
      suggestions: [
        {
          title: "先暂停重大决定 24 小时",
          body: "不要在情绪高点做长期选择，先把担心拆开。",
          confidence: "medium",
          evidence: ["用户表达了害怕选错。"],
        },
        {
          title: "把担心写成事实和想象两列",
          body: "下一次倾诉可以继续聊“我真正想保护什么”。",
          confidence: "medium",
          evidence: ["对话中出现了对小动作的接受。"],
        },
      ],
      keyUncertainties: ["核心压力来自职业变化还是身份变化仍需确认。"],
      safetyBoundary: "建议仅供参考，最终决定权在你手中。",
    },
  };
}

export function App() {
  const [backendMode, setBackendMode] = useState<BackendMode>("checking");
  const [spaceId, setSpaceId] = useState<string | null>(null);
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const [screen, setScreen] = useState<ScreenName>("home");
  const [detailTab, setDetailTab] = useState<DetailTab>("transcript");
  const [status, setStatus] = useState<RecordingStatus>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [segments, setSegments] = useState<TranscriptSegment[]>(liveTranscriptSeed.slice(0, 4));
  const [records, setRecords] = useState<ConversationRecord[]>(recentRecords);
  const [selectedRecordId, setSelectedRecordId] = useState(recentRecords[0]?.localId ?? "");
  const [summary, setSummary] = useState<SummaryArtifact | undefined>();
  const [expertAdvice, setExpertAdvice] = useState<ExpertAdviceJobResponse | undefined>();
  const [contextScope] = useState<ContextScope>("current_with_history");
  const [advicePhase, setAdvicePhase] = useState<AdvicePhase>("idle");
  const [coachReplyVisible, setCoachReplyVisible] = useState(false);
  const [followup, setFollowup] = useState("");
  const [recordingNotice, setRecordingNotice] = useState("");

  const timerRef = useRef<number | null>(null);
  const transcriptTimerRef = useRef<number | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const adviceTimersRef = useRef<number[]>([]);

  const activeRecord = useMemo(
    () => records.find((record) => record.localId === selectedRecordId) ?? records[0],
    [records, selectedRecordId],
  );
  const isLiveRecording = status === "recording" || status === "processing";
  const detailSegments = isLiveRecording ? segments : activeRecord?.segments?.length ? activeRecord.segments : liveTranscriptSeed;
  const detailRecord: ConversationRecord | undefined = isLiveRecording
    ? {
        localId: "live-recording",
        recordingId: recordingId ?? undefined,
        title: status === "processing" ? "正在处理" : "正在录音",
        createdAt: "刚刚",
        durationText: formatDuration(elapsed),
        status,
        segments,
      }
    : activeRecord;
  const visibleSummary = summary ?? (!isLiveRecording ? activeRecord?.summary : undefined) ?? makeLocalSummary(detailRecord?.title ?? "未命名对话", detailSegments);
  const visibleAdvice = expertAdvice ?? makeLocalAdvice(contextScope);

  useEffect(() => {
    emotionTalkApi
      .health()
      .then(() => setBackendMode("connected"))
      .catch(() => setBackendMode("demo"));
  }, []);

  useEffect(() => {
    return () => {
      stopTimers();
      void stopBrowserRecorder();
      adviceTimersRef.current.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  async function ensureSpace() {
    if (spaceId) return spaceId;
    const space = await emotionTalkApi.createSpace("家的倾诉空间");
    setSpaceId(space.spaceId);
    return space.spaceId;
  }

  function showScreen(name: ScreenName) {
    setScreen(name);
    if (name !== "advice") setCoachReplyVisible(false);
  }

  function stopTimers() {
    if (timerRef.current) window.clearInterval(timerRef.current);
    if (transcriptTimerRef.current) window.clearInterval(transcriptTimerRef.current);
    timerRef.current = null;
    transcriptTimerRef.current = null;
  }

  async function startBrowserRecorder() {
    const params = new URLSearchParams(window.location.search);
    mediaChunksRef.current = [];
    if (params.get("mockAudio") === "1") return "当前为模拟录音，用来验证转写和摘要流程。";
    if (!window.isSecureContext) return "当前是 HTTP/IP 访问，浏览器不会开放真实麦克风；已进入模拟转写。";
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") return "当前浏览器不支持网页录音；已进入模拟转写。";

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) mediaChunksRef.current.push(event.data);
      };
      recorder.onstop = () => stream.getTracks().forEach((track) => track.stop());
      recorder.start(1000);
      mediaRecorderRef.current = recorder;
      return "真实麦克风录音中。";
    } catch {
      return "麦克风未授权或不可用；已进入模拟转写。";
    }
  }

  function stopBrowserRecorder() {
    const recorder = mediaRecorderRef.current;
    mediaRecorderRef.current = null;
    if (!recorder || recorder.state === "inactive") return Promise.resolve();
    return new Promise<void>((resolve) => {
      const previousOnStop = recorder.onstop;
      recorder.onstop = (event) => {
        previousOnStop?.call(recorder, event);
        resolve();
      };
      recorder.stop();
    });
  }

  async function startRecording() {
    setStatus("recording");
    setElapsed(0);
    setSegments([]);
    setSummary(undefined);
    setExpertAdvice(undefined);
    setAdvicePhase("idle");
    setRecordingNotice("正在请求麦克风...");
    setScreen("detail");
    setDetailTab("transcript");
    setRecordingNotice(await startBrowserRecorder());

    try {
      if (backendMode === "connected") {
        const currentSpaceId = await ensureSpace();
        const recording = await emotionTalkApi.createRecording(currentSpaceId, nowTitle());
        setRecordingId(recording.recordingId);
        await emotionTalkApi.createAsrSession(currentSpaceId, recording.recordingId);
      }
    } catch {
      setRecordingId(null);
    }

    timerRef.current = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    let cursor = 0;
    transcriptTimerRef.current = window.setInterval(() => {
      if (cursor >= liveTranscriptSeed.length) return;
      const nextSegment = liveTranscriptSeed[cursor];
      cursor += 1;
      setSegments((current) => [...current, nextSegment]);
    }, 1500);
  }

  function cancelRecording() {
    stopTimers();
    void stopBrowserRecorder();
    setStatus("idle");
  }

  async function finishRecording() {
    if (status !== "recording") return;
    setStatus("processing");
    stopTimers();
    await stopBrowserRecorder();

    const finalSegments = segments.length ? segments : liveTranscriptSeed;
    const durationText = formatDuration(Math.max(elapsed, 136));
    const title = "刚刚的倾诉记录";
    let finalSummary = makeLocalSummary(title, finalSegments);

    try {
      const audioBlob = mediaChunksRef.current.length
        ? new Blob(mediaChunksRef.current, { type: mediaChunksRef.current[0]?.type || "audio/webm" })
        : null;
      if (recordingId && audioBlob) {
        await emotionTalkApi.createAudioUploadAuthorization(recordingId, audioBlob.type, audioBlob.size);
      }
      if (recordingId && backendMode === "connected") {
        await emotionTalkApi.submitTranscript(recordingId, title, durationText, finalSegments);
        finalSummary = await emotionTalkApi.createSummaryJob(recordingId);
      }
    } catch {
      finalSummary = makeLocalSummary(title, finalSegments);
    }

    const localId = recordingId ?? makeClientId("local_recording");
    setSummary(finalSummary);
    setRecords((current) => [
      {
        localId,
        recordingId: recordingId ?? undefined,
        title,
        createdAt: "刚刚",
        durationText,
        status: "completed",
        segments: finalSegments,
        summary: finalSummary,
      },
      ...current,
    ]);
    setSelectedRecordId(localId);
    setStatus("completed");
    setScreen("detail");
    setDetailTab("summary");
  }

  async function startAdvice() {
    setScreen("advice");
    setAdvicePhase("history");
    setCoachReplyVisible(false);
    adviceTimersRef.current.forEach((id) => window.clearTimeout(id));
    adviceTimersRef.current = [
      window.setTimeout(() => setAdvicePhase("experts"), 1000),
      window.setTimeout(async () => {
        try {
          const targetRecord = activeRecord;
          const job =
            targetRecord?.recordingId && backendMode === "connected"
              ? await emotionTalkApi.createExpertAdviceJob(targetRecord.recordingId, contextScope)
              : makeLocalAdvice(contextScope);
          setExpertAdvice(job);
        } catch {
          setExpertAdvice(makeLocalAdvice(contextScope));
        } finally {
          setAdvicePhase("done");
        }
      }, 2100),
    ];
  }

  function openRecord(record: ConversationRecord) {
    setSelectedRecordId(record.localId);
    setScreen("detail");
    setDetailTab("transcript");
  }

  function sendFollowup() {
    if (!followup.trim()) return;
    setCoachReplyVisible(true);
    setFollowup("");
  }

  return (
    <main className="page">
      <section className="phone-shell" aria-label="Emotion Talk">
        <div className="phone">
          <HomeScreen
            active={screen === "home"}
            records={records}
            backendMode={backendMode}
            onOpenProfile={() => showScreen("profile")}
            onOpenDetail={openRecord}
            onStartRecording={startRecording}
          />
          <DetailScreen
            active={screen === "detail"}
            tab={detailTab}
            record={detailRecord}
            summary={visibleSummary}
            segments={detailSegments}
            onBack={() => showScreen("home")}
            onTabChange={setDetailTab}
            onStartAdvice={startAdvice}
          />
          <AdviceScreen
            active={screen === "advice"}
            phase={advicePhase}
            advice={visibleAdvice}
            followup={followup}
            coachReplyVisible={coachReplyVisible}
            onBack={() => showScreen("detail")}
            onFollowupChange={setFollowup}
            onSendFollowup={sendFollowup}
          />
          <ProfileScreen active={screen === "profile"} onBack={() => showScreen("home")} />
          <RecordingPanel
            active={status === "recording" || status === "processing"}
            elapsed={elapsed}
            processing={status === "processing"}
            notice={recordingNotice}
            onCancel={cancelRecording}
            onFinish={finishRecording}
          />
        </div>
      </section>
    </main>
  );
}

function StatusBar({ time = "14:42" }: { time?: string }) {
  return (
    <div className="status">
      <span>{time}</span>
      <span className="status-icons">
        <span className="signal" aria-hidden="true"><span /><span /><span /><span /></span>
        <span className="battery" aria-hidden="true" />
      </span>
    </div>
  );
}

function IconButton({ label, children, onClick }: { label: string; children: React.ReactNode; onClick?: () => void }) {
  return (
    <button className="icon-btn" type="button" aria-label={label} onClick={onClick}>
      {children}
    </button>
  );
}

function HomeScreen({
  active,
  records,
  backendMode,
  onOpenProfile,
  onOpenDetail,
  onStartRecording,
}: {
  active: boolean;
  records: ConversationRecord[];
  backendMode: BackendMode;
  onOpenProfile: () => void;
  onOpenDetail: (record: ConversationRecord) => void;
  onStartRecording: () => void;
}) {
  return (
    <section className={`screen ${active ? "active" : ""}`} aria-label="空间首页">
      <StatusBar />
      <div className="content">
        <div className="topbar">
          <div className="title-area">
            <h1>家的倾诉空间</h1>
            <p className="subtle">2 位成员  18 条记录</p>
          </div>
          <IconButton label="搜索"><MagnifyingGlass className="icon" /></IconButton>
          <IconButton label="更多"><DotsThree className="icon" /></IconButton>
        </div>

        <div className="search">
          <MagnifyingGlass className="icon" />
          <span>搜索记录、原话、主题</span>
        </div>

        <button className="profile-card" type="button" onClick={onOpenProfile}>
          <div className="profile-head">
            <div>
              <h2>空间画像</h2>
              <p className="subtle">系统目前的理解，可查看和修正</p>
            </div>
            <span className="tag">{backendMode === "connected" ? "更新于今天" : "演示"}</span>
          </div>
          <div className="profile-grid">
            <span className="soft-chip"><strong>3</strong>反复主题</span>
            <span className="soft-chip"><strong>焦虑</strong>常见情绪</span>
            <span className="soft-chip"><strong>选择压力</strong>本周高频</span>
            <span className="soft-chip"><strong>陪伴</strong>支持偏好</span>
          </div>
        </button>

        <div className="segment" aria-label="记录分组">
          <button className="active" type="button">最近</button>
          <button type="button">我的</button>
          <button type="button">共享</button>
          <button type="button">收藏</button>
        </div>

        <div className="section-head">
          <h2>最近记录</h2>
          <button className="pill" type="button"><FunnelSimple size={14} />筛选</button>
        </div>

        <div className="list">
          {recordsForInteraction(records).map((record, index) => (
            <RecordRow key={`${record.localId}-${index}`} record={record} index={index} onOpen={() => onOpenDetail(record)} />
          ))}
        </div>
      </div>

      <div className="floating-actions">
        <button className="round-action" type="button" aria-label="新建"><Plus className="icon" /></button>
        <button className="record-btn" type="button" onClick={onStartRecording} aria-label="开始录音">
          <Microphone className="icon" />
        </button>
      </div>

      <nav className="tabbar" aria-label="底部导航">
        <button className="active" type="button"><House className="icon" />空间</button>
        <button type="button"><BookmarkSimple className="icon" />记录</button>
        <button type="button"><SlidersHorizontal className="icon" />主题</button>
        <button type="button"><UserCircle className="icon" />我的</button>
      </nav>
    </section>
  );
}

function recordsForInteraction(records: ConversationRecord[]) {
  return records;
}

function RecordRow({ record, index, onOpen }: { record: ConversationRecord; index: number; onOpen: () => void }) {
  const tags = ["已关联 3 条历史", "已摘要", "画像已更新", "已收藏"];
  return (
    <button className="list-row" type="button" onClick={onOpen}>
      <span className="thumb" aria-hidden="true"><span className="thumb-line" /><span className="thumb-line" /><span className="thumb-line" /><span className="thumb-line" /></span>
      <span>
        <span className="row-title">{record.title}</span>
        <span className="row-meta"><span>{record.createdAt}</span><span>{record.durationText}</span><span>{tags[index] ?? "已摘要"}</span></span>
      </span>
      <span className="more">...</span>
    </button>
  );
}

function DetailScreen({
  active,
  tab,
  record,
  summary,
  segments,
  onBack,
  onTabChange,
  onStartAdvice,
}: {
  active: boolean;
  tab: DetailTab;
  record?: ConversationRecord;
  summary: SummaryArtifact;
  segments: TranscriptSegment[];
  onBack: () => void;
  onTabChange: (tab: DetailTab) => void;
  onStartAdvice: () => void;
}) {
  return (
    <section className={`screen ${active ? "active" : ""}`} aria-label="记录详情">
      <StatusBar time="14:44" />
      <div className="content">
        <div className="topbar">
          <IconButton label="返回" onClick={onBack}><ArrowLeft className="icon" /></IconButton>
          <span className="title-area" />
          <IconButton label="分享"><ShareFat className="icon" /></IconButton>
          <IconButton label="更多"><DotsThree className="icon" /></IconButton>
        </div>

        <h1 className="detail-title">{record?.title ?? "未命名对话"}</h1>
        <p className="subtle">{record?.createdAt ?? "刚刚"}  {record?.durationText ?? "00:00"}</p>

        <div className="player">
          <button className="play" type="button" aria-label="播放"><Play weight="fill" className="icon" /></button>
          <div className="player-mid">
            <div className="progress"><span /></div>
            <div className="player-times"><span>08:32</span><span>{record?.durationText ?? "35:47"}</span></div>
          </div>
          <span className="speed">1.0x</span>
        </div>

        <div className="tabs">
          <button className={tab === "transcript" ? "active" : ""} type="button" onClick={() => onTabChange("transcript")}>转写</button>
          <button className={tab === "summary" ? "active" : ""} type="button" onClick={() => onTabChange("summary")}>AI摘要</button>
          <button className={tab === "chapters" ? "active" : ""} type="button" onClick={() => onTabChange("chapters")}>章节</button>
        </div>

        <div className={`transcript ${tab === "transcript" ? "active" : ""}`}>
          {segments.slice(0, 4).map((segment, index) => (
            <article className="utterance" key={`${segment.timestamp}-${index}`}>
              <span className={`speaker ${index % 2 === 0 ? "rose" : ""}`}>{index % 2 === 0 ? "1" : "2"}</span>
              <div>
                <div className="speaker-line">{index % 2 === 0 ? "满月" : "戒凡"} {segment.timestamp}</div>
                <p>{segment.text}</p>
              </div>
            </article>
          ))}
        </div>

        <div className={`summary ${tab === "summary" ? "active" : ""}`}>
          <article className="note-card">
            <h3>本次主要困惑</h3>
            <ul className="bullet-list">
              {(summary.keyPoints.length ? summary.keyPoints : [
                "不确定当前选择是出于真实意愿，还是被焦虑推动。",
                "反复出现“害怕选错”和“想重新定义自己”的表达。",
                "当前更需要把担心拆开，而不是立刻做结论。",
              ]).slice(0, 3).map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
          <article className="note-card">
            <h3>和历史记录的关联</h3>
            <ul className="bullet-list">
              <li>“不知道自己想成为什么样的人”在最近 3 次记录中反复出现。</li>
              <li>“害怕以后后悔”与 06-13 的职业转型记录高度相关。</li>
              <li>系统不确定：核心压力来自职业变化，还是身份变化。</li>
            </ul>
          </article>
          <button className="primary-action" type="button" onClick={onStartAdvice}>
            <Sparkle className="icon" />
            请求专家团建议
          </button>
        </div>

        <div className={`chapters ${tab === "chapters" ? "active" : ""}`}>
          {summary.chapters.map((chapter) => (
            <article className="note-card" key={chapter.title}>
              <h3>{chapter.startTimestamp} {chapter.title}</h3>
              <p>{chapter.summary}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function AdviceScreen({
  active,
  phase,
  advice,
  followup,
  coachReplyVisible,
  onBack,
  onFollowupChange,
  onSendFollowup,
}: {
  active: boolean;
  phase: AdvicePhase;
  advice: ExpertAdviceJobResponse;
  followup: string;
  coachReplyVisible: boolean;
  onBack: () => void;
  onFollowupChange: (value: string) => void;
  onSendFollowup: () => void;
}) {
  const done = phase === "done";
  const rounds = groupEventsByRound(advice.events);
  return (
    <section className={`screen ${active ? "active" : ""}`} aria-label="专家团建议">
      <StatusBar time="14:47" />
      <div className="content">
        <div className="topbar">
          <IconButton label="返回" onClick={onBack}><ArrowLeft className="icon" /></IconButton>
          <span className="title-area" />
          <IconButton label="复制"><Copy className="icon" /></IconButton>
        </div>

        <h1 className="detail-title">专家团建议</h1>
        <p className="subtle">基于当前对话，参考 3 条相关历史记录</p>

        <div className="advice-status">
          <div className="status-row done">
            <span className="check">✓</span>
            <span>
              <span className="status-label">读取当前对话</span>
              <span className="status-copy">已提取核心问题和关键原话</span>
            </span>
            <span className="tag">完成</span>
          </div>
          <div className={`status-row ${done ? "done" : "running"}`}>
            <span className="check">{done ? "✓" : "2"}</span>
            <span>
              <span className="status-label">{done ? "专家团建议完成" : phase === "experts" ? "专家团多轮讨论" : "参考历史记录"}</span>
              <span className="status-copy">{done ? "已生成总-多轮过程-裁判结论" : phase === "experts" ? "正在初判、质疑、修正，并交给裁判收敛" : "正在查找最近相似主题"}</span>
            </span>
            <span className="tag">{done ? "完成" : "生成中"}</span>
          </div>
        </div>

        <div className={`expert-grid ${done ? "" : "hidden"}`}>
          <article className="advice-card">
            <h3>专家团摘要</h3>
            <ul className="bullet-list">
              <li>{advice.artifact.overview}</li>
              <li>现在不宜立刻做重大决定，先澄清“我害怕失去什么”。</li>
              <li>可以先做一个 20 分钟的小练习，不把它变成计划压力。</li>
            </ul>
          </article>

          {rounds.map((round) => (
            <article className="round-card" key={round.round}>
              <div className="round-head">
                <span className="round-title">
                  <strong>{round.round === 1 ? "第一轮讨论" : round.round === 2 ? "第二轮讨论" : "第三轮讨论"}</strong>
                  <span>{round.round === 1 ? "三位专家分别初判" : round.round === 2 ? "互相质疑和压缩风险" : "根据质疑修正结论"}</span>
                </span>
                <span className="tag">{round.round === 1 ? "初判" : round.round === 2 ? "质疑" : "修正"}</span>
              </div>
              {round.events.map((event) => (
                <div className="agent-line" key={event.eventId}>
                  <span className="agent-name">{participantNames[event.participant ?? ""] ?? "专家"}</span>
                  <span className="agent-text">{event.payload.content}</span>
                </div>
              ))}
            </article>
          ))}

          <article className="judge-card">
            <div className="expert-head">
              <h3>裁判收敛</h3>
              <span className="tag">最终取舍</span>
            </div>
            <p>裁判保留“先拆分担心”作为最终建议，删除“马上做价值排序”的版本。原因是后者更重，可能增加压力。</p>
          </article>

          <article className="advice-card">
            <h3>最终建议</h3>
            <ul className="bullet-list">
              {advice.artifact.suggestions.map((suggestion) => <li key={suggestion.title}>{suggestion.title}：{suggestion.body}</li>)}
            </ul>
            <div className={`coach-reply ${coachReplyVisible ? "active" : ""}`}>我理解你的补充。这个信息更像是“关键事实修正”，系统会建议重新审视现实行动部分，但不需要推翻整份建议。</div>
          </article>
        </div>
      </div>

      <div className="input-bar">
        <input value={followup} onChange={(event) => onFollowupChange(event.target.value)} type="text" placeholder="补充、追问或反驳，系统会判断怎么处理" />
        <button className="send" type="button" onClick={onSendFollowup} aria-label="发送"><PaperPlaneRight className="icon" /></button>
      </div>
    </section>
  );
}

function groupEventsByRound(events: DeliberationEvent[]) {
  return [1, 2, 3].map((round) => ({
    round,
    events: events.filter((event) => event.round === round && event.participant && event.payload.content),
  }));
}

function ProfileScreen({ active, onBack }: { active: boolean; onBack: () => void }) {
  return (
    <section className={`screen ${active ? "active" : ""}`} aria-label="空间画像">
      <StatusBar time="14:45" />
      <div className="content">
        <div className="topbar">
          <IconButton label="返回" onClick={onBack}><ArrowLeft className="icon" /></IconButton>
          <span className="title-area" />
          <IconButton label="编辑"><Sparkle className="icon" /></IconButton>
        </div>
        <h1 className="detail-title">空间画像</h1>
        <p className="subtle">这是系统目前的理解，不是对人的定义。</p>

        <div className="expert-grid profile-stack">
          <ProfileCard title="反复出现的主题" items={["职业转型的不确定。", "害怕因为焦虑做选择。", "想重新理解自己的身份变化。"]} actions={["准确", "不准确", "补充"]} />
          <ProfileCard title="常见情绪" items={["迷茫，经常出现在谈长期规划时。", "焦虑，常和“怕以后后悔”一起出现。", "疲惫，通常发生在连续讨论之后。"]} actions={["准确", "删除"]} />
          <article className="profile-detail-card">
            <h3>系统不确定</h3>
            <p>当前最核心压力可能来自职业变化，也可能来自身份变化。需要更多记录确认。</p>
          </article>
        </div>
      </div>
    </section>
  );
}

function ProfileCard({ title, items, actions }: { title: string; items: string[]; actions: string[] }) {
  return (
    <article className="profile-detail-card">
      <h3>{title}</h3>
      <ul className="bullet-list">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
      <div className="pill-row">
        {actions.map((action) => <button className="pill" type="button" key={action}>{action}</button>)}
      </div>
    </article>
  );
}

function RecordingPanel({
  active,
  elapsed,
  processing,
  notice,
  onCancel,
  onFinish,
}: {
  active: boolean;
  elapsed: number;
  processing: boolean;
  notice: string;
  onCancel: () => void;
  onFinish: () => void;
}) {
  return (
    <div className={`recording-panel ${active ? "active" : ""}`} aria-live="polite">
      <div className="recording-top">
        <div>
          <h3>{processing ? "正在处理" : "正在录音"}</h3>
          <p>{processing ? "正在生成转写和摘要" : "会自动转写和生成摘要"}</p>
        </div>
        <div className="timer">{formatDuration(elapsed)}</div>
      </div>
      <div className="wave" aria-hidden="true">
        {Array.from({ length: 16 }, (_, index) => <span key={index} style={{ height: `${22 + (index % 5) * 5}px` }} />)}
      </div>
      {notice ? <div className="recording-notice">{notice}</div> : null}
      <div className="record-actions">
        <button className="secondary-action" type="button" onClick={onCancel}>取消</button>
        <button className="secondary-action stop-btn" type="button" onClick={onFinish} disabled={processing}>结束并处理</button>
      </div>
    </div>
  );
}
