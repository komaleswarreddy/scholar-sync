#!/usr/bin/env python3
"""Extract per-agent Model 1/2/3 from Model Selection.xlsx GPT sub-rows."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent_eval.config import infer_provider
from evals.agent_eval.registry import DEFAULT_FALLBACK_MODELS, XLSX_AGENT_NAME_TO_ID, list_scope_agents

XLSX_PATH = ROOT / "Reference dataset" / "Model Selection.xlsx"
OUT_JSON = ROOT / "evals" / "agent_eval" / "agent_models.json"
MODELS_YAML = ROOT / "config" / "models.yaml"
PRICING_YAML = ROOT / "config" / "model_pricing.yaml"

SKIP_AGENTS = frozenset({"Intent Classifier Agent"})

# Pricing hints from xlsx GPT row ($ stripped)
DEFAULT_PRICING = {
    "gpt-5.4-mini": {"input_per_1m_usd": 0.75, "output_per_1m_usd": 4.50},
    "gpt-5.4-nano": {"input_per_1m_usd": 0.20, "output_per_1m_usd": 1.00},
    "gpt-5.4": {"input_per_1m_usd": 2.50, "output_per_1m_usd": 15.00},
    "claude-haiku-4-5": {"input_per_1m_usd": 1.00, "output_per_1m_usd": 5.00},
    "claude-sonnet-4-6": {"input_per_1m_usd": 3.00, "output_per_1m_usd": 15.00},
    "gemini-3.5-flash": {"input_per_1m_usd": 1.50, "output_per_1m_usd": 6.00},
    "gemini-3.1-flash-lite": {"input_per_1m_usd": 0.30, "output_per_1m_usd": 2.50},
    "deepseek-v4-flash": {"input_per_1m_usd": 0.14, "output_per_1m_usd": 0.28},
    "deepseek-chat": {"input_per_1m_usd": 0.14, "output_per_1m_usd": 0.28},
    "deepseek-reasoner": {"input_per_1m_usd": 0.55, "output_per_1m_usd": 2.19},
}


def _clean_model_id(raw: str) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s or s.upper().startswith("N/A"):
        return None
    s = s.replace("$", "").strip()
    return s


def _parse_gpt_rows() -> dict[str, list[dict]]:
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb["All Different LLM Responses"]
    cur_agent: str | None = None
    out: dict[str, list[dict]] = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[2]:
            cur_agent = str(row[2]).strip()
        llm_used = (row[5] or "").strip() if len(row) > 5 else ""
        if llm_used != "GPT" or not cur_agent or cur_agent in SKIP_AGENTS:
            continue
        agent_id = XLSX_AGENT_NAME_TO_ID.get(cur_agent)
        if not agent_id or agent_id not in list_scope_agents():
            continue

        models = []
        for col in (6, 9, 12):
            mid = _clean_model_id(row[col] if len(row) > col else None)
            if not mid:
                continue
            provider = infer_provider(mid)
            entry = {
                "model": mid,
                "provider": provider,
                "skip_runtime": provider in ("gemini", "deepseek", "unknown"),
                "configured": True,
            }
            if provider == "unknown":
                entry["flag"] = "unsupported_provider"
            models.append(entry)

        if not models:
            models = [
                {
                    "model": e["model"],
                    "provider": e["provider"],
                    "skip_runtime": False,
                    "configured": True,
                    "fallback": True,
                }
                for e in DEFAULT_FALLBACK_MODELS
            ]
        out[agent_id] = models

    return out


def _update_models_yaml(agent_models: dict[str, list[dict]], doc: dict) -> None:
    agents = doc.setdefault("agents", {})
    for agent_id, models in agent_models.items():
        cfg = agents.setdefault(agent_id, {})
        cfg["prompt_versions"] = ["v1", "v2", "v3"]
        cfg["default_prompt"] = "v1"
        cfg["models"] = [m["model"] for m in models if m.get("model")]


def extract(*, update_yaml: bool = True) -> dict:
    agent_models = _parse_gpt_rows()
    payload = {
        "source": str(XLSX_PATH),
        "sheet": "All Different LLM Responses",
        "row_filter": "LLM Used == GPT",
        "agents": agent_models,
        "runtime_skip": "gemini + deepseek + unknown (configured but skipped at runtime)",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if update_yaml:
        doc = yaml.safe_load(MODELS_YAML.read_text(encoding="utf-8")) or {}
        _update_models_yaml(agent_models, doc)
        MODELS_YAML.write_text(yaml.dump(doc, sort_keys=False, default_flow_style=False), encoding="utf-8")
        pricing_doc = yaml.safe_load(PRICING_YAML.read_text(encoding="utf-8")) or {}
        pricing = pricing_doc.setdefault("pricing", {})
        for mid, rates in DEFAULT_PRICING.items():
            pricing.setdefault(mid, rates)
        PRICING_YAML.write_text(yaml.dump(pricing_doc, sort_keys=False, default_flow_style=False), encoding="utf-8")

    report_path = ROOT / "evals" / "reports" / "agent_matrix" / "model_extraction_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"\nWrote {OUT_JSON}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-yaml", action="store_true")
    args = parser.parse_args()
    extract(update_yaml=not args.no_yaml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
