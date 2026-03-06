# StudyVault

StudyVault is a personal AI study assistant that lets you build a private knowledge library from PDF documents and YouTube videos, then ask natural language questions answered exclusively from your own uploaded material. It uses a multi-agent RAG (Retrieval-Augmented Generation) pipeline to semantically chunk and index content, retrieve the most relevant passages at query time, and generate cited answers via an LLM.

---

## Agents

| Agent | Purpose |
|---|---|
| **YouTubeAgent** | Extracts transcripts from YouTube URLs with a 3-layer fallback: English → any available language → MCP subprocess |
| **ChunkingAgent** | Splits raw text into semantically coherent chunks using `SemanticChunker` (95th-percentile cosine boundaries), falling back to `RecursiveCharacterTextSplitter` |
| **IndexingAgent** | Embeds chunks with OpenAI `text-embedding-3-small` and upserts them as vector points to Qdrant, then writes point IDs and chunk count back to PostgreSQL |
| **RAGOrchestrator** | Wires all agents together via LangChain LCEL chains; handles ingestion pipelines for PDFs and YouTube, filtered vector search, prompt construction, and LLM response generation |

---

## How to Run

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- An OpenAI API key (required for embeddings and LLM fallback)

### Setup

1. Create the backend environment file:
   ```
   code/webapp/backend/.env.docker
   ```
   Minimum required contents:
   ```env
   OPENAI_API_KEY=sk-...
   DATABASE_URL=postgresql://postgres:postgres@db:5432/studyvault
   SECRET_KEY=your-secret-key-here
   # Optional — if omitted, GPT-4o-mini is used instead
   GEMINI_API_KEY=...
   ```

2. Start all services from the `code/` directory:
   ```powershell
   cd code
   docker-compose up --build
   ```

3. Open the app in your browser:
   - **Frontend:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **Qdrant Dashboard:** http://localhost:6333/dashboard

### Stopping
```powershell
docker-compose down
```
Add `-v` to also delete the database and vector store volumes:
```powershell
docker-compose down -v
```
