from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name, between 2 and 100 characters",
    )
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters long"
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters long"
    )


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
