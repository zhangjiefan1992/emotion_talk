from __future__ import annotations

import os
import asyncio
import base64
import json
import threading
import subprocess
import tempfile
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .deliberation import DeliberationService
from .models import (
    DeliberationArtifact,
    DeliberationEvent,
    DeliberationJob,
    HistoricalContextItem,
    RecordingTranscript,
    TranscriptSegment,
)
from .providers import LLMProvider, ProviderError, provider_from_env
from .storage import MemoryStorage, StorageBackend, storage_from_env
from .transcript import parse_markdown_transcript

DEFAULT_OWNER_ID = "default_user"
DEFAULT_SPACE_NAME = "家的倾诉空间"
MAX_SPACES_PER_OWNER = 5


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_summary(text: str, *, limit: int = 180) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "..."


class HistoricalContextRequest(BaseModel):
    source_type: str = Field(default="recording", alias="sourceType")
    source_id: str = Field(alias="sourceId")
    title: str
    created_at_text: str = Field(default="", alias="createdAtText")
    summary: str
    key_points: list[str] = Field(default_factory=list, alias="keyPoints")
    relevance: str = "selected"

    def to_context_item(self) -> HistoricalContextItem:
        return HistoricalContextItem(
            source_type=self.source_type,
            source_id=self.source_id,
            title=self.title,
            created_at_text=self.created_at_text,
            summary=self.summary,
            key_points=self.key_points,
            relevance=self.relevance,
        )


class MarkdownJobRequest(BaseModel):
    markdown: str = Field(min_length=1)
    source_type: str = Field(default="recording", alias="sourceType")
    source_id: str = Field(default="dev-recording", alias="sourceId")
    context_scope: str = Field(default="current_only", alias="contextScope")
    historical_context: list[HistoricalContextRequest] = Field(
        default_factory=list,
        alias="historicalContext",
    )


class SpaceCreateRequest(BaseModel):
    name: str = "默认倾诉空间"
    owner_id: str = Field(default=DEFAULT_OWNER_ID, alias="ownerId")


class CurrentSpaceRequest(BaseModel):
    space_id: str = Field(alias="spaceId")


class RecordingCreateRequest(BaseModel):
    space_id: str = Field(alias="spaceId")
    title: str | None = None
    started_at: str | None = Field(default=None, alias="startedAt")
    client_recording_id: str | None = Field(default=None, alias="clientRecordingId")


class TranscriptSegmentRequest(BaseModel):
    speaker: str = "发言人"
    timestamp: str = ""
    text: str = Field(min_length=1)
    start_ms: int | None = Field(default=None, alias="startMs")
    end_ms: int | None = Field(default=None, alias="endMs")


class TranscriptSubmitRequest(BaseModel):
    markdown: str | None = None
    title: str | None = None
    created_at_text: str = Field(default="", alias="createdAtText")
    duration_text: str = Field(default="", alias="durationText")
    segments: list[TranscriptSegmentRequest] = Field(default_factory=list)


class SummaryJobRequest(BaseModel):
    force: bool = False


class ExpertAdviceJobRequest(BaseModel):
    context_scope: str = Field(default="current_only", alias="contextScope")
    history_limit: int = Field(default=5, ge=0, le=20, alias="historyLimit")
    historical_context: list[HistoricalContextRequest] = Field(
        default_factory=list,
        alias="historicalContext",
    )
    include_profile: bool = Field(default=False, alias="includeProfile")


class AsrSessionRequest(BaseModel):
    space_id: str = Field(alias="spaceId")
    recording_id: str = Field(alias="recordingId")
    provider: str = "paraformer"
    model: str = "paraformer-realtime-8k-v2"


class AudioUploadAuthorizationRequest(BaseModel):
    mime_type: str = Field(default="audio/mpeg", alias="mimeType")
    byte_size: int | None = Field(default=None, alias="byteSize")
    checksum_sha256: str | None = Field(default=None, alias="checksumSha256")


class AudioTranscriptionRequest(BaseModel):
    audio_base64: str = Field(alias="audioBase64", min_length=1)
    mime_type: str = Field(default="audio/x-caf", alias="mimeType")
    title: str | None = None
    created_at_text: str = Field(default="", alias="createdAtText")
    duration_text: str = Field(default="", alias="durationText")


