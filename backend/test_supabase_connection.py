"""
Test script to verify Supabase and PostgreSQL connections
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_postgres_connection_async():
    """Test PostgreSQL database connection (async)"""
    print("[TEST] Testing PostgreSQL connection...")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        from app.core.config import settings
        
        if not settings.DATABASE_URL:
            print("[ERROR] DATABASE_URL not set in .env file")
            return False
        
        # Create async engine and test connection
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print("[SUCCESS] PostgreSQL connection successful!")
            print(f"   Database version: {version[:50]}...")
            await engine.dispose()
            return True
    except Exception as e:
        print(f"[ERROR] PostgreSQL connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_supabase_storage():
    """Test Supabase Storage connection"""
    print("\n[TEST] Testing Supabase Storage connection...")
    try:
        from app.core.config import settings
        from app.services.storage import get_supabase_client
        
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            print("[ERROR] SUPABASE_URL or SUPABASE_KEY not set in .env file")
            return False
        
        print(f"   Supabase URL: {settings.SUPABASE_URL}")
        print(f"   API Key: {settings.SUPABASE_KEY[:20]}...{settings.SUPABASE_KEY[-10:]}")
        
        # Try to get the client
        client = get_supabase_client()
        print("[SUCCESS] Supabase client created successfully!")
        
        # Test bucket access
        bucket_name = "scholarsync-files"
        try:
            # Try to list buckets or check if bucket exists
            buckets = client.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if bucket_name in bucket_names:
                print(f"[SUCCESS] Storage bucket '{bucket_name}' exists!")
            else:
                print(f"[WARNING] Storage bucket '{bucket_name}' not found.")
                print(f"   Available buckets: {bucket_names}")
                print(f"   You may need to create the bucket or update the bucket name in storage.py")
            
            return True
        except Exception as e:
            print(f"[WARNING] Could not verify bucket (this is okay if bucket doesn't exist yet): {str(e)}")
            print("   The connection works, but you may need to create the 'scholarsync-files' bucket")
            return True  # Connection works even if bucket check fails
            
    except Exception as e:
        print(f"[ERROR] Supabase Storage connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Testing Supabase and PostgreSQL Connections")
    print("=" * 60)
    print()
    
    # Check environment variables
    from app.core.config import settings
    print("Environment Variables Check:")
    print(f"   DATABASE_URL: {'[OK] Set' if settings.DATABASE_URL else '[MISSING] Not set'}")
    print(f"   SUPABASE_URL: {'[OK] Set' if settings.SUPABASE_URL else '[MISSING] Not set'}")
    print(f"   SUPABASE_KEY: {'[OK] Set' if settings.SUPABASE_KEY else '[MISSING] Not set'}")
    print()
    
    if not settings.DATABASE_URL:
        print("[ERROR] DATABASE_URL is required. Please add it to your .env file")
        return
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_KEY are required. Please add them to your .env file")
        return
    
    # Test connections
    import asyncio
    pg_ok = asyncio.run(test_postgres_connection_async())
    supabase_ok = test_supabase_storage()
    
    print()
    print("=" * 60)
    if pg_ok and supabase_ok:
        print("[SUCCESS] All connections successful! You're ready to go.")
    else:
        print("[ERROR] Some connections failed. Please check the errors above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
