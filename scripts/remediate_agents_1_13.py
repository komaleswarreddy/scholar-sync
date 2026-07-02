#!/usr/bin/env python3
"""
Run / verify agents 1–13 on dedicated LangSmith workspaces and update testing_Results.csv.

Workflow per agent:
  1. Switch workspace
  2. Discover experiments (checkpoint + LangSmith projects on tenant)
  3. Validate 100% output fill vs dataset size
  4. Fix: purge partial/failed checkpoint entries, re-run missing combos
  5. Write production sheet row (spaced links, Gemini issue notes)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from evals.agent_eval.config import PROMPT_VERSIONS, dataset_name, get_agent_models  # noqa: E402
from langsmith import Client

# Workspace registry (mirrors scripts/switch_workspace.py)
WORKSPACES: dict[str, dict[str, str]] = {
    "pscmrmindssprint2k25": {
        "tenant": "15d476d5-df92-4760-96b8-52f9130946bf",
        "key": "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",
        "gmail": "pscmrmindssprint2k25@gmail.com",
    },
    "scombinator26": {
        "tenant": "47ca8a69-43eb-4f05-812b-c7778fe6987d",
        "key": "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",
        "gmail": "scombinator26@gmail.com",
    },
    "emaildam3": {
        "tenant": "aafff4b5-45a3-4448-9f7d-805bfc70098d",
        "key": "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",
        "gmail": "emaildam3@gmail.com",
    },
    "gra7399": {
        "tenant": "67272628-c819-44db-bbda-e500db0d6982",
        "key": "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",
        "gmail": "gra7399@gmail.com",
    },
    "sui332307": {
        "tenant": "33d88f33-0349-4117-89c6-5d0d56252773",
        "key": "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",
        "gmail": "sui332307@gmail.com",
    },
    "eskomal66": {
        "tenant": "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b",
        "key": "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",
        "gmail": "eskomal66@gmail.com",
    },
    "cursemes9": {
        "tenant": "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7",
        "key": "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",
        "gmail": "cursemes9@gmail.com",
    },
    "sujithgundala97": {
        "tenant": "bf982111-f0d4-424f-9520-3605217266b1",
        "key": "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",
        "gmail": "sujith.gundala97@gmail.com",
    },
    "kumarsujith006": {
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "key": "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",
        "gmail": "kumarsujith006@gmail.com",
    },
    "citizena45": {
        "tenant": "9fced417-9e4c-442f-bcda-d11a78caaec8",
        "key": "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",
        "gmail": "citizena45@gmail.com",
    },
}
# Uncapped workspaces preferred for fallback runs (checked live before use).
FALLBACK_ORDER = (
    "citizena45",
    "sujithgundala97",
    "kumarsujith006",
    "emaildam3",
    "gra7399",
    "sui332307",
    "pscmrmindssprint2k25",
)
AGENTS_14_21_WORKSPACES = ("sujithgundala97", "kumarsujith006")

CSV_PATH = ROOT / "Reference dataset" / "testing_Results.csv"
AGENT_MODELS_PATH = ROOT / "evals" / "agent_eval" / "agent_models.json"
CHECKPOINT = ROOT / "evals" / "reports" / "agent_matrix" / "step_checkpoint.json"
NOTES_COL = "Run Issues / Notes"

AGENTS_1_13: list[dict[str, Any]] = [
    {
        "sno": 1,
        "name": "Intent Classifier",
        "agent_id": "intent_classifier",
        "workspace": "pscmrmindssprint2k25",
        "tenant": "15d476d5-df92-4760-96b8-52f9130946bf",
        "gmail": "pscmrmindssprint2k25@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "295b86be-1402-43ff-939d-538344ae7905",
        "harness": "intent_classifier",
        "rerun": "verify",
    },
    {
        "sno": 2,
        "name": "Query Rewriter",
        "agent_id": "query_rewriter",
        "workspace": "scombinator26",
        "tenant": "47ca8a69-43eb-4f05-812b-c7778fe6987d",
        "gmail": "scombinator26@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "84a1c3ca-4fee-4806-8e29-0eca58633d1f",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 3,
        "name": "Query Decomposer",
        "agent_id": "query_decomposer",
        "workspace": "scombinator26",
        "tenant": "47ca8a69-43eb-4f05-812b-c7778fe6987d",
        "gmail": "scombinator26@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "c3328aa5-c137-4e01-a6e8-02054d4ce5ed",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 4,
        "name": "Scope Narrower",
        "agent_id": "scope_narrower",
        "workspace": "scombinator26",
        "tenant": "47ca8a69-43eb-4f05-812b-c7778fe6987d",
        "gmail": "scombinator26@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "02275774-755e-45fa-aa0f-3f64c1cfc0b1",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 5,
        "name": "Direct Chat",
        "agent_id": "direct_chat",
        "workspace": "emaildam3",
        "tenant": "aafff4b5-45a3-4448-9f7d-805bfc70098d",
        "gmail": "emaildam3@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "e3f9e470-cdb8-4400-a079-aa9411f0117d",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 6,
        "name": "Chat Summarizer",
        "agent_id": "chat_summarizer",
        "workspace": "emaildam3",
        "tenant": "aafff4b5-45a3-4448-9f7d-805bfc70098d",
        "gmail": "emaildam3@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "813c16ca-3306-4204-9662-c34bca691b95",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 7,
        "name": "RAG Chat Response Generator",
        "agent_id": "rag_chat_response_generator",
        "workspace": "emaildam3",
        "tenant": "aafff4b5-45a3-4448-9f7d-805bfc70098d",
        "gmail": "emaildam3@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "626b2e4e-dcc5-4610-ad1f-5fd2e66fefc7",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 8,
        "name": "Studio System JSON",
        "agent_id": "studio_system_json",
        "workspace": "gra7399",
        "tenant": "67272628-c819-44db-bbda-e500db0d6982",
        "gmail": "gra7399@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "ce80306d-aaf4-420c-929f-12f3fc4d7e25",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 9,
        "name": "Studio Quiz",
        "agent_id": "studio_quiz",
        "workspace": "gra7399",
        "tenant": "67272628-c819-44db-bbda-e500db0d6982",
        "gmail": "gra7399@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "5d6d7d20-a35f-4cf4-b0bc-1f811ce3c8c3",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 10,
        "name": "Studio Flashcards",
        "agent_id": "studio_flashcards",
        "workspace": "sui332307",
        "tenant": "33d88f33-0349-4117-89c6-5d0d56252773",
        "gmail": "sui332307@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "ed0b1f2a-6909-42c0-bb19-706d07713f6f",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 11,
        "name": "Studio Mind Map",
        "agent_id": "studio_mind_map",
        "workspace": "sui332307",
        "tenant": "33d88f33-0349-4117-89c6-5d0d56252773",
        "gmail": "sui332307@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "85b7f4ee-2126-44c2-9f31-af7584fdc28e",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 12,
        "name": "Studio Slide Deck",
        "agent_id": "studio_slide_deck",
        "workspace": "sui332307",
        "tenant": "33d88f33-0349-4117-89c6-5d0d56252773",
        "gmail": "sui332307@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "d7a057aa-284a-4dd8-86d4-ab0d0926e3c8",
        "harness": "agent_eval",
        "rerun": "verify",
    },
    {
        "sno": 13,
        "name": "Studio Fallback Legacy",
        "agent_id": "studio_fallback_legacy",
        "workspace": "eskomal66",
        "tenant": "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b",
        "gmail": "eskomal66@gmail.com",
        "password": "asdfvbnm1234",
        "dataset_id": "c2a6c1e7-7297-4ff1-ab3c-2be5712a9076",
        "harness": "agent_eval",
        "rerun": "verify",
    },
]

AGENTS_14_21: list[dict[str, Any]] = [
    {
        "sno": 14,
        "name": "Problem DNA Analyzer",
        "agent_id": "problem_dna_analyzer",
        "workspace": "citizena45",
        "tenant": "9fced417-9e4c-442f-bcda-d11a78caaec8",
        "gmail": "citizena45@gmail.com",
        "password": "",
        "dataset_id": "3884fde6-91ed-424e-aed4-41ad68ce53b3",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 15,
        "name": "Whole File Reduce",
        "agent_id": "whole_file_reduce",
        "workspace": "sujithgundala97",
        "tenant": "bf982111-f0d4-424f-9520-3605217266b1",
        "gmail": "sujith.gundala97@gmail.com",
        "password": "Password123@",
        "dataset_id": "bcb824c0-d345-4b90-aa40-18157e16b0ab",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 16,
        "name": "Whole File Map Summarizer",
        "agent_id": "whole_file_map_summarizer",
        "workspace": "sujithgundala97",
        "tenant": "bf982111-f0d4-424f-9520-3605217266b1",
        "gmail": "sujith.gundala97@gmail.com",
        "password": "Password123@",
        "dataset_id": "78278c36-6755-4863-b6bd-3f09b60d5c4f",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 17,
        "name": "Explain From Basics",
        "agent_id": "explain_from_basics",
        "workspace": "kumarsujith006",
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "gmail": "kumarsujith006@gmail.com",
        "password": "Password123@",
        "dataset_id": "e3223208-28ac-4ea6-b9cd-a9d3feda5901",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 18,
        "name": "Show Best Approach",
        "agent_id": "show_best_approach",
        "workspace": "kumarsujith006",
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "gmail": "kumarsujith006@gmail.com",
        "password": "Password123@",
        "dataset_id": "a8db66c6-3bb8-4fc0-9bea-9f0b899f1922",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 19,
        "name": "Show Missing Idea",
        "agent_id": "show_missing_idea",
        "workspace": "kumarsujith006",
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "gmail": "kumarsujith006@gmail.com",
        "password": "Password123@",
        "dataset_id": "894b6e87-01b5-4c22-804a-34934044c0be",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 20,
        "name": "NCERT Document Sketch",
        "agent_id": "ncert_document_sketch",
        "workspace": "kumarsujith006",
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "gmail": "kumarsujith006@gmail.com",
        "password": "Password123@",
        "dataset_id": "61abca7e-7a3a-4239-b67f-606e8fb05440",
        "harness": "agent_eval",
        "rerun": "step",
    },
    {
        "sno": 21,
        "name": "Help Me Solve It",
        "agent_id": "help_me_solve_it",
        "workspace": "kumarsujith006",
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "gmail": "kumarsujith006@gmail.com",
        "password": "Password123@",
        "dataset_id": "7ea61a2d-cb6f-4d33-ba75-f39876d84ba4",
        "harness": "agent_eval",
        "rerun": "step",
    },
]

ALL_AGENTS = AGENTS_1_13 + AGENTS_14_21

SESSION_RE = re.compile(
    r"https://smith\.langchain\.com/o/([a-f0-9-]+)/datasets/([a-f0-9-]+)/compare\?selectedSessions=([a-f0-9-]+)"
)


def _switch_workspace(key: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "switch_workspace.py"), key],
        check=True,
        cwd=str(ROOT),
    )
    # Child switch_workspace.py writes .env; reload so Client() uses the new API key.
    load_dotenv(ROOT / ".env", override=True)
    ws = WORKSPACES.get(key)
    if ws:
        os.environ["LANGSMITH_API_KEY"] = ws["key"]


def _make_client() -> Client:
    load_dotenv(ROOT / ".env", override=True)
    return Client()


def _is_workspace_capped(workspace_name: str) -> bool:
    """True when LangSmith workspace is in_reject_set (monthly trace cap hit)."""
    import os

    import requests

    ws = WORKSPACES.get(workspace_name)
    if not ws:
        return True
    endpoint = (os.environ.get("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com").rstrip(
        "/"
    )
    try:
        resp = requests.get(
            f"{endpoint}/api/v1/workspaces/current/usage_limits",
            headers={"x-api-key": ws["key"]},
            timeout=15,
        )
        if resp.ok:
            return bool(resp.json().get("in_reject_set"))
    except Exception:
        pass
    return False


def _resolve_workspace(meta: dict, *, need_run: bool) -> tuple[dict, str | None]:
    """Use primary workspace for verify; pick uncapped fallback when runs are needed."""
    primary = meta["workspace"]
    if not need_run:
        return meta, None
    if not _is_workspace_capped(primary):
        return meta, None
    for fb in FALLBACK_ORDER:
        if fb == primary or _is_workspace_capped(fb):
            continue
        ws = WORKSPACES[fb]
        updated = {
            **meta,
            "workspace": fb,
            "tenant": ws["tenant"],
            "gmail": ws["gmail"],
            "primary_workspace": primary,
        }
        note = (
            f"WORKSPACE FALLBACK - primary {primary} trace-capped; "
            f"runs executed on {fb} ({ws['tenant']})"
        )
        print(f"  [!] {primary} trace-capped -> fallback {fb}")
        return updated, note
    return meta, f"TRACE CAP — {primary} and all fallbacks capped; verify-only"


def _ensure_dataset_uploaded(agent_id: str) -> str | None:
    """Ensure dataset exists on active workspace; upload if missing."""
    client = _make_client()
    ds_name = dataset_name(agent_id)
    try:
        ds = client.read_dataset(dataset_name=ds_name)
        return str(ds.id)
    except Exception:
        pass
    print(f"  Uploading dataset {ds_name} to active workspace...")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "upload_prompt_tiered_to_langsmith.py"),
            "--agent",
            agent_id,
        ],
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return None
    try:
        ds = client.read_dataset(dataset_name=ds_name)
        return str(ds.id)
    except Exception:
        return None


def _existing_csv_links(agent_id: str) -> list[str]:
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    header = rows[0]
    try:
        aid_idx = header.index("Agent ID")
        links_idx = header.index("LangSmith Compare Links")
    except ValueError:
        return []
    for row in rows[1:]:
        if len(row) > aid_idx and row[aid_idx].strip() == agent_id:
            cell = row[links_idx] if len(row) > links_idx else ""
            return [u.strip() for u in re.split(r"\s+", cell or "") if u.strip().startswith("http")]
    return []


def _load_checkpoint() -> dict:
    if not CHECKPOINT.exists():
        return {"completed": {}}
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def _save_checkpoint(ckpt: dict) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(ckpt, indent=2), encoding="utf-8")


def _experiment_key(agent_id: str, prompt_version: str, provider: str, model: str) -> str:
    return f"{agent_id}::{prompt_version}::{provider}::{model}"


def _active_tenant() -> str:
    key = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
    for ws in WORKSPACES.values():
        if ws["key"] == key:
            return ws["tenant"]
    return ""


def _compare_url(client: Client, tenant: str, agent_id: str, experiment_name: str) -> str | None:
    try:
        proj = client.read_project(project_name=experiment_name)
        session_id = str(proj.id)
        ds_id = str(getattr(proj, "reference_dataset_id", "") or "")
        if not ds_id:
            ds_id = str(client.read_dataset(dataset_name=dataset_name(agent_id)).id)
        url_tenant = _active_tenant() or tenant
        return (
            f"https://smith.langchain.com/o/{url_tenant}/datasets/{ds_id}"
            f"/compare?selectedSessions={session_id}"
        )
    except Exception:
        return None


def _output_fill_rate(
    client: Client, experiment_name: str, project_id: str = ""
) -> tuple[int, int, int]:
    """Return (filled, total, error_count) for root runs."""
    filled = 0
    total = 0
    errors = 0
    offset = 0
    while True:
        kwargs: dict[str, Any] = {"is_root": True, "limit": 100, "offset": offset}
        if project_id:
            kwargs["project_id"] = project_id
        else:
            kwargs["project_name"] = experiment_name
        batch = list(client.list_runs(**kwargs))
        if not batch:
            break
        total += len(batch)
        for r in batch:
            if r.error:
                errors += 1
            elif isinstance(r.outputs, dict) and bool(r.outputs.keys()):
                filled += 1
        if len(batch) < 100:
            break
        offset += len(batch)
    return filled, total, errors


def _dataset_size(client: Client, agent_id: str) -> int:
    try:
        ds = client.read_dataset(dataset_name=dataset_name(agent_id))
        return len(list(client.list_examples(dataset_id=ds.id)))
    except Exception:
        pass
    try:
        from packages.core.evaluation.datasets.loader import load_agent_dataset

        return len(load_agent_dataset(agent_id))
    except Exception:
        return 50


def _norm_label(label: str) -> str:
    return label.replace(".", "-").replace("/", "-").lower()


def _parse_experiment_name(name: str, agent_id: str) -> dict[str, str] | None:
    prefix = f"ae-{agent_id}-"
    if not name.startswith(prefix):
        return None
    rest = name[len(prefix) :]
    for pv in PROMPT_VERSIONS:
        pv_prefix = f"{pv}-"
        if not rest.startswith(pv_prefix):
            continue
        tail = rest[len(pv_prefix) :]
        specs = sorted(get_agent_models(agent_id), key=lambda s: len(s.label), reverse=True)
        for spec in specs:
            for label in (spec.label, spec.label.replace(".", "-")):
                label_prefix = f"{label}-"
                if tail.lower().startswith(label_prefix.lower()):
                    return {
                        "experiment_name": name,
                        "prompt_version": pv,
                        "provider": spec.provider,
                        "model": spec.model,
                        "agent_id": agent_id,
                    }
    return None


def _discover_from_csv(agent_id: str, tenant: str, client: Client) -> list[dict]:
    """Resolve experiment names from existing sheet compare links (session IDs)."""
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    header = rows[0]
    try:
        aid_idx = header.index("Agent ID")
        links_idx = header.index("LangSmith Compare Links")
    except ValueError:
        return []
    links_cell = ""
    for row in rows[1:]:
        if len(row) > aid_idx and row[aid_idx].strip() == agent_id:
            links_cell = row[links_idx] if len(row) > links_idx else ""
            break
    found: dict[str, dict] = {}
    for match in SESSION_RE.finditer(links_cell or ""):
        link_tenant, ds_id, session_id = match.groups()
        try:
            proj = client.read_project(project_id=session_id)
            name = str(getattr(proj, "name", "") or "")
            meta = _parse_experiment_name(name, agent_id)
            if meta:
                meta = dict(meta)
                meta["session_id"] = session_id
                meta["compare_url"] = (
                    f"https://smith.langchain.com/o/{link_tenant}/datasets/{ds_id}"
                    f"/compare?selectedSessions={session_id}"
                )
                found[name] = meta
        except Exception:
            continue
    return list(found.values())


def _discover_langsmith_experiments(client: Client, agent_id: str) -> list[dict]:
    found: dict[str, dict] = {}
    prefix = f"ae-{agent_id}-"
    try:
        projects = list(client.list_projects(name_contains=prefix))
    except Exception:
        projects = []
    for proj in projects:
        name = str(getattr(proj, "name", "") or "")
        if not name.startswith(prefix):
            continue
        meta = _parse_experiment_name(name, agent_id)
        if meta:
            found[name] = meta
    return list(found.values())


def _collect_checkpoint_experiments(agent_id: str) -> list[dict]:
    ckpt = _load_checkpoint()
    rows = []
    for key, row in ckpt.get("completed", {}).items():
        aid = row.get("agent_id") or key.split("::")[0]
        if aid != agent_id or row.get("status") == "error":
            continue
        if row.get("experiment_name"):
            rows.append(row)
    return rows


def _collect_all_experiments(agent_id: str, tenant: str, client: Client) -> list[dict]:
    by_name: dict[str, dict] = {}
    for row in _collect_checkpoint_experiments(agent_id):
        by_name[row["experiment_name"]] = row
    for row in _discover_langsmith_experiments(client, agent_id):
        by_name[row["experiment_name"]] = row
    for row in _discover_from_csv(agent_id, tenant, client):
        by_name[row["experiment_name"]] = row
    return list(by_name.values())


def _is_valid_run(filled: int, total: int, expected: int) -> bool:
    if total == 0 or filled < total:
        return False
    min_ok = max(1, int(expected * 0.9))
    return total >= min_ok


def _expected_runtime_models(agent_id: str) -> list[dict]:
    agents = json.loads(AGENT_MODELS_PATH.read_text(encoding="utf-8"))["agents"]
    return [
        m
        for m in agents.get(agent_id, [])
        if not m.get("skip_runtime") and m.get("configured", True)
    ]


def _skipped_gemini_models(agent_id: str) -> list[dict]:
    agents = json.loads(AGENT_MODELS_PATH.read_text(encoding="utf-8"))["agents"]
    return [m for m in agents.get(agent_id, []) if m.get("skip_runtime")]


def _finalize_audit_issues(
    agent_id: str,
    valid: list[dict],
    issues: list[str],
    *,
    tenant: str = "",
) -> list[str]:
    """Drop stale partial/error notes when a valid experiment exists for that combo."""
    best_keys = {(v["prompt_version"], v["model"]) for v in valid}
    final_issues: list[str] = []
    for note in issues:
        if note.startswith("MISSING —"):
            continue
        if note.startswith("GEMINI SKIPPED"):
            final_issues.append(note)
            continue
        if any(
            token in note
            for token in (
                "PARTIAL OUTPUT",
                "ERROR RUNS",
                "cannot read runs",
                "smoke/partial dataset",
                "0 root runs",
            )
        ):
            pv_model = note.split(":")[0]
            parts = pv_model.split("/")
            if len(parts) == 2 and (parts[0], parts[1]) in best_keys:
                continue
            final_issues.append(note)
            continue
        final_issues.append(note)

    missing_suffix = (
        f" on tenant {tenant}" if tenant else " found"
    )
    for m in _expected_runtime_models(agent_id):
        model = m["model"]
        for pv in PROMPT_VERSIONS:
            if (pv, model) not in best_keys:
                final_issues.append(
                    f"MISSING — {pv}/{model}: no valid full-run experiment{missing_suffix}"
                )

    seen: set[str] = set()
    deduped: list[str] = []
    for note in final_issues:
        if note not in seen:
            seen.add(note)
            deduped.append(note)
    return deduped


def _audit_agent(
    client: Client, meta: dict
) -> tuple[list[dict], list[str]]:
    """Return (valid_experiments, issue_notes)."""
    agent_id = meta["agent_id"]
    expected = _dataset_size(client, agent_id)
    issues: list[str] = []
    valid: list[dict] = []
    best: dict[tuple[str, str], tuple[dict, int]] = {}

    for exp in _collect_all_experiments(agent_id, meta["tenant"], client):
        name = exp["experiment_name"]
        session_id = str(exp.get("session_id") or exp.get("project_id") or "")
        try:
            filled, total, errors = _output_fill_rate(client, name, project_id=session_id)
        except Exception as exc:
            issues.append(
                f"{exp.get('prompt_version','?')}/{exp.get('model','?')}: cannot read runs ({exc})"
            )
            continue

        pv = exp.get("prompt_version", "?")
        model = exp.get("model", "?")

        if total == 0:
            issues.append(f"{pv}/{model}: experiment exists but 0 root runs")
            continue
        if errors > 0:
            issues.append(
                f"{pv}/{model}: ERROR RUNS {errors}/{total} "
                f"(e.g. parse_model_response — needs re-run)"
            )
            continue
        if filled < total:
            issues.append(
                f"{pv}/{model}: PARTIAL OUTPUT {filled}/{total} (empty rows — needs re-run)"
            )
            continue
        if total < max(1, int(expected * 0.9)):
            issues.append(
                f"{pv}/{model}: smoke/partial dataset {total}/{expected} examples — excluded from sheet"
            )
            continue

        url = exp.get("compare_url") or _compare_url(client, meta["tenant"], agent_id, name)
        if not url:
            issues.append(f"{pv}/{model}: missing compare URL — excluded")
            continue

        key = (pv, model)
        if key not in best or total > best[key][1]:
            entry = dict(exp)
            entry["compare_url"] = url
            if session_id:
                entry["session_id"] = session_id
            best[key] = (entry, total)
        print(f"  [OK] {pv}/{model}: {filled}/{total}")

    valid = [v[0] for v in best.values()]

    for m in _skipped_gemini_models(agent_id):
        model = m["model"]
        missing = [
            pv
            for pv in PROMPT_VERSIONS
            if (pv, model) not in best
        ]
        if missing:
            issues.append(
                f"GEMINI SKIPPED — {model}: configured skip_runtime=true "
                f"(health-check 503/UNAVAILABLE). Missing prompts: {', '.join(missing)}. "
                f"Re-run when Gemini API is stable: "
                f"python -m evals.agent_eval.run_matrix --step --agent {agent_id}"
            )

    return valid, _finalize_audit_issues(
        agent_id, valid, issues, tenant=meta["tenant"]
    )


def _purge_checkpoint_agent(agent_id: str) -> None:
    ckpt = _load_checkpoint()
    ckpt["completed"] = {
        k: v
        for k, v in ckpt.get("completed", {}).items()
        if (v.get("agent_id") or k.split("::")[0]) != agent_id
    }
    _save_checkpoint(ckpt)


def _purge_checkpoint_combo(agent_id: str, pv: str, provider: str, model: str) -> None:
    ckpt = _load_checkpoint()
    key = _experiment_key(agent_id, pv, provider, model)
    completed = ckpt.get("completed", {})
    if key in completed:
        del completed[key]
        ckpt["completed"] = completed
        _save_checkpoint(ckpt)


def _purge_partial_checkpoint(agent_id: str, tenant: str, client: Client, expected: int) -> None:
    for exp in _collect_all_experiments(agent_id, tenant, client):
        try:
            filled, total, errors = _output_fill_rate(client, exp["experiment_name"])
        except Exception:
            continue
        if errors > 0 or not _is_valid_run(filled, total, expected):
            _purge_checkpoint_combo(
                agent_id,
                exp.get("prompt_version", ""),
                exp.get("provider", ""),
                exp.get("model", ""),
            )


def _sync_valid_checkpoint(agent_id: str, valid: list[dict]) -> None:
    ckpt = _load_checkpoint()
    completed = ckpt.setdefault("completed", {})
    for exp in valid:
        key = _experiment_key(
            agent_id,
            exp["prompt_version"],
            exp["provider"],
            exp["model"],
        )
        completed[key] = {
            "agent_id": agent_id,
            "experiment_prefix": f"ae-{agent_id}-{exp['prompt_version']}-{exp['provider']}-{exp['model']}".replace(
                "/", "-"
            )[:80],
            "prompt_version": exp["prompt_version"],
            "provider": exp["provider"],
            "model": exp["model"],
            "experiment_name": exp["experiment_name"],
        }
    ckpt["completed"] = completed
    _save_checkpoint(ckpt)


def _run_agent_eval_full(agent_id: str) -> int:
    while True:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "evals.agent_eval.run_matrix",
                "--step",
                "--agent",
                agent_id,
            ],
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            return proc.returncode
        status = subprocess.run(
            [
                sys.executable,
                "-m",
                "evals.agent_eval.run_matrix",
                "--status",
                "--agent",
                agent_id,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if "[ ]" not in status.stdout:
            break
    return 0


def _build_csv_row(meta: dict, valid: list[dict], issues: list[str], client: Client) -> list[str]:
    exp_models = [m["model"] for m in _expected_runtime_models(meta["agent_id"])]
    completed_models = sorted({r["model"] for r in valid})
    completed_prompts = sorted({r["prompt_version"] for r in valid})
    exp_prompts = list(PROMPT_VERSIONS)
    pending_models = [
        m["model"]
        for m in _skipped_gemini_models(meta["agent_id"])
    ] + [m for m in exp_models if m not in completed_models]
    pending_prompts = [p for p in exp_prompts if p not in completed_prompts]

    pending_model_str = (
        "; ".join(dict.fromkeys(pending_models))
        if pending_models
        else "none (all planned models done)"
    )
    pending_prompt_str = (
        ", ".join(pending_prompts) if pending_prompts else "none (all prompts done)"
    )

    links = []
    for r in sorted(valid, key=lambda x: (x["prompt_version"], x["model"])):
        url = r.get("compare_url")
        if not url:
            url = _compare_url(client, meta["tenant"], meta["agent_id"], r["experiment_name"])
        if url:
            links.append(url)

    # Do not merge stale CSV links — they often point at pre-fix error sessions.

    runtime_combo_count = len(exp_models) * len(exp_prompts)
    runtime_ok = (
        len(completed_models) == len(exp_models)
        and len(completed_prompts) == len(exp_prompts)
        and len(valid) >= runtime_combo_count
        and not any(n.startswith("MISSING —") for n in issues)
    )
    if runtime_ok:
        runtime_note = (
            f"{len(valid)}/{runtime_combo_count} runtime combos verified — "
            f"100% output fill on LangSmith (all examples scored)."
        )
        gemini_notes = [n for n in issues if n.startswith("GEMINI SKIPPED")]
        notes = runtime_note + (
            f" | {' | '.join(gemini_notes)}" if gemini_notes else ""
        )
    else:
        notes = " | ".join(issues) if issues else "All runtime models: 100% output fill on dedicated workspace."

    return [
        str(meta["sno"]),
        meta["name"],
        meta["agent_id"],
        f"{len(completed_models)}/{len(exp_models)} completed — {', '.join(completed_models) if completed_models else 'none'}",
        pending_model_str,
        f"{len(completed_prompts)}/{len(exp_prompts)} completed — {', '.join(completed_prompts) if completed_prompts else 'none'}",
        pending_prompt_str,
        meta["tenant"],
        meta["gmail"],
        meta["password"],
        "\n\n".join(links),
        meta.get("dataset_id", ""),
        meta.get("primary_tenant", meta["tenant"]),
        notes,
    ]


def update_csv_for_agents(agent_rows: list[tuple[dict, list[dict], list[str]]]) -> None:
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    for col in ("LangSmith Dataset ID", "Primary Workspace Tenant", NOTES_COL):
        if col not in header:
            header.append(col)

    target_ids = {meta["agent_id"] for meta, _, _ in agent_rows}
    out_rows = [header]
    for row in rows[1:]:
        if len(row) < 3 or row[2] in target_ids:
            continue
        while len(row) < len(header):
            row.append("")
        out_rows.append(row[: len(header)])

    for meta, valid, issues in agent_rows:
        _switch_workspace(meta["workspace"])
        client = _make_client()
        new_row = _build_csv_row(meta, valid, issues, client)
        while len(new_row) < len(header):
            new_row.append("")
        out_rows.append(new_row[: len(header)])

    out_rows[1:] = sorted(out_rows[1:], key=lambda r: int(r[0]) if r and r[0].isdigit() else 999)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out_rows)
    print(f"Updated {CSV_PATH} for agents: {', '.join(target_ids)}")


def _audit_agent_multi(meta: dict, workspaces: list[str]) -> tuple[list[dict], list[str]]:
    """Audit across multiple workspaces (merge valid experiments)."""
    all_valid: dict[tuple[str, str], dict] = {}
    issue_pool: list[str] = []
    for ws in workspaces:
        _switch_workspace(ws)
        client = _make_client()
        valid, issues = _audit_agent(client, meta)
        for v in valid:
            all_valid[(v["prompt_version"], v["model"])] = v
        issue_pool.extend(issues)
    merged = list(all_valid.values())
    return merged, _finalize_audit_issues(meta["agent_id"], merged, issue_pool)


def _remediate_agent_eval(meta: dict, client: Client, *, full: bool) -> tuple[list[dict], list[str]]:
    agent_id = meta["agent_id"]
    expected = _dataset_size(client, agent_id)

    if full:
        print(f"  Full re-run: clearing checkpoint for {agent_id}")
        _purge_checkpoint_agent(agent_id)
    else:
        _purge_partial_checkpoint(agent_id, meta["tenant"], client, expected)
        pre_valid, _ = _audit_agent(client, meta)
        _sync_valid_checkpoint(agent_id, pre_valid)

    status = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.agent_eval.run_matrix",
            "--status",
            "--agent",
            agent_id,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if "[ ]" in status.stdout:
        print(f"  Running pending combos for {agent_id}...")
        rc = _run_agent_eval_full(agent_id)
        if rc != 0:
            return [], [f"RUN FAILED: agent_eval exited {rc}"]

    valid, issues = _audit_agent(client, meta)
    if agent_id == "query_rewriter":
        valid, issues = _audit_agent_multi(meta, ["scombinator26", "gra7399"])
    elif meta.get("sno", 0) in range(14, 22):
        ws = meta["workspace"]
        valid, issues = _audit_agent_multi(meta, [ws])
    _sync_valid_checkpoint(agent_id, valid)
    return valid, issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="append", help="Agent id(s); default all 1-13")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--csv-only", action="store_true")
    parser.add_argument("--from-sno", type=int, default=1, help="Start from agent S.No (default 1)")
    args = parser.parse_args()

    targets = [
        a
        for a in ALL_AGENTS
        if a["sno"] >= args.from_sno and (not args.agent or a["agent_id"] in args.agent)
    ]
    if not targets:
        print("No agents matched")
        return 1

    agent_rows: list[tuple[dict, list[dict], list[str]]] = []

    for meta in targets:
        aid = meta["agent_id"]
        meta = {**meta, "primary_tenant": meta["tenant"]}
        need_run = not args.verify_only and not args.csv_only
        meta, fallback_note = _resolve_workspace(meta, need_run=need_run)
        print(f"\n=== Agent {meta['sno']}: {aid} on {meta['workspace']} ===")
        _switch_workspace(meta["workspace"])
        client = _make_client()

        if fallback_note:
            print(f"  {fallback_note}")

        if meta["harness"] == "intent_classifier":
            if args.csv_only or not args.verify_only:
                if need_run and _is_workspace_capped("scombinator26"):
                    ds_id = _ensure_dataset_uploaded("intent_classifier")
                    if ds_id:
                        meta["dataset_id"] = ds_id
                subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "update_intent_classifier_testing_results.py")],
                    cwd=str(ROOT),
                )
            continue

        if need_run:
            ds_id = _ensure_dataset_uploaded(aid)
            if ds_id:
                meta["dataset_id"] = ds_id

        if args.verify_only or args.csv_only:
            if aid in ("query_decomposer", "scope_narrower", "query_rewriter"):
                valid, issues = _audit_agent_multi(
                    meta,
                    ["emaildam3", "scombinator26", "gra7399"]
                    if aid == "query_decomposer"
                    else ["scombinator26", "gra7399"]
                    if aid == "query_rewriter"
                    else ["emaildam3", "scombinator26"],
                )
            elif aid == "studio_fallback_legacy":
                valid, issues = _audit_agent_multi(meta, ["eskomal66", "emaildam3"])
            elif aid == "studio_flashcards":
                valid, issues = _audit_agent_multi(meta, ["sui332307", "gra7399"])
            else:
                valid, issues = _audit_agent(client, meta)
            if fallback_note:
                issues = [fallback_note] + issues
            if args.verify_only:
                for note in issues:
                    print(f"  {note}")
            if valid and meta["harness"] == "agent_eval":
                _sync_valid_checkpoint(aid, valid)
            agent_rows.append((meta, valid, issues))
            continue

        if fallback_note and "verify-only" in (fallback_note or "").lower():
            if aid == "query_rewriter":
                valid, issues = _audit_agent_multi(meta, ["scombinator26", "gra7399"])
            else:
                valid, issues = _audit_agent(client, meta)
            issues = [fallback_note] + issues
            agent_rows.append((meta, valid, issues))
            continue

        full = meta["rerun"] == "full"
        valid, issues = _remediate_agent_eval(meta, client, full=full)
        if fallback_note:
            issues = [fallback_note] + issues
        for note in issues:
            print(f"  {note}")
        agent_rows.append((meta, valid, issues))

    if agent_rows:
        update_csv_for_agents(agent_rows)

    if not args.verify_only and not args.csv_only:
        _switch_workspace("scombinator26")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "update_intent_classifier_testing_results.py")],
            cwd=str(ROOT),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