def _transcript_from_request(request: TranscriptSubmitRequest, *, fallback_title: str) -> RecordingTranscript:
    if request.markdown:
        return parse_markdown_transcript(request.markdown)
    if not request.segments:
        raise HTTPException(status_code=422, detail="markdown or segments is required")
    segments = [
        TranscriptSegment(
            speaker=item.speaker,
            timestamp=item.timestamp,
            text=item.text,
        )
        for item in request.segments
    ]
    return RecordingTranscript(
        title=request.title or fallback_title,
        created_at_text=request.created_at_text,
        duration_text=request.duration_text,
        segments=segments,
        full_text="\n".join(f"{item.speaker} {item.timestamp}\n{item.text}" for item in segments),
    )


def _summary_from_transcript(transcript: RecordingTranscript, provider: LLMProvider) -> dict[str, Any]:
    raw = provider.complete(_summary_prompt(transcript), purpose="summary")
    data = _parse_json_object(raw, purpose="summary")
    overview = str(data.get("overview", "")).strip()
    if not overview:
        raise HTTPException(status_code=502, detail="LLM summary missing overview")
    key_points = [str(item).strip() for item in data.get("keyPoints", []) if str(item).strip()]
    chapters = [
        {
            "title": str(item.get("title", "")).strip() or "过程",
            "startTimestamp": str(item.get("startTimestamp", "")).strip() or "00:00",
            "summary": str(item.get("summary", "")).strip(),
        }
        for item in data.get("chapters", [])
        if isinstance(item, dict) and str(item.get("summary", "")).strip()
    ]
    return {
        "status": "completed",
        "title": transcript.title,
        "overview": overview,
        "keyPoints": key_points,
        "chapters": chapters,
        "modelTrace": {
            "runtime": "llm_summary",
            "templateVersion": "emotion_talk_summary_v1",
        },
    }


def _summary_prompt(transcript: RecordingTranscript) -> str:
    return f"""请基于下面这次倾诉转写生成 AI 纪要。

要求：
- 只依据转写内容，不要套用样例，不要脑补人生建议。
- 结构是“总-过程-总”：overview 是第一个总，chapters 是过程，keyPoints 是最后收束。
- 输出 JSON，不要 Markdown。
- JSON schema:
{{
  "title": "简短标题",
  "overview": "100字以内总览",
  "keyPoints": ["最后收束要点1", "最后收束要点2"],
  "chapters": [
    {{"title": "阶段标题", "startTimestamp": "00:00", "summary": "阶段摘要"}}
  ]
}}

转写：
{transcript.full_text}
"""


def _parse_json_object(text: str, *, purpose: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.strip("`")
        clean = clean.removeprefix("json").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise HTTPException(status_code=502, detail=f"LLM {purpose} did not return JSON")
    try:
        data = json.loads(clean[start : end + 1])
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM {purpose} returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail=f"LLM {purpose} JSON must be an object")
    return data


