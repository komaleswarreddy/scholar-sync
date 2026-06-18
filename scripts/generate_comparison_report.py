#!/usr/bin/env python3
"""Generate prompt×model comparison markdown from experiment reports."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "evals" / "reports"
MANIFEST = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"
REGISTRY = ROOT / "prompts" / "registry.yaml"
MODELS = ROOT / "config" / "models.yaml"
OUT = ROOT / "evaluation" / "AGENT_PROMPT_MODEL_COMPARISON.generated.md"
MAIN_MD = ROOT / "evaluation" / "AGENT_DATASETS_AND_SCORING.md"

V2_DIFF = (
    "v2 adds: stricter NCERT/CBSE grounding, JSON-only output, reasoning ≤40 words, "
    "no chain-of-thought in output fields."
)

START = "<!-- COMPARISON_APPENDIX_START -->"
END = "<!-- COMPARISON_APPENDIX_END -->"


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _prompt_paths(agent_id: str, reg: dict) -> Dict[str, str]:
    block = (reg.get("agents") or {}).get(agent_id) or {}
    out: Dict[str, str] = {}
    for ver in ("v1", "v2"):
        vb = block.get(ver) or {}
        parts = []
        for k, v in vb.items():
            if k != "default":
                parts.append(f"{k}={v}")
        if parts:
            out[ver] = ", ".join(parts)
    return out


def _sample_example_ids(agent_id: str) -> List[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for ds in manifest.get("datasets") or []:
        if ds.get("dataset_id") == agent_id:
            path = ROOT / ds["path"]
            if path.is_file():
                doc = json.loads(path.read_text(encoding="utf-8"))
                items = doc.get("items") or []
                return [str(it.get("id", "")) for it in items[:3]]
    return []


def _agent_section(
    ds: dict,
    reg: dict,
    models_cfg: dict,
    report: dict | None,
) -> str:
    aid = ds["dataset_id"]
    agents = models_cfg.get("agents") or {}
    acfg = agents.get(aid) or {}
    paths = _prompt_paths(aid, reg)
    evaluator = acfg.get("evaluator", report.get("evaluator") if report else "formatter")
    threshold = acfg.get("passing_threshold", 90)
    models = acfg.get("models") or ["gpt-4o-mini"]
    sample_ids = _sample_example_ids(aid)

    lines = [
        f"### {ds.get('sno', '?')}. `{aid}` — {ds.get('agent_name', aid)}",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Tier | {ds.get('tier', '?')} ({ds.get('actual_examples', '?')} examples) |",
        f"| Local dataset | `{ds.get('path', '')}` |",
        f"| LangSmith dataset | `nbm-prompt-{aid}` |",
        f"| Evaluator | `{evaluator}` (pass ≥ {threshold}%) |",
        f"| Candidate models | {', '.join(models)} |",
        f"| Sample example IDs | {', '.join(sample_ids) or 'n/a'} |",
        "",
        "**Prompt versions**",
        "",
    ]
    for ver, p in paths.items():
        lines.append(f"- **{ver}**: `{p}`")
    if not paths:
        lines.append("- v1/v2: see dataset `agent.prompt_template` under `eval/` templates")
    lines.extend(["", f"**v1 vs v2 difference:** {V2_DIFF}", ""])

    if report and report.get("rows"):
        lines.extend([
            "**Prompt × model comparison**",
            "",
            "| Prompt | Model | Score | Pass rate | Input $ | Output $ | Total $ | Latency ms | Passed |",
            "|--------|-------|-------|-----------|---------|----------|---------|------------|--------|",
        ])
        for row in report["rows"]:
            lines.append(
                f"| {row.get('prompt')} | {row.get('model')} | {row.get('score')} | "
                f"{row.get('pass_rate')} | ${row.get('input_cost_usd', 0):.6f} | "
                f"${row.get('output_cost_usd', 0):.6f} | ${row.get('cost_usd', 0):.6f} | "
                f"{row.get('latency_ms')} | {'PASS' if row.get('passed') else 'FAIL'} |"
            )
        winner = report.get("winner") or {}
        lines.append("")
        if winner.get("selected"):
            w = winner.get("winner") or {}
            lines.append(
                f"**Best config:** prompt=`{w.get('prompt')}` model=`{w.get('model')}` "
                f"score={w.get('score')} total_cost=${w.get('cost_usd', 0):.6f} "
                f"(composite={winner.get('composite_score')})"
            )
        else:
            be = (winner.get("best_effort") or {})
            lines.append(
                f"**No config above threshold.** Best effort: prompt=`{be.get('prompt')}` "
                f"model=`{be.get('model')}` score={be.get('score')}"
            )
        lines.append(f"")
        lines.append(f"*Eval mode: {'live LLM' if report.get('live') else 'mock'} | batch: `{report.get('eval_batch_id', 'n/a')}`*")
        lines.append("")

        examples = report.get("example_results") or []
        if examples:
            ex = examples[0]
            lines.extend([
                "**Worked example (first result)**",
                "",
                f"- Example ID: `{ex.get('example_id')}` | variation: `{ex.get('variation')}` | "
                f"prompt: `{ex.get('prompt')}` | model: `{ex.get('model')}` | score: {ex.get('score')}",
                "",
                "```json",
                json.dumps({"inputs": ex.get("inputs"), "expected": ex.get("expected")}, indent=2)[:1200],
                "```",
                "",
            ])
    else:
        lines.append("*No experiment report yet — run `python eval.py --agent " + aid + " --limit 5`*")
        lines.append("")

    lines.extend([
        "**Verify in LangSmith:** Tracing → project `notebooklm-dev` → filter run name "
        f"`experiment/{aid}/` or `eval/{aid}/` → check metadata `prompt_version`, `input_cost_usd`.",
        "",
        "---",
        "",
    ])
    return "\n".join(lines)


def _overall_summary(all_reports: List[dict]) -> str:
    rows_flat: List[dict] = []
    total_cost = 0.0
    passed_agents = 0
    failed_agents: List[str] = []
    v1_wins = 0
    v2_wins = 0
    mini_wins = 0
    gpt4o_wins = 0

    for rep in all_reports:
        aid = rep.get("agent_name", "")
        winner = rep.get("winner") or {}
        if winner.get("selected"):
            passed_agents += 1
            w = winner.get("winner") or {}
            if w.get("prompt") == "v1":
                v1_wins += 1
            elif w.get("prompt") == "v2":
                v2_wins += 1
            if w.get("model") == "gpt-4o-mini":
                mini_wins += 1
            elif w.get("model") == "gpt-4o":
                gpt4o_wins += 1
        else:
            failed_agents.append(aid)
        for row in rep.get("rows") or []:
            rows_flat.append({**row, "agent": aid})
            total_cost += float(row.get("cost_usd") or 0)

    rows_flat.sort(key=lambda r: (-float(r.get("score") or 0), float(r.get("cost_usd") or 0)))
    top10 = rows_flat[:10]

    lines = [
        "## Overall summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Agents evaluated | {len(all_reports)} |",
        f"| Agents with winner above threshold | {passed_agents} |",
        f"| Agents below threshold | {len(failed_agents)} |",
        f"| Total eval cost (all rows) | ${total_cost:.4f} |",
        f"| v1 prompt wins | {v1_wins} |",
        f"| v2 prompt wins | {v2_wins} |",
        f"| gpt-4o-mini wins | {mini_wins} |",
        f"| gpt-4o wins | {gpt4o_wins} |",
        "",
    ]
    if failed_agents:
        lines.append(f"**Below threshold:** {', '.join(failed_agents)}")
        lines.append("")

    lines.extend([
        "### Top 10 prompt×model configurations (by score, then cost)",
        "",
        "| Rank | Agent | Prompt | Model | Score | Total $ | Passed |",
        "|------|-------|--------|-------|-------|---------|--------|",
    ])
    for i, r in enumerate(top10, 1):
        lines.append(
            f"| {i} | {r.get('agent')} | {r.get('prompt')} | {r.get('model')} | "
            f"{r.get('score')} | ${r.get('cost_usd', 0):.6f} | "
            f"{'PASS' if r.get('passed') else 'FAIL'} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reg = _load_yaml(REGISTRY)
    models_cfg = _load_yaml(MODELS)
    datasets = manifest.get("datasets") or []

    all_reports: List[dict] = []
    sections: List[str] = [
        "# Agent prompt × model comparison (auto-generated)",
        "",
        f"*Generated: {datetime.now(timezone.utc).isoformat()}*",
        "",
        "Do not edit manually — regenerate with `python scripts/generate_comparison_report.py`.",
        "",
    ]

    for ds in datasets:
        aid = ds["dataset_id"]
        rep_path = REPORTS / f"experiment_{aid}.json"
        report = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.is_file() else None
        if report:
            all_reports.append(report)
        sections.append(_agent_section(ds, reg, models_cfg, report))

    sections.insert(4, _overall_summary(all_reports))
    return "\n".join(sections)


def _merge_into_main_md(generated: str) -> None:
    ui_guide = """

