from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, example="aarchi")
    email: EmailStr = Field(..., example="aarchi@example.com")
    password: str = Field(..., min_length=6, example="secret123")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="aarchi@example.com")
    password: str = Field(..., min_length=1, example="secret123")


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
