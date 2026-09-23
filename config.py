import os
from dotenv import load_dotenv

load_dotenv()


def _parse_int_list(raw_value: str | None, fallback: list[int]) -> list[int]:
    if not raw_value:
        return fallback

    ids: list[int] = []
    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            ids.append(int(value))
        except ValueError:
            continue

    return ids or fallback


def normalize_role(role: str | None) -> str:
    if not role:
        return "parent"

    normalized = str(role).strip().lower()
    if normalized in {"super_admin", "admin", "teacher", "parent", "student"}:
        return normalized
    return "parent"


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPER_ADMIN_IDS = _parse_int_list(os.getenv("SUPER_ADMIN_IDS"), [5341602920])
ADMIN_IDS = _parse_int_list(os.getenv("ADMIN_IDS"), SUPER_ADMIN_IDS)

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://localhost:8000")
DATABASE_PATH = os.getenv("DATABASE_PATH", "educenter.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATABASE_PATH}")
PROXY_URL = os.getenv("PROXY_URL", "").strip() or None


def is_super_admin(telegram_id: int | None) -> bool:
    return bool(telegram_id is not None and telegram_id in SUPER_ADMIN_IDS)


def is_admin(telegram_id: int | None) -> bool:
    return bool(telegram_id is not None and (telegram_id in SUPER_ADMIN_IDS or telegram_id in ADMIN_IDS))


def get_effective_role(telegram_id: int | None, stored_role: str | None = None) -> str:
    if is_super_admin(telegram_id):
        return "super_admin"
    if is_admin(telegram_id):
        return "admin"
    return normalize_role(stored_role)


def get_webapp_url(path: str = "") -> str:
    base = WEBAPP_BASE_URL.rstrip("/")
    clean_path = "/" + path.lstrip("/") if path else ""
    return f"{base}{clean_path}"