## How to verify in LangSmith (2026 UI)

| Goal | Where to navigate | What to filter |
|------|-------------------|----------------|
| Eval traces | **Tracing** (sidebar) → project `notebooklm-dev` | Run name contains `eval/` or `experiment/` |
| Prompt comparison | Run detail → **Metadata** | `prompt_version`: `v1` vs `v2` |
| Input/output cost | Run → **Metadata** or **Feedback** | `input_cost_usd`, `output_cost_usd`, `total_cost_usd` |
| Pass/fail scores | Run → **Feedback** | `weighted_score`, `passed`, `metric_*` |
| Dataset examples | **Datasets & Experiments** → `nbm-prompt-{agent}` | Examples tab |
| Model leaderboard | Tracing → filter `experiment/{agent}/` | Sort by `weighted_score` feedback |
| Monitoring charts | **Monitoring** → project `notebooklm-dev` | Date range = today; tabs **LLM Calls**, **Cost & Tokens** |

### Why Monitoring looked empty

1. **Wrong project** — select `notebooklm-dev` explicitly (not org-wide default).
2. **run_type was `chain`** — eval runs now use `run_type=llm` so **LLM Calls** and **Cost & Tokens** populate.
3. **Date filter** — set range to include your eval batch date.
4. **Sidebar count ≠ Monitoring chart** — open **Tracing** list for individual runs; Monitoring aggregates over time.

