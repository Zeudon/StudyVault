# Multi-Agent RAG System for StudyVault

This folder contains the multi-agent RAG system implementation using LangChain.

## Architecture

### Agents
1. **Chunking & Indexing Agent** (`chunking_agent.py`)
   - Extracts and chunks text from PDFs
   - Generates embeddings
   - Stores in Qdrant with metadata
   - Handles retries and error logging

2. **YouTube Transcript Agent** (`youtube_agent.py`)
   - Fetches transcripts from YouTube videos
   - Uses youtube-transcript-api
   - Returns cleaned transcript text

3. **RAG Orchestrator** (`rag_orchestrator.py`)
   - Coordinates between agents
   - Manages workflow for PDF/YouTube uploads
   - Handles database updates

## Data Flow

### PDF Upload Flow
1. User uploads PDF → Backend receives file
2. Chunking Agent extracts & chunks text
3. Chunking Agent generates embeddings
4. Chunking Agent stores in Qdrant (returns point IDs)
5. Backend stores metadata in PostgreSQL with Qdrant IDs

### YouTube Upload Flow
1. User provides YouTube URL → Backend receives URL
2. YouTube Agent fetches transcript
3. Chunking Agent chunks transcript
4. Chunking Agent generates embeddings & stores in Qdrant
5. Backend stores metadata in PostgreSQL with Qdrant IDs

## Components

- `chunking_agent.py` - Document processing and embedding
- `youtube_agent.py` - YouTube transcript extraction
- `rag_orchestrator.py` - Main orchestration logic
- `config.py` - Configuration and settings
- `tools.py` - LangChain tools for agents
