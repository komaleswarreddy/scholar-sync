"""
Test script to check if endpoints are working
"""
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_endpoints():
    """Test the endpoints to see what errors occur"""
    try:
        from app.core.database import AsyncSessionLocal, engine, Base
        from app.models import Source, Note, Tenant
        from sqlalchemy import select, text
        
        print("[TEST] Testing database connection...")
        async with AsyncSessionLocal() as db:
            # Test if tables exist
            result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            print(f"[TEST] Found tables: {tables}")
            
            if 'sources' not in tables:
                print("[ERROR] 'sources' table does not exist!")
                print("[INFO] Run: python init_db.py to create tables")
                return False
                
            if 'notes' not in tables:
                print("[ERROR] 'notes' table does not exist!")
                print("[INFO] Run: python init_db.py to create tables")
                return False
                
            if 'tenants' not in tables:
                print("[ERROR] 'tenants' table does not exist!")
                print("[INFO] Run: python init_db.py to create tables")
                return False
            
            # Test query
            print("[TEST] Testing query on sources table...")
            result = await db.execute(select(Source).limit(1))
            sources = result.scalars().all()
            print(f"[TEST] Query successful, found {len(sources)} sources")
            
            print("[TEST] Testing query on notes table...")
            result = await db.execute(select(Note).limit(1))
            notes = result.scalars().all()
            print(f"[TEST] Query successful, found {len(notes)} notes")
            
            print("[SUCCESS] Database and tables are working!")
            return True
            
    except Exception as e:
        import traceback
        print(f"[ERROR] Test failed: {type(e).__name__}: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_endpoints())
    sys.exit(0 if result else 1)
