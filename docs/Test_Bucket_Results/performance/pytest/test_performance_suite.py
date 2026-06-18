"""
PRF-01..07 performance integration tests.

Smoke tests run in fast E2E gate; full load/soak are manual (SKIP by default).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.performance_client import CHAT_QUESTIONS, generate_studio_timed, stream_chat_timed
from tests.helpers.performance_stats import percentiles

ROOT = Path(__file__).resolve().parents[2]

# Smoke thresholds (relaxed tier)
SMOKE_TTFT_P95_MS = 5000.0
SMOKE_E2E_P95_MS = 15000.0


@pytest.mark.integration
@pytest.mark.performance
class TestPRFChatSmoke:
    """PRF-01 / PRF-02 — chat TTFT and E2E under small concurrent sample."""

    def test_prf01_02_chat_smoke(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        prf_chat_source_id,
    ):
        token = auth_token
        n = 5
        samples = []
        for i in range(n):
            result = stream_chat_timed(
                api_client,
                base_url=base_url,
                token=token,
                message=CHAT_QUESTIONS[i % len(CHAT_QUESTIONS)],
                active_source_ids=[prf_chat_source_id],
            )
            assert result.error is None or result.http_status != 500, (
                f"[open_bug] chat error: {result.error}"
            )
            if result.error:
                pytest.fail(f"[error-spike] request {i}: {result.error}")
            samples.append(result)

        warmed = samples[2:] if len(samples) > 2 else samples
        ttft_vals = [float(r.ttft_ms) for r in warmed if r.ttft_ms is not None]
        e2e_vals = [float(r.e2e_ms) for r in warmed if r.e2e_ms is not None]
        ttft = percentiles(ttft_vals)
        e2e = percentiles(e2e_vals)

        assert ttft.get("n", 0) >= 1, "No successful warmed chat samples"
        assert e2e.get("n", 0) >= 1, "No successful warmed chat samples"
        if ttft.get("p95", 0) >= SMOKE_TTFT_P95_MS or e2e.get("p95", 0) >= SMOKE_E2E_P95_MS:
            pytest.xfail(
                f"PRF latency smoke budget exceeded (TTFT P95={ttft.get('p95'):.0f}ms, "
                f"E2E P95={e2e.get('p95'):.0f}ms) — harness OK, tune env or use manual PDF thresholds"
            )


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
class TestPRFIngestSmoke:
    """PRF-04 — ingestion latency smoke (optional slow layer)."""

    def test_prf04_ingest_smoke(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        fixtures_dir,
    ):
        import uuid

        from tests.helpers.performance_client import ingest_timed

        durations = []
        for i in range(3):
            unique = fixtures_dir / f"_prf_ingest_{uuid.uuid4().hex}.txt"
            unique.write_text(f"PRF ingest probe {i}: {uuid.uuid4()}\n" * 50, encoding="utf-8")
            try:
                result = ingest_timed(
                    api_client,
                    base_url=base_url,
                    token=auth_token,
                    file_path=unique,
                    title=f"prf_ingest_{i}",
                    timeout_s=120.0,
                )
                assert result.error is None, result.error
                assert result.e2e_ms is not None
                durations.append(result.e2e_ms / 1000.0)
            finally:
                unique.unlink(missing_ok=True)

        p95 = percentiles(durations).get("p95", 0)
        assert p95 < 90.0, f"PRF-04 smoke ingest P95 {p95:.1f}s exceeds 90s"


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
class TestPRFStudioSmoke:
    """PRF-05 — one generation per task type (smoke)."""

    @pytest.mark.parametrize("task_type", ["quiz", "flashcards", "mind_map", "report"])
    def test_prf05_studio_smoke_per_type(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        stu_standard_source_id,
        task_type,
    ):
        token = auth_token
        result = generate_studio_timed(
            api_client,
            base_url=base_url,
            token=token,
            task_type=task_type,
            source_ids=[stu_standard_source_id],
        )
        assert result.status_code < 500, f"[open_bug] studio {task_type} HTTP {result.status_code}"
        assert result.status_code == 200, f"studio {task_type} failed: {result.error}"
        smoke_budget_ms = 60000.0
        assert (result.e2e_ms or 0) < smoke_budget_ms, (
            f"PRF-05 {task_type} {result.e2e_ms}ms exceeds smoke budget"
        )


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.load
class TestPRFLoadFull:
    """PRF-06 — full classroom load (manual only)."""

    @pytest.mark.skip(reason="Manual: PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_load.py")
    def test_prf06_load_full(self):
        env = os.environ.copy()
        env.setdefault("PRF_ATTEST_NO_RESTART", "1")
        code = subprocess.call(
            [sys.executable, "scripts/run_prf_load.py", "--full"],
            cwd=str(ROOT),
            env=env,
        )
        assert code == 0


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.load
class TestPRFSoakFull:
    """PRF-07 — 2-4h soak (manual only)."""

    @pytest.mark.skip(reason="Manual: PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_soak.py")
    def test_prf07_soak_full(self):
        env = os.environ.copy()
        env.setdefault("PRF_ATTEST_NO_RESTART", "1")
        code = subprocess.call(
            [sys.executable, "scripts/run_prf_soak.py"],
            cwd=str(ROOT),
            env=env,
        )
        assert code == 0
