#!/usr/bin/env python3
"""
Cross-verify Agents 17-22 questions against Problem solver_Questions bank.

Emits a checklist markdown report and exits non-zero on hard failures.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
REPORT_PATH = SCRIPTS / "problem_solver_provenance_checklist.md"

PDF_ROOT = ROOT / "Problem solver_Questions"
ALLOWED_PDFS = {p.name for p in PDF_ROOT.rglob("*.pdf")} if PDF_ROOT.exists() else set()

SOURCE_KEY_TO_PDF = {
    "cbse_biology": "Biology_Testing_Question_Bank_Updated.pdf",
    "cbse_mathematics": "Mathematics_Testing_Question_Bank.pdf",
    "cbse_physics": "Physics_testing_Question_Bank.pdf",
    "jee_april_2026": "Mains 2026 April.pdf",
    "jee_jan_2026": "Mains 2026 Jan.pdf",
    "neet_botany": "Botany.pdf",
    "neet_chemistry": "Chemistry.pdf",
    "neet_physics": "Physics.pdf",
    "neet_zoology": "Zoology.pdf",
}


def normalize(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip().lower())
    s = re.sub(r"^q\d+\.\s*", "", s)
    return s


def jaccard(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", normalize(a)))
    tb = set(re.findall(r"[a-z0-9]+", normalize(b)))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_bank_index() -> dict[str, dict]:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in bank["questions"]}
    by_norm: dict[str, dict] = {}
    for q in bank["questions"]:
        by_norm[normalize(q["problem_text_normalized"])] = q
    return {"by_id": by_id, "by_norm": by_norm, "questions": bank["questions"]}


def parse_md_examples(text: str) -> list[dict[str, str]]:
    block = text[text.find("## 17."):]
    examples = []
    headers = list(re.finditer(r"#### Example \d+: `(?P<id>[\w-]+)`", block))
    for i, hm in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(block)
        chunk = block[hm.start():end]
        ex_id = hm.group("id")
        prob_m = re.search(r"\*\*Problem Text Normalized:\*\*\s*\n\n(.+?)\n\n\*\*", chunk, re.S)
        if not prob_m:
            continue
        examples.append({"example_id": ex_id, "problem_text": prob_m.group(1).strip()})
    return examples


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    checklist: list[str] = [
        "# Problem Solver Agents 17-22 — Provenance Checklist",
        "",
    ]

    if not BANK_PATH.exists():
        print(f"Missing bank: {BANK_PATH}", file=sys.stderr)
        return 1
    if not POOL_PATH.exists():
        print(f"Missing pool: {POOL_PATH}", file=sys.stderr)
        return 1

    bank_idx = load_bank_index()
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    pool_items = {it["example_id"]: it for it in pool["items"]}

    # --- Checklist section 1: PDF catalog ---
    checklist.append("## 1. Source PDF catalog")
    checklist.append("")
    checklist.append(f"- [ ] All 9 PDFs present under `Problem solver_Questions/`")
    for sk, pdf in sorted(SOURCE_KEY_TO_PDF.items()):
        ok = pdf in ALLOWED_PDFS
        checklist.append(f"- [{'x' if ok else ' '}] `{pdf}` ({sk})")
        if not ok:
            failures.append(f"Missing PDF: {pdf}")
    checklist.append("")

    # --- Section 2: Pool vs bank ---
    checklist.append("## 2. Eval pool (165) vs question bank")
    checklist.append("")
    bank_hits = 0
    for it in pool["items"]:
        pid = it["id"]
        norm = normalize(it["problem_text_normalized"])
        bank_q = bank_idx["by_id"].get(pid) or bank_idx["by_norm"].get(norm)
        if bank_q:
            bank_hits += 1
            sim = jaccard(it["problem_text_normalized"], bank_q["problem_text_normalized"])
            if sim < 0.85:
                warnings.append(f"{it['example_id']}: low similarity to bank id {pid} ({sim:.2f})")
        else:
            best_sim = max(
                (jaccard(it["problem_text_normalized"], q["problem_text_normalized"]) for q in bank_idx["questions"]),
                default=0.0,
            )
            if best_sim >= 0.85:
                warnings.append(f"{it['example_id']}: not matched by id but fuzzy bank hit ({best_sim:.2f})")
            else:
                failures.append(f"{it['example_id']}: not found in question bank (best_sim={best_sim:.2f})")
    checklist.append(f"- [{'x' if bank_hits == 165 else ' '}] 165/165 pool items traceable to bank ({bank_hits}/165)")
    checklist.append("")

    # --- Section 3: source_key / PDF mapping ---
    checklist.append("## 3. source_key → PDF mapping")
    checklist.append("")
    for it in pool["items"]:
        sk = it["source_key"]
        pdf = SOURCE_KEY_TO_PDF.get(sk, "")
        if it["source_pdf"] != pdf:
            failures.append(f"{it['example_id']}: source_pdf {it['source_pdf']} != expected {pdf}")
    checklist.append(f"- [{'x' if not any('source_pdf' in f for f in failures) else ' '}] All source_key maps to correct PDF filename")
    checklist.append("")

    # --- Section 4: LLM gold coverage ---
    checklist.append("## 4. Production LLM gold")
    checklist.append("")
    llm_count = sum(1 for it in pool["items"] if it.get("gold_source") == "production_llm" and it.get("llm_gold"))
    checklist.append(f"- [{'x' if llm_count == 165 else ' '}] 165/165 examples have `production_llm` gold ({llm_count}/165)")
    if llm_count < 165:
        warnings.append(f"Only {llm_count}/165 have production LLM gold — run generate_problem_solver_llm_gold.py")
    checklist.append("")

    # --- Section 5: Complete_Agent_DataSet.md vs pool ---
    checklist.append("## 5. Complete_Agent_DataSet.md vs eval pool")
    checklist.append("")
    if MD.exists():
        md_examples = parse_md_examples(MD.read_text(encoding="utf-8"))
        md_norms = [normalize(e["problem_text"]) for e in md_examples]
        if len(md_examples) != 165:
            failures.append(f"MD has {len(md_examples)} problem examples in 17-22, expected 165")
        if len(md_norms) != len(set(md_norms)):
            failures.append(f"Duplicate problem texts in MD: {len(md_norms) - len(set(md_norms))}")
        pool_norms = {normalize(it["problem_text_normalized"]) for it in pool["items"]}
        md_set = set(md_norms)
        if md_set != pool_norms:
            only_md = len(md_set - pool_norms)
            only_pool = len(pool_norms - md_set)
            if only_md or only_pool:
                failures.append(f"MD/pool mismatch: only_in_md={only_md}, only_in_pool={only_pool}")
        for ex in md_examples:
            if ex["example_id"] not in pool_items:
                failures.append(f"MD example {ex['example_id']} not in pool")
        checklist.append(f"- [{'x' if len(md_examples) == 165 else ' '}] 165 examples in markdown")
        checklist.append(f"- [{'x' if len(md_norms) == len(set(md_norms)) else ' '}] Unique problem texts in markdown")
        checklist.append(f"- [{'x' if md_set == pool_norms else ' '}] Markdown matches eval pool texts")
    else:
        failures.append("Complete_Agent_DataSet.md not found")
    checklist.append("")

    # --- Section 6: Per-source coverage ---
    checklist.append("## 6. Per-source PDF coverage in eval pool")
    checklist.append("")
    src_counts = Counter(it["source_key"] for it in pool["items"])
    for sk, minimum in [
        ("cbse_biology", 12), ("cbse_mathematics", 10), ("cbse_physics", 12),
        ("jee_april_2026", 18), ("jee_jan_2026", 18),
        ("neet_botany", 18), ("neet_chemistry", 18), ("neet_physics", 18), ("neet_zoology", 18),
    ]:
        c = src_counts.get(sk, 0)
        ok = c >= minimum
        checklist.append(f"- [{'x' if ok else ' '}] `{sk}`: {c} (min {minimum})")
        if not ok:
            failures.append(f"Source {sk}: {c} < minimum {minimum}")
    checklist.append("")

    # --- Section 7: Diagram / vision extraction quality ---
    checklist.append("## 7. Diagram / vision extraction quality")
    checklist.append("")
    try:
        from verify_diagram_extraction_quality import main as verify_diagram_quality  # noqa: WPS433

        diagram_rc = verify_diagram_quality()
        checklist.append(
            f"- [{'x' if diagram_rc == 0 else ' '}] verify_diagram_extraction_quality.py passes"
        )
        if diagram_rc != 0:
            failures.append("Diagram extraction quality verification failed")
    except Exception as exc:
        checklist.append("- [ ] verify_diagram_extraction_quality.py (not run)")
        warnings.append(f"Could not run diagram quality verify: {exc}")
    checklist.append("")

    # --- Summary ---
    checklist.append("## Summary")
    checklist.append("")
    checklist.append(f"- **Failures:** {len(failures)}")
    checklist.append(f"- **Warnings:** {len(warnings)}")
    if failures:
        checklist.append("")
        checklist.append("### Failures")
        for f in failures:
            checklist.append(f"- {f}")
    if warnings:
        checklist.append("")
        checklist.append("### Warnings")
        for w in warnings:
            checklist.append(f"- {w}")

    REPORT_PATH.write_text("\n".join(checklist) + "\n", encoding="utf-8")
    print(f"Wrote checklist: {REPORT_PATH}")
    print(f"Failures: {len(failures)}, Warnings: {len(warnings)}")
    if failures:
        for f in failures[:15]:
            print(f"  FAIL: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
