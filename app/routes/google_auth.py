from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

router = APIRouter(prefix="/google-business", tags=["Google Business"])

class TokenRequest(BaseModel):
    access_token: str

@router.post("/me")
def get_business_profile(req: TokenRequest):
    business_profile_url = "https://mybusinessbusinessinformation.googleapis.com/v1/accounts"
    print("📥 Received request to /google-business/me with token:", req.access_token)

    headers = {
        "Authorization": f"Bearer {req.access_token}"
    }

    try:
        res = requests.get(business_profile_url, headers=headers)
        print(f"📡 Google Business API Response: {res.status_code} {res.text}")

        # Raise error if response is not 2xx
        res.raise_for_status()

        data = res.json()

        if "accounts" not in data:
            raise HTTPException(status_code=400, detail="Không tìm thấy tài khoản doanh nghiệp nào")

        return data["accounts"]

    except requests.exceptions.HTTPError as http_err:
        print("❌ HTTPError:", str(http_err))
        raise HTTPException(status_code=res.status_code, detail=res.json())
    
    except Exception as e:
        print("❗ Unexpected error:", str(e))
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi nội bộ")
