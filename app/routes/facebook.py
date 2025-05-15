from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from app.models.facebook import FacebookPostCreate, FacebookPostResponse, MediaUploadResponse
from app.controllers.facebook_controller import FacebookController
from app.controllers.auth_controller import AuthController, oauth2_scheme
import os
import shutil
from pathlib import Path
from typing import List, Optional
import uuid

router = APIRouter(prefix="/api/facebook", tags=["facebook"])
facebook_controller = FacebookController()
auth_controller = AuthController()

# Tạo thư mục tạm thời để lưu trữ file media
TEMP_UPLOAD_DIR = Path("temp/uploads")
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class FacebookPostRequest(FacebookPostCreate):
    page_id: str

@router.post("/post", response_model=FacebookPostResponse)
async def create_facebook_post(
    post_request: FacebookPostRequest,
    current_user = Depends(auth_controller.get_current_user)
):
    """
    Đăng một bài viết mới lên trang Facebook.
    
    - Yêu cầu xác thực người dùng
    - Cần cung cấp ID của trang Facebook và thông tin bài đăng
    - Trả về thông tin về bài đăng đã tạo
    """
    # Lấy thông tin người dùng hiện tại
    user_id = current_user["id"]
    
    # TODO: Lấy Facebook page access token từ cơ sở dữ liệu
    # Trong ứng dụng thực tế, bạn nên lưu trữ page access token trong cơ sở dữ liệu
    # và lấy ra khi cần. Ở đây chúng ta tạm sử dụng giá trị mặc định
    page_access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    
    if not page_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy access token cho trang Facebook"
        )
    
    try:
        # Đăng bài lên Facebook
        result = await facebook_controller.post_to_page(
            page_id=post_request.page_id,
            page_access_token=page_access_token,
            content=post_request.content,
            link=post_request.link,
            place_id=post_request.place_id,
            media_ids=post_request.media_ids,
            tags=post_request.tags
        )
        
        # Log hoạt động
        print(f"User {user_id} posted to Facebook page {post_request.page_id}: {result['post_id']}")
        
        return result
    
    except Exception as e:
        print(f"Error posting to Facebook for user {user_id}: {str(e)}")
        raise

@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_facebook_media(
    file: UploadFile = File(...),
    page_id: str = Form(...),
    caption: Optional[str] = Form(None),
    is_video: bool = Form(False),
    current_user = Depends(auth_controller.get_current_user)
):
    """
    Tải lên phương tiện (ảnh, video) để đính kèm vào bài đăng Facebook.
    
    - Yêu cầu xác thực người dùng
    - Hỗ trợ các định dạng ảnh (jpg, png, webp), video (mp4)
    - Trả về media_id để sử dụng khi đăng bài
    """
    # Lấy thông tin người dùng hiện tại
    user_id = current_user["id"]
    
    # TODO: Lấy Facebook page access token từ cơ sở dữ liệu
    page_access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    
    if not page_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy access token cho trang Facebook"
        )
    
    # Kiểm tra định dạng file
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webp"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file không được hỗ trợ. Các định dạng hỗ trợ: {', '.join(valid_extensions)}"
        )
    
    # Xác định loại file
    is_video = file_ext == ".mp4" or is_video
    
    try:
        # Tạo tên file duy nhất
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = TEMP_UPLOAD_DIR / unique_filename
        
        # Lưu file tạm thời
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Upload lên Facebook
        result = await facebook_controller.upload_media(
            page_id=page_id,
            page_access_token=page_access_token,
            file_path=str(file_path),
            caption=caption,
            is_video=is_video
        )
        
        # Xóa file tạm thời sau khi tải lên
        os.unlink(file_path)
        
        # Log hoạt động
        print(f"User {user_id} uploaded media to Facebook: {result['media_id']}")
        
        return result
    
    except Exception as e:
        # Đảm bảo xóa file tạm nếu có lỗi
        if os.path.exists(file_path):
            os.unlink(file_path)
        
        print(f"Error uploading media to Facebook for user {user_id}: {str(e)}")
        raise

@router.get("/pages")
async def get_facebook_pages(current_user = Depends(auth_controller.get_current_user)):
    """
    Lấy danh sách các trang Facebook mà người dùng quản lý.
    
    - Yêu cầu xác thực người dùng
    - Trả về danh sách các trang với ID và access token
    """
    # Lấy thông tin người dùng hiện tại
    user_id = current_user["id"]
    
    # TODO: Lấy Facebook user access token từ cơ sở dữ liệu
    user_access_token = os.getenv("FACEBOOK_USER_ACCESS_TOKEN")
    
    if not user_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy Facebook access token cho người dùng"
        )
    
    try:
        # Lấy danh sách trang
        result = await facebook_controller.get_user_pages(user_access_token)
        
        # Log hoạt động
        print(f"User {user_id} retrieved Facebook pages list")
        
        return result
    
    except Exception as e:
        print(f"Error getting Facebook pages for user {user_id}: {str(e)}")
        raise 