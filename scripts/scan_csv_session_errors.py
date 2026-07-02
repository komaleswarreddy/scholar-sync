#!/usr/bin/env python3
"""Scan CSV compare-link sessions for LangSmith error runs (agents 1-13)."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client

CSV_PATH = ROOT / "Reference dataset" / "testing_Results.csv"
KEYS_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"
SESSION_RE = re.compile(
    r"https://smith\.langchain\.com/o/([a-f0-9-]+)/datasets/([a-f0-9-]+)/compare\?selectedSessions=([a-f0-9-]+)"
)


def _client_for_tenant(tenant: str) -> Client:
    keys = json.loads(KEYS_PATH.read_text(encoding="utf-8"))
    key = keys.get(tenant)
    if not key:
        raise RuntimeError(f"No API key for tenant {tenant}")
    return Client(api_key=key)


def _session_stats(client: Client, session_id: str) -> dict:
    ok = errors = empty = 0
    sample_err = ""
    name = ""
    try:
        proj = client.read_project(project_id=session_id)
        name = str(getattr(proj, "name", "") or "")
    except Exception as exc:
        return {"name": "", "ok": 0, "errors": 0, "empty": 0, "sample_err": str(exc)[:120]}

    offset = 0
    while True:
        batch = list(
            client.list_runs(project_id=session_id, is_root=True, limit=100, offset=offset)
        )
        if not batch:
            break
        for r in batch:
            if r.error:
                errors += 1
                if not sample_err:
                    sample_err = str(r.error)[:160]
            elif isinstance(r.outputs, dict) and r.outputs:
                ok += 1
            else:
                empty += 1
        if len(batch) < 100:
            break
        offset += len(batch)
    return {"name": name, "ok": ok, "errors": errors, "empty": empty, "sample_err": sample_err}


def main() -> None:
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    sno_idx = header.index("S.No")
    aid_idx = header.index("Agent ID")
    links_idx = header.index("LangSmith Compare Links")

    problems: list[str] = []
    for row in rows[1:]:
        if not row or not row[sno_idx].isdigit():
            continue
        sno = int(row[sno_idx])
        if sno > 13:
            continue
        agent_id = row[aid_idx].strip()
        links_cell = row[links_idx] if len(row) > links_idx else ""
        by_tenant: dict[str, Client] = {}
        for m in SESSION_RE.finditer(links_cell or ""):
            tenant, _ds, session_id = m.groups()
            if tenant not in by_tenant:
                by_tenant[tenant] = _client_for_tenant(tenant)
            stats = _session_stats(by_tenant[tenant], session_id)
            if stats["errors"] > 0:
                problems.append(
                    f"#{sno} {agent_id} | {stats['name']} | "
                    f"ok={stats['ok']} err={stats['errors']} | {stats['sample_err']}"
                )
            elif stats["ok"] == 0 and stats["empty"] > 0:
                problems.append(
                    f"#{sno} {agent_id} | {stats['name']} | EMPTY ok=0 empty={stats['empty']}"
                )

    print(f"Scanned agents 1-13 — {len(problems)} problematic CSV-linked session(s):\n")
    for p in problems:
        print(p)


if __name__ == "__main__":
    main()
