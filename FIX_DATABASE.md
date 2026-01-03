# Fix Database Connection - Step by Step

## Current Issue

Database hostname `db.btzzflqfqitkjrmtfojg.supabase.co` is not resolving.

## Solution Steps

### Step 1: Verify Supabase Project Status

1. Go to: https://supabase.com/dashboard
2. Look for your project: `btzzflqfqitkjrmtfojg`
3. Check status:
   - ✅ **Active** = Good, continue
   - ⏸️ **Paused** = Click "Restore" and wait 2-3 minutes

### Step 2: Get Correct Connection String

1. In Supabase dashboard, click your project
2. Go to **Settings** (gear icon) → **Database**
3. Scroll to **Connection string** section
4. Click **URI** tab
5. You'll see something like:
   ```
   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
6. **Copy this entire string**

### Step 3: Convert to AsyncPG Format

The connection string needs `+asyncpg` added:

**Original:**
```
postgresql://postgres.btzzflqfqitkjrmtfojg:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**For .env (add +asyncpg):**
```
postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Important**: 
- If password has special characters, they should be URL-encoded
- `@` becomes `%40`
- Your password `ItsTime@365LetsGo` should be `ItsTime%40365LetsGo`

### Step 4: Update .env File

Edit `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:ItsTime%40365LetsGo@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Note**: Use the exact connection string from Supabase, just add `+asyncpg` after `postgresql`.

### Step 5: Test Connection

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.database import engine
import asyncio

async def test():
    try:
        async with engine.begin() as conn:
            result = await conn.execute('SELECT version()')
            print('✅ Database connected!')
            print(f'   Version: {result.scalar()[:50]}...')
            return True
    except Exception as e:
        print(f'❌ Error: {str(e)[:200]}')
        return False

asyncio.run(test())
"
```

### Step 6: Run Database Schema

Once connection works:

1. Go to Supabase SQL Editor
2. Click **New query**
3. Open `backend/init_db.sql`
4. Copy all contents
5. Paste into SQL Editor
6. Click **Run**
7. Should see: "Success. No rows returned"

### Step 7: Verify Tables Created

1. In Supabase, go to **Table Editor**
2. You should see:
   - `tenants`
   - `sources`
   - `chats`
   - `messages`
   - `notes`

## Alternative: Direct Connection (If Pooler Doesn't Work)

If the pooler connection doesn't work, try direct connection:

1. In Supabase Settings → Database
2. Find **Connection string** → **Direct connection**
3. Use port **5432** instead of **6543**
4. Format:
   ```
   postgresql+asyncpg://postgres:password@db.xxxxx.supabase.co:5432/postgres
   ```

## Troubleshooting

### "Connection refused"
- Check Supabase project is active
- Verify connection string is correct
- Try direct connection instead of pooler

### "Password authentication failed"
- Verify password is correct
- Check URL encoding of special characters
- Try resetting password in Supabase

### "Host not found"
- Check internet connection
- Verify Supabase project exists
- Try pinging the hostname

## Success Indicators

✅ Connection test returns version
✅ Can query `SELECT 1`
✅ Tables exist after running schema
✅ Can insert/query data


