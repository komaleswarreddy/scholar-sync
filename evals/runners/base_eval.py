"""
Base Evaluation Runner

Shared utilities for evaluation runners.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]


class BaseEvalRunner(ABC):
    """Base class for evaluation runners."""

    name: str = "base_eval"
    reports_dir: Path = ROOT / "evals" / "reports"

    @abstractmethod
    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Run evaluation and return report dict."""

    def write_report(self, filename: str, report: Dict[str, Any]) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.reports_dir / filename
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return path

    def load_baseline(self, filename: str) -> Optional[Dict[str, Any]]:
        path = self.reports_dir / filename
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def check_regression(
        self,
        current_score: float,
        baseline_score: float,
        max_drop_pct: float = 3.0,
    ) -> Dict[str, Any]:
        drop = baseline_score - current_score
        drop_pct = (drop / baseline_score * 100.0) if baseline_score else 0.0
        return {
            "baseline_score": baseline_score,
            "current_score": current_score,
            "drop": round(drop, 2),
            "drop_pct": round(drop_pct, 2),
            "regressed": drop_pct > max_drop_pct,
            "max_drop_pct": max_drop_pct,
        }
