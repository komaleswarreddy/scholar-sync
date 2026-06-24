#!/usr/bin/env python3
"""Audit agents 1-22 for duplicate and near-duplicate examples."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

INPUT_KEYS = (
    r"Query|User Request|Draft Answer|Message|Old Conversation|Context|"
    r"Task Instruction|Answer|Custom Instructions|Task Type|Studio Task|"
    r"Source Title|Topic|Unsupported Sentences|Selected Source Count|Focused Query|"
    r"Problem Text Normalized|Student Attempt|Action|Interaction Count"
)

PREFIX_TO_AGENT = [
    ("intent_classifier", 1),
    ("query_rewriter", 2),
    ("query_decomposer", 3),
    ("scope_narrower", 4),
    ("chat_policy_block", 5),
    ("direct_chat", 6),
    ("chat_summarizer", 8),
    ("hallucination_guard_retry", 9),
    ("studio_system_json", 10),
    ("studio_quiz", 11),
    ("studio_flashcards", 12),
    ("studio_mind_map", 13),
    ("studio_slide_deck", 14),
    ("studio_fallback_legacy", 15),
    ("studio_context_embedding_query", 16),
    ("problem_dna_analyzer", 17),
    ("explain_from_basics", 18),
    ("show_best_approach", 19),
    ("show_missing_idea", 20),
    ("help_me_solve_it", 21),
    ("problem_solver_followup", 22),
]


def normalize(s: str) -> str:
    s = re.sub(r"\[Eval (?:grounding ref|transcript ref):[^\]]+\]", "", s, flags=re.I)
    s = re.sub(r"\(No indexed excerpt[^\)]*\)", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s.strip().lower())


def agent_num(ex_id: str) -> int:
    for prefix, num in PREFIX_TO_AGENT:
        if ex_id.startswith(prefix):
            return num
    return 0


def extract_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    m = re.search(r"\*\*Inputs\*\*\s*\n\n(.+?)\n\n\*\*Expected output\*\*", block, re.S)
    if not m:
        m = re.search(
            r"(?:^|\n)Inputs\s*\n\n(.+?)\n\n(?:Expected output|\*\*Expected output\*\*)",
            block,
            re.S,
        )
    if not m:
        return fields
    body = m.group(1)
    for km in re.finditer(
        rf"\*\*({INPUT_KEYS}):\*\*\s*\n\n(.*?)(?=\n\n\*\*(?:{INPUT_KEYS}):|\Z)",
        body,
        re.S,
    ):
        key = km.group(1).lower().replace(" ", "_")
        val = km.group(2).strip()
        if val:
            fields[key] = val
    return fields


def parse_examples(text: str) -> list[tuple[str, int, dict[str, str]]]:
    header_re = re.compile(r"#### Example \d+: [`']?(?P<id>[a-z][\w-]*)[`']?", re.I)
    headers = [(m.start(), m.group("id")) for m in header_re.finditer(text)]
    out: list[tuple[str, int, dict[str, str]]] = []
    for i, (start, ex_id) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        block = text[start:end]
        fields = extract_fields(block)
        out.append((ex_id, agent_num(ex_id), fields))
    return out


def main() -> int:
    text = MD.read_text(encoding="utf-8")
    examples = parse_examples(text)
    by_agent: Counter[int] = Counter(ag for _, ag, _ in examples)
    print("Examples per agent:", dict(sorted(by_agent.items())))
    print(f"Total examples parsed: {len(examples)}\n")

    field_keys = [
        "query", "message", "user_request", "draft_answer", "context", "answer",
        "old_conversation", "task_instruction", "custom_instructions", "focused_query",
        "problem_text_normalized",
    ]

    exact_dup_groups = 0
    for key in field_keys:
        bucket: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for ex_id, ag, fields in examples:
            val = fields.get(key)
            if not val or len(normalize(val)) < 12:
                continue
            bucket[normalize(val)].append((ex_id, ag))
        for val, ids in bucket.items():
            if len(ids) <= 1:
                continue
            if key == "context" and all(ag in (11, 12, 13, 14, 15) for _, ag in ids):
                continue
            exact_dup_groups += 1
            if exact_dup_groups <= 8:
                if exact_dup_groups == 1:
                    print("EXACT duplicates:")
                print(f"  [{', '.join(f'A{ag}:{eid}' for eid, ag in ids)}] ({key})")
                print(f"    {val[:90]}...")

    if exact_dup_groups == 0:
        print("EXACT duplicates: none across agents 1-22\n")
    else:
        print(f"EXACT duplicate groups: {exact_dup_groups}\n")

    id_counts = Counter(ex_id for ex_id, _, _ in examples)
    dup_ids = [i for i, c in id_counts.items() if c > 1]
    print(f"Duplicate example IDs: {len(dup_ids)}")

    issues = exact_dup_groups + len(dup_ids)
    if issues == 0:
        print("\nRESULT: No problematic duplicates across agents 1-22.")
        return 0
    print(f"\nRESULT: {issues} potential issue(s) — review above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
