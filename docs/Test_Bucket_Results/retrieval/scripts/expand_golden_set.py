#!/usr/bin/env python3
"""
Expand retrieval_golden.json to full RET matrix coverage.

Usage:
  python scripts/expand_golden_set.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evals" / "datasets" / "retrieval_golden.json"

THRESHOLDS = {
    "recall_at_1": 0.65,
    "recall_at_3": 0.85,
    "recall_at_5": 0.92,
    "recall_at_10": 0.97,
    "mrr": 0.75,
    "context_precision": 0.70,
    "multi_doc_top5_min_sources": 0.80,
    "negative_refusal_rate": 1.0,
    "paraphrase_jaccard_top5": 0.60,
    "formula_recall_at_3": 0.85,
    "question_type_recall_at_3_min": 0.75,
    "long_question_recall_at_3": 0.75,
}

FACTUAL_SEEDS = [
    ("fact-photosynthesis-equation", "What is the balanced equation for photosynthesis?", ["6CO2", "photosynthesis"], "DEFINITION"),
    ("fact-chlorophyll-role", "What does chlorophyll do in plants?", ["chlorophyll"], "DEFINITION"),
    ("fact-mitochondria", "Why is the mitochondria called the powerhouse of the cell?", ["mitochondria", "powerhouse"], "DEFINITION"),
    ("fact-calvin-reactants", "What are the reactants in the Calvin cycle?", ["carbon dioxide", "water"], "EXPLANATION"),
    ("fact-light-absorption", "Which wavelengths does chlorophyll absorb most?", ["red", "blue"], "DEFINITION"),
    ("fact-energy-conversion", "How do plants convert light energy?", ["chemical energy"], "EXPLANATION"),
    ("fact-chapter-intro", "What is photosynthesis according to the chapter introduction?", ["photosynthesis", "light energy"], "COMPREHENSION"),
    (
        "fact-plant-biology",
        "After reading the chapter introduction, what inputs do plants need besides light for photosynthesis?",
        ["carbon dioxide", "water"],
        "COMPREHENSION",
    ),
    ("fact-ret-golden", "What is RET_GOLDEN_FACT about photosynthesis?", ["6CO2", "C6H12O6"], "QUESTION"),
    ("fact-energy-transfer", "How is energy transferred in plants per the filler pages?", ["energy transfer"], "EXPLANATION"),
    (
        "fact-page-filler",
        "Summarize what the chapter says about chlorophyll and the colors of light it absorbs.",
        ["chlorophyll", "red"],
        "COMPREHENSION",
    ),
    ("fact-co2-role", "What role does carbon dioxide play in photosynthesis?", ["carbon dioxide", "CO2"], "DEFINITION"),
    ("fact-water-role", "What role does water play in the photosynthesis equation?", ["water", "H2O"], "DEFINITION"),
    ("fact-oxygen-output", "What gas is produced during photosynthesis?", ["oxygen", "O2"], "DEFINITION"),
    ("fact-glucose-output", "What sugar is produced in photosynthesis?", ["glucose", "C6H12O6"], "DEFINITION"),
    ("fact-pigment", "What pigment is mentioned for light absorption?", ["chlorophyll"], "DEFINITION"),
    ("fact-calvin-name", "What cycle is named in the chapter?", ["Calvin"], "DEFINITION"),
    ("fact-assertion-energy", "Assertion: Plants store chemical energy from light. Reason: Chlorophyll captures photons.", ["chlorophyll", "chemical energy"], "ASSERTION_REASON"),
    ("fact-assertion-co2", "Assertion: CO2 is a reactant. Reason: It enters the Calvin cycle.", ["carbon dioxide", "Calvin"], "ASSERTION_REASON"),
    ("fact-comprehension-passage", "After reading the chapter passage, summarize the main process plants use to make food.", ["photosynthesis"], "COMPREHENSION"),
]

FORMULA_TOPICS = [
    ("Snell's law", ["Snell", "sin"]),
    ("Henderson-Hasselbalch equation", ["Henderson-Hasselbalch", "pH"]),
    ("Newton's second law", ["Newton", "F = ma"]),
    ("refraction angles", ["Snell", "incidence"]),
    ("pKa and pH relationship", ["pKa", "pH"]),
    ("force mass acceleration", ["F = ma", "mass"]),
]

NEGATIVE_QUESTIONS = [
    "How do I build a quantum entanglement communicator at home?",
    "What year will humans establish a permanent Mars colony?",
    "What is the capital of Antarctica's largest city?",
    "How do I synthesize dark matter in a kitchen?",
    "Who won the 2099 World Cup?",
    "What is the chemical formula for unobtanium?",
    "What is the orbital period of the fictional planet Krypton in our uploaded biology chapter?",
    "What is the population of Atlantis?",
    "How do I travel faster than light using Calvin cycle?",
    "What is the phone number of the International Space Station?",
]

PARAPHRASE_GROUPS = {
    "chlorophyll": [
        "What is chlorophyll's function?",
        "Describe the role of chlorophyll in photosynthesis.",
        "How does chlorophyll help plants capture light?",
        "Tell me about chlorophyll absorption of light.",
        "Which pigment absorbs red and blue light in plants?",
    ],
    "photosynthesis_eq": [
        "What is the photosynthesis equation?",
        "Give the balanced chemical equation for photosynthesis.",
        "How do CO2 and water combine in photosynthesis?",
        "What reactants and products define photosynthesis?",
        "State the formula summarizing photosynthesis in plants.",
    ],
    "mitochondria": [
        "Why is mitochondria the powerhouse?",
        "What makes mitochondria the cell's powerhouse?",
        "Explain mitochondria as energy producer.",
        "How does mitochondria relate to cellular energy?",
        "Describe the powerhouse role of mitochondria.",
    ],
    "snell": [
        "State Snell's law.",
        "What is Snell's law formula?",
        "How are incidence and refraction angles related?",
        "Give the equation for refraction at an interface.",
        "What formula relates n1 sin theta1 and n2 sin theta2?",
    ],
}

LONG_QUESTION_TEMPLATES = [
    "I was reading about energy transfer in plants and got confused about how light energy becomes chemical energy. Can you explain using the sources?",
    "In my biology class we discussed photosynthesis but I still do not understand the role of chlorophyll. Could you clarify from the uploaded chapter?",
    "I am preparing for an exam and need help understanding the Calvin cycle reactants mentioned in the chapter. What should I know?",
    "After studying the photosynthesis equation I am unsure how carbon dioxide fits in. Please explain step by step from the document.",
    "My textbook chapter on plant biology mentions filler content about energy transfer. What are the key ideas I should remember?",
]


def _item(
    item_id: str,
    *,
    bucket: str,
    question: str,
    fixture_files: list[str],
    expected_phrases: list[str],
    question_type: str = "QUESTION",
    negative: bool = False,
    paraphrase_group: str | None = None,
    allowed_sources_min: int | None = None,
) -> dict:
    row: dict = {
        "id": item_id,
        "bucket": bucket,
        "question_type": question_type,
        "question": question,
        "fixture_files": fixture_files,
        "expected_phrases": expected_phrases,
        "negative": negative,
    }
    if paraphrase_group:
        row["paraphrase_group"] = paraphrase_group
    if allowed_sources_min is not None:
        row["allowed_sources_min"] = allowed_sources_min
    if negative:
        row["expect_refusal"] = True
    return row


def build_items() -> list[dict]:
    items: list[dict] = []

    for item_id, question, phrases, qtype in FACTUAL_SEEDS:
        fixture = (
            "sample_phrase_alpha.txt"
            if item_id == "fact-mitochondria"
            else "standard_chapter.pdf"
        )
        items.append(
            _item(
                item_id,
                bucket="factual",
                question=question,
                fixture_files=[fixture],
                expected_phrases=phrases,
                question_type=qtype,
            )
        )

    for i in range(30):
        topic, phrases = FORMULA_TOPICS[i % len(FORMULA_TOPICS)]
        items.append(
            _item(
                f"formula-{i+1:02d}",
                bucket="formula",
                question=f"Explain or state the formula for: {topic}",
                fixture_files=["physics_formulas.pdf", "sample_phrase_beta.txt"],
                expected_phrases=phrases,
                question_type="QUESTION",
            )
        )

    for i, question in enumerate(NEGATIVE_QUESTIONS, start=1):
        items.append(
            _item(
                f"negative-{i:02d}",
                bucket="negative",
                question=question,
                fixture_files=["standard_chapter.pdf"],
                expected_phrases=[],
                question_type="QUESTION",
                negative=True,
            )
        )

    for group_name, phrasings in PARAPHRASE_GROUPS.items():
        fixtures = (
            ["standard_chapter.pdf"]
            if group_name in {"chlorophyll", "photosynthesis_eq"}
            else ["physics_formulas.pdf", "sample_phrase_beta.txt"]
            if group_name == "snell"
            else ["sample_phrase_alpha.txt"]
        )
        phrases = (
            ["chlorophyll"]
            if group_name == "chlorophyll"
            else ["6CO2", "photosynthesis"]
            if group_name == "photosynthesis_eq"
            else ["mitochondria"]
            if group_name == "mitochondria"
            else ["Snell"]
        )
        for j, question in enumerate(phrasings, start=1):
            items.append(
                _item(
                    f"paraphrase-{group_name}-{j}",
                    bucket="paraphrase_group",
                    question=question,
                    fixture_files=fixtures,
                    expected_phrases=phrases,
                    question_type="DEFINITION",
                    paraphrase_group=group_name,
                )
            )

    multi_pairs = [
        ("From the biology chapter and physics formulas PDF, what does each document cover?", ["photosynthesis", "Snell"]),
        ("Compare chlorophyll in the chapter with Snell's law in the physics PDF.", ["chlorophyll", "Snell"]),
        ("What photosynthesis facts are in the chapter and what formulas are in the physics sheet?", ["photosynthesis", "Newton"]),
        ("Use standard chapter and physics_formulas.pdf: name one biology topic and one physics equation.", ["Calvin", "Henderson"]),
        ("Across chapter PDF and physics PDF, list one concept from each file.", ["chlorophyll", "pH"]),
        ("Retrieve from chapter and physics sources about light and refraction.", ["light", "refraction"]),
        ("What is in standard_chapter versus physics_formulas?", ["energy", "F = ma"]),
        ("Find photosynthesis in the chapter and Snell's law in the formula PDF.", ["photosynthesis", "sin"]),
        ("Use both PDFs: plant energy conversion and Henderson-Hasselbalch.", ["chemical energy", "pKa"]),
        ("Multi-source query: Calvin cycle from chapter and Newton's law from physics PDF.", ["Calvin", "Newton"]),
    ]
    for i, (question, phrases) in enumerate(multi_pairs, start=1):
        items.append(
            _item(
                f"multi-doc-{i:02d}",
                bucket="multi_doc",
                question=question,
                fixture_files=["standard_chapter.pdf", "physics_formulas.pdf"],
                expected_phrases=phrases,
                question_type="EXPLANATION",
                allowed_sources_min=2,
            )
        )

    for i in range(15):
        base = LONG_QUESTION_TEMPLATES[i % len(LONG_QUESTION_TEMPLATES)]
        extra = f" I have read pages {i+1} through {i+3} and still need clarity."
        items.append(
            _item(
                f"long-question-{i+1:02d}",
                bucket="long_question",
                question=base + extra,
                fixture_files=["standard_chapter.pdf"],
                expected_phrases=["photosynthesis", "chlorophyll", "energy", "Calvin", "carbon dioxide"][i % 5 : i % 5 + 1],
                question_type="QUESTION",
            )
        )

    return items


def main() -> int:
    payload = {
        "version": 2,
        "description": "Expanded golden set for RET-01..RET-11 production gate.",
        "thresholds": THRESHOLDS,
        "items": build_items(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['items'])} items to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
