"""Load tiered and JSONL evaluation datasets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

ROOT = Path(__file__).resolve().parents[4]
TIERED_DIR = ROOT / "evals" / "datasets" / "prompt_tiered"
MANIFEST_PATH = TIERED_DIR / "manifest.json"


@dataclass
class DatasetRecord:
    id: str
    input: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    variation: str = ""
    tags: List[str] = field(default_factory=list)


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        return {"datasets": []}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def dataset_version_hash(agent_id: str) -> str:
    """SHA256 prefix of dataset file for reproducibility."""
    manifest = load_manifest()
    for ds in manifest.get("datasets") or []:
        if ds.get("dataset_id") == agent_id:
            path = ROOT / ds["path"]
            if path.is_file():
                return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return "unknown"


def _normalize_item(raw: Dict[str, Any]) -> DatasetRecord:
    return DatasetRecord(
        id=str(raw.get("id", "")),
        input=dict(raw.get("inputs") or raw.get("input") or {}),
        expected_output=dict(raw.get("reference_outputs") or raw.get("expected_output") or {}),
        metadata=dict(raw.get("metadata") or {}),
        variation=str(raw.get("variation") or ""),
        tags=list(raw.get("tags") or []),
    )


def load_agent_dataset(agent_id: str, *, limit: Optional[int] = None) -> List[DatasetRecord]:
    """Load normalized records for an agent from prompt_tiered JSON."""
    manifest = load_manifest()
    path: Optional[Path] = None
    for ds in manifest.get("datasets") or []:
        if ds.get("dataset_id") == agent_id:
            path = ROOT / ds["path"]
            break
    if path is None or not path.is_file():
        raise FileNotFoundError(f"No tiered dataset for agent_id={agent_id}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    items = [_normalize_item(it) for it in doc.get("items") or []]
    if limit is not None:
        return items[:limit]
    return items


def load_jsonl_dataset(path: Path, *, limit: Optional[int] = None) -> List[DatasetRecord]:
    records: List[DatasetRecord] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            records.append(_normalize_item(raw))
            if limit and len(records) >= limit:
                break
    return records


def iter_all_agents() -> Iterator[str]:
    for ds in load_manifest().get("datasets") or []:
        yield str(ds["dataset_id"])
