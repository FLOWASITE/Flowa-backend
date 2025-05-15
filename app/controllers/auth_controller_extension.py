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
                    return {"valid": False, "message": "User not found"}
                
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
