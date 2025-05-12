from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class SocialAccountBase(BaseModel):
    platform_name: Optional[str] = None
    brand_id: UUID
    account_name: str
    account_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    account_type: Optional[str] = None
    status: Optional[str] = None
    user_id: UUID
    account_picture: Optional[str] = None


class SocialAccountCreate(SocialAccountBase):
    pass


class SocialAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    account_type: Optional[str] = None
    status: Optional[str] = None


class SocialAccount(SocialAccountBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
