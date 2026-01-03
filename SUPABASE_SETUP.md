# Supabase Setup Guide

## ✅ What You've Added

You've added your Supabase API key to `.env`:
```
SUPABASE_KEY=sb_secret_Ea20FQ_T_38nGwit_jYeNA_-IOqlFoG
```

## ⚠️ Important: You Still Need the Database URL

The **API key** is different from the **Database connection string**. You need both!

### What You Have:
- ✅ **SUPABASE_KEY** - API key for Supabase client (optional, for Supabase features)
- ❌ **DATABASE_URL** - PostgreSQL connection string (REQUIRED for the app to work)

## 📝 How to Get Your Database URL

### Step 1: Go to Supabase Dashboard
1. Go to https://supabase.com/dashboard
2. Select your project

### Step 2: Get Database Connection String
1. Go to **Settings** (gear icon in sidebar)
2. Click **Database**
3. Scroll down to **Connection string**
4. Find **URI** tab
5. Copy the connection string

It will look like:
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

### Step 3: Convert to AsyncPG Format

The app uses `asyncpg`, so you need to add `+asyncpg`:

**Original:**
```
postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

**For .env file:**
```
postgresql+asyncpg://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

### Step 4: Add to .env

Edit `backend/.env` and update:
```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres
```

**Replace:**
- `YOUR_PASSWORD` - The database password you set when creating the project
- `xxxxx` - Your project reference ID

## 🔐 About Your API Key

The key you provided (`sb_secret_...`) is a **Service Role Key**. This is:
- ✅ **Powerful** - Has full access to your project
- ⚠️ **Sensitive** - Never commit to git (already in .gitignore)
- ⚠️ **Development only** - For production, use environment variables

### Key Types:
- **Service Role Key** (`sb_secret_...`) - Full access, use in backend
- **Anon Key** (`eyJhbG...`) - Public, limited access, use in frontend

For this app, the Service Role Key is fine for backend use.

## ✅ Next Steps

1. **Get your DATABASE_URL** (see steps above)
2. **Add it to `backend/.env`**
3. **Run the database schema:**
   - Go to Supabase SQL Editor
   - Copy contents of `backend/init_db.sql`
   - Paste and run
4. **Test the connection:**
   ```bash
   cd backend
   source venv/bin/activate
   python -c "from app.core.config import settings; print('✅ Config loaded!')"
   ```

## 🗄️ Setting Up the Database Schema

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New query**
3. Copy the entire contents of `backend/init_db.sql`
4. Paste into the editor
5. Click **Run** (or press Cmd/Ctrl + Enter)
6. You should see: "Success. No rows returned"

This creates:
- `tenants` table
- `sources` table
- `chats` table
- `messages` table
- `notes` table
- A test tenant with subdomain "default"

## 🧪 Test Your Setup

After adding DATABASE_URL:

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.config import settings
print('✅ Config loaded!')
print(f'Database: {settings.DATABASE_URL[:30]}...')
"
```

If you see the success message, you're good to go!

## 📚 Additional Supabase Resources

- **Dashboard**: https://supabase.com/dashboard
- **Documentation**: https://supabase.com/docs
- **SQL Editor**: In dashboard → SQL Editor

## ⚠️ Security Reminder

- ✅ `.env` is in `.gitignore` (won't be committed)
- ⚠️ Never share your API keys
- ⚠️ Use different keys for development and production
- ⚠️ Service Role Key has full access - keep it secret!


