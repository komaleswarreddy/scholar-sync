# API Keys & Services Explained

## Overview

This document explains each service, whether it's required, and how to get started.

---

## 1. Database URL (PostgreSQL/Supabase) 🔴 **REQUIRED**

### What it is:
- **PostgreSQL** is the main database that stores:
  - Tenants (schools)
  - Sources (uploaded documents)
  - Chats and messages
  - Notes
  - User data

### Do you need it?
**YES - Required** - The app cannot run without a database.

### Options:

#### Option A: Supabase (Recommended - Free Tier Available) ⭐
- **Free tier**: 500MB database, 2GB bandwidth
- **Easiest setup**: No local installation needed
- **Includes**: PostgreSQL + Storage + Auth (though we use Clerk)

**How to get:**
1. Go to https://supabase.com
2. Sign up (free)
3. Create a new project
4. Go to **Settings → Database**
5. Copy the connection string
6. Format: `postgresql+asyncpg://postgres:[YOUR-PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres`

**Example:**
```
DATABASE_URL=postgresql+asyncpg://postgres:mypassword123@abcdefghijklmnop.supabase.co:5432/postgres
```

#### Option B: Local PostgreSQL
- **Free**: Install locally
- **Requires**: PostgreSQL installation on your machine

**How to set up:**
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15
createdb scholarsync

# Then use:
DATABASE_URL=postgresql+asyncpg://yourusername@localhost:5432/scholarsync
```

#### Option C: Other Cloud Providers
- **AWS RDS**, **Google Cloud SQL**, **Azure Database** - All work, but require setup

---

## 2. Pinecone API Key 🔴 **REQUIRED**

### What it is:
- **Pinecone** is a vector database that stores:
  - Document embeddings (AI representations of text)
  - Enables semantic search (finding relevant content by meaning, not just keywords)
  - Powers the RAG (Retrieval-Augmented Generation) chat feature

### Do you need it?
**YES - Required** - Chat functionality won't work without it.

### Why it's needed:
When you upload a PDF, the app:
1. Extracts text
2. Splits into chunks
3. Converts to embeddings (vectors)
4. Stores in Pinecone
5. When you ask a question, it searches Pinecone for relevant chunks

### Free Tier:
- **Free tier available**: 1 index, 100K vectors
- **Perfect for development/testing**

### How to get:
1. Go to https://pinecone.io
2. Sign up (free tier available)
3. Create an index:
   - **Name**: `scholarsync-vectors`
   - **Dimensions**: `1536` (for OpenAI embeddings)
   - **Metric**: `cosine`
   - **Environment**: Choose closest to you (e.g., `us-east-1`)
4. Go to **API Keys** section
5. Copy your API key

**Example:**
```
PINECONE_API_KEY=abc123def456...
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=scholarsync-vectors
```

---

## 3. OpenAI API Key 🔴 **REQUIRED**

### What it is:
- **OpenAI** provides:
  - Text embeddings (converting text to vectors for search)
  - GPT-4o-mini (for structured generation: quizzes, flashcards, etc.)

### Do you need it?
**YES - Required** - Used for:
- Generating embeddings (vector search)
- Studio features (quiz, flashcards generation)

### Free Tier:
- **Pay-as-you-go**: ~$0.10 per 1M tokens
- **$5 free credit** for new accounts
- **Very cheap** for development/testing

### How to get:
1. Go to https://platform.openai.com
2. Sign up or log in
3. Go to **API Keys** (https://platform.openai.com/api-keys)
4. Click **"Create new secret key"**
5. Copy the key (starts with `sk-`)
6. **Important**: Save it immediately - you can't see it again!

**Example:**
```
OPENAI_API_KEY=sk-proj-abc123def456...
```

### Cost Estimate:
- Embeddings: ~$0.0001 per document
- GPT-4o-mini: ~$0.15 per 1M input tokens
- **For testing**: $5 credit lasts a long time

---

## 4. Google Gemini API Key 🔴 **REQUIRED**

### What it is:
- **Google Gemini** provides:
  - Gemini 1.5 Flash (for chat responses)
  - Large context window (handles long documents)
  - Used for RAG chat and content-heavy generation

### Do you need it?
**YES - Required** - Chat feature uses Gemini for responses.

### Free Tier:
- **Free tier available**: 15 requests per minute
- **Generous free quota** for development

### How to get:
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click **"Create API Key"**
4. Copy the key

**Example:**
```
GEMINI_API_KEY=AIzaSyAbc123Def456...
```

### Alternative:
- You could use OpenAI GPT-4 for chat instead, but Gemini 1.5 Flash is cheaper and has better context handling

---

## 5. AWS S3 Credentials 🟡 **REQUIRED (but alternatives available)**

### What it is:
- **AWS S3** stores:
  - Uploaded PDF files
  - Original documents
  - File storage for sources

### Do you need it?
**YES - Required** - But you have alternatives:

#### Option A: AWS S3 (Original)
- **Free tier**: 5GB storage, 20K GET requests/month
- **Requires**: AWS account setup

**How to get:**
1. Go to https://aws.amazon.com
2. Create AWS account
3. Go to **S3** service
4. Create a bucket (e.g., `scholarsync-storage`)
5. Go to **IAM** → **Users** → Create user with S3 permissions
6. Generate access keys

**Example:**
```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_BUCKET_NAME=scholarsync-storage
```

#### Option B: Supabase Storage (Easier) ⭐
- **Free tier**: 1GB storage
- **Simpler setup**: Already have Supabase for database
- **Requires code change**: Need to update `storage.py` to use Supabase Storage instead of S3

#### Option C: Local File Storage (Development Only)
- **Free**: Store files locally
- **Not recommended for production**

---

## 6. Clerk Keys 🔴 **REQUIRED**

### What it is:
- **Clerk** provides:
  - User authentication (sign up, sign in)
  - User management
  - Session management
  - Multi-tenancy support

### Do you need it?
**YES - Required** - Authentication system.

### Free Tier:
- **Free tier**: Up to 10,000 monthly active users
- **Perfect for development and small apps**

### How to get:
1. Go to https://clerk.com
2. Sign up (free tier available)
3. Create a new application
4. Go to **API Keys** section
5. Copy:
   - **Publishable Key** (starts with `pk_test_`)
   - **Secret Key** (starts with `sk_test_`)
6. Go to **Settings** → **Allowed Origins**
7. Add: `http://localhost:3000`

