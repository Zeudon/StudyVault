from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LibraryItemResponse(BaseModel):
    id: int
    user_id: int
    title: str
    type: str
    url: str
    created_at: datetime

    class Config:
        from_attributes = True
