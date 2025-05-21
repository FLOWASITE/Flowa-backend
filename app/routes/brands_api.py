from fastapi import APIRouter, Depends, HTTPException, status
from app.controllers.auth_controller import AuthController
from app.utils.database import get_db_connection
from typing import List, Dict, Any

router = APIRouter(prefix="/api/brands", tags=["brands"])
auth_controller = AuthController()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_brands(current_user = Depends(auth_controller.get_current_user)):
    """
    Get all brands for the authenticated user.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lấy tất cả brands của user
        cursor.execute(
            """SELECT * FROM brands 
               WHERE user_id = %s 
               ORDER BY created_at DESC""", 
            (current_user["id"],)
        )
        
        brands = cursor.fetchall()
        
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

@router.get("/{brand_id}", response_model=Dict[str, Any])
async def get_brand_detail(brand_id: str, current_user = Depends(auth_controller.get_current_user)):
    """
    Get detail of a specific brand.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lấy thông tin brand
        cursor.execute(
            """SELECT * FROM brands 
               WHERE id = %s AND user_id = %s""", 
            (brand_id, current_user["id"])
        )
        
        brand = cursor.fetchone()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        return {
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
