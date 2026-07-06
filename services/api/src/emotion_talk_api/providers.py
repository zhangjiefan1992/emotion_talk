from __future__ import annotations

import os
from typing import Protocol

import httpx


class LLMProvider(Protocol):
    def complete(self, prompt: str, *, purpose: str) -> str:
        """Return a text completion for one deliberation step."""


class ProviderError(RuntimeError):
    pass


class DeepSeekProvider:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise ProviderError("DEEPSEEK_API_KEY is required for DeepSeekProvider")
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str, *, purpose: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 Emotion Talk 服务端的多 Agent 讨论运行时。"
                        "输出必须克制、具体、可执行，不做医疗诊断，不承诺治疗效果。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"DeepSeek request failed for {purpose}: {exc}") from exc
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"DeepSeek response shape is invalid for {purpose}") from exc


class HeuristicProvider:
    """Offline fallback for wiring tests and demos when no LLM key is available."""

    def complete(self, prompt: str, *, purpose: str) -> str:
        theme = _detect_prompt_theme(prompt)
        if theme == "emotional_uncertainty":
            return _emotional_uncertainty_response(purpose)

        if purpose.startswith("initial:life_coach"):
            return "把接下来一个月定义为恢复职业主动权的冲刺期，先收敛目标，再做低成本验证。"
        if purpose.startswith("initial:counselor"):
            return "先承认迷茫和压力是真实存在的，规划要降低自责感，避免把一次学习变成自我证明。"
        if purpose.startswith("initial:reality_strategist"):
            return "现实上要把语言学习、岗位验证、家庭节奏拆开，不要同时追求学习、授课和求职三个满分。"
        if purpose.startswith("challenge:"):
            return "需要增加可观测交付物，否则学习投入和职业结果之间会断开。"
        if purpose.startswith("revision:"):
            return "修正后建议采用主线学习、支线验证、周末恢复的节奏，不让计划挤压身体和家庭。"
        return (
            "{"
            '"overview":"这次对话的核心是用西班牙语 B1 暑期班作为职业转型的恢复性入口，而不是马上逼出最终答案。",'
            '"processSummary":[{"round":1,"title":"初判","summary":"专家分别看到目标、情绪和现实约束。"},{"round":2,"title":"互评","summary":"主要挑战是避免只学习不验证。"},{"round":3,"title":"修正","summary":"形成学习为主、验证为辅、保留恢复空间的方案。"}],'
            '"suggestions":[{"title":"七月只设一个主目标","body":"把 B1 暑期班作为主线，暂停高消耗授课任务，确保语言能力恢复。","confidence":"high","evidence":["对话中提到需要 all in 学习。"]},{"title":"每周做一个低负担职业验证","body":"例如看外贸岗位、回复一个机会、记录一个简历素材，不追求马上入职。","confidence":"medium","evidence":["对话中提到仍有外贸岗位联系。"]}],'
            '"keyUncertainties":["课程强度未知。","外贸岗位收入和家庭节奏匹配度未知。"],'
            '"safetyBoundary":"这不是心理治疗、医疗诊断或职业承诺，只是基于当前对话的规划建议。"'
            "}"
        )


def _detect_prompt_theme(prompt: str) -> str:
    career_language_markers = ("西班牙语", "B1", "外贸", "暑期班")
    emotional_uncertainty_markers = (
        "真正想要的生活",
        "别人都在往前走",
        "不知道下一步",
        "小动作",
        "停在原地",
        "困惑拆开看",
        "人生级问题",
        "行动感",
        "迷茫",
        "七天",
        "触发点",
        "真实需求",
    )
    if any(marker in prompt for marker in emotional_uncertainty_markers) and not any(
        marker in prompt for marker in career_language_markers
    ):
        return "emotional_uncertainty"
    return "career_language"


def _emotional_uncertainty_response(purpose: str) -> str:
    if purpose.startswith("initial:life_coach"):
        return "先把人生级问题降维成一周内可验证的小动作，目标不是立刻找到终局答案，而是恢复行动感。"
    if purpose.startswith("initial:counselor"):
        return "迷茫和比较感都是真实压力信号，建议先承接情绪，再讨论选择，不要把自己推向马上表态。"
    if purpose.startswith("initial:reality_strategist"):
        return "现实上要把困惑写成假设，把下一步变成低成本实验，否则对话结束后仍会停留在反复消耗。"
    if purpose.startswith("challenge:life_coach"):
        return "只说小动作还不够，需要定义记录格式和复盘时间，否则一周后仍然缺少判断材料。"
    if purpose.startswith("challenge:counselor"):
        return "行动建议要足够轻，不能把本来用于恢复安全感的记录变成新的自我考核。"
    if purpose.startswith("challenge:reality_strategist"):
        return "需要区分情绪触发点和现实约束，避免把所有不舒服都解释成方向错误。"
    if purpose.startswith("revision:life_coach"):
        return "修正后建议采用七天状态实验：每天只记录一个触发点、一个真实需求和一个可执行动作。"
    if purpose.startswith("revision:counselor"):
        return "修正后建议把记录写得短而温和，重点是看见自己，而不是给自己打分。"
    if purpose.startswith("revision:reality_strategist"):
        return "修正后建议七天后再做方向判断，先用连续记录补齐信息，而不是在单次情绪里做大决定。"
    return (
        "{"
        '"overview":"这次对话的核心不是马上解决整个人生方向，而是把迷茫、比较感和下一步行动拆开，先恢复一点可执行感。",'
        '"processSummary":[{"round":1,"title":"初判","summary":"专家分别看到方向感缺失、情绪压力和现实行动断点。"},{"round":2,"title":"互评","summary":"主要挑战是避免建议过重，也避免只停留在安慰。"},{"round":3,"title":"修正","summary":"最终收敛为七天状态实验，用很小的记录动作积累判断材料。"}],'
        '"suggestions":[{"title":"做七天状态实验","body":"每天只写三行：一个触发点、一个真实需求、一个可执行动作。写短一点，重点是连续。","confidence":"medium","evidence":["对话中提到不知道下一步该选什么。","对话中出现了对小动作的接受。"]},{"title":"暂缓重大结论","body":"七天内先不急着判断自己是不是失败、方向是不是错了，等记录形成模式后再讨论选择。","confidence":"medium","evidence":["对话中提到别人都在往前走带来的压力。"]}],'
        '"keyUncertainties":["当前压力来源还没有被完全拆开。","连续记录后才知道这是短期情绪波动还是长期模式。"],'
        '"safetyBoundary":"这些建议用于自我梳理和沟通辅助，不构成医疗诊断、心理治疗或人生重大决定建议。"'
        "}"
    )


def provider_from_env(name: str = "deepseek") -> LLMProvider:
    if name == "deepseek":
        return DeepSeekProvider()
    if name == "heuristic":
        if os.getenv("EMOTION_TALK_ALLOW_HEURISTIC", "").lower() not in {"1", "true", "yes"}:
            raise ProviderError("HeuristicProvider is disabled. Set EMOTION_TALK_ALLOW_HEURISTIC=true for local wiring tests.")
        return HeuristicProvider()
    raise ProviderError(f"Unsupported provider: {name}")
