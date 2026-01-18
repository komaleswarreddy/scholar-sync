"""
Script to add the feedback column to the messages table.
Run this script to fix the 500 error when loading chats.

Usage:
    python backend/add_feedback_column.py
"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import engine

async def add_feedback_column():
    """Add feedback column to messages table if it doesn't exist."""
    try:
        async with engine.begin() as conn:
            # Check if column exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'messages' 
                AND column_name = 'feedback'
            """)
            result = await conn.execute(check_query)
            exists = result.fetchone() is not None
            
            if exists:
                print("[OK] Feedback column already exists in messages table.")
                return
            
            # Add the column
            alter_query = text("""
                ALTER TABLE messages 
                ADD COLUMN feedback VARCHAR
            """)
            await conn.execute(alter_query)
            print("[OK] Successfully added feedback column to messages table.")
            
    except Exception as e:
        print(f"[ERROR] Error adding feedback column: {type(e).__name__}: {str(e)}")
        print("\nYou can also run this SQL manually:")
        print("ALTER TABLE messages ADD COLUMN IF NOT EXISTS feedback VARCHAR;")
        sys.exit(1)

if __name__ == "__main__":
    print("Adding feedback column to messages table...")
    asyncio.run(add_feedback_column())
    print("\n[OK] Done! You can now restart your backend server.")
