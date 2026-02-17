from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from dotenv import load_dotenv

from database import engine, Base, get_db
from models import User, LibraryItem
from schemas import UserCreate, UserLogin, UserResponse, Token, LibraryItemResponse, ChatRequest, ChatResponse
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from vector_service import VectorService

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
vector_service = VectorService()

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
        
        # Index in vector database
        try:
            vector_service.index_pdf(file_path, current_user.id, title)
        except Exception as e:
            print(f"Error indexing PDF: {e}")
    
    elif type == "youtube":
        if not url:
            raise HTTPException(status_code=400, detail="YouTube URL is required")
        file_path = url
        
        # Index YouTube video
        try:
            vector_service.index_youtube(url, current_user.id, title)
        except Exception as e:
            print(f"Error indexing YouTube video: {e}")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")
    
    # Create library item
    new_item = LibraryItem(
        user_id=current_user.id,
        title=title,
        type=type,
        url=file_path,
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
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
    
    # Delete from vector database
    try:
        vector_service.delete_document(item.id)
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
    
    # TODO: Implement RAG system query
    # This will:
    # 1. Search vector database for relevant documents from user's library
    # 2. Retrieve relevant chunks/context
    # 3. Send to LLM with context for answer generation
    # 4. Return formatted response with sources
    
    # Placeholder response for now
    try:
        # Future: response = vector_service.query_rag(user_query, user_id)
        response_text = f"RAG system received your query: '{user_query}'. LLM integration coming soon!"
        sources = []
        
        return ChatResponse(
            response=response_text,
            sources=sources
        )
    except Exception as e:
        print(f"Error in RAG query: {e}")
        raise HTTPException(status_code=500, detail="Error processing your query")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
