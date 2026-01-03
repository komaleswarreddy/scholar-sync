# Next Steps Checklist

## ✅ Completed

- [x] Backend server starts successfully
- [x] Health endpoint working
- [x] API docs accessible
- [x] Lazy API key loading implemented
- [x] Supabase API key added
- [x] Database URL configured (needs verification)

## 🔄 In Progress

### 1. Database Connection (Priority: HIGH)

**Current Issue**: DNS resolution error for database hostname

**Action Items**:
- [ ] Verify Supabase project is active (not paused)
- [ ] Get correct connection string from Supabase dashboard
- [ ] Update DATABASE_URL in `.env` if needed
- [ ] Run database schema (`init_db.sql`) in Supabase SQL Editor
- [ ] Test database connection

**How to Fix**:
1. Go to https://supabase.com/dashboard
2. Select your project
3. Check project status (should be "Active")
4. Go to **Settings** → **Database**
5. Copy **Connection string** → **URI**
6. Convert to asyncpg: `postgresql+asyncpg://...`
7. Update `backend/.env`
8. Run `backend/init_db.sql` in SQL Editor

### 2. Add Remaining API Keys (Priority: MEDIUM)

**Needed for full functionality**:

- [ ] **Pinecone API Key**
  - Go to https://pinecone.io
  - Create index: `scholarsync-vectors` (1536 dims, cosine)
  - Get API key
  - Add to `backend/.env`

- [ ] **OpenAI API Key**
  - Go to https://platform.openai.com/api-keys
  - Create new key
  - Add to `backend/.env`

- [ ] **Google Gemini API Key**
  - Go to https://makersuite.google.com/app/apikey
  - Create API key
  - Add to `backend/.env`

- [ ] **Clerk Keys**
  - Go to https://clerk.com
  - Create application
  - Get publishable key and secret key
  - Add to `backend/.env` and `apps/web/.env.local`

- [ ] **AWS S3** (or use Supabase Storage)
  - Create S3 bucket OR
  - Use Supabase Storage (already have it!)

## 🧪 Testing Steps

After each step, test:

### Test 1: Database Connection
```bash
cd backend
source venv/bin/activate
python -c "
from app.core.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT COUNT(*) FROM tenants')
        print(f'✅ Connected! {result.scalar()} tenant(s)')
asyncio.run(test())
"
```

### Test 2: Server Health
```bash
cd backend
source venv/bin/activate
python run.py
# In another terminal:
curl http://localhost:8000/health
```

### Test 3: API Endpoints
- Visit: http://localhost:8000/api/docs
- Test endpoints interactively

## 📋 Quick Reference

**Backend .env location**: `backend/.env`
**Frontend .env location**: `apps/web/.env.local`
**Database schema**: `backend/init_db.sql`

## 🎯 Priority Order

1. **Fix database connection** (blocks data operations)
2. **Add Clerk keys** (blocks authentication)
3. **Add Pinecone key** (blocks vector search)
4. **Add OpenAI key** (blocks embeddings)
5. **Add Gemini key** (blocks chat)
6. **Add S3/Storage** (blocks file uploads)

## 💡 Tips

- Server can start without API keys (lazy loading)
- Database connection is tested on first use
- You can test endpoints one by one as you add keys
- Use Supabase Storage instead of S3 for simplicity


