# Testing Guide - Full Workflow

## Services Started ✅

### Backend Server
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **Status**: Running

### Frontend Server
- **URL**: http://localhost:3000
- **Status**: Running

---

## Testing Workflow

### Step 1: Open the App
1. Open your browser
2. Go to: **http://localhost:3000**
3. You should see the dashboard

### Step 2: Upload a Source (PDF)
1. In the left sidebar, click **"Add sources"**
2. Select a PDF file
3. Wait for upload and processing
4. The file will be:
   - Uploaded to Supabase Storage
   - Text extracted
   - Chunked into pieces
   - Embedded using OpenAI
   - Stored in Pinecone
   - Saved to database

### Step 3: Chat with Your Document
1. Select the uploaded source (checkbox in left sidebar)
2. Go to the chat interface (center panel)
3. Type a question about your document
4. Example questions:
   - "What is this document about?"
   - "Summarize the main points"
   - "What are the key concepts?"
5. Watch the streaming response from Gemini

### Step 4: Generate Studio Content
1. Make sure sources are selected
2. Go to Studio panel (right sidebar, top)
3. Click any tool:
   - **Mind Map**: Visual representation
   - **Reports**: Comprehensive report
   - **Flashcards**: Study cards
   - **Quiz**: Questions and answers
   - **Infographic**: Visual brief
   - **Slide Deck**: Presentation outline

### Step 5: Create Notes
1. Go to Notes panel (right sidebar, bottom)
2. Click the **+** button
3. Enter note content
4. Or save chat responses to notes

---

## API Endpoints to Test

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. List Sources
```bash
curl http://localhost:8000/api/v1/ingest/sources \
  -H "X-Tenant-ID: default-tenant-id"
```

### 3. Upload Source
```bash
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -H "X-Tenant-ID: default-tenant-id" \
  -F "file=@/path/to/your/file.pdf" \
  -F "title=My Document"
```

### 4. Chat (Streaming)
```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default-tenant-id" \
  -H "X-User-ID: dev-user-123" \
  -d '{
    "message": "What is this document about?",
    "history": [],
    "active_source_ids": ["source-id-here"]
  }'
```

### 5. List Notes
```bash
curl http://localhost:8000/api/v1/notes \
  -H "X-Tenant-ID: default-tenant-id" \
  -H "X-User-ID: dev-user-123"
```

### 6. Create Note
```bash
curl -X POST http://localhost:8000/api/v1/notes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default-tenant-id" \
  -H "X-User-ID: dev-user-123" \
  -d '{
    "content": "This is a test note"
  }'
```

---

## Expected Behavior

### Upload Process:
1. ✅ File uploads to Supabase Storage
2. ✅ Text extraction from PDF
3. ✅ Text chunking (1000 chars with 200 overlap)
4. ✅ Embedding generation (OpenAI)
5. ✅ Vector storage (Pinecone)
6. ✅ Metadata saved (Database)

### Chat Process:
1. ✅ User question embedded
2. ✅ Similar chunks retrieved from Pinecone
3. ✅ Context built from chunks
4. ✅ Response generated (Gemini)
5. ✅ Streaming response to frontend
6. ✅ Citations displayed

### Studio Process:
1. ✅ Selected sources retrieved
2. ✅ Context extracted
3. ✅ Content generated (OpenAI/Gemini)
4. ✅ Structured output returned

---

## Troubleshooting

### Backend not starting?
- Check if port 8000 is available
- Check Python virtual environment is activated
- Check all API keys are in `.env`

### Frontend not starting?
- Check if port 3000 is available
- Run `pnpm install` if needed
- Check `NEXT_PUBLIC_API_URL` in `.env.local`

### Upload fails?
- Check Supabase Storage bucket exists
- Check file size limits
- Check OpenAI API quota

### Chat not working?
- Check if sources are uploaded
- Check if vectors are in Pinecone
- Check Gemini API key

### Studio not working?
- Check if sources are selected
- Check OpenAI/Gemini API keys
- Check API quota limits

---

## Monitoring

### Backend Logs:
Check the terminal where backend is running for:
- Request logs
- Error messages
- Processing status

### Frontend Logs:
Check the browser console (F12) for:
- API calls
- Errors
- Network requests

### API Documentation:
Visit http://localhost:8000/api/docs for:
- All available endpoints
- Request/response schemas
- Try out endpoints directly

---

## Next Steps

1. ✅ Upload a test PDF
2. ✅ Ask questions in chat
3. ✅ Generate Studio content
4. ✅ Create and manage notes
5. ✅ Test all features

**Happy Testing! 🚀**


