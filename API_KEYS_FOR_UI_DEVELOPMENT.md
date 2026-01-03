# API Keys Required for Frontend UI Development

## 🎯 Quick Answer: What You Need

### For Building Static UI Components (Layout, Styling, Components)
**✅ NO API KEYS NEEDED** - You can build the entire UI without any API keys!

### For Testing Interactive Features
Different features require different keys. See breakdown below.

---

## 📋 Complete API Keys List

### 1. 🔴 **Clerk Keys** - **MANDATORY for Authentication UI**

**Required For:**
- Sign-in page (`/sign-in`)
- Sign-up page (`/sign-up`)
- User authentication flow
- Protected routes (dashboard access)

**Can You Skip It?**
- ❌ **NO** - If you want users to sign in/sign up
- ✅ **YES** - If you're just building static UI components (we've disabled it for now)

**Where to Get:**
1. Go to https://clerk.com
2. Sign up (free tier: 10K users/month)
3. Create application
4. Copy keys from API Keys section

**Add to:**
```env
# apps/web/.env.local
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# backend/.env
CLERK_SECRET_KEY=sk_test_...
```

**Cost:** Free tier available

---

### 2. 🔴 **Pinecone API Key** - **MANDATORY for Upload & Chat Features**

**Required For:**
- ✅ Uploading documents (`POST /api/v1/ingest/upload`)
- ✅ Chat functionality (`POST /api/v1/chat/stream`)
- ✅ Source management (storing document embeddings)

**Can You Skip It?**
- ❌ **NO** - If you want to test file uploads or chat
- ✅ **YES** - If you're only building static UI components

**Where to Get:**
1. Go to https://pinecone.io
2. Sign up (free tier: 100K vectors)
3. Create index:
   - Name: `scholarsync-vectors`
   - Dimensions: `1536`
   - Metric: `cosine`
4. Copy API key

**Add to:**
```env
# backend/.env
PINECONE_API_KEY=your-key-here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=scholarsync-vectors
```

**Cost:** Free tier available

---

### 3. 🔴 **OpenAI API Key** - **MANDATORY for Upload & Studio Features**

**Required For:**
- ✅ Uploading documents (generates embeddings)
- ✅ Studio features (quiz, flashcards generation)
- ✅ Vector search (embeddings)

**Can You Skip It?**
- ❌ **NO** - If you want to test file uploads or studio features
- ✅ **YES** - If you're only building static UI components

**Where to Get:**
1. Go to https://platform.openai.com
2. Sign up (get $5 free credit)
3. Go to API Keys section
4. Create new secret key

**Add to:**
```env
# backend/.env
OPENAI_API_KEY=sk-proj-...
```

**Cost:** $5 free credit, then pay-as-you-go (~$0.10 per 1M tokens)

---

### 4. 🔴 **Google Gemini API Key** - **MANDATORY for Chat Feature**

**Required For:**
- ✅ Chat responses (`POST /api/v1/chat/stream`)
- ✅ Content-heavy studio tasks (reports, infographics)

**Can You Skip It?**
- ❌ **NO** - If you want to test chat functionality
- ✅ **YES** - If you're only building static UI components

**Where to Get:**
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google
3. Create API key

**Add to:**
```env
# backend/.env
GEMINI_API_KEY=AIzaSy...
```

**Cost:** Free tier (15 requests/minute)

---

### 5. 🟡 **AWS S3 / Storage** - **MANDATORY for File Uploads**

**Required For:**
- ✅ Uploading PDF files (`POST /api/v1/ingest/upload`)
- ✅ Storing original documents

**Can You Skip It?**
- ❌ **NO** - If you want to test file uploads
- ✅ **YES** - If you're only building static UI components

**Options:**
1. **AWS S3** (Original)
   - Free tier: 5GB storage
   - Requires AWS account setup

2. **Supabase Storage** (Easier) ⭐
   - Free tier: 1GB storage
   - Already have Supabase for database
   - Simpler setup

