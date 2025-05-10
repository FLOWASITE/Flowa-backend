from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
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
