#!/usr/bin/env python3
"""Shared markdown rendering for agent evaluation dataset sections (Agents 5–6 style)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_j2(path: str | Path) -> str:
    """Read a production Jinja template; strip standalone `{# ... #}` comment lines."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    text = p.read_text(encoding="utf-8")
    lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*\{#.*#\}\s*$", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def render_metadata_table(rows: list[tuple[str, str]]) -> str:
    lines = ["| Field | Value |", "|-------|-------|"]
    for k, v in rows:
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def render_taxonomy_table(
    rows: list[tuple[str, str, str | int]],
    col3_header: str = "Example quota",
) -> str:
    lines = [
        f"| Variation | Failure/behavior tested | {col3_header} |",
        "|-----------|-------------------------|" + ("-" * (len(col3_header) + 2) + "|"),
    ]
    for var, behavior, quota in rows:
        lines.append(f"| `{var}` | {behavior} | {quota} |")
    return "\n".join(lines)


def render_quality_check(dimensions: list[tuple[str, str]]) -> str:
    lines = [
        "**Quality Check (evaluation layer)** — every example is graded against these dimensions:",
        "",
    ]
    for name, desc in dimensions:
        lines.append(f"* **{name}** — {desc}")
    return "\n".join(lines)


def render_langsmith_config(items: list[str]) -> str:
    return "**LangSmith configuration**\n\n" + "\n".join(f"* {item}" for item in items)


def render_prompt_blocks(blocks: list[tuple[str, str, str]]) -> str:
    """Each block: (label, fenced_lang, content)."""
    parts: list[str] = []
    for label, lang, content in blocks:
        parts.append(f"**{label}:**\n\n```{lang}\n{content}\n```")
    return "\n\n".join(parts)


def render_agent_header(
    *,
    title: str,
    metadata_rows: list[tuple[str, str]],
    agent_responsibility: str,
    audit_finding: str,
    taxonomy_rows: list[tuple[str, str, str | int]],
    quality_dimensions: list[tuple[str, str]],
    langsmith_items: list[str],
    prompt_blocks: list[tuple[str, str, str]],
    runtime_note: str,
    eval_count: int,
    extras: str = "",
    taxonomy_col3: str = "Example quota",
) -> str:
    parts = [
        title,
        "",
        render_metadata_table(metadata_rows),
        "",
        f"**Agent responsibility:** {agent_responsibility}",
        "",
        f"**Audit finding (baseline v1.0.0):** {audit_finding}",
        "",
        "**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:",
        "",
        render_taxonomy_table(taxonomy_rows, taxonomy_col3),
        "",
        render_quality_check(quality_dimensions),
        "",
        render_langsmith_config(langsmith_items),
        "",
        render_prompt_blocks(prompt_blocks),
        "",
        f"*Runtime note:* {runtime_note}",
    ]
    if extras.strip():
        parts.extend(["", extras.strip()])
    parts.extend(["", f"### Evaluation examples ({eval_count})", ""])
    return "\n".join(parts)


def render_variation_section(variation_name: str) -> str:
    return f"## Variation: `{variation_name}`\n"


@dataclass
class ExampleRecord:
    ex_id: str
    variation: str
    tags: list[str]
    inputs: dict[str, str]
    outputs: dict[str, str]
    quality: list[str]
    extra_meta: str = ""


def example_block_v2(
    example_num: int,
    ex_id: str,
    variation: str,
    tags: list[str],
    inputs: dict[str, str],
    outputs: dict[str, str],
    quality: list[str],
    extra_meta: str = "",
) -> str:
    tag_line = ", ".join(tags)
    lines = [
        f"#### Example {example_num}: `{ex_id}`",
        "",
        f"- **Variation:** {variation}",
        f"- **Tags:** {tag_line}",
    ]
    if extra_meta:
        lines.append(extra_meta)
    lines += ["", "**Inputs**", ""]
    for k, v in inputs.items():
        lines.append(f"**{k.replace('_', ' ').title()}:**")
        lines.append("")
        lines.append(v)
        lines.append("")
    lines += ["**Expected output**", ""]
    for k, v in outputs.items():
        lines.append(f"**{k.replace('_', ' ').title()}:**")
        lines.append("")
        lines.append(v)
        lines.append("")
    qc = ". ".join(quality) + "."
    lines += [f"**Quality Check:** {qc}", "", "---", ""]
    return "\n".join(lines)


def render_examples_grouped(
    examples: list[ExampleRecord],
    variation_order: list[str],
) -> str:
    """Emit examples under ## Variation headers; restart Example 1..N per variation."""
    by_var: dict[str, list[ExampleRecord]] = {v: [] for v in variation_order}
    for ex in examples:
        if ex.variation not in by_var:
            by_var[ex.variation] = []
        by_var[ex.variation].append(ex)

    parts: list[str] = []
    for var in variation_order:
        bucket = by_var.get(var, [])
        if not bucket:
            continue
        parts.append(render_variation_section(var))
        parts.append("")
        for i, ex in enumerate(bucket, start=1):
            parts.append(
                example_block_v2(
                    i,
                    ex.ex_id,
                    ex.variation,
                    ex.tags,
                    ex.inputs,
                    ex.outputs,
                    ex.quality,
                    ex.extra_meta,
                )
            )
    return "\n".join(parts)


def example_from_record(rec: ExampleRecord, num: int) -> str:
    return example_block_v2(
        num, rec.ex_id, rec.variation, rec.tags, rec.inputs, rec.outputs, rec.quality, rec.extra_meta
    )


def locked_variation(var: str, mapping: dict[str, str]) -> str:
    return mapping.get(var, var)
