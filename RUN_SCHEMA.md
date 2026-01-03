# Run Database Schema - Quick Guide

## ✅ Database Connection Ready

Your database password has been configured. Now you need to create the tables.

## 📋 Step 1: Run the Schema in Supabase

### Method 1: Supabase SQL Editor (Recommended)

1. **Go to Supabase Dashboard:**
   - Visit: https://supabase.com/dashboard
   - Select your project

2. **Open SQL Editor:**
   - Click **SQL Editor** in the left sidebar
   - Click **New query** button

3. **Copy and Paste Schema:**
   - Open `backend/init_db.sql` in your editor
   - Copy the entire file contents
   - Paste into Supabase SQL Editor

4. **Run the Query:**
   - Click **Run** button (or press Cmd/Ctrl + Enter)
   - Wait for "Success. No rows returned" message

5. **Verify Tables Created:**
   - Go to **Table Editor** in sidebar
   - You should see these tables:
     - `tenants`
     - `sources`
     - `chats`
     - `messages`
     - `notes`

## ✅ Step 2: Test Database Connection

After running the schema, test the connection:

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.database import engine
import asyncio

async def test():
    try:
        async with engine.begin() as conn:
            result = await conn.execute('SELECT COUNT(*) FROM tenants')
            count = result.scalar()
            print(f'✅ Database connected! Found {count} tenant(s)')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"
```

## 🚀 Step 3: Start the Backend Server

Once the schema is run and connection works:

```bash
cd backend
source venv/bin/activate
python run.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

## 🧪 Step 4: Test the API

Open in browser:
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/api/docs

## 📝 What the Schema Creates

The `init_db.sql` script creates:

1. **tenants** - School/tenant information
   - Includes a test tenant with subdomain "default"

2. **sources** - Uploaded documents
   - Links to tenants

3. **chats** - Chat sessions
   - Links to tenants and users

4. **messages** - Chat messages
   - Includes citations

5. **notes** - User notes
   - Can link to chat messages

Plus indexes for performance!

## ⚠️ Troubleshooting

### "relation does not exist"
- Run the schema script in Supabase SQL Editor
- Check tables were created in Table Editor

### "connection refused" or DNS error
- Check Supabase project is active (not paused)
- Verify connection string is correct
- Try again in a few moments

### "password authentication failed"
- Verify password is correct (URL-encoded if it has special chars)
- Check password in Supabase Settings → Database

## 🎉 Next Steps After Schema

Once database is working:
1. ✅ Add remaining API keys (Pinecone, OpenAI, Gemini, Clerk)
2. ✅ Start backend server
3. ✅ Start frontend server
4. ✅ Test the application!


