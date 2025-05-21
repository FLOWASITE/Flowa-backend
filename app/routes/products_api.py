from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.controllers.auth_controller import AuthController
from app.utils.database import get_db_connection
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/products", tags=["products"])
auth_controller = AuthController()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_products(
    brand_id: Optional[str] = Query(None, description="Filter products by brand ID"),
    current_user = Depends(auth_controller.get_current_user)
):
    """
    Get all products for the authenticated user, optionally filtered by brand.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Xây dựng query dựa trên filter
        query = """
            SELECT p.*, b.name as brand_name 
            FROM products p
            JOIN brands b ON p.brand_id = b.id
            WHERE p.user_id = %s
        """
        params = [current_user["id"]]
        
        if brand_id:
            query += " AND p.brand_id = %s"
            params.append(brand_id)
            
        query += " ORDER BY p.created_at DESC"
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        
        return [
            {
                "id": product["id"],
                "name": product["name"],
                "description": product["description"],
                "brand_id": product["brand_id"],
                "brand_name": product["brand_name"],
                "price": product["price"],
                "image_url": product["image_url"],
                "features": product["features"],
                "category": product["category"],
                "tags": product["tags"],
                "is_active": product["is_active"],
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

@router.get("/{product_id}", response_model=Dict[str, Any])
async def get_product_detail(product_id: str, current_user = Depends(auth_controller.get_current_user)):
    """
    Get detail of a specific product.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lấy thông tin product
        cursor.execute(
            """SELECT p.*, b.name as brand_name 
               FROM products p
               JOIN brands b ON p.brand_id = b.id
               WHERE p.id = %s AND p.user_id = %s""", 
            (product_id, current_user["id"])
        )
        
        product = cursor.fetchone()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "brand_id": product["brand_id"],
            "brand_name": product["brand_name"],
            "price": product["price"],
            "image_url": product["image_url"],
            "features": product["features"],
            "category": product["category"],
            "tags": product["tags"],
            "is_active": product["is_active"],
            "created_at": product["created_at"],
            "updated_at": product["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
