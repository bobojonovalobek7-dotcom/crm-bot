from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def get_main_keyboard(role: str = "parent", webapp_url: str | None = None):
    role_name = (role or "parent").lower()
    has_https_webapp = bool(webapp_url and str(webapp_url).startswith("https://"))

    if role_name in {"admin", "super_admin"}:
        crm_btn = (
            KeyboardButton(text="📊 CRM Web App", web_app=WebAppInfo(url=webapp_url))
            if has_https_webapp
            else KeyboardButton(text="📊 CRM Web App")
        )
        kb = [
            [crm_btn, KeyboardButton(text="👤 Yangi admin")],
            [KeyboardButton(text="👨‍🏫 Yangi ustoz"), KeyboardButton(text="💰 Yangi to'lov")],
            [KeyboardButton(text="💬 Murojaatlar"), KeyboardButton(text="📈 Hisobotlar")],
            [KeyboardButton(text="📣 Xabar yuborish"), KeyboardButton(text="🔄 Qayta ishga tushirish")],
        ]
    elif role_name == "teacher":
        web_btn = (
            KeyboardButton(text="👨‍🏫 Web panel", web_app=WebAppInfo(url=webapp_url))
            if has_https_webapp
            else KeyboardButton(text="👨‍🏫 Web panel")
        )
        kb = [
            [KeyboardButton(text="👥 Guruhlarim"), KeyboardButton(text="📅 Dars jadvali")],
            [KeyboardButton(text="✅ Davomat"), KeyboardButton(text="📚 Materiallar")],
            [KeyboardButton(text="💬 Murojaat"), web_btn],
            [KeyboardButton(text="🔄 Qayta ishga tushirish")],
        ]
    elif role_name == "student":
        kb = [
            [KeyboardButton(text="📅 Dars jadvali"), KeyboardButton(text="💳 To'lovlar tarixi")],
            [KeyboardButton(text="🧑‍🏫 Bugungi mashg'ulot"), KeyboardButton(text="✅ Davomatim")],
            [KeyboardButton(text="💬 Murojaat va taklif"), KeyboardButton(text="🔄 Qayta ishga tushirish")],
        ]
    else:  # parent
        kb = [
            [KeyboardButton(text="👶 Farzandlarim"), KeyboardButton(text="📅 Dars jadvali")],
            [KeyboardButton(text="🧑‍🏫 Bugungi mashg'ulot"), KeyboardButton(text="💳 To'lovlar tarixi")],
            [KeyboardButton(text="✅ Davomat"), KeyboardButton(text="💬 Murojaat va taklif")],
            [KeyboardButton(text="🔄 Qayta ishga tushirish")],
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)



def get_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )