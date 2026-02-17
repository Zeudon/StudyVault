# Quick Start: Testing Your RAG System

## Prerequisites Checklist

- [ ] PostgreSQL running (port 5432)
- [ ] Qdrant running (port 6333)
- [ ] OpenAI API key obtained
- [ ] Database migrated with new columns

## Step 1: Environment Setup

Create or update your `.env` file in `backend/` folder:

```env
# Database
DATABASE_URL=postgresql://studyvault_user:studyvault_pass@localhost:5432/studyvault

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Vector Database
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=studyvault_documents

# OpenAI (REQUIRED!)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Upload Directory
UPLOAD_DIR=./uploads
```

## Step 2: Database Migration

Run this SQL to add new columns:

```sql
-- Connect to your database
psql -U studyvault_user -d studyvault

-- Add new columns
ALTER TABLE library_items ADD COLUMN IF NOT EXISTS qdrant_ids JSON;
ALTER TABLE library_items ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;
```

Or recreate the database (development only - will delete all data!):

```bash
psql -U studyvault_user -d postgres
DROP DATABASE IF EXISTS studyvault;
CREATE DATABASE studyvault;
GRANT ALL PRIVILEGES ON DATABASE studyvault TO studyvault_user;
\q
```

## Step 3: Install Dependencies

```bash
cd code/webapp/backend
pip install -r requirements.txt
```

## Step 4: Start Services

### Option A: Local Development

```bash
# Terminal 1: Start PostgreSQL (if not running as service)
# Usually runs as a system service

# Terminal 2: Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Terminal 3: Start Backend
cd code/webapp/backend
python main.py

# Terminal 4: Start Frontend
cd code/webapp/frontend
npm run dev
```

### Option B: Docker (Full Stack)

```bash
# Make sure .env.docker has OPENAI_API_KEY
docker-compose up
```

## Step 5: Test the System

### 5.1 Register a User

1. Open http://localhost:3000
2. Click "Sign Up"
3. Create account: username `testuser`, password `test123`
4. Log in

### 5.2 Upload a PDF

1. Click "Add Content"
2. Select "PDF"
3. Choose a PDF file
4. Enter title: "Test Document"
5. Click "Upload"
6. **Watch the console/logs**: Should see chunking progress

Expected log output:
```
Processing PDF: /path/to/file.pdf
Successfully chunked document into X chunks
Embedded 1 batch(es) of X total chunks
Successfully indexed X chunks to Qdrant
```

### 5.3 Upload a YouTube Video

1. Click "Add Content"
2. Select "YouTube"
3. Enter URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
4. Enter title: "Test Video"
5. Click "Upload"
6. **Watch the console/logs**: Should see transcript extraction

Expected log output:
```
Successfully fetched YouTube transcript: X words
Processing YouTube transcript for Test Video
Successfully chunked document into X chunks
Embedded 1 batch(es) of X total chunks
Successfully indexed X chunks to Qdrant
```

### 5.4 Query the System

1. Go to Library page
2. Enter a question related to your uploaded content
3. Click "Send" or press Enter
4. **Expected result**:
   - Top 5 relevant chunks displayed
   - Source documents listed with relevance scores
   - Context from your documents

Example query:
```
"What is the main topic discussed in the document?"
```

Expected response format:
```
Based on the following information from your library:

[Source 1]
[relevant chunk text]

[Source 2]
[relevant chunk text]

...

Note: LLM integration coming soon! The system found 5 relevant chunks from 2 document(s) in your library.

Sources:
- Test Document (pdf) - Relevance: 0.876
- Test Video (youtube) - Relevance: 0.743
```

## Step 6: Verify in Qdrant Dashboard

1. Open http://localhost:6333/dashboard
2. Click on "Collections"
3. You should see `studyvault_documents` collection
4. Check:
   - Vector count matches total chunks uploaded
   - Each vector has proper payload with metadata

## Troubleshooting

### Issue: "OpenAI API key not found"
**Solution**: Add `OPENAI_API_KEY` to `.env` file and restart backend

### Issue: "Collection does not exist"
**Solution**: The collection is auto-created on first upload. Check Qdrant is running on port 6333

### Issue: "column qdrant_ids does not exist"
**Solution**: Run the database migration SQL from Step 2

### Issue: "No transcript found for video"
**Solution**: Video must have captions enabled. Try a different video

### Issue: "Error embedding chunks"
**Solution**: 
- Check OpenAI API key is valid
- Check internet connection
- Check OpenAI API quota/billing

### Issue: Backend won't start - "ModuleNotFoundError: No module named 'rag'"
**Solution**: The backend is adding the parent directory to sys.path. Verify:
```python
# In main.py, these lines should exist:
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rag import RAGOrchestrator
```

## Testing with cURL

### Upload PDF
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=Test Document" \
  -F "description=Testing RAG system"
```

### Upload YouTube
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "url=https://www.youtube.com/watch?v=VIDEO_ID" \
  -F "title=Test Video" \
  -F "description=Testing YouTube agent"
```

### Query RAG System
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_query": "What is the main topic?"}'
```

### Get JWT Token
```bash
# First login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'

# Copy the "access_token" from response
```

## Success Criteria

✅ **System is working correctly if:**

1. PDFs upload without errors
2. Console shows "Successfully indexed X chunks to Qdrant"
3. Database shows `qdrant_ids` and `chunk_count` populated
4. YouTube videos extract transcripts successfully
5. Qdrant dashboard shows vectors in `studyvault_documents` collection
6. Query returns relevant chunks with proper sources
7. Different users only see their own documents in results

## Next Steps After Testing

Once the system is working:

1. **Add LLM Generation**: Integrate GPT-4 in the chat endpoint
2. **Tune Chunking**: Adjust CHUNK_SIZE in config.py based on your needs
3. **Add More File Types**: Extend to support .docx, .txt, .md, etc.
4. **Improve UI**: Show chunk preview, highlight relevant sections
5. **Add Filters**: Filter by document type, date, tags
6. **Monitor Usage**: Track which documents are queried most

## Performance Tips

- **Batch Uploads**: Upload multiple documents at once (future feature)
- **Adjust Chunk Size**: Smaller chunks = more precise, larger = more context
- **Use Filters**: Adding metadata filters speeds up search
- **Cache Embeddings**: Consider caching common queries
- **Monitor Costs**: OpenAI embeddings cost $0.00002 per 1K tokens

---

**Ready to test!** Start with Step 1 and work through each step. Check off the prerequisites before beginning.
