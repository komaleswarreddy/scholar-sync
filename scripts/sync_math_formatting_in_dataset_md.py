#!/usr/bin/env python3
"""Sync math formatting contract into Complete_Agent_DataSet.md problem-solver sections."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATHS = [
    ROOT / "Reference dataset" / "Complete_Agent_DataSet.md",
    ROOT / "scripts" / "agents_17_22_problem_solver.md",
]
CONTRACT = ROOT / "packages/core/prompts/templates/problem_solver/math_formatting_contract.j2"
INCLUDE = "{% include 'problem_solver/math_formatting_contract.j2' %}"

BRIEF_BLOCK = re.compile(
    r"Use `\\\[ \.\.\. \\\]` for display equations and `\$\.\.\.\$` for inline math inside `bodyMarkdown`\.\n"
    r"Put spaces around multiplication: `72 \\\\times 1000`\. Wrap units in `\\\\text\{\}`(?:, e\.g\. `\\\\text\{ km/h\}` and `\\\\text\{ m/s\}\^2`)?\.\n\n",
    re.MULTILINE,
)

INLINE_CONTRACT_START = "# MATHEMATICAL FORMATTING CONTRACT"
INLINE_CONTRACT_END = "# REASONING RULES"


def replace_inline_contract(block: str) -> str:
    start = block.find(INLINE_CONTRACT_START)
    if start < 0:
        return block
    end = block.find(INLINE_CONTRACT_END, start)
    if end < 0:
        return block
    return block[:start] + INCLUDE + "\n\n" + block[end:]


def insert_before_return_json(block: str) -> str:
    if INCLUDE in block:
        return block
    marker = "Return JSON only:"
    idx = block.find(marker)
    if idx < 0:
        return block
    return block[:idx] + INCLUDE + "\n\n" + block[idx:]


def patch_section_19(text: str) -> str:
    """Show Best Approach — replace inlined contract with include."""
    header = "## 19. Show Best Approach Coach"
    nxt = "## 20. Show Missing Idea Coach"
    return _patch_between(text, header, nxt, replace_inline_contract)


def patch_section_18(text: str) -> str:
    header = "## 18. Explain From Basics Coach"
    nxt = "## 19. Show Best Approach Coach"
    return _patch_between(text, header, nxt, insert_before_return_json)


def patch_section_20(text: str) -> str:
    header = "## 20. Show Missing Idea Coach"
    nxt = "## 21. Help Me Solve It Coach"
    text = _patch_between(text, header, nxt, insert_before_return_json)
    return _add_latex_quality_dim(text, header, nxt, after="typical_student_trap")


def patch_section_21(text: str) -> str:
    header = "## 21. Help Me Solve It Coach"
    nxt = "## 22. Problem Solver Follow-up Handler"
    text = _patch_between(text, header, nxt, lambda b: BRIEF_BLOCK.sub(INCLUDE + "\n\n", b))
    return _add_latex_quality_dim(text, header, nxt, after="cumulative_context")


def patch_section_22(text: str) -> str:
    header = "## 22. Problem Solver Follow-up Handler"
    nxt = None

    def fn(block: str) -> str:
        block = BRIEF_BLOCK.sub("", block)
        return insert_before_return_json(block)

    text = _patch_section_tail(text, header, fn)
    return _add_latex_quality_dim_tail(text, header)


def _patch_between(text: str, header: str, nxt: str, fn) -> str:
    start = text.find(header)
    end = text.find(nxt, start)
    if start < 0 or end < 0:
        raise SystemExit(f"Missing section bounds: {header!r} -> {nxt!r}")
    body = text[start:end]
    patched = _patch_prompt_jinja(body, fn)
    return text[:start] + patched + text[end:]


def _patch_section_tail(text: str, header: str, fn) -> str:
    start = text.find(header)
    if start < 0:
        raise SystemExit(f"Missing section: {header!r}")
    body = text[start:]
    patched = _patch_prompt_jinja(body, fn)
    return text[:start] + patched


def _patch_prompt_jinja(section: str, fn) -> str:
    pt = section.find("**Prompt template (production):**")
    if pt < 0:
        raise SystemExit("Prompt template block not found in section")
    jstart = section.find("```jinja2", pt)
    jend = section.find("```", jstart + 10)
    if jstart < 0 or jend < 0:
        raise SystemExit("jinja2 fence not found")
    inner = section[jstart + len("```jinja2\n") : jend]
    new_inner = fn(inner)
    if new_inner == inner:
        # try brief block replace for 21/22 style
        new_inner = BRIEF_BLOCK.sub(INCLUDE + "\n\n", inner)
    return section[: jstart + len("```jinja2\n")] + new_inner + section[jend:]


def _add_latex_quality_dim(text: str, header: str, nxt: str, after: str) -> str:
    start = text.find(header)
    end = text.find(nxt, start)
    body = text[start:end]
    needle = f"* **{after}**"
    insert = "* **latex_format** — Multiplication spaced; units in `\\text{}`; JSON backslashes escaped in `bodyMarkdown`.\n"
    if "**latex_format**" in body[: body.find("### Evaluation")]:
        return text
    idx = body.find(needle)
    if idx < 0:
        return text
    line_end = body.find("\n", idx)
    body = body[: line_end + 1] + insert + body[line_end + 1 :]
    return text[:start] + body + text[end:]


def _add_latex_quality_dim_tail(text: str, header: str) -> str:
    start = text.find(header)
    body = text[start:]
    if "**latex_format**" in body[: body.find("### Evaluation")]:
        return text
    needle = "* **reveal_level**"
    insert = "* **latex_format** — Multiplication spaced; units in `\\text{}`; JSON backslashes escaped in `bodyMarkdown`.\n"
    idx = body.find(needle)
    if idx < 0:
        return text
    line_end = body.find("\n", idx)
    body = body[: line_end + 1] + insert + body[line_end + 1 :]
    return text[:start] + body


def main() -> None:
    if not CONTRACT.is_file():
        raise SystemExit(f"Missing contract file: {CONTRACT}")
    for md_path in MD_PATHS:
        if not md_path.is_file():
            print(f"Skip missing: {md_path}")
            continue
        text = md_path.read_text(encoding="utf-8")
        for fn in (patch_section_18, patch_section_19, patch_section_20, patch_section_21, patch_section_22):
            text = fn(text)
        md_path.write_text(text, encoding="utf-8")
        print(f"Updated {md_path}")


if __name__ == "__main__":
    main()
