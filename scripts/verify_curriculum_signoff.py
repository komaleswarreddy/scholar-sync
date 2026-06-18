#!/usr/bin/env python3
"""
Verify curriculum manual sign-off for ING-08 and RET-04 rubric artifacts.

Exits 0 when:
  - RET-04: all samples scored, supported rate >= 95%
  - ING-08: all samples scored, pass rate >= 90% (all four criteria per sample)

Writes evals/reports/curriculum_signoff_summary.json on success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RET04_PATH = ROOT / "evals" / "reports" / "ret04_rubric.json"
ING08_PATH = ROOT / "evals" / "reports" / "ing08_rubric_batch.json"
SUMMARY_PATH = ROOT / "evals" / "reports" / "curriculum_signoff_summary.json"

RET04_THRESHOLD = 0.95
ING08_THRESHOLD = 0.90
ING08_CRITERIA = (
    "complete_sentences",
    "semantic_coherence",
    "reasonable_overlap",
    "formula_equation_integrity",
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_ret04(data: dict) -> tuple[bool, str, dict]:
    samples = data.get("samples") or []
    errors = data.get("errors") or []
    if errors:
        return False, f"RET-04 export has {len(errors)} question errors — re-run export first", {}
    if not samples:
        return False, "RET-04 has no citation samples", {}

    unscored = [s for s in samples if s.get("claim_supported") is None]
    if unscored:
        return False, f"RET-04: {len(unscored)} samples missing claim_supported", {}

    supported = sum(1 for s in samples if s.get("claim_supported") is True)
    rate = supported / len(samples)
    meta = {
        "total_citations": len(samples),
        "supported": supported,
        "rate": round(rate, 4),
        "threshold": RET04_THRESHOLD,
        "pass": rate >= RET04_THRESHOLD,
    }
    if rate < RET04_THRESHOLD:
        return False, f"RET-04 support rate {rate:.1%} < {RET04_THRESHOLD:.0%}", meta
    return True, "RET-04 curriculum sign-off OK", meta


def _iter_ing08_samples(data: dict):
    if data.get("samples"):
        for sample in data["samples"]:
            yield sample
        return
    if data.get("chunks"):
        for sample in data["chunks"]:
            yield sample
        return
    for source in data.get("sources") or []:
        fixture = str(source.get("fixture_file") or "")
        for sample in source.get("samples") or []:
            preview = str(sample.get("text_preview") or "")
            if "encrypted" in fixture.lower() or "ENCRYPTED_SECRET" in preview:
                continue
            scores = sample.get("scores") or sample
            yield {
                "complete_sentences": scores.get("complete_sentences"),
                "semantic_coherence": scores.get("semantic_coherence"),
                "reasonable_overlap": scores.get("reasonable_overlap"),
                "formula_equation_integrity": scores.get("formula_equation_integrity"),
            }


def verify_ing08(data: dict) -> tuple[bool, str, dict]:
    samples = list(_iter_ing08_samples(data))
    if not samples:
        return False, "ING-08 has no chunk samples", {}

    passing = 0
    for sample in samples:
        missing = [c for c in ING08_CRITERIA if sample.get(c) is None]
        if missing:
            return False, f"ING-08 sample missing scores for: {', '.join(missing)}", {}
        if all(sample.get(c) in (1, True, "1", "pass") for c in ING08_CRITERIA):
            passing += 1

    rate = passing / len(samples)
    meta = {
        "total_samples": len(samples),
        "passing": passing,
        "rate": round(rate, 4),
        "threshold": ING08_THRESHOLD,
        "pass": rate >= ING08_THRESHOLD,
    }
    if rate < ING08_THRESHOLD:
        return False, f"ING-08 pass rate {rate:.1%} < {ING08_THRESHOLD:.0%}", meta
    return True, "ING-08 curriculum sign-off OK", meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ret04", default=str(RET04_PATH))
    parser.add_argument("--ing08", default=str(ING08_PATH))
    parser.add_argument("--skip-ing08", action="store_true")
    parser.add_argument("--skip-ret04", action="store_true")
    args = parser.parse_args()

    summary: dict = {"ret04": None, "ing08": None, "overall_pass": False}
    ok = True

    if not args.skip_ret04:
        try:
            ret04_data = _load_json(Path(args.ret04))
            ret_ok, ret_msg, ret_meta = verify_ret04(ret04_data)
            summary["ret04"] = {"ok": ret_ok, "message": ret_msg, **ret_meta}
            print(ret_msg)
            ok = ok and ret_ok
        except FileNotFoundError as exc:
            print(str(exc))
            ok = False

    if not args.skip_ing08:
        try:
            ing08_data = _load_json(Path(args.ing08))
            ing_ok, ing_msg, ing_meta = verify_ing08(ing08_data)
            summary["ing08"] = {"ok": ing_ok, "message": ing_msg, **ing_meta}
            print(ing_msg)
            ok = ok and ing_ok
        except FileNotFoundError as exc:
            print(str(exc))
            ok = False

    summary["overall_pass"] = ok
    if ok:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote {SUMMARY_PATH}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
