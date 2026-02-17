"""
RAG Tools for LangChain Integration
"""
from langchain.tools import tool
from typing import Dict
import asyncio


@tool
async def extract_pdf_text(file_path: str) -> Dict:
    """
    Extract text from a PDF file
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Dictionary with extracted text and metadata
    """
    from .chunking_agent import ChunkingIndexingAgent
    
    agent = ChunkingIndexingAgent()
    text = await agent.extract_text_from_pdf(file_path)
    
    return {
        "text": text,
        "length": len(text),
        "status": "success"
    }


@tool
async def chunk_document(text: str, chunk_size: int = 400, chunk_overlap: int = 40) -> Dict:
    """
    Split document into chunks
    
    Args:
        text: Document text
        chunk_size: Size of each chunk in tokens
        chunk_overlap: Overlap between chunks
        
    Returns:
        Dictionary with chunks and metadata
    """
    from .chunking_agent import ChunkingIndexingAgent
    
    agent = ChunkingIndexingAgent()
    chunks = await agent.chunk_text(text)
    
    return {
        "chunks": chunks,
        "count": len(chunks),
        "status": "success"
    }


@tool
async def embed_text(text: str) -> Dict:
    """
    Generate embedding for text
    
    Args:
        text: Text to embed
        
    Returns:
        Dictionary with embedding vector
    """
    from .chunking_agent import ChunkingIndexingAgent
    
    agent = ChunkingIndexingAgent()
    embedding = await agent.embeddings.aembed_query(text)
    
    return {
        "embedding": embedding,
        "dimension": len(embedding),
        "status": "success"
    }


@tool
async def fetch_youtube_transcript(url: str) -> Dict:
    """
    Fetch transcript from YouTube video
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary with transcript text
    """
    from .youtube_agent import get_youtube_transcript
    
    result = await get_youtube_transcript(url)
    return result


# Export all tools
__all__ = [
    'extract_pdf_text',
    'chunk_document',
    'embed_text',
    'fetch_youtube_transcript'
]
