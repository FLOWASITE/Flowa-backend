from fastapi import HTTPException, Depends, status
import tweepy
from app.models.user import User
from app.controllers.auth_controller import AuthController, oauth2_scheme
import os
from typing import Optional, List
from datetime import datetime

class TwitterController:
    def __init__(self):
        # Twitter API credentials
        self.api_key = os.getenv('TWITTER_API_KEY', 'rjha1G24VCnUormt2q62H8WPX')
        self.api_secret = os.getenv('TWITTER_API_SECRET', 'oxlvgYU4Jl6I78W4fCFlmqofZjMdEl6fuvwT3cUPxqY2HW1jMY')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Kiểm tra nếu thiếu thông tin xác thực
        if not all([self.api_key, self.api_secret]):
            print("WARNING: Missing Twitter API credentials. Some functionality might not work.")
    
    def _get_client(self, user_token=None, user_secret=None):
        """
        Tạo và trả về client Twitter API v2.
        Nếu cung cấp user_token và user_secret, sẽ sử dụng thông tin xác thực của người dùng.
        Nếu không, sẽ sử dụng thông tin xác thực của ứng dụng.
        """
        try:
            # Sử dụng thông tin xác thực cụ thể của người dùng nếu có
            if user_token and user_secret:
                client = tweepy.Client(
                    bearer_token=self.bearer_token,
                    consumer_key=self.api_key, 
                    consumer_secret=self.api_secret,
                    access_token=user_token, 
                    access_token_secret=user_secret
                )
            else:
                # Sử dụng thông tin xác thực của ứng dụng
                client = tweepy.Client(
                    bearer_token=self.bearer_token,
                    consumer_key=self.api_key, 
                    consumer_secret=self.api_secret,
                    access_token=self.access_token, 
                    access_token_secret=self.access_token_secret
                )
            return client
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Không thể khởi tạo Twitter client: {str(e)}"
            )
    
    async def post_tweet(self, content: str, user_token: Optional[str] = None, user_secret: Optional[str] = None, 
                         media_ids: Optional[List[str]] = None, reply_to_id: Optional[str] = None):
        """
        Đăng bài viết (tweet) mới trên Twitter.
        
        Args:
            content: Nội dung bài đăng, tối đa 280 ký tự
            user_token: Token truy cập của người dùng (tùy chọn)
            user_secret: Secret của token truy cập người dùng (tùy chọn)
            media_ids: Danh sách ID media để đính kèm (tùy chọn)
            reply_to_id: ID của tweet mà bài đăng mới đang trả lời (tùy chọn)
            
        Returns:
            dict: Thông tin về tweet đã đăng
        """
        try:
            # In thông tin API key để debug
            print(f"DEBUG - Twitter API Key (5 ký tự đầu): {self.api_key[:5] if self.api_key else 'None'}")
            print(f"DEBUG - Content: {content}")
            print(f"DEBUG - Using user token: {user_token is not None}")
            print(f"DEBUG - Media IDs: {media_ids}")
            
            # Kiểm tra độ dài nội dung tweet
            if len(content) > 280:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nội dung tweet không được vượt quá 280 ký tự"
                )
            
            # Lấy Twitter client
            client = self._get_client(user_token, user_secret)
            
            # Đăng tweet mới
            response = client.create_tweet(
                text=content, 
                media_ids=media_ids,
                in_reply_to_tweet_id=reply_to_id
            )
            
            # Xây dựng thông tin phản hồi
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"
            
            return {
                "success": True,
                "tweet_id": tweet_id,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "tweet_url": tweet_url
            }
            
        except tweepy.TweepyException as e:
            # Xử lý lỗi từ Twitter API
            error_message = str(e)
            status_code = status.HTTP_400_BAD_REQUEST
            
            # Phân loại lỗi cụ thể từ Twitter API
            if "401" in error_message:
                status_code = status.HTTP_401_UNAUTHORIZED
                error_message = "Không có quyền truy cập Twitter API. Kiểm tra thông tin xác thực."
            elif "429" in error_message:
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
                error_message = "Đã vượt quá giới hạn yêu cầu Twitter API. Thử lại sau."
            
            raise HTTPException(
                status_code=status_code,
                detail=f"Lỗi Twitter API: {error_message}"
            )
            
        except Exception as e:
            # Xử lý các lỗi khác
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi đăng tweet: {str(e)}"
            )
    
    async def upload_media(self, file_path: str, user_token: Optional[str] = None, user_secret: Optional[str] = None):
        """
        Tải lên phương tiện (ảnh, video, gif) để đính kèm vào tweet.
        
        Args:
            file_path: Đường dẫn đến file cần tải lên
            user_token: Token truy cập của người dùng (tùy chọn)
            user_secret: Secret của token truy cập người dùng (tùy chọn)
            
        Returns:
            str: Media ID có thể sử dụng khi đăng tweet
        """
        try:
            # Khởi tạo API v1.1 để tải lên phương tiện (API v2 chưa hỗ trợ tải lên phương tiện)
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                user_token or self.access_token, 
                user_secret or self.access_token_secret
            )
            api = tweepy.API(auth)
            
            # Tải lên phương tiện
            media = api.media_upload(filename=file_path)
            
            return {
                "success": True,
                "media_id": str(media.media_id)
            }
            
        except tweepy.TweepyException as e:
            # Xử lý lỗi từ Twitter API
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi tải lên phương tiện: {str(e)}"
            )
            
        except Exception as e:
            # Xử lý các lỗi khác
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi tải lên phương tiện: {str(e)}"
            )
