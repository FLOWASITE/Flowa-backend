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
