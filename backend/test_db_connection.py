"""
Database Connection Tester

Tests different connection string formats to find the working one.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from urllib.parse import quote

# Your credentials
PASSWORD = "ItsTime@365LetsGo"
PASSWORD_ENCODED = quote(PASSWORD, safe='')
PROJECT_REF = "btzzflqfqitkjrmtfojg"

# Different connection string formats to try
CONNECTION_STRINGS = [
    # Format 1: Direct connection (port 5432)
    f"postgresql+asyncpg://postgres:{PASSWORD_ENCODED}@db.{PROJECT_REF}.supabase.co:5432/postgres",
    
    # Format 2: Pooler connection (port 6543)
    f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD_ENCODED}@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
    
    # Format 3: Pooler with session mode (port 5432)
    f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD_ENCODED}@aws-0-us-east-1.pooler.supabase.com:5432/postgres?pgbouncer=true",
    
    # Format 4: Alternative pooler format
    f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD_ENCODED}@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
    
    # Format 5: Direct with project ref in username
    f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD_ENCODED}@db.{PROJECT_REF}.supabase.co:5432/postgres",
]

async def test_connection(url: str, name: str):
    """Test a connection string."""
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute("SELECT version()")
            version = result.scalar()
            print(f"✅ {name}: SUCCESS")
            print(f"   URL: {url[:80]}...")
            print(f"   PostgreSQL: {version[:60]}...")
            await engine.dispose()
            return True, url
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"❌ {name}: FAILED - {error_msg}")
        return False, None

async def main():
    print("=" * 70)
    print("Testing Database Connection Strings")
    print("=" * 70)
    print()
    
    working_url = None
    
    for i, url in enumerate(CONNECTION_STRINGS, 1):
        name = f"Format {i}"
        success, url_result = await test_connection(url, name)
        if success:
            working_url = url_result
            print()
            print("=" * 70)
            print("✅ FOUND WORKING CONNECTION!")
            print("=" * 70)
            print()
            print("Add this to backend/.env:")
            print(f"DATABASE_URL={url_result}")
            print()
            break
        print()
    
    if not working_url:
        print("=" * 70)
        print("❌ None of the connection formats worked")
        print("=" * 70)
        print()
        print("Please:")
        print("1. Go to Supabase Dashboard")
        print("2. Settings → Database → Connection string")
        print("3. Copy the URI connection string")
        print("4. Add '+asyncpg' after 'postgresql'")
        print("5. Update backend/.env")
        print()
        print("Also check:")
        print("- Is your Supabase project active (not paused)?")
        print("- Is your password correct?")
        print("- Is your internet connection working?")
    
    return working_url

if __name__ == "__main__":
    result = asyncio.run(main())


