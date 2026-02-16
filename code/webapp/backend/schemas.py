from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password is too long. Maximum 72 bytes allowed.')
        return v


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


class ChatRequest(BaseModel):
    user_query: str


class ChatResponse(BaseModel):
    response: str
    sources: Optional[list] = []
