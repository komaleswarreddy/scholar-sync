# Setup Guide

## Prerequisites

- **Node.js** 18+ and **pnpm** 8+
- **Python** 3.11+
- **PostgreSQL** 15+ (or use Supabase)
- **Pinecone** account
- **AWS S3** bucket (or Supabase Storage)
- **Clerk** account for authentication
- **OpenAI** API key
- **Google Gemini** API key

## Step 1: Install Dependencies

```bash
# Install root dependencies
pnpm install

# Install Python dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Environment Variables

### Backend (.env)

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scholarsync
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Vector Database
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=scholarsync-vectors

# LLM APIs
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key

# Storage
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=scholarsync-storage

# Authentication
CLERK_SECRET_KEY=your-clerk-secret-key

# App
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend (.env.local)

Create `apps/web/.env.local`:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
```

## Step 3: Database Setup

### Option A: Using Supabase

1. Create a Supabase project
2. Run the SQL schema (create migration):

```sql
-- Create tenants table
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subdomain TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create sources table
CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  s3_key TEXT NOT NULL,
  type TEXT DEFAULT 'pdf',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create chats table
CREATE TABLE chats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create messages table
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create notes table
CREATE TABLE notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  source_ref_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ
);

-- Create indexes
CREATE INDEX idx_sources_tenant_id ON sources(tenant_id);
CREATE INDEX idx_chats_tenant_id ON chats(tenant_id);
CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_notes_tenant_id ON notes(tenant_id);
CREATE INDEX idx_notes_user_id ON notes(user_id);

-- Insert a test tenant (for development)
INSERT INTO tenants (subdomain, name) VALUES ('default', 'Default School');
```

### Option B: Using Local PostgreSQL

1. Create database: `createdb scholarsync`
2. Run the SQL schema above

## Step 4: Pinecone Setup

1. Create a Pinecone account
2. Create a serverless index:
   - Name: `scholarsync-vectors`
   - Dimensions: `1536` (for OpenAI text-embedding-3-small)
   - Metric: `cosine`
3. Get your API key

## Step 5: AWS S3 Setup

1. Create an S3 bucket
2. Configure CORS (if needed)
3. Create IAM user with S3 access
4. Get access key and secret

## Step 6: Clerk Setup

1. Create a Clerk account
2. Create a new application
3. Get your publishable key and secret key
4. Configure allowed origins (localhost:3000 for dev)

## Step 7: Run the Application

### Start Backend

```bash
cd backend
source venv/bin/activate
python run.py
# Or: uvicorn app.main:app --reload
```

Backend will run on `http://localhost:8000`

### Start Frontend

```bash
# From root
pnpm --filter @scholarsync/web dev

# Or from apps/web
cd apps/web
pnpm dev
```

Frontend will run on `http://localhost:3000`

## Step 8: Verify Setup

1. **Backend Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **API Docs:**
   Visit `http://localhost:8000/api/docs`

3. **Frontend:**
   Visit `http://localhost:3000` and sign in

## Troubleshooting

### Backend Issues

- **Database connection error**: Check DATABASE_URL and ensure PostgreSQL is running
- **Pinecone error**: Verify API key and index name
- **Import errors**: Ensure you're in the virtual environment and dependencies are installed

### Frontend Issues

- **Build errors**: Run `pnpm install` from root
- **Clerk errors**: Verify environment variables
- **API connection**: Check NEXT_PUBLIC_API_URL matches backend URL

## Next Steps

1. Create your first tenant in the database
2. Upload a test PDF source
3. Start chatting with your sources!


