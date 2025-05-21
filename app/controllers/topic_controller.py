from fastapi import HTTPException, Depends, status
from app.models.topic import TopicCreate, TopicUpdate, Topic, TopicStatus, TopicGenerateRequest
from app.utils.database import get_db_connection
from datetime import datetime
import uuid
import requests
import json
import os
from config.settings import AI_API_URL, AI_API_KEY

class TopicController:
    async def create_topic(self, topic_data: TopicCreate, user_id: str):
        """Create a new topic for the user."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify that the brand exists and belongs to the user
            cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (topic_data.brand_id, user_id))
            brand = cursor.fetchone()
            
            if not brand:
                raise HTTPException(status_code=404, detail="Brand not found or does not belong to user")
            
            # If product_id is provided, verify that it exists and belongs to the user
            if topic_data.product_id:
                cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (topic_data.product_id, user_id))
                product = cursor.fetchone()
                
                if not product:
                    raise HTTPException(status_code=404, detail="Product not found or does not belong to user")
            
            topic_id = str(uuid.uuid4())
            now = datetime.now()
            
            cursor.execute(
                """INSERT INTO topics 
                   (id, title, description, brand_id, product_id, target_audience, category, user_id, status, created_at, updated_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                   RETURNING *""", 
                (
                    topic_id, 
                    topic_data.title, 
                    topic_data.description, 
                    topic_data.brand_id, 
                    topic_data.product_id, 
                    topic_data.target_audience, 
                    topic_data.category, 
                    user_id, 
                    TopicStatus.PENDING.value, 
                    now, 
                    now
                )
            )
            
            topic = cursor.fetchone()
            conn.commit()
            
            return {
                "id": topic["id"],
                "title": topic["title"],
                "description": topic["description"],
                "brand_id": topic["brand_id"],
                "product_id": topic["product_id"],
                "target_audience": topic["target_audience"],
                "category": topic["category"],
                "user_id": topic["user_id"],
                "status": topic["status"],
                "created_at": topic["created_at"],
                "updated_at": topic["updated_at"]
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
    
    async def get_topics(self, user_id: str, status: str = None, brand_id: str = None, product_id: str = None):
        """Get all topics for a user, optionally filtered by status, brand, or product."""
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
            params = [user_id]
            
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
                    "target_audience": topic["target_audience"],
                    "category": topic["category"],
                    "user_id": topic["user_id"],
                    "status": topic["status"],
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
    
    async def get_topic(self, topic_id: str, user_id: str):
        """Get a specific topic by ID."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT t.*, b.name as brand_name, p.name as product_name 
                   FROM topics t
                   LEFT JOIN brands b ON t.brand_id = b.id
                   LEFT JOIN products p ON t.product_id = p.id
                   WHERE t.id = %s AND t.user_id = %s""", 
                (topic_id, user_id)
            )
            topic = cursor.fetchone()
            
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            
            return {
                "id": topic["id"],
                "title": topic["title"],
                "description": topic["description"],
                "brand_id": topic["brand_id"],
                "brand_name": topic["brand_name"],
                "product_id": topic["product_id"],
                "product_name": topic["product_name"],
                "target_audience": topic["target_audience"],
                "category": topic["category"],
                "user_id": topic["user_id"],
                "status": topic["status"],
                "created_at": topic["created_at"],
                "updated_at": topic["updated_at"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    async def update_topic(self, topic_id: str, topic_data: TopicUpdate, user_id: str):
        """Update a topic."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if topic exists and belongs to user
            cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, user_id))
            existing_topic = cursor.fetchone()
            
            if not existing_topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            
            # Build update query dynamically based on provided fields
            update_fields = []
            params = []
            
            if topic_data.title is not None:
                update_fields.append("title = %s")
                params.append(topic_data.title)
                
            if topic_data.description is not None:
                update_fields.append("description = %s")
                params.append(topic_data.description)
                
            if topic_data.status is not None:
                update_fields.append("status = %s")
                params.append(topic_data.status.value)
                
            if topic_data.target_audience is not None:
                update_fields.append("target_audience = %s")
                params.append(topic_data.target_audience)
                
            if topic_data.category is not None:
                update_fields.append("category = %s")
                params.append(topic_data.category)
            
            # Add updated_at
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            
            # Add topic_id and user_id to params
            params.append(topic_id)
            params.append(user_id)
            
            # Execute update if there are fields to update
            if update_fields:
                query = f"""
                    UPDATE topics 
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING *
                """
                
                cursor.execute(query, params)
                updated_topic = cursor.fetchone()
                conn.commit()
                
                # Get brand and product names
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
                    "target_audience": updated_topic["target_audience"],
                    "category": updated_topic["category"],
                    "user_id": updated_topic["user_id"],
                    "status": updated_topic["status"],
                    "created_at": updated_topic["created_at"],
                    "updated_at": updated_topic["updated_at"]
                }
            
            # If no fields to update, return existing topic
            # Get brand and product names
            cursor.execute("SELECT name FROM brands WHERE id = %s", (existing_topic["brand_id"],))
            brand = cursor.fetchone()
            brand_name = brand["name"] if brand else None
            
            product_name = None
            if existing_topic["product_id"]:
                cursor.execute("SELECT name FROM products WHERE id = %s", (existing_topic["product_id"],))
                product = cursor.fetchone()
                product_name = product["name"] if product else None
            
            return {
                "id": existing_topic["id"],
                "title": existing_topic["title"],
                "description": existing_topic["description"],
                "brand_id": existing_topic["brand_id"],
                "brand_name": brand_name,
                "product_id": existing_topic["product_id"],
                "product_name": product_name,
                "target_audience": existing_topic["target_audience"],
                "category": existing_topic["category"],
                "user_id": existing_topic["user_id"],
                "status": existing_topic["status"],
                "created_at": existing_topic["created_at"],
                "updated_at": existing_topic["updated_at"]
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
    
    async def delete_topic(self, topic_id: str, user_id: str):
        """Delete a topic."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if topic exists and belongs to user
            cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, user_id))
            existing_topic = cursor.fetchone()
            
            if not existing_topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            
            # Delete topic
            cursor.execute("DELETE FROM topics WHERE id = %s AND user_id = %s", (topic_id, user_id))
            conn.commit()
            
            return {"message": "Topic deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    async def approve_topic(self, topic_id: str, user_id: str):
        """Approve a topic."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if topic exists and belongs to user
            cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, user_id))
            existing_topic = cursor.fetchone()
            
            if not existing_topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            
            # Update topic status to approved
            now = datetime.now()
            cursor.execute(
                """UPDATE topics 
                   SET status = %s, updated_at = %s
                   WHERE id = %s AND user_id = %s
                   RETURNING *""", 
                (TopicStatus.APPROVED.value, now, topic_id, user_id)
            )
            
            updated_topic = cursor.fetchone()
            if not updated_topic:
                raise HTTPException(status_code=404, detail="Failed to update topic")
                
            conn.commit()
            
            # Get brand and product names
            brand_name = None
            if updated_topic["brand_id"]:
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
                "target_audience": updated_topic["target_audience"],
                "category": updated_topic["category"],
                "user_id": updated_topic["user_id"],
                "status": updated_topic["status"],
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
    
    async def reject_topic(self, topic_id: str, user_id: str):
        """Reject a topic."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if topic exists and belongs to user
            cursor.execute("SELECT * FROM topics WHERE id = %s AND user_id = %s", (topic_id, user_id))
            existing_topic = cursor.fetchone()
            
            if not existing_topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            
            # Update topic status to rejected
            now = datetime.now()
            cursor.execute(
                """UPDATE topics 
                   SET status = %s, updated_at = %s
                   WHERE id = %s AND user_id = %s
                   RETURNING *""", 
                (TopicStatus.REJECTED.value, now, topic_id, user_id)
            )
            
            updated_topic = cursor.fetchone()
            if not updated_topic:
                raise HTTPException(status_code=404, detail="Failed to update topic")
                
            conn.commit()
            
            # Get brand and product names
            brand_name = None
            if updated_topic["brand_id"]:
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
                "target_audience": updated_topic["target_audience"],
                "category": updated_topic["category"],
                "user_id": updated_topic["user_id"],
                "status": updated_topic["status"],
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
    
    async def generate_topics(self, request_data: TopicGenerateRequest, user_id: str):
        """Generate topics using AI API."""
        conn = None
        try:
            # Verify that the brand exists and belongs to the user
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM brands WHERE id = %s AND user_id = %s", (request_data.brand_id, user_id))
            brand = cursor.fetchone()
            
            if not brand:
                raise HTTPException(status_code=404, detail="Brand not found or does not belong to user")
            
            # If product_id is provided, verify that it exists and belongs to the user
            if request_data.product_id:
                cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (request_data.product_id, user_id))
                product = cursor.fetchone()
                
                if not product:
                    raise HTTPException(status_code=404, detail="Product not found or does not belong to user")
            
            # Get previous topics if requested
            previous_topics = []
            if request_data.use_previous_topics:
                cursor.execute(
                    """SELECT * FROM topics 
                       WHERE user_id = %s AND status = %s 
                       ORDER BY created_at DESC 
                       LIMIT %s""", 
                    (user_id, TopicStatus.APPROVED.value, request_data.max_previous_topics)
                )
                previous_topics = cursor.fetchall()
            
            # Prepare data for AI API
            ai_request_data = {
                "prompt": request_data.prompt,
                "brand": {
                    "id": brand["id"],
                    "name": brand["name"],
                    "description": brand["description"]
                },
                "count": request_data.count
            }
            
            # Add product if provided
            if request_data.product_id and product:
                ai_request_data["product"] = {
                    "id": product["id"],
                    "name": product["name"],
                    "description": product["description"],
                    "category": product["category"]
                }
            
            # Add previous topics if available
            if previous_topics:
                ai_request_data["previous_topics"] = [
                    {
                        "id": topic["id"],
                        "title": topic["title"],
                        "description": topic["description"],
                        "target_audience": topic["target_audience"],
                        "category": topic["category"]
                    }
                    for topic in previous_topics
                ]
            
            # Call AI API to generate topics
            # In a real implementation, this would be a call to an external AI service
            # For now, we'll simulate it with some mock data
            
            # Uncomment this in a real implementation
            # headers = {
            #     "Content-Type": "application/json",
            #     "Authorization": f"Bearer {AI_API_KEY}"
            # }
            # response = requests.post(AI_API_URL, json=ai_request_data, headers=headers)
            # if response.status_code != 200:
            #     raise HTTPException(status_code=response.status_code, detail=f"AI API error: {response.text}")
            # ai_response = response.json()
            
            # Mock AI response for demonstration
            ai_response = {
                "topics": [
                    {
                        "title": f"Topic about {brand['name']} #{i+1}",
                        "description": f"Description for topic {i+1}",
                        "target_audience": "General audience",
                        "category": "product_highlight",
                        "brand_id": brand["id"],
                        "product_id": request_data.product_id
                    }
                    for i in range(request_data.count)
                ]
            }
            
            # Save generated topics to database
            generated_topics = []
            for topic_data in ai_response["topics"]:
                topic_id = str(uuid.uuid4())
                now = datetime.now()
                
                cursor.execute(
                    """INSERT INTO topics 
                       (id, title, description, brand_id, product_id, target_audience, category, user_id, status, created_at, updated_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                       RETURNING *""", 
                    (
                        topic_id, 
                        topic_data["title"], 
                        topic_data["description"], 
                        topic_data["brand_id"], 
                        topic_data.get("product_id"), 
                        topic_data.get("target_audience"), 
                        topic_data.get("category"), 
                        user_id, 
                        TopicStatus.PENDING.value, 
                        now, 
                        now
                    )
                )
                
                topic = cursor.fetchone()
                generated_topics.append({
                    "id": topic["id"],
                    "title": topic["title"],
                    "description": topic["description"],
                    "brand_id": topic["brand_id"],
                    "product_id": topic["product_id"],
                    "target_audience": topic["target_audience"],
                    "category": topic["category"],
                    "user_id": topic["user_id"],
                    "status": topic["status"],
                    "created_at": topic["created_at"],
                    "updated_at": topic["updated_at"]
                })
            
            conn.commit()
            
            return {"topics": generated_topics}
            
        except HTTPException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error generating topics: {str(e)}")
        finally:
            if conn:
                conn.close()
