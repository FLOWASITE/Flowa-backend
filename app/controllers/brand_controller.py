from fastapi import HTTPException, Depends, status
from app.models.brand import BrandCreate, BrandUpdate, Brand
from app.utils.database import get_db_connection
from datetime import datetime
import uuid

class BrandController:
    async def create_brand(self, brand_data: BrandCreate, user_id: str):
        """Create a new brand for the user."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            brand_id = str(uuid.uuid4())
            now = datetime.now()
            
            cursor.execute(
                """INSERT INTO brands 
                   (id, name, description, logo_url, website, user_id, created_at, updated_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                   RETURNING *""", 
                (
                    brand_id, 
                    brand_data.name, 
                    brand_data.description, 
                    brand_data.logo_url, 
                    brand_data.website, 
                    user_id, 
                    now, 
                    now
                )
            )
            
            brand = cursor.fetchone()
            conn.commit()
            
            return {
                "id": brand["id"],
                "name": brand["name"],
                "description": brand["description"],
                "logo_url": brand["logo_url"],
                "website": brand["website"],
                "user_id": brand["user_id"],
                "created_at": brand["created_at"],
                "updated_at": brand["updated_at"]
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    async def get_brands(self, user_id: str):
        """Get all brands for a user."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM brands WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            brands = cursor.fetchall()
            
            return [
                {
                    "id": brand["id"],
                    "name": brand["name"],
                    "description": brand["description"],
                    "logo_url": brand["logo_url"],
                    "website": brand["website"],
                    "user_id": brand["user_id"],
                    "created_at": brand["created_at"],
                    "updated_at": brand["updated_at"]
                }
                for brand in brands
            ]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    async def get_brand(self, brand_id: str, user_id: str):
        """Get a specific brand by ID."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (brand_id, user_id))
            brand = cursor.fetchone()
            
            if not brand:
                raise HTTPException(status_code=404, detail="Brand not found")
            
            return {
                "id": brand["id"],
                "name": brand["name"],
                "description": brand["description"],
                "logo_url": brand["logo_url"],
                "website": brand["website"],
                "user_id": brand["user_id"],
                "created_at": brand["created_at"],
                "updated_at": brand["updated_at"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    async def update_brand(self, brand_id: str, brand_data: BrandUpdate, user_id: str):
        """Update a brand."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if brand exists and belongs to user
            cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (brand_id, user_id))
            existing_brand = cursor.fetchone()
            
            if not existing_brand:
                raise HTTPException(status_code=404, detail="Brand not found")
            
            # Build update query dynamically based on provided fields
            update_fields = []
            params = []
            
            if brand_data.name is not None:
                update_fields.append("name = %s")
                params.append(brand_data.name)
                
            if brand_data.description is not None:
                update_fields.append("description = %s")
                params.append(brand_data.description)
                
            if brand_data.logo_url is not None:
                update_fields.append("logo_url = %s")
                params.append(brand_data.logo_url)
                
            if brand_data.website is not None:
                update_fields.append("website = %s")
                params.append(brand_data.website)
            
            # Add updated_at
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            
            # Add brand_id and user_id to params
            params.append(brand_id)
            params.append(user_id)
            
            # Execute update if there are fields to update
            if update_fields:
                query = f"""
                    UPDATE brands 
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING *
                """
                
                cursor.execute(query, params)
                updated_brand = cursor.fetchone()
                conn.commit()
                
                return {
                    "id": updated_brand["id"],
                    "name": updated_brand["name"],
                    "description": updated_brand["description"],
                    "logo_url": updated_brand["logo_url"],
                    "website": updated_brand["website"],
                    "user_id": updated_brand["user_id"],
                    "created_at": updated_brand["created_at"],
                    "updated_at": updated_brand["updated_at"]
                }
            
            # If no fields to update, return existing brand
            return {
                "id": existing_brand["id"],
                "name": existing_brand["name"],
                "description": existing_brand["description"],
                "logo_url": existing_brand["logo_url"],
                "website": existing_brand["website"],
                "user_id": existing_brand["user_id"],
                "created_at": existing_brand["created_at"],
                "updated_at": existing_brand["updated_at"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    async def delete_brand(self, brand_id: str, user_id: str):
        """Delete a brand."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if brand exists and belongs to user
            cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (brand_id, user_id))
            existing_brand = cursor.fetchone()
            
            if not existing_brand:
                raise HTTPException(status_code=404, detail="Brand not found")
            
            # Delete brand
            cursor.execute("DELETE FROM brands WHERE id = %s AND user_id = %s", (brand_id, user_id))
            conn.commit()
            
            return {"message": "Brand deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