**Example:**
```
# Frontend (.env.local)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_abc123...
CLERK_SECRET_KEY=sk_test_def456...

# Backend (.env)
CLERK_SECRET_KEY=sk_test_def456...
```

---

## Summary: What You Actually Need

### Minimum for Development:

1. ✅ **Database** (Supabase - Free) - **REQUIRED**
2. ✅ **Pinecone** (Free tier) - **REQUIRED**
3. ✅ **OpenAI** ($5 free credit) - **REQUIRED**
4. ✅ **Gemini** (Free tier) - **REQUIRED**
5. ✅ **Storage** (Supabase Storage - Free, or AWS S3) - **REQUIRED**
6. ✅ **Clerk** (Free tier) - **REQUIRED**

### Total Cost for Development:
**$0 - $5** (just OpenAI's $5 credit, everything else is free)

### Quick Start Priority:

1. **Start with Supabase** (Database + Storage in one)
2. **Get Clerk** (5 minutes)
3. **Get Pinecone** (5 minutes)
4. **Get OpenAI** (5 minutes, $5 credit)
5. **Get Gemini** (2 minutes, free)
6. **Get AWS S3** (or use Supabase Storage)

---

## Development vs Production

### Development (What you need now):
- All services above with free tiers
- Local development environment
- Test data

### Production (Later):
- Same services, but:
  - Paid tiers for higher limits
  - Production API keys
  - Proper security setup
  - Monitoring and logging

---

## Need Help?

Each service has excellent documentation:
- **Supabase**: https://supabase.com/docs
- **Pinecone**: https://docs.pinecone.io
- **OpenAI**: https://platform.openai.com/docs
- **Gemini**: https://ai.google.dev/docs
- **AWS S3**: https://docs.aws.amazon.com/s3
- **Clerk**: https://clerk.com/docs

---

## Next Steps

1. **Start with Supabase** (easiest, covers database + storage)
2. **Get Clerk** (quick setup)
3. **Get API keys** (OpenAI, Gemini, Pinecone)
4. **Add keys to .env files**
5. **Start the app!**


