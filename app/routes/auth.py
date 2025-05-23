
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import UserCreate, UserLogin, UserVerify, Token, GoogleAuthRequest
from app.controllers.auth_controller import AuthController, oauth2_scheme
from typing import Optional
from fastapi.responses import RedirectResponse
from config.settings import GOOGLE_REDIRECT_URI

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import UserCreate, UserLogin, UserVerify, Token
from app.controllers.auth_controller import AuthController, oauth2_scheme
from typing import Optional


router = APIRouter(prefix="/api/auth", tags=["authentication"])
auth_controller = AuthController()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Đăng ký người dùng mới.
    
    - Yêu cầu email và mật khẩu
    - Gửi mã xác thực đến email người dùng
    - Trả về thông tin người dùng đã đăng ký
    """
    return await auth_controller.register(user_data)

@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_email(verification_data: UserVerify):
    """
    Xác thực email người dùng bằng mã xác thực.
    
    - Yêu cầu email và mã xác thực
    - Xác thực email người dùng
    - Trả về token JWT nếu xác thực thành công
    """
    return await auth_controller.verify_email(verification_data)

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    """
    Đăng nhập người dùng.
    
    - Yêu cầu email và mật khẩu
    - Xác thực thông tin đăng nhập
    - Trả về token JWT nếu xác thực thành công
    """
    return await auth_controller.login(login_data)

@router.post("/logout")
async def logout(response: Response, token: str = Depends(oauth2_scheme)):
    """
    Đăng xuất người dùng.
    
    - Xóa cookie và session
    - Trả về thông báo đăng xuất thành công
    """
    # JWT là stateless nên không cần lưu trữ token ở server
    # Chỉ cần xóa cookie ở client
    response.delete_cookie(key="access_token")
    return {"message": "Đăng xuất thành công"}

@router.get("/me")
async def get_current_user(current_user = Depends(auth_controller.get_current_user)):
    """
    Lấy thông tin người dùng hiện tại.
    
    - Yêu cầu token JWT
    - Trả về thông tin người dùng hiện tại
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "fullname": current_user["fullname"],
        "is_active": current_user["is_active"],
        "is_verified": current_user["is_verified"],
        "created_at": current_user["created_at"],
        "updated_at": current_user["updated_at"]
    }


@router.post("/google", response_model=Token)
async def google_auth(auth_data: GoogleAuthRequest, response: Response):
    """
    Xác thực người dùng bằng Google.
    
    - Yêu cầu token ID từ Google
    - Xác thực token với Google
    - Tạo hoặc cập nhật người dùng trong cơ sở dữ liệu
    - Trả về token JWT nếu xác thực thành công
    """
    token_data = await auth_controller.google_auth(auth_data.token_id)
    
    # Đặt cookie HttpOnly nếu cần
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token_data['access_token']}",
        httponly=True,
        max_age=1800,  # 30 phút
        expires=1800,
        samesite="lax",
        secure=False  # Đặt thành True trong môi trường production với HTTPS
    )
    
    return token_data

@router.options("/verify-token")
async def verify_token_options():
    # Handle OPTIONS preflight request for CORS
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={})
    # Add CORS headers manually
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Max-Age"] = "600"
    return response

@router.post("/verify-token")
async def verify_token(request: Request):
    """
    Xác thực token JWT.
    
    - Yêu cầu token JWT trong header Authorization
    - Trả về kết quả xác thực với trạng thái và thông tin người dùng nếu hợp lệ
    """
    # Import controller extension
    from app.controllers.auth_controller_extension import AuthControllerExtension
    from fastapi.responses import JSONResponse
    
    # Lấy token từ header Authorization
    authorization = request.headers.get("Authorization")
    
    if not authorization:
        result = {"valid": False, "message": "Missing Authorization header"}
    else:
        # In ra thông tin debug
        print(f"Authorization header: {authorization}")
        
        # Xác thực token
        auth_controller_extension = AuthControllerExtension()
        result = await auth_controller_extension.verify_token(authorization)
        
        # In ra kết quả xác thực
        print(f"Verification result: {result}")
    
    # Create a response with CORS headers
    response = JSONResponse(content=result)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@router.get("/google/url")
async def get_google_auth_url():
    """
    Lấy URL xác thực Google và chuyển hướng người dùng.
    
    - Chuyển hướng trực tiếp đến trang đăng nhập Google
    """
    auth_url = await auth_controller.get_google_auth_url()
    return RedirectResponse(url=auth_url["url"])

@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None, scope: str = None, state: str = None):
    """
    Callback từ Google OAuth2.
    
    - Xử lý callback từ Google sau khi người dùng xác thực
    - Tạo hoặc cập nhật người dùng trong cơ sở dữ liệu
    - Chuyển hướng người dùng đến trang chủ với token JWT
    """
    try:
        # In toàn bộ các thông số để phân tích và debug
        print("===== GOOGLE CALLBACK DEBUG INFO =====")
        print(f"Request path: {GOOGLE_REDIRECT_URI}")
        print(f"Code: {code[:10] if code and len(code) > 10 else code}")
        print(f"Error: {error}")
        print(f"Scope: {scope}")
        print(f"State: {state}")
        print("=======================================\n")
        
        # Frontend URLs - sử dụng từ môi trường hoặc cấu hình
        frontend_url = "https://flowa.one"  # Flowa landing page
        dashboard_url = "https://ai.flowa.one" # Flowa_prod dashboard
        token_handler_url = "https://ai.flowa.one/token-handler" # Token handler page
        
        if error:
            print(f"[ERROR] Google Auth Error: {error}")
            redirect_url = f"{frontend_url}/auth-callback?error={error}"
            return RedirectResponse(url=redirect_url)
        
        if not code:
            print("[ERROR] No code provided in Google callback")
            redirect_url = f"{frontend_url}/auth-callback?error=no_code"
            return RedirectResponse(url=redirect_url)
        
        # Xử lý với code nhận được từ Google
        try:    
            print(f"[INFO] Processing Google code: {code[:10]}...")
            # Gọi controller để xử lý code và tạo token
            result = await auth_controller.handle_google_callback(code)
            redirect_url = result.get("redirect_url")
            
            # Lấy token từ kết quả xử lý
            token = result.get("access_token", "")
            
            # Thay đổi chuyển hướng đến token-handler thay vì dashboard trực tiếp
            redirect_url = f"{token_handler_url}?token={token}"
                
            print(f"[SUCCESS] Redirecting to token handler: {redirect_url}")
            return RedirectResponse(url=redirect_url)
            
        except Exception as controller_error:
            print(f"[ERROR] Handle Google Callback Exception: {str(controller_error)}")
            import traceback
            traceback.print_exc()
            
            # Ngay cả khi lỗi, vẫn cố gắng chuyển hướng đến token-handler với token lỗi
            # để ứng dụng frontend có thể xử lý lỗi đúng cách
            token = "error_token"
            error_message = str(controller_error)
            redirect_url = f"{token_handler_url}?token={token}&error=backend_error&message={error_message}"
            return RedirectResponse(url=redirect_url)
            
    except Exception as outer_error:
        print(f"[CRITICAL] Unhandled error in Google callback route: {str(outer_error)}")
        import traceback
        traceback.print_exc()
        
        # Luôn chuyển hướng đến trang xử lý token trong mọi trường hợp
        fallback_token = "emergency_fallback_token"
        token_handler_url = "https://ai.flowa.one/token-handler"
        redirect_url = f"{token_handler_url}?token={fallback_token}&error=internal_server_error&message=Server+error"
        return RedirectResponse(url=redirect_url)

