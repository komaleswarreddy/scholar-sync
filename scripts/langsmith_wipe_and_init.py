"""
LangSmith workspace cleanup + init.

Modes:
  inventory  -> read-only listing of projects, datasets, prompts (default)
  wipe       -> DELETE all prompts, datasets, and tracing projects, then create
                a fresh empty project named 'Scholarsync'.

Reads LANGSMITH_API_KEY / LANGSMITH_ENDPOINT from the project .env.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from langsmith import Client

NEW_PROJECT = "Scholarsync"


def load_env() -> tuple[str, str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    api_key = None
    endpoint = "https://api.smith.langchain.com"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("LANGSMITH_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
            elif line.startswith("LANGSMITH_ENDPOINT="):
                endpoint = line.split("=", 1)[1].strip()
    api_key = os.environ.get("LANGSMITH_API_KEY", api_key)
    endpoint = os.environ.get("LANGSMITH_ENDPOINT", endpoint)
    if not api_key:
        sys.exit("No LANGSMITH_API_KEY found in env or .env")
    return api_key, endpoint


def iter_prompts(client: Client):
    """Paginate prompts; the API caps limit at 100."""
    offset = 0
    page = 100
    while True:
        resp = client.list_prompts(limit=page, offset=offset)
        items = list(getattr(resp, "repos", resp))
        if not items:
            break
        for pr in items:
            yield pr
        if len(items) < page:
            break
        offset += page


def prompt_handle(pr) -> str:
    return (
        getattr(pr, "repo_handle", None)
        or getattr(pr, "full_name", None)
        or str(pr)
    )


def inventory(client: Client) -> None:
    print("=== PROJECTS (tracing sessions) ===")
    projects = list(client.list_projects())
    for p in projects:
        print(f"  - {p.name}  (id={p.id})")
    print(f"  total: {len(projects)}\n")

    print("=== DATASETS ===")
    datasets = list(client.list_datasets())
    for d in datasets:
        print(f"  - {d.name}  (id={d.id}, examples={getattr(d, 'example_count', '?')})")
    print(f"  total: {len(datasets)}\n")

    print("=== PROMPTS (repos) ===")
    count = 0
    for pr in iter_prompts(client):
        print(f"  - {prompt_handle(pr)}")
        count += 1
    print(f"  total: {count}\n")


def wipe(client: Client, new_project: str = NEW_PROJECT) -> None:
    # 1) Prompts
    print("Deleting prompts...")
    handles = [prompt_handle(pr) for pr in iter_prompts(client)]
    for handle in handles:
        try:
            client.delete_prompt(handle)
            print(f"  deleted prompt: {handle}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED prompt {handle}: {e}")

    # 2) Datasets
    print("Deleting datasets...")
    for d in list(client.list_datasets()):
        try:
            client.delete_dataset(dataset_id=d.id)
            print(f"  deleted dataset: {d.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED dataset {d.name}: {e}")

    # 3) Projects
    print("Deleting projects...")
    for p in list(client.list_projects()):
        try:
            client.delete_project(project_id=p.id)
            print(f"  deleted project: {p.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED project {p.name}: {e}")

    # 4) Create fresh project
    print(f"Creating fresh project '{new_project}'...")
    try:
        proj = client.create_project(project_name=new_project)
        print(f"  created project: {proj.name} (id={proj.id})")
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED creating project: {e}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    api_key, endpoint = load_env()
    client = Client(api_url=endpoint, api_key=api_key)

    sample = list(client.list_projects(limit=1))
    print(f"[ok] Connected to {endpoint} (sample fetch ok: {len(sample)} row)\n")

    if mode == "inventory":
        inventory(client)
    elif mode == "wipe":
        wipe(client)
        print("\n=== POST-WIPE INVENTORY ===")
        inventory(client)
    else:
        sys.exit(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
