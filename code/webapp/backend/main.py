from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import from rag folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database import engine, Base, get_db
from models import User, LibraryItem
from schemas import UserCreate, UserLogin, UserResponse, Token, LibraryItemResponse, ChatRequest, ChatResponse
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from rag import RAGOrchestrator

load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="StudyVault API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
rag_orchestrator = RAGOrchestrator()

# Ensure upload directory exists
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


@app.get("/")
async def root():
    return {"message": "StudyVault API is running"}


@app.post("/api/auth/signup", response_model=dict)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        hashed_password=hashed_password,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": new_user.email})
    
    return {
        "user": {
            "id": new_user.id,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
        },
        "token": access_token,
    }


@app.post("/api/auth/login", response_model=dict)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return token"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        "token": access_token,
    }


@app.get("/api/library", response_model=List[LibraryItemResponse])
async def get_library(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all library items for the current user"""
    items = db.query(LibraryItem).filter(LibraryItem.user_id == current_user.id).all()
    return items


@app.post("/api/library/upload", response_model=LibraryItemResponse)
async def upload_content(
    title: str = Form(...),
    type: str = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload new content (PDF or YouTube link)"""
    file_path = None
    
    if type == "pdf":
        if not file:
            raise HTTPException(status_code=400, detail="PDF file is required")
        
        # Save file
        file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Create library item first to get the ID
        new_item = LibraryItem(
            user_id=current_user.id,
            title=title,
            type=type,
            url=file_path,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        # Index in RAG system using orchestrator
        try:
            user_name = f"{current_user.first_name} {current_user.last_name}"
            result = await rag_orchestrator.process_pdf_upload(
                file_path=file_path,
                user_id=current_user.id,
                user_name=user_name,
                title=title,
                library_item_id=new_item.id
            )
            
            if result["status"] == "success":
                # Update library item with Qdrant IDs
                new_item.qdrant_ids = result["point_ids"]
                new_item.chunk_count = result["chunk_count"]
                db.commit()
                db.refresh(new_item)
            else:
                print(f"Error indexing PDF: {result.get('error')}")
        except Exception as e:
            print(f"Error indexing PDF: {e}")
    
    elif type == "youtube":
        if not url:
            raise HTTPException(status_code=400, detail="YouTube URL is required")
        file_path = url
        
        # Create library item first to get the ID
        new_item = LibraryItem(
            user_id=current_user.id,
            title=title,
            type=type,
            url=file_path,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        # Index YouTube video using orchestrator
        try:
            user_name = f"{current_user.first_name} {current_user.last_name}"
            result = await rag_orchestrator.process_youtube_upload(
                youtube_url=url,
                user_id=current_user.id,
                user_name=user_name,
                title=title,
                library_item_id=new_item.id
            )
            
            if result["status"] == "success":
                # Update library item with Qdrant IDs
                new_item.qdrant_ids = result["point_ids"]
                new_item.chunk_count = result["chunk_count"]
                db.commit()
                db.refresh(new_item)
            else:
                print(f"Error indexing YouTube: {result.get('error')}")
        except Exception as e:
            print(f"Error indexing YouTube video: {e}")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")
    
    return new_item


@app.get("/api/library/{item_id}/download")
async def download_file(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download/view a PDF file"""
    item = db.query(LibraryItem).filter(
        LibraryItem.id == item_id,
        LibraryItem.user_id == current_user.id,
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.type != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF files can be downloaded")
    
    if not os.path.exists(item.url):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Extract filename from path
    filename = os.path.basename(item.url)
    
    return FileResponse(
        path=item.url,
        filename=filename,
        media_type="application/pdf",
    )


@app.delete("/api/library/{item_id}")
async def delete_library_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a library item"""
    item = db.query(LibraryItem).filter(
        LibraryItem.id == item_id,
        LibraryItem.user_id == current_user.id,
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Delete file if it's a PDF
    if item.type == "pdf" and os.path.exists(item.url):
        try:
            os.remove(item.url)
        except Exception as e:
            print(f"Error deleting file: {e}")
    
    # Delete from vector database using RAG orchestrator
    try:
        await rag_orchestrator.delete_document(item.id)
    except Exception as e:
        print(f"Error deleting from vector DB: {e}")
    
    db.delete(item)
    db.commit()
    
    return {"message": "Item deleted successfully"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query the RAG system with user's question"""
    user_query = chat_request.user_query
    user_id = current_user.id
    user_name = current_user.username
    
    try:
        # Search vector database for relevant documents from user's library
        search_results = await rag_orchestrator.search_documents(
            query=user_query,
            user_id=user_id,
            limit=5  # Get top 5 most relevant chunks
        )
        
        if not search_results:
            return ChatResponse(
                response="I couldn't find any relevant information in your library to answer this question. Try uploading some documents first!",
                sources=[]
            )
        
        # Build context from search results
        context_parts = []
        sources = []
        seen_items = set()
        
        for i, result in enumerate(search_results, 1):
            chunk_text = result.get("text", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0)
            
            # Add chunk to context
            context_parts.append(f"[Source {i}]\n{chunk_text}\n")
            
            # Add unique sources
            library_item_id = metadata.get("library_item_id")
            if library_item_id and library_item_id not in seen_items:
                seen_items.add(library_item_id)
                sources.append({
                    "title": metadata.get("title", "Unknown"),
                    "type": metadata.get("source_type", "unknown"),
                    "url": metadata.get("source_url", ""),
                    "relevance_score": round(score, 3)
                })
        
        # Combine context
        context = "\n".join(context_parts)
        
        # TODO: Send to LLM with context for answer generation
        # For now, return the context with a placeholder response
        response_text = f"""Based on the following information from your library:

{context}

**Note:** LLM integration coming soon! The system found {len(search_results)} relevant chunks from {len(sources)} document(s) in your library."""
        
        return ChatResponse(
            response=response_text,
            sources=sources
        )
    except Exception as e:
        print(f"Error in RAG query: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error processing your query")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
