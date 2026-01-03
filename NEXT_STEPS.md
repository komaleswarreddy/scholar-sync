# Next Steps - Setup Progress

## ✅ Completed

1. ✅ **Monorepo structure** - All files created
2. ✅ **Node.js dependencies** - Installed via pnpm
3. ✅ **Frontend setup** - Next.js app ready
4. ✅ **Backend structure** - All code files created
5. ✅ **Environment templates** - `.env.example` files created
6. ✅ **Database schema** - SQL script ready (`backend/init_db.sql`)

## ⚠️ Action Required

### 1. Install Python 3.11+

**Your current Python version (3.7.3) is too old.**

**macOS (Recommended):**
```bash
# Option A: Using Homebrew
brew install python@3.11
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Option B: Using pyenv (better for managing multiple versions)
brew install pyenv
pyenv install 3.11.7
cd backend
pyenv local 3.11.7
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**After installing Python 3.11+, restore original requirements:**
```bash
# Restore the original requirements.txt (Python 3.11 compatible)
git checkout backend/requirements.txt
# Or manually update to use latest versions
```

### 2. Set Up Environment Variables

**Backend:**
```bash
cd backend
cp .env.example .env
# Edit .env and add your API keys
```

**Frontend:**
```bash
cd apps/web
cp .env.local.example .env.local
# Edit .env.local and add your Clerk keys
```

### 3. Set Up Database

**Option A: Using Supabase (Easiest)**
1. Create a Supabase project
2. Go to SQL Editor
3. Copy and paste contents of `backend/init_db.sql`
4. Run the script
5. Update `DATABASE_URL` in `backend/.env`

**Option B: Using Local PostgreSQL**
```bash
# Create database
createdb scholarsync

# Run schema
psql scholarsync < backend/init_db.sql

# Or connect and paste SQL
psql scholarsync
# Then paste contents of backend/init_db.sql
```

### 4. Set Up External Services

1. **Pinecone:**
   - Create account at https://pinecone.io
   - Create index: `scholarsync-vectors` (1536 dimensions, cosine)
   - Get API key

2. **AWS S3:**
   - Create S3 bucket
   - Create IAM user with S3 access
   - Get access key and secret

3. **Clerk:**
   - Create account at https://clerk.com
   - Create application
   - Get publishable key and secret key
   - Add `http://localhost:3000` to allowed origins

4. **API Keys:**
   - OpenAI: https://platform.openai.com/api-keys
   - Google Gemini: https://makersuite.google.com/app/apikey

### 5. Start the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # After Python 3.11 is installed
python run.py
# Should see: "Uvicorn running on http://0.0.0.0:8000"
```

**Terminal 2 - Frontend:**
```bash
pnpm --filter @scholarsync/web dev
# Should see: "Ready on http://localhost:3000"
```

### 6. Verify Setup

1. **Backend Health:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy","version":"1.0.0"}
   ```

2. **API Docs:**
   Visit: http://localhost:8000/api/docs

3. **Frontend:**
   Visit: http://localhost:3000
   - Should redirect to sign-in
   - Sign up with Clerk
   - Should redirect to dashboard

## 📝 Quick Reference

- **Backend API:** http://localhost:8000
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/docs
- **Database Schema:** `backend/init_db.sql`
- **Environment Templates:** `.env.example` files

## 🐛 Troubleshooting

**Python version issues:**
- See `PYTHON_VERSION.md` for detailed instructions

**Database connection:**
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format in `.env`

**Clerk authentication:**
- Verify keys in `.env.local`
- Check Clerk dashboard for allowed origins

**Port conflicts:**
- Backend: Change port in `backend/run.py`
- Frontend: Change port in `apps/web/package.json` scripts


