"""Check what chapter data is stored for Class 10 Science."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config.settings import settings


async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT DISTINCT class, subject, chapter_no, chapter_name 
                FROM ncert_global_documents 
                WHERE class=10 AND subject ILIKE 'Science%'
                ORDER BY chapter_no 
                LIMIT 20
            """)
        )
        rows = result.fetchall()
        print("\n" + "=" * 80)
        print("NCERT Data in Database - Class 10, Science")
        print("=" * 80)
        if rows:
            for c, s, n, cn in rows:
                print(f"Class={c:2d} | Subject={s:10s} | Chapter={n} | Name='{cn}'")
        else:
            print("❌ No data found!")
        print("=" * 80 + "\n")


asyncio.run(check())
