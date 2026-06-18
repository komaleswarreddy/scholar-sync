#!/usr/bin/env python3
"""Generate v2 prompt templates from v1 + dataset-only agents. Updates registry.yaml."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "packages" / "core" / "prompts" / "templates"
REGISTRY = ROOT / "prompts" / "registry.yaml"
MANIFEST = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"

V2_SUFFIX = """
{# === v2 prompt variant: stricter CBSE/NCERT + JSON contract === #}
CRITICAL (v2 instructions):
- Ground responses in NCERT/CBSE syllabus vocabulary when the task is educational.
- Output ONLY the required JSON or format — no markdown fences, no text before/after JSON.
- Keep reasoning fields to 40 words or fewer.
- Think step-by-step internally; do not reveal chain-of-thought outside required fields.
"""

MISSING_AGENTS = [
    "query_decomposer",
    "chat_policy_block",
    "hallucination_guard_retry",
    "studio_context_embedding_query",
    "whole_file_map_template",
    "image_ocr",
    "diagram_label_ocr",
    "refusal_templates",
]


def _v2_path(rel: str) -> str:
    if rel.endswith(".j2"):
        return rel.replace(".j2", "_v2.j2")
    return rel + "_v2"


def _write_v2_from_v1(rel_path: str) -> str:
    src = TEMPLATES / rel_path
    if not src.is_file():
        return rel_path
    dst_rel = _v2_path(rel_path)
    dst = TEMPLATES / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8")
    if "_v2 prompt variant" not in content:
        dst.write_text(content.rstrip() + "\n" + V2_SUFFIX, encoding="utf-8")
    return dst_rel


def _dataset_template(agent_id: str) -> str | None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for ds in manifest.get("datasets") or []:
        if ds.get("dataset_id") == agent_id:
            path = ROOT / ds["path"]
            if path.is_file():
                doc = json.loads(path.read_text(encoding="utf-8"))
                return doc.get("agent", {}).get("prompt_template")
    return None


def main() -> int:
    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {"agents": {}}
    agents = reg.setdefault("agents", {})

    for agent_id, block in list(agents.items()):
        v1 = block.get("v1") or {}
        v2 = {}
        for key, rel in v1.items():
            if key == "default":
                continue
            v2[key] = _write_v2_from_v1(str(rel))
        if v2:
            block["v2"] = v2

    eval_dir = TEMPLATES / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    for agent_id in MISSING_AGENTS:
        tmpl = _dataset_template(agent_id)
        if not tmpl:
            print(f"WARN: no dataset template for {agent_id}")
            continue
        v1_rel = f"eval/{agent_id}_v1.j2"
        v2_rel = f"eval/{agent_id}_v2.j2"
        v1_path = TEMPLATES / v1_rel
        v2_path = TEMPLATES / v2_rel
        if not v1_path.is_file():
            v1_path.write_text(tmpl.strip() + "\n", encoding="utf-8")
        if not v2_path.is_file():
            v2_path.write_text(tmpl.strip() + "\n" + V2_SUFFIX, encoding="utf-8")
        agents[agent_id] = {
            "v1": {"template": v1_rel},
            "v2": {"template": v2_rel},
            "default": "v1",
        }

    REGISTRY.write_text(
        yaml.dump(reg, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Updated {REGISTRY} with v2 entries for {len(agents)} agents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
