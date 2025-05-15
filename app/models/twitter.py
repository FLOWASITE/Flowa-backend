from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class TweetCreate(BaseModel):
    """Model để tạo tweet mới"""
    content: str = Field(..., min_length=1, max_length=280, description="Nội dung tweet, tối đa 280 ký tự")
    media_ids: Optional[List[str]] = Field(None, description="Danh sách ID media để đính kèm (tùy chọn)")
    reply_to_id: Optional[str] = Field(None, description="ID của tweet mà bài đăng mới đang trả lời (tùy chọn)")
    
    @validator('content')
    def validate_content(cls, v):
        if len(v) > 280:
            raise ValueError('Nội dung tweet không được vượt quá 280 ký tự')
        return v

class TweetResponse(BaseModel):
    """Model cho phản hồi sau khi tạo tweet"""
    success: bool
    tweet_id: str
    content: str
    created_at: str
    tweet_url: str

class MediaUploadResponse(BaseModel):
    """Model cho phản hồi sau khi tải lên media"""
    success: bool
    media_id: str
