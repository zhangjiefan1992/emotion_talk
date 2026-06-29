# -*- coding: utf-8 -*-
"""AgentScope service for the Emotion Talk expert team spike."""

import os
from pathlib import Path

import uvicorn
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from agentscope.app import create_app, SubAgentTemplate
from agentscope.app.deps import get_current_user_id as default_get_current_user_id
from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import RedisStorage
from agentscope.app.workspace_manager import LocalWorkspaceManager
from agentscope.permission import PermissionContext, PermissionMode

from prompts import EXPERT_TEMPLATE, EXPERT_TYPES


SPIKE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = Path(
    os.getenv(
        "AGENTSCOPE_SPIKE_WORKSPACE_DIR",
        str(SPIKE_DIR / ".tmp" / "workspaces"),
    ),
)


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable."""
    return int(os.getenv(name, str(default)))


async def get_current_user_id() -> str:
    """Local-only user id placeholder for the spike."""
    return os.getenv("AGENTSCOPE_SPIKE_USER_ID", "local-dev-user")


def build_expert_templates() -> list[SubAgentTemplate]:
    """Build the three Emotion Talk expert worker templates."""
    return [
        SubAgentTemplate(
            type=item["type"],
            description=item["description"],
            system_prompt_template=EXPERT_TEMPLATE,
            permission_context=PermissionContext(
                mode=PermissionMode.EXPLORE,
            ),
            override_leader_mode=True,
            extend_leader_permission_rules=False,
            extend_leader_working_directories=False,
        )
        for item in EXPERT_TYPES
    ]


redis_host = os.getenv("AGENTSCOPE_SPIKE_REDIS_HOST", "127.0.0.1")
redis_port = env_int("AGENTSCOPE_SPIKE_REDIS_PORT", 16379)
redis_db = env_int("AGENTSCOPE_SPIKE_REDIS_DB", 0)

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app = create_app(
    storage=RedisStorage(
        host=redis_host,
        port=redis_port,
        db=redis_db,
    ),
    message_bus=RedisMessageBus(
        host=redis_host,
        port=redis_port,
        db=redis_db,
    ),
    workspace_manager=LocalWorkspaceManager(
        basedir=str(WORKSPACE_DIR),
        default_mcps=[],
    ),
    custom_subagent_templates=build_expert_templates(),
    extra_middlewares=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ],
    title="Emotion Talk AgentScope Spike",
)

app.dependency_overrides[default_get_current_user_id] = get_current_user_id


@app.get("/healthz")
async def healthz() -> dict:
    """Basic health endpoint for local checks."""
    return {
        "ok": True,
        "redis": f"{redis_host}:{redis_port}/{redis_db}",
        "workspaceDir": str(WORKSPACE_DIR),
        "templates": [item["type"] for item in EXPERT_TYPES],
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("AGENTSCOPE_SPIKE_HOST", "127.0.0.1"),
        port=env_int("AGENTSCOPE_SPIKE_PORT", 18000),
        reload=False,
    )