**Add to:**
```env
# backend/.env
# Option A: AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=scholarsync-storage

# Option B: Supabase Storage (if using)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

**Cost:** Free tier available (both options)

---

### 6. ✅ **Database (Supabase)** - **ALREADY CONFIGURED**

**Status:** ✅ Already set up and working!

**Not needed:** You already have this configured.

---

## 🎨 Frontend UI Development Breakdown

### Phase 1: Static UI Components (No API Keys Needed)
**What You Can Build:**
- ✅ Dashboard layout (3-column grid)
- ✅ Source list sidebar (UI only)
- ✅ Chat interface (UI only)
- ✅ Studio cards (UI only)
- ✅ Notes section (UI only)
- ✅ All styling and design tokens
- ✅ Navigation and routing
- ✅ Loading states and animations

**API Keys Required:** **NONE**

---

### Phase 2: Authentication UI (Clerk Required)
**What You Can Build:**
- ✅ Sign-in page
- ✅ Sign-up page
- ✅ Protected routes
- ✅ User profile

**API Keys Required:**
- 🔴 **Clerk** (mandatory)

---

### Phase 3: Source Management UI (Multiple Keys Required)
**What You Can Build:**
- ✅ File upload component
- ✅ Source list with real data
- ✅ Delete source functionality

**API Keys Required:**
- 🔴 **Pinecone** (for embeddings)
- 🔴 **OpenAI** (for embeddings)
- 🟡 **Storage** (S3 or Supabase)

---

### Phase 4: Chat UI (Multiple Keys Required)
**What You Can Build:**
- ✅ Chat message display
- ✅ Streaming responses
- ✅ Citations
- ✅ Source selection

**API Keys Required:**
- 🔴 **Pinecone** (for vector search)
- 🔴 **OpenAI** (for embeddings)
- 🔴 **Gemini** (for chat responses)

---

### Phase 5: Studio UI (Multiple Keys Required)
**What You Can Build:**
- ✅ Quiz generation
- ✅ Flashcards generation
- ✅ Mind map generation
- ✅ Report generation

**API Keys Required:**
- 🔴 **OpenAI** (for structured tasks)
- 🔴 **Gemini** (for content-heavy tasks)
- 🔴 **Pinecone** (for source context)

---

## 📊 Priority Order for UI Development

### Start Here (No Keys Needed):
1. ✅ Build static UI components
2. ✅ Implement layouts and styling
3. ✅ Create mock data for UI testing
4. ✅ Set up routing and navigation

### Then Add (For Interactive Features):

**Minimum for Basic Functionality:**
1. 🔴 **Clerk** - Enable authentication
2. 🔴 **Pinecone** - Enable uploads and chat
3. 🔴 **OpenAI** - Enable embeddings
4. 🔴 **Gemini** - Enable chat responses
5. 🟡 **Storage** - Enable file storage

**Full Feature Set:**
- All keys above

---

## 💰 Cost Summary

### Free Tier Available:
- ✅ Clerk (10K users/month)
- ✅ Pinecone (100K vectors)
- ✅ Gemini (15 requests/minute)
- ✅ Supabase Storage (1GB)
- ✅ Database (Supabase - 500MB)

### Paid (But Cheap):
- OpenAI: $5 free credit, then ~$0.10 per 1M tokens
- AWS S3: Free tier (5GB), then pay-as-you-go

### Total Development Cost:
**$0 - $5** (just OpenAI's $5 credit, everything else free)

---

## 🚀 Recommended Development Path

### Week 1: Static UI (No Keys)
1. Build all UI components
2. Implement layouts
3. Add styling and animations
4. Create mock data

### Week 2: Add Authentication (Clerk)
1. Get Clerk keys
2. Enable authentication
3. Test sign-in/sign-up flows

### Week 3: Add Core Features (Pinecone, OpenAI, Gemini)
1. Get remaining API keys
2. Test file uploads
3. Test chat functionality
4. Test studio features

---

## ✅ Current Status

**What's Working Now:**
- ✅ Backend server (running)
- ✅ Frontend server (running)
- ✅ Database (connected)
- ✅ Static UI (can be built)

**What Needs Keys:**
- ⏳ Clerk (for authentication)
- ⏳ Pinecone (for uploads/chat)
- ⏳ OpenAI (for embeddings/studio)
- ⏳ Gemini (for chat)
- ⏳ Storage (for file uploads)

---

## 🎯 Bottom Line

**For Building Frontend UI:**
- **Static components:** ✅ No keys needed
- **Interactive features:** 🔴 Keys required (see above)

**Start building UI now, add keys as you need features!**


