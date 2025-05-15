"""
Google Authentication Routes
---------------------------
Định nghĩa các routes để xử lý đăng nhập và xác thực với Google OAuth.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse

from app.controllers.google_auth_controller import google_auth_controller

# Thiết lập logging
logger = logging.getLogger("google_auth_routes")
logger.setLevel(logging.INFO)

# Tạo router với prefix
router = APIRouter(
    prefix="/google",
    tags=["google_auth"],
    responses={404: {"description": "Not found"}},
)

@router.get("/login")
async def google_login():
    """
    Khởi tạo quá trình đăng nhập Google OAuth2.
    
    Returns:
        RedirectResponse: Chuyển hướng đến trang xác thực Google.
    """
    logger.info("Starting Google login flow")
    auth_url = await google_auth_controller.get_auth_url()
    return RedirectResponse(url=auth_url["url"])

@router.get("/url")
async def get_google_auth_url():
    """
    Lấy URL xác thực Google OAuth2.
    
    Returns:
        dict: Dictionary chứa URL xác thực Google.
    """
    logger.info("Getting Google auth URL")
    return await google_auth_controller.get_auth_url()

@router.get("/callback")
async def google_callback(code: str = Query(None), error: str = Query(None), state: str = Query(None)):
    """
    Xử lý callback từ Google OAuth2 sau khi người dùng xác thực.
    
    Args:
        code (str, optional): Authorization code từ Google.
        error (str, optional): Mã lỗi nếu người dùng từ chối xác thực.
        state (str, optional): State token để ngăn CSRF attack.
        
    Returns:
        RedirectResponse: Chuyển hướng đến dashboard hoặc trang lỗi.
    """
    # Ghi log thông tin callback
    logger.info("Received Google callback")
    logger.info(f"Code present: {code is not None}")
    logger.info(f"Error present: {error is not None}")
    
    # Kiểm tra lỗi từ Google
    if error:
        logger.error(f"Google auth error: {error}")
        # Chuyển hướng đến trang lỗi
        error_url = "http://localhost:8080/login?error=google_auth_failed&message=" + error
        return RedirectResponse(url=error_url)
    
    # Kiểm tra có mã xác thực không
    if not code:
        logger.error("No authorization code in callback")
        error_url = "http://localhost:8080/login?error=no_auth_code"
        return RedirectResponse(url=error_url)
    
    try:
        # Xử lý callback với code
        result = await google_auth_controller.handle_callback(code)
        
        # Chuyển hướng đến dashboard với token
        return RedirectResponse(url=result["redirect_url"])
        
    except HTTPException as e:
        # Xử lý lỗi HTTPException
        logger.error(f"HTTP error in callback: {e.detail}")
        error_url = f"http://localhost:8080/login?error=auth_failed&message={e.detail}"
        return RedirectResponse(url=error_url)
        
    except Exception as e:
        # Xử lý lỗi không mong muốn
        logger.error(f"Unexpected error in callback: {str(e)}")
        error_url = "http://localhost:8080/login?error=server_error&message=Internal server error"
        return RedirectResponse(url=error_url)
