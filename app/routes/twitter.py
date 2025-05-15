from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from app.models.twitter import TweetCreate, TweetResponse, MediaUploadResponse
from app.controllers.twitter_controller import TwitterController
from app.controllers.auth_controller import AuthController, oauth2_scheme
import os
import shutil
from pathlib import Path
from typing import List
import uuid

router = APIRouter(prefix="/api/twitter", tags=["twitter"])
twitter_controller = TwitterController()
auth_controller = AuthController()

# Tu1ea1o thu01b0 mu1ee5c tu1ea1m thu1eddi u0111u1ec3 lu01b0u tru1eef file media
TEMP_UPLOAD_DIR = Path("temp/uploads")
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/tweet", response_model=TweetResponse)
async def create_tweet(tweet_data: TweetCreate, current_user = Depends(auth_controller.get_current_user)):
    """
    u0110u0103ng mu1ed9t tweet mu1edbi tru00ean X (Twitter).
    
    - Yu00eau cu1ea7u xu00e1c thu1ef1c ngu01b0u1eddi du00f9ng
    - Tru1ea3 vu1ec1 thu00f4ng tin vu1ec1 tweet u0111u00e3 u0111u0103ng
    """
    # Lu1ea5y thu00f4ng tin ngu01b0u1eddi du00f9ng hiu1ec7n tu1ea1i
    user_id = current_user["id"]
    
    # Kiu1ec3m tra xem ngu01b0u1eddi du00f9ng u0111u00e3 liu00ean ku1ebft tu00e0i khou1ea3n Twitter chu01b0a
    # (Chu1ee9c nu0103ng nu00e0y cu1ea7n u0111u01b0u1ee3c phu00e1t triu1ec3n thu00eam)
    
    # Vu00ec chu01b0a cu00f3 chu1ee9c nu0103ng liu00ean ku1ebft tu00e0i khou1ea3n, chu00fang ta tu1ea1m thu1eddi su1eed du1ee5ng thu00f4ng tin xu00e1c thu1ef1c cu1ee7a u1ee9ng du1ee5ng
    try:
        # u0110u0103ng tweet su1eed du1ee5ng Twitter API
        result = await twitter_controller.post_tweet(
            content=tweet_data.content,
            media_ids=tweet_data.media_ids,
            reply_to_id=tweet_data.reply_to_id
        )
        
        # Log hou1ea1t u0111u1ed9ng
        print(f"User {user_id} posted a tweet with ID: {result['tweet_id']}")
        
        return result
    except Exception as e:
        print(f"Error posting tweet for user {user_id}: {str(e)}")
        raise

@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(file: UploadFile = File(...), current_user = Depends(auth_controller.get_current_user)):
    """
    Tu1ea3i lu00ean phu01b0u01a1ng tiu1ec7n (u1ea3nh, video, gif) u0111u1ec3 u0111u00ednh ku00e8m vu00e0o tweet.
    
    - Yu00eau cu1ea7u xu00e1c thu1ef1c ngu01b0u1eddi du00f9ng
    - Hu1ed7 tru1ee3 cu00e1c u0111u1ecbnh du1ea1ng u1ea3nh (jpg, png, webp), video (mp4), vu00e0 gif
    - Tru1ea3 vu1ec1 media_id u0111u1ec3 su1eed du1ee5ng khi u0111u0103ng tweet
    """
    # Lu1ea5y thu00f4ng tin ngu01b0u1eddi du00f9ng hiu1ec7n tu1ea1i
    user_id = current_user["id"]
    
    # Kiu1ec3m tra u0111u1ecbnh du1ea1ng file
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webp"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Supported types: {', '.join(valid_extensions)}"
        )
    
    try:
        # Tu1ea1o tu00ean file duy nhu1ea5t
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = TEMP_UPLOAD_DIR / unique_filename
        
        # Lu01b0u file tu1ea1m thu1eddi
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Tu1ea3i lu00ean Twitter
        result = await twitter_controller.upload_media(str(file_path))
        
        # Xu00f3a file tu1ea1m thu1eddi sau khi tu1ea3i lu00ean
        os.unlink(file_path)
        
        # Log hou1ea1t u0111u1ed9ng
        print(f"User {user_id} uploaded media: {result['media_id']}")
        
        return result
    except Exception as e:
        # u0110u1ea3m bu1ea3o xu00f3a file tu1ea1m nu1ebfu cu00f3 lu1ed7i
        if os.path.exists(file_path):
            os.unlink(file_path)
        
        print(f"Error uploading media for user {user_id}: {str(e)}")
        raise

@router.post("/batch/upload", response_model=List[MediaUploadResponse])
async def batch_upload_media(
    files: List[UploadFile] = File(...),
    current_user = Depends(auth_controller.get_current_user)
):
    """
    Tu1ea3i lu00ean nhiu1ec1u file phu01b0u01a1ng tiu1ec7n cu00f9ng lu00fac.
    
    - Yu00eau cu1ea7u xu00e1c thu1ef1c ngu01b0u1eddi du00f9ng
    - Cho phu00e9p tu1ea3i lu00ean tu1ed1i u0111a 4 file cu00f9ng lu00fac (giu1edbi hu1ea1n cu1ee7a Twitter)
    - Tru1ea3 vu1ec1 danh su00e1ch media_id u0111u1ec3 su1eed du1ee5ng khi u0111u0103ng tweet
    """
    # Lu1ea5y thu00f4ng tin ngu01b0u1eddi du00f9ng hiu1ec7n tu1ea1i
    user_id = current_user["id"]
    
    # Giu1edbi hu1ea1n su1ed1 lu01b0u1ee3ng file
    if len(files) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can upload a maximum of 4 media files per tweet"
        )
    
    results = []
    temp_files = []
    
    try:
        for file in files:
            # Kiu1ec3m tra u0111u1ecbnh du1ea1ng file
            valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webp"]
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in valid_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not supported: {file.filename}. Supported types: {', '.join(valid_extensions)}"
                )
            
            # Tu1ea1o tu00ean file duy nhu1ea5t
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = TEMP_UPLOAD_DIR / unique_filename
            temp_files.append(file_path)
            
            # Lu01b0u file tu1ea1m thu1eddi
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Tu1ea3i lu00ean Twitter
            result = await twitter_controller.upload_media(str(file_path))
            results.append(result)
        
        # Log hou1ea1t u0111u1ed9ng
        print(f"User {user_id} batch uploaded {len(results)} media files")
        
        return results
    
    except Exception as e:
        print(f"Error batch uploading media for user {user_id}: {str(e)}")
        raise
    
    finally:
        # Xu00f3a tu1ea5t cu1ea3 cu00e1c file tu1ea1m thu1eddi
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.unlink(file_path)
