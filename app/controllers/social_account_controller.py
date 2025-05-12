from fastapi import APIRouter, HTTPException, Depends
from app.models.social_account import SocialAccountCreate, SocialAccountUpdate, SocialAccount
from app.services.social_account_service import SocialAccountService  # Import Service

router = APIRouter()

# Create a new social account
@router.post("/social-accounts/", response_model=SocialAccount)
async def create_social_account(
    social_account_data: SocialAccountCreate, 
    service: SocialAccountService = Depends()
):
    try:
        return await service.create_social_account(social_account_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Get social account by ID
@router.get("/social-accounts/{account_id}", response_model=SocialAccount)
async def get_social_account(
    account_id: str, 
    service: SocialAccountService = Depends()
):
    try:
        return await service.get_social_account_by_id(account_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# Update social account by ID
@router.put("/social-accounts/{account_id}", response_model=SocialAccount)
async def update_social_account(
    account_id: str, 
    social_account_data: SocialAccountUpdate, 
    service: SocialAccountService = Depends()
):
    try:
        return await service.update_social_account(account_id, social_account_data)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# Delete social account by ID
@router.delete("/social-accounts/{account_id}")
async def delete_social_account(
    account_id: str, 
    service: SocialAccountService = Depends()
):
    try:
        await service.delete_social_account(account_id)
        return {"message": "Social account deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# Get all social accounts for a specific user
@router.get("/social-accounts/user/{user_id}", response_model=List[SocialAccount])
async def get_social_accounts_by_user(
    user_id: str, 
    service: SocialAccountService = Depends()
):
    try:
        return await service.get_social_accounts_by_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
