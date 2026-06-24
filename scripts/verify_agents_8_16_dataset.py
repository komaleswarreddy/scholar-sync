#!/usr/bin/env python3
"""Verify Agents 8-16 dataset quality in Complete_Agent_DataSet.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from studio_slide_deck_quality import bullets_per_slide, is_stub_deck  # noqa: E402

MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

TARGETS = {
    "chat_summarizer": 20,
    "hallucination_guard_retry": 15,
    "studio_system_json": 15,
    "studio_quiz": 25,
    "studio_flashcards": 22,
    "studio_mind_map": 24,
    "studio_slide_deck": 22,
    "studio_fallback_legacy": 15,
    "studio_context_embedding_query": 15,
}

MIN_AGENT_EXAMPLES = 15

PLACEHOLDER_PATTERNS = [
    r'"definition":\s*"from source"',
    r'"term":\s*"example"',
    r"Rewrite using only excerpt terms",
    r"\bTBD\b",
    r"unchanged from baseline",
]

SCOPE_MODES = {"per_concept", "multi_concept", "per_source", "multi_source", "no_source"}
STUDIO_AGENTS = {"studio_quiz", "studio_flashcards", "studio_mind_map", "studio_slide_deck"}

AGENT_SECTIONS = [
    ("## 8. Chat Summarizer", "chat_summarizer"),
    ("## 9. Hallucination Guard", "hallucination_guard_retry"),
    ("## 10. Studio System Prompt", "studio_system_json"),
    ("## 11. Studio Quiz", "studio_quiz"),
    ("## 12. Studio Flashcards", "studio_flashcards"),
    ("## 13. Studio Mind Map", "studio_mind_map"),
    ("## 14. Studio Slide Deck", "studio_slide_deck"),
    ("## 15. Studio Fallback", "studio_fallback_legacy"),
    ("## 16. Studio Context Embedding", "studio_context_embedding_query"),
]

MIN_PROMPT_FENCE_LEN = 80

STUDIO_INPUT_PREFIXES = (
    "studio_quiz-",
    "studio_flashcards-",
    "studio_mind_map-",
    "studio_slide_deck-",
    "studio_fallback_legacy-",
)


def _studio_only_ids(ids: list[str]) -> bool:
    return all(any(i.startswith(p) for p in STUDIO_INPUT_PREFIXES) for i in ids)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def extract_input_strings(example_block: str) -> list[str]:
    m = re.search(r"\*\*Inputs\*\*\s*\n\n(.+?)\n\n\*\*Expected output\*\*", example_block, re.S)
    if not m:
        return []
    block = m.group(1)
    keys = (
        r"Query|User Request|Draft Answer|Message|Old Conversation|Context|"
        r"Task Instruction|Answer|Custom Instructions|Task Type|Studio Task|"
        r"Source Title|Topic|Unsupported Sentences|Selected Source Count"
    )
    out: list[str] = []
    for km in re.finditer(rf"\*\*({keys}):\*\*\s*\n\n(.*?)(?=\n\n\*\*(?:{keys}):|\Z)", block, re.S):
        val = km.group(2).strip()
        if val and len(val) > 10:
            out.append(normalize(val))
    return out


def agent_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    nxt = re.search(r"\n## \d+\. ", text[start + len(heading) :])
    end = start + len(heading) + (nxt.start() if nxt else len(text))
    return text[start:end]


def count_examples(text: str, prefix: str) -> int:
    return len(re.findall(rf"`{prefix}-\d{{3}}`", text))


def main() -> int:
    text = MD.read_text(encoding="utf-8")
    errors: list[str] = []

    # Example counts
    for prefix, target in TARGETS.items():
        actual = count_examples(text, prefix)
        if actual != target:
            errors.append(f"{prefix}: expected {target}, got {actual}")
        if actual < MIN_AGENT_EXAMPLES:
            errors.append(f"{prefix}: {actual} below minimum {MIN_AGENT_EXAMPLES}")

    # No Evaluators in agents 8-16
    sec8 = text[text.find("## 8. Chat Summarizer") :]
    if "**Evaluators:**" in sec8:
        errors.append("Evaluators lines found in agents 8-16")

    # Structure alignment (Agents 5–6 documentation standard)
    sec8_end = text.find("## 8. Chat Summarizer")
    agents_8_16_blob = text[sec8_end:] if sec8_end >= 0 else ""
    for heading, prefix in AGENT_SECTIONS:
        sec = agent_section(text, heading)
        if not sec:
            errors.append(f"Missing agent section: {heading}")
            continue
        for marker in (
            "**Audit finding (baseline v1.0.0):**",
            "**Fixed Variation Taxonomy (locked)**",
            "**Quality Check (evaluation layer)**",
        ):
            if marker not in sec:
                errors.append(f"{prefix}: missing {marker}")
        fences = re.findall(r"```(?:jinja2|yaml|text|json)?\n(.+?)```", sec, re.S)
        if not fences or max(len(f.strip()) for f in fences) < MIN_PROMPT_FENCE_LEN:
            errors.append(f"{prefix}: missing full inline prompt fenced block")
        if "### Evaluation examples" not in sec:
            errors.append(f"{prefix}: missing ### Evaluation examples header")
        if not re.search(r"## Variation: `[\w_]+`", sec):
            errors.append(f"{prefix}: missing ## Variation: headers")
        if not re.search(r"#### Example 1: `" + re.escape(prefix), sec):
            errors.append(f"{prefix}: missing per-variation Example 1 numbering")

    if re.search(r"\[Eval (?:grounding|transcript) ref:", agents_8_16_blob, re.I):
        errors.append("Eval ref suffixes found in agents 8-16 inputs")
    if re.search(r"eval ref:", agents_8_16_blob, re.I):
        errors.append("Eval ref placeholder strings found in agents 8-16")
    if "Eval reference template" in agents_8_16_blob:
        errors.append("Eval reference template block found in agents 8-16")

    # Placeholders — scan example blocks only (not agent responsibility headers)
    example_blocks = re.findall(r"#### Example \d+: `.+?(?=\n#### Example|\n## \d+\. |\Z)", agents_8_16_blob, re.S)
    example_text = "\n".join(example_blocks)
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, example_text, re.I):
            errors.append(f"Placeholder pattern matched in examples: {pat}")

    # Hallucination guard balance
    hg = agent_section(text, "## 9. Hallucination Guard")
    rewrite = len(re.findall(r"rewrite", hg, re.I))
    pass_through = len(re.findall(r"pass_through|pass_minor", hg, re.I))
    if rewrite < 5:
        errors.append(f"Hallucination guard rewrite cases: {rewrite} (need >=5)")
    if pass_through < 5:
        errors.append(f"Hallucination guard pass cases: {pass_through} (need >=5)")

    # Mind map multi-source
    mm = agent_section(text, "## 13. Studio Mind Map")
    multi_src = len(re.findall(r"\*\*selected_source_count:\*\* [23]", mm))
    if multi_src < 8:
        errors.append(f"Mind map multi-source examples: {multi_src} (need >=8)")

    # Studio scope matrix
    for agent_prefix in STUDIO_AGENTS:
        heading_map = {
            "studio_quiz": "## 11. Studio Quiz",
            "studio_flashcards": "## 12. Studio Flashcards",
            "studio_mind_map": "## 13. Studio Mind Map",
            "studio_slide_deck": "## 14. Studio Slide Deck",
        }
        sec = agent_section(text, heading_map[agent_prefix])
        found = set()
        for mode in SCOPE_MODES:
            if f"scope_mode:{mode}" in sec:
                found.add(mode)
        missing = SCOPE_MODES - found
        if missing:
            errors.append(f"{agent_prefix} missing scope modes: {missing}")

    # Slide deck production gold checks
    sd = agent_section(text, "## 14. Studio Slide Deck")
    if "| Version | 1.2.0 |" not in sd:
        errors.append("studio_slide_deck: expected version 1.2.0 (production LLM gold)")
    if "production_llm_gold" not in sd:
        errors.append("studio_slide_deck: missing production_llm_gold tags")
    stub_decks = 0
    low_variance = 0
    for m in re.finditer(
        r"`studio_slide_deck-\d{3}`.+?\*\*Slide Deck Markdown:\*\*\s*\n\n(.+?)\n\n\*\*Quality Check:",
        sd,
        re.S,
    ):
        deck = m.group(1).strip()
        if is_stub_deck(deck):
            stub_decks += 1
        counts = bullets_per_slide(deck)
        if counts and len(set(counts)) < 2 and len(counts) > 2:
            low_variance += 1
    if stub_decks:
        errors.append(f"studio_slide_deck: {stub_decks} examples still look like stub decks")
    if low_variance:
        errors.append(f"studio_slide_deck: {low_variance} decks lack bullet variance")

    # Agent 16 — embedding query quality
    emb = agent_section(text, "## 16. Studio Context Embedding")
    if "**Why this agent is needed**" not in emb:
        errors.append("studio_context_embedding_query: missing Why this agent is needed section")
    if "Eval embedding query builder contract" not in emb:
        errors.append("studio_context_embedding_query: missing eval embedding contract prompt block")
    if "| Version | 1.3.0 |" not in emb:
        errors.append("studio_context_embedding_query: expected version 1.3.0")
    emb_outputs = re.findall(
        r"`studio_context_embedding_query-\d{3}`.+?\*\*Embedding Query:\*\*\s*\n\n(.+?)\n\n\*\*Quality Check:",
        emb,
        re.S,
    )
    if len(emb_outputs) != TARGETS["studio_context_embedding_query"]:
        errors.append(
            f"studio_context_embedding_query: expected {TARGETS['studio_context_embedding_query']} "
            f"embedding outputs, parsed {len(emb_outputs)}"
        )
    for i, q in enumerate(emb_outputs, start=1):
        q_stripped = q.strip()
        if len(q_stripped) < 80:
            errors.append(f"studio_context_embedding_query output #{i} too short ({len(q_stripped)} chars)")
        if not q_stripped.endswith("NCERT"):
            errors.append(f"studio_context_embedding_query output #{i} must end with NCERT token")

    all_inputs: dict[str, list[str]] = {}
    for m in re.finditer(r"#### Example \d+: `(?P<id>[\w-]+)`(.+?)(?=\n#### Example|\n## \d+\. |\Z)", text, re.S):
        ex_id = m.group("id")
        inputs = extract_input_strings(m.group(0))
        for inp in inputs:
            all_inputs.setdefault(inp, []).append(ex_id)

    dupes = {k: v for k, v in all_inputs.items() if len(v) > 1}
    problem_dupes = {k: v for k, v in dupes.items() if not _studio_only_ids(v)}
    if problem_dupes:
        errors.append(f"Cross-agent duplicate inputs: {len(problem_dupes)}")
        for k, ids in list(problem_dupes.items())[:5]:
            preview = k[:60].encode("ascii", errors="replace").decode("ascii")
            errors.append(f"  dup [{ids[0]} vs {ids[1]}]: {preview}...")

    # Header check
    if "sixteen-agent" not in text[:2000] and "twenty-two-agent" not in text[:2000]:
        errors.append("Header not updated to sixteen-agent or twenty-two-agent")

    # Report
    total_new = sum(TARGETS.values())
    print(f"Target new examples: {total_new}")
    for prefix, target in TARGETS.items():
        print(f"  {prefix}: {count_examples(text, prefix)}/{target}")
    print(f"Hallucination rewrite/pass tags: {rewrite}/{pass_through}")
    print(f"Mind map multi-source count tags: {multi_src}")
    print(f"Duplicate input strings (non-studio): {len(problem_dupes)}")
    print(f"Shared studio context groups (intentional): {len(dupes) - len(problem_dupes)}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            safe = e.encode("ascii", errors="replace").decode("ascii")
            print(f"  - {safe}")
        return 1

    print("\nOK — all verification checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
