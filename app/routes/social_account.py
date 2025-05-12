from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.controllers.social_controller import SocialController

router = APIRouter(prefix="/api/social", tags=["social"])
social_controller = SocialController()

class SocialAccountRequest(BaseModel):
    user_id: str
    platform: str  # ví dụ: "facebook", "google"
    account_id: str
    profile_url: Optional[str] = None

class SocialAccountApprovalRequest(BaseModel):
    account_ids: List[str]
    approve: bool

@router.post("/link")
async def link_social_account(request: SocialAccountRequest):
    """
    Liên kết tài khoản mạng xã hội với người dùng.
    """
    result = await social_controller.link_account(
        user_id=request.user_id,
        platform=request.platform,
        account_id=request.account_id,
        profile_url=request.profile_url
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result

@router.get("/accounts")
async def get_social_accounts(user_id: str):
    """
    Lấy danh sách tài khoản mạng xã hội đã liên kết cho một user.
    """
    result = await social_controller.get_accounts(user_id=user_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result

@router.post("/approve")
async def approve_social_accounts(request: SocialAccountApprovalRequest):
    """
    Duyệt hoặc từ chối danh sách tài khoản mạng xã hội.
    """
    result = await social_controller.approve_accounts(
        account_ids=request.account_ids,
        approve=request.approve
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
