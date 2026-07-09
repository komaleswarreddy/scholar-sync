"""
IIL feedback-loop end-to-end debugger.

1. Backfill InteractionLogs for assistant messages that have feedback
2. Score expert feedback into curation_candidates
3. Approve one pending candidate and verify derived_knowledge_artifacts row

Usage:
  python scripts/debug_iil_flywheel.py
  python scripts/debug_iil_flywheel.py --approve-one
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from config.settings import settings
from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.iil import (
    CurationCandidate,
    DerivedKnowledgeArtifact,
    InteractionFeedback,
    InteractionLog,
)
from packages.core.iil.curation_scorer import run_scoring_batch, score_feedback_event
from packages.core.iil.curation_service import review_candidate
from packages.core.iil.enums import CurationStatus, SignalType
from packages.core.iil.interaction_log_service import backfill_logs_for_assistant_messages


def _ok(label: str, detail: str = "") -> None:
    print(f"  [OK] {label}" + (f" — {detail}" if detail else ""))


def _fail(label: str, detail: str = "") -> None:
    print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


def _info(label: str) -> None:
    print(f"  [..] {label}")


async def snapshot() -> dict:
    async with AsyncSessionLocal() as db:
        return {
            "logs": int(await db.scalar(select(func.count(InteractionLog.id))) or 0),
            "feedback": int(await db.scalar(select(func.count(InteractionFeedback.id))) or 0),
            "expert_feedback": int(
                await db.scalar(
                    select(func.count(InteractionFeedback.id)).where(
                        InteractionFeedback.signal_type.in_(
                            [
                                SignalType.EXPERT_VALIDATED.value,
                                SignalType.EXPERT_NOTE.value,
                                SignalType.MISSING_DIMENSION.value,
                            ]
                        )
                    )
                )
                or 0
            ),
            "candidates": int(await db.scalar(select(func.count(CurationCandidate.id))) or 0),
            "pending": int(
                await db.scalar(
                    select(func.count(CurationCandidate.id)).where(
                        CurationCandidate.status == CurationStatus.PENDING.value
                    )
                )
                or 0
            ),
            "approved": int(
                await db.scalar(
                    select(func.count(CurationCandidate.id)).where(
                        CurationCandidate.status == CurationStatus.APPROVED.value
                    )
                )
                or 0
            ),
            "artifacts": int(
                await db.scalar(select(func.count(DerivedKnowledgeArtifact.id))) or 0
            ),
            "active_artifacts": int(
                await db.scalar(
                    select(func.count(DerivedKnowledgeArtifact.id)).where(
                        DerivedKnowledgeArtifact.is_active.is_(True)
                    )
                )
                or 0
            ),
        }


async def score_orphan_expert_feedback() -> int:
    created = 0
    async with AsyncSessionLocal() as db:
        subq = select(CurationCandidate.feedback_id).where(
            CurationCandidate.feedback_id.isnot(None)
        )
        result = await db.execute(
            select(InteractionFeedback)
            .where(
                InteractionFeedback.signal_type.in_(
                    [
                        SignalType.EXPERT_VALIDATED.value,
                        SignalType.EXPERT_NOTE.value,
                        SignalType.MISSING_DIMENSION.value,
                    ]
                )
            )
            .where(InteractionFeedback.id.notin_(subq))
            .order_by(InteractionFeedback.created_at.desc())
            .limit(50)
        )
        for fb in result.scalars().all():
            if await score_feedback_event(db, fb.id):
                created += 1
    return created


async def link_candidates_to_logs() -> int:
    """Attach interaction_log_id on candidates that only have feedback.message_id."""
    updated = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CurationCandidate, InteractionFeedback)
            .join(InteractionFeedback, InteractionFeedback.id == CurationCandidate.feedback_id)
            .where(CurationCandidate.interaction_log_id.is_(None))
            .where(InteractionFeedback.message_id.isnot(None))
        )
        for cand, fb in result.all():
            log_result = await db.execute(
                select(InteractionLog).where(InteractionLog.message_id == fb.message_id)
            )
            log = log_result.scalar_one_or_none()
            if not log:
                continue
            cand.interaction_log_id = log.id
            if not cand.concept_node_id and log.concept_node_id:
                cand.concept_node_id = log.concept_node_id
            updated += 1
        if updated:
            await db.commit()
    return updated


async def approve_one_pending() -> tuple[bool, str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CurationCandidate)
            .where(CurationCandidate.status == CurationStatus.PENDING.value)
            .order_by(CurationCandidate.created_at.desc())
            .limit(1)
        )
        cand = result.scalar_one_or_none()
        if not cand:
            return False, "no pending candidates"

        before_artifacts = int(
            await db.scalar(select(func.count(DerivedKnowledgeArtifact.id))) or 0
        )
        reviewed = await review_candidate(
            db,
            candidate_id=cand.id,
            reviewer_id="debug-script",
            decision="approved",
            review_notes="E2E debug approve",
            confidence_score=4,
        )
        art_result = await db.execute(
            select(DerivedKnowledgeArtifact).where(
                DerivedKnowledgeArtifact.candidate_id == reviewed.id
            )
        )
        artifact = art_result.scalar_one_or_none()
        after_artifacts = int(
            await db.scalar(select(func.count(DerivedKnowledgeArtifact.id))) or 0
        )

        if reviewed.status != CurationStatus.APPROVED.value:
            return False, f"status={reviewed.status}"
        if not artifact:
            return False, "no derived_knowledge_artifacts row"
        if not (artifact.content or "").strip():
            return False, "artifact content empty"
        if after_artifacts <= before_artifacts:
            return False, "artifact count did not increase"

        detail = (
            f"candidate={reviewed.id} artifact={artifact.id} "
            f"content_len={len(artifact.content)} "
            f"embedding_id={artifact.embedding_id or 'none'} "
            f"tags={artifact.dimension_tags}"
        )
        return True, detail


async def verify_log_create_smoke() -> tuple[bool, str]:
    """Create a log for the newest assistant message that has feedback, if any missing."""
    async with AsyncSessionLocal() as db:
        n = await backfill_logs_for_assistant_messages(db, limit=20)
        return True, f"backfilled {n} interaction_log(s)"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--approve-one",
        action="store_true",
        help="Approve one pending candidate and verify artifact row",
    )
    parser.add_argument("--no-approve", action="store_true", help="Skip approve step")
    args = parser.parse_args()
    do_approve = args.approve_one or not args.no_approve

    print("=" * 60)
    print("IIL flywheel E2E debugger")
    print(f"IIL_ENABLED={settings.IIL_ENABLED}")
    print(f"IIL_LOGGING_ASYNC_TIMEOUT_MS={settings.IIL_LOGGING_ASYNC_TIMEOUT_MS}")
    print("=" * 60)

    print("\n=== Snapshot (before) ===")
    before = await snapshot()
    for k, v in before.items():
        print(f"  {k}: {v}")

    failures = 0

    print("\n=== 1. Backfill interaction_logs from feedback messages ===")
    ok, detail = await verify_log_create_smoke()
    (_ok if ok else _fail)("backfill_logs_for_assistant_messages", detail)
    if not ok:
        failures += 1

    print("\n=== 2. Batch score logs ===")
    async with AsyncSessionLocal() as db:
        n_logs = await run_scoring_batch(db, limit=100)
    _ok("run_scoring_batch", f"{n_logs} candidate(s)")

    print("\n=== 3. Score orphan expert feedback ===")
    n_fb = await score_orphan_expert_feedback()
    _ok("score_feedback_event", f"{n_fb} candidate(s)")

    print("\n=== 4. Link candidates to logs ===")
    linked = await link_candidates_to_logs()
    _ok("link_candidates_to_logs", f"{linked} updated")

    print("\n=== Snapshot (after scoring) ===")
    mid = await snapshot()
    for k, v in mid.items():
        delta = v - before[k]
        print(f"  {k}: {v}" + (f" (+{delta})" if delta else ""))

    if mid["logs"] == 0 and mid["feedback"] > 0:
        _fail("interaction_logs still empty despite feedback")
        failures += 1
    elif mid["logs"] > 0:
        _ok("interaction_logs populated", str(mid["logs"]))

    if mid["expert_feedback"] > 0 and mid["candidates"] == 0:
        _fail("expert feedback but zero candidates")
        failures += 1
    elif mid["candidates"] > 0:
        _ok("curation_candidates present", f"pending={mid['pending']} total={mid['candidates']}")

    if do_approve and mid["pending"] > 0:
        print("\n=== 5. Approve one pending candidate -> derived artifact ===")
        ok, detail = await approve_one_pending()
        (_ok if ok else _fail)("review_candidate approve", detail)
        if not ok:
            failures += 1

        print("\n=== Snapshot (after approve) ===")
        after = await snapshot()
        for k, v in after.items():
            delta = v - mid[k]
            print(f"  {k}: {v}" + (f" (+{delta})" if delta else ""))

        if after["artifacts"] <= mid["artifacts"]:
            _fail("derived_knowledge_artifacts not created")
            failures += 1
        else:
            _ok("derived_knowledge_artifacts created", str(after["artifacts"]))
    elif do_approve:
        _info("no pending candidates to approve")

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED ({failures})")
        return 1
    print("All IIL flywheel checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
