# Adding API Keys - Step by Step Guide

Let's add API keys one by one and test each one. I'll guide you through each step.

## Priority Order

1. **Pinecone API Key** - For vector search (needed for chat & source ingestion)
2. **OpenAI API Key** - For embeddings (needed for vector search)
3. **Gemini API Key** - For chat responses
4. **AWS S3 or Supabase Storage** - For file storage
5. **Clerk Keys** - For authentication (can be done later)

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

```bash
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=scholarsync-vectors
```

### Test it:
Once added, we'll test the Pinecone connection.

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

```bash
OPENAI_API_KEY=sk-proj-your-key-here
```

### Test it:
Once added, we'll test the OpenAI connection.

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

```bash
GEMINI_API_KEY=AIzaSy-your-key-here
```

### Test it:
Once added, we'll test the Gemini connection.

---

## Step 4: Storage (AWS S3 or Supabase Storage) 🟡

### Option A: Supabase Storage (Easier) ⭐

Since you already have Supabase for the database:

1. **Go to your Supabase project**
2. **Storage** → **Create bucket**
   - Name: `scholarsync-files`
   - Public: No (private bucket)
3. **Get Storage URL and Key**:
   - Settings → API
   - Copy `SUPABASE_URL` and `SUPABASE_KEY`

### Add to .env:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Option B: AWS S3

1. **Go to AWS**: https://aws.amazon.com/
2. **Create S3 bucket**
3. **Create IAM user** with S3 permissions
4. **Get access keys**

### Add to .env:

```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=scholarsync-storage
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

```bash
# Backend
CLERK_SECRET_KEY=sk_test_your-key-here
```

```bash
# Frontend (apps/web/.env.local)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-key-here
```

---

## Testing Each Key

After adding each key, we'll:
1. Restart the backend server
2. Test the connection
3. Verify it works
4. Move to the next key

---

## Ready to Start?

**Let's begin with Step 1: Pinecone API Key**

Tell me when you have your Pinecone API key ready, and I'll help you add it and test it!


