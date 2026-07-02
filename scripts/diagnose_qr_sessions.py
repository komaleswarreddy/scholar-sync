"""Diagnose LangSmith sessions for query_rewriter CSV links."""
from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client

CSV_PATH = ROOT / "Reference dataset" / "testing_Results.csv"
SESSION_RE = re.compile(
    r"smith\.langchain\.com/o/([^/]+)/datasets/([^/]+)/compare\?selectedSessions=([a-f0-9-]+)"
)


SCOMBINATOR_KEY = "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"


def main() -> None:
    key = os.environ.get("LANGSMITH_API_KEY", "") or SCOMBINATOR_KEY
    client = Client(api_key=key)
    links_cell = ""
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) > 2 and row[2] == "query_rewriter":
                links_cell = row[10] if len(row) > 10 else ""
                break

    for m in SESSION_RE.finditer(links_cell):
        tenant, ds_id, session_id = m.groups()
        proj = client.read_project(project_id=session_id)
        name = getattr(proj, "name", "")
        errors = ok = empty = 0
        offset = 0
        sample_err = ""
        while True:
            batch = list(
                client.list_runs(
                    project_id=session_id, is_root=True, limit=100, offset=offset
                )
            )
            if not batch:
                break
            for r in batch:
                if r.error:
                    errors += 1
                    if not sample_err:
                        sample_err = str(r.error)[:200]
                elif isinstance(r.outputs, dict) and r.outputs:
                    ok += 1
                else:
                    empty += 1
            if len(batch) < 100:
                break
            offset += len(batch)
        print(f"\n{name}")
        print(f"  session={session_id}")
        print(f"  ok={ok} errors={errors} empty={empty}")
        if sample_err:
            print(f"  sample_error={sample_err}")


if __name__ == "__main__":
    main()
