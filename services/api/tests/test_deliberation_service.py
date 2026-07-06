import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from emotion_talk_api.app import _audio_extension, create_app
from emotion_talk_api.deliberation import DeliberationService
from emotion_talk_api.models import HistoricalContextItem
from emotion_talk_api.models import TranscriptSegment
from emotion_talk_api.providers import HeuristicProvider, ProviderError, provider_from_env
from emotion_talk_api.reports import render_html_report, render_test_report
from emotion_talk_api.storage import SQLiteStorage
from emotion_talk_api.transcript import parse_markdown_transcript


SAMPLE_MARKDOWN = """# 06-13 职业转型与长期规划(1)

> 创建时间: 2026-06-13 21:40

> 转写时长: 37分23秒

## 关键词

暂无关键词

## 转文字

戒凡 00:00:01

六月份、七月份是不是有西班牙语 B1 的培训？

发言人 2 00:00:18

是的，有暑期班，一个月到八月初结束。

戒凡 00:00:31

七月份周一周二周四上课，周三周五可能做课后作业，周末再分配给家庭和身体调整。

发言人 2 00:01:02

如果作业比较多，我可能要 all in，像考专四那样重新把单词、语法、口语听力捡起来。
"""


def wait_for_job(client: TestClient, job_id: str, *, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/expert-advice-jobs/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not finish")


class FakeProvider:
    def __init__(self):
        self.calls = []

    def complete(self, prompt: str, *, purpose: str) -> str:
        self.calls.append((purpose, prompt))
        if purpose == "summary":
            return json.dumps(
                {
                    "title": "职业转型与长期规划",
                    "overview": "这次对话先把语言学习、岗位验证和家庭节奏放到同一张图里看。",
                    "keyPoints": ["七月主攻 B1 学习。", "每周保留一个低负担职业验证动作。"],
                    "chapters": [
                        {
                            "title": "确认学习机会",
                            "startTimestamp": "00:00",
                            "summary": "对话确认六七月有西班牙语 B1 暑期班。",
                        },
                        {
                            "title": "拆分现实节奏",
                            "startTimestamp": "00:31",
                            "summary": "讨论把上课、作业、家庭和身体调整分开安排。",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        if purpose.startswith("initial:life_coach"):
            return "先把七月定义为 B1 冲刺月，目标不是学完一本书，而是恢复可求职的语言信心。"
        if purpose.startswith("initial:counselor"):
            return "情绪上需要允许不确定存在，避免把职业转型压成一次必须成功的考试。"
        if purpose.startswith("initial:reality_strategist"):
            return "现实路径应拆成 B1 学习、外贸岗位验证、家庭节奏三条线，并设置可观测交付物。"
        if purpose.startswith("challenge:"):
            return "挑战点：建议需要更具体，避免 all in 后没有求职验证动作。"
        if purpose.startswith("revision:"):
            return "修正版：七月以学习为主，但每周保留一个低负担职业验证动作。"
        if purpose == "judge":
            return json.dumps(
                {
                    "overview": "这次对话的核心不是单纯学西班牙语，而是用 B1 暑期班重启职业可能性。",
                    "processSummary": [
                        {"round": 1, "title": "初判", "summary": "三位专家分别看到目标、情绪和现实约束。"},
                        {"round": 2, "title": "互评", "summary": "主要挑战是避免学习和求职验证脱节。"},
                        {"round": 3, "title": "修正", "summary": "形成七月主攻学习、保留轻量验证的方案。"},
                    ],
                    "suggestions": [
                        {
                            "title": "把七月定义为语言恢复冲刺月",
                            "body": "用 B1 暑期班恢复词汇、语法、口语和听力，但不要同时承担授课赚钱任务。",
                            "confidence": "high",
                            "evidence": ["发言人提到需要像考专四一样 all in。"],
                        },
                        {
                            "title": "每周保留一个轻量职业验证动作",
                            "body": "只做低负担动作，例如看 3 个外贸 JD、回复 1 个岗位、整理 1 条简历 bullet。",
                            "confidence": "medium",
                            "evidence": ["对话中提到 Boss 上仍有外贸岗位联系。"],
                        },
                    ],
                    "keyUncertainties": ["B1 暑期班真实作业强度未知。", "外贸岗位收入和家庭节奏是否匹配仍需验证。"],
                    "safetyBoundary": "这不是心理治疗或职业承诺，只是基于一次对话的规划建议。",
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected purpose: {purpose}")


class TranscriptParsingTest(unittest.TestCase):
    def test_parses_dingtalk_style_markdown_transcript(self):
        transcript = parse_markdown_transcript(SAMPLE_MARKDOWN)

        self.assertEqual(transcript.title, "06-13 职业转型与长期规划(1)")
        self.assertEqual(transcript.created_at_text, "2026-06-13 21:40")
        self.assertEqual(transcript.duration_text, "37分23秒")
        self.assertEqual(len(transcript.segments), 4)
        self.assertEqual(transcript.segments[0].speaker, "戒凡")
        self.assertEqual(transcript.segments[1].speaker, "发言人 2")
        self.assertIn("B1 的培训", transcript.full_text)
        self.assertIn("暑期班", transcript.full_text)


class DeliberationServiceTest(unittest.TestCase):
    def test_generates_completed_job_with_events_and_artifact(self):
        provider = FakeProvider()
        transcript = parse_markdown_transcript(SAMPLE_MARKDOWN)
        service = DeliberationService(provider=provider)

        job = service.run_from_transcript(
            transcript,
            source_type="recording",
            source_id="sample-recording",
        )

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.source_type, "recording")
        self.assertTrue(job.artifact.overview.startswith("这次对话的核心"))
        self.assertEqual(len(job.artifact.suggestions), 2)
        self.assertEqual([event.seq for event in job.events], list(range(1, len(job.events) + 1)))
        self.assertIn("input_snapshot_frozen", {event.type for event in job.events})
        self.assertIn("expert_message_added", {event.type for event in job.events})
        self.assertIn("expert_challenge_added", {event.type for event in job.events})
        self.assertIn("expert_revision_added", {event.type for event in job.events})
        self.assertIn("artifact_completed", {event.type for event in job.events})
        self.assertEqual(len(provider.calls), 10)

    def test_freezes_selected_history_context_for_expert_team(self):
        provider = FakeProvider()
        transcript = parse_markdown_transcript(SAMPLE_MARKDOWN)
        service = DeliberationService(provider=provider)

        job = service.run_from_transcript(
            transcript,
            source_type="recording",
            source_id="current-recording",
            context_scope="current_with_history",
            historical_context=[
                HistoricalContextItem(
                    source_type="recording",
                    source_id="history-recording",
                    title="06-10 职业焦虑复盘",
                    created_at_text="2026-06-10 22:00",
                    summary="用户反复提到外贸稳定收入和长期热爱之间的拉扯。",
                    key_points=["外贸提供安全感", "普拉提代表长期理想"],
                    relevance="same_space_recent",
                )
            ],
        )

        self.assertEqual(job.input_snapshot["contextScope"], "current_with_history")
        self.assertEqual(job.input_snapshot["historyCount"], 1)
        self.assertEqual(job.context_usage["historyCount"], 1)
        first_prompt = provider.calls[0][1]
        self.assertIn("优先依据当前这次转写", first_prompt)
        self.assertIn("06-10 职业焦虑复盘", first_prompt)
        self.assertIn("外贸提供安全感", first_prompt)

    def test_heuristic_provider_uses_current_emotional_transcript_without_sample_leakage(self):
        transcript = parse_markdown_transcript(
            """# 06-24 倾诉与状态梳理

> 创建时间: 2026-06-24 18:40

> 转写时长: 02分16秒

## 转文字

发言人 1 00:00

我最近一直在想，当前这个状态到底是不是我真正想要的生活。

发言人 2 00:18

你先不用急着给自己下结论，我们可以把困惑拆开看。

发言人 1 00:42

我最难受的点是，别人都在往前走，我却不知道下一步该选什么。

发言人 2 01:10

也许今天不需要马上解决人生，只需要找到一个能开始验证的小动作。
"""
        )

        job = DeliberationService(provider=HeuristicProvider()).run_from_transcript(
            transcript,
            source_type="recording",
            source_id="emotional-sample",
        )

        artifact_text = json.dumps(job.artifact.to_dict(), ensure_ascii=False)
        self.assertIn("七天状态实验", artifact_text)
        self.assertNotIn("西班牙语", artifact_text)
        self.assertNotIn("B1", artifact_text)


class ApiTest(unittest.TestCase):
    def test_heuristic_provider_requires_explicit_local_flag(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProviderError):
                provider_from_env("heuristic")
        with patch.dict(os.environ, {"EMOTION_TALK_ALLOW_HEURISTIC": "true"}, clear=True):
            self.assertIsInstance(provider_from_env("heuristic"), HeuristicProvider)

    def test_summary_job_uses_llm_provider(self):
        provider = FakeProvider()
        app = create_app(provider=provider)
        client = TestClient(app)

        space = client.post("/spaces", json={"name": "家庭倾诉空间"}).json()
        recording = client.post(
            "/recordings",
            json={"spaceId": space["spaceId"], "title": "06-13 职业转型与长期规划"},
        ).json()
        client.post(
            f"/recordings/{recording['recordingId']}/transcript",
            json={"markdown": SAMPLE_MARKDOWN},
        )

        response = client.post(f"/recordings/{recording['recordingId']}/summary-jobs", json={})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["modelTrace"]["runtime"], "llm_summary")
        self.assertIn("语言学习", data["overview"])
        self.assertEqual(provider.calls[0][0], "summary")

    def test_summary_job_returns_503_when_llm_key_is_missing(self):
        with patch.dict(os.environ, {"EMOTION_TALK_LLM_PROVIDER": "deepseek"}, clear=True):
            app = create_app()
            client = TestClient(app)
            space = client.post("/spaces", json={"name": "家庭倾诉空间"}).json()
            recording = client.post(
                "/recordings",
                json={"spaceId": space["spaceId"], "title": "06-13 职业转型与长期规划"},
            ).json()
            client.post(
                f"/recordings/{recording['recordingId']}/transcript",
                json={"markdown": SAMPLE_MARKDOWN},
            )

            response = client.post(f"/recordings/{recording['recordingId']}/summary-jobs", json={})

        self.assertEqual(response.status_code, 503)
        self.assertIn("DEEPSEEK_API_KEY", response.json()["detail"])

    def test_space_management_defaults_limits_names_and_switches_current(self):
        app = create_app(provider=FakeProvider())
        client = TestClient(app)

        listed = client.get("/users/default_user/spaces").json()
        self.assertEqual(listed["spaces"][0]["name"], "家的倾诉空间")
        self.assertEqual(listed["currentSpaceId"], listed["spaces"][0]["spaceId"])

        duplicate = client.post("/spaces", json={"name": "家的倾诉空间", "ownerId": "default_user"})
        self.assertEqual(duplicate.status_code, 409)

        created_ids = []
        for name in ["工作", "家庭", "成长", "健康"]:
            response = client.post("/spaces", json={"name": name, "ownerId": "default_user"})
            self.assertEqual(response.status_code, 200)
            created_ids.append(response.json()["spaceId"])
        too_many = client.post("/spaces", json={"name": "第六个", "ownerId": "default_user"})
        self.assertEqual(too_many.status_code, 409)

        switched = client.post("/users/default_user/current-space", json={"spaceId": created_ids[-1]}).json()
        self.assertEqual(switched["currentSpaceId"], created_ids[-1])
        current = [space for space in switched["spaces"] if space["isCurrent"]]
        self.assertEqual([space["spaceId"] for space in current], [created_ids[-1]])

    def test_space_list_hides_legacy_duplicates_and_caps_visible_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = SQLiteStorage(Path(tmp) / "emotion_talk.sqlite3")
            for index, name in enumerate(["家", "家", "工作", "成长", "健康", "财务", "朋友"]):
                storage.save_space(
                    {
                        "spaceId": f"legacy_{index}",
                        "ownerId": "legacy_user",
                        "name": name,
                        "isCurrent": index == 5,
                        "createdAt": f"2026-07-06T00:0{index}:00+00:00",
                    }
                )
            app = create_app(provider=FakeProvider(), storage=storage)
            client = TestClient(app)

            listed = client.get("/users/legacy_user/spaces").json()

        names = [space["name"] for space in listed["spaces"]]
        self.assertLessEqual(len(names), 5)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(listed["currentSpaceId"], "legacy_5")
        self.assertEqual(listed["spaces"][0]["spaceId"], "legacy_5")

    def test_lists_recordings_by_space(self):
        app = create_app(provider=FakeProvider())
        client = TestClient(app)

        one = client.post("/spaces", json={"name": "空间一"}).json()
        two = client.post("/spaces", json={"name": "空间二"}).json()
        first = client.post("/recordings", json={"spaceId": one["spaceId"], "title": "一号记录"}).json()
        client.post("/recordings", json={"spaceId": two["spaceId"], "title": "二号记录"})

        response = client.get(f"/spaces/{one['spaceId']}/recordings")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([item["recordingId"] for item in data], [first["recordingId"]])

    def test_post_markdown_returns_job_artifact(self):
        app = create_app(provider=FakeProvider())
        client = TestClient(app)

        response = client.post(
            "/deliberation-jobs/from-markdown",
            json={
                "markdown": SAMPLE_MARKDOWN,
                "sourceType": "recording",
                "sourceId": "sample-recording",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["artifact"]["suggestions"][0]["title"], "把七月定义为语言恢复冲刺月")
        self.assertGreaterEqual(len(data["events"]), 10)

    def test_recording_resource_flow_creates_history_aware_expert_job(self):
        app = create_app(provider=FakeProvider())
        client = TestClient(app)

        space = client.post("/spaces", json={"name": "家庭倾诉空间"}).json()
        history = client.post(
            "/recordings",
            json={"spaceId": space["spaceId"], "title": "06-10 职业焦虑复盘"},
        ).json()
        client.post(
            f"/recordings/{history['recordingId']}/transcript",
            json={"markdown": SAMPLE_MARKDOWN},
        )
        client.post(f"/recordings/{history['recordingId']}/summary-jobs", json={})

        current = client.post(
            "/recordings",
            json={"spaceId": space["spaceId"], "title": "06-13 职业转型与长期规划"},
        ).json()
        client.post(
            f"/recordings/{current['recordingId']}/transcript",
            json={"markdown": SAMPLE_MARKDOWN},
        )

        response = client.post(
            f"/recordings/{current['recordingId']}/expert-advice-jobs",
            json={"contextScope": "current_with_history", "historyLimit": 3},
        )

        self.assertEqual(response.status_code, 200)
        created_job = response.json()
        self.assertEqual(created_job["status"], "running")
        job = wait_for_job(client, created_job["jobId"])
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["sourceType"], "recording")
        self.assertEqual(job["sourceId"], current["recordingId"])
        self.assertEqual(job["contextUsage"]["scope"], "current_with_history")
        self.assertEqual(job["contextUsage"]["historyCount"], 1)
        self.assertEqual(job["contextUsage"]["historySources"][0]["sourceId"], history["recordingId"])

        events = client.get(f"/expert-advice-jobs/{job['jobId']}/events").json()
        artifact = client.get(f"/expert-advice-jobs/{job['jobId']}/artifact").json()

        self.assertGreaterEqual(len(events), 10)
        self.assertEqual(artifact["suggestions"][0]["title"], "把七月定义为语言恢复冲刺月")

    def test_sqlite_storage_survives_app_restart(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "emotion_talk.sqlite3"
            app = create_app(provider=FakeProvider(), storage=SQLiteStorage(db_path))
            client = TestClient(app)

            space = client.post("/spaces", json={"name": "家庭倾诉空间"}).json()
            recording = client.post(
                "/recordings",
                json={"spaceId": space["spaceId"], "title": "06-13 职业转型与长期规划"},
            ).json()
            client.post(
                f"/recordings/{recording['recordingId']}/transcript",
                json={"markdown": SAMPLE_MARKDOWN},
            )
            client.post(f"/recordings/{recording['recordingId']}/summary-jobs", json={})

            restarted = create_app(provider=FakeProvider(), storage=SQLiteStorage(db_path))
            restarted_client = TestClient(restarted)
            response = restarted_client.get(f"/recordings/{recording['recordingId']}")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "summarized")
            self.assertEqual(data["transcript"]["segmentCount"], 4)
            self.assertEqual(data["summaryArtifact"]["title"], "06-13 职业转型与长期规划(1)")

    def test_audio_transcription_endpoint_stores_transcript(self):
        app = create_app(provider=FakeProvider())
        client = TestClient(app)
        space = client.post("/spaces", json={"name": "家庭倾诉空间"}).json()
        recording = client.post("/recordings", json={"spaceId": space["spaceId"], "title": "真实录音"}).json()

        with patch(
            "emotion_talk_api.app._transcribe_audio_with_dashscope",
            return_value=[TranscriptSegment(speaker="我", timestamp="00:01", text="今天测试真实录音识别。")],
        ):
            response = client.post(
                f"/recordings/{recording['recordingId']}/audio-transcriptions",
                json={
                    "audioBase64": "AAECAw==",
                    "mimeType": "audio/x-caf",
                    "title": "真实录音",
                    "durationText": "00:05",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "transcribed")
        self.assertEqual(data["transcript"]["segmentCount"], 1)
        self.assertEqual(data["audioObject"]["byteSize"], 4)

    def test_browser_audio_mime_types_keep_real_extensions(self):
        self.assertEqual(_audio_extension("audio/webm"), "webm")
        self.assertEqual(_audio_extension("audio/ogg"), "ogg")


class ReportTest(unittest.TestCase):
    def test_renders_test_report_with_verification_summary(self):
        provider = FakeProvider()
        transcript = parse_markdown_transcript(SAMPLE_MARKDOWN)
        job = DeliberationService(provider=provider).run_from_transcript(
            transcript,
            source_type="recording",
            source_id="sample-recording",
        )

        report = render_test_report(
            transcript=transcript,
            job=job,
            source_path="/tmp/sample.md",
            verification={
                "unit_tests": "passed",
                "real_run": "not_run",
            },
        )

        self.assertIn("# 测试报告", report)
        self.assertIn("06-13 职业转型与长期规划(1)", report)
        self.assertIn("completed", report)
        self.assertIn("把七月定义为语言恢复冲刺月", report)

    def test_renders_html_report_with_expert_timeline_and_judge_decision(self):
        provider = FakeProvider()
        transcript = parse_markdown_transcript(SAMPLE_MARKDOWN)
        job = DeliberationService(provider=provider).run_from_transcript(
            transcript,
            source_type="recording",
            source_id="sample-recording",
        )

        html = render_html_report(transcript=transcript, job=job)

        self.assertIn("专家团时间轴", html)
        self.assertIn("life_coach", html)
        self.assertIn("counselor", html)
        self.assertIn("reality_strategist", html)
        self.assertIn("裁判决策", html)
        self.assertIn("上下文使用", html)
        self.assertIn("把七月定义为语言恢复冲刺月", html)
        self.assertIn("初判", html)
        self.assertIn("互评", html)
        self.assertIn("修正", html)


if __name__ == "__main__":
    unittest.main()
