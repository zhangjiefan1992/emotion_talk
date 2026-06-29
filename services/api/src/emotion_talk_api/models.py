from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TranscriptSegment:
    speaker: str
    timestamp: str
    text: str


@dataclass(frozen=True)
class RecordingTranscript:
    title: str
    created_at_text: str
    duration_text: str
    segments: list[TranscriptSegment]
    full_text: str


@dataclass(frozen=True)
class HistoricalContextItem:
    source_type: str
    source_id: str
    title: str
    summary: str
    created_at_text: str = ""
    key_points: list[str] = field(default_factory=list)
    relevance: str = "selected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceType": self.source_type,
            "sourceId": self.source_id,
            "title": self.title,
            "createdAtText": self.created_at_text,
            "summary": self.summary,
            "keyPoints": self.key_points,
            "relevance": self.relevance,
        }


def historical_context_item_from_dict(data: dict[str, Any]) -> HistoricalContextItem:
    return HistoricalContextItem(
        source_type=str(data.get("sourceType", data.get("source_type", "recording"))),
        source_id=str(data.get("sourceId", data.get("source_id", ""))),
        title=str(data.get("title", "")),
        created_at_text=str(data.get("createdAtText", data.get("created_at_text", ""))),
        summary=str(data.get("summary", "")),
        key_points=[str(item) for item in data.get("keyPoints", data.get("key_points", []))],
        relevance=str(data.get("relevance", "selected")),
    )


@dataclass(frozen=True)
class ProcessSummary:
    round: int
    title: str
    summary: str


@dataclass(frozen=True)
class Suggestion:
    title: str
    body: str
    confidence: str = "medium"
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DeliberationArtifact:
    overview: str
    process_summary: list[ProcessSummary]
    suggestions: list[Suggestion]
    key_uncertainties: list[str]
    safety_boundary: str
    model_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["processSummary"] = data.pop("process_summary")
        data["keyUncertainties"] = data.pop("key_uncertainties")
        data["safetyBoundary"] = data.pop("safety_boundary")
        data["modelTrace"] = data.pop("model_trace")
        return data


@dataclass(frozen=True)
class DeliberationEvent:
    event_id: str
    job_id: str
    seq: int
    type: str
    visibility: str
    payload: dict[str, Any]
    participant: str | None = None
    round: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["eventId"] = data.pop("event_id")
        data["jobId"] = data.pop("job_id")
        return data


@dataclass(frozen=True)
class DeliberationJob:
    job_id: str
    source_type: str
    source_id: str
    template: str
    status: str
    input_snapshot: dict[str, Any]
    events: list[DeliberationEvent]
    artifact: DeliberationArtifact
    context_usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "sourceType": self.source_type,
            "sourceId": self.source_id,
            "template": self.template,
            "status": self.status,
            "inputSnapshot": self.input_snapshot,
            "events": [event.to_dict() for event in self.events],
            "artifact": self.artifact.to_dict(),
            "contextUsage": self.context_usage,
        }


def deliberation_job_from_dict(data: dict[str, Any]) -> DeliberationJob:
    artifact_data = data["artifact"]
    artifact = DeliberationArtifact(
        overview=artifact_data.get("overview", ""),
        process_summary=[
            ProcessSummary(
                round=item.get("round", index + 1),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
            )
            for index, item in enumerate(artifact_data.get("processSummary", []))
        ],
        suggestions=[
            Suggestion(
                title=item.get("title", ""),
                body=item.get("body", ""),
                confidence=item.get("confidence", "medium"),
                evidence=list(item.get("evidence", [])),
            )
            for item in artifact_data.get("suggestions", [])
        ],
        key_uncertainties=list(artifact_data.get("keyUncertainties", [])),
        safety_boundary=artifact_data.get("safetyBoundary", ""),
        model_trace=dict(artifact_data.get("modelTrace", {})),
    )
    return DeliberationJob(
        job_id=data["jobId"],
        source_type=data["sourceType"],
        source_id=data["sourceId"],
        template=data["template"],
        status=data["status"],
        input_snapshot=dict(data.get("inputSnapshot", {})),
        events=[
            DeliberationEvent(
                event_id=item["eventId"],
                job_id=item["jobId"],
                seq=item["seq"],
                type=item["type"],
                visibility=item["visibility"],
                payload=dict(item.get("payload", {})),
                participant=item.get("participant"),
                round=item.get("round"),
            )
            for item in data.get("events", [])
        ],
        artifact=artifact,
        context_usage=dict(data.get("contextUsage", {})),
    )
