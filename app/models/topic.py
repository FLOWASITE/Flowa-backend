from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum

class TopicStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class TopicBase(BaseModel):
    title: str
    description: Optional[str] = None
    brand_id: str
    product_id: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None

class TopicCreate(TopicBase):
    pass

class TopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TopicStatus] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None

class Topic(TopicBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    status: TopicStatus = TopicStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        orm_mode = True

class TopicGenerateRequest(BaseModel):
    product_id: str
    brand_id: str
    prompt: str
    count: int = 5
    use_previous_topics: bool = True
    max_previous_topics: int = 5

class TopicGenerateResponse(BaseModel):
    topics: List[Topic]