def create_app(
    *,
    provider: LLMProvider | None = None,
    storage: StorageBackend | None = None,
) -> FastAPI:
    app = FastAPI(title="Emotion Talk API", version="0.2.0")
    store = storage or MemoryStorage()
    spaces: dict[str, dict[str, Any]] = store.load_spaces()
    recordings: dict[str, dict[str, Any]] = store.load_recordings()
    jobs: dict[str, Any] = store.load_jobs()
    jobs_lock = threading.Lock()

    @app.exception_handler(ProviderError)
    async def provider_error_handler(_request, exc: ProviderError) -> JSONResponse:
        message = str(exc)
        status = 503 if "required" in message or "disabled" in message else 502
        return JSONResponse(status_code=status, content={"detail": message})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/asr/realtime")
    async def realtime_asr(websocket: WebSocket) -> None:
        await websocket.accept()
        await _run_realtime_asr(websocket)

    @app.get("/dev-fixtures/career-transition-transcript", response_class=PlainTextResponse)
    def career_transition_transcript_fixture() -> PlainTextResponse:
        path = Path.home() / "Downloads" / "06-13 职业转型与长期规划(1).md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="fixture transcript not found")
        return PlainTextResponse(path.read_text(encoding="utf-8"))

    @app.post("/deliberation-jobs/from-markdown")
    def create_deliberation_job(request: MarkdownJobRequest) -> dict:
        selected_provider = _selected_provider(provider)
        transcript = parse_markdown_transcript(request.markdown)
        job = DeliberationService(provider=selected_provider).run_from_transcript(
            transcript,
            source_type=request.source_type,
            source_id=request.source_id,
            context_scope=request.context_scope,
            historical_context=[item.to_context_item() for item in request.historical_context],
        )
        jobs[job.job_id] = job
        store.save_job(job)
        return job.to_dict()

    @app.post("/spaces")
    def create_space(request: SpaceCreateRequest) -> dict[str, Any]:
        owner_id = _clean_owner_id(request.owner_id)
        name = _clean_space_name(request.name)
        _assert_can_create_space(spaces, owner_id=owner_id, name=name)
        space_id = _new_id("space")
        is_current = not _owner_spaces(spaces, owner_id)
        record = {
            "spaceId": space_id,
            "ownerId": owner_id,
            "name": name,
            "isCurrent": is_current,
            "createdAt": _now_iso(),
        }
        spaces[space_id] = record
        store.save_space(record)
        return record

    @app.get("/users/{owner_id}/spaces")
    def list_user_spaces(owner_id: str) -> dict[str, Any]:
        owner_id = _clean_owner_id(owner_id)
        current = _ensure_default_space(spaces, owner_id=owner_id, store=store)
        visible_spaces = _visible_owner_spaces(spaces, owner_id)
        return {
            "ownerId": owner_id,
            "currentSpaceId": current["spaceId"],
            "spaces": [_space_public(space, owner_id=owner_id) for space in visible_spaces],
        }

    @app.post("/users/{owner_id}/current-space")
    def set_current_space(owner_id: str, request: CurrentSpaceRequest) -> dict[str, Any]:
        owner_id = _clean_owner_id(owner_id)
        target = spaces.get(request.space_id)
        if not target or _space_owner(target) != owner_id:
            raise HTTPException(status_code=404, detail="space not found")
        for space in _owner_spaces(spaces, owner_id):
            space["isCurrent"] = space["spaceId"] == request.space_id
            store.save_space(space)
        return {
            "ownerId": owner_id,
            "currentSpaceId": request.space_id,
            "spaces": [_space_public(space, owner_id=owner_id) for space in _visible_owner_spaces(spaces, owner_id)],
        }

    @app.get("/spaces/{space_id}")
    def get_space(space_id: str) -> dict[str, Any]:
        if space_id not in spaces:
            raise HTTPException(status_code=404, detail="space not found")
        return spaces[space_id]

    @app.post("/recordings")
    def create_recording(request: RecordingCreateRequest) -> dict[str, Any]:
        if request.space_id not in spaces:
            raise HTTPException(status_code=404, detail="space not found")
        recording_id = _new_id("rec")
        record = {
            "recordingId": recording_id,
            "spaceId": request.space_id,
            "clientRecordingId": request.client_recording_id,
            "title": request.title or "未命名对话",
            "status": "recording",
            "startedAt": request.started_at or _now_iso(),
            "createdAt": _now_iso(),
            "transcript": None,
            "summaryArtifact": None,
            "expertAdviceJobIds": [],
            "audioObject": None,
        }
        recordings[recording_id] = record
        store.save_recording(record)
        return _recording_response(record)

    @app.get("/recordings/{recording_id}")
    def get_recording(recording_id: str) -> dict[str, Any]:
        return _recording_response(_require_recording(recordings, recording_id))

    @app.get("/spaces/{space_id}/recordings")
    def list_space_recordings(space_id: str) -> list[dict[str, Any]]:
        if space_id not in spaces:
            raise HTTPException(status_code=404, detail="space not found")
        items = [record for record in recordings.values() if record["spaceId"] == space_id]
        items.sort(key=lambda item: str(item.get("createdAt", "")), reverse=True)
        return [_recording_response(record) for record in items]

    @app.post("/recordings/{recording_id}/transcript")
    def submit_transcript(recording_id: str, request: TranscriptSubmitRequest) -> dict[str, Any]:
        record = _require_recording(recordings, recording_id)
        transcript = _transcript_from_request(request, fallback_title=record["title"])
        record["title"] = transcript.title or record["title"]
        record["transcript"] = transcript
        record["status"] = "transcribed"
        store.save_recording(record)
        return _recording_response(record)

    @app.post("/recordings/{recording_id}/audio-upload-authorizations")
    def create_audio_upload_authorization(
        recording_id: str,
        request: AudioUploadAuthorizationRequest,
    ) -> dict[str, Any]:
        record = _require_recording(recordings, recording_id)
        object_key = f"spaces/{record['spaceId']}/recordings/{recording_id}/audio/source.{_audio_extension(request.mime_type)}"
        authorization = {
            "uploadId": _new_id("upload"),
            "recordingId": recording_id,
            "objectKey": object_key,
            "mimeType": request.mime_type,
            "byteSize": request.byte_size,
            "checksumSha256": request.checksum_sha256,
            "method": "PUT",
            "uploadUrl": None,
            "status": "dev_stub",
            "note": "OSS presigned upload URL will be generated here in production.",
        }
        record["audioObject"] = {
            "objectKey": object_key,
            "mimeType": request.mime_type,
            "byteSize": request.byte_size,
            "checksumSha256": request.checksum_sha256,
        }
        store.save_recording(record)
        return authorization

    @app.post("/recordings/{recording_id}/audio-transcriptions")
    def transcribe_recording_audio(recording_id: str, request: AudioTranscriptionRequest) -> dict[str, Any]:
        record = _require_recording(recordings, recording_id)
        try:
            audio_bytes = base64.b64decode(request.audio_base64, validate=True)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="audioBase64 is invalid") from exc
        segments = _transcribe_audio_with_dashscope(audio_bytes, mime_type=request.mime_type)
        transcript = RecordingTranscript(
            title=request.title or record["title"],
            created_at_text=request.created_at_text,
            duration_text=request.duration_text,
            segments=segments,
            full_text="\n".join(f"{item.speaker} {item.timestamp}\n{item.text}" for item in segments),
        )
        record["title"] = transcript.title or record["title"]
        record["transcript"] = transcript
        record["status"] = "transcribed"
        record["audioObject"] = {
            "objectKey": f"spaces/{record['spaceId']}/recordings/{recording_id}/audio/source.{_audio_extension(request.mime_type)}",
            "mimeType": request.mime_type,
            "byteSize": len(audio_bytes),
            "checksumSha256": None,
        }
        store.save_recording(record)
        return _recording_response(record)

    @app.post("/asr-sessions")
    def create_asr_session(request: AsrSessionRequest) -> dict[str, Any]:
        if request.space_id not in spaces:
            raise HTTPException(status_code=404, detail="space not found")
        _require_recording(recordings, request.recording_id)
        return {
            "asrSessionId": _new_id("asr"),
            "spaceId": request.space_id,
            "recordingId": request.recording_id,
            "provider": request.provider,
            "model": request.model,
            "credentialMode": "temporary_api_key",
            "expiresAt": None,
            "sdkConfig": {
                "provider": request.provider,
                "model": request.model,
                "temporaryApiKey": None,
            },
            "status": "dev_stub",
            "note": "Backend will mint Bailian/DashScope temporary credentials here.",
        }

    @app.post("/recordings/{recording_id}/summary-jobs")
    def create_summary_job(recording_id: str, request: SummaryJobRequest) -> dict[str, Any]:
        record = _require_recording(recordings, recording_id)
        transcript = _require_transcript(record)
        if record["summaryArtifact"] and not request.force:
            return record["summaryArtifact"]
        summary = _summary_from_transcript(transcript, _selected_provider(provider))
        summary["summaryJobId"] = _new_id("summary")
        summary["recordingId"] = recording_id
        record["summaryArtifact"] = summary
        record["status"] = "summarized"
        store.save_recording(record)
        return summary

    @app.post("/recordings/{recording_id}/expert-advice-jobs")
    def create_recording_expert_advice_job(
        recording_id: str,
        request: ExpertAdviceJobRequest,
    ) -> dict[str, Any]:
        record = _require_recording(recordings, recording_id)
        transcript = _require_transcript(record)
        selected_provider = _selected_provider(provider)
        history = _select_history_context(
            recordings,
            current_recording=record,
            context_scope=request.context_scope,
            limit=request.history_limit,
        )
        history.extend(item.to_context_item() for item in request.historical_context)
        profile_context = _space_profile_stub(spaces[record["spaceId"]]) if request.include_profile else {}
        service = DeliberationService(provider=selected_provider)
        job_id = _new_id("job")
        running_job = DeliberationJob(
            job_id=job_id,
            source_type="recording",
            source_id=recording_id,
            template=service.template,
            status="running",
            input_snapshot=service._build_input_snapshot(
                transcript,
                context_scope=request.context_scope,
                historical_context=history,
                profile_context=profile_context,
            ),
            events=[],
            artifact=_empty_deliberation_artifact(),
            context_usage=service._build_context_usage(
                context_scope=request.context_scope,
                historical_context=history,
                profile_context=profile_context,
            ),
        )
        with jobs_lock:
            jobs[job_id] = running_job
            store.save_job(running_job)
        record["expertAdviceJobIds"].append(job_id)
        store.save_recording(record)
        threading.Thread(
            target=_run_expert_advice_job,
            args=(
                job_id,
                service,
                transcript,
                recording_id,
                request.context_scope,
                history,
                profile_context,
                jobs,
                jobs_lock,
                store,
            ),
            daemon=True,
        ).start()
        return running_job.to_dict()

    @app.get("/expert-advice-jobs/{job_id}")
    def get_expert_advice_job(job_id: str) -> dict[str, Any]:
        return _require_job(jobs, job_id).to_dict()

    @app.get("/expert-advice-jobs/{job_id}/events")
    def get_expert_advice_job_events(job_id: str) -> list[dict[str, Any]]:
        return [event.to_dict() for event in _require_job(jobs, job_id).events]

    @app.get("/expert-advice-jobs/{job_id}/artifact")
    def get_expert_advice_job_artifact(job_id: str) -> dict[str, Any]:
        return _require_job(jobs, job_id).artifact.to_dict()

    return app


