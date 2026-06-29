from __future__ import annotations

import argparse
import json
from pathlib import Path

from .deliberation import DeliberationService
from .providers import provider_from_env
from .reports import render_advice_markdown, render_html_report, render_test_report
from .transcript import parse_markdown_transcript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an Emotion Talk deliberation job.")
    parser.add_argument("input", help="Path to a DingTalk-style markdown transcript.")
    parser.add_argument("--output-dir", default="outputs/deliberation/latest")
    parser.add_argument("--provider", default="deepseek", choices=["deepseek", "heuristic"])
    parser.add_argument("--source-type", default="recording")
    parser.add_argument("--source-id", default="dev-recording")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input).expanduser()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown = input_path.read_text(encoding="utf-8")
    transcript = parse_markdown_transcript(markdown)
    provider = provider_from_env(args.provider)
    job = DeliberationService(provider=provider).run_from_transcript(
        transcript,
        source_type=args.source_type,
        source_id=args.source_id,
    )

    (output_dir / "job.json").write_text(
        json.dumps(job.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "advice.md").write_text(render_advice_markdown(job), encoding="utf-8")
    report = render_test_report(
        transcript=transcript,
        job=job,
        source_path=str(input_path),
        verification={
            "cli_real_run": f"provider={args.provider}",
            "job_status": job.status,
            "event_count": len(job.events),
        },
    )
    (output_dir / "test-report.md").write_text(report, encoding="utf-8")
    (output_dir / "index.html").write_text(
        render_html_report(transcript=transcript, job=job),
        encoding="utf-8",
    )

    print(f"job_id={job.job_id}")
    print(f"status={job.status}")
    print(f"output_dir={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
