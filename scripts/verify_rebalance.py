#!/usr/bin/env python3
import re
from pathlib import Path

MD = Path(__file__).resolve().parents[1] / "Reference dataset" / "ScholarSync_Intent_Classifier_Refined (1).md"
text = MD.read_text(encoding="utf-8")
PDFS = [
    "kebo106", "kebo107", "kebo110", "lebo105",
    "kech104", "kech106", "kech203", "lech103", "lech104", "lech105", "lech203",
    "kemh105", "kemh107", "kemh111", "lemh205", "lemh207",
    "keph105", "keph106", "leph103", "leph201",
]

assert text.count("intent_classifier-") == 63
assert text.count("query_rewriter-") == 56
assert text.count("query_decomposer-") == 48
assert text.count("scope_narrower-") == 25

queries = re.findall(r"\*\*Query:\*\*\s*\n(.+?)(?=\n\n|\n\*\*|\n####|\n---)", text, re.S)
norms = [re.sub(r"\s+", " ", q.strip().lower()) for q in queries]
assert len(dups := {q for q in norms if norms.count(q) > 1}) == 0, dups

missing_pdfs = [p for p in PDFS if p not in text]
assert not missing_pdfs, missing_pdfs

# intent classifier source_pdf balance
ic = text[text.index("### Evaluation examples (63)"):text.index("## 2. Query Rewriter")]
for subj in ("biology", "chemistry", "mathematics", "physics"):
    c = len(re.findall(rf"source_pdf_\w+.*\b{subj}\b|\b{subj}\b.*source_pdf_", ic, re.I))
    tags = len(re.findall(rf"\b{subj}\b", ic, re.I))
    print(f"intent_classifier {subj}: tag_mentions={tags}")

print("OK: counts, dedup, all 20 PDFs referenced")
