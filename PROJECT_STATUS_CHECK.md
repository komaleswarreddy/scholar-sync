# Check Supabase Project Status

## ⚠️ Current Issue

The database hostname `db.btzzflqfqitkjrmtfojg.supabase.co` is not resolving. This usually means:

1. **Project is Paused** (most common)
2. **Project was deleted**
3. **Project reference is incorrect**

## 🔍 How to Check Project Status

### Step 1: Go to Supabase Dashboard

1. Visit: **https://supabase.com/dashboard**
2. Sign in to your account

### Step 2: Check Project List

Look for a project with reference: `btzzflqfqitkjrmtfojg`

**What to look for:**
- ✅ **Green dot / "Active"** = Project is running
- ⏸️ **Gray dot / "Paused"** = Project is paused (needs restoration)
- ❌ **Not in list** = Project might be deleted or wrong reference

### Step 3: If Project is Paused

1. Click on the paused project
2. Look for **"Restore"** or **"Resume"** button
3. Click it
4. Wait 2-3 minutes for project to activate
5. Try connection again

### Step 4: Verify Project Details

Once project is active:

1. Click on the project
2. Go to **Settings** → **General**
3. Check:
   - **Project ID**: Should match `btzzflqfqitkjrmtfojg`
   - **Region**: Note this (e.g., `us-east-1`)
   - **Status**: Should be "Active"

### Step 5: Get Fresh Connection String

After project is active:

1. Go to **Settings** → **Database**
2. Scroll to **Connection string**
3. Click **URI** tab
4. Copy the connection string
5. It should look like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres
   ```

## 🔄 Alternative: Create New Project

If the project doesn't exist or can't be restored:

1. Go to Supabase Dashboard
2. Click **"New Project"**
3. Fill in:
   - **Name**: `scholarsync-dev`
   - **Database Password**: Choose a password (save it!)
   - **Region**: Choose closest to you
4. Wait 2-3 minutes for setup
5. Get the new connection string
6. Update `backend/.env` with new connection string

## 🧪 Test After Restoration

Once project is active, test connection:

```bash
cd backend
source venv/bin/activate
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

## 📝 What to Do Now

1. **Check Supabase Dashboard** - Is project active?
2. **If paused** - Click "Restore" and wait
3. **If not found** - Create new project or verify project reference
4. **Get fresh connection string** - From Settings → Database
5. **Update .env** - With new connection string
6. **Test connection** - Using the command above

## 💡 Quick Check

You can also check project status via API (if you have access token), but the easiest way is through the dashboard.


