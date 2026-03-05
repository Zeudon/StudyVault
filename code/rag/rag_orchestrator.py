"""
RAG Orchestrator
================
Wires all agents together using LangChain LCEL (LangChain Expression Language).

Ingestion pipelines
-------------------
  pdf_ingestion_chain   : PDF file → ChunkingAgent → IndexingAgent → result dict
  youtube_ingestion_chain: YouTube URL → YouTubeAgent → ChunkingAgent → IndexingAgent → result dict

Query pipeline
--------------
  query_chain           : (user_query, user_id) → RetrievalAgent → PromptAndResponseAgent → ChatResponse
"""
import logging
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableLambda

from .chunking_agent import ChunkingAgent, ChunkingIndexingAgent, IndexingAgent
from .config import (
    COLLECTION_NAME,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    OPENAI_CHAT_MODEL,
    RETRIEVAL_TOP_K,
)
from .youtube_agent import YouTubeAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM initialisation (Gemini primary, OpenAI fallback)
# ---------------------------------------------------------------------------

def _build_llm():
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=0.3,
            )
        except ImportError:
            logger.warning("langchain-google-genai not installed — falling back to OpenAI")

    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=OPENAI_CHAT_MODEL, temperature=0.3)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are StudyVault, an AI assistant that answers questions based exclusively on the "
    "user's uploaded study materials. Cite the source title and type for every claim you make. "
    "If the answer cannot be found in the provided context, say: "
    "\"I don't have enough information in your library to answer this question.\""
)


def _build_prompt(user_query: str, chunks: List[Dict]) -> str:
    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"[Source: {chunk.get('title', 'Unknown')} "
            f"({chunk.get('source_type', '?')}), "
            f"chunk {chunk.get('chunk_index', '?')}]\n"
            f"{chunk.get('text', '')}"
        )
    context = "\n\n".join(context_parts)
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context}\n\n"
        f"User question: {user_query}"
    )


# ---------------------------------------------------------------------------
# RAGOrchestrator
# ---------------------------------------------------------------------------

