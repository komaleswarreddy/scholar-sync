#!/usr/bin/env python3
"""Apply full rebalance for Query Rewriter, Decomposer, and Scope Narrower sections."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "ScholarSync_Intent_Classifier_Refined (1).md"

PDFS = [
    "kebo106", "kebo107", "kebo110", "lebo105",
    "kech104", "kech106", "kech203", "lech103", "lech104", "lech105", "lech203",
    "kemh105", "kemh107", "kemh111", "lemh205", "lemh207",
    "keph105", "keph106", "leph103", "leph201",
]


def splice(text: str, start: str, end: str, body: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + body + text[j:]


def rewriter_section() -> str:
    # Examples 001-009 already updated in file; regenerate 010-056 and keep 001-009 from file
    existing = MD.read_text(encoding="utf-8")
    keep_end = existing.index("**Follow-up coreference (009-012)**")
    keep_start = existing.index("### Evaluation examples (56)")
    prefix = existing[keep_start:keep_end]
    # prefix ends before follow-up block - actually we want 001-009 only
    ex9_end = existing.index("#### Example 10: `query_rewriter-010`")
    prefix = existing[keep_start:ex9_end]

    blocks = []

    blocks.append("""#### Example 10: `query_rewriter-010`

- **Variation:** follow_up_coreference

**Inputs**

**Query:** give me an example of that
**Transcript Section:** ## Transcript
Student: How does a covalent bond form?
Assistant: explained electron sharing in covalent bonding.
**Max Rewrites:** 3

**Expected output**

**Queries:**
- covalent bond formation worked example
- electron sharing covalent bond methane example
**Confidence:** 0.84
**Reasoning:** 'That' resolved to covalent bond formation; rewrite targets a worked example specifically.

**Quality Check:** Intent lock: pass . Coreference: resolved -- 'that'->covalent bond formation . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, coreference_resolution

#### Example 11: `query_rewriter-011`

- **Variation:** follow_up_coreference

**Inputs**

**Query:** compare both curves
**Transcript Section:** ## Transcript
Student: What's the difference between a parabola and an ellipse?
Assistant: introduced both conic sections.
**Max Rewrites:** 3

**Expected output**

**Queries:**
- parabola versus ellipse comparison
- eccentricity parabola ellipse differences
**Confidence:** 0.83
**Reasoning:** 'Both' resolved to parabola and ellipse from the transcript topic.

**Quality Check:** Intent lock: pass . Coreference: resolved -- 'both'->parabola and ellipse . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, coreference_resolution

#### Example 12: `query_rewriter-012`

- **Variation:** follow_up_coreference

**Inputs**

**Query:** show me the derivation for it
**Transcript Section:** ## Transcript
Student: What is Ohm's law?
Assistant: stated the V equals IR relationship.
**Max Rewrites:** 3

**Expected output**

**Queries:**
- Ohm's law derivation microscopic model
- drift velocity derivation Ohm's law
**Confidence:** 0.85
**Reasoning:** 'It' resolved to Ohm's law; rewrite targets the derivation specifically.

**Quality Check:** Intent lock: pass . Coreference: resolved -- 'it'->Ohm's law . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, coreference_resolution

---

**Metadata lookup (013-016)**

#### Example 13: `query_rewriter-013`

- **Variation:** metadata_lookup

**Inputs**

**Query:** who is the publisher of this biology ncert anatomy chapter
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- publisher name NCERT biology textbook anatomy flowering plants
- publication details title page biology
**Confidence:** 0.88
**Reasoning:** Publisher/title-page keywords retained verbatim so header/copyright lines match keyword search.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Retained: publisher, title page

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, keyword_retention

#### Example 14: `query_rewriter-014`

- **Variation:** metadata_lookup

**Inputs**

**Query:** whats the copyright year on dis coordination compounds pdf
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- copyright year coordination compounds NCERT chapter
- publication date title page coordination compounds
**Confidence:** 0.83
**Reasoning:** Copyright and chapter-name keywords retained despite the typo in the rest of the message.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Retained: copyright; typo 'dis' corrected

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, keyword_retention

#### Example 15: `query_rewriter-015`

- **Variation:** metadata_lookup

**Inputs**

**Query:** find author name of the three dimensional geometry chapter
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- author name three dimensional geometry chapter NCERT
- writer credit three dimensional geometry
**Confidence:** 0.85
**Reasoning:** Author/writer keywords kept in at least one query, with the specific chapter name preserved.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Retained: author, writer, chapter name

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, keyword_retention

#### Example 16: `query_rewriter-016`

- **Variation:** metadata_lookup

**Inputs**

**Query:** is this ray optics book ncert or some private published one
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- NCERT or private publisher ray optics textbook
- book authorship title page ray optics
**Confidence:** 0.8
**Reasoning:** Authorship framing preserved; query stays a metadata lookup rather than drifting into content questions.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Retained: author, publisher

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, keyword_retention

---

**Comparison query (017-020)**

#### Example 17: `query_rewriter-017`

- **Variation:** comparison_query

**Inputs**

**Query:** monocot root vs dicot root internal structure
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- monocot versus dicot root internal structure
- differences monocot dicot root anatomy
**Confidence:** 0.89
**Reasoning:** Both root types retained in the comparison framing.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Both entities retained: monocot, dicot root

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, dual_entity_retention

#### Example 18: `query_rewriter-018`

- **Variation:** comparison_query

**Inputs**

**Query:** ionic bond vs covalent bond which shares electrons
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- ionic versus covalent bond electron sharing
- which bond type transfers versus shares electrons
**Confidence:** 0.9
**Reasoning:** Both bond types retained across all queries.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Both entities retained: ionic, covalent bond

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, dual_entity_retention

