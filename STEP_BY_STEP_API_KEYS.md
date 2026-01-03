# Step-by-Step: Adding API Keys

Let's add API keys one by one and test each one. I'll guide you through each step.

## Current Status

Your `.env` file has placeholder values. We'll replace them one by one.

---

## Step 1: Pinecone API Key 🔴 **START HERE**

### Why it's needed:
- Stores document embeddings for semantic search
- Powers the chat feature (finding relevant content)
- Required for source ingestion

### How to get it:

1. **Go to Pinecone**: https://www.pinecone.io/
2. **Sign up** (free tier available)
3. **Create an Index**:
   - Click "Create Index"
   - **Name**: `scholarsync-vectors`
   - **Dimensions**: `1536` (for OpenAI embeddings)
   - **Metric**: `cosine`
   - **Environment**: Choose closest to you (e.g., `us-east-1`)
4. **Get API Key**:
   - Go to "API Keys" section
   - Copy your API key
   - Note your environment (e.g., `us-east-1`)

### Add to .env:

Open `backend/.env` and replace:
```bash
PINECONE_API_KEY=your-pinecone-api-key
```

With your actual key:
```bash
PINECONE_API_KEY=pc-abc123def456...
```

### Test it:

Run this command to test:
```bash
cd backend
python test_api_keys.py
```

Or test just Pinecone:
```bash
python -c "from test_api_keys import test_pinecone; test_pinecone()"
```

**Tell me when you've added your Pinecone key, and I'll help you test it!**

---

## Step 2: OpenAI API Key 🔴 **NEXT**

### Why it's needed:
- Generates embeddings (converts text to vectors)
- Powers Studio features (quiz, flashcards generation)
- Required for vector search

### How to get it:

1. **Go to OpenAI**: https://platform.openai.com/
2. **Sign up** or log in
3. **Get API Key**:
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy the key (starts with `sk-`)
   - **Important**: Save it immediately - you can't see it again!

### Add to .env:

Replace:
```bash
OPENAI_API_KEY=your-openai-api-key
```

With:
```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### Test it:

```bash
python -c "from test_api_keys import test_openai; test_openai()"
```

---

## Step 3: Gemini API Key 🔴 **NEXT**

### Why it's needed:
- Powers chat responses
- Handles long context (large documents)
- Used for RAG chat feature

### How to get it:

1. **Go to Google AI Studio**: https://makersuite.google.com/app/apikey
2. **Sign in** with Google account
3. **Create API Key**:
   - Click "Create API Key"
   - Copy the key (starts with `AIzaSy`)

### Add to .env:

Replace:
```bash
GEMINI_API_KEY=your-gemini-api-key
```

With:
```bash
GEMINI_API_KEY=AIzaSy-your-actual-key-here
```

### Test it:

```bash
python -c "from test_api_keys import test_gemini; test_gemini()"
```

---

## Step 4: Storage (Choose One)

### Option A: Supabase Storage ⭐ (Recommended - You already have Supabase!)

1. **Go to your Supabase project**: https://supabase.com/dashboard
2. **Storage** → **Create bucket**
   - Name: `scholarsync-files`
   - Public: No (private bucket)
3. **Your keys are already in .env**:
   - `SUPABASE_URL` ✅
   - `SUPABASE_KEY` ✅

### Option B: AWS S3

1. **Go to AWS**: https://aws.amazon.com/
2. **Create S3 bucket**
3. **Create IAM user** with S3 permissions
4. **Get access keys**

### Add to .env:

Replace:
```bash
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=scholarsync-storage
```

### Test it:

```bash
python -c "from test_api_keys import test_aws_s3; test_aws_s3()"
# OR
python -c "from test_api_keys import test_supabase_storage; test_supabase_storage()"
```

---

## Step 5: Clerk Keys 🟡 (Can be done later)

### Why it's needed:
- User authentication
- Session management
- Multi-tenancy support

### How to get it:

1. **Go to Clerk**: https://clerk.com/
2. **Sign up** (free tier)
3. **Create application**
4. **Get keys**:
   - Publishable Key (frontend)
   - Secret Key (backend)

### Add to .env:

**Backend** (`backend/.env`):
```bash
CLERK_SECRET_KEY=sk_test_your-key-here
```

**Frontend** (`apps/web/.env.local`):
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-key-here
```

---

## Testing All Keys

After adding keys, test all at once:

```bash
cd backend
python test_api_keys.py
```

This will show you which keys are working and which still need to be added.

---

## Ready to Start?

**Let's begin with Step 1: Pinecone API Key**

1. Get your Pinecone API key (follow instructions above)
2. Add it to `backend/.env`
3. Tell me when it's added, and I'll help you test it!


