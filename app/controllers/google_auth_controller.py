"""
Google Authentication Controller
-------------------------------
Xử lý đăng nhập và xác thực với Google OAuth2.
"""

import json
import aiohttp
import asyncio
import secrets
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import HTTPException, Depends
from google.oauth2 import id_token
from google.auth import transport as google_requests
import jwt

from config.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    JWT_SECRET_KEY,
    JWT_ALGORITHM
)
from app.models.user import GoogleUser

# Thiết lập logging
logger = logging.getLogger("google_auth")
logger.setLevel(logging.INFO)

class GoogleAuthController:
    """Controller xử lý xác thực Google OAuth2."""
    
    async def get_auth_url(self):
        """
        Tạo URL xác thực Google OAuth2.
        
        Returns:
            dict: Dictionary chứa URL xác thực Google.
        """
        # Ghi log thông tin xác thực
        logger.info(f"Creating Google auth URL with redirect URI: {GOOGLE_REDIRECT_URI}")
        
        # Tạo state token để tránh CSRF attack
        state = secrets.token_urlsafe(16)
        
        # Tạo OAuth URL với các tham số cần thiết
        auth_url = "https://accounts.google.com/o/oauth2/auth?"
        params = {
            "response_type": "code",
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
            "include_granted_scopes": "true",
            "prompt": "select_account"
        }
        
        # URL cuối cùng
        final_url = auth_url + urlencode(params)
        logger.info(f"Google auth URL created: {final_url[:50]}...")
        
        return {"url": final_url}
    
    async def handle_callback(self, code: str):
        """
        Xử lý callback từ Google OAuth2.
        
        Args:
            code (str): Authorization code từ Google OAuth2.
        
        Returns:
            dict: Thông tin người dùng và token JWT.
        """
        logger.info(f"=== HANDLING GOOGLE CALLBACK START ===")
        logger.info(f"Code first 10 chars: {code[:10] if len(code) > 10 else code}...")
        
        try:
            # Bước 1: Trao đổi authorization code lấy token
            logger.info("STEP 1: Exchanging code for token...")
            token_data = await self._exchange_code_for_token(code)
            
            # In token response (những phần không nhạy cảm)
            token_keys = token_data.keys()
            logger.info(f"Token response contains keys: {', '.join(token_keys)}")
            
            # Bước 2: Xác thực và lấy thông tin người dùng
            logger.info("STEP 2: Verifying token and getting user info...")
            user_info = await self._verify_and_get_user_info(token_data.get('id_token'))
            
            # In thông tin người dùng (không có thông tin nhạy cảm)
            logger.info(f"User email: {user_info.get('email')}")
            logger.info(f"User name: {user_info.get('name')}")
            
            # Bước 3: Tạo JWT token cho người dùng
            logger.info("STEP 3: Creating JWT token...")
            access_token = self._create_jwt_token(user_info)
            
            # Bước 4: Tạo URL chuyển hướng đến dashboard
            dashboard_url = "https://localhost:3000/dashboard"
            redirect_url = f"{dashboard_url}?token={access_token}"
            
            logger.info(f"STEP 4: Authentication successful for {user_info.get('email')}")
            logger.info(f"Redirecting to: {redirect_url[:50]}...")
            logger.info(f"=== HANDLING GOOGLE CALLBACK COMPLETE ===\n")
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_info,
                "redirect_url": redirect_url
            }
            
        except Exception as e:
            logger.error(f"!!! ERROR in Google callback: {str(e)}")
            # Log stack trace for debugging
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"=== HANDLING GOOGLE CALLBACK FAILED ===\n")
            raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    
    async def _exchange_code_for_token(self, code: str):
        """
        Trao đổi authorization code lấy access token và ID token từ Google.
        
        Args:
            code (str): Authorization code từ Google OAuth2.
            
        Returns:
            dict: Token response từ Google.
        """
        logger.info("Exchanging code for tokens...")
        
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        logger.info(f"Using redirect_uri: {GOOGLE_REDIRECT_URI}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Token exchange failed: {error_text}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Failed to exchange code for token: {error_text}"
                        )
                    
                    token_response = await response.json()
                    logger.info("Token exchange successful")
                    return token_response
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during token exchange: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
    
    async def _verify_and_get_user_info(self, id_token_value: str):
        """
        Xác thực ID token và lấy thông tin người dùng.
        
        Args:
            id_token_value (str): ID token từ Google.
            
        Returns:
            dict: Thông tin người dùng.
        """
        if not id_token_value:
            logger.error("No ID token received from Google")
            raise HTTPException(status_code=400, detail="Missing ID token")
        
        logger.info(f"Verifying ID token with Google...")
        
        try:
            # Xác thực ID token với Google API
            user_data = id_token.verify_oauth2_token(
                id_token_value,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
            
            # Log thông tin giúp debug
            logger.info(f"ID token claims: {', '.join(user_data.keys())}")
            
            # Kiểm tra token hợp lệ
            if not user_data:
                logger.error("Empty user data after verification")
                raise HTTPException(status_code=400, detail="Invalid token")
            
            # Kiểm tra email đã xác thực
            email_verified = user_data.get('email_verified', False)
            if not email_verified:
                email = user_data.get('email', 'unknown')
                logger.warning(f"Unverified email: {email}")
                raise HTTPException(status_code=400, detail="Email not verified")
            
            # Trích xuất thông tin cần thiết từ token
            user_info = {
                "id": user_data.get('sub', ''),
                "email": user_data.get('email', ''),
                "name": user_data.get('name', ''),
                "given_name": user_data.get('given_name', ''),
                "family_name": user_data.get('family_name', ''),
                "picture": user_data.get('picture', ''),
                "locale": user_data.get('locale', '')
            }
            
            # Log để debug (bỏ qua thông tin nhạy cảm)
            logger.info(f"User ID (sub): {user_info['id'][:5]}...")
            logger.info(f"Email: {user_info['email']}")
            logger.info(f"Name: {user_info['name']}")
            logger.info(f"Locale: {user_info['locale']}")
            
            return user_info
            
        except ValueError as e:
            logger.error(f"ID token verification failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")
    
    def _create_jwt_token(self, user_info: dict):
        """
        Tạo JWT token cho người dùng.
        
        Args:
            user_info (dict): Thông tin người dùng từ Google.
            
        Returns:
            str: JWT token.
        """
        logger.info(f"Creating JWT token for user: {user_info.get('email')}")
        
        # Đảm bảo ID người dùng tồn tại
        user_id = user_info.get('id')
        if not user_id:
            logger.warning("User ID missing, using email as fallback")
            user_id = user_info.get('email', 'unknown')
        
        # Thời gian hết hạn: 7 ngày
        expires_delta = timedelta(days=7)
        expire = datetime.utcnow() + expires_delta
        
        # Tạo payload với thông tin người dùng từ Google
        to_encode = {
            "sub": user_info.get('email', ''),
            "user_id": user_id,
            "name": user_info.get('name', ''),
            "email": user_info.get('email', ''),
            "given_name": user_info.get('given_name', ''),
            "family_name": user_info.get('family_name', ''),
            "picture": user_info.get('picture', ''),
            "locale": user_info.get('locale', ''),
            "exp": expire,
            "iat": datetime.utcnow(),
            "provider": "google"
        }
        
        # Log thông tin giúp debug
        logger.info(f"JWT payload keys: {', '.join(to_encode.keys())}")
        logger.info(f"Token will expire at: {expire.isoformat()}")
        
        # Mã hóa JWT token
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                JWT_SECRET_KEY,
                algorithm=JWT_ALGORITHM
            )
            logger.info(f"JWT token created successfully, length: {len(encoded_jwt)}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Error creating JWT token: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating authentication token: {str(e)}")

# Khởi tạo controller
google_auth_controller = GoogleAuthController()
