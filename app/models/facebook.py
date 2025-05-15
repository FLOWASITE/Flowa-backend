from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class FacebookPostCreate(BaseModel):
    """
    Model cho việc tạo một bài đăng Facebook mới.
    """
    content: str = Field(..., description="Nội dung bài đăng", max_length=5000)
    link: Optional[str] = Field(None, description="URL liên kết đính kèm")
    place_id: Optional[str] = Field(None, description="ID địa điểm")
    tags: Optional[List[str]] = Field(None, description="Danh sách ID người dùng được gắn thẻ")
    media_ids: Optional[List[str]] = Field(None, description="Danh sách ID media đã upload")
    
class MediaUploadResponse(BaseModel):
    """
    Phản hồi khi upload media lên Facebook.
    """
    success: bool = Field(..., description="Trạng thái thành công")
    media_id: str = Field(..., description="ID của media đã upload")
    media_url: Optional[str] = Field(None, description="URL của media đã upload")

class FacebookPostResponse(BaseModel):
    """
    Phản hồi khi đăng bài thành công.
    """
    success: bool = Field(..., description="Trạng thái thành công")
    post_id: str = Field(..., description="ID của bài đăng")
    content: str = Field(..., description="Nội dung bài đăng")
    created_at: str = Field(..., description="Thời gian tạo bài đăng")
    post_url: Optional[str] = Field(None, description="URL đến bài đăng")
    
class FacebookErrorResponse(BaseModel):
    """
    Phản hồi khi có lỗi từ Facebook API.
    """
    success: bool = False
    error_code: int = Field(..., description="Mã lỗi từ Facebook")
    error_message: str = Field(..., description="Thông báo lỗi")
    error_subcode: Optional[int] = Field(None, description="Mã lỗi phụ") 