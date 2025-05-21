from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.controllers.auth_controller import AuthController
from app.utils.database import get_db_connection
from app.services.rag_service import RAGService
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/topics", tags=["topics"])
auth_controller = AuthController()
rag_service = RAGService()

class PendingTopicData(BaseModel):
    title: str
    description: Optional[str] = None
    brand_id: str
    product_id: Optional[str] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    keywords: Optional[List[str]] = Field(default_factory=list)
    content_goals: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None
    prompt: Optional[str] = None
    status: Optional[str] = 'approved'

@router.post("/approve_pending", response_model=Dict[str, Any])
async def approve_pending_topic(topic_data: PendingTopicData, current_user = Depends(auth_controller.get_current_user)):
    print(f"Received pending topic data for approval: {topic_data.model_dump_json()}")
    
    # Process brand_id
    try:
        brand_id = uuid.UUID(topic_data.brand_id) if topic_data.brand_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid brand_id format: {topic_data.brand_id}. Must be a valid UUID.")
    
    # Process product_id
    product_id = None
    if topic_data.product_id and topic_data.product_id not in ["null", "undefined"]:
        try:
            # Try to convert to UUID
            product_id = uuid.UUID(topic_data.product_id)
        except ValueError:
            # If it's a numeric ID, we'll handle it differently
            if topic_data.product_id.isdigit():
                # For numeric IDs, we need to look up the corresponding UUID in the database
                product_conn = None
                try:
                    product_conn = get_db_connection()
                    product_cursor = product_conn.cursor()
                    # Try to find a product with this numeric ID or name
                    product_cursor.execute("SELECT id FROM products WHERE name = %s OR id::text = %s", 
                                  (topic_data.product_id, topic_data.product_id))
                    product = product_cursor.fetchone()
                    if product:
                        product_id = product["id"]
                except Exception as e:
                    print(f"Error looking up product: {e}")
                finally:
                    if product_conn:
                        product_conn.close()
    
    # Now insert the topic with a new connection
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        new_topic_id = uuid.uuid4()
        now = datetime.now()
        user_id = current_user["id"]

        try:
            # Convert UUID objects to strings before inserting into the database
            topic_id_str = str(new_topic_id)
            brand_id_str = str(brand_id) if brand_id else None
            product_id_str = str(product_id) if product_id else None
            
            print(f"Inserting topic with ID: {topic_id_str}, brand_id: {brand_id_str}, product_id: {product_id_str}")
            
            cursor.execute(
                """INSERT INTO topics 
                   (id, title, description, brand_id, product_id, user_id, prompt, status, target_audience, keywords, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    topic_id_str,
                    topic_data.title,
                    topic_data.description,
                    brand_id_str, 
                    product_id_str, 
                    user_id,
                    topic_data.prompt,
                    'approved', 
                    topic_data.target_audience,
                    topic_data.keywords, 
                    now,
                    now
                )
            )
            
            inserted_topic = cursor.fetchone()
            if not inserted_topic:
                conn.rollback()
                raise HTTPException(status_code=500, detail="Failed to save and approve pending topic")

            # Get brand name
            brand_name = None
            if inserted_topic["brand_id"]:
                cursor.execute("SELECT name FROM brands WHERE id = %s", (inserted_topic["brand_id"],))
                brand = cursor.fetchone()
                brand_name = brand["name"] if brand else None
            
            # Get product name
            product_name = None
            if inserted_topic["product_id"]:
                cursor.execute("SELECT name FROM products WHERE id = %s", (inserted_topic["product_id"],))
                product = cursor.fetchone()
                product_name = product["name"] if product else None

            # Commit the transaction
            conn.commit()

            # Return the response
            return {
                "id": str(inserted_topic["id"]),
                "title": inserted_topic["title"],
                "description": inserted_topic["description"],
                "brand_id": str(inserted_topic["brand_id"]) if inserted_topic["brand_id"] else None,
                "brand_name": brand_name,
                "product_id": str(inserted_topic["product_id"]) if inserted_topic["product_id"] else None,
                "product_name": product_name,
                "user_id": str(inserted_topic["user_id"]),
                "prompt": inserted_topic["prompt"],
                "category": inserted_topic["category"],
                "status": inserted_topic["status"],
                "keywords": inserted_topic["keywords"],
                "target_audience": inserted_topic["target_audience"],
                "created_at": inserted_topic["created_at"].isoformat(),
                "updated_at": inserted_topic["updated_at"].isoformat()
            }
        except Exception as inner_e:
            conn.rollback()
            print(f"Inner exception in approve_pending_topic: {str(inner_e)}")
            raise inner_e

    except HTTPException as http_ex:
        print(f"HTTP exception in approve_pending_topic: {str(http_ex)}")
        raise
    except Exception as e:
        print(f"Error in approve_pending_topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as close_e:
                print(f"Error closing connection: {str(close_e)}")
                pass

@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_topics(
    status: Optional[str] = Query(None, description="Filter topics by status (pending, approved, rejected, completed)"),
    brand_id: Optional[str] = Query(None, description="Filter topics by brand ID"),
    product_id: Optional[str] = Query(None, description="Filter topics by product ID"),
    current_user = Depends(auth_controller.get_current_user)
):
    """
    Get all topics for the authenticated user, optionally filtered by status, brand, or product.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT t.*, b.name as brand_name, p.name as product_name 
            FROM topics t
            LEFT JOIN brands b ON t.brand_id = b.id
            LEFT JOIN products p ON t.product_id = p.id
            WHERE t.user_id = %s
        """
        params = [current_user["id"]]
        
        if status:
            query += " AND t.status = %s"
            params.append(status)
            
        if brand_id:
            query += " AND t.brand_id = %s"
            params.append(brand_id)
            
        if product_id:
            query += " AND t.product_id = %s"
            params.append(product_id)
            
        query += " ORDER BY t.created_at DESC"
        
        cursor.execute(query, params)
        topics = cursor.fetchall()
        
        return [
            {
                "id": topic["id"],
                "title": topic["title"],
                "description": topic["description"],
                "brand_id": topic["brand_id"],
                "brand_name": topic["brand_name"],
                "product_id": topic["product_id"],
                "product_name": topic["product_name"],
                "user_id": topic["user_id"],
                "prompt": topic["prompt"],
                "category": topic["category"],
                "status": topic["status"],
                "keywords": topic["keywords"],
                "relevance_score": topic["relevance_score"],
                "target_audience": topic["target_audience"],
                "created_at": topic["created_at"],
                "updated_at": topic["updated_at"]
            }
            for topic in topics
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/generate", response_model=Dict[str, Any])
async def generate_topics(
    brand_id: str = Query(..., description="Brand ID to generate topics for"),
    product_id: Optional[str] = Query(None, description="Product ID to generate topics for"),
    prompt: str = Query(..., description="Prompt for topic generation"),
    count: int = Query(5, description="Number of topics to generate"),
    current_user = Depends(auth_controller.get_current_user)
):
    """
    Generate topics using RAG service.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (brand_id, current_user["id"]))
        brand = cursor.fetchone()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or does not belong to user")
        
        product = None
        if product_id:
            cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, current_user["id"]))
            product = cursor.fetchone()
            
            if not product:
                raise HTTPException(status_code=404, detail="Product not found or does not belong to user")
        
        cursor.execute(
            """SELECT * FROM topics 
               WHERE user_id = %s AND status = 'approved' 
               ORDER BY created_at DESC 
               LIMIT 5""", 
            (current_user["id"],)
        )
        previous_topics = cursor.fetchall()
        
        brand_info = f"Brand: {brand['name']}\nDescription: {brand['description']}\nIndustry: {brand['industry']}"
        
        product_context = ""
        if product:
            product_context = f"Product: {product['name']}\nDescription: {product['description']}\nCategory: {product['category']}\nFeatures: {product['features']}"
        
        if product:
            generated_topics = rag_service.generate_topics_for_brand_product(
                product_id=product_id,
                brand_id=brand_id,
                count=count
            )
        else:
            topic_generator = rag_service.create_multiple_topics_generator(
                product_context=prompt,
                brand_info=brand_info,
                count=count
            )
            generated_topics = topic_generator()
        
        saved_topics = []
        for topic_data in generated_topics.get("topics", []):
            topic_id = str(uuid.uuid4())
            now = datetime.now()
            
            title = topic_data.get("title", "")
            description = topic_data.get("description", "")
            target_audience = topic_data.get("target_audience", "")
            category = topic_data.get("category", "")
            
            cursor.execute(
                """INSERT INTO topics 
                   (id, title, description, brand_id, product_id, user_id, prompt, category, status, target_audience, created_at, updated_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                   RETURNING *""", 
                (
                    topic_id, 
                    title, 
                    description, 
                    brand_id, 
                    product_id, 
                    current_user["id"], 
                    prompt,
                    category,
                    "pending", 
                    target_audience,
                    now, 
                    now
                )
            )
            
            topic = cursor.fetchone()
            saved_topics.append({
                "id": topic["id"],
                "title": topic["title"],
                "description": topic["description"],
                "brand_id": topic["brand_id"],
                "product_id": topic["product_id"],
                "user_id": topic["user_id"],
                "prompt": topic["prompt"],
                "category": topic["category"],
                "status": topic["status"],
                "target_audience": topic["target_audience"],
                "created_at": topic["created_at"],
                "updated_at": topic["updated_at"]
            })
        
        conn.commit()
        
        return {"topics": saved_topics}
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating topics: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/approve_by_numeric_id/{topic_id}", response_model=Dict[str, Any])
async def approve_topic_by_numeric_id(topic_id: str, current_user = Depends(auth_controller.get_current_user)):
    """
    Approve a topic using numeric ID.
    """
    conn = None
    try:
        try:
            uuid_obj = uuid.UUID(topic_id)
            topic_id = str(uuid_obj)  
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid topic ID format: '{topic_id}'. Must be a valid UUID.")
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, current_user["id"]))
        existing_topic = cursor.fetchone()
        
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        now = datetime.now()
        cursor.execute(
            """UPDATE topics 
               SET status = 'approved', updated_at = %s
               WHERE id = %s AND user_id = %s
               RETURNING *""", 
            (now, topic_id, current_user["id"])
        )
        
        updated_topic = cursor.fetchone()
        if not updated_topic:
            raise HTTPException(status_code=404, detail="Failed to update topic")
            
        conn.commit()
        
        cursor.execute("SELECT name FROM brands WHERE id = %s", (updated_topic["brand_id"],))
        brand = cursor.fetchone()
        brand_name = brand["name"] if brand else None
        
        product_name = None
        if updated_topic["product_id"]:
            cursor.execute("SELECT name FROM products WHERE id = %s", (updated_topic["product_id"],))
            product = cursor.fetchone()
            product_name = product["name"] if product else None
        
        return {
            "id": updated_topic["id"],
            "title": updated_topic["title"],
            "description": updated_topic["description"],
            "brand_id": updated_topic["brand_id"],
            "brand_name": brand_name,
            "product_id": updated_topic["product_id"],
            "product_name": product_name,
            "user_id": updated_topic["user_id"],
            "prompt": updated_topic["prompt"],
            "category": updated_topic["category"],
            "status": updated_topic["status"],
            "target_audience": updated_topic["target_audience"],
            "created_at": updated_topic["created_at"],
            "updated_at": updated_topic["updated_at"]
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

@router.post("/{topic_id}/approve", response_model=Dict[str, Any])
async def approve_topic(topic_id: str, current_user = Depends(auth_controller.get_current_user)):
    """
    Approve a topic.
    """
    conn = None
    try:
        try:
            uuid_obj = uuid.UUID(topic_id)
            topic_id = str(uuid_obj)  
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid topic ID format. Must be a valid UUID.")
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, current_user["id"]))
        existing_topic = cursor.fetchone()
        
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        now = datetime.now()
        cursor.execute(
            """UPDATE topics 
               SET status = 'approved', updated_at = %s
               WHERE id = %s AND user_id = %s
               RETURNING *""", 
            (now, topic_id, current_user["id"])
        )
        
        updated_topic = cursor.fetchone()
        if not updated_topic:
            raise HTTPException(status_code=404, detail="Failed to update topic")
            
        conn.commit()
        
        cursor.execute("SELECT name FROM brands WHERE id = %s", (updated_topic["brand_id"],))
        brand = cursor.fetchone()
        brand_name = brand["name"] if brand else None
        
        product_name = None
        if updated_topic["product_id"]:
            cursor.execute("SELECT name FROM products WHERE id = %s", (updated_topic["product_id"],))
            product = cursor.fetchone()
            product_name = product["name"] if product else None
        
        return {
            "id": updated_topic["id"],
            "title": updated_topic["title"],
            "description": updated_topic["description"],
            "brand_id": updated_topic["brand_id"],
            "brand_name": brand_name,
            "product_id": updated_topic["product_id"],
            "product_name": product_name,
            "user_id": updated_topic["user_id"],
            "prompt": updated_topic["prompt"],
            "category": updated_topic["category"],
            "status": updated_topic["status"],
            "target_audience": updated_topic["target_audience"],
            "created_at": updated_topic["created_at"],
            "updated_at": updated_topic["updated_at"]
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

@router.post("/{topic_id}/reject", response_model=Dict[str, Any])
async def reject_topic(topic_id: str, current_user = Depends(auth_controller.get_current_user)):
    """
    Reject a topic.
    """
    conn = None
    try:
        try:
            uuid_obj = uuid.UUID(topic_id)
            topic_id = str(uuid_obj)  
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid topic ID format. Must be a valid UUID.")
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, current_user["id"]))
        existing_topic = cursor.fetchone()
        
        if not existing_topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        now = datetime.now()
        cursor.execute(
            """UPDATE topics 
               SET status = 'rejected', updated_at = %s
               WHERE id = %s AND user_id = %s
               RETURNING *""", 
            (now, topic_id, current_user["id"])
        )
        
        updated_topic = cursor.fetchone()
        if not updated_topic:
            raise HTTPException(status_code=404, detail="Failed to update topic")
            
        conn.commit()
        
        cursor.execute("SELECT name FROM brands WHERE id = %s", (updated_topic["brand_id"],))
        brand = cursor.fetchone()
        brand_name = brand["name"] if brand else None
        
        product_name = None
        if updated_topic["product_id"]:
            cursor.execute("SELECT name FROM products WHERE id = %s", (updated_topic["product_id"],))
            product = cursor.fetchone()
            product_name = product["name"] if product else None
        
        return {
            "id": updated_topic["id"],
            "title": updated_topic["title"],
            "description": updated_topic["description"],
            "brand_id": updated_topic["brand_id"],
            "brand_name": brand_name,
            "product_id": updated_topic["product_id"],
            "product_name": product_name,
            "user_id": updated_topic["user_id"],
            "prompt": updated_topic["prompt"],
            "category": updated_topic["category"],
            "status": updated_topic["status"],
            "target_audience": updated_topic["target_audience"],
            "created_at": updated_topic["created_at"],
            "updated_at": updated_topic["updated_at"]
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
