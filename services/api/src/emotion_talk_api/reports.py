from __future__ import annotations

import collections
import html
import json
import re
from typing import Any

from .models import DeliberationJob, RecordingTranscript

PARTICIPANT_LABELS = {
    "life_coach": "人生教练",
    "counselor": "心理咨询视角",
    "reality_strategist": "现实行动视角",
}

ROUND_TITLES = {
    1: "第一轮：初判",
    2: "第二轮：互评",
    3: "第三轮：修正",
}


def render_advice_markdown(job: DeliberationJob) -> str:
    lines = [
        f"# {job.input_snapshot.get('title', '专家团建议')}",
        "",
        "## 总览",
        "",
        job.artifact.overview,
        "",
        "## 过程",
        "",
    ]
    for item in job.artifact.process_summary:
        lines.extend(
            [
                f"### 第 {item.round} 轮：{item.title}",
                "",
                item.summary,
                "",
            ]
        )
    lines.extend(["## 建议", ""])
    for index, suggestion in enumerate(job.artifact.suggestions, start=1):
        lines.extend(
            [
                f"### {index}. {suggestion.title}",
                "",
                suggestion.body,
                "",
                f"- 置信度：{suggestion.confidence}",
            ]
        )
        if suggestion.evidence:
            lines.append(f"- 依据：{'；'.join(suggestion.evidence)}")
        lines.append("")
    lines.extend(["## 关键不确定性", ""])
    for item in job.artifact.key_uncertainties:
        lines.append(f"- {item}")
    lines.extend(["", "## 安全边界", "", job.artifact.safety_boundary, ""])
    return "\n".join(lines)


def render_test_report(
    *,
    transcript: RecordingTranscript,
    job: DeliberationJob,
    source_path: str,
    verification: dict[str, Any],
) -> str:
    event_counts = collections.Counter(event.type for event in job.events)
    lines = [
        "# 测试报告",
        "",
        "## 测试对象",
        "",
        f"- Source: `{source_path}`",
        f"- Title: {transcript.title}",
        f"- Created At: {transcript.created_at_text}",
        f"- Duration: {transcript.duration_text}",
        f"- Segments: {len(transcript.segments)}",
        "",
        "## 服务端链路",
        "",
        f"- Job ID: `{job.job_id}`",
        f"- Source Type: `{job.source_type}`",
        f"- Source ID: `{job.source_id}`",
        f"- Template: `{job.template}`",
        f"- Status: `{job.status}`",
        f"- Event Count: {len(job.events)}",
        "",
        "## 事件统计",
        "",
    ]
    for event_type, count in sorted(event_counts.items()):
        lines.append(f"- `{event_type}`: {count}")
    lines.extend(["", "## 输出建议", ""])
    for index, suggestion in enumerate(job.artifact.suggestions, start=1):
        lines.extend(
            [
                f"### {index}. {suggestion.title}",
                "",
                suggestion.body,
                "",
            ]
        )
    lines.extend(["## 关键不确定性", ""])
    for item in job.artifact.key_uncertainties:
        lines.append(f"- {item}")
    lines.extend(["", "## 安全边界", "", job.artifact.safety_boundary, ""])
    lines.extend(["## 验证记录", ""])
    for name, result in verification.items():
        lines.append(f"- `{name}`: {result}")
    lines.append("")
    return "\n".join(lines)


def _safe_text(value: Any) -> str:
    text = str(value if value is not None else "")
    text = text.replace("—", "-").replace("–", "-")
    return html.escape(text)


def _rich_text(value: Any) -> str:
    text = _safe_text(value)
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return ""
    return "\n".join(f"<p>{part.replace(chr(10), '<br>')}</p>" for part in paragraphs)


def _event_cards(job: DeliberationJob, round_number: int, event_type: str) -> str:
    cards = []
    for event in job.events:
        if event.round != round_number or event.type != event_type:
            continue
        participant = event.participant or "unknown"
        label = PARTICIPANT_LABELS.get(participant, participant)
        content = event.payload.get("content", "")
        cards.append(
            f"""
            <article class="expert-card">
              <div class="expert-head">
                <span>{_safe_text(label)}</span>
                <code>{_safe_text(participant)}</code>
              </div>
              <div class="expert-body">{_rich_text(content)}</div>
            </article>
            """
        )
    return "\n".join(cards)