def _selected_provider(provider: LLMProvider | None) -> LLMProvider:
    return provider or provider_from_env(os.getenv("EMOTION_TALK_LLM_PROVIDER", "deepseek"))


def _empty_deliberation_artifact() -> DeliberationArtifact:
    return DeliberationArtifact(
        overview="",
        process_summary=[],
        suggestions=[],
        key_uncertainties=[],
        safety_boundary="",
    )


def _run_expert_advice_job(
    job_id: str,
    service: DeliberationService,
    transcript: RecordingTranscript,
    recording_id: str,
    context_scope: str,
    history: list[HistoricalContextItem],
    profile_context: dict[str, Any],
    jobs: dict[str, DeliberationJob],
    jobs_lock: threading.Lock,
    store: StorageBackend,
) -> None:
    def save_event(event: DeliberationEvent) -> None:
        with jobs_lock:
            job = jobs[job_id]
            job.events.append(event)
            store.save_job(job)

    try:
        final_job = service.run_from_transcript(
            transcript,
            source_type="recording",
            source_id=recording_id,
            context_scope=context_scope,
            historical_context=history,
            profile_context=profile_context,
            job_id=job_id,
            on_event=save_event,
        )
        with jobs_lock:
            jobs[job_id] = final_job
            store.save_job(final_job)
    except Exception as exc:
        with jobs_lock:
            job = jobs[job_id]
            job.status = "failed"
            seq = (job.events[-1].seq if job.events else 0) + 1
            job.events.append(
                DeliberationEvent(
                    event_id=f"evt_{seq:04d}",
                    job_id=job_id,
                    seq=seq,
                    type="job_failed",
                    visibility="user_visible",
                    payload={"message": str(exc)},
                )
            )
            store.save_job(job)