#### Example 19: `query_rewriter-019`

- **Variation:** comparison_query

**Inputs**

**Query:** strict inequality vs non-strict inequality solution on number line
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- strict versus non-strict linear inequality number line
- open closed interval linear inequality solution
**Confidence:** 0.91
**Reasoning:** Both inequality types retained; number-line representation kept as comparison axis.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Both entities retained: strict, non-strict inequality

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, dual_entity_retention

#### Example 20: `query_rewriter-020`

- **Variation:** comparison_query

**Inputs**

**Query:** cells in series vs cells in parallel which gives higher terminal voltage
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- cells in series versus parallel terminal voltage
- equivalent EMF series parallel cell combination
**Confidence:** 0.88
**Reasoning:** Both circuit configurations retained; terminal voltage is the comparison axis.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . Both entities retained: series, parallel cells

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, dual_entity_retention

---

**Multi-part compound (021-024)**

#### Example 21: `query_rewriter-021`

- **Variation:** multi_part_compound

**Inputs**

**Query:** define mitosis, list stages of mitosis, and explain cytokinesis
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- mitosis definition cell division
- stages of mitosis prophase metaphase anaphase telophase
- cytokinesis after mitosis
**Confidence:** 0.84
**Reasoning:** Three distinct sub-asks (definition, stages, cytokinesis) each get their own query.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . 3 sub-parts covered: definition, stages, cytokinesis

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, subtopic_coverage

#### Example 22: `query_rewriter-022`

- **Variation:** multi_part_compound

**Inputs**

**Query:** define alkanes, explain sp3 hybridization in methane, and state general formula
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- alkanes definition saturated hydrocarbons
- sp3 hybridization methane structure
- general formula alkanes CnH2n+2
**Confidence:** 0.85
**Reasoning:** Definition, hybridization, and formula each mapped to a separate query.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . 3 sub-parts covered

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, subtopic_coverage

#### Example 23: `query_rewriter-023`

- **Variation:** multi_part_compound

**Inputs**

**Query:** state binomial theorem, give general term, and find middle term when n is even
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- binomial theorem statement
- general term binomial expansion
- middle term binomial expansion n even
**Confidence:** 0.86
**Reasoning:** Three named sub-asks each preserved as a distinct retrieval query, in the order asked.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . 3 sub-parts covered

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, subtopic_coverage

#### Example 24: `query_rewriter-024`

- **Variation:** multi_part_compound

**Inputs**

**Query:** define angular momentum, state conservation law, and explain torque-angular acceleration relation
**Transcript Section:** 
**Max Rewrites:** 3

**Expected output**

**Queries:**
- angular momentum definition L equals I omega
- law of conservation of angular momentum
- torque angular acceleration relation
**Confidence:** 0.87
**Reasoning:** Three sub-asks (definition, conservation, relation) each become their own query.

**Quality Check:** Intent lock: pass . Coreference: n/a . Length: pass . Vocabulary: n/a . Abbreviation: n/a . Noise: n/a . 3 sub-parts covered

**Evaluators:** json_schema, retrieval_overlap, intent_lock_check, subtopic_coverage

---

""")

    blocks.append(_rewriter_tail())
    return prefix + "".join(blocks)


def _rewriter_tail() -> str:
    return Path(__file__).with_name("rebalance_rewriter_tail.md").read_text(encoding="utf-8")


def decomposer_section() -> str:
    return Path(__file__).with_name("rebalance_decomposer.md").read_text(encoding="utf-8")


def narrower_section() -> str:
    return Path(__file__).with_name("rebalance_scope_narrower.md").read_text(encoding="utf-8")


def verify(text: str) -> None:
    queries = re.findall(r"\*\*Query:\*\*\s*\n(.+?)(?=\n\n|\n\*\*|\n####|\n---)", text, re.S)
    norms = [re.sub(r"\s+", " ", q.strip().lower()) for q in queries]
    dups = sorted({q for q in norms if norms.count(q) > 1})
    missing = [p for p in PDFS if p not in text]
    counts = {
        "biology": len(re.findall(r"\bbiology\b", text, re.I)),
        "chemistry": len(re.findall(r"\bchemistry\b", text, re.I)),
        "mathematics": len(re.findall(r"\bmathematics\b", text, re.I)),
        "physics": len(re.findall(r"\bphysics\b", text, re.I)),
    }
    print("Examples:", {
        "intent": text.count("intent_classifier-"),
        "rewriter": text.count("query_rewriter-"),
        "decomposer": text.count("query_decomposer-"),
        "narrower": text.count("scope_narrower-"),
    })
    print("source_pdf tags:", text.count("source_pdf_"))
    print("subject mentions:", counts)
    print("duplicate queries:", len(dups))
    if dups:
        for d in dups[:10]:
            print("  ", d[:100])
    print("missing PDF tags in file:", missing)


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    rw = rewriter_section()
    text = splice(
        text,
        "### Evaluation examples (56)\n",
        "\n---\n\n---\n\n## 3. Query Decomposer Agent (Refined)",
        rw + "\n---\n\n---\n\n## 3. Query Decomposer Agent (Refined)",
    )
    text = splice(
        text,
        "### Evaluation examples (48)\n",
        "\n\n\n\n## 4. Scope Narrower Agent (Refined)",
        "### Evaluation examples (48)\n\n" + decomposer_section() + "\n\n\n\n## 4. Scope Narrower Agent (Refined)",
    )
    i = text.index("### Evaluation examples (25)\n")
    text = text[:i] + "### Evaluation examples (25)\n\n" + narrower_section() + "\n---\n"
    MD.write_text(text, encoding="utf-8")
    verify(text)


if __name__ == "__main__":
    main()
