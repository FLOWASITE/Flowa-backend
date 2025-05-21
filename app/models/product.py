from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    brand_id: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = None
    brand_id: Optional[str] = None

class Product(ProductBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        orm_mode = True
