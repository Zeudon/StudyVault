from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    library_items = relationship("LibraryItem", back_populates="user", cascade="all, delete-orphan")


class LibraryItem(Base):
    __tablename__ = "library_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'pdf' or 'youtube'
    url = Column(String, nullable=False)  # file path or YouTube URL
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="library_items")
