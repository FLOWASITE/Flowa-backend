from fastapi import APIRouter, HTTPException
import requests
from pydantic import BaseModel
from base64 import b64encode
import os

router = APIRouter(prefix="/twitter", tags=["Twitter OAuth"])

class TwitterCallbackRequest(BaseModel):
    code: str
    code_verifier: str

@router.post("/callback")
async def twitter_callback(request: TwitterCallbackRequest):
    token_url = "https://api.twitter.com/2/oauth2/token"
    user_info_url = "https://api.twitter.com/2/users/me"

    client_id = "TTFvOGtnVXF4ZUhicnF6NExiTGY6MTpjaQ"
    client_secret = "amomd9_mHnXUJXwA3OjJ_kpz8Toec6-Ejog6FRYhV5mubfqWdC"
    redirect_uri = "https://localhost:8080/auth/twitter/callback"

    basic_token = b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_token}"
    }

    payload = {
        "code": request.code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": request.code_verifier
    }

    try:
        token_res = requests.post(token_url, data=payload, headers=headers)
        token_data = token_res.json()

        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Invalid token response: " + token_data.get("error_description", "Unknown error"))

        access_token = token_data["access_token"]

        user_info_res = requests.get(
            f"{user_info_url}?user.fields=profile_image_url",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        user_info = user_info_res.json()

        if "data" not in user_info:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Twitter")

        return {
            "access_token": access_token,
            "user_id": user_info["data"]["id"],
            "username": user_info["data"]["username"],
            "profile_image_url": user_info["data"]["profile_image_url"]
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data from Twitter: {str(e)}")
