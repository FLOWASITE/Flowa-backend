from fastapi import HTTPException, Depends, status
from jwt.exceptions import PyJWTError
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM
import jwt

class AuthControllerExtension:
    async def verify_token(self, token: str):
        """
        Xác thực token JWT và trả về kết quả xác thực
        
        Args:
            token (str): JWT token cần xác thực
            
        Returns:
            dict: Kết quả xác thực với trạng thái và thông tin người dùng nếu hợp lệ
        """
        try:
            # Xóa tiền tố 'Bearer ' nếu có
            if token and token.startswith('Bearer '):
                token = token.replace('Bearer ', '')
                
            # Giải mã token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            email: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            
            if email is None or user_id is None:
                return {"valid": False, "message": "Invalid token format"}
            
            # Kiểm tra user trong database
            conn = None
            try:
                from app.utils.database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                
                if user is None:
                    # Nếu người dùng không tồn tại trong database, tạo một đối tượng tạm thời
                    print(f"User with ID {user_id} not found in database. Creating temporary user object.")
                    
                    # Tạo người dùng mới trong database
                    try:
                        # Tạo một password_hash mặc định cho Google login
                        import hashlib
                        default_password_hash = hashlib.sha256(f"GOOGLE_AUTH_{user_id}".encode()).hexdigest()
                        
                        cursor.execute(
                            """INSERT INTO users 
                               (id, email, password_hash, full_name, is_active, is_verified, role, created_at, updated_at) 
                               VALUES (%s, %s, %s, %s, TRUE, TRUE, 'admin', NOW(), NOW()) 
                               RETURNING *""", 
                            (user_id, email, default_password_hash, email.split('@')[0])
                        )
                        conn.commit()
                        user = cursor.fetchone()
                        print(f"Created new user: {user['email']}")
                    except Exception as insert_error:
                        print(f"Error creating user: {str(insert_error)}")
                        # Vẫn trả về valid=True để cho phép đăng nhập
                        return {
                            "valid": True,
                            "user": {
                                "id": user_id,
                                "email": email,
                                "fullname": email.split('@')[0],
                                "is_active": True,
                                "is_verified": True,
                                "role": "admin"
                            }
                        }
                
                if not user["is_active"]:
                    return {"valid": False, "message": "Inactive user"}
                
                # Trả về kết quả xác thực thành công
                return {
                    "valid": True,
                    "user": {
                        "id": user["id"],
                        "email": user["email"],
                        "fullname": user["full_name"],
                        "is_active": user["is_active"],
                        "is_verified": user["is_verified"],
                        "role": user["role"]
                    }
                }
                
            except Exception as e:
                return {"valid": False, "message": f"Database error: {str(e)}"}
            
            finally:
                if conn:
                    conn.close()
                    
        except PyJWTError:
            return {"valid": False, "message": "Invalid token"}
        except Exception as e:
            return {"valid": False, "message": f"Verification error: {str(e)}"}
