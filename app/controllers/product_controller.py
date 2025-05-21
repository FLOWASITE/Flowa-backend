from fastapi import HTTPException, Depends, status
from app.models.product import ProductCreate, ProductUpdate, Product
from app.utils.database import get_db_connection
from datetime import datetime
import uuid

class ProductController:
    async def create_product(self, product_data: ProductCreate, user_id: str):
        """Create a new product for the user."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify that the brand exists and belongs to the user
            cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (product_data.brand_id, user_id))
            brand = cursor.fetchone()
            
            if not brand:
                raise HTTPException(status_code=404, detail="Brand not found or does not belong to user")
            
            product_id = str(uuid.uuid4())
            now = datetime.now()
            
            cursor.execute(
                """INSERT INTO products 
                   (id, name, description, brand_id, image_url, category, price, user_id, created_at, updated_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                   RETURNING *""", 
                (
                    product_id, 
                    product_data.name, 
                    product_data.description, 
                    product_data.brand_id, 
                    product_data.image_url, 
                    product_data.category, 
                    product_data.price, 
                    user_id, 
                    now, 
                    now
                )
            )
            
            product = cursor.fetchone()
            conn.commit()
            
            return {
                "id": product["id"],
                "name": product["name"],
                "description": product["description"],
                "brand_id": product["brand_id"],
                "image_url": product["image_url"],
                "category": product["category"],
                "price": product["price"],
                "user_id": product["user_id"],
                "created_at": product["created_at"],
                "updated_at": product["updated_at"]
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
    
    async def get_products(self, user_id: str, brand_id: str = None):
        """Get all products for a user, optionally filtered by brand."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if brand_id:
                cursor.execute(
                    """SELECT p.*, b.name as brand_name 
                       FROM products p
                       JOIN brands b ON p.brand_id = b.id
                       WHERE p.user_id = %s AND p.brand_id = %s 
                       ORDER BY p.created_at DESC""", 
                    (user_id, brand_id)
                )
            else:
                cursor.execute(
                    """SELECT p.*, b.name as brand_name 
                       FROM products p
                       JOIN brands b ON p.brand_id = b.id
                       WHERE p.user_id = %s 
                       ORDER BY p.created_at DESC""", 
                    (user_id,)
                )
                
            products = cursor.fetchall()
            
            return [
                {
                    "id": product["id"],
                    "name": product["name"],
                    "description": product["description"],
                    "brand_id": product["brand_id"],
                    "brand_name": product["brand_name"],
                    "image_url": product["image_url"],
                    "category": product["category"],
                    "price": product["price"],
                    "user_id": product["user_id"],
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
    
    async def get_product(self, product_id: str, user_id: str):
        """Get a specific product by ID."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT p.*, b.name as brand_name 
                   FROM products p
                   JOIN brands b ON p.brand_id = b.id
                   WHERE p.id = %s AND p.user_id = %s""", 
                (product_id, user_id)
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
                "image_url": product["image_url"],
                "category": product["category"],
                "price": product["price"],
                "user_id": product["user_id"],
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
    
    async def update_product(self, product_id: str, product_data: ProductUpdate, user_id: str):
        """Update a product."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if product exists and belongs to user
            cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, user_id))
            existing_product = cursor.fetchone()
            
            if not existing_product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # If brand_id is being updated, verify that the new brand exists and belongs to the user
            if product_data.brand_id is not None and product_data.brand_id != existing_product["brand_id"]:
                cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (product_data.brand_id, user_id))
                brand = cursor.fetchone()
                
                if not brand:
                    raise HTTPException(status_code=404, detail="Brand not found or does not belong to user")
            
            # Build update query dynamically based on provided fields
            update_fields = []
            params = []
            
            if product_data.name is not None:
                update_fields.append("name = %s")
                params.append(product_data.name)
                
            if product_data.description is not None:
                update_fields.append("description = %s")
                params.append(product_data.description)
                
            if product_data.brand_id is not None:
                update_fields.append("brand_id = %s")
                params.append(product_data.brand_id)
                
            if product_data.image_url is not None:
                update_fields.append("image_url = %s")
                params.append(product_data.image_url)
                
            if product_data.category is not None:
                update_fields.append("category = %s")
                params.append(product_data.category)
                
            if product_data.price is not None:
                update_fields.append("price = %s")
                params.append(product_data.price)
            
            # Add updated_at
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            
            # Add product_id and user_id to params
            params.append(product_id)
            params.append(user_id)
            
            # Execute update if there are fields to update
            if update_fields:
                query = f"""
                    UPDATE products 
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING *
                """
                
                cursor.execute(query, params)
                updated_product = cursor.fetchone()
                conn.commit()
                
                # Get brand name
                cursor.execute("SELECT name FROM brands WHERE id = %s", (updated_product["brand_id"],))
                brand = cursor.fetchone()
                brand_name = brand["name"] if brand else None
                
                return {
                    "id": updated_product["id"],
                    "name": updated_product["name"],
                    "description": updated_product["description"],
                    "brand_id": updated_product["brand_id"],
                    "brand_name": brand_name,
                    "image_url": updated_product["image_url"],
                    "category": updated_product["category"],
                    "price": updated_product["price"],
                    "user_id": updated_product["user_id"],
                    "created_at": updated_product["created_at"],
                    "updated_at": updated_product["updated_at"]
                }
            
            # If no fields to update, return existing product
            # Get brand name
            cursor.execute("SELECT name FROM brands WHERE id = %s", (existing_product["brand_id"],))
            brand = cursor.fetchone()
            brand_name = brand["name"] if brand else None
            
            return {
                "id": existing_product["id"],
                "name": existing_product["name"],
                "description": existing_product["description"],
                "brand_id": existing_product["brand_id"],
                "brand_name": brand_name,
                "image_url": existing_product["image_url"],
                "category": existing_product["category"],
                "price": existing_product["price"],
                "user_id": existing_product["user_id"],
                "created_at": existing_product["created_at"],
                "updated_at": existing_product["updated_at"]
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
    
    async def delete_product(self, product_id: str, user_id: str):
        """Delete a product."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if product exists and belongs to user
            cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, user_id))
            existing_product = cursor.fetchone()
            
            if not existing_product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Delete product
            cursor.execute("DELETE FROM products WHERE id = %s AND user_id = %s", (product_id, user_id))
            conn.commit()
            
            return {"message": "Product deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
