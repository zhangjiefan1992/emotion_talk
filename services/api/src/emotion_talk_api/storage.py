from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol

from .models import (
    DeliberationJob,
    RecordingTranscript,
    TranscriptSegment,
    deliberation_job_from_dict,
)


class StorageBackend(Protocol):
    def load_spaces(self) -> dict[str, dict[str, Any]]:
        ...

    def load_recordings(self) -> dict[str, dict[str, Any]]:
        ...

    def load_jobs(self) -> dict[str, DeliberationJob]:
        ...

    def save_space(self, space: dict[str, Any]) -> None:
        ...

    def save_recording(self, recording: dict[str, Any]) -> None:
        ...

    def save_job(self, job: DeliberationJob) -> None:
        ...


class MemoryStorage:
    def load_spaces(self) -> dict[str, dict[str, Any]]:
        return {}

    def load_recordings(self) -> dict[str, dict[str, Any]]:
        return {}

    def load_jobs(self) -> dict[str, DeliberationJob]:
        return {}

    def save_space(self, space: dict[str, Any]) -> None:
        return None

    def save_recording(self, recording: dict[str, Any]) -> None:
        return None

    def save_job(self, job: DeliberationJob) -> None:
        return None


class SQLiteStorage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def load_spaces(self) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("select id, data from spaces").fetchall()
        return {row["id"]: json.loads(row["data"]) for row in rows}

    def load_recordings(self) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("select id, data from recordings").fetchall()
        return {row["id"]: _deserialize_recording(json.loads(row["data"])) for row in rows}

    def load_jobs(self) -> dict[str, DeliberationJob]:
        with self._connect() as conn:
            rows = conn.execute("select id, data from jobs").fetchall()
        return {row["id"]: deliberation_job_from_dict(json.loads(row["data"])) for row in rows}

    def save_space(self, space: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into spaces(id, data) values(?, ?) on conflict(id) do update set data=excluded.data",
                (space["spaceId"], _json_dumps(space)),
            )

    def save_recording(self, recording: dict[str, Any]) -> None:
        data = _serialize_recording(recording)
        with self._connect() as conn:
            conn.execute(
                """
                insert into recordings(id, space_id, data) values(?, ?, ?)
                on conflict(id) do update set space_id=excluded.space_id, data=excluded.data
                """,
                (recording["recordingId"], recording["spaceId"], _json_dumps(data)),
            )

    def save_job(self, job: DeliberationJob) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into jobs(id, data) values(?, ?) on conflict(id) do update set data=excluded.data",
                (job.job_id, _json_dumps(job.to_dict())),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists spaces (
                    id text primary key,
                    data text not null
                );

                create table if not exists recordings (
                    id text primary key,
                    space_id text not null,
                    data text not null
                );

                create index if not exists idx_recordings_space_id on recordings(space_id);

                create table if not exists jobs (
                    id text primary key,
                    data text not null
                );
                """
            )


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _serialize_recording(recording: dict[str, Any]) -> dict[str, Any]:
    data = dict(recording)
    transcript = data.get("transcript")
    if isinstance(transcript, RecordingTranscript):
        data["transcript"] = {
            "title": transcript.title,
            "createdAtText": transcript.created_at_text,
            "durationText": transcript.duration_text,
            "segments": [asdict(segment) for segment in transcript.segments],
            "fullText": transcript.full_text,
        }
    return data


def _deserialize_recording(data: dict[str, Any]) -> dict[str, Any]:
    transcript = data.get("transcript")
    if isinstance(transcript, dict):
        data["transcript"] = RecordingTranscript(
            title=str(transcript.get("title", "")),
            created_at_text=str(transcript.get("createdAtText", "")),
            duration_text=str(transcript.get("durationText", "")),
            segments=[
                TranscriptSegment(
                    speaker=str(item.get("speaker", "发言人")),
                    timestamp=str(item.get("timestamp", "")),
                    text=str(item.get("text", "")),
                )
                for item in transcript.get("segments", [])
            ],
            full_text=str(transcript.get("fullText", "")),
        )
    return data


def storage_from_env() -> StorageBackend:
    path = Path(os.environ.get("EMOTION_TALK_DB_PATH", ".data/emotion_talk.sqlite3"))
    return SQLiteStorage(path)
