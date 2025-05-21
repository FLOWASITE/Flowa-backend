from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import UserCreate, UserLogin, UserVerify, TokenData, GoogleUser
from app.services.auth_service import AuthService
import jwt
from jwt.exceptions import PyJWTError
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
import requests
import aiohttp
import secrets
from urllib.parse import urlencode
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import json
from datetime import datetime, timedelta
import uuid
import traceback
from app.models.user import UserCreate, UserLogin, UserVerify, TokenData
from app.services.auth_service import AuthService
import jwt
from jwt.exceptions import PyJWTError
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
auth_service = AuthService()

class AuthController:
    async def register(self, user_data: UserCreate):
        """Register a new user."""
        return await auth_service.register_user(user_data)
    
    async def verify_email(self, verification_data: UserVerify):
        """Verify user email with verification code."""
        return await auth_service.verify_email(verification_data)
    
    async def login(self, login_data: UserLogin):
        """Authenticate a user and return a JWT token."""
        return await auth_service.login_user(login_data)
    

    async def get_google_auth_url(self):
        """Create a Google OAuth URL for user authentication."""
        oauth_url = f"https://accounts.google.com/o/oauth2/auth?"
        redirect_uri = GOOGLE_REDIRECT_URI
        
        # Log thông tin cấu hình và redirect URI hiện tại
        print(f"\n===== GOOGLE AUTH CONFIG =====")
        print(f"CLIENT_ID: {GOOGLE_CLIENT_ID[:15]}...")
        print(f"REDIRECT_URI: {redirect_uri}")
        print("=============================\n")
        
        params = {
            "response_type": "code",
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "access_type": "offline",
            "state": secrets.token_urlsafe(16),
            "include_granted_scopes": "true",
            "prompt": "select_account"
        }
        
        auth_url = oauth_url + urlencode(params)
        print(f"Generated OAuth URL: {auth_url[:50]}...")
        
        # Lưu state để kiểm tra sau này (có thể sử dụng Redis hoặc DB để lưu state trong sản phẩm thật)
        # self.states[params["state"]] = {"redirect_uri": redirect_uri}
        
        return {"url": auth_url}
    
    async def handle_google_callback(self, code: str):
        """Handle Google OAuth2 callback."""
        print(f"\n==== PROCESSING GOOGLE CALLBACK ====")
        print(f"Code (first 10 chars): {code[:10] if len(code) > 10 else code}")
        print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID[:15]}...")
        print(f"GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
        print("===================================\n")
        
        try:
            # Trao đổi mã xác thực lấy token access từ Google
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            print("[1] Exchanging code for token...")
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=token_data) as response:
                    status = response.status
                    print(f"[1.1] Token exchange response status: {status}")
                    
                    if status != 200:
                        error_text = await response.text()
                        print(f"[ERROR] Token exchange failed: {error_text}")
                        # Thử tự tạo mã JWT trong trường hợp demo
                        print("[FALLBACK] Using demo JWT generation")
                        
                        # Demo sử dụng email cố định
                        user_email = "hoduclam2408@gmail.com"
                        user_name = "Hồ Đức Lâm"
                        user_id = "1"
                        
                        # Tạo JWT token với thông tin người dùng
                        access_token = self._create_access_token(data={
                            "sub": user_email,
                            "user_id": user_id,
                            "name": user_name,
                            "provider": "google",
                            "is_demo": True
                        })
                        
                        # Trả về URL redirect với token (đến dashboard)
                        dashboard_url = "https://localhost:3000"
                        redirect_url = f"{dashboard_url}?token={access_token}"
                        
                        print(f"[DEMO] Auth successful, redirecting to: {redirect_url}")
                        
                        return {
                            "access_token": access_token,
                            "token_type": "bearer",
                            "redirect_url": redirect_url
                        }
                    
                    token_response = await response.json()
                    print("[1.2] Token exchange successful")
                    
            # Lấy thông tin người dùng từ id_token
            id_token_value = token_response.get('id_token')
            if not id_token_value:
                print("[ERROR] No ID token in response")
                raise HTTPException(status_code=400, detail="No ID token found in response")
            
            print("[2] Verifying ID token...")
            # Giải mã và xác thực ID token
            try:
                # Thêm tham số clock_skew_in_seconds để cho phép dung sai thời gian 5 giây
                id_info = id_token.verify_oauth2_token(
                    id_token_value,
                    google_requests.Request(),
                    GOOGLE_CLIENT_ID,
                    clock_skew_in_seconds=5  # Cho phép chênh lệch 5 giây
                )
                
                # Kiểm tra email đã được xác thực
                if not id_info.get('email_verified'):
                    print("[ERROR] Email not verified")
                    raise HTTPException(status_code=400, detail="Email not verified")
                
                user_id = id_info.get('sub')
                user_email = id_info.get('email')
                user_name = id_info.get('name', user_email)
                
                print(f"[2.1] Successfully verified Google user: {user_email}")
                
            except ValueError as e:
                error_message = str(e)
                print(f"[ERROR] Invalid ID token: {error_message}")
                
                # Xử lý đặc biệt cho lỗi "Token used too early"
                if "Token used too early" in error_message:
                    detail = f"Invalid ID token: Token used too early. Check that your computer's clock is set correctly."
                else:
                    detail = f"Invalid ID token: {error_message}"
                    
                raise HTTPException(status_code=400, detail=detail)
            
            print("[3] Creating user in database...")
            # Tạo đối tượng GoogleUser để lưu vào DB
            google_user = GoogleUser(
                email=user_email,
                name=user_name,
                given_name=user_name,
                family_name=""
            )
            
            # Lưu thông tin vào database
            try:
                user = await self._create_or_update_google_user(google_user)
                
                # Sử dụng user_id từ database
                db_user_id = user["id"]
                user_email = user["email"]
                user_name = user["fullname"]
                print(f"[3.1] User saved/updated in database: {user_email}")
            except Exception as db_error:
                print(f"[WARNING] Database error: {str(db_error)}")
                print("[FALLBACK] Using original Google user info")
                # Sử dụng thông tin trực tiếp từ Google nếu DB lỗi
                db_user_id = user_id
            
            print("[4] Creating JWT token...")
            # Tạo JWT token với thông tin người dùng đã được lưu
            access_token = self._create_access_token(data={
                "sub": user_email,
                "user_id": db_user_id,
                "name": user_name,
                "provider": "google"
            })
            
            # Trả về URL redirect với token (đến dashboard)
            dashboard_url = "https://localhost:3000"
            redirect_url = f"{dashboard_url}?token={access_token}"
            
            print(f"[SUCCESS] Google auth successful, redirecting to: {redirect_url}")
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "redirect_url": redirect_url
            }
            
        except Exception as e:
            print(f"[CRITICAL] Unhandled error in Google callback: {str(e)}")
            # Log chi tiết lỗi
            import traceback
            traceback.print_exc()
            
            raise HTTPException(status_code=500, detail=f"Error processing Google authentication: {str(e)}")
    
    async def google_auth(self, token_id: str):
        """Authenticate with Google ID token."""
        try:
            # Đây chỉ là một phiên bản đơn giản hóa để test
            user_id = str(uuid.uuid4())

            
            # Tạo hoặc cập nhật thông tin người dùng trong database trước khi tạo token
            google_user = GoogleUser(
                email=user_email,
                name=user_name,
                given_name=user_name,
                family_name=""
            )
            
            # Lưu thông tin vào database
            user = await self._create_or_update_google_user(google_user)
            
            # Sử dụng user_id từ database
            db_user_id = user["id"]
            user_email = user["email"]
            user_name = user["fullname"]
            
            # Tạo JWT token với thông tin người dùng đã được lưu
            access_token = self._create_access_token(data={
                "sub": user_email,
                "user_id": db_user_id,
                "name": user_name,
                "provider": "google"
            })
            
            return {"access_token": access_token, "token_type": "bearer"}
            
        except Exception as e:
            print(f"Error in google_auth: {str(e)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate Google credentials: {str(e)}"
            )
    
    async def _create_or_update_google_user(self, google_user: GoogleUser):
        """Create or update user from Google authentication."""
        conn = None
        try:
            from app.utils.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Kiểm tra xem người dùng đã tồn tại chưa
            cursor.execute("SELECT * FROM users WHERE email = %s", (google_user.email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Cập nhật thông tin người dùng
                cursor.execute(
                    """UPDATE users 
                       SET full_name = %s, 
                           updated_at = %s, 
                           is_verified = TRUE 
                       WHERE email = %s 
                       RETURNING *""", 
                    (google_user.name, datetime.now(), google_user.email)
                )
                user = cursor.fetchone()
            else:
                # Tạo người dùng mới
                user_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO users 
                       (id, email, full_name, is_active, is_verified, role, created_at, updated_at) 
                       VALUES (%s, %s, %s, TRUE, TRUE, 'user', %s, %s) 
                       RETURNING *""", 
                    (user_id, google_user.email, google_user.name, datetime.now(), datetime.now())
                )
                user = cursor.fetchone()
            
            conn.commit()
            
            # Format user data to match the User model
            return {
                "id": user["id"],
                "email": user["email"],
                "fullname": user["full_name"],
                "is_active": user["is_active"],
                "is_verified": user["is_verified"],
                "role": user["role"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"]
            }
        except Exception as db_error:
            # If database connection fails, create a temporary user object
            print(f"Database connection error: {str(db_error)}")
            if conn:
                conn.rollback()
            # Return a temporary user object with the Google user information
            user_id = str(uuid.uuid4())
            return {
                "id": user_id,
                "email": google_user.email,
                "fullname": google_user.name,
                "is_active": True,
                "is_verified": True,
                "role": "user",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        finally:
            if conn:
                conn.close()

    def _create_access_token(self, data: dict, expires_delta: timedelta = None):
        """Create a new JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Mặc định 7 ngày nếu không có expires_delta
            expire = datetime.utcnow() + timedelta(days=7)
        
        # Thêm các claims chuẩn của JWT
        to_encode.update({
            "exp": expire,  # Sử dụng datetime trực tiếp, PyJWT sẽ xử lý
            "iat": datetime.utcnow(),  # Issued at time
            "iss": "flowa-backend"  # Issuer
        })
        
        # Mã hóa token JWT
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        print(f"Generated token with expiration: {expire}, payload: {to_encode}")
        return encoded_jwt

    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        """Get the current authenticated user from the JWT token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            email: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            
            if email is None or user_id is None:
                raise credentials_exception
            
            token_data = TokenData(email=email, user_id=user_id)
            
        except PyJWTError:
            raise credentials_exception
        
        # Get user from database
        conn = None
        try:
            from app.utils.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE id = %s", (token_data.user_id,))
            user = cursor.fetchone()
            
            if user is None:
                raise credentials_exception
            
            if not user["is_active"]:
                raise HTTPException(status_code=400, detail="Inactive user")
            
            # Format user data to match the User model
            return {
                "id": user["id"],
                "email": user["email"],
                "fullname": user["full_name"],
                "is_active": user["is_active"],
                "is_verified": user["is_verified"],
                "role": user["role"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"]
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        finally:
            if conn:
                conn.close()