def _clean_owner_id(owner_id: str) -> str:
    return owner_id.strip() or DEFAULT_OWNER_ID


def _clean_space_name(name: str) -> str:
    clean = " ".join(name.split())
    if not clean:
        raise HTTPException(status_code=422, detail="space name is required")
    return clean


def _space_owner(space: dict[str, Any]) -> str:
    return str(space.get("ownerId") or DEFAULT_OWNER_ID)


def _owner_spaces(spaces: dict[str, dict[str, Any]], owner_id: str) -> list[dict[str, Any]]:
    return [space for space in spaces.values() if _space_owner(space) == owner_id]


def _sorted_owner_spaces(spaces: dict[str, dict[str, Any]], owner_id: str) -> list[dict[str, Any]]:
    items = _owner_spaces(spaces, owner_id)
    items.sort(key=lambda item: str(item.get("createdAt", "")))
    return items


def _visible_owner_spaces(spaces: dict[str, dict[str, Any]], owner_id: str) -> list[dict[str, Any]]:
    """Return the product-visible space set, hiding legacy duplicated rows."""
    current = next((space for space in _owner_spaces(spaces, owner_id) if space.get("isCurrent")), None)
    candidates = _sorted_owner_spaces(spaces, owner_id)
    if current:
        candidates = [current, *[space for space in candidates if space["spaceId"] != current["spaceId"]]]

    visible: list[dict[str, Any]] = []
    names: set[str] = set()
    for space in candidates:
        normalized = str(space.get("name", "")).casefold()
        if normalized in names:
            continue
        visible.append(space)
        names.add(normalized)
        if len(visible) >= MAX_SPACES_PER_OWNER:
            break
    return visible


