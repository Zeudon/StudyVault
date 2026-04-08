from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, BackgroundTasks, Query
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

from database import engine, Base, get_db, SessionLocal
from models import User, LibraryItem
from schemas import UserCreate, UserLogin, UserResponse, Token, LibraryItemResponse, ItemStatusResponse, ChatRequest, ChatResponse
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from rag import RAGOrchestrator

load_dotenv()

# Create database tables and apply incremental migrations
Base.metadata.create_all(bind=engine)
from database import run_migrations
run_migrations()

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


async def _run_processing(
    item_id: int,
    content_type: str,
    file_path: str,
    user_id: int,
    user_name: str,
    title: str,
) -> None:
    """Background task: runs the RAG pipeline and updates processing_status in the DB."""
    db = SessionLocal()
    try:
        item = db.query(LibraryItem).filter(LibraryItem.id == item_id).first()
        if not item:
            return
        item.processing_status = "processing"
        db.commit()

        if content_type == "pdf":
            result = await rag_orchestrator.process_pdf_upload(
                file_path=file_path,
                user_id=user_id,
                user_name=user_name,
                title=title,
                library_item_id=item_id,
            )
        else:  # youtube
            result = await rag_orchestrator.process_youtube_upload(
                youtube_url=file_path,
                user_id=user_id,
                user_name=user_name,
                title=title,
                library_item_id=item_id,
            )

        # Re-query to get a fresh object after the long-running pipeline
        item = db.query(LibraryItem).filter(LibraryItem.id == item_id).first()
        if not item:
            return

        if result.get("status") == "success":
            item.qdrant_ids = result["point_ids"]
            item.chunk_count = result["chunk_count"]
            item.processing_status = "completed"
            item.processing_error = None
        else:
            item.processing_status = "failed"
            item.processing_error = result.get("error", "Unknown error during processing")
        db.commit()

    except Exception as exc:
        try:
            db.rollback()
            item = db.query(LibraryItem).filter(LibraryItem.id == item_id).first()
            if item:
                item.processing_status = "failed"
                item.processing_error = str(exc)
                db.commit()
        except Exception:
            pass
        import traceback
        traceback.print_exc()
    finally:
        db.close()


@app.post("/api/library/upload", response_model=LibraryItemResponse, status_code=202)
async def upload_content(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    type: str = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload new content (PDF or YouTube link) — returns 202 immediately, processes in background."""
    if type == "pdf":
        if not file:
            raise HTTPException(status_code=400, detail="PDF file is required")
        file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(await file.read())
    elif type == "youtube":
        if not url:
            raise HTTPException(status_code=400, detail="YouTube URL is required")
        file_path = url
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")

    new_item = LibraryItem(
        user_id=current_user.id,
        title=title,
        type=type,
        url=file_path,
        processing_status="pending",
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    user_name = f"{current_user.first_name} {current_user.last_name}"
    background_tasks.add_task(
        _run_processing,
        item_id=new_item.id,
        content_type=type,
        file_path=file_path,
        user_id=current_user.id,
        user_name=user_name,
        title=title,
    )

    return new_item


@app.get("/api/library/processing-status", response_model=List[ItemStatusResponse])
async def get_processing_status(
    ids: str = Query(..., description="Comma-separated library item IDs to check"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return processing status for a specific set of library items (used for polling)."""
    try:
        item_ids = [int(i.strip()) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item IDs")

    items = db.query(LibraryItem).filter(
        LibraryItem.id.in_(item_ids),
        LibraryItem.user_id == current_user.id,
    ).all()
    return items


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
    """Query the RAG system with the user's question."""
    user_query = chat_request.user_query
    user_id = current_user.id

    try:
        result = await rag_orchestrator.generate_response(
            user_query=user_query,
            user_id=user_id,
            db=db,
        )
        return ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
        )
    except Exception as e:
        print(f"Error in RAG query: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error processing your query")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
