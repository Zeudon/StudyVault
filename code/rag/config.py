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
CHUNK_SIZE = 400  # tokens
CHUNK_OVERLAP = 40  # tokens
SEPARATORS = ["\n\n", "\n", " ", ""]

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
