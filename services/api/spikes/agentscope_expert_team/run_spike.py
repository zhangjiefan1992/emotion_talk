# -*- coding: utf-8 -*-
"""Drive a local AgentScope expert-team spike through HTTP APIs."""

import asyncio
import collections
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from agentscope.message import TextBlock, UserMsg

from prompts import LEADER_SYSTEM_PROMPT, SPIKE_USER_PROMPT


BASE_URL = os.getenv("AGENTSCOPE_SPIKE_BASE_URL", "http://127.0.0.1:18000")
USER_ID = os.getenv("AGENTSCOPE_SPIKE_USER_ID", "local-dev-user")
TIMEOUT_SECONDS = int(os.getenv("AGENTSCOPE_SPIKE_TIMEOUT_SECONDS", "180"))
IDLE_AFTER_REPLY_SECONDS = int(
    os.getenv("AGENTSCOPE_SPIKE_IDLE_AFTER_REPLY_SECONDS", "10")
)
SETUP_ONLY = os.getenv("AGENTSCOPE_SPIKE_SETUP_ONLY") == "1"
VERBOSE_EVENTS = os.getenv("AGENTSCOPE_SPIKE_VERBOSE_EVENTS") == "1"
MILESTONE_EVENT_TYPES = {
    "REPLY_START",
    "REPLY_END",
    "HINT_BLOCK",
    "CUSTOM",
    "EXCEED_MAX_ITERS",
}


@dataclass(frozen=True)
class ProviderConfig:
    credential_type: str
    model_type: str
    model: str
    credential_payload: dict[str, Any]


