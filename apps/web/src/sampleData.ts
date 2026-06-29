import type { ConversationRecord, TranscriptSegment } from "./types";

export const liveTranscriptSeed: TranscriptSegment[] = [
  {
    speaker: "发言人 1",
    timestamp: "00:00",
    text: "我最近一直在想，当前这个状态到底是不是我真正想要的生活。",
    startMs: 0,
    endMs: 7200,
  },
  {
    speaker: "发言人 2",
    timestamp: "00:18",
    text: "你先不用急着给自己下结论，我们可以把困惑拆开看。",
    startMs: 18000,
    endMs: 26800,
  },
  {
    speaker: "发言人 1",
    timestamp: "00:42",
    text: "我最难受的点是，别人都在往前走，我却不知道下一步该选什么。",
    startMs: 42000,
    endMs: 53400,
  },
  {
    speaker: "发言人 2",
    timestamp: "01:10",
    text: "也许今天不需要马上解决人生，只需要找到一个能开始验证的小动作。",
    startMs: 70000,
    endMs: 83600,
  },
  {
    speaker: "发言人 1",
    timestamp: "01:36",
    text: "如果只是一个小动作，我觉得我可以接受。至少不是继续停在原地。",
    startMs: 96000,
    endMs: 110000,
  },
];

export const recentRecords: ConversationRecord[] = [
  {
    localId: "seed-1",
    title: "06-15 晚间倾诉",
    createdAt: "戒凡",
    durationText: "35:47",
    status: "completed",
    segments: liveTranscriptSeed.slice(0, 3),
  },
  {
    localId: "seed-2",
    title: "06-13 职业转型和长期规划",
    createdAt: "满月",
    durationText: "37:23",
    status: "completed",
    segments: liveTranscriptSeed.slice(1, 4),
  },
  {
    localId: "seed-3",
    title: "06-12 迷茫和身份变化",
    createdAt: "满月",
    durationText: "28:16",
    status: "completed",
    segments: liveTranscriptSeed.slice(2),
  },
  {
    localId: "seed-4",
    title: "06-10 关于要不要马上行动",
    createdAt: "戒凡",
    durationText: "22:05",
    status: "completed",
    segments: liveTranscriptSeed.slice(0, 4),
  },
];

export function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}