class RAGOrchestrator:
    """Main orchestrator — exposes ingestion and query pipelines."""

    def __init__(self):
        self.youtube_agent = YouTubeAgent()
        self.chunking_agent_cls = ChunkingAgent()
        self.indexing_agent = IndexingAgent()
        # Kept for search_documents (uses qdrant_client / embeddings directly)
        self._legacy_agent = ChunkingIndexingAgent()
        self._llm = None  # lazy-initialised on first use

    @property
    def llm(self):
        if self._llm is None:
            self._llm = _build_llm()
        return self._llm

    # ------------------------------------------------------------------
    # LCEL ingestion chains
    # ------------------------------------------------------------------

    def _make_pdf_chain(self):
        """Return an LCEL chain: input_dict → result_dict."""

        async def _extract(inp: Dict) -> Dict:
            inp["text"] = await self.chunking_agent_cls.extract_text_from_pdf(inp["file_path"])
            return inp

        async def _chunk(inp: Dict) -> Dict:
            metadata = {
                "user_id": inp["user_id"],
                "user_name": inp["user_name"],
                "title": inp["title"],
                "source_type": "pdf",
                "source_url": inp["file_path"],
                "library_item_id": inp["library_item_id"],
            }
            inp["docs"] = await self.chunking_agent_cls.chunk(inp["text"], metadata)
            return inp

        async def _index(inp: Dict) -> Dict:
            result = await self.indexing_agent.process(
                inp["docs"], inp["library_item_id"], db=inp.get("db")
            )
            result["character_count"] = len(inp["text"])
            return result

        return (
            RunnableLambda(_extract)
            | RunnableLambda(_chunk)
            | RunnableLambda(_index)
        )

    def _make_youtube_chain(self):
        """Return an LCEL chain: input_dict → result_dict."""

        async def _transcript(inp: Dict) -> Dict:
            inp["text"] = await self.youtube_agent.get_transcript(inp["youtube_url"])
            return inp

        async def _chunk(inp: Dict) -> Dict:
            metadata = {
                "user_id": inp["user_id"],
                "user_name": inp["user_name"],
                "title": inp["title"],
                "source_type": "youtube",
                "source_url": inp["youtube_url"],
                "library_item_id": inp["library_item_id"],
            }
            inp["docs"] = await self.chunking_agent_cls.chunk(inp["text"], metadata)
            return inp

        async def _index(inp: Dict) -> Dict:
            result = await self.indexing_agent.process(
                inp["docs"], inp["library_item_id"], db=inp.get("db")
            )
            result["character_count"] = len(inp["text"])
            return result

        return (
            RunnableLambda(_transcript)
            | RunnableLambda(_chunk)
            | RunnableLambda(_index)
        )

    # ------------------------------------------------------------------
    # Public ingestion API
    # ------------------------------------------------------------------

    async def process_pdf_upload(
        self,
        file_path: str,
        user_id: int,
        user_name: str,
        title: str,
        library_item_id: int,
        db=None,
    ) -> Dict:
        logger.info("Processing PDF upload: %s for user %d", title, user_id)
        try:
            chain = self._make_pdf_chain()
            result = await chain.ainvoke({
                "file_path": file_path,
                "user_id": user_id,
                "user_name": user_name,
                "title": title,
                "library_item_id": library_item_id,
                "db": db,
            })
            logger.info("PDF processed: %s chunks", result.get("chunk_count"))
            return result
        except Exception as exc:
            logger.error("process_pdf_upload error: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def process_youtube_upload(
        self,
        youtube_url: str,
        user_id: int,
        user_name: str,
        title: str,
        library_item_id: int,
        db=None,
    ) -> Dict:
        logger.info("Processing YouTube upload: %s for user %d", title, user_id)
        try:
            chain = self._make_youtube_chain()
            result = await chain.ainvoke({
                "youtube_url": youtube_url,
                "user_id": user_id,
                "user_name": user_name,
                "title": title,
                "library_item_id": library_item_id,
                "db": db,
            })
            logger.info("YouTube processed: %s chunks", result.get("chunk_count"))
            return result
        except Exception as exc:
            logger.error("process_youtube_upload error: %s", exc)
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    async def delete_document(self, library_item_id: int) -> Dict:
        logger.info("Deleting document chunks for library_item_id=%d", library_item_id)
        try:
            await self.indexing_agent.delete_by_library_item_id(library_item_id)
            return {"status": "success"}
        except Exception as exc:
            logger.error("delete_document error: %s", exc)
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # RetrievalAgent: search Qdrant filtered by user_id
    # ------------------------------------------------------------------

    async def search_documents(
        self,
        query: str,
        user_id: int,
        limit: int = RETRIEVAL_TOP_K,
    ) -> Dict:
        """
        Return the top-*limit* most relevant chunks for *user_id*.
        Result shape: {"status", "results": [...], "count"}
        Each result has: text, title, source_type, source_url,
                         library_item_id, chunk_index, score
        """
        logger.info("Searching documents for user %d: '%s'", user_id, query)
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_vec = await self._legacy_agent.embeddings.aembed_query(query)
            response = await self._legacy_agent.qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vec,
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=limit,
                with_payload=True,
            )
            hits = response.points
            results = [
                {
                    "text": h.payload.get("text"),
                    "title": h.payload.get("title"),
                    "source_type": h.payload.get("source_type"),
                    "source_url": h.payload.get("source_url"),
                    "library_item_id": h.payload.get("library_item_id"),
                    "chunk_index": h.payload.get("chunk_index"),
                    "score": h.score,
                }
                for h in hits
            ]
            logger.info("Found %d relevant chunks", len(results))
            return {"status": "success", "results": results, "count": len(results)}
        except Exception as exc:
            logger.error("search_documents error: %s", exc)
            return {"status": "error", "error": str(exc), "results": []}

    # ------------------------------------------------------------------
    # PromptAndResponseAgent: build prompt + call LLM
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        user_query: str,
        user_id: int,
        db=None,
    ) -> Dict[str, Any]:
        """
        Full query pipeline:
          1. RetrievalAgent — search user-scoped Qdrant
          2. PromptAndResponseAgent — build prompt, call LLM, return response + sources
        """
        # Step 1 — retrieve
        search_result = await self.search_documents(user_query, user_id)
        chunks: List[Dict] = search_result.get("results", [])

        if not chunks:
            return {
                "response": (
                    "I couldn't find any relevant information in your library to answer "
                    "this question. Try uploading some documents first!"
                ),
                "sources": [],
            }

        # Step 2 — build prompt
        prompt_text = _build_prompt(user_query, chunks)

        # Step 3 — call LLM
        try:
            from langchain_core.messages import HumanMessage
            ai_msg = await self.llm.ainvoke([HumanMessage(content=prompt_text)])
            response_text = ai_msg.content
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            response_text = (
                "I encountered an error generating a response. "
                "Please check your API key configuration."
            )

        # Step 4 — deduplicate sources
        sources: List[Dict] = []
        seen: set = set()
        for chunk in chunks:
            lib_id = chunk.get("library_item_id")
            if lib_id and lib_id not in seen:
                seen.add(lib_id)
                sources.append({
                    "title": chunk.get("title", "Unknown"),
                    "type": chunk.get("source_type", "unknown"),
                    "url": chunk.get("source_url", ""),
                    "relevance_score": round(chunk.get("score", 0.0), 3),
                })

        return {"response": response_text, "sources": sources}
