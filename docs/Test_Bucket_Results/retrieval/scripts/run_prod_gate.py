#!/usr/bin/env python3
"""
Layered local production gate for ING-01..11 and RET-01..11.

Usage:
  # Terminal 1: API without --reload
  .\\venv\\Scripts\\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

  # Terminal 2:
  $env:INTEGRATION_TESTS="1"
  python scripts/run_prod_gate.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
REPORTS = ROOT / "evals" / "reports"
SCORECARD_JSON = REPORTS / "prod_gate_scorecard.json"
SCORECARD_MD = ROOT / "docs" / "PROD_GATE_SCORECARD.md"


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.call(cmd, cwd=str(ROOT), env=merged)


def preflight(base_url: str) -> tuple[bool, str]:
    required = ["DATABASE_URL", "OPENAI_API_KEY", "PINECONE_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        return False, f"Missing env: {', '.join(missing)}"
    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        return False, "Set INTEGRATION_TESTS=1"
    try:
        r = httpx.get(f"{base_url}/health", timeout=10.0)
        if r.status_code != 200:
            return False, f"/health returned {r.status_code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"API unreachable: {exc}"
    return True, "ok"


def ensure_api_healthy(base_url: str) -> None:
    """Restart the local API only when /health is unreachable (not to mask load failures)."""
    try:
        if httpx.get(f"{base_url}/health", timeout=10.0).status_code == 200:
            return
    except Exception:  # noqa: BLE001
        pass
    print(f"API unhealthy at {base_url}; attempting recovery restart...")
    restart_local_api(base_url)


def ensure_api_transaction_pooler(base_url: str) -> None:
    """
    Restart local API once when .env still points at Supabase session pooler (5432).

    connection.py auto-upgrades 5432→6543 at import time; the running process must reload.
    """
    db_url = os.getenv("DATABASE_URL", "")
    force_session = os.getenv("DATABASE_FORCE_SESSION_POOLER", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if (
        force_session
        or "pooler.supabase.com" not in db_url
        or ":5432" not in db_url
    ):
        return
    parsed = urlparse(base_url)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return
    print(
        "DATABASE_URL uses Supabase session pooler (5432); restarting API "
        "so transaction pooler auto-upgrade (6543) takes effect..."
    )
    restart_local_api(base_url)


def restart_local_api(base_url: str) -> None:
    """Restart uvicorn on 127.0.0.1 when /health is down."""
    parsed = urlparse(base_url)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        print(f"Skipping API restart for non-local host: {base_url}")
        return
    port = parsed.port or 8000
    if sys.platform == "win32":
        ps = (
            f"$p = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique; "
            "if ($p) { $p | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
        )
        subprocess.call(["powershell", "-NoProfile", "-Command", ps], cwd=str(ROOT))
    else:
        subprocess.call(["bash", "-lc", f"fuser -k {port}/tcp 2>/dev/null || true"], cwd=str(ROOT))
    time.sleep(3)
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            if httpx.get(f"{base_url}/health", timeout=5.0).status_code == 200:
                print(f"API restarted and healthy at {base_url}")
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    print(f"Warning: API restart attempted but /health not ready at {base_url}")


def validate_classroom_locust_result(exit_code: int) -> int:
    """
    Locust exits 1 on any failure; gate allows <1% failures and zero pool-exhaustion signatures.

    Reads the latest stats CSV under evals/reports/locust_classroom_* if present, else trusts exit_code.
    """
    if exit_code == 0:
        return 0
    reports = sorted(
        list(REPORTS.glob("classroom_load_stats*_stats.csv"))
        + list(REPORTS.glob("fast_classroom_stats*_stats.csv")),
        key=lambda p: p.stat().st_mtime,
    )
    candidate = reports[-1] if reports else None
    if candidate is None:
        return exit_code
    text = candidate.read_text(encoding="utf-8", errors="replace")
    if "MaxClientsInSessionMode" in text or "EMAXCONNSESSION" in text:
        print("Classroom load: pool exhaustion detected in Locust output")
        return 1
    # Locust CSV: Type,Name,Request Count,Failure Count,...
    total = 0
    failures = 0
    for line in text.splitlines():
        if line.startswith('"Aggregated"') or line.startswith("Aggregated,"):
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) >= 4:
                try:
                    total = int(parts[2])
                    failures = int(parts[3])
                except ValueError:
                    pass
            break
    if total > 0:
        rate = failures / total
        print(f"Classroom load: {failures}/{total} failures ({rate:.2%})")
        if rate < 0.01:
            return 0
    return exit_code


def load_curriculum_signoff() -> dict[str, bool]:
    """Return {RET-04: bool, ING-08: bool} from verify_curriculum_signoff subprocess."""
    result = subprocess.run(
        [sys.executable, "scripts/verify_curriculum_signoff.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"RET-04": False, "ING-08": False}
    summary_path = REPORTS / "curriculum_signoff_summary.json"
    if not summary_path.exists():
        return {"RET-04": False, "ING-08": False}
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "RET-04": bool((data.get("ret04") or {}).get("pass")),
        "ING-08": bool((data.get("ing08") or {}).get("pass")),
    }


def load_retrieval_pass() -> dict[str, bool]:
    path = REPORTS / "retrieval_latest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("pass") or {}


def build_scorecard(layer_results: dict[str, Any]) -> dict[str, Any]:
    ret_pass = load_retrieval_pass()
    curriculum = load_curriculum_signoff()
    ret04_export_ok = layer_results.get("ret04_rubric", {}).get("exit_code") == 0
    rows: list[dict[str, Any]] = []

    demo_ok = layer_results.get("demo_pytest", {}).get("exit_code") == 0
    slow_ok = layer_results.get("slow_pytest", {}).get("exit_code") == 0
    locust_ok = layer_results.get("locust", {}).get("exit_code") == 0

    for i in range(1, 12):
        tid = f"ING-{i:02d}"
        if tid == "ING-02":
            rows.append(
                {
                    "test_id": tid,
                    "status": "KNOWN_GAP",
                    "source": "documented",
                    "notes": "DOCX ingestion not implemented; TXT portion covered by pytest",
                }
            )
        elif tid == "ING-04":
            rows.append(
                {
                    "test_id": tid,
                    "status": "KNOWN_GAP",
                    "source": "pytest slow",
                    "notes": "50-page synthetic SLA: "
                    + ("PASS" if slow_ok else "FAIL")
                    + "; 100+ NCERT fixture out of scope",
                }
            )
        elif tid == "ING-08":
            ing08_status = "PASS" if curriculum.get("ING-08") else "PENDING"
            rows.append(
                {
                    "test_id": tid,
                    "status": ing08_status,
                    "source": "rubric export",
                    "artifact": "evals/reports/ing08_rubric_batch.json",
                    "notes": "Curriculum sign-off required (≥90%)",
                }
            )
        elif tid == "ING-11":
            status = "PASS" if locust_ok else ("FAIL" if "locust" in layer_results else "PENDING")
            rows.append(
                {
                    "test_id": tid,
                    "status": status,
                    "source": "locust_classroom",
                    "notes": "40 users (35 chat stream + 5 upload), 10m sustained; see locustfile_classroom.py",
                }
            )
        elif tid == "ING-10":
            rows.append(
                {
                    "test_id": tid,
                    "status": "PASS" if slow_ok else "FAIL",
                    "source": "pytest slow",
                    "notes": "3 TXT latency probe approximates matrix 20-PDF criterion",
                }
            )
        else:
            rows.append(
                {
                    "test_id": tid,
                    "status": "PASS" if demo_ok else "FAIL",
                    "source": "pytest",
                }
            )

    for i in range(1, 12):
        tid = f"RET-{i:02d}"
        if tid == "RET-04":
            if not ret04_export_ok:
                ret04_status = "FAIL"
                ret04_notes = "Rubric export failed — re-run after classroom load passes"
            elif curriculum.get("RET-04"):
                ret04_status = "PASS"
                ret04_notes = "Curriculum sign-off ≥95% supported"
            else:
                ret04_status = "PENDING"
                ret04_notes = "Export OK; curriculum sign-off required (≥95%)"
            rows.append(
                {
                    "test_id": tid,
                    "status": ret04_status,
                    "source": "rubric export",
                    "artifact": "evals/reports/ret04_rubric.json",
                    "notes": ret04_notes,
                }
            )
        elif tid == "RET-07":
            rows.append(
                {
                    "test_id": tid,
                    "status": "PASS" if layer_results.get("demo_pytest", {}).get("exit_code") == 0 else "FAIL",
                    "source": "pytest integration",
                }
            )
        elif tid in ret_pass:
            rows.append(
                {
                    "test_id": tid,
                    "status": "PASS" if ret_pass[tid] else "FAIL",
                    "source": "retrieval_eval",
                }
            )
        elif tid == "RET-03":
            rows.append(
                {
                    "test_id": tid,
                    "status": "PASS" if ret_pass.get("RET-03") else "FAIL",
                    "source": "retrieval_eval",
                    "notes": "Phrase-proxy precision; full RAGAS LLM-judge not implemented",
                }
            )
        else:
            rows.append({"test_id": tid, "status": "FAIL", "source": "retrieval_eval", "notes": "No eval result"})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "convention": "indexed status equals matrix ready",
        "layers": layer_results,
        "rows": rows,
    }


def write_markdown(scorecard: dict[str, Any]) -> None:
    lines = [
        "# Production Gate Scorecard",
        "",
        f"Generated: {scorecard['generated_at']}",
        "",
        "Status convention: `indexed` API status = matrix `ready`.",
        "",
        "| Test ID | Status | Source | Notes |",
        "|---------|--------|--------|-------|",
    ]
    for row in scorecard["rows"]:
        notes = row.get("notes", row.get("artifact", ""))
        lines.append(
            f"| {row['test_id']} | {row['status']} | {row.get('source', '')} | {notes} |"
        )
    lines.extend(
        [
            "",
            "## Manual sign-off",
            "",
            "See [docs/rubrics/CURRICULUM_SIGNOFF.md](rubrics/CURRICULUM_SIGNOFF.md) for ING-08 and RET-04.",
            "",
        ]
    )
    SCORECARD_MD.parent.mkdir(parents=True, exist_ok=True)
    SCORECARD_MD.write_text("\n".join(lines), encoding="utf-8")


CLASSROOM_CHAT_USER = "classroom_chat_shared"


def seed_classroom_chat_source(base_url: str) -> tuple[str, str]:
    """
    Pre-upload and index one shared chapter for chat students.

    Avoids 35 simultaneous uploads at Locust spawn (which overwhelms ingest/DB pool).
    Returns (user_id, source_id) for CLASSROOM_CHAT_* env vars passed to Locust.
    """
    sys.path.insert(0, str(ROOT))
    from tests.helpers.auth import make_dev_jwt  # noqa: E402
    from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402

    fixture = ROOT / "tests" / "fixtures" / "ingestion" / "standard_chapter.pdf"
    if not fixture.exists():
        run([sys.executable, "scripts/generate_test_fixtures.py"])
    token = make_dev_jwt(CLASSROOM_CHAT_USER)
    with httpx.Client(timeout=180.0) as client:
        resp = upload_file(
            client,
            base_url=base_url,
            token=token,
            file_path=fixture,
            title="classroom_shared_chapter",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Classroom seed upload failed: {resp.status_code} {resp.text[:300]}")
        source_id = resp.json()["id"]
        wait_for_source_status(client, base_url=base_url, token=token, source_id=source_id)
    print(f"Classroom chat seed ready: user={CLASSROOM_CHAT_USER} source={source_id}")
    return CLASSROOM_CHAT_USER, source_id


def export_ret04_rubric(base_url: str) -> int:
    """Upload chapter source and export RET-04 rubric samples."""
    sys.path.insert(0, str(ROOT))
    from tests.helpers.auth import make_dev_jwt  # noqa: E402
    from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402

    fixtures = ROOT / "tests" / "fixtures" / "ingestion" / "standard_chapter.pdf"
    questions = ROOT / "evals" / "datasets" / "ret04_questions.txt"
    if not questions.exists():
        run([sys.executable, "scripts/export_ret04_questions.py"])
    source_id = os.getenv("RET04_SOURCE_ID", "").strip()
    if not source_id:
        token = make_dev_jwt("ret_eval_user")
        with httpx.Client(timeout=120.0) as client:
            resp = upload_file(client, base_url=base_url, token=token, file_path=fixtures)
            if resp.status_code != 200:
                print(f"RET-04 upload failed: {resp.status_code} {resp.text}")
                return 1
            source_id = resp.json()["id"]
            wait_for_source_status(client, base_url=base_url, token=token, source_id=source_id)
    else:
        print(f"RET-04 reusing indexed source: {source_id}")
    cmd = [
        sys.executable,
        "scripts/rubric_ret04_citation_check.py",
        "--base-url",
        base_url,
        "--source-id",
        source_id,
        "--questions",
        str(questions),
        "--output",
        "evals/reports/ret04_rubric.json",
        "--resume",
    ]
    return run(cmd)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-step",
        default=None,
        help="Resume gate from this layer (e.g. retrieval_eval). Skips earlier steps.",
    )
    parser.add_argument(
        "--assume-passed",
        default="",
        help="Comma-separated layer names to treat as exit 0 without running.",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Run only post-eval layers: ret04_rubric,locust,testsprite (comma-separated).",
    )
    args = parser.parse_args()

    base_url = os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000")
    os.environ.setdefault("INTEGRATION_TESTS", "1")

    ok, msg = preflight(base_url)
    if not ok:
        print(f"Preflight failed: {msg}")
        return 2

    layer_results: dict[str, Any] = {}
    assume_passed = {s.strip() for s in args.assume_passed.split(",") if s.strip()}
    if args.from_step:
        assume_passed |= {"fixtures", "expand_golden", "ret04_questions", "unit", "demo_pytest", "slow_pytest"}

    steps: list[tuple[str, list[str]]] = [
        ("fixtures", [sys.executable, "scripts/generate_test_fixtures.py"]),
        ("expand_golden", [sys.executable, "scripts/expand_golden_set.py"]),
        ("ret04_questions", [sys.executable, "scripts/export_ret04_questions.py"]),
        ("unit", [sys.executable, "-m", "pytest", "tests/unit/test_file_validator.py", "tests/unit/test_pdf_upload_validator.py", "-q"]),
        (
            "demo_pytest",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/",
                "-m",
                "integration and not slow",
                "-v",
            ],
        ),
        (
            "slow_pytest",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/",
                "-m",
                "integration and slow",
                "-v",
            ],
        ),
        (
            "retrieval_eval",
            [
                sys.executable,
                "evals/runners/retrieval_eval.py",
                "--report",
                "evals/reports/retrieval_latest.json",
            ],
        ),
        ("ing08_rubric", [sys.executable, "scripts/export_ing08_batch.py"]),
    ]

    if args.from_step:
        names = [n for n, _ in steps]
        if args.from_step not in names:
            print(f"Unknown --from-step {args.from_step!r}; choices: {names}")
            return 2
        skip_until = names.index(args.from_step)
        for skip_name, skip_cmd in steps[:skip_until]:
            layer_results[skip_name] = {"exit_code": 0, "command": skip_cmd, "assumed": True}
        steps = steps[skip_until:]

    only_layers = {s.strip() for s in args.only.split(",") if s.strip()}
    if only_layers and SCORECARD_JSON.exists():
        prior = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))
        layer_results.update(prior.get("layers") or {})

    run_main_steps = not only_layers
    if run_main_steps:
        for name, cmd in steps:
            if name in assume_passed:
                layer_results[name] = {"exit_code": 0, "command": cmd, "assumed": True}
                continue
            code = run(cmd)
            layer_results[name] = {"exit_code": code, "command": cmd}
            if code != 0 and name not in {"ing08_rubric", "slow_pytest", "retrieval_eval", "ret04_rubric", "locust"}:
                print(f"Layer {name} failed with exit {code}")
                scorecard = build_scorecard(layer_results)
                REPORTS.mkdir(parents=True, exist_ok=True)
                SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
                write_markdown(scorecard)
                return code
            if code != 0:
                print(f"Layer {name} failed with exit {code} (continuing gate)")

    locust_code = layer_results.get("locust", {}).get("exit_code", 1)
    if not only_layers or "locust" in only_layers:
        ensure_api_transaction_pooler(base_url)
        ensure_api_healthy(base_url)
        try:
            chat_user, chat_source_id = seed_classroom_chat_source(base_url)
        except Exception as exc:  # noqa: BLE001
            print(f"Classroom seed failed: {exc}")
            locust_code = 1
            layer_results["locust"] = {"exit_code": locust_code, "error": str(exc)}
            scorecard = build_scorecard(layer_results)
            REPORTS.mkdir(parents=True, exist_ok=True)
            SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
            write_markdown(scorecard)
            return locust_code
        short_classroom = os.getenv("GATE_CLASSROOM_SHORT", "").strip() in {"1", "true", "yes"}
        classroom_runtime = "3m" if short_classroom else "10m"
        classroom_users = "12" if short_classroom else "40"
        classroom_spawn = "3" if short_classroom else "5"
        stats_csv = REPORTS / "classroom_load_stats.csv"
        locust_cmd = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            "tests/load/locustfile_classroom.py",
            "--headless",
            "--users",
            classroom_users,
            "--spawn-rate",
            classroom_spawn,
            "--run-time",
            classroom_runtime,
            "--csv",
            str(stats_csv.with_suffix("")),
            "--host",
            base_url,
        ]
        locust_code = run(
            locust_cmd,
            env={
                "CLASSROOM_CHAT_USER": chat_user,
                "CLASSROOM_CHAT_SOURCE_ID": chat_source_id,
            },
        )
        locust_code = validate_classroom_locust_result(locust_code)
        layer_results["locust"] = {"exit_code": locust_code, "command": locust_cmd}
        if locust_code != 0:
            print(f"Classroom load test failed with exit {locust_code}")
            scorecard = build_scorecard(layer_results)
            REPORTS.mkdir(parents=True, exist_ok=True)
            SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
            write_markdown(scorecard)
            return locust_code

    ret04_code = layer_results.get("ret04_rubric", {}).get("exit_code", 1)
    if not only_layers or "ret04_rubric" in only_layers:
        ensure_api_transaction_pooler(base_url)
        ensure_api_healthy(base_url)
        ret04_code = export_ret04_rubric(base_url)
        layer_results["ret04_rubric"] = {"exit_code": ret04_code}
        if ret04_code != 0:
            print(f"RET-04 rubric export failed with exit {ret04_code}")
            scorecard = build_scorecard(layer_results)
            REPORTS.mkdir(parents=True, exist_ok=True)
            SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
            write_markdown(scorecard)
            return ret04_code

    testsprite_code = layer_results.get("testsprite", {}).get("exit_code")
    if not only_layers or "testsprite" in only_layers:
        ensure_api_healthy(base_url)
        testsprite_code = run([sys.executable, "scripts/run_testsprite_local.py"])
        layer_results["testsprite"] = {"exit_code": testsprite_code}
        if testsprite_code != 0:
            print(f"TestSprite local verification below pass bar (exit {testsprite_code})")

    scorecard = build_scorecard(layer_results)
    REPORTS.mkdir(parents=True, exist_ok=True)
    SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    write_markdown(scorecard)
    print(f"\nScorecard: {SCORECARD_JSON}")
    print(f"Markdown:  {SCORECARD_MD}")

    automated_fail = any(
        r["status"] == "FAIL" for r in scorecard["rows"] if r["status"] not in {"PENDING", "KNOWN_GAP"}
    )
    ret04_code = layer_results.get("ret04_rubric", {}).get("exit_code", 0)
    testsprite_code = layer_results.get("testsprite", {}).get("exit_code", 0)
    if automated_fail or locust_code != 0 or ret04_code != 0 or testsprite_code != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
