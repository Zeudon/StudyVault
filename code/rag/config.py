"""
Configuration for RAG System
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "studyvault_documents"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# Chunking Configuration
CHUNK_SIZE = 400  # characters
CHUNK_OVERLAP = 40  # characters
SEPARATORS = ["\n\n", "\n", " ", ""]
SEMANTIC_CHUNK_THRESHOLD = int(os.getenv("SEMANTIC_CHUNK_THRESHOLD", "95"))  # percentile

# Retrieval Configuration
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # 'gemini' or 'openai'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

# YouTube MCP Configuration
YOUTUBE_MCP_URL = os.getenv("YOUTUBE_MCP_URL", "http://localhost:3100")
MIN_TRANSCRIPT_LENGTH = int(os.getenv("MIN_TRANSCRIPT_LENGTH", "200"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