def provider_from_env() -> ProviderConfig:
    """Select the first configured LLM provider from environment vars."""
    if api_key := os.getenv("DASHSCOPE_API_KEY"):
        return ProviderConfig(
            credential_type="dashscope_credential",
            model_type="dashscope_chat",
            model=os.getenv("AGENTSCOPE_SPIKE_MODEL", "qwen-plus"),
            credential_payload={
                "type": "dashscope_credential",
                "name": "local dashscope",
                "api_key": api_key,
                "base_url": os.getenv(
                    "DASHSCOPE_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                ),
            },
        )
    if api_key := os.getenv("DEEPSEEK_API_KEY"):
        return ProviderConfig(
            credential_type="deepseek_credential",
            model_type="deepseek_chat",
            model=os.getenv("AGENTSCOPE_SPIKE_MODEL", "deepseek-chat"),
            credential_payload={
                "type": "deepseek_credential",
                "name": "local deepseek",
                "api_key": api_key,
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            },
        )
    if api_key := os.getenv("ANTHROPIC_API_KEY"):
        payload: dict[str, Any] = {
            "type": "anthropic_credential",
            "name": "local anthropic",
            "api_key": api_key,
        }
        if base_url := os.getenv("ANTHROPIC_BASE_URL"):
            payload["base_url"] = base_url
        return ProviderConfig(
            credential_type="anthropic_credential",
            model_type="anthropic_chat",
            model=os.getenv("AGENTSCOPE_SPIKE_MODEL", "claude-sonnet-4-5"),
            credential_payload=payload,
        )
    if api_key := os.getenv("OPENAI_API_KEY"):
        payload = {
            "type": "openai_credential",
            "name": "local openai",
            "api_key": api_key,
        }
        if base_url := os.getenv("OPENAI_BASE_URL"):
            payload["base_url"] = base_url
        return ProviderConfig(
            credential_type="openai_credential",
            model_type="openai_chat",
            model=os.getenv("AGENTSCOPE_SPIKE_MODEL", "gpt-4.1-mini"),
            credential_payload=payload,
        )

    raise RuntimeError(
        "No LLM API key found. Set DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, "
        "ANTHROPIC_API_KEY, or OPENAI_API_KEY."
    )


async def post_json(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    """POST JSON and return JSON, raising with useful detail on failure."""
    response = await client.post(path, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(
            f"POST {path} failed: {response.status_code} {response.text}"
        )
    return response.json()


async def stream_events(
    client: httpx.AsyncClient,
    agent_id: str,
    session_id: str,
    events: list[dict],
    stop: asyncio.Event,
) -> None:
    """Collect SSE events until stop is set."""
    async with client.stream(
        "GET",
        f"/sessions/{session_id}/stream",
        params={"agent_id": agent_id},
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if stop.is_set():
                break
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload:
                continue
            event = json.loads(payload)
            events.append(event)
            event_type = event.get("type")
            if VERBOSE_EVENTS or event_type in MILESTONE_EVENT_TYPES:
                print(f"event: {event_type}")


async def main() -> None:
    provider = provider_from_env()
    headers = {"X-User-ID": USER_ID}
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=headers,
        timeout=httpx.Timeout(30.0, read=None),
    ) as client:
        health = (await client.get("/healthz")).json()
        print(f"health: {health}")

        credential = await post_json(
            client,
            "/credential/",
            {"data": provider.credential_payload},
        )
        credential_id = credential["credential_id"]
        print(f"credential: {credential_id}")

        agent = await post_json(
            client,
            "/agent/",
            {
                "name": "expert_judge",
                "system_prompt": LEADER_SYSTEM_PROMPT,
            },
        )
        agent_id = agent["agent_id"]
        print(f"agent: {agent_id}")

        session = await post_json(
            client,
            "/sessions/",
            {
                "agent_id": agent_id,
                "workspace_id": f"expert-spike-{int(time.time())}",
                "name": "AgentScope expert team spike",
                "chat_model_config": {
                    "type": provider.model_type,
                    "credential_id": credential_id,
                    "model": provider.model,
                    "parameters": {
                        "temperature": 0.3,
                    },
                },
            },
        )
        session_id = session["session_id"]
        print(f"session: {session_id}")

        if SETUP_ONLY:
            print("setup-only: created credential, agent, and session; chat not triggered")
            return

        events: list[dict] = []
        stop = asyncio.Event()
        reader = asyncio.create_task(
            stream_events(client, agent_id, session_id, events, stop),
        )

        await asyncio.sleep(0.5)
        user_msg = UserMsg(
            name="user",
            content=[TextBlock(text=SPIKE_USER_PROMPT)],
        )
        await post_json(
            client,
            "/chat/",
            {
                "agent_id": agent_id,
                "session_id": session_id,
                "input": user_msg.model_dump(mode="json"),
            },
        )
        print("chat: started")

        deadline = time.monotonic() + TIMEOUT_SECONDS
        last_seen_count = 0
        last_event_at = time.monotonic()
        while time.monotonic() < deadline:
            await asyncio.sleep(2)
            if len(events) != last_seen_count:
                last_seen_count = len(events)
                last_event_at = time.monotonic()
            if any(event.get("type") == "REPLY_END" for event in events) and (
                time.monotonic() - last_event_at >= IDLE_AFTER_REPLY_SECONDS
            ):
                break

        stop.set()
        reader.cancel()
        try:
            await reader
        except asyncio.CancelledError:
            pass

        sessions = await client.get("/sessions/", params={"agent_id": agent_id})
        sessions.raise_for_status()
        session_payload = sessions.json()
        session_items = session_payload.get("sessions", [])
        latest_session = session_items[0]["session"] if session_items else {}
        context_count = len(latest_session.get("state", {}).get("context", []))
        print(
            "sessions: "
            f"count={len(session_items)} latest={latest_session.get('id')} "
            f"context_messages={context_count}"
        )

        event_counts = collections.Counter(
            event.get("type") for event in events if event.get("type")
        )
        print("event summary:")
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type}: {count}")

        out_path = "services/api/spikes/agentscope_expert_team/.tmp/last-events.json"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"events saved: {out_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from None
