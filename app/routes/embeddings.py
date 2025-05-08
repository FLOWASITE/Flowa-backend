from fastapi import APIRouter, HTTPException
from typing import Optional
from app.utils.product_embeddings import ProductEmbeddings

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])
product_embeddings = ProductEmbeddings()

@router.post("/products/{product_id}")
async def generate_product_embedding(product_id: str):
    """
    Generate and store embedding for a specific product.
    
    Args:
        product_id (str): ID of the product to generate embedding for
        
    Returns:
        dict: Result of the operation
    """
    result = product_embeddings.generate_product_embedding(product_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.post("/products")
async def generate_all_product_embeddings():
    """
    Generate and store embeddings for all products without embeddings.
    
    Returns:
        dict: Result of the operation
    """
    result = product_embeddings.generate_all_product_embeddings()
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result 