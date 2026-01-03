# Environment Variables Setup Guide

## ✅ Files Created

- `backend/.env` - Backend environment variables
- `apps/web/.env.local` - Frontend environment variables

## 📝 Next Steps: Add Your API Keys

### Backend (.env)

Edit `backend/.env` and replace the placeholder values:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scholarsync
# Or for Supabase:
# DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres

# Vector Database
PINECONE_API_KEY=your-actual-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=scholarsync-vectors

# LLM APIs
OPENAI_API_KEY=sk-your-actual-openai-key
GEMINI_API_KEY=your-actual-gemini-key

# Storage
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Authentication
CLERK_SECRET_KEY=sk_test_your-clerk-secret-key

# App
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend (.env.local)

Edit `apps/web/.env.local` and replace the placeholder values:

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-clerk-publishable-key
CLERK_SECRET_KEY=sk_test_your-clerk-secret-key

# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Environment
NEXT_PUBLIC_ENVIRONMENT=development
```

## 🔑 Where to Get API Keys

### 1. Database (PostgreSQL/Supabase)

**Supabase (Recommended):**
1. Go to https://supabase.com
2. Create a new project
3. Go to Settings → Database
4. Copy the connection string
5. Format: `postgresql+asyncpg://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres`

**Local PostgreSQL:**
```bash
createdb scholarsync
# Then use: postgresql+asyncpg://user:password@localhost:5432/scholarsync
```

### 2. Pinecone

1. Sign up at https://pinecone.io
2. Create a new index:
   - Name: `scholarsync-vectors`
   - Dimensions: `1536` (for OpenAI embeddings)
   - Metric: `cosine`
3. Go to API Keys section
4. Copy your API key

### 3. OpenAI

1. Go to https://platform.openai.com/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### 4. Google Gemini

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

### 5. AWS S3

1. Go to AWS Console
2. Create S3 bucket
3. Create IAM user with S3 permissions
4. Generate access keys
5. Copy Access Key ID and Secret Access Key

### 6. Clerk

1. Go to https://clerk.com
2. Sign up or sign in
3. Create a new application
4. Go to API Keys section
5. Copy:
   - Publishable Key (starts with `pk_test_`)
   - Secret Key (starts with `sk_test_`)
6. Add `http://localhost:3000` to allowed origins

## ⚠️ Important Notes

- **Never commit `.env` or `.env.local` files to git** (they're in .gitignore)
- **Keep your API keys secure** - don't share them
- **Use different keys for development and production**
- **For production**, use environment variables from your hosting platform

## ✅ Verification

After adding your keys, test the backend:

```bash
cd backend
source venv/bin/activate
python -c "from app.core.config import settings; print('✅ Config loaded!')"
```

If you see the success message, your environment is configured correctly!


