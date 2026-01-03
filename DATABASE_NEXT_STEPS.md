# Database Setup - Next Steps

## ✅ What's Done

- ✅ **DATABASE_URL** - Added to `.env` (needs password)
- ✅ **SUPABASE_URL** - Updated with your project URL
- ✅ **SUPABASE_KEY** - Already added

## ⚠️ Action Required: Add Your Database Password

Your connection string has `[YOUR-PASSWORD]` placeholder. You need to replace it with your actual database password.

### How to Find/Set Your Password

**Option 1: You Remember the Password**
- When you created the Supabase project, you set a database password
- Replace `[YOUR-PASSWORD]` in `.env` with that password

**Option 2: Reset the Password**
1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **Database**
4. Scroll to **Database password**
5. Click **Reset database password**
6. Copy the new password
7. Update `.env` with the new password

### Update .env

Edit `backend/.env` and replace `[YOUR-PASSWORD]`:

**Before:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres
```

**After (example):**
```env
DATABASE_URL=postgresql+asyncpg://postgres:MySecurePassword123@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres
```

## 📋 Step 2: Run Database Schema

After updating the password, you need to create the database tables.

### Method 1: Using Supabase SQL Editor (Recommended)

1. Go to https://supabase.com/dashboard
2. Select your project
3. Click **SQL Editor** in the sidebar
4. Click **New query**
5. Open `backend/init_db.sql` in your editor
6. Copy the entire contents
7. Paste into Supabase SQL Editor
8. Click **Run** (or press Cmd/Ctrl + Enter)
9. You should see: "Success. No rows returned"

### Method 2: Using psql (Command Line)

```bash
# Install psql if needed (macOS)
brew install postgresql

# Connect and run schema
psql "postgresql://postgres:YOUR_PASSWORD@db.btzzflqfqitkjrmtfojg.supabase.co:5432/postgres" -f backend/init_db.sql
```

## ✅ Step 3: Verify Database Connection

After updating the password, test the connection:

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.config import settings
from app.core.database import engine
import asyncio

async def test():
    try:
        async with engine.begin() as conn:
            print('✅ Database connection successful!')
    except Exception as e:
        print(f'❌ Connection failed: {e}')

asyncio.run(test())
"
```

If you see "✅ Database connection successful!", you're all set!

## 🗄️ What the Schema Creates

The `init_db.sql` script creates:

1. **tenants** - School/tenant information
2. **sources** - Uploaded documents (PDFs, text)
3. **chats** - Chat sessions
4. **messages** - Chat messages with citations
5. **notes** - User notes

Plus:
- Indexes for performance
- Foreign key relationships
- A test tenant with subdomain "default"

## 🧪 Quick Test

After everything is set up:

```bash
cd backend
source venv/bin/activate
python run.py
```

Visit: http://localhost:8000/health

Should return: `{"status":"healthy","version":"1.0.0"}`

## 📝 Summary Checklist

- [ ] Replace `[YOUR-PASSWORD]` in `DATABASE_URL` with actual password
- [ ] Run `backend/init_db.sql` in Supabase SQL Editor
- [ ] Test database connection
- [ ] Start backend server
- [ ] Verify health endpoint

## 🐛 Troubleshooting

### "password authentication failed"
- Check password is correct (no extra spaces)
- Try resetting password in Supabase dashboard

### "connection refused"
- Check Supabase project is active
- Verify connection string format
- Ensure `+asyncpg` is in the URL

### "relation does not exist"
- Run the `init_db.sql` schema script
- Check tables were created in Supabase dashboard

### "timeout"
- Check your internet connection
- Verify Supabase project is not paused
- Try again in a few moments

## 🎉 Once Connected

You'll be able to:
- Store tenant information
- Upload and index documents
- Save chat conversations
- Store user notes

Ready to continue! 🚀


