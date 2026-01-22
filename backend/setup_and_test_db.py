#!/usr/bin/env python3
"""
Database Setup and Test Script

This script:
1. Tests database connection
2. Creates tables if they don't exist
3. Seeds default tenant if it doesn't exist
4. Tests the full middleware flow
"""

import asyncio
import uuid
import sys
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.tenant import Tenant
from app.models.source import Source
from app.models.chat import Chat, Message
from app.models.note import Note
from sqlalchemy import select

DEV_TENANT_ID = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"

async def test_connection():
    """Test if we can connect to the database"""
    print("Testing database connection...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar()
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

async def create_tables():
    """Create all tables if they don't exist"""
    print("\nCreating database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables created/verified successfully!")
        return True
    except Exception as e:
        print(f"Failed to create tables: {str(e)}")
        return False

async def run_migration_add_user_id():
    """Add user_id column to sources table if it doesn't exist"""
    print("\nRunning migration: Add user_id to sources table...")
    try:
        async with AsyncSessionLocal() as session:
            # Check if user_id column exists
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='sources' AND column_name='user_id'
            """))
            column_exists = result.scalar_one_or_none() is not None
            
            if column_exists:
                print("user_id column already exists in sources table")
                return True
            
            # Add user_id column
            await session.execute(text("ALTER TABLE sources ADD COLUMN user_id TEXT"))
            await session.commit()
            
            # Create index
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_sources_user_id ON sources(user_id)"))
            await session.commit()
            
            print("Successfully added user_id column to sources table")
            print("   Note: Existing sources will have NULL user_id. You may want to:")
            print("   - Delete them: DELETE FROM sources WHERE user_id IS NULL;")
            print("   - Or assign them to a user: UPDATE sources SET user_id = 'your_user_id' WHERE user_id IS NULL;")
            return True
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        return False

async def seed_default_tenant():
    """Seed the default tenant if it doesn't exist"""
    print("\nSeeding default tenant...")
    try:
        async with AsyncSessionLocal() as session:
            # Check if tenant exists
            result = await session.execute(
                select(Tenant).where(Tenant.subdomain == "default")
            )
            existing_tenant = result.scalar_one_or_none()

            if existing_tenant:
                print(f"Tenant 'default' already exists (ID: {existing_tenant.id})")
                return True

            # Create new tenant
            new_tenant = Tenant(
                id=uuid.UUID(DEV_TENANT_ID),
                subdomain="default",
                name="Development School",
                settings={"theme": "light"}
            )
            session.add(new_tenant)
            await session.commit()
            print(f"Created 'default' tenant (ID: {DEV_TENANT_ID})")
            return True
    except Exception as e:
        print(f"Failed to seed tenant: {str(e)}")
        return False

async def verify_tenant_lookup():
    """Verify we can look up the tenant (simulating middleware)"""
    print("\nVerifying tenant lookup (middleware simulation)...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.subdomain == "default")
            )
            tenant = result.scalar_one_or_none()

            if tenant:
                print(f"Tenant lookup successful!")
                print(f"   Subdomain: {tenant.subdomain}")
                print(f"   ID: {tenant.id}")
                print(f"   Name: {tenant.name}")
                return True
            else:
                print("Tenant not found!")
                return False
    except Exception as e:
        print(f"Tenant lookup failed: {str(e)}")
        return False

async def main():
    print("=" * 60)
    print("DATABASE SETUP AND TEST")
    print("=" * 60)

    # Step 1: Test connection
    if not await test_connection():
        print("\nCannot proceed - database connection failed")
        print("   Please check your DATABASE_URL in .env")
        sys.exit(1)

    # Step 2: Create tables
    if not await create_tables():
        print("\nTable creation failed, but continuing...")

    # Step 2.5: Run migration for user_id column
    if not await run_migration_add_user_id():
        print("\nMigration failed, but continuing...")

    # Step 3: Seed tenant
    if not await seed_default_tenant():
        print("\nTenant seeding failed, but continuing...")

    # Step 4: Verify lookup
    if not await verify_tenant_lookup():
        print("\nTenant lookup failed")

    # Cleanup
    await engine.dispose()

    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print("\nDatabase is ready for middleware to use!")
    print("   The middleware should now be able to:")
    print("   1. Connect to database")
    print("   2. Look up tenant by subdomain")
    print("   3. Extract user_id from JWT token")
    print("   4. Set both in request.state")

if __name__ == "__main__":
    asyncio.run(main())

