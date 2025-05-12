from fastapi import HTTPException
from datetime import datetime
from typing import List
from app.utils.database import get_db_connection
from app.models.social_account import SocialAccountCreate, SocialAccountUpdate, SocialAccount
from psycopg2.extras import RealDictCursor


class SocialAccountService:

    def _get_connection_and_cursor(self):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        return conn, cursor

    async def create_social_account(self, account_data: SocialAccountCreate):
        """Tạo mới hoặc cập nhật tài khoản mạng xã hội nếu đã tồn tại cùng platform và account_id"""
        conn, cursor = self._get_connection_and_cursor()

        try:
            print(f"Đang xử lý tài khoản cho: {account_data}")

            # Lấy platform_id từ platform_name
            cursor.execute("SELECT id FROM platforms WHERE name = %s", (account_data.platform_name,))
            platform_row = cursor.fetchone()

            if not platform_row:
                raise HTTPException(status_code=400, detail="Nền tảng không hợp lệ.")

            platform_id = platform_row["id"]

            # Kiểm tra tài khoản đã tồn tại chưa (cùng account_id và platform_id)
            cursor.execute("""
                SELECT id FROM social_accounts
                WHERE account_id = %s AND platform_id = %s
            """, (account_data.account_id, platform_id))

            existing_account = cursor.fetchone()

            if existing_account:
                print("Tài khoản đã tồn tại. Cập nhật thông tin...")
                # Nếu đã tồn tại, cập nhật thông tin
                cursor.execute("""
                    UPDATE social_accounts
                    SET brand_id = %s,
                        account_name = %s,
                        access_token = %s,
                        refresh_token = %s,
                        token_expires_at = %s,
                        account_type = %s,
                        status = %s,
                        user_id = %s,
                        account_picture = %s
                    WHERE account_id = %s AND platform_id = %s
                """, (
                    str(account_data.brand_id),
                    account_data.account_name,
                    account_data.access_token,
                    account_data.refresh_token,
                    account_data.token_expires_at,
                    account_data.account_type,
                    account_data.status,
                    str(account_data.user_id),
                    account_data.account_picture,
                    account_data.account_id,
                    platform_id
                ))

            else:
                print("Tài khoản chưa tồn tại. Tạo mới...")
                # Nếu chưa có, tạo mới
                cursor.execute("""
                    INSERT INTO social_accounts (
                        platform_id, brand_id, account_name, account_id, access_token,
                        refresh_token, token_expires_at, account_type, status, user_id, account_picture
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    platform_id,
                    str(account_data.brand_id),
                    account_data.account_name,
                    str(account_data.account_id),
                    account_data.access_token,
                    account_data.refresh_token,
                    account_data.token_expires_at,
                    account_data.account_type,
                    account_data.status,
                    str(account_data.user_id),
                    account_data.account_picture
                ))

            conn.commit()

            # Trả về bản ghi đã cập nhật hoặc vừa tạo
            cursor.execute("""
                SELECT sa.*, p.name AS platform_name
                FROM social_accounts sa
                JOIN platforms p ON sa.platform_id = p.id
                WHERE sa.account_id = %s AND sa.platform_id = %s
            """, (account_data.account_id, platform_id))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Không lấy được thông tin tài khoản sau khi lưu.")

            return SocialAccount(**row)

        except Exception as e:
            import traceback
            traceback.print_exc()
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý tài khoản mạng xã hội: {str(e)}")

        finally:
            print("Đóng kết nối cơ sở dữ liệu.")
            cursor.close()
            conn.close()


    async def get_social_account(self, account_id: str):
        """Lấy thông tin tài khoản mạng xã hội theo account_id"""
        conn, cursor = self._get_connection_and_cursor()

        try:
            cursor.execute("SELECT * FROM social_accounts WHERE account_id = %s", (account_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
            return SocialAccount(**row)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy tài khoản: {str(e)}")

        finally:
            cursor.close()
            conn.close()

    async def update_social_account(self, id: str, account_data: SocialAccountUpdate):
        """Cập nhật tài khoản mạng xã hội"""
        conn, cursor = self._get_connection_and_cursor()

        try:
            cursor.execute("SELECT * FROM social_accounts WHERE id = %s", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để cập nhật.")

            update_data = {k: v for k, v in account_data.dict().items() if v is not None}
            if not update_data:
                raise HTTPException(status_code=400, detail="Không có trường nào để cập nhật.")

            update_data["updated_at"] = datetime.utcnow()

            set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
            values = list(update_data.values()) + [id]

            cursor.execute(
                f"UPDATE social_accounts SET {set_clause} WHERE id = %s",
                tuple(values)
            )
            conn.commit()

            # Lấy lại bản ghi sau khi cập nhật
            cursor.execute("SELECT * FROM social_accounts WHERE id = %s", (id,))
            row = cursor.fetchone()
            return SocialAccount(**row)

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật tài khoản: {str(e)}")

        finally:
            cursor.close()
            conn.close()

    async def delete_social_account(self, id: str):
        """Xoá tài khoản mạng xã hội"""
        conn, cursor = self._get_connection_and_cursor()

        try:
            cursor.execute("SELECT id FROM social_accounts WHERE id = %s", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để xoá.")

            cursor.execute("DELETE FROM social_accounts WHERE id = %s", (id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi khi xoá tài khoản: {str(e)}")

        finally:
            cursor.close()
            conn.close()

    async def list_social_accounts(self, user_id: str) -> List[SocialAccount]:
        """Liệt kê các tài khoản mạng xã hội theo user_id kèm tên platform"""
        conn, cursor = self._get_connection_and_cursor()

        try:
            cursor.execute("""
                SELECT sa.*, p.name AS platform_name
                FROM social_accounts sa
                JOIN platforms p ON sa.platform_id = p.id
                WHERE sa.user_id = %s
            """, (user_id,))
            
            rows = cursor.fetchall()

            # Gán thêm platform_name vào mô hình trả về nếu cần
            return [SocialAccount(**row) for row in rows]

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách tài khoản: {str(e)}")

        finally:
            cursor.close()
            conn.close()
            """Liệt kê các tài khoản mạng xã hội theo user_id"""
            conn, cursor = self._get_connection_and_cursor()

            try:
                cursor.execute("SELECT * FROM social_accounts WHERE user_id = %s", (user_id,))
                rows = cursor.fetchall()
                return [SocialAccount(**row) for row in rows]

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách tài khoản: {str(e)}")

            finally:
                cursor.close()
                conn.close()

    async def list_social_accounts(self, user_id: str, brand_id: str) -> List[SocialAccount]:
        """Liệt kê các tài khoản mạng xã hội theo user_id và brand_id kèm tên platform"""
        conn, cursor = self._get_connection_and_cursor()

        try:
            cursor.execute("""
                SELECT sa.*, p.name AS platform_name
                FROM social_accounts sa
                JOIN platforms p ON sa.platform_id = p.id
                WHERE sa.user_id = %s AND sa.brand_id = %s
            """, (user_id, brand_id))
            
            rows = cursor.fetchall()

            # Gán thêm platform_name vào mô hình trả về nếu cần
            return [SocialAccount(**row) for row in rows]

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách tài khoản: {str(e)}")

        finally:
            cursor.close()
            conn.close()
