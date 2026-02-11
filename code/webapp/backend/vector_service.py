from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from PyPDF2 import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import os
from typing import List
from dotenv import load_dotenv
import uuid

load_dotenv()


class VectorService:
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        try:
            # Initialize Qdrant client
            if self.qdrant_api_key:
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            else:
                self.client = QdrantClient(url=self.qdrant_url)
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings()
            
            # Text splitter for chunking
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            )
            
            # Collection name
            self.collection_name = "studyvault_documents"
            
            # Create collection if it doesn't exist
            self._ensure_collection()
        except Exception as e:
            print(f"Warning: Could not initialize vector service: {e}")
            self.client = None
    
    def _ensure_collection(self):
        """Ensure the Qdrant collection exists"""
        if not self.client:
            return
            
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
        except Exception as e:
            print(f"Error ensuring collection: {e}")
    
    def index_pdf(self, file_path: str, user_id: int, title: str):
        """Index a PDF file into the vector database"""
        if not self.client:
            return
            
        try:
            # Extract text from PDF
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # Split into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Create embeddings and store
            points = []
            for i, chunk in enumerate(chunks):
                embedding = self.embeddings.embed_query(chunk)
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "user_id": user_id,
                        "title": title,
                        "type": "pdf",
                        "file_path": file_path,
                        "chunk_index": i,
                    },
                )
                points.append(point)
            
            # Upsert to Qdrant
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Indexed {len(chunks)} chunks from PDF: {title}")
        except Exception as e:
            print(f"Error indexing PDF: {e}")
            raise
    
    def index_youtube(self, url: str, user_id: int, title: str):
        """Index a YouTube video transcript into the vector database"""
        if not self.client:
            return
            
        try:
            # Extract video ID from URL
            video_id = url.split("v=")[-1].split("&")[0]
            
            # Get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([t["text"] for t in transcript_list])
            
            # Split into chunks
            chunks = self.text_splitter.split_text(transcript_text)
            
            # Create embeddings and store
            points = []
            for i, chunk in enumerate(chunks):
                embedding = self.embeddings.embed_query(chunk)
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "user_id": user_id,
                        "title": title,
                        "type": "youtube",
                        "url": url,
                        "chunk_index": i,
                    },
                )
                points.append(point)
            
            # Upsert to Qdrant
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Indexed {len(chunks)} chunks from YouTube: {title}")
        except Exception as e:
            print(f"Error indexing YouTube video: {e}")
            raise
    
    def delete_document(self, item_id: int):
        """Delete a document from the vector database"""
        if not self.client:
            return
            
        try:
            # In a production system, you'd want to track point IDs
            # For now, this is a placeholder
            pass
        except Exception as e:
            print(f"Error deleting from vector DB: {e}")
    
    def search(self, query: str, user_id: int, limit: int = 5) -> List[dict]:
        """Search for relevant documents"""
        if not self.client:
            return []
            
        try:
            # Create query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search in Qdrant
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter={
                    "must": [{"key": "user_id", "match": {"value": user_id}}]
                },
            )
            
            return [
                {
                    "text": result.payload["text"],
                    "title": result.payload["title"],
                    "type": result.payload["type"],
                    "score": result.score,
                }
                for result in results
            ]
        except Exception as e:
            print(f"Error searching: {e}")
            return []
