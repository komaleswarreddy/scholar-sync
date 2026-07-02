#!/usr/bin/env python3
"""Structure testing_Results.csv: workspace accounts + dataset IDs per agent."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "Reference dataset" / "testing_Results.csv"
WORKSPACES_PATH = ROOT / "Reference dataset" / "langsmith_workspaces.csv"

# Cursemes9 uploads (no compare links yet for pending agents)
FALLBACK_DATASET_IDS: dict[str, str] = {
    "tutor_notebook_bootstrap": "15cab6a2-656e-4975-b6da-af013625ce43",
    "tutor_follow_up_questions": "c1688ab5-a0a0-47d2-89fa-886951337885",
    "source_question_extraction": "c93f6c51-a200-489c-aa67-8935d6638e8d",
    "image_ocr": "2486b89f-d5da-43e7-83ad-7efc3d49259a",
    "diagram_label_ocr": "491929ad-a052-471e-848c-d1e52757ddb3",
}

# Canonical LangSmith workspace -> Gmail (from compare-link tenant IDs)
TENANT_GMAIL: dict[str, str] = {
    "15d476d5-df92-4760-96b8-52f9130946bf": "pscmrmindssprint2k25@gmail.com",
    "47ca8a69-43eb-4f05-812b-c7778fe6987d": "scombinator26@gmail.com",
    "aafff4b5-45a3-4448-9f7d-805bfc70098d": "emaildam3@gmail.com",
    "67272628-c819-44db-bbda-e500db0d6982": "gra7399@gmail.com",
    "33d88f33-0349-4117-89c6-5d0d56252773": "sui332307@gmail.com",
    "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b": "eskomal66@gmail.com",
    "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7": "cursemes9@gmail.com",
}

TENANT_PASSWORD: dict[str, str] = {
    "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7": "ASDFvbnm1234@",
}
DEFAULT_PASSWORD = "asdfvbnm1234"

LINK_RE = re.compile(
    r"https://smith\.langchain\.com/o/([a-f0-9-]+)/datasets/([a-f0-9-]+)/compare"
)


def _clean_email(s: str) -> str:
    return " ".join(s.replace("\n", " ").replace("\r", " ").split()).strip()


def _parse_links(cell: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in LINK_RE.finditer(cell or ""):
        out.append((m.group(1), m.group(2)))
    return out


def _primary_tenant(links: list[tuple[str, str]], declared: str) -> str:
    if not links:
        tenants = [t.strip() for t in declared.split("|") if t.strip()]
        return tenants[0] if tenants else ""
    counts = Counter(t for t, _ in links)
    return counts.most_common(1)[0][0]


def _primary_dataset(links: list[tuple[str, str]], agent_id: str) -> str:
    if links:
        ds_counts = Counter(ds for _, ds in links)
        return ds_counts.most_common(1)[0][0]
    return FALLBACK_DATASET_IDS.get(agent_id, "")


def main() -> int:
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        print("Empty CSV")
        return 1

    header = rows[0]
    # Normalize header additions
    extra_cols = ["LangSmith Dataset ID", "Primary Workspace Tenant"]
    for col in extra_cols:
        if col not in header:
            header.append(col)

    idx = {name: header.index(name) for name in header}
    out_rows: list[list[str]] = [header]
    workspace_agents: dict[str, list[str]] = defaultdict(list)

    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        # Pad short rows
        while len(row) < len(header) - len(extra_cols):
            row.append("")

        agent_id = row[idx["Agent ID"]].strip()
        links_cell = row[idx["LangSmith Compare Links"]] if "LangSmith Compare Links" in idx else ""
        links = _parse_links(links_cell)

        row[idx["Gmail Account(s)"]] = _clean_email(row[idx["Gmail Account(s)"]])
        declared_tenant = row[idx["Workspace Tenant(s)"]].strip()
        primary_tenant = _primary_tenant(links, declared_tenant)
        dataset_id = _primary_dataset(links, agent_id)

        # Align gmail/password with primary tenant when canonical mapping exists
        if primary_tenant in TENANT_GMAIL:
            row[idx["Gmail Account(s)"]] = TENANT_GMAIL[primary_tenant]
            row[idx["Gmail Password"]] = TENANT_PASSWORD.get(primary_tenant, DEFAULT_PASSWORD)
        if primary_tenant:
            row[idx["Workspace Tenant(s)"]] = primary_tenant

        # Ensure row has all columns
        while len(row) < len(header):
            row.append("")
        row[idx["LangSmith Dataset ID"]] = dataset_id
        row[idx["Primary Workspace Tenant"]] = primary_tenant

        if primary_tenant:
            workspace_agents[primary_tenant].append(agent_id)

        out_rows.append(row)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out_rows)

    # Build workspace reference (one row per tenant from agent rows)
    tenant_info: dict[str, dict[str, str]] = {}
    for tenant, gmail in TENANT_GMAIL.items():
        tenant_info[tenant] = {
            "gmail": gmail,
            "password": TENANT_PASSWORD.get(tenant, DEFAULT_PASSWORD),
        }

    ws_header = [
        "Workspace #",
        "Tenant ID",
        "Gmail Account",
        "Gmail Password",
        "LangSmith Project",
        "Agents Count",
        "Agent IDs",
    ]
    ws_rows = [ws_header]
    for i, (tenant, info) in enumerate(sorted(tenant_info.items()), 1):
        agents = workspace_agents.get(tenant, [])
        ws_rows.append(
            [
                str(i),
                tenant,
                info["gmail"],
                info["password"],
                "ScholarSync-v2",
                str(len(agents)),
                "; ".join(sorted(set(agents))),
            ]
        )

    with open(WORKSPACES_PATH, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(ws_rows)

    print(f"Updated {CSV_PATH} ({len(out_rows) - 1} agents)")
    print(f"Wrote {WORKSPACES_PATH} ({len(ws_rows) - 1} workspaces)")
    missing_ds = [r[idx["Agent ID"]] for r in out_rows[1:] if not r[idx["LangSmith Dataset ID"]]]
    if missing_ds:
        print(f"Missing dataset ID: {missing_ds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
