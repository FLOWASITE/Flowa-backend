import os
import jwt
import random
import string
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.utils.database import get_db_connection
from app.models.user import UserCreate, UserLogin, UserVerify
from fastapi import HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES, EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a stored password against a provided password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """Generate a random verification code."""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
        """Create a JWT token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def send_verification_email(email: str, verification_code: str) -> bool:
        """Send verification email with the verification code."""
        try:
            message = MIMEMultipart()
            message["From"] = EMAIL_FROM
            message["To"] = email
            message["Subject"] = "Email Verification"
            
            body = f"""
            <html>
              <body>
                <h2>Email Verification</h2>
                <p>Thank you for registering. Please use the following verification code to complete your registration:</p>
                <h3>{verification_code}</h3>
                <p>This code will expire in 10 minutes.</p>
              </body>
            </html>
            """
            
            message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.sendmail(EMAIL_FROM, email, message.as_string())
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    async def register_user(self, user_data: UserCreate):
        """Register a new user."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (user_data.email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")
            
            # Hash the password
            hashed_password = self.get_password_hash(user_data.password)
            
            # Generate verification code
            verification_code = self.generate_verification_code()
            
            # Insert user into database
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, full_name, is_active, is_verified, verification_code, verification_code_expires_at, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, full_name, is_active, is_verified, created_at, updated_at, role
                """,
                (
                    user_data.email,
                    hashed_password,
                    user_data.fullname,
                    True,  # is_active
                    False,  # is_verified
                    verification_code,
                    datetime.utcnow() + timedelta(minutes=10),  # verification code expires in 10 minutes
                    'admin'  # default role
                )
            )
            
            user = cursor.fetchone()
            conn.commit()
            
            # Send verification email
            email_sent = self.send_verification_email(user_data.email, verification_code)
            
            return {
                "success": True,
                "message": "User registered successfully. Please check your email for verification code.",
                "email_sent": email_sent,
                "user": user
            }
        
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to register user: {str(e)}")
        
        finally:
            cursor.close()
            conn.close()
    
    async def verify_email(self, verification_data: UserVerify):
        """Verify user email with verification code."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user exists and verification code is valid
            cursor.execute(
                """
                SELECT * FROM users 
                WHERE email = %s AND verification_code = %s AND verification_code_expires_at > %s
                """,
                (verification_data.email, verification_data.verification_code, datetime.utcnow())
            )
            
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=400, detail="Invalid or expired verification code")
            
            # Update user as verified
            cursor.execute(
                """
                UPDATE users 
                SET is_verified = TRUE, verification_code = NULL, verification_code_expires_at = NULL, updated_at = %s
                WHERE email = %s
                RETURNING id, email, full_name, is_active, is_verified, created_at, updated_at, role
                """,
                (datetime.utcnow(), verification_data.email)
            )
            
            verified_user = cursor.fetchone()
            conn.commit()
            
            # Create access token
            access_token = self.create_access_token(
                data={"sub": verified_user["email"], "user_id": str(verified_user["id"])}
            )
            
            return {
                "success": True,
                "message": "Email verified successfully",
                "access_token": access_token,
                "token_type": "bearer",
                "user": verified_user
            }
        
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to verify email: {str(e)}")
        
        finally:
            cursor.close()
            conn.close()
    
    async def login_user(self, login_data: UserLogin):
        """Authenticate a user and return a JWT token."""
        print(f"[LOGIN] Attempting login for user: {login_data.email}")
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = get_db_connection()
            print(f"[LOGIN] Database connection established successfully")
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (login_data.email,))
            user = cursor.fetchone()
            print(f"[LOGIN] User query result: {user is not None}")
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            # Verify password
            password_verified = self.verify_password(login_data.password, user["password_hash"])
            print(f"[LOGIN] Password verification: {password_verified}")
            if not password_verified:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            # Check if user is verified
            if not user["is_verified"]:
                raise HTTPException(status_code=401, detail="Email not verified")
            
            # Create access token
            access_token = self.create_access_token(
                data={"sub": user["email"], "user_id": str(user["id"])}
            )
            print(f"[LOGIN] Successfully created access token")
            
            return {
                "success": True,
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "fullname": user["full_name"],
                    "is_active": user["is_active"],
                    "is_verified": user["is_verified"],
                    "role": user["role"],
                    "created_at": user["created_at"],
                    "updated_at": user["updated_at"]
                }
            }
        
        except HTTPException as e:
            print(f"[LOGIN ERROR] HTTP Exception: {e.detail}")
            raise e
        
        except Exception as e:
            error_detail = f"Login failed: {str(e)}"
            print(f"[LOGIN ERROR] Exception: {error_detail}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=error_detail)
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            print("[LOGIN] Database connection closed")
