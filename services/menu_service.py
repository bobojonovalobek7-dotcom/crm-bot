import logging
from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo, MenuButtonDefault
from config import get_effective_role, get_webapp_url
from database.db import get_user, get_parent_students

logger = logging.getLogger(__name__)


async def resolve_user_webapp_url(telegram_id: int | None, user: dict | None = None) -> str:
    """
    Determines the dedicated Web App URL for a given user according to their role and ID:
    - Super Admin & Admin -> /admin
    - Teacher -> /teacher/{teacher_id}
    - Student -> /parent/{student_id}
    - Parent -> /parent/{child_id} (or own student portal if no children linked yet)
    """
    if not user and telegram_id:
        user = await get_user(telegram_id)

    role = get_effective_role(telegram_id, user["role"] if user else "parent")

    if role in {"super_admin", "admin"}:
        return get_webapp_url("/admin")

    if role == "teacher" and user:
        return get_webapp_url(f"/teacher/{user['id']}")

    if role == "parent" and user:
        children = await get_parent_students(user["id"])
        if children:
            return get_webapp_url(f"/parent/{children[0]['student_id']}")
        return get_webapp_url(f"/parent/{user['id']}")

    if role == "student" and user:
        return get_webapp_url(f"/student/{user['id']}")

    return get_webapp_url("/")


def resolve_menu_button_text(role: str) -> str:
    if role == "super_admin":
        return "👑 Super Admin Portali"
    if role == "admin":
        return "🛡 Admin Portali"
    if role == "teacher":
        return "👨‍🏫 Ustoz Portali"
    if role == "student":
        return "👨‍🎓 O'quvchi Portali"
    return "👨‍👩‍👧 Ota-ona Portali"


async def setup_user_webapp_menu(bot: Bot, telegram_id: int, user: dict | None = None) -> str:
    """
    Configures the persistent Telegram Chat Menu Button at the bottom-left of the chat.
    If the webapp URL starts with https://, sets MenuButtonWebApp.
    Otherwise safely falls back without raising errors.
    Returns the resolved URL.
    """
    if not user and telegram_id:
        user = await get_user(telegram_id)

    role = get_effective_role(telegram_id, user["role"] if user else "parent")
    url = await resolve_user_webapp_url(telegram_id, user)
    button_text = resolve_menu_button_text(role)

    if url.startswith("https://"):
        try:
            await bot.set_chat_menu_button(
                chat_id=telegram_id,
                menu_button=MenuButtonWebApp(
                    text=button_text,
                    web_app=WebAppInfo(url=url)
                )
            )
            logger.info(f"Chat menu button set to {button_text} ({url}) for user {telegram_id}")
        except Exception as e:
            logger.warning(f"Could not set chat menu button for {telegram_id}: {e}")

    else:
        # Telegram Bot API rejects http:// for MenuButtonWebApp
        try:
            await bot.set_chat_menu_button(
                chat_id=telegram_id,
                menu_button=MenuButtonDefault()
            )
        except Exception as e:
            logger.debug(f"Default menu button reset note for {telegram_id}: {e}")

    return url
