"""
Chunking and Indexing Agents
----------------------------
ChunkingAgent  — extracts PDF text and splits content into semantic chunks.
IndexingAgent  — embeds chunks and persists them to Qdrant; also writes
                 qdrant_ids / chunk_count back to the PostgreSQL LibraryItem.
ChunkingIndexingAgent — backward-compatibility wrapper that composes the two.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    MAX_RETRIES,
    QDRANT_API_KEY,
    QDRANT_URL,
    RETRY_DELAY,
    SEMANTIC_CHUNK_THRESHOLD,
    SEPARATORS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ChunkingAgent
# ---------------------------------------------------------------------------

class ChunkingAgent:
    """
    Splits raw text into semantically coherent LangChain Documents.

    Primary strategy  : SemanticChunker (langchain-experimental).
    Fallback strategy : RecursiveCharacterTextSplitter.
    """

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=SEPARATORS,
            length_function=len,
        )

    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Return all text from a PDF file (runs loader in thread executor)."""
        try:
            loop = asyncio.get_event_loop()
            loader = PyPDFLoader(file_path)
            docs = await loop.run_in_executor(None, loader.load)
            text = "\n\n".join(d.page_content for d in docs)
            logger.info("Extracted %d characters from PDF: %s", len(text), file_path)
            return text
        except Exception as exc:
            logger.error("Error extracting PDF %s: %s", file_path, exc)
            raise

    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Document]:
        """
        Chunk *text* and attach *metadata* to every chunk.
        Uses SemanticChunker for texts > 500 chars, otherwise RecursiveCharacterTextSplitter.
        """
        if len(text) < 500:
            logger.info("Text is short — using recursive splitter directly")
            return self._chunk_recursive(text, metadata)
        try:
            return await self._chunk_semantic(text, metadata)
        except Exception as exc:
            logger.warning("SemanticChunker failed (%s) — falling back to recursive splitter", exc)
            return self._chunk_recursive(text, metadata)

    async def _chunk_semantic(self, text: str, metadata: Dict[str, Any]) -> List[Document]:
        from langchain_experimental.text_splitter import SemanticChunker  # lazy import
        chunker = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=SEMANTIC_CHUNK_THRESHOLD,
        )
        loop = asyncio.get_event_loop()
        raw_docs: List[Document] = await loop.run_in_executor(
            None, chunker.create_documents, [text]
        )
        chunks = [d.page_content for d in raw_docs]
        logger.info("SemanticChunker produced %d chunks", len(chunks))
        return self._build_documents(chunks, metadata)

    def _chunk_recursive(self, text: str, metadata: Dict[str, Any]) -> List[Document]:
        chunks = self._recursive_splitter.split_text(text)
        logger.info("RecursiveCharacterTextSplitter produced %d chunks", len(chunks))
        return self._build_documents(chunks, metadata)

    @staticmethod
    def _build_documents(chunks: List[str], metadata: Dict[str, Any]) -> List[Document]:
        total = len(chunks)
        return [
            Document(
                page_content=chunk,
                metadata={**metadata, "chunk_index": idx, "total_chunks": total},
            )
            for idx, chunk in enumerate(chunks)
        ]


# ---------------------------------------------------------------------------
# IndexingAgent
# ---------------------------------------------------------------------------

class IndexingAgent:
    """
    Embeds LangChain Documents and persists them to Qdrant.
    Optionally writes qdrant_ids / chunk_count back to PostgreSQL.
    """

    def __init__(self):
        if QDRANT_API_KEY:
            self.qdrant_client = AsyncQdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            self.qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.collection_name = COLLECTION_NAME

    async def ensure_collection(self):
        """Create the Qdrant collection + user_id payload index if absent."""
        try:
            info = await self.qdrant_client.get_collections()
            exists = any(c.name == self.collection_name for c in info.collections)
            if not exists:
                await self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION, distance=Distance.COSINE
                    ),
                )
                # Payload index on user_id enables fast per-user filtered search
                await self.qdrant_client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="user_id",
                    field_schema=PayloadSchemaType.INTEGER,
                )
                logger.info("Created Qdrant collection: %s", self.collection_name)
            else:
                logger.info("Qdrant collection already exists: %s", self.collection_name)
        except Exception as exc:
            logger.error("ensure_collection error: %s", exc)
            raise

    async def embed_documents(self, docs: List[Document]) -> List[List[float]]:
        """Embed each document chunk with per-chunk retry logic."""
        result: List[List[float]] = []
        for idx, doc in enumerate(docs):
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    vec = await self.embeddings.aembed_query(doc.page_content)
                    result.append(vec)
                    break
                except Exception as exc:
                    logger.warning(
                        "Embed attempt %d/%d failed for chunk %d: %s",
                        attempt, MAX_RETRIES, idx, exc,
                    )
                    if attempt == MAX_RETRIES:
                        raise
                    await asyncio.sleep(RETRY_DELAY * attempt)
        return result

    async def index_documents(
        self, docs: List[Document], embeddings: List[List[float]]
    ) -> List[str]:
        """Upsert embedded Documents into Qdrant; return list of point UUIDs."""
        await self.ensure_collection()
        points: List[PointStruct] = []
        point_ids: List[str] = []
        now = datetime.now(timezone.utc).isoformat()

        for doc, vec in zip(docs, embeddings):
            pid = str(uuid4())
            point_ids.append(pid)
            payload = {"text": doc.page_content, **doc.metadata, "timestamp": now}
            points.append(PointStruct(id=pid, vector=vec, payload=payload))

        await self.qdrant_client.upsert(
            collection_name=self.collection_name, points=points, wait=True
        )
        logger.info("Upserted %d points to Qdrant", len(points))
        return point_ids

    async def delete_by_library_item_id(self, library_item_id: int):
        """Delete all Qdrant points belonging to a given library item."""
        await self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="library_item_id", match=MatchValue(value=library_item_id)
                    )
                ]
            ),
            wait=True,
        )
        logger.info("Deleted Qdrant points for library_item_id=%d", library_item_id)

    def update_library_item(
        self, db, library_item_id: int, point_ids: List[str], chunk_count: int
    ):
        """Write qdrant_ids and chunk_count back to the LibraryItem PostgreSQL row."""
        try:
            from models import LibraryItem  # noqa: PLC0415 — importable via sys.path set by main.py

            item = db.query(LibraryItem).filter(LibraryItem.id == library_item_id).first()
            if item:
                item.qdrant_ids = point_ids
                item.chunk_count = chunk_count
                db.commit()
                logger.info(
                    "Updated LibraryItem %d: %d chunks, %d Qdrant points",
                    library_item_id, chunk_count, len(point_ids),
                )
        except Exception as exc:
            logger.error("update_library_item error: %s", exc)

    async def process(
        self,
        docs: List[Document],
        library_item_id: int,
        db=None,
    ) -> Dict[str, Any]:
        """Embed and index *docs*; optionally write stats back to PostgreSQL."""
        try:
            embeddings = await self.embed_documents(docs)
            point_ids = await self.index_documents(docs, embeddings)
            if db is not None:
                self.update_library_item(db, library_item_id, point_ids, len(docs))
            return {"status": "success", "point_ids": point_ids, "chunk_count": len(docs)}
        except Exception as exc:
            logger.error("IndexingAgent.process error: %s", exc)
            return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# ChunkingIndexingAgent — backward-compatibility shim
