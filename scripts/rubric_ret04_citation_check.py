#!/usr/bin/env python3
"""
RET-04 citation correctness rubric exporter.

Collects chat responses with citations for manual verification.
Target: >=95% citations support their claims.

Usage:
  NOTEBOOKLM_API_URL=http://127.0.0.1:8000 python scripts/rubric_ret04_citation_check.py \\
    --source-id <uuid> --questions questions.txt --output evals/reports/ret04_rubric.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.chat_client import stream_chat  # noqa: E402


def _load_resume_state(out_path: Path) -> tuple[list[dict], list[dict[str, str]], set[str]]:
    if not out_path.exists():
        return [], [], set()
    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], [], set()
    rows = list(data.get("samples") or [])
    errors = list(data.get("errors") or [])
    done = {r["question"] for r in rows if r.get("question")}
    return rows, errors, done


def _write_payload(
    out_path: Path,
    *,
    questions: list[str],
    rows: list[dict],
    errors: list[dict[str, str]],
    done: set[str],
) -> None:
    succeeded = done
    with_citations = {r["question"] for r in rows if r.get("question") and r.get("citation_text")}
    payload = {
        "test_id": "RET-04",
        "pass_threshold": 0.95,
        "questions_attempted": len(questions),
        "questions_succeeded": len(succeeded),
        "questions_with_citations": len(with_citations),
        "samples": rows,
        "errors": errors,
        "instructions": "For each row verify the answer claim is contained in or directly supported by citation_text.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", default="ret_eval_user")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--questions", required=True, help="Text file, one question per line")
    parser.add_argument("--output", default="evals/reports/ret04_rubric.json")
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=500,
        help="Pause between questions to reduce thundering herd (default 500ms).",
    )
    parser.add_argument(
        "--stream-timeout",
        type=float,
        default=300.0,
        help="Per-question SSE timeout in seconds (default 300).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip questions that already have citation samples in --output.",
    )
    args = parser.parse_args()

    raw_lines = Path(args.questions).read_text(encoding="utf-8").splitlines()
    raw_lines = [q.strip() for q in raw_lines if q.strip()]
    questions: list[str] = []
    seen_q: set[str] = set()
    for q in raw_lines:
        if q not in seen_q:
            seen_q.add(q)
            questions.append(q)
    if len(questions) < len(raw_lines):
        print(f"Deduped questions: {len(raw_lines)} lines -> {len(questions)} unique")
    token = make_dev_jwt(args.user_id)
    out = Path(args.output)

    rows, errors, done = _load_resume_state(out) if args.resume else ([], [], set())
    question_set = set(questions)
    errors = [e for e in errors if e.get("question") in question_set]
    if args.resume and done:
        errors = [e for e in errors if e.get("question") not in done]
        print(f"Resume: skipping {len(done)} questions with existing samples")

    import time

    stream_timeout = httpx.Timeout(args.stream_timeout, connect=30.0)
    with httpx.Client(timeout=stream_timeout) as client:
        for idx, q in enumerate(questions):
            if q in done:
                continue
            if idx > 0 and args.delay_ms > 0:
                time.sleep(args.delay_ms / 1000.0)
            chat = None
            last_error = ""
            for attempt in range(3):
                try:
                    chat = stream_chat(
                        client,
                        base_url=args.base_url,
                        token=token,
                        message=q,
                        active_source_ids=[args.source_id],
                        timeout=args.stream_timeout,
                    )
                    if chat.error:
                        last_error = chat.error
                        chat = None
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                            continue
                        break
                    break
                except httpx.HTTPStatusError as exc:
                    last_error = str(exc)
                    if exc.response.status_code in {500, 502, 503, 429} and attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    break
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RequestError) as exc:
                    last_error = str(exc)
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    break
            if chat is None:
                if last_error:
                    errors = [e for e in errors if e.get("question") != q]
                    errors.append({"question": q, "error": last_error})
                _write_payload(out, questions=questions, rows=rows, errors=errors, done=done)
                continue
            errors = [e for e in errors if e.get("question") != q]
            if not chat.citations:
                errors.append(
                    {
                        "question": q,
                        "error": "Chat completed but returned no citations",
                    }
                )
                _write_payload(out, questions=questions, rows=rows, errors=errors, done=done)
                print(f"  [{len(done)}/{len(questions)}] NO_CITATIONS: {q[:60]}...")
                continue
            done.add(q)
            for citation in chat.citations:
                rows.append(
                    {
                        "question": q,
                        "answer_excerpt": chat.text[:400],
                        "citation_index": citation.get("index"),
                        "citation_text": (citation.get("text") or "")[:500],
                        "claim_supported": None,
                        "contradicts_claim": None,
                        "reviewer_notes": "",
                    }
                )
            _write_payload(out, questions=questions, rows=rows, errors=errors, done=done)
            print(f"  [{len(done)}/{len(questions)}] OK: {q[:60]}...")

    succeeded = len(done)
    print(
        f"Wrote {len(rows)} citation rows to {out} "
        f"({succeeded}/{len(questions)} questions OK, {len(errors)} errors)"
    )
    if errors:
        return 1
    if succeeded < len(questions):
        return 1
    if not rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
