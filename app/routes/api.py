from fastapi import APIRouter, Body, Query, HTTPException, Response, Depends
import os
import json
import base64
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from app.controllers.content_controller import ContentController
from app.utils.database import get_db_connection
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["content"])
content_controller = ContentController()

class TopicRequest(BaseModel):
    product_id: Optional[str] = None
    product_query: Optional[str] = None
    brand_id: Optional[str] = None
    prompt: Optional[str] = None
    count: int = 1
    use_previous_topics: bool = True
    max_previous_topics: int = 5

class ContentRequest(BaseModel):
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    with_related: bool = True

class BrandProductTopicsRequest(BaseModel):
    brand_id: str
    product_id: str
    count: int = 3
    save_to_db: bool = True

class MultipleTopic(BaseModel):
    product_id: str
    brand_id: str
    prompt: Optional[str] = None
    count: int = 5
    use_previous_topics: bool = True
    max_previous_topics: int = 5

class TopicApprovalRequest(BaseModel):
    topics: List[dict]
    save_to_db: bool = True

@router.post("/topics/generate")
async def generate_topic(request: TopicRequest):
    """
    Generate a topic based on product information.
    
    - Use product_id to base the topic on a specific product
    - Or use product_query to find relevant products to base the topic on
    - Optional brand_id to include brand context
    - Optional prompt to guide the topic generation
    - count to specify number of topics to generate (default: 1)
    - use_previous_topics to consider existing topics (default: True)
    - max_previous_topics to limit number of previous topics used (default: 5)
    """
    if not request.product_id and not request.product_query:
        raise HTTPException(status_code=400, detail="Either product_id or product_query must be provided")
    
    result = await content_controller.generate_topic(
        product_id=request.product_id,
        product_query=request.product_query,
        brand_id=request.brand_id,
        prompt=request.prompt,
        count=request.count,
        use_previous_topics=request.use_previous_topics,
        max_previous_topics=request.max_previous_topics
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.post("/brand-product/topics")
async def generate_brand_product_topics(request: BrandProductTopicsRequest):
    """
    Generate multiple topics for a product from a specific brand.
    
    - Requires brand_id and product_id
    - Optionally specify the number of topics to generate (default: 3)
    - Returns JSON format with topics and SEO information
    """
    result = await content_controller.generate_brand_product_topics(
        brand_id=request.brand_id,
        product_id=request.product_id,
        count=request.count,
        save_to_db=request.save_to_db
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.post("/content/generate")
async def generate_content(request: ContentRequest):
    """
    Generate content based on a topic.
    
    - Use topic_id to generate content based on an existing topic
    - Or use topic_title to specify a new topic
    - Set with_related to false to disable using related content as context
    """
    if not request.topic_id and not request.topic_title:
        raise HTTPException(status_code=400, detail="Either topic_id or topic_title must be provided")
    
    result = await content_controller.generate_content(
        topic_id=request.topic_id,
        topic_title=request.topic_title,
        with_related=request.with_related
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.get("/topics")
async def get_topics(limit: int = Query(10, ge=1, le=50)):
    """
    Get a list of generated topics.
    """
    result = await content_controller.get_topics(limit=limit)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.get("/content")
async def get_content(
    content_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get content by ID or topic ID.
    
    - Use content_id to get a specific content
    - Or use topic_id to get content for a specific topic
    - If neither is provided, returns the most recent content
    """
    result = await content_controller.get_content(
        content_id=content_id,
        topic_id=topic_id,
        limit=limit
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.post("/topics/generate-multiple")
async def generate_multiple_topics(request: MultipleTopic):
    """
    Generate multiple topics based on product and brand information.
    
    - Requires product_id and brand_id
    - Optionally specify the number of topics to generate (default: 5)
    - Returns JSON format with multiple topics and their SEO information
    """
    result = await content_controller.generate_brand_product_topics(
        brand_id=request.brand_id,
        product_id=request.product_id,
        count=request.count,
        save_to_db=True,
        prompt=request.prompt,
        use_previous_topics=request.use_previous_topics,
        max_previous_topics=request.max_previous_topics
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.post("/topics/approve")
async def approve_topics(request: TopicApprovalRequest):
    """
    Approve and save topics to database.
    
    - Requires a list of topics to save
    - Only saves topics with status 'complete'
    - Returns the list of saved topics
    """
    result = await content_controller.save_approved_topics(
        topics=request.topics,
        save_to_db=request.save_to_db
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result 

class ApprovedTopicContentRequest(BaseModel):
    topic_id: str = Field(..., description="ID của chủ đề đã được duyệt để tạo nội dung")
    with_related: bool = Field(default=True, description="Có sử dụng nội dung liên quan làm ngữ cảnh hay không")
    save_to_db: bool = Field(default=True, description="Có lưu nội dung đã tạo vào cơ sở dữ liệu hay không")

@router.post("/content/generate-from-approved")
async def generate_content_from_approved_topic(request: ApprovedTopicContentRequest):
    """
    Tạo nội dung cho một chủ đề cụ thể đã được duyệt sử dụng RAG.
    
    - Yêu cầu ID của chủ đề đã được duyệt
    - Tạo nội dung cho chủ đề sử dụng RAG
    - Tùy chọn sử dụng nội dung liên quan làm ngữ cảnh
    - Lưu nội dung đã tạo vào cơ sở dữ liệu
    - Trả về nội dung đã tạo
    """
    try:
        result = await content_controller.generate_content_from_approved_topic(
            topic_id=request.topic_id,
            with_related=request.with_related,
            save_to_db=request.save_to_db
        )
        
        if not result.get("success"):
            error_message = result.get("error", "Unknown error")
            technical_error = result.get("technical_error", "")
            
            # Kiểm tra nếu là lỗi quota hoặc rate limit của OpenAI
            if "quota" in error_message.lower() or "rate limit" in error_message.lower() or "429" in error_message or "insufficient_quota" in technical_error:
                raise HTTPException(
                    status_code=429, 
                    detail="Hệ thống đang tạm thời quá tải. Vui lòng thử lại sau ít phút."
                )
            else:
                raise HTTPException(status_code=500, detail=error_message)
        
        return result
    except Exception as e:
        error_message = str(e)
        if "quota" in error_message.lower() or "rate limit" in error_message.lower() or "429" in error_message or "insufficient_quota" in error_message:
            raise HTTPException(
                status_code=429, 
                detail="Hệ thống đang tạm thời quá tải. Vui lòng thử lại sau ít phút."
            )
        raise HTTPException(status_code=500, detail=error_message)

class ContentImageResponse(BaseModel):
    error: Optional[str] = None

@router.get('/content/view-image/{content_id}')
def view_content_image(content_id: str):
    """
    Endpoint để hiển thị ảnh từ base64 data của nội dung
    """
    try:
        # Kết nối đến cơ sở dữ liệu
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Kiểm tra xem có cột preview_image không
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'content' AND column_name = 'preview_image'")
        has_preview_image = cursor.fetchone() is not None
        
        if not has_preview_image:
            return JSONResponse(status_code=404, content={'error': 'Preview image column does not exist'})
        
        # Lấy dữ liệu ảnh từ cơ sở dữ liệu
        cursor.execute("SELECT content, preview_image FROM content WHERE id = %s", (content_id,))
        result = cursor.fetchone()
        
        if not result:
            return JSONResponse(status_code=404, content={'error': 'Content not found'})
        
        content_json, preview_image = result
        
        if not preview_image:
            # Nếu không có preview_image, thử lấy từ trường content
            content_data = json.loads(content_json)
            if 'preview_image' in content_data:
                preview_image = content_data['preview_image']
            elif 'image' in content_data and 'base64_data' in content_data['image']:
                image_format = content_data['image'].get('format', 'png')
                preview_image = f"data:image/{image_format};base64,{content_data['image']['base64_data']}"
        
        if not preview_image:
            return JSONResponse(status_code=404, content={'error': 'No image found for this content'})
        
        # Trích xuất dữ liệu base64 từ URL data
        if preview_image.startswith('data:'):
            mime_type, base64_data = preview_image.split(';base64,', 1)
            image_data = base64.b64decode(base64_data)
            
            # Xác định loại MIME
            if 'png' in mime_type:
                mime_type = 'image/png'
            elif 'jpeg' in mime_type or 'jpg' in mime_type:
                mime_type = 'image/jpeg'
            else:
                mime_type = 'image/png'  # Mặc định
            
            # Trả về ảnh
            return Response(content=image_data, media_type=mime_type)
        else:
            return JSONResponse(status_code=400, content={'error': 'Invalid image data format'})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

class SqlScriptResponse(BaseModel):
    message: Optional[str] = None
    error: Optional[str] = None

@router.post('/admin/run-sql-script', response_model=SqlScriptResponse)
def run_sql_script():
    """
    Endpoint để thực thi script SQL để thêm các cột mới vào bảng content
    """
    try:
        # Kết nối đến cơ sở dữ liệu
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Đọc script SQL
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts', 'add_columns_to_content.sql')
        
        if not os.path.exists(script_path):
            return JSONResponse(status_code=404, content={'error': 'SQL script not found'})
        
        with open(script_path, 'r') as f:
            sql_script = f.read()
        
        # Thực thi script
        cursor.execute(sql_script)
        conn.commit()
        
        return {'message': 'SQL script executed successfully'}
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()