def _space_public(space: dict[str, Any], *, owner_id: str | None = None) -> dict[str, Any]:
    return {
        "spaceId": space["spaceId"],
        "ownerId": owner_id or _space_owner(space),
        "name": space.get("name", DEFAULT_SPACE_NAME),
        "isCurrent": bool(space.get("isCurrent")),
        "createdAt": space.get("createdAt", ""),
    }


def _assert_can_create_space(spaces: dict[str, dict[str, Any]], *, owner_id: str, name: str) -> None:
    owner_spaces = _owner_spaces(spaces, owner_id)
    if len(_visible_owner_spaces(spaces, owner_id)) >= MAX_SPACES_PER_OWNER:
        raise HTTPException(status_code=409, detail="a user can have at most 5 spaces")
    normalized = name.casefold()
    if any(str(space.get("name", "")).casefold() == normalized for space in owner_spaces):
        raise HTTPException(status_code=409, detail="space name already exists")


def _ensure_default_space(
    spaces: dict[str, dict[str, Any]],
    *,
    owner_id: str,
    store: StorageBackend,
) -> dict[str, Any]:
    owner_spaces = _owner_spaces(spaces, owner_id)
    current = next((space for space in owner_spaces if space.get("isCurrent")), None)
    if current:
        return current
    if owner_spaces:
        owner_spaces[0]["isCurrent"] = True
        owner_spaces[0]["ownerId"] = owner_id
        store.save_space(owner_spaces[0])
        return owner_spaces[0]
    space = {
        "spaceId": _new_id("space"),
        "ownerId": owner_id,
        "name": DEFAULT_SPACE_NAME,
        "isCurrent": True,
        "createdAt": _now_iso(),
    }
    spaces[space["spaceId"]] = space
    store.save_space(space)
    return space


def _require_recording(recordings: dict[str, dict[str, Any]], recording_id: str) -> dict[str, Any]:
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="recording not found")
    return recordings[recording_id]


def _require_job(jobs: dict[str, Any], job_id: str) -> Any:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="expert advice job not found")
    return jobs[job_id]


def _require_transcript(recording: dict[str, Any]) -> RecordingTranscript:
    transcript = recording.get("transcript")
    if transcript is None:
        raise HTTPException(status_code=409, detail="recording transcript is required")
    return transcript


