from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def get_main_keyboard(role: str = "parent", webapp_url: str | None = None):
    role_name = (role or "parent").lower()

    if role_name == "super_admin":
        kb = [
            [KeyboardButton(text="👥 Adminlar"), KeyboardButton(text="👤 Yangi admin")],
            [KeyboardButton(text="👨‍🏫 Yangi ustoz"), KeyboardButton(text="💰 Yangi to'lov")],
            [KeyboardButton(text="📈 Hisobotlar"), KeyboardButton(text="💬 Murojaatlar")],
            [KeyboardButton(text="📣 Xabar yuborish"), KeyboardButton(text="🔄 Qayta ishga tushirish")],
        ]
    elif role_name == "admin":
        kb = [
            [KeyboardButton(text="👤 Yangi admin"), KeyboardButton(text="👨‍🏫 Yangi ustoz")],
            [KeyboardButton(text="💰 Yangi to'lov"), KeyboardButton(text="📈 Hisobotlar")],
            [KeyboardButton(text="💬 Murojaatlar"), KeyboardButton(text="📣 Xabar yuborish")],
            [KeyboardButton(text="🔄 Qayta ishga tushirish")],
        ]
    elif role_name == "teacher":
        kb = [
            [KeyboardButton(text="👥 Guruhlarim"), KeyboardButton(text="📅 Dars jadvali")],
            [KeyboardButton(text="✅ Davomat"), KeyboardButton(text="📚 Materiallar")],
            [KeyboardButton(text="💬 Murojaat"), KeyboardButton(text="🔄 Qayta ishga tushirish")],
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