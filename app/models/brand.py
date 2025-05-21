from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class BrandBase(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BrandBase):
    name: Optional[str] = None

class Brand(BrandBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        orm_mode = True
