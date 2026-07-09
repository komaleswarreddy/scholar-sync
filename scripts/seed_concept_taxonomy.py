#!/usr/bin/env python3
"""Seed Concept taxonomy from NCERT catalog chapter concepts JSON."""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from typing import Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.concept import Concept
from packages.core.database.models.ncert_catalog import NcertCatalogChapter

ConceptKey = Tuple[str, int, str, int, str]


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "concept"


async def _load_existing_keys(db: AsyncSession) -> Set[ConceptKey]:
    result = await db.execute(
        select(
            Concept.board,
            Concept.class_num,
            Concept.subject_key,
            Concept.chapter_no,
            Concept.slug,
        ).where(Concept.board == "CBSE")
    )
    return {
        (row.board, row.class_num, row.subject_key, row.chapter_no, row.slug)
        for row in result.all()
    }


async def seed_concepts(db: AsyncSession, *, dry_run: bool = False) -> int:
    await db.execute(text("SET statement_timeout = '180s'"))
    chapters_result = await db.execute(select(NcertCatalogChapter))
    chapters = chapters_result.scalars().all()
    existing = await _load_existing_keys(db)
    pending: list[Concept] = []
    created = 0

    for ch in chapters:
        concepts_raw = ch.concepts or []
        if not isinstance(concepts_raw, list):
            continue
        for item in concepts_raw:
            if isinstance(item, str):
                name = item.strip()
            elif isinstance(item, dict):
                name = (item.get("name") or item.get("title") or "").strip()
            else:
                continue
            if not name:
                continue
            slug = _slugify(name)
            key: ConceptKey = ("CBSE", ch.class_num, ch.subject_key, ch.chapter_no, slug)
            if key in existing:
                continue
            existing.add(key)
            created += 1
            if dry_run:
                continue
            pending.append(
                Concept(
                    board="CBSE",
                    class_num=ch.class_num,
                    subject_key=ch.subject_key,
                    chapter_no=ch.chapter_no,
                    name=name,
                    slug=slug,
                    ncert_chapter_id=ch.id,
                    tenant_id=None,
                )
            )

    if not dry_run and pending:
        for concept in pending:
            db.add(concept)
            await db.commit()
            db.expunge_all()

    return created


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Seed Concept taxonomy from NCERT catalog")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        n = await seed_concepts(db, dry_run=args.dry_run)
    action = "Would create" if args.dry_run else "Created"
    print(f"{action} {n} concept row(s)")


if __name__ == "__main__":
    asyncio.run(main())
