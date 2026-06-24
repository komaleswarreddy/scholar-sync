#!/usr/bin/env python3
"""Sync prompt sections in Complete_Agent_DataSet.md from production templates and fragments."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
SCRIPTS = ROOT / "scripts"
POLICY = ROOT / "packages" / "core" / "prompts" / "policies" / "chat_policy.default.yaml"
PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates"


def replace_agent_section(text: str, header: str, next_header: str, fragment: str) -> str:
    start = text.find(header)
    if start < 0:
        raise SystemExit(f"Missing section header: {header!r}")
    end = text.find(next_header, start + len(header))
    if end < 0:
        raise SystemExit(f"Missing next header after {header!r}: {next_header!r}")
    body = fragment.strip() + "\n\n"
    return text[:start] + body + text[end:]


def patch_agent5_yaml(fragment_path: Path) -> None:
    yaml_text = POLICY.read_text(encoding="utf-8").strip()
    frag = fragment_path.read_text(encoding="utf-8")
    new_frag, n = re.subn(
        r"```yaml\n.*?```",
        "```yaml\n" + yaml_text + "\n```",
        frag,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise SystemExit("agent5 yaml block not found")
    fragment_path.write_text(new_frag, encoding="utf-8")


def extract_agent_from_combined(combined: str, header: str, next_header: str | None) -> str:
    start = combined.find(header)
    if start < 0:
        raise SystemExit(f"Missing {header} in combined fragment")
    if next_header:
        end = combined.find(next_header, start + len(header))
        if end < 0:
            return combined[start:].strip()
        return combined[start:end].strip()
    return combined[start:].strip()


def main() -> None:
    agent5_path = SCRIPTS / "agent5_chat_policy_block.md"
    patch_agent5_yaml(agent5_path)

    text = MD.read_text(encoding="utf-8")

    replacements = [
        ("## 5. Chat Policy Block (YAML)", "## 6.", agent5_path.read_text(encoding="utf-8")),
        ("## 10. Studio System Prompt (JSON tasks)", "## 11.", (SCRIPTS / "agent10_studio_system_json.md").read_text(encoding="utf-8")),
        ("## 11. Studio Quiz Generator", "## 12.", (SCRIPTS / "agent11_studio_quiz.md").read_text(encoding="utf-8")),
        ("## 12. Studio Flashcards Generator", "## 13.", (SCRIPTS / "agent12_studio_flashcards.md").read_text(encoding="utf-8")),
    ]
    for header, nxt, frag in replacements:
        text = replace_agent_section(text, header, nxt, frag)

    ps_combined = (SCRIPTS / "agents_17_22_problem_solver.md").read_text(encoding="utf-8")
    for header, nxt in (
        ("## 17. Problem DNA Analyzer", "## 18."),
        ("## 19. Show Best Approach Coach", "## 20."),
    ):
        frag = extract_agent_from_combined(ps_combined, header, nxt)
        text = replace_agent_section(text, header, nxt, frag)

    MD.write_text(text, encoding="utf-8")
    print(f"Updated {MD}")


if __name__ == "__main__":
    main()
