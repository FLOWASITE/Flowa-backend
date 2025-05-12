class SocialController:
    def __init__(self):
        pass

    async def link_account(self, user_id: str, platform: str, account_id: str, profile_url: str = None):
        # TODO: Thêm logic lưu vào DB hoặc gọi external API
        return {
            "success": True,
            "message": f"Linked {platform} account {account_id} to user {user_id}"
        }

    async def get_accounts(self, user_id: str):
        # TODO: Truy vấn DB
        return {
            "success": True,
            "accounts": [
                {"platform": "facebook", "account_id": "123", "profile_url": "https://fb.com/user123"},
                {"platform": "google", "account_id": "456", "profile_url": "https://plus.google.com/user456"}
            ]
        }

    async def approve_accounts(self, account_ids: list, approve: bool):
        # TODO: Cập nhật trạng thái duyệt trong DB
        status = "approved" if approve else "rejected"
        return {
            "success": True,
            "message": f"{len(account_ids)} accounts have been {status}"
        }
