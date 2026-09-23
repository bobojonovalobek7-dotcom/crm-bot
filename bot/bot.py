import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import BOT_TOKEN, WEBAPP_BASE_URL, PROXY_URL
from bot.handlers import admin, student, teacher
from database.models import init_db


async def main():
    logging.basicConfig(level=logging.INFO)

    await init_db()

    session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else None
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(teacher.router)
    dp.include_router(student.router)

    if WEBAPP_BASE_URL.startswith("https://"):
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Web App", web_app=WebAppInfo(url=WEBAPP_BASE_URL))
            )
            logging.info("Telegram WebApp global menu button faollashtirildi!")
        except Exception as e:
            logging.warning(f"Global WebApp menu button sozlashda eslatma: {e}")

    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)



if __name__ == "__main__":
    import asyncio

    asyncio.run(main())