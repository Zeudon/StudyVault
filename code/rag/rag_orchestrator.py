"""
RAG Orchestrator
Coordinates between YouTube Agent and Chunking/Indexing Agent
"""
import logging
from typing import Dict, Optional
from .youtube_agent import YouTubeAgent
from .chunking_agent import ChunkingIndexingAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Main orchestrator for RAG system"""
    
    def __init__(self):
        self.youtube_agent = YouTubeAgent()
        self.chunking_agent = ChunkingIndexingAgent()
    
    async def process_pdf_upload(
        self,
        file_path: str,
        user_id: int,
        user_name: str,
        title: str,
        library_item_id: int
    ) -> Dict:
        """
        Process PDF upload: extract, chunk, embed, and index
        
        Args:
            file_path: Path to PDF file
            user_id: User ID
            user_name: User's full name
            title: Document title
            library_item_id: Library item ID from database
            
        Returns:
            Result dictionary with point_ids and statistics
        """
        logger.info(f"Processing PDF upload: {title} for user {user_id}")
        
        try:
            result = await self.chunking_agent.process_pdf(
                file_path=file_path,
                user_id=user_id,
                user_name=user_name,
                title=title,
                library_item_id=library_item_id
            )
            
            if result["status"] == "success":
                logger.info(
                    f"Successfully processed PDF: {title} "
                    f"({result['chunk_count']} chunks, {result['character_count']} chars)"
                )
            else:
                logger.error(f"Failed to process PDF: {title} - {result.get('error')}")
            
            return result
        except Exception as e:
            logger.error(f"Error in process_pdf_upload: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process_youtube_upload(
        self,
        youtube_url: str,
        user_id: int,
        user_name: str,
        title: str,
        library_item_id: int
    ) -> Dict:
        """
        Process YouTube upload: fetch transcript, chunk, embed, and index
        
        Args:
            youtube_url: YouTube video URL
            user_id: User ID
            user_name: User's full name
            title: Video title
            library_item_id: Library item ID from database
            
        Returns:
            Result dictionary with point_ids and statistics
        """
        logger.info(f"Processing YouTube upload: {title} for user {user_id}")
        
        try:
            # Step 1: Fetch transcript using YouTube agent
            transcript_result = await self.youtube_agent.fetch_transcript_with_fallback(youtube_url)
            
            if not transcript_result:
                error_msg = "Failed to fetch YouTube transcript"
                logger.error(f"{error_msg}: {youtube_url}")
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            logger.info(f"Fetched transcript ({len(transcript_result)} chars) for: {youtube_url}")
            
            # Step 2: Process transcript using chunking agent
            result = await self.chunking_agent.process_youtube_transcript(
                transcript=transcript_result,
                user_id=user_id,
                user_name=user_name,
                title=title,
                youtube_url=youtube_url,
                library_item_id=library_item_id
            )
            
            if result["status"] == "success":
                logger.info(
                    f"Successfully processed YouTube: {title} "
                    f"({result['chunk_count']} chunks, {result['character_count']} chars)"
                )
            else:
                logger.error(f"Failed to process YouTube: {title} - {result.get('error')}")
            
            return result
        except Exception as e:
            logger.error(f"Error in process_youtube_upload: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def delete_document(self, library_item_id: int):
        """
        Delete all chunks for a library item from Qdrant
        
        Args:
            library_item_id: Library item ID
        """
        logger.info(f"Deleting document chunks for library_item_id: {library_item_id}")
        
        try:
            await self.chunking_agent.delete_by_library_item_id(library_item_id)
            logger.info(f"Successfully deleted chunks for library_item_id: {library_item_id}")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def search_documents(
        self,
        query: str,
        user_id: int,
        limit: int = 5
    ) -> Dict:
        """
        Search for relevant documents for a user
        
        Args:
            query: Search query
            user_id: User ID to filter results
            limit: Maximum number of results
            
        Returns:
            Search results with relevant chunks
        """
        logger.info(f"Searching documents for user {user_id}: '{query}'")
        
        try:
            # Generate query embedding
            query_embedding = await self.chunking_agent.embeddings.aembed_query(query)
            
            # Search Qdrant with user filter
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            search_results = await self.chunking_agent.qdrant_client.search(
                collection_name=self.chunking_agent.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                results.append({
                    "text": result.payload.get("text"),
                    "title": result.payload.get("title"),
                    "source_type": result.payload.get("source_type"),
                    "score": result.score,
                    "chunk_index": result.payload.get("chunk_index"),
                })
            
            logger.info(f"Found {len(results)} relevant chunks")
            return {
                "status": "success",
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {
                "status": "error",
                "error": str(e),
                "results": []
            }
