from fastapi import HTTPException, Depends, status
import requests
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

class FacebookController:
    def __init__(self):
        # Facebook API credentials
        self.app_id = os.getenv('FACEBOOK_APP_ID')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET')
        self.api_version = "v17.0"  # Phiên bản API Facebook
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Kiểm tra nếu thiếu thông tin xác thực
        if not all([self.app_id, self.app_secret]):
            print("WARNING: Missing Facebook API credentials. Some functionality might not work.")
    
    def _get_app_access_token(self):
        """
        Lấy app access token từ Facebook.
        """
        try:
            url = f"{self.base_url}/oauth/access_token"
            params = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "client_credentials"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Không thể lấy app access token: {response.text}"
                )
                
            return response.json().get("access_token")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi lấy app access token: {str(e)}"
            )
    
    async def post_to_page(self, page_id: str, page_access_token: str, content: str, 
                         link: Optional[str] = None, place_id: Optional[str] = None,
                         media_ids: Optional[List[str]] = None, tags: Optional[List[str]] = None):
        """
        Đăng bài lên một trang Facebook.
        
        Args:
            page_id: ID của trang Facebook
            page_access_token: Access token của trang
            content: Nội dung bài đăng
            link: URL liên kết đính kèm (tùy chọn)
            place_id: ID địa điểm (tùy chọn)
            media_ids: Danh sách ID media đã upload (tùy chọn)
            tags: Danh sách ID người dùng được gắn thẻ (tùy chọn)
            
        Returns:
            dict: Thông tin về bài đăng
        """
        try:
            url = f"{self.base_url}/{page_id}/feed"
            
            # Chuẩn bị dữ liệu đăng bài
            data = {
                "message": content,
                "access_token": page_access_token
            }
            
            # Thêm các tham số tùy chọn nếu có
            if link:
                data["link"] = link
                
            if place_id:
                data["place"] = place_id
                
            if tags:
                data["tags"] = ",".join(tags)
                
            if media_ids:
                # Nếu có media, sử dụng endpoint photos hoặc videos thay vì feed
                if len(media_ids) == 1:
                    # Đăng một ảnh/video
                    data["attached_media"] = [{"media_fbid": media_id} for media_id in media_ids]
                else:
                    # Đăng nhiều ảnh/video
                    attached_media = []
                    for media_id in media_ids:
                        attached_media.append({"media_fbid": media_id})
                    data["attached_media"] = json.dumps(attached_media)
            
            # Gửi yêu cầu đăng bài
            response = requests.post(url, data=data)
            
            # Xử lý phản hồi
            if response.status_code != 200:
                error_data = response.json().get("error", {})
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error_code": error_data.get("code", 0),
                        "error_message": error_data.get("message", "Lỗi không xác định"),
                        "error_subcode": error_data.get("error_subcode")
                    }
                )
            
            # Lấy thông tin bài đăng
            result = response.json()
            post_id = result.get("id")
            
            return {
                "success": True,
                "post_id": post_id,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "post_url": f"https://facebook.com/{post_id}"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi đăng bài lên Facebook: {str(e)}"
            )
    
    async def upload_media(self, page_id: str, page_access_token: str, file_path: str, 
                        caption: Optional[str] = None, is_video: bool = False):
        """
        Upload media (ảnh hoặc video) lên Facebook.
        
        Args:
            page_id: ID của trang Facebook
            page_access_token: Access token của trang
            file_path: Đường dẫn đến file cần upload
            caption: Mô tả cho ảnh/video (tùy chọn)
            is_video: True nếu file là video, False nếu là ảnh
            
        Returns:
            dict: Thông tin về media đã upload
        """
        try:
            # Endpoint khác nhau cho ảnh và video
            endpoint = "videos" if is_video else "photos"
            url = f"{self.base_url}/{page_id}/{endpoint}"
            
            # Chuẩn bị dữ liệu
            data = {
                "access_token": page_access_token,
                "published": "false"  # Chưa công khai
            }
            
            if caption:
                data["caption"] = caption
            
            # Đọc file
            with open(file_path, "rb") as file:
                files = {
                    "source": (os.path.basename(file_path), file, "multipart/form-data")
                }
                
                # Upload file
                response = requests.post(url, data=data, files=files)
            
            # Xử lý phản hồi
            if response.status_code != 200:
                error_data = response.json().get("error", {})
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error_code": error_data.get("code", 0),
                        "error_message": error_data.get("message", "Lỗi không xác định"),
                        "error_subcode": error_data.get("error_subcode")
                    }
                )
            
            # Lấy thông tin media
            result = response.json()
            media_id = result.get("id")
            
            return {
                "success": True,
                "media_id": media_id,
                "media_url": f"https://facebook.com/{media_id}"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi upload media lên Facebook: {str(e)}"
            )
    
    async def get_user_pages(self, user_access_token: str):
        """
        Lấy danh sách các trang Facebook mà người dùng quản lý.
        
        Args:
            user_access_token: Access token của người dùng
            
        Returns:
            list: Danh sách các trang với ID và access token
        """
        try:
            url = f"{self.base_url}/me/accounts"
            params = {
                "access_token": user_access_token,
                "fields": "id,name,access_token,picture"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                error_data = response.json().get("error", {})
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error_code": error_data.get("code", 0),
                        "error_message": error_data.get("message", "Lỗi không xác định"),
                        "error_subcode": error_data.get("error_subcode")
                    }
                )
            
            # Lấy danh sách trang
            result = response.json()
            pages = result.get("data", [])
            
            return {
                "success": True,
                "pages": pages
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi lấy danh sách trang Facebook: {str(e)}"
            ) 