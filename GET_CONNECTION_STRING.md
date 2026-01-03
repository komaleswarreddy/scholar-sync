# How to Get the Correct Database Connection String

## Step-by-Step Instructions

### Step 1: Access Supabase Dashboard

1. Go to: **https://supabase.com/dashboard**
2. Sign in to your account
3. You should see your project list

### Step 2: Select Your Project

1. Find project with reference: `btzzflqfqitkjrmtfojg`
2. Click on it to open

### Step 3: Check Project Status

**Important**: Look at the top of the dashboard:
- ✅ **"Active"** or **"Running"** = Good, continue
- ⏸️ **"Paused"** = Click "Restore" button and wait 2-3 minutes

### Step 4: Get Connection String

1. Click **Settings** (gear icon) in the left sidebar
2. Click **Database** in the settings menu
3. Scroll down to **Connection string** section
4. You'll see tabs: **URI**, **JDBC**, **Golang**, etc.
5. Click **URI** tab
6. You'll see a connection string like:

```
postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

OR

```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### Step 5: Copy the Connection String

**Important**: 
- Copy the ENTIRE string
- It should include your password (or `[YOUR-PASSWORD]` placeholder)
- Note which format you see (pooler or direct)

### Step 6: Convert for AsyncPG

The connection string needs `+asyncpg` added:

**If you see:**
```
postgresql://postgres.btzzflqfqitkjrmtfojg:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Change to:**
```
postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**If you see:**
```
postgresql://postgres:password@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres
```

**Change to:**
```
postgresql+asyncpg://postgres:password@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres
```

### Step 7: Handle Password Encoding

If your password has special characters (like `@`), they need to be URL-encoded:

- `@` → `%40`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`
- `&` → `%26`
- `+` → `%2B`
- `=` → `%3D`

**Your password**: `ItsTime@365LetsGo`
**Encoded**: `ItsTime%40365LetsGo`

So if the connection string shows:
```
postgresql://postgres:ItsTime@365LetsGo@host:port/db
```

Change to:
```
postgresql+asyncpg://postgres:ItsTime%40365LetsGo@host:port/db
```

### Step 8: Update .env File

1. Open `backend/.env`
2. Find the line: `DATABASE_URL=...`
3. Replace with your converted connection string
4. Save the file

### Step 9: Test the Connection

```bash
cd backend
source venv/bin/activate
python test_db_connection.py
```

Or manually test:
```bash
python -c "
from app.core.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT version()')
        print('✅ Connected!', result.scalar()[:50])
asyncio.run(test())
"
```

## Common Issues

### Issue 1: "Project not found" or "Paused"
**Solution**: 
- Go to dashboard
- Check if project is paused
- Click "Restore" if needed
- Wait 2-3 minutes

### Issue 2: "Password authentication failed"
**Solution**:
- Verify password is correct
- Check URL encoding of special characters
- Try resetting password in Supabase Settings → Database

### Issue 3: "Connection refused"
**Solution**:
- Check if using correct port (5432 for direct, 6543 for pooler)
- Verify connection string format
- Try the other connection type (pooler vs direct)

### Issue 4: "Host not found" (DNS error)
**Solution**:
- Verify project reference is correct
- Check Supabase project is active
- Try the pooler connection instead of direct

## Quick Reference

**Your Project Reference**: `btzzflqfqitkjrmtfojg`
**Your Password**: `ItsTime@365LetsGo` (encode `@` as `%40`)

**Expected Formats**:
- Pooler: `postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:ItsTime%40365LetsGo@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
- Direct: `postgresql+asyncpg://postgres:ItsTime%40365LetsGo@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres`

## Need Help?

If you're stuck:
1. Take a screenshot of the Supabase connection string page
2. Share the connection string format you see (you can redact the password)
3. I can help convert it to the correct format