def render_html_report(*, transcript: RecordingTranscript, job: DeliberationJob) -> str:
    artifact_json = _safe_text(json.dumps(job.artifact.to_dict(), ensure_ascii=False, indent=2))
    event_counts = collections.Counter(event.type for event in job.events)
    context_usage = job.context_usage or {}
    context_scope = context_usage.get("scope") or job.input_snapshot.get("contextScope", "current_only")
    history_sources = context_usage.get("historySources", [])
    history_count = context_usage.get("historyCount", job.input_snapshot.get("historyCount", 0))
    history_source_items = "\n".join(
        f"""
        <li>
          <b>{_safe_text(item.get("title", ""))}</b>
          <span>{_safe_text(item.get("sourceId", ""))} / {_safe_text(item.get("relevance", ""))}</span>
        </li>
        """
        for item in history_sources
    )
    if not history_source_items:
        history_source_items = "<li><b>未引用历史记录</b><span>本次建议默认优先当前对话。</span></li>"
    count_items = "\n".join(
        f"<div class=\"metric\"><b>{count}</b><span>{_safe_text(event_type)}</span></div>"
        for event_type, count in sorted(event_counts.items())
    )
    suggestion_cards = "\n".join(
        f"""
        <article class="suggestion-card">
          <div class="suggestion-number">{index:02d}</div>
          <h3>{_safe_text(suggestion.title)}</h3>
          <p>{_safe_text(suggestion.body)}</p>
          <div class="chips">
            <span>{_safe_text(suggestion.confidence)}</span>
            {"".join(f"<span>{_safe_text(item)}</span>" for item in suggestion.evidence[:2])}
          </div>
        </article>
        """
        for index, suggestion in enumerate(job.artifact.suggestions, start=1)
    )
    process_summary = "\n".join(
        f"""
        <div class="summary-step">
          <b>{item.round:02d}</b>
          <div>
            <h3>{_safe_text(item.title)}</h3>
            <p>{_safe_text(item.summary)}</p>
          </div>
        </div>
        """
        for item in job.artifact.process_summary
    )
    timeline_sections = "\n".join(
        f"""
        <section class="round-section" id="round-{round_number}">
          <div class="round-title">
            <span>{round_number:02d}</span>
            <h2>{_safe_text(title)}</h2>
          </div>
          <div class="expert-grid">
            {_event_cards(job, round_number, event_type)}
          </div>
        </section>
        """
        for round_number, title, event_type in [
            (1, ROUND_TITLES[1], "expert_message_added"),
            (2, ROUND_TITLES[2], "expert_challenge_added"),
            (3, ROUND_TITLES[3], "expert_revision_added"),
        ]
    )
    uncertainty_items = "\n".join(
        f"<li>{_safe_text(item)}</li>" for item in job.artifact.key_uncertainties
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_safe_text(transcript.title)} - 专家团时间轴</title>
  <style>
    :root {{
      --bg: #f5f7f8;
      --paper: #ffffff;
      --paper-soft: #f0f5f2;
      --ink: #151f1a;
      --muted: #65716b;
      --line: #d9e1dd;
      --accent: #136f4b;
      --accent-dark: #0d4f38;
      --accent-soft: #e1f0ea;
      --rose-soft: #f7e8ed;
      --amber-soft: #f5edda;
      --blue-soft: #e5eef7;
      --shadow: 0 18px 55px rgba(23, 35, 29, 0.08);
      --radius: 8px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      line-height: 1.65;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .layout {{
      display: grid;
      grid-template-columns: 292px minmax(0, 1fr);
      min-height: 100dvh;
    }}
    .side {{
      position: sticky;
      top: 0;
      height: 100dvh;
      border-right: 1px solid var(--line);
      background: rgba(255,255,255,0.82);
      backdrop-filter: blur(18px);
      padding: 28px 22px;
      overflow: auto;
    }}
    .brand {{ display: grid; gap: 8px; padding-bottom: 22px; border-bottom: 1px solid var(--line); }}
    .brand strong {{ font-size: 18px; }}
    .brand span {{ color: var(--muted); font-size: 13px; }}
    .nav {{ display: grid; gap: 6px; padding: 20px 0; }}
    .nav a {{ border-radius: var(--radius); color: var(--muted); font-size: 14px; padding: 9px 10px; }}
    .nav a:hover, .nav a.active {{ background: var(--accent-soft); color: var(--accent-dark); }}
    .side-meta {{ display: grid; gap: 10px; border-top: 1px solid var(--line); padding-top: 18px; color: var(--muted); font-size: 13px; }}
    .side-meta b {{ color: var(--ink); }}
    .main {{ padding: 42px min(6vw, 72px) 72px; }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 28px;
      align-items: end;
      max-width: 1220px;
      margin: 0 auto 26px;
    }}
    h1 {{ margin: 0; font-size: clamp(34px, 5vw, 64px); line-height: 1.08; letter-spacing: 0; }}
    .hero p {{ max-width: 760px; margin: 18px 0 0; color: #405047; font-size: 18px; }}
    .hero-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 22px;
    }}
    .hero-card dl {{ display: grid; gap: 14px; margin: 0; }}
    .hero-card div {{ display: flex; justify-content: space-between; gap: 14px; border-bottom: 1px solid var(--line); padding-bottom: 12px; }}
    .hero-card div:last-child {{ border-bottom: 0; padding-bottom: 0; }}
    dt {{ color: var(--muted); font-size: 13px; }}
    dd {{ margin: 0; font-weight: 700; text-align: right; }}
    .section, .round-section {{ max-width: 1220px; margin: 0 auto; padding: 34px 0; border-top: 1px solid var(--line); }}
    .section h2 {{ margin: 0 0 18px; font-size: clamp(24px, 3vw, 36px); line-height: 1.2; }}
    .brief {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .brief-map {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1px;
      background: var(--line);
    }}
    .map-cell {{ background: var(--paper); padding: 18px; }}
    .map-cell:nth-child(1) {{ background: #eef8f4; }}
    .map-cell:nth-child(2) {{ background: var(--amber-soft); }}
    .map-cell:nth-child(3) {{ background: var(--rose-soft); }}
    .map-cell:nth-child(4) {{ background: var(--blue-soft); }}
    .map-cell b {{ display: block; color: var(--accent-dark); font-size: 13px; margin-bottom: 8px; }}
    .map-cell p {{ margin: 0; color: #3e4d45; font-size: 14px; }}
    .overview {{ padding: 22px; font-size: 18px; color: #344139; }}
    .suggestions {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
    .suggestion-card {{ background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 20px; }}
    .suggestion-number {{ color: var(--accent-dark); font-size: 13px; font-weight: 800; margin-bottom: 10px; }}
    .suggestion-card h3 {{ margin: 0 0 10px; font-size: 20px; line-height: 1.35; }}
    .suggestion-card p {{ margin: 0; color: #3f4d45; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
    .chips span {{ border: 1px solid var(--line); background: var(--paper-soft); border-radius: 999px; color: #35443c; font-size: 12px; padding: 4px 9px; }}
    .process-summary {{ display: grid; gap: 12px; }}
    .summary-step {{ display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 18px; background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; }}
    .summary-step b {{ color: var(--accent-dark); font-size: 22px; }}
    .summary-step h3 {{ margin: 0 0 6px; font-size: 18px; }}
    .summary-step p {{ margin: 0; color: #3f4d45; }}
    .round-title {{ display: flex; align-items: baseline; gap: 12px; margin-bottom: 18px; }}
    .round-title span {{ color: var(--accent-dark); font-weight: 800; }}
    .round-title h2 {{ margin: 0; font-size: clamp(24px, 3vw, 34px); }}
    .expert-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; align-items: start; }}
    .expert-card {{ background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: 0 8px 26px rgba(23,35,29,0.045); overflow: hidden; }}
    .expert-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; border-bottom: 1px solid var(--line); background: var(--paper-soft); padding: 12px 14px; }}
    .expert-head span {{ font-weight: 800; }}
    .expert-head code {{ color: var(--muted); font-size: 12px; }}
    .expert-body {{ padding: 16px; color: #344139; font-size: 14px; }}
    .expert-body p {{ margin: 0 0 12px; }}
    .expert-body p:last-child {{ margin-bottom: 0; }}
    .judge-grid {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(300px, .9fr); gap: 18px; }}
    .judge-card, .plain-card {{ background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 20px; }}
    .judge-card h3, .plain-card h3 {{ margin: 0 0 12px; font-size: 20px; }}
    .judge-card p, .plain-card p {{ margin: 0; color: #3f4d45; }}
    .plain-card ul {{ display: grid; gap: 10px; margin: 0; padding-left: 20px; color: #3f4d45; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .metric {{ background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px; }}
    .metric b {{ display: block; color: var(--accent-dark); font-size: 22px; line-height: 1; margin-bottom: 8px; }}
    .metric span {{ color: var(--muted); font-size: 13px; word-break: break-word; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }}
    .button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 40px; border-radius: var(--radius); border: 1px solid var(--accent); background: var(--accent); color: #fff; font-size: 14px; font-weight: 750; padding: 8px 14px; cursor: pointer; }}
    .button.secondary {{ background: var(--paper); color: var(--accent-dark); }}
    .button:active {{ transform: translateY(1px); }}
    details {{ background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px 18px; }}
    summary {{ cursor: pointer; color: var(--accent-dark); font-weight: 800; }}
    pre {{ overflow: auto; margin: 16px 0 0; border-radius: var(--radius); background: #111a16; color: #dbe8e2; padding: 18px; font-size: 12px; line-height: 1.6; white-space: pre-wrap; }}
    .toast {{ position: fixed; right: 20px; bottom: 20px; opacity: 0; pointer-events: none; transform: translateY(8px); transition: opacity 160ms ease, transform 160ms ease; background: var(--ink); color: #fff; border-radius: var(--radius); padding: 10px 12px; font-size: 13px; }}
    .toast.show {{ opacity: 1; transform: translateY(0); }}
    @media (max-width: 1080px) {{
      .layout {{ display: block; }}
      .side {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      .nav {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .hero, .judge-grid {{ grid-template-columns: 1fr; }}
      .main {{ padding: 28px 18px 56px; }}
    }}
    @media (max-width: 820px) {{
      .brief-map, .suggestions, .expert-grid, .metrics {{ grid-template-columns: 1fr; }}
      .summary-step {{ grid-template-columns: 1fr; }}
      .hero-card div {{ display: grid; }}
      dd {{ text-align: left; }}
    }}
    @media (max-width: 560px) {{
      .nav {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
      .toast {{ transition: none; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="side">
      <div class="brand">
        <strong>AI 图文纪要</strong>
        <span>{_safe_text(transcript.title)}</span>
      </div>
      <nav class="nav" aria-label="页面目录">
        <a href="#summary">图文摘要</a>
        <a href="#suggestions">最终建议</a>
        <a href="#process">过程摘要</a>
        <a href="#context">上下文</a>
        <a href="#round-1">第一轮</a>
        <a href="#round-2">第二轮</a>
        <a href="#round-3">第三轮</a>
        <a href="#judge">裁判决策</a>
        <a href="#verification">测试报告</a>
      </nav>
      <div class="side-meta">
        <span>状态 <b>{_safe_text(job.status)}</b></span>
        <span>转写片段 <b>{len(transcript.segments)}</b></span>
        <span>事件 <b>{len(job.events)}</b></span>
        <span>专家 <b>{len(PARTICIPANT_LABELS)}</b></span>
        <span>历史引用 <b>{_safe_text(history_count)}</b></span>
      </div>
    </aside>

    <main class="main">
      <header class="hero">
        <div>
          <h1>{_safe_text(transcript.title)}</h1>
          <p>完整展示三轮专家输出、专家互评、修正意见和裁判决策，便于回看推理过程。</p>
          <div class="actions">
            <a class="button" href="./advice.md">查看 Markdown</a>
            <a class="button secondary" href="./test-report.md">查看测试报告</a>
          </div>
        </div>
        <div class="hero-card">
          <dl>
            <div><dt>创建时间</dt><dd>{_safe_text(transcript.created_at_text)}</dd></div>
            <div><dt>转写时长</dt><dd>{_safe_text(transcript.duration_text)}</dd></div>
            <div><dt>上下文范围</dt><dd>{_safe_text(context_scope)}</dd></div>
            <div><dt>模板</dt><dd>{_safe_text(job.template)}</dd></div>
            <div><dt>运行时</dt><dd>{_safe_text(job.artifact.model_trace.get("runtime", ""))}</dd></div>
          </dl>
        </div>
      </header>

      <section class="section" id="summary">
        <h2>图文摘要</h2>
        <div class="brief">
          <div class="brief-map">
            <div class="map-cell"><b>01 关键问题</b><p>外贸稳定路径与普拉提理想方向之间的取舍。</p></div>
            <div class="map-cell"><b>02 时间窗口</b><p>7月集中西语训练，8月进行外贸岗位验证。</p></div>
            <div class="map-cell"><b>03 风险提醒</b><p>务实路径可能带来情绪消耗，B计划不能停留在想象。</p></div>
            <div class="map-cell"><b>04 交付结果</b><p>三轮专家讨论后形成 3 条克制建议。</p></div>
          </div>
          <div class="overview">{_safe_text(job.artifact.overview)}</div>
        </div>
      </section>

      <section class="section" id="suggestions">
        <h2>最终建议</h2>
        <div class="suggestions">{suggestion_cards}</div>
      </section>

      <section class="section" id="process">
        <h2>过程摘要</h2>
        <div class="process-summary">{process_summary}</div>
      </section>

      <section class="section" id="context">
        <h2>上下文使用</h2>
        <div class="judge-grid">
          <article class="plain-card">
            <h3>本次范围</h3>
            <p>contextScope: {_safe_text(context_scope)}<br>historyCount: {_safe_text(history_count)}<br>profileIncluded: {_safe_text(context_usage.get("profileIncluded", False))}</p>
          </article>
          <article class="plain-card">
            <h3>历史来源</h3>
            <ul>{history_source_items}</ul>
          </article>
        </div>
      </section>

      <section class="section">
        <h2>专家团时间轴</h2>
        <p class="overview">下面是每一轮每个专家的完整输出。第一轮是初判，第二轮是互相挑战，第三轮是结合挑战后的修正。</p>
      </section>

      {timeline_sections}

      <section class="section" id="judge">
        <h2>裁判决策</h2>
        <div class="judge-grid">
          <article class="judge-card">
            <h3>裁判收敛</h3>
            <p>{_safe_text(job.artifact.overview)}</p>
          </article>
          <article class="plain-card">
            <h3>关键不确定性</h3>
            <ul>{uncertainty_items}</ul>
          </article>
          <article class="plain-card">
            <h3>安全边界</h3>
            <p>{_safe_text(job.artifact.safety_boundary)}</p>
          </article>
          <article class="plain-card">
            <h3>模型轨迹</h3>
            <p>runtime: {_safe_text(job.artifact.model_trace.get("runtime", ""))}<br>template: {_safe_text(job.artifact.model_trace.get("templateVersion", ""))}</p>
          </article>
        </div>
      </section>

      <section class="section" id="verification">
        <h2>测试报告</h2>
        <div class="metrics">
          <div class="metric"><b>{len(transcript.segments)}</b><span>转写片段</span></div>
          <div class="metric"><b>{len(job.events)}</b><span>normalized events</span></div>
          <div class="metric"><b>{len(job.artifact.suggestions)}</b><span>最终建议</span></div>
          {count_items}
        </div>
        <div class="actions">
          <a class="button" href="./test-report.md">打开完整报告</a>
          <a class="button secondary" href="./job.json">打开 job.json</a>
        </div>
      </section>

      <section class="section" id="raw">
        <h2>结构化数据</h2>
        <details>
          <summary>查看 artifact JSON</summary>
          <pre id="artifact-json">{artifact_json}</pre>
        </details>
        <div class="actions">
          <button class="button secondary" type="button" id="copy-json">复制 JSON 摘要</button>
        </div>
      </section>
    </main>
  </div>
  <div class="toast" id="toast" role="status" aria-live="polite">已复制</div>
  <script>
    const links = Array.from(document.querySelectorAll(".nav a"));
    const sections = links.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
    const activate = (id) => {{
      links.forEach((link) => {{
        link.classList.toggle("active", link.getAttribute("href") === "#" + id);
      }});
    }};
    const observer = new IntersectionObserver((entries) => {{
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) activate(visible.target.id);
    }}, {{ rootMargin: "-20% 0px -60% 0px", threshold: [0.05, 0.2, 0.5] }});
    sections.forEach((section) => observer.observe(section));
    if (sections[0]) activate(sections[0].id);

    const toast = document.getElementById("toast");
    document.getElementById("copy-json").addEventListener("click", async () => {{
      const text = document.getElementById("artifact-json").innerText;
      await navigator.clipboard.writeText(text);
      toast.classList.add("show");
      window.setTimeout(() => toast.classList.remove("show"), 1400);
    }});
  </script>
</body>
</html>"""
