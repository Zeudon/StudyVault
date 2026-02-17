"""
Chunking and Indexing Agent
Handles document extraction, chunking, embedding, and indexing to Qdrant
"""
import asyncio
import logging
from typing import List, Dict, Optional
from uuid import uuid4
import time

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PointIdsList,
    Filter,
    FieldCondition,
    MatchValue
)

from .config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    MAX_RETRIES,
    RETRY_DELAY,
    SEPARATORS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkingIndexingAgent:
    """Agent for chunking documents and indexing them into Qdrant"""
    
    def __init__(self):
        """Initialize the agent with Qdrant client and embeddings"""
        # Initialize async Qdrant client
        if QDRANT_API_KEY:
            self.qdrant_client = AsyncQdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY
            )
        else:
            self.qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=SEPARATORS,
            length_function=len,
        )
        
        self.collection_name = COLLECTION_NAME
    
    async def ensure_collection(self):
        """Ensure Qdrant collection exists"""
        try:
            collections = await self.qdrant_client.get_collections()
            collection_exists = any(
                c.name == self.collection_name for c in collections.collections
            )
            
            if not collection_exists:
                await self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            # Run PDF loading in thread pool (PyPDFLoader is synchronous)
            loop = asyncio.get_event_loop()
            loader = PyPDFLoader(file_path)
            documents = await loop.run_in_executor(None, loader.load)
            
            # Combine all pages
            text = "\n\n".join([doc.page_content for doc in documents])
            logger.info(f"Extracted {len(text)} characters from PDF: {file_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            raise
    
    async def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        try:
            chunks = self.text_splitter.split_text(text)
            logger.info(f"Split text into {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            raise
    
    async def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for chunks with retry logic
        
        Args:
            chunks: List of text chunks
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i, chunk in enumerate(chunks):
            retries = 0
            while retries < MAX_RETRIES:
                try:
                    # Embed single chunk
                    embedding = await self.embeddings.aembed_query(chunk)
                    embeddings.append(embedding)
                    logger.debug(f"Embedded chunk {i+1}/{len(chunks)}")
                    break
                except Exception as e:
                    retries += 1
                    logger.warning(
                        f"Error embedding chunk {i+1} (attempt {retries}/{MAX_RETRIES}): {e}"
                    )
                    if retries < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * retries)
                    else:
                        logger.error(f"Failed to embed chunk {i+1} after {MAX_RETRIES} attempts")
                        raise
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    async def index_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        user_id: int,
        user_name: str,
        title: str,
        source_type: str,
        source_url: str,
        library_item_id: int
    ) -> List[str]:
        """
        Index chunks into Qdrant
        
        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors
            user_id: User ID
            user_name: User's full name
            title: Document title
            source_type: 'pdf' or 'youtube'
            source_url: File path or YouTube URL
            library_item_id: Library item ID from PostgreSQL
            
        Returns:
            List of Qdrant point IDs
        """
        try:
            await self.ensure_collection()
            
            points = []
            point_ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid4())
                point_ids.append(point_id)
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "user_id": user_id,
                        "user_name": user_name,
                        "title": title,
                        "source_type": source_type,
                        "source_url": source_url,
                        "library_item_id": library_item_id,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "timestamp": time.time()
                    }
                )
                points.append(point)
            
            # Upsert all points to Qdrant
            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            
            logger.info(f"Indexed {len(points)} chunks for {title} (library_item_id: {library_item_id})")
            return point_ids
            
        except Exception as e:
            logger.error(f"Error indexing chunks: {e}")
            raise
    
    async def delete_by_library_item_id(self, library_item_id: int):
        """
        Delete all chunks associated with a library item
        
        Args:
            library_item_id: Library item ID
        """
        try:
            # Delete points with matching library_item_id
            await self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="library_item_id",
                            match=MatchValue(value=library_item_id)
                        )
                    ]
                ),
                wait=True
            )
            logger.info(f"Deleted chunks for library_item_id: {library_item_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks for library_item_id {library_item_id}: {e}")
            raise
    
    async def process_pdf(
        self,
        file_path: str,
        user_id: int,
        user_name: str,
        title: str,
        library_item_id: int
    ) -> Dict[str, any]:
        """
        Complete PDF processing pipeline
        
        Args:
            file_path: Path to PDF file
            user_id: User ID
            user_name: User's full name
            title: Document title
            library_item_id: Library item ID
            
        Returns:
            Dictionary with point_ids and statistics
        """
        try:
            # Extract text
            text = await self.extract_text_from_pdf(file_path)
            
            # Chunk text
            chunks = await self.chunk_text(text)
            
            # Generate embeddings
            embeddings = await self.embed_chunks(chunks)
            
            # Index chunks
            point_ids = await self.index_chunks(
                chunks=chunks,
                embeddings=embeddings,
                user_id=user_id,
                user_name=user_name,
                title=title,
                source_type="pdf",
                source_url=file_path,
                library_item_id=library_item_id
            )
            
            return {
                "status": "success",
                "point_ids": point_ids,
                "chunk_count": len(chunks),
                "character_count": len(text)
            }
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process_youtube_transcript(
        self,
        transcript: str,
        user_id: int,
        user_name: str,
        title: str,
        youtube_url: str,
        library_item_id: int
    ) -> Dict[str, any]:
        """
        Complete YouTube transcript processing pipeline
        
        Args:
            transcript: YouTube transcript text
            user_id: User ID
            user_name: User's full name
            title: Video title
            youtube_url: YouTube URL
            library_item_id: Library item ID
            
        Returns:
            Dictionary with point_ids and statistics
        """
        try:
            # Chunk transcript
            chunks = await self.chunk_text(transcript)
            
            # Generate embeddings
            embeddings = await self.embed_chunks(chunks)
            
            # Index chunks
            point_ids = await self.index_chunks(
                chunks=chunks,
                embeddings=embeddings,
                user_id=user_id,
                user_name=user_name,
                title=title,
                source_type="youtube",
                source_url=youtube_url,
                library_item_id=library_item_id
            )
            
            return {
                "status": "success",
                "point_ids": point_ids,
                "chunk_count": len(chunks),
                "character_count": len(transcript)
            }
        except Exception as e:
            logger.error(f"Error processing YouTube transcript for {youtube_url}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