async def _run_realtime_asr(websocket: WebSocket) -> None:
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
    if not api_key:
        await websocket.send_json({"type": "error", "message": "DASHSCOPE_API_KEY or BAILIAN_API_KEY is required"})
        await websocket.close()
        return
    from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

    loop = asyncio.get_running_loop()
    events: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    model = websocket.query_params.get("model") or os.getenv("ASR_REALTIME_MODEL", "paraformer-realtime-v2")
    sample_rate = _realtime_sample_rate(websocket.query_params.get("sample_rate"), model=model)

    class Callback(RecognitionCallback):
        def on_open(self) -> None:
            loop.call_soon_threadsafe(
                events.put_nowait,
                {"type": "ready", "model": model, "sampleRate": sample_rate},
            )

        def on_event(self, result: RecognitionResult) -> None:
            sentence = result.get_sentence()
            for item in sentence if isinstance(sentence, list) else [sentence]:
                if not item:
                    continue
                loop.call_soon_threadsafe(
                    events.put_nowait,
                    {
                        "type": "transcript",
                        "text": str(item.get("text", "")).strip(),
                        "isFinal": RecognitionResult.is_sentence_end(item),
                        "startMs": item.get("begin_time"),
                        "endMs": item.get("end_time"),
                    },
                )

        def on_error(self, result: RecognitionResult) -> None:
            loop.call_soon_threadsafe(
                events.put_nowait,
                {
                    "type": "error",
                    "message": str(getattr(result, "message", None) or getattr(result, "code", None) or "Realtime ASR failed"),
                },
            )

        def on_complete(self) -> None:
            loop.call_soon_threadsafe(events.put_nowait, {"type": "complete"})

        def on_close(self) -> None:
            loop.call_soon_threadsafe(events.put_nowait, None)

    recognition = Recognition(
        model=model,
        callback=Callback(),
        format="pcm",
        sample_rate=sample_rate,
        api_key=api_key,
    )

    async def send_events() -> None:
        while True:
            event = await events.get()
            if event is None:
                return
            await websocket.send_json(event)

    sender = asyncio.create_task(send_events())
    try:
        try:
            recognition.start()
        except Exception as exc:
            await websocket.send_json({"type": "error", "message": f"Realtime ASR start failed: {exc}"})
            await websocket.close()
            return
        while True:
            recognition.send_audio_frame(await websocket.receive_bytes())
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await events.put({"type": "error", "message": f"Realtime ASR stream failed: {exc}"})
    finally:
        if getattr(recognition, "_running", False):
            try:
                await asyncio.to_thread(recognition.stop)
            except Exception:
                pass
        sender.cancel()


def _realtime_sample_rate(raw_value: str | None, *, model: str) -> int:
    if raw_value:
        try:
            sample_rate = int(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="sample_rate must be an integer") from exc
        if sample_rate not in {8000, 16000}:
            raise HTTPException(status_code=422, detail="sample_rate must be 8000 or 16000")
        return sample_rate
    configured = os.getenv("ASR_REALTIME_SAMPLE_RATE")
    if configured:
        return _realtime_sample_rate(configured, model=model)
    return 8000 if "8k" in model.lower() else 16000


