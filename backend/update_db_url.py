"""
Quick script to update DATABASE_URL in .env file
"""

import sys
import re

def update_env_file(connection_string):
    """Update DATABASE_URL in .env file."""
    env_file = ".env"
    
    try:
        # Read current .env
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace DATABASE_URL line
        pattern = r'^DATABASE_URL=.*$'
        replacement = f'DATABASE_URL={connection_string}'
        
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Write back
        with open(env_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated {env_file}")
        print(f"   New DATABASE_URL: {connection_string[:80]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_db_url.py 'postgresql+asyncpg://...'")
        print()
        print("Example:")
        print("  python update_db_url.py 'postgresql+asyncpg://postgres:pass@host:5432/db'")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    update_env_file(connection_string)


