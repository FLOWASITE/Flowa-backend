from fastapi import APIRouter, HTTPException, Query
from app.utils.database import get_db_connection
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/products-simple", tags=["products-simple"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_products(brand_id: Optional[str] = Query(None, description="Filter products by brand ID")):
    """
    Get all products without authentication, optionally filtered by brand.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Xây dựng query dựa trên filter
        query = """
            SELECT p.*, b.name as brand_name 
            FROM products p
            LEFT JOIN brands b ON p.brand_id = b.id
        """
        params = []
        
        if brand_id:
            query += " WHERE p.brand_id = %s"
            params.append(brand_id)
            
        query += " ORDER BY p.created_at DESC"
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        
        if not products:
            # Nếu không có products, trả về danh sách rỗng
            return []
        
        return [
            {
                "id": product["id"],
                "name": product["name"],
                "description": product["description"],
                "brand_id": product["brand_id"],
                "brand_name": product.get("brand_name"),
                "price": product.get("price"),
                "image_url": product.get("image_url"),
                "features": product.get("features"),
                "category": product.get("category"),
                "tags": product.get("tags"),
                "is_active": product.get("is_active", True),
                "created_at": product["created_at"],
                "updated_at": product["updated_at"]
            }
            for product in products
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.get("/check", response_model=Dict[str, Any])
async def check_products_table():
    """
    Check if products table exists and return its structure.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Kiểm tra bảng products có tồn tại không
        cursor.execute(
            """SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'products'
            )"""
        )
        
        table_exists = cursor.fetchone()["exists"]
        
        if not table_exists:
            return {"exists": False, "message": "Products table does not exist"}
        
        # Lấy cấu trúc bảng products
        cursor.execute(
            """SELECT column_name, data_type 
               FROM information_schema.columns 
               WHERE table_name = 'products'"""
        )
        
        columns = cursor.fetchall()
        
        # Đếm số lượng products
        cursor.execute("SELECT COUNT(*) FROM products")
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
