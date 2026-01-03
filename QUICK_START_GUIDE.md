# Quick Start Guide - Get Running in 30 Minutes

## Step-by-Step Setup

### Step 1: Database (5 minutes) ⭐ Start Here

**Use Supabase (Recommended):**

1. Go to https://supabase.com
2. Click "Start your project"
3. Sign up with GitHub (easiest)
4. Click "New Project"
5. Fill in:
   - **Name**: `scholarsync-dev`
   - **Database Password**: (save this!)
   - **Region**: Choose closest
6. Wait 2 minutes for setup
7. Go to **Settings** → **Database**
8. Find **Connection string** → **URI**
9. Copy it, format should be:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
   ```
10. Convert to asyncpg format for `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
   ```
11. Go to **SQL Editor** in Supabase
12. Copy contents of `backend/init_db.sql`
13. Paste and click "Run"
14. ✅ Database ready!

**Also get Supabase Storage (for files):**
1. In Supabase, go to **Storage**
2. Click "Create bucket"
3. Name: `scholarsync-files`
4. Make it **Private**
5. ✅ Storage ready!

---

### Step 2: Clerk Authentication (5 minutes)

1. Go to https://clerk.com
2. Click "Get Started"
3. Sign up (free)
4. Click "Create Application"
5. Choose:
   - **Name**: `ScholarSync Dev`
   - **Authentication**: Email (or Google for easier testing)
6. Click "Create"
7. Go to **API Keys**
8. Copy:
   - **Publishable key** (starts with `pk_test_`)
   - **Secret key** (starts with `sk_test_`)
9. Go to **Settings** → **Domains**
10. Add: `localhost:3000`
11. ✅ Clerk ready!

---

### Step 3: Pinecone (5 minutes)

1. Go to https://pinecone.io
2. Click "Get Started"
3. Sign up (free tier available)
4. Click "Create Index"
5. Fill in:
   - **Index Name**: `scholarsync-vectors`
   - **Dimensions**: `1536` (for OpenAI embeddings)
   - **Metric**: `cosine`
   - **Cloud Provider**: AWS (or GCP)
   - **Region**: `us-east-1` (or closest)
6. Click "Create Index"
7. Wait 1 minute
8. Go to **API Keys**
9. Copy your API key
10. ✅ Pinecone ready!

---

### Step 4: OpenAI (3 minutes)

1. Go to https://platform.openai.com
2. Sign up or log in
3. Add payment method (required, but $5 free credit)
4. Go to **API Keys**: https://platform.openai.com/api-keys
5. Click "Create new secret key"
6. Name it: `scholarsync-dev`
7. **Copy immediately** (you won't see it again!)
8. Save it somewhere safe
9. ✅ OpenAI ready!

**Note**: You get $5 free credit. This lasts a long time for development.

---

### Step 5: Google Gemini (2 minutes)

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key
5. ✅ Gemini ready!

**Note**: Free tier is very generous for development.

---

### Step 6: AWS S3 (10 minutes) OR Use Supabase Storage

#### Option A: Use Supabase Storage (Easier - Already have it!)

If you used Supabase in Step 1, you already have storage! Just skip AWS S3.

**Update your code later** to use Supabase Storage instead of S3.

#### Option B: AWS S3 (If you want to use S3)

1. Go to https://aws.amazon.com
2. Create AWS account (free tier available)
3. Go to **S3** service
4. Click "Create bucket"
5. Name: `scholarsync-storage-dev`
6. Region: `us-east-1`
7. Uncheck "Block all public access" (or keep it for private)
8. Click "Create bucket"
9. Go to **IAM** → **Users**
10. Click "Add users"
11. Name: `scholarsync-s3-user`
12. Select "Programmatic access"
13. Click "Next: Permissions"
14. Attach policy: `AmazonS3FullAccess` (for dev only)
15. Click through and create user
16. **Save the Access Key ID and Secret Access Key**
17. ✅ AWS S3 ready!

---

## Step 7: Add Keys to .env Files

### Backend (.env)

Edit `backend/.env`:

```env
# Database (from Supabase Step 1)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres

# Vector Database (from Pinecone Step 3)
PINECONE_API_KEY=your-pinecone-key-here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=scholarsync-vectors

# LLM APIs
OPENAI_API_KEY=sk-proj-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here

# Storage (from AWS Step 6 OR use Supabase)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=scholarsync-storage-dev

# Authentication (from Clerk Step 2)
CLERK_SECRET_KEY=sk_test_your-clerk-secret-key

# App
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend (.env.local)

Edit `apps/web/.env.local`:

```env
# Clerk (from Step 2)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-clerk-publishable-key
CLERK_SECRET_KEY=sk_test_your-clerk-secret-key

# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Environment
NEXT_PUBLIC_ENVIRONMENT=development
```

---

## Step 8: Test Your Setup

### Test Backend:

```bash
cd backend
source venv/bin/activate
python -c "from app.core.config import settings; print('✅ Config loaded successfully!')"
```

If you see the success message, your environment is configured!

### Test Database Connection:

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        print('✅ Database connection successful!')
asyncio.run(test())
"
```

---

## Step 9: Start the Application!

### Terminal 1 - Backend:

```bash
cd backend
source venv/bin/activate
python run.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2 - Frontend:

```bash
pnpm --filter @scholarsync/web dev
```

You should see:
```
✓ Ready in X seconds
○ Local: http://localhost:3000
```

### Test:

1. Visit http://localhost:8000/health
   - Should return: `{"status":"healthy","version":"1.0.0"}`

2. Visit http://localhost:8000/api/docs
   - Should show API documentation

3. Visit http://localhost:3000
   - Should redirect to Clerk sign-in

---

## Troubleshooting

### "Field required" errors:
- Check all required fields in `.env` are filled
- No placeholder values (like `your-key-here`)

### Database connection errors:
- Verify `DATABASE_URL` format is correct
- Check password is correct
- Ensure database exists

### API key errors:
- Verify keys are copied correctly (no extra spaces)
- Check keys are active in respective dashboards
- For OpenAI: Ensure payment method is added

### Port already in use:
- Backend: Change port in `backend/run.py`
- Frontend: Kill process on port 3000 or change port

---

## You're Done! 🎉

Once all services are connected, you can:
1. Upload PDFs
2. Chat with your documents
3. Generate quizzes and flashcards
4. Create notes

Happy coding! 🚀


