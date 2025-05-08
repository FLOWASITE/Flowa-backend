from fastapi import APIRouter, Body, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from app.controllers.content_controller import ContentController

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