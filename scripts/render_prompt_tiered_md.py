"""Render evals/datasets/prompt_tiered as human-readable markdown."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def human_key(key: str) -> str:
    label = key.replace("_", " ")
    label = re.sub(r"([a-z])([A-Z])", r"\1 \2", label)
    return label.title()

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals" / "datasets" / "prompt_tiered"
OUT = ROOT / "evals" / "datasets" / "PROMPT_TIERED_COMPLETE.md"


def fmt_value(value: Any, indent: int = 0) -> list[str]:
    """Render a value as readable markdown lines."""
    prefix = "  " * indent
    lines: list[str] = []

    if value is None:
        lines.append(f"{prefix}- *(empty)*")
    elif isinstance(value, bool):
        lines.append(f"{prefix}- **{str(value).lower()}**")
    elif isinstance(value, (int, float)):
        lines.append(f"{prefix}- {value}")
    elif isinstance(value, str):
        if "\n" in value:
            lines.append(f"{prefix}:")
            for line in value.splitlines():
                lines.append(f"{prefix}  > {line}")
        else:
            lines.append(f"{prefix}- {value}")
    elif isinstance(value, list):
        if not value:
            lines.append(f"{prefix}- *(none)*")
        elif all(isinstance(x, str) for x in value):
            for item in value:
                lines.append(f"{prefix}- {item}")
        elif all(isinstance(x, dict) for x in value):
            for i, item in enumerate(value, 1):
                lines.append(f"{prefix}**Item {i}:**")
                lines.extend(fmt_dict(item, indent + 1))
        else:
            for item in value:
                lines.extend(fmt_value(item, indent))
    elif isinstance(value, dict):
        lines.extend(fmt_dict(value, indent))
    else:
        lines.append(f"{prefix}- {value!r}")

    return lines


def fmt_dict(data: dict[str, Any], indent: int = 0) -> list[str]:
    prefix = "  " * indent
    lines: list[str] = []
    for key, value in data.items():
        label = human_key(key)
        if isinstance(value, dict):
            lines.append(f"{prefix}**{label}:**")
            lines.extend(fmt_dict(value, indent + 1))
        elif isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            lines.append(f"{prefix}**{label}:**")
            for i, item in enumerate(value, 1):
                lines.append(f"{prefix}  - *Entry {i}*")
                lines.extend(fmt_dict(item, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}**{label}:**")
            lines.extend(fmt_value(value, indent + 1))
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{prefix}**{label}:**")
            for line in value.splitlines():
                lines.append(f"{prefix}  > {line}")
        else:
            lines.append(f"{prefix}**{label}:** {value}")
    return lines


def fmt_prompt_template(template: str) -> list[str]:
    lines = ["**Prompt template:**", ""]
    if "SYSTEM:" in template and "USER" in template:
        parts = template.split("USER", 1)
        system_part = parts[0].replace("SYSTEM:", "", 1).strip()
        user_part = ("USER" + parts[1]).strip() if len(parts) > 1 else ""
        lines.extend(["*System instructions:*", ""])
        for line in system_part.splitlines():
            lines.append(f"> {line}")
        if user_part:
            lines.extend(["", "*User / task template:*", ""])
            for line in user_part.splitlines():
                lines.append(f"> {line}")
    else:
        for line in template.splitlines():
            lines.append(f"> {line}")
    return lines


def render_item(item: dict[str, Any], index: int) -> list[str]:
    lines = [
        f"#### Example {index}: `{item['id']}`",
        "",
        f"- **Variation:** {item.get('variation', '—')}",
        f"- **Tags:** {', '.join(item.get('tags', [])) or '—'}",
    ]
    if item.get("notes"):
        lines.append(f"- **Notes:** {item['notes']}")
    lines.append("")

    lines.append("**Inputs**")
    lines.append("")
    lines.extend(fmt_dict(item.get("inputs", {}), 0))
    lines.append("")

    lines.append("**Expected output**")
    lines.append("")
    lines.extend(fmt_dict(item.get("reference_outputs", {}), 0))
    lines.append("")

    evaluators = item.get("evaluators", [])
    if evaluators:
        lines.append(f"**Evaluators:** {', '.join(evaluators)}")
        lines.append("")

    return lines


def render_dataset(data: dict[str, Any]) -> list[str]:
    agent = data["agent"]
    langsmith = data.get("langsmith", {})
    items = data.get("items", [])

    tier_label = agent.get("tier", "").replace("_", " ").title()
    lines = [
        f"## {agent.get('sno')}. {agent.get('name')}",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Dataset ID | `{data.get('dataset_id')}` |",
        f"| Category | {agent.get('category')} |",
        f"| Tier | {tier_label} |",
        f"| Target examples | {agent.get('target_examples')} |",
        f"| Actual examples | {len(items)} |",
        f"| Version | {data.get('version', '—')} |",
        "",
    ]

    if langsmith:
        lines.extend([
            "**LangSmith configuration**",
            "",
            f"- Dataset name prefix: `{langsmith.get('dataset_name_prefix', '—')}`",
            f"- Input keys: {', '.join(f'`{k}`' for k in langsmith.get('input_keys', [])) or '—'}",
            f"- Output keys: {', '.join(f'`{k}`' for k in langsmith.get('output_keys', [])) or '—'}",
            "",
        ])

    if agent.get("prompt_template"):
        lines.extend(fmt_prompt_template(agent["prompt_template"]))
        lines.append("")

    lines.append(f"### Evaluation examples ({len(items)})")
    lines.append("")

    for i, item in enumerate(items, 1):
        lines.extend(render_item(item, i))

    return lines


def render_manifest_table(manifest: dict[str, Any]) -> list[str]:
    lines = [
        "## Dataset index",
        "",
        f"- **Generated:** {manifest.get('generated_at', '—')}",
        f"- **Generator:** `{manifest.get('generator', '—')}`",
        f"- **Total datasets:** {manifest.get('total_datasets')}",
        f"- **Total examples:** {manifest.get('total_items')}",
        f"- **Skipped agents:** {', '.join(manifest.get('skipped_agents', [])) or 'none'}",
        "",
        "| S.no | Agent | Tier | Examples | Category |",
        "|------|-------|------|----------|----------|",
    ]
    for ds in manifest.get("datasets", []):
        tier = ds.get("tier", "").replace("_", " ").title()
        lines.append(
            f"| {ds.get('sno')} | {ds.get('agent_name')} | {tier} | "
            f"{ds.get('actual_examples')} | {ds.get('category_folder')} |"
        )
    lines.append("")
    return lines


def main() -> None:
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    excluded = (SOURCE / "EXCLUDED_AGENTS.md").read_text(encoding="utf-8").strip()
    readme = (SOURCE / "README.md").read_text(encoding="utf-8").strip()

    lines: list[str] = [
        "# Prompt Tiered Evaluation Datasets",
        "",
        "Human-readable reference for all golden datasets in `evals/datasets/prompt_tiered/`.",
        "Source JSON files are unchanged; this document is for review, planning, and manual eval.",
        "",
        "---",
        "",
        readme,
        "",
        "---",
        "",
        "## Excluded agents",
        "",
        excluded.split("\n", 1)[1].strip() if excluded.startswith("#") else excluded,
        "",
        "---",
        "",
    ]
    lines.extend(render_manifest_table(manifest))
    lines.append("---")
    lines.append("")

    for ds in manifest["datasets"]:
        path = ROOT / ds["path"]
        data = json.loads(path.read_text(encoding="utf-8"))
        lines.extend(render_dataset(data))
        lines.append("---")
        lines.append("")

  # Schema appendix
    schema = json.loads((SOURCE / "schema.json").read_text(encoding="utf-8"))
    lines.extend([
        "## Shared item schema",
        "",
        "Each dataset item follows this structure:",
        "",
        "| Field | Required | Description |",
        "|-------|----------|-------------|",
        "| `id` | yes | Unique example ID (e.g. `intent_classifier-001`) |",
        "| `variation` | yes | Eval axis: typo, diagram, security, follow_up, etc. |",
        "| `tags` | no | Board, subject, and filter tags |",
        "| `inputs` | yes | Variables passed to the Jinja prompt template |",
        "| `reference_outputs` | yes | Expected JSON, text, or judge criteria |",
        "| `evaluators` | no | Suggested automated checks |",
        "| `notes` | no | Optional reviewer notes |",
        "",
        "**Dataset-level fields:** `version`, `dataset_id`, `agent` (metadata + prompt), `langsmith`, `items`.",
        "",
        f"Schema version: **{schema.get('title', 'ScholarSync Tiered Prompt Dataset')}** (`{schema.get('properties', {}).get('version', {}).get('const', '1.0.0')}`)",
        "",
    ])

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written: {OUT}")
    print(f"Lines: {len(lines)}")
    print(f"Size bytes: {OUT.stat().st_size}")


if __name__ == "__main__":
    main()