def _transcribe_audio_with_dashscope(audio_bytes: bytes, *, mime_type: str) -> list[TranscriptSegment]:
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DASHSCOPE_API_KEY or BAILIAN_API_KEY is required")
    wav_bytes = _to_wav_bytes(audio_bytes, mime_type=mime_type)
    # ponytail: data URI is local MVP; use OSS file_url before 45-minute production audio.
    data_uri = "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode()
    body = json.dumps(
        {
            "model": os.getenv("ASR_BATCH_MODEL", "paraformer-v2"),
            "input": {"file_urls": [data_uri]},
            "parameters": {"language_hints": ["zh"]},
        }
    ).encode()
    created = _dashscope_json(
        "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription",
        api_key=api_key,
        data=body,
        headers={"Content-Type": "application/json", "X-DashScope-Async": "enable"},
    )
    task_id = created.get("output", {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=502, detail="DashScope ASR did not return task_id")
    deadline = time.monotonic() + int(os.getenv("ASR_POLL_TIMEOUT_SECONDS", "90"))
    while time.monotonic() < deadline:
        time.sleep(1)
        status = _dashscope_json(f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}", api_key=api_key)
        task_status = status.get("output", {}).get("task_status")
        if task_status == "SUCCEEDED":
            result_url = status.get("output", {}).get("results", [{}])[0].get("transcription_url")
            if not result_url:
                raise HTTPException(status_code=502, detail="DashScope ASR result URL is missing")
            return _segments_from_dashscope_result(_public_json(result_url))
        if task_status == "FAILED":
            message = status.get("output", {}).get("message", "DashScope ASR failed")
            raise HTTPException(status_code=502, detail=message)
    raise HTTPException(status_code=504, detail="DashScope ASR timed out")


def _to_wav_bytes(audio_bytes: bytes, *, mime_type: str) -> bytes:
    ext = _audio_extension(mime_type)
    if ext == "wav":
        return audio_bytes
    with tempfile.TemporaryDirectory() as tmp_dir:
        source = Path(tmp_dir) / f"source.{ext}"
        target = Path(tmp_dir) / "source.wav"
        source.write_bytes(audio_bytes)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-ar", "16000", "-ac", "1", str(target)],
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise HTTPException(status_code=500, detail="ffmpeg is required to normalize uploaded audio") from exc
        return target.read_bytes()


def _dashscope_json(
    url: str,
    *,
    api_key: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", **(headers or {})},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DashScope request failed: {exc}") from exc


def _public_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DashScope result fetch failed: {exc}") from exc


def _segments_from_dashscope_result(result: dict[str, Any]) -> list[TranscriptSegment]:
    transcript = (result.get("transcripts") or [{}])[0]
    sentences = transcript.get("sentences") or []
    segments = [
        TranscriptSegment(speaker="我", timestamp=_timestamp_from_ms(item.get("begin_time", 0)), text=str(item.get("text", "")).strip())
        for item in sentences
        if str(item.get("text", "")).strip()
    ]
    if segments:
        return segments
    text = str(transcript.get("text", "")).strip()
    if text:
        return [TranscriptSegment(speaker="我", timestamp="00:00", text=text)]
    raise HTTPException(status_code=422, detail="DashScope ASR returned empty transcript")


def _timestamp_from_ms(value: Any) -> str:
    seconds = max(0, int(value or 0) // 1000)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _audio_extension(mime_type: str) -> str:
    return {
        "audio/mpeg": "mp3",
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
        "audio/x-m4a": "m4a",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/x-caf": "caf",
        "audio/caf": "caf",
    }.get(mime_type.lower(), "caf")


def _recording_response(recording: dict[str, Any]) -> dict[str, Any]:
    transcript = recording.get("transcript")
    return {
        "recordingId": recording["recordingId"],
        "spaceId": recording["spaceId"],
        "clientRecordingId": recording.get("clientRecordingId"),
        "title": recording["title"],
        "status": recording["status"],
        "startedAt": recording["startedAt"],
        "createdAt": recording["createdAt"],
        "transcript": {
            "title": transcript.title,
            "createdAtText": transcript.created_at_text,
            "durationText": transcript.duration_text,
            "segmentCount": len(transcript.segments),
            "segments": [
                {
                    "speaker": segment.speaker,
                    "timestamp": segment.timestamp,
                    "text": segment.text,
                }
                for segment in transcript.segments
            ],
        }
        if transcript
        else None,
        "summaryArtifact": recording.get("summaryArtifact"),
        "audioObject": recording.get("audioObject"),
        "expertAdviceJobIds": recording.get("expertAdviceJobIds", []),
    }


def _select_history_context(
    recordings: dict[str, dict[str, Any]],
    *,
    current_recording: dict[str, Any],
    context_scope: str,
    limit: int,
) -> list[HistoricalContextItem]:
    if context_scope == "current_only" or limit <= 0:
        return []
    if context_scope != "current_with_history":
        raise HTTPException(status_code=422, detail="unsupported contextScope")

    selected: list[HistoricalContextItem] = []
    for record in recordings.values():
        if record["recordingId"] == current_recording["recordingId"]:
            continue
        if record["spaceId"] != current_recording["spaceId"]:
            continue
        summary = record.get("summaryArtifact")
        transcript = record.get("transcript")
        if not summary and not transcript:
            continue
        selected.append(
            HistoricalContextItem(
                source_type="recording",
                source_id=record["recordingId"],
                title=record["title"],
                created_at_text=(transcript.created_at_text if transcript else record["createdAt"]),
                summary=summary["overview"] if summary else _compact_summary(transcript.full_text),
                key_points=list(summary.get("keyPoints", [])) if summary else [],
                relevance="same_space_recent",
            )
        )
    return selected[-limit:]


def _space_profile_stub(space: dict[str, Any]) -> dict[str, Any]:
    return {
        "spaceId": space["spaceId"],
        "spaceName": space["name"],
        "profileStatus": "not_enough_data",
    }


app = create_app(storage=storage_from_env())
