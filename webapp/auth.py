import hmac
import hashlib
import json
import time
import base64
from urllib.parse import parse_qsl
from fastapi import Request

from config import BOT_TOKEN, SUPER_ADMIN_IDS, ADMIN_IDS, is_super_admin, is_admin
from database.db import get_user

SESSION_COOKIE_NAME = "educenter_session"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 kun


def validate_telegram_init_data(init_data: str, bot_token: str = BOT_TOKEN) -> dict | None:
    """
    Validates Telegram Mini App initData using HMAC-SHA256 signature algorithm:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not bot_token:
        return None

    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # Secret key = HMAC_SHA256(key="WebAppData", msg=bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calculated_hash, received_hash):
            user_data = None
            if "user" in parsed_data:
                try:
                    user_data = json.loads(parsed_data["user"])
                except Exception:
                    pass
            return {"raw": parsed_data, "user": user_data}
        return None
    except Exception:
        return None


def create_session_token(payload: dict, secret: str = BOT_TOKEN) -> str:
    """Creates a tamper-proof signed session token using HMAC-SHA256."""
    data = dict(payload)
    data["exp"] = int(time.time()) + SESSION_MAX_AGE
    data_str = json.dumps(data, sort_keys=True)
    signature = hmac.new(secret.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha256).hexdigest()
    b64_data = base64.urlsafe_b64encode(data_str.encode("utf-8")).decode("utf-8")
    return f"{b64_data}.{signature}"


def verify_session_token(token: str, secret: str = BOT_TOKEN) -> dict | None:
    """Verifies a tamper-proof signed session token."""
    if not token or "." not in token:
        return None

    try:
        b64_data, signature = token.rsplit(".", 1)
        data_str = base64.urlsafe_b64decode(b64_data.encode("utf-8")).decode("utf-8")

        expected_sig = hmac.new(secret.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return None

        data = json.loads(data_str)
        if time.time() > data.get("exp", 0):
            return None  # Expired

        return data
    except Exception:
        return None


async def get_session_user(request: Request) -> dict | None:
    """Extracts authenticated user from cookies or X-Telegram-Init-Data header."""
    # 1. Check signed cookie
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        session = verify_session_token(cookie_token)
        if session:
            return session

    # 2. Check X-Telegram-Init-Data header (direct Telegram WebApp requests)
    tg_header = request.headers.get("X-Telegram-Init-Data")
    if tg_header:
        validated = validate_telegram_init_data(tg_header)
        if validated and validated.get("user"):
            tg_user = validated["user"]
            telegram_id = int(tg_user["id"])
            user_db = await get_user(telegram_id)

            role = "parent"
            if is_super_admin(telegram_id):
                role = "super_admin"
            elif is_admin(telegram_id):
                role = "admin"
            elif user_db:
                role = user_db["role"]

            return {
                "telegram_id": telegram_id,
                "role": role,
                "full_name": tg_user.get("first_name", "") + " " + tg_user.get("last_name", ""),
                "db_user_id": user_db["id"] if user_db else None,
            }

    return None
