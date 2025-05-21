from fastapi import APIRouter, HTTPException
from app.utils.database import get_db_connection
from typing import List, Dict, Any

router = APIRouter(prefix="/api/brands-simple", tags=["brands-simple"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_brands():
    """
    Get all brands without authentication.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lấy tất cả brands
        cursor.execute(
            """SELECT * FROM brands 
               ORDER BY created_at DESC"""
        )
        
        brands = cursor.fetchall()
        
        if not brands:
            # Nếu không có brands, trả về danh sách rỗng
            return []
        
        return [
            {
                "id": brand["id"],
                "name": brand["name"],
                "description": brand["description"],
                "logo_url": brand["logo_url"],
                "website": brand["website"],
                "industry": brand["industry"],
                "created_at": brand["created_at"],
                "updated_at": brand["updated_at"],
                "user_id": brand["user_id"]
            }
            for brand in brands
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.get("/check", response_model=Dict[str, Any])
async def check_brands_table():
    """
    Check if brands table exists and return its structure.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Kiểm tra bảng brands có tồn tại không
        cursor.execute(
            """SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'brands'
            )"""
        )
        
        table_exists = cursor.fetchone()["exists"]
        
        if not table_exists:
            return {"exists": False, "message": "Brands table does not exist"}
        
        # Lấy cấu trúc bảng brands
        cursor.execute(
            """SELECT column_name, data_type 
               FROM information_schema.columns 
               WHERE table_name = 'brands'"""
        )
        
        columns = cursor.fetchall()
        
        # Đếm số lượng brands
        cursor.execute("SELECT COUNT(*) FROM brands")
        count = cursor.fetchone()["count"]
        
        return {
            "exists": True,
            "count": count,
            "columns": [
                {"name": col["column_name"], "type": col["data_type"]}
                for col in columns
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
