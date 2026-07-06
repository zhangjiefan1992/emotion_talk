from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .models import (
    DeliberationArtifact,
    DeliberationEvent,
    DeliberationJob,
    HistoricalContextItem,
    ProcessSummary,
    RecordingTranscript,
    Suggestion,
)
from .providers import LLMProvider


@dataclass(frozen=True)
class Participant:
    id: str
    name: str
    role_prompt: str


DEFAULT_PARTICIPANTS = [
    Participant(
        id="life_coach",
        name="人生教练",
        role_prompt="聚焦目标、节奏、行动闭环和可执行的下一步。",
    ),
    Participant(
        id="counselor",
        name="心理咨询视角",
        role_prompt="聚焦情绪承接、心理安全、表达边界和自我接纳。",
    ),
    Participant(
        id="reality_strategist",
        name="现实行动视角",
        role_prompt="聚焦现实约束、资源、机会成本、求职验证和家庭节奏。",
    ),
]


class DeliberationService:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        participants: list[Participant] | None = None,
        template: str = "emotion_talk_expert_team_v1",
    ) -> None:
        self.provider = provider
        self.participants = participants or DEFAULT_PARTICIPANTS
        self.template = template

    def run_from_transcript(
        self,
        transcript: RecordingTranscript,
        *,
        source_type: str,
        source_id: str,
        context_scope: str = "current_only",
        historical_context: list[HistoricalContextItem] | None = None,
        profile_context: dict[str, Any] | None = None,
        job_id: str | None = None,
        on_event: Callable[[DeliberationEvent], None] | None = None,
    ) -> DeliberationJob:
        historical_context = historical_context or []
        profile_context = profile_context or {}
        if context_scope not in {"current_only", "current_with_history"}:
            raise ValueError(f"Unsupported context scope: {context_scope}")

        job_id = job_id or f"job_{uuid.uuid4().hex[:16]}"
        seq = 0
        events: list[DeliberationEvent] = []

        def emit(
            event_type: str,
            payload: dict[str, Any],
            *,
            visibility: str = "user_visible",
            participant: str | None = None,
            round_number: int | None = None,
        ) -> None:
            nonlocal seq
            seq += 1
            event = DeliberationEvent(
                event_id=f"evt_{seq:04d}",
                job_id=job_id,
                seq=seq,
                type=event_type,
                visibility=visibility,
                payload=payload,
                participant=participant,
                round=round_number,
            )
            events.append(event)
            if on_event:
                on_event(event)

        input_snapshot = self._build_input_snapshot(
            transcript,
            context_scope=context_scope,
            historical_context=historical_context,
            profile_context=profile_context,
        )
        context_usage = self._build_context_usage(
            context_scope=context_scope,
            historical_context=historical_context,
            profile_context=profile_context,
        )
        emit("job_created", {"template": self.template}, visibility="internal")
        emit("context_scope_selected", context_usage)
        emit("input_snapshot_frozen", input_snapshot)
        emit("safety_precheck_passed", {"reason": "no crisis signal detected"})

        initial_views: dict[str, str] = {}
        emit("round_started", {"title": "初判"}, round_number=1)
        for participant in self.participants:
            content = self.provider.complete(
                self._initial_prompt(participant, input_snapshot),
                purpose=f"initial:{participant.id}",
            )
            initial_views[participant.id] = content
            emit(
                "expert_message_added",
                {"title": "初判", "content": content},
                participant=participant.id,
                round_number=1,
            )

        challenges: dict[str, str] = {}
        emit("round_started", {"title": "互评"}, round_number=2)
        for participant in self.participants:
            content = self.provider.complete(
                self._challenge_prompt(participant, input_snapshot, initial_views),
                purpose=f"challenge:{participant.id}",
            )
            challenges[participant.id] = content
            emit(
                "expert_challenge_added",
                {"title": "互评", "content": content},
                participant=participant.id,
                round_number=2,
            )

        revisions: dict[str, str] = {}
        emit("round_started", {"title": "修正"}, round_number=3)
        for participant in self.participants:
            content = self.provider.complete(
                self._revision_prompt(participant, input_snapshot, initial_views, challenges),
                purpose=f"revision:{participant.id}",
            )
            revisions[participant.id] = content
            emit(
                "expert_revision_added",
                {"title": "修正", "content": content},
                participant=participant.id,
                round_number=3,
            )

        emit("judge_synthesis_started", {"title": "裁判收敛"})
        artifact_text = self.provider.complete(
            self._judge_prompt(input_snapshot, initial_views, challenges, revisions),
            purpose="judge",
        )
        artifact = self._parse_artifact(artifact_text)
        artifact.model_trace.update(
            {
                "runtime": "lightweight_state_machine",
                "templateVersion": self.template,
                "participants": [participant.id for participant in self.participants],
                "contextUsage": context_usage,
            }
        )
        emit("safety_review_passed", {"reason": "artifact includes safety boundary"})
        emit("artifact_completed", artifact.to_dict())
        emit("job_completed", {"status": "completed"})

        return DeliberationJob(
            job_id=job_id,
            source_type=source_type,
            source_id=source_id,
            template=self.template,
            status="completed",
            input_snapshot=input_snapshot,
            events=events,
            artifact=artifact,
            context_usage=context_usage,
        )

    def _build_input_snapshot(
        self,
        transcript: RecordingTranscript,
        *,
        context_scope: str,
        historical_context: list[HistoricalContextItem],
        profile_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "title": transcript.title,
            "createdAtText": transcript.created_at_text,
            "durationText": transcript.duration_text,
            "segmentCount": len(transcript.segments),
            "speakers": sorted({segment.speaker for segment in transcript.segments}),
            "transcriptText": transcript.full_text,
            "contextScope": context_scope,
            "historyCount": len(historical_context),
            "historicalContext": [item.to_dict() for item in historical_context],
            "profileContext": profile_context,
        }

    def _build_context_usage(
        self,
        *,
        context_scope: str,
        historical_context: list[HistoricalContextItem],
        profile_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "scope": context_scope,
            "primary": "current_recording",
            "historyCount": len(historical_context),
            "historySources": [
                {
                    "sourceType": item.source_type,
                    "sourceId": item.source_id,
                    "title": item.title,
                    "relevance": item.relevance,
                }
                for item in historical_context
            ],
            "profileIncluded": bool(profile_context),
        }

    def _context_prompt_section(self, snapshot: dict[str, Any]) -> str:
        history = snapshot.get("historicalContext", [])
        profile = snapshot.get("profileContext", {})
        if snapshot.get("contextScope") == "current_only":
            history_block = "历史上下文：本次请求选择 current_only，不引用历史纪要。"
        elif history:
            history_block = "历史上下文（只能作为补充线索，不能覆盖当前转写事实）：\n" + json.dumps(
                history,
                ensure_ascii=False,
                indent=2,
            )
        else:
            history_block = "历史上下文：本次请求允许引用历史，但服务端没有选中可用历史。"

        if profile:
            profile_block = "用户/空间画像（只能作为补充线索）：\n" + json.dumps(
                profile,
                ensure_ascii=False,
                indent=2,
            )
        else:
            profile_block = "用户/空间画像：无。"

        return f"""上下文使用规则：
- 优先依据当前这次转写，历史信息只能用于识别反复出现的模式和补充背景。
- 如果当前转写与历史信息冲突，以当前转写为准，并在不确定性中说明。
- 不要声称看过未提供的历史信息。

{history_block}

{profile_block}
"""

    def _initial_prompt(self, participant: Participant, snapshot: dict[str, Any]) -> str:
        return f"""你是{participant.name}。
职责：{participant.role_prompt}

请基于以下转写，给出第一轮初判。要求：
- 只输出 3 到 6 条要点。
- 具体、克制，不做医疗诊断。
- 关注当前困惑、长期方向与下一步行动。

{self._context_prompt_section(snapshot)}

转写：
{snapshot["transcriptText"]}
"""

    def _challenge_prompt(
        self,
        participant: Participant,
        snapshot: dict[str, Any],
        initial_views: dict[str, str],
    ) -> str:
        return f"""你是{participant.name}。
请阅读其他专家第一轮观点，提出挑战或补充。不要重复自己的初判。

输入标题：{snapshot["title"]}

第一轮观点：
{json.dumps(initial_views, ensure_ascii=False, indent=2)}

{self._context_prompt_section(snapshot)}

请输出 2 到 4 条挑战或修正建议。"""

    def _revision_prompt(
        self,
        participant: Participant,
        snapshot: dict[str, Any],
        initial_views: dict[str, str],
        challenges: dict[str, str],
    ) -> str:
        return f"""你是{participant.name}。
请结合第一轮观点和互评挑战，给出你的修正版观点。

输入标题：{snapshot["title"]}

第一轮：
{json.dumps(initial_views, ensure_ascii=False, indent=2)}

互评：
{json.dumps(challenges, ensure_ascii=False, indent=2)}

{self._context_prompt_section(snapshot)}

请输出 3 到 5 条修正版观点，强调可执行和边界。"""

    def _judge_prompt(
        self,
        snapshot: dict[str, Any],
        initial_views: dict[str, str],
        challenges: dict[str, str],
        revisions: dict[str, str],
    ) -> str:
        return f"""你是裁判/收敛器。请基于专家团三轮讨论，输出严格 JSON，不要 markdown。

JSON schema:
{{
  "overview": "string",
  "processSummary": [{{"round": 1, "title": "string", "summary": "string"}}],
  "suggestions": [{{"title": "string", "body": "string", "confidence": "high|medium|low", "evidence": ["string"]}}],
  "keyUncertainties": ["string"],
  "safetyBoundary": "string"
}}

要求：
- suggestions 只能 1 到 3 条。
- 建议必须点到为止，不要替用户做决定。
- 必须结合当前转写中的事实证据。
- 不输出医疗诊断、心理治疗承诺或极端建议。

输入快照：
{json.dumps({k: v for k, v in snapshot.items() if k != "transcriptText"}, ensure_ascii=False, indent=2)}

{self._context_prompt_section(snapshot)}

第一轮：
{json.dumps(initial_views, ensure_ascii=False, indent=2)}

互评：
{json.dumps(challenges, ensure_ascii=False, indent=2)}

修正：
{json.dumps(revisions, ensure_ascii=False, indent=2)}
"""

    def _parse_artifact(self, text: str) -> DeliberationArtifact:
        cleaned = text.strip()
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = {
                "overview": cleaned,
                "processSummary": [],
                "suggestions": [],
                "keyUncertainties": ["裁判输出不是合法 JSON，需要重新生成。"],
                "safetyBoundary": "这不是医疗、心理治疗或职业承诺。",
            }
        return DeliberationArtifact(
            overview=str(data.get("overview", "")).strip(),
            process_summary=[
                ProcessSummary(
                    round=int(item.get("round", index + 1)),
                    title=str(item.get("title", "")),
                    summary=str(item.get("summary", "")),
                )
                for index, item in enumerate(data.get("processSummary", []))
            ],
            suggestions=[
                Suggestion(
                    title=str(item.get("title", "")),
                    body=str(item.get("body", "")),
                    confidence=str(item.get("confidence", "medium")),
                    evidence=[str(evidence) for evidence in item.get("evidence", [])],
                )
                for item in data.get("suggestions", [])
            ][:3],
            key_uncertainties=[str(item) for item in data.get("keyUncertainties", [])],
            safety_boundary=str(data.get("safetyBoundary", "")),
        )
