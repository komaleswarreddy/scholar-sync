#!/usr/bin/env python3
"""Audit agents 1-16 for duplicate and near-duplicate examples."""

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
    r"Source Title|Topic|Unsupported Sentences|Selected Source Count|Focused Query"
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
]


def normalize(s: str) -> str:
    s = re.sub(r"\[Eval (?:grounding ref|transcript ref):[^\]]+\]", "", s, flags=re.I)
    s = re.sub(r"\(No indexed excerpt[^\)]*\)", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s.strip().lower())


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalize(s)))


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


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
    for km in re.finditer(
        rf"\*\*({INPUT_KEYS}):\*\*\s+(.+?)(?=\n\n|\n\*\*|\Z)",
        body,
        re.S,
    ):
        key = km.group(1).lower().replace(" ", "_")
        val = km.group(2).strip()
        if val and key not in fields:
            fields[key] = val
    return fields


def parse_examples(text: str) -> list[tuple[str, int, dict[str, str]]]:
    # Match both: #### Example 1: intent_classifier-001
    # and: #### Example 2: `query_rewriter-002`
    header_re = re.compile(
        r"#### Example \d+: [`']?(?P<id>[a-z][\w-]*)[`']?",
        re.I,
    )
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
        "query",
        "message",
        "user_request",
        "draft_answer",
        "context",
        "answer",
        "old_conversation",
        "task_instruction",
        "custom_instructions",
        "focused_query",
    ]

    exact_dup_groups = 0
    studio_context_dupes = 0
    for key in field_keys:
        bucket: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for ex_id, ag, fields in examples:
            val = fields.get(key)
            if not val or len(normalize(val)) < 12:
                continue
            bucket[normalize(val)].append((ex_id, ag))
        dupes = {k: v for k, v in bucket.items() if len(v) > 1}
        for val, ids in dupes.items():
            if key == "context" and all(ag in (11, 12, 13, 14, 15) for _, ag in ids):
                studio_context_dupes += 1
                continue
            exact_dup_groups += 1
            if exact_dup_groups <= 5:
                if exact_dup_groups == 1:
                    print("EXACT duplicates (non-studio-context):")
                label = ", ".join(f"A{ag}:{eid}" for eid, ag in ids)
                print(f"  [{label}] ({key})")
                print(f"    {val[:100].encode('ascii', errors='replace').decode()}...")
    if studio_context_dupes:
        print(
            f"EXACT duplicate 'context': {studio_context_dupes} studio-only group(s) "
            "— intentional NCERT reuse\n"
        )

    if exact_dup_groups == 0:
        print("EXACT duplicates: none across agents 1-16\n")

    # A1-4 query vs A5-6 message/user_request
    queries = {
        normalize(f["query"]): (ex_id, ag)
        for ex_id, ag, f in examples
        if f.get("query") and len(normalize(f["query"])) > 10
    }
    cross = []
    for ex_id, ag, f in examples:
        if ag not in (5, 6):
            continue
        for k in ("message", "user_request"):
            if f.get(k) and normalize(f[k]) in queries:
                qid, qag = queries[normalize(f[k])]
                cross.append((qid, qag, ex_id, ag, k))
    print(f"Query (A1-4) exact match to A5-6 message/user_request: {len(cross)}")
    for row in cross[:10]:
        print(f"  A{row[1]} {row[0]} <-> A{row[3]} {row[2]} ({row[4]})")
    print()

    # Near-duplicates Jaccard >= 0.80 on primary text fields
    primary: list[tuple[str, int, str, str]] = []
    for ex_id, ag, fields in examples:
        for k in (
            "query",
            "message",
            "user_request",
            "context",
            "old_conversation",
            "answer",
            "draft_answer",
        ):
            if fields.get(k) and len(normalize(fields[k])) >= 35:
                primary.append((ex_id, ag, k, fields[k]))

    similar: list[tuple[float, tuple, tuple]] = []
    for i in range(len(primary)):
        for j in range(i + 1, len(primary)):
            a, b = primary[i], primary[j]
            if a[0] == b[0] and a[2] == b[2]:
                continue
            sim = jaccard(a[3], b[3])
            if sim >= 0.80:
                similar.append((sim, a, b))
    similar.sort(reverse=True)
    print(f"Near-duplicate pairs (Jaccard >= 0.80): {len(similar)}")
    for sim, a, b in similar[:15]:
        print(f"  {sim:.2f} A{a[1]} {a[0]} ({a[2]}) <-> A{b[1]} {b[0]} ({b[2]})")
    print()

    # Shared NCERT context cores (after stripping eval refs)
    ctx_bucket: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for ex_id, ag, fields in examples:
        c = fields.get("context")
        if c and len(normalize(c)) > 40:
            ctx_bucket[normalize(c)].append((ex_id, ag))
    ctx_exact = {
        k: v
        for k, v in ctx_bucket.items()
        if len(v) > 1
        and not all(ag in (11, 12, 13, 14, 15) for _, ag in v)
    }
    print(f"Exact duplicate context (refs stripped): {len(ctx_exact)} group(s)")
    for val, ids in list(ctx_exact.items())[:8]:
        agents = sorted({ag for _, ag in ids})
        print(f"  agents {agents}: {[x[0] for x in ids]}")
        print(f"    {val[:90].encode('ascii', errors='replace').decode()}...")
    print()

    # Prefix overlap — intentional reuse of same NCERT facts
    prefix_bucket: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for ex_id, ag, fields in examples:
        c = fields.get("context")
        if c and len(normalize(c)) > 50:
            prefix_bucket[normalize(c)[:100]].append((ex_id, ag))
    prefix_shared = {k: v for k, v in prefix_bucket.items() if len(v) > 1}
    cross_prefix = [
        (k, v) for k, v in prefix_shared.items() if len({ag for _, ag in v}) > 1
    ]
    print(f"Shared context prefix (100 chars, cross-agent): {len(cross_prefix)} group(s)")
    print("(Same NCERT facts reused with different eval refs is expected for Studio agents.)\n")
    for k, v in cross_prefix[:10]:
        agents = sorted({ag for _, ag in v})
        print(f"  {len(v)}x agents {agents}: {k[:70].encode('ascii', errors='replace').decode()}...")

    id_counts = Counter(ex_id for ex_id, _, _ in examples)
    dup_ids = [i for i, c in id_counts.items() if c > 1]
    print(f"\nDuplicate example IDs: {len(dup_ids)}")

    issues = exact_dup_groups + len(cross) + len(dup_ids)
    # Near-duplicates and studio context prefix reuse are informational only
    if issues == 0:
        print("\nRESULT: No problematic duplicates. Shared NCERT fact prefixes across Studio agents are intentional.")
        return 0
    print(f"\nRESULT: {issues} potential issue(s) found — review above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
