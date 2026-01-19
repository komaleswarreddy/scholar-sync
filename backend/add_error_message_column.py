"""
Script to add the error_message column to the sources table.
Run this script to enable error message storage and display.

Usage:
    python backend/add_error_message_column.py
"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import engine

async def add_error_message_column():
    """Add error_message column to sources table if it doesn't exist."""
    try:
        async with engine.begin() as conn:
            # Check if column exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sources' 
                AND column_name = 'error_message'
            """)
            result = await conn.execute(check_query)
            exists = result.fetchone() is not None
            
            if exists:
                print("[OK] error_message column already exists in sources table.")
                return
            
            # Add the column
            alter_query = text("""
                ALTER TABLE sources 
                ADD COLUMN error_message VARCHAR
            """)
            await conn.execute(alter_query)
            print("[OK] Successfully added error_message column to sources table.")
            
    except Exception as e:
        print(f"[ERROR] Error adding error_message column: {type(e).__name__}: {str(e)}")
        print("\nYou can also run this SQL manually:")
        print("ALTER TABLE sources ADD COLUMN IF NOT EXISTS error_message VARCHAR;")
        sys.exit(1)

if __name__ == "__main__":
    print("Adding error_message column to sources table...")
    asyncio.run(add_error_message_column())
    print("\n[OK] Done! You can now restart your backend server.")