Filter by eval batch: metadata `eval_batch_id` (e.g. `20260617T120000Z`).

---

## Suggested next steps

- **LangSmith `evaluate()` API** — link datasets to experiment sessions for native Experiments UI
- **Human review queue** — wire `evaluation/human_review.yaml` for failed examples
- **Annotation queues** — route sub-threshold runs to LangSmith annotation
- **Custom dashboards** — chart `weighted_score` by `prompt_version` and `model`
- **Production online eval** — sample live chat traces with same evaluators
- **CI hard-gate** — fail PR when pass_rate drops below threshold
- **Cost caps** — `--max-cost-usd` on publish script
- **CSV export** — spreadsheet export from `experiment_*.json`
- **Prompt diff viewer** — compare v1 vs v2 Jinja files in repo

"""

    if MAIN_MD.is_file():
        text = MAIN_MD.read_text(encoding="utf-8")
        block = f"{START}\n{generated}\n{END}"
        if START in text and END in text:
            pre = text[: text.index(START)]
            post = text[text.index(END) + len(END) :]
            text = pre + block + post
        else:
            text = text.rstrip() + "\n\n" + block + ui_guide
        if "## How to verify in LangSmith" not in text:
            text += ui_guide
        MAIN_MD.write_text(text, encoding="utf-8")


def main() -> int:
    body = generate()
    OUT.write_text(body, encoding="utf-8")
    _merge_into_main_md(body)
    print(f"Wrote {OUT}")
    print(f"Merged into {MAIN_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