# ---------------------------------------------------------------------------

class ChunkingIndexingAgent:
    """
    Deprecated: prefer using ChunkingAgent + IndexingAgent directly.
    Kept so that any legacy imports continue to work unchanged.
    """

    def __init__(self):
        self._chunker = ChunkingAgent()
        self._indexer = IndexingAgent()
        # Expose sub-clients still referenced by RAGOrchestrator.search_documents
        self.embeddings = self._chunker.embeddings
        self.qdrant_client = self._indexer.qdrant_client
        self.collection_name = COLLECTION_NAME
        self.text_splitter = self._chunker._recursive_splitter

    async def ensure_collection(self):
        return await self._indexer.ensure_collection()

    async def extract_text_from_pdf(self, file_path: str) -> str:
        return await self._chunker.extract_text_from_pdf(file_path)

    async def chunk_text(self, text: str) -> List[str]:
        docs = await self._chunker.chunk(text, {})
        return [d.page_content for d in docs]

    async def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        docs = [Document(page_content=c) for c in chunks]
        return await self._indexer.embed_documents(docs)

    async def index_chunks(
        self,
        chunks: List[str],
        embeddings_list: List[List[float]],
        user_id: int,
        user_name: str,
        title: str,
        source_type: str,
        source_url: str,
        library_item_id: int,
    ) -> List[str]:
        metadata = {
            "user_id": user_id,
            "user_name": user_name,
            "title": title,
            "source_type": source_type,
            "source_url": source_url,
            "library_item_id": library_item_id,
        }
        docs = [
            Document(
                page_content=c,
                metadata={**metadata, "chunk_index": i, "total_chunks": len(chunks)},
            )
            for i, c in enumerate(chunks)
        ]
        return await self._indexer.index_documents(docs, embeddings_list)

    async def delete_by_library_item_id(self, library_item_id: int):
        return await self._indexer.delete_by_library_item_id(library_item_id)

    async def process_pdf(
        self,
        file_path: str,
        user_id: int,
        user_name: str,
        title: str,
        library_item_id: int,
        db=None,
    ) -> Dict[str, Any]:
        try:
            text = await self._chunker.extract_text_from_pdf(file_path)
            metadata = {
                "user_id": user_id,
                "user_name": user_name,
                "title": title,
                "source_type": "pdf",
                "source_url": file_path,
                "library_item_id": library_item_id,
            }
            docs = await self._chunker.chunk(text, metadata)
            result = await self._indexer.process(docs, library_item_id, db=db)
            result["character_count"] = len(text)
            return result
        except Exception as exc:
            logger.error("process_pdf error: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def process_youtube_transcript(
        self,
        transcript: str,
        user_id: int,
        user_name: str,
        title: str,
        youtube_url: str,
        library_item_id: int,
        db=None,
    ) -> Dict[str, Any]:
        try:
            metadata = {
                "user_id": user_id,
                "user_name": user_name,
                "title": title,
                "source_type": "youtube",
                "source_url": youtube_url,
                "library_item_id": library_item_id,
            }
            docs = await self._chunker.chunk(transcript, metadata)
            result = await self._indexer.process(docs, library_item_id, db=db)
            result["character_count"] = len(transcript)
            return result
        except Exception as exc:
            logger.error("process_youtube_transcript error: %s", exc)
            return {"status": "error", "error": str(exc)}
