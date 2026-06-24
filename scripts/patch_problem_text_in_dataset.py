#!/usr/bin/env python3
"""Patch problem/document text in Complete_Agent_DataSet.md (text-only, keeps LLM gold)."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
POOL_17_22 = SCRIPTS / "problem_solver_eval_pool.json"
POOL_23_25 = SCRIPTS / "agents_23_25_eval_pool.json"
BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"

AGENT_17_START = "## 17. Problem DNA Analyzer"
AGENT_23_START = "## 23. Tutor Notebook Bootstrap Agent"
AGENT_25_START = "## 25. Source Question Extraction Agent"


def _page_document_text(source_key: str, page: int, by_page: dict[tuple[str, int], list[dict]]) -> str:
    qs = by_page.get((source_key, page), [])
    if not qs:
        return ""
    raw = (qs[0].get("raw_text") or "").strip()
    if len(raw) >= 80:
        return raw[:4000]
    return "\n\n".join(q["problem_text_normalized"] for q in qs)[:4000]


def _refresh_agent25_document_text(pool: dict) -> int:
    if not BANK_PATH.exists():
        return 0
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    by_page: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for q in bank["questions"]:
        by_page[(q["source_key"], int(q["page"]))].append(q)

    updated = 0
    for item in pool.get("items", []):
        if item.get("agent_num") != 25:
            continue
        sk = item.get("source_key")
        page = item.get("page")
        if not sk or not page:
            continue
        new_text = _page_document_text(sk, int(page), by_page)
        if new_text and new_text != item.get("document_text"):
            item["document_text"] = new_text
            updated += 1
    return updated


def _patch_problem_text_block(section: str, example_id: str, new_text: str) -> tuple[str, bool]:
    pattern = (
        rf"(#### Example \d+: `{re.escape(example_id)}`"
        rf"[\s\S]*?\*\*Problem Text Normalized:\*\*\s*\n\n)"
        rf"([\s\S]*?)"
        rf"(\n\n\*\*Ncert Context:\*\*)"
    )
    match = re.search(pattern, section)
    if not match:
        return section, False
    replacement = match.group(1) + new_text.strip() + match.group(3)
    return section[: match.start()] + replacement + section[match.end() :], True


def _patch_document_text_block(section: str, example_id: str, new_text: str) -> tuple[str, bool]:
    pattern = (
        rf"(#### Example \d+: `{re.escape(example_id)}`"
        rf"[\s\S]*?\*\*Document Text:\*\*\s*\n\n)"
        rf"([\s\S]*?)"
        rf"(\n\n\*\*Expected output\*\*)"
    )
    match = re.search(pattern, section)
    if not match:
        return section, False
    replacement = match.group(1) + new_text.strip() + match.group(3)
    return section[: match.start()] + replacement + section[match.end() :], True


def _patch_variation_tag(section: str, example_id: str, variation: str, tags: list[str]) -> tuple[str, bool]:
    pattern = rf"(#### Example \d+: `{re.escape(example_id)}`\s*\n\n)- \*\*Variation:\*\* [^\n]+\n(- \*\*Tags:\*\* )([^\n]+)"
    match = re.search(pattern, section)
    if not match:
        return section, False
    tag_str = ", ".join(tags)
    replacement = f"{match.group(1)}- **Variation:** {variation}\n{match.group(2)}{tag_str}"
    return section[: match.start()] + replacement + section[match.end() :], True


def main() -> int:
    if not MD.exists():
        print(f"Missing dataset: {MD}", file=sys.stderr)
        return 1
    if not POOL_17_22.exists():
        print(f"Missing pool: {POOL_17_22}", file=sys.stderr)
        return 1

    text = MD.read_text(encoding="utf-8")
    pool_17_22 = json.loads(POOL_17_22.read_text(encoding="utf-8"))
    by_example = {
        item["example_id"]: item["problem_text_normalized"]
        for item in pool_17_22.get("items", [])
    }

    start_17 = text.find(AGENT_17_START)
    end_17 = text.find(AGENT_23_START)
    if start_17 < 0 or end_17 < 0:
        print("Could not locate Agents 17–22 section boundaries", file=sys.stderr)
        return 1

    section_17_22 = text[start_17:end_17]
    patched_17_22 = 0
    for example_id, problem_text in by_example.items():
        section_17_22, ok = _patch_problem_text_block(section_17_22, example_id, problem_text)
        if ok:
            patched_17_22 += 1
    text = text[:start_17] + section_17_22 + text[end_17:]

    patched_25 = 0
    if POOL_23_25.exists():
        pool_23_25 = json.loads(POOL_23_25.read_text(encoding="utf-8"))
        refreshed = _refresh_agent25_document_text(pool_23_25)
        if refreshed:
            pool_23_25["version"] = "1.4.3"
            POOL_23_25.write_text(
                json.dumps(pool_23_25, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Refreshed {refreshed} Agent 25 document_text entries in pool")

        start_25 = text.find(AGENT_25_START)
        start_23 = text.find(AGENT_23_START)
        if start_23 >= 0:
            end_23_25 = len(text) if start_25 < 0 else start_25
            section_23_24 = text[start_23:end_23_25]
            patched_var = 0
            for item in pool_23_25.get("items", []):
                if item.get("agent_num") not in (23, 24):
                    continue
                ex_id = item["example_id"]
                section_23_24, ok = _patch_variation_tag(
                    section_23_24, ex_id, item["variation"], item.get("tags", [])
                )
                if ok:
                    patched_var += 1
            text = text[:start_23] + section_23_24 + text[end_23_25:]
            print(f"Patched {patched_var} variation tags (Agents 23–24)")

        if start_25 >= 0:
            section_25 = text[start_25:]
            patched_var_25 = 0
            for item in pool_23_25.get("items", []):
                ex_id = item["example_id"]
                if item.get("agent_num") == 25:
                    section_25, ok = _patch_variation_tag(
                        section_25, ex_id, item["variation"], item.get("tags", [])
                    )
                    if ok:
                        patched_var_25 += 1
                    doc = item.get("document_text", "")
                    section_25, ok = _patch_document_text_block(section_25, ex_id, doc)
                    if ok:
                        patched_25 += 1
            if patched_var_25:
                print(f"Patched {patched_var_25} variation tags (Agent 25)")
            text = text[:start_25] + section_25

    MD.write_text(text, encoding="utf-8")
    print(f"Patched {patched_17_22} Problem Text Normalized blocks (Agents 17–22)")
    print(f"Patched {patched_25} Document Text blocks (Agent 25)")
    print(f"Updated {MD} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
