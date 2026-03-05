"""
RAG Tools for LangChain Integration
All tools are implemented as proper async LangChain @tool functions.
"""
from typing import Dict, List

from langchain_core.tools import tool


@tool
async def extract_pdf_text(file_path: str) -> Dict:
    """Extract all text from a PDF file at *file_path*."""
    from .chunking_agent import ChunkingAgent
    agent = ChunkingAgent()
    text = await agent.extract_text_from_pdf(file_path)
    return {"text": text, "length": len(text), "status": "success"}


@tool
async def chunk_document(text: str, metadata: dict = None) -> Dict:
    """
    Split *text* into semantically coherent chunks.
    *metadata* dict is attached to every resulting chunk.
    """
    from .chunking_agent import ChunkingAgent
    agent = ChunkingAgent()
    docs = await agent.chunk(text, metadata or {})
    return {
        "chunks": [d.page_content for d in docs],
        "count": len(docs),
        "status": "success",
    }


@tool
async def embed_and_index(
    chunks: List[str],
    library_item_id: int,
    metadata: dict = None,
) -> Dict:
    """
    Embed *chunks* and upsert them to Qdrant as points for *library_item_id*.
    *metadata* is merged into every chunk's payload.
    """
    from langchain_core.documents import Document
    from .chunking_agent import IndexingAgent

    agent = IndexingAgent()
    docs = [
        Document(
            page_content=c,
            metadata={**(metadata or {}), "chunk_index": i, "total_chunks": len(chunks)},
        )
        for i, c in enumerate(chunks)
    ]
    return await agent.process(docs, library_item_id)


@tool
async def fetch_youtube_transcript(url: str) -> Dict:
    """Fetch the transcript for a YouTube video at *url*."""
    from .youtube_agent import get_youtube_transcript
    return await get_youtube_transcript(url)


@tool
async def search_user_documents(query: str, user_id: int, limit: int = 5) -> Dict:
    """
    Search the user's library in Qdrant for chunks semantically relevant to *query*.
    Only documents belonging to *user_id* are returned.
    """
    from .rag_orchestrator import RAGOrchestrator
    orchestrator = RAGOrchestrator()
    return await orchestrator.search_documents(query, user_id, limit=limit)


# Export all tools
__all__ = [
    'extract_pdf_text',
    'chunk_document',
    'embed_and_index',
    'fetch_youtube_transcript',
    'search_user_documents',
]
