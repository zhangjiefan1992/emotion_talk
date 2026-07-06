from __future__ import annotations

import re

from .models import RecordingTranscript, TranscriptSegment


_SPEAKER_LINE = re.compile(r"^(.+?)\s+(\d{2}:\d{2}(?::\d{2})?)$")


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\u00a0", " ")).strip()


def parse_markdown_transcript(markdown: str) -> RecordingTranscript:
    """Parse DingTalk-style markdown transcript export."""
    lines = [_clean(line) for line in markdown.splitlines()]
    title = ""
    created_at_text = ""
    duration_text = ""
    in_transcript = False
    segments: list[TranscriptSegment] = []
    current_speaker: str | None = None
    current_timestamp: str | None = None
    current_text: list[str] = []

    def flush_segment() -> None:
        nonlocal current_speaker, current_timestamp, current_text
        if current_speaker and current_timestamp and current_text:
            text = "\n".join(part for part in current_text if part).strip()
            if text:
                segments.append(
                    TranscriptSegment(
                        speaker=current_speaker,
                        timestamp=current_timestamp,
                        text=text,
                    )
                )
        current_speaker = None
        current_timestamp = None
        current_text = []

    for line in lines:
        if not line:
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("> 创建时间:"):
            created_at_text = line.split(":", 1)[1].strip()
            continue
        if line.startswith("> 转写时长:"):
            duration_text = line.split(":", 1)[1].strip()
            continue
        if line == "## 转文字":
            in_transcript = True
            continue
        if not in_transcript:
            continue

        speaker_match = _SPEAKER_LINE.match(line)
        if speaker_match:
            flush_segment()
            current_speaker = speaker_match.group(1).strip()
            current_timestamp = speaker_match.group(2).strip()
            continue
        if line.startswith("#"):
            continue
        current_text.append(line)

    flush_segment()
    full_text = "\n\n".join(
        f"{segment.speaker} {segment.timestamp}\n{segment.text}"
        for segment in segments
    )
    return RecordingTranscript(
        title=title,
        created_at_text=created_at_text,
        duration_text=duration_text,
        segments=segments,
        full_text=full_text,
    )
