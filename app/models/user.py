from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    fullname: Optional[str] = None


class UserCreate(UserBase):
    password: str
    

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserVerify(BaseModel):
    email: EmailStr
    verification_code: str


class User(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    role: str = 'user'
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    token_id: str


class GoogleUser(BaseModel):
    email: EmailStr
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    locale: Optional[str] = None
