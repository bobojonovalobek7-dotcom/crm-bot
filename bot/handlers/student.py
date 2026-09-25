from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from config import get_effective_role, get_webapp_url
from database.db import (
    add_user,
    get_user,
    get_user_by_id,
    get_student_groups,
    get_student_payments,
    get_student_attendance,
    get_parent_students,
    create_feedback,
    update_user_role,
)
from services.menu_service import setup_user_webapp_menu, resolve_user_webapp_url
from bot.handlers.admin import (
    CREATION_SESSIONS,
    _handle_creation_step,
    should_cancel_creation_session,
    start_creation_wizard,
    handle_admin_reply_step,
    handle_broadcast_message,
    is_admin_creation_cmd,
    is_teacher_creation_cmd,
)
from bot.keyboards.default import get_main_keyboard, get_phone_keyboard
from bot.keyboards.inline import (
    get_parent_children_keyboard,
    get_child_details_keyboard,
    get_feedback_type_keyboard,
)
from services.notifications import notify_new_feedback

router = Router()
FEEDBACK_SESSIONS: dict[int, dict] = {}


def build_student_reply(text: str) -> str:
    """Fallback static template used for unit-tests and unregistered queries."""
    value = (text or "").strip()
    normalized = value.lower()

    if "dars jadval" in normalized:
        return (
            "Dars jadvali\n\n"
            "- Dushanba: 16:00 - Matematika\n"
            "- Seshanba: 18:00 - Ingliz tili\n"
            "- Chorshanba: 17:30 - Fizika\n"
            "- Payshanba: 16:30 - Informatika\n\n"
            "Har kuni ertalab dars va topshiriqlar haqida xabar keladi."
        )

    if "to'lov" in normalized or "tarixi" in normalized:
        return (
            "To'lovlar tarixi\n\n"
            "- Avgust: 350 000 so'm to'landi\n"
            "- Sentabr: 350 000 so'm to'landi\n"
            "- Oktyabr: 350 000 so'm kutilmoqda\n\n"
            "Agar qarz yoki to'lov ma'lumoti bo'lsa, admin bilan bog'laning."
        )

    if "bugungi" in normalized or "mashg'ulot" in normalized or "dars" in normalized:
        return (
            "Bugungi mashg'ulot\n\n"
            "- 16:00 — Matematika\n"
            "- 17:30 — Ingliz tili\n"
            "- 18:30 — Mustaqil ish va uy vazifalari\n\n"
            "Dars ishlanmalar va materiallar keyinchalik shu bot orqali yuklab olinadi."
        )

    if "qo'llab" in normalized or "support" in normalized or "yordam" in normalized:
        return (
            "Yordam / qo'llab-quvvatlash\n\n"
            "- Yangi admin\n"
            "- Yangi ustoz\n"
            "- Yangi to'lov\n"
            "- Dars jadvali\n"
            "- To'lovlar tarixi\n\n"
            "Telefon: +998 90 123 45 67\n"
            "Telegram: @zahro_support\n"
            "Ish vaqti: 9:00 - 18:00"
        )

    if "crm" in normalized or "web" in normalized or "crm web app" in normalized:
        return f"CRM paneli: {get_webapp_url('/admin')}"

    if (
        "yangi admin" in normalized
        or "/create_admin" in normalized
        or "/add_admin" in normalized
        or ("admin" in normalized and any(k in normalized for k in ["qo'sh", "qosh", "yarat", "yangi"]))
    ):
        return (
            "Yangi admin yaratish uchun quyidagi ketma-ketlik bo'yicha ma'lumot kiriting:\n\n"
            "1) Ism va familiya\n"
            "2) Telefon raqam\n"
            "3) Telegram ID"
        )

    if (
        "yangi ustoz" in normalized
        or "/create_teacher" in normalized
        or "/add_teacher" in normalized
        or "yangi oqituvchi" in normalized
        or "teacher" in normalized
        or (any(t in normalized for t in ["ustoz", "o'qituvchi", "oqituvchi"]) and any(k in normalized for k in ["qo'sh", "qosh", "yarat", "yangi"]))
    ):
        return (
            "Yangi ustoz yaratish uchun quyidagi ketma-ketlik bo'yicha ma'lumot kiriting:\n\n"
            "1) Ism va familiya\n"
            "2) Telefon raqam\n"
            "3) Telegram ID"
        )

    if "yangi to'lov" in normalized or "tolov" in normalized:
        return "To'lov qabul qilish uchun: /add_payment <student_id> | <group_id> | <amount> | <payment_type> | <month_for> | <note>"

    if "guruhlarim" in normalized:
        return "Guruhlarim bo'limi: guruhlar ro'yxati va o'quvchilar ma'lumotlari admin paneldan ko'rinadi."

    if "davomat" in normalized:
        return "Davomat kiritish uchun admin panel yoki /admin dan foydalaning."

    if "materiallar" in normalized:
        return "Materiallar bo'limi tez orada dars ishlanmalar va fayllar bilan kengaytiriladi."

    if "hisobotlar" in normalized:
        return "Hisobotlar haqida ma'lumotni admin paneldan ko'ring."

    if "xabar yuborish" in normalized or "yuborish" in normalized:
        return "Xabar yuborish uchun admin paneldagi xabar funksiyasidan foydalaning."

    if "qayta ishga tushirish" in normalized or "restart" in normalized or value in {"/restart", "/start", "start"}:
        return "Bot qayta ishga tushirilmoqda. Menu yangilanadi..."

    if value in {"/help", "/start", "start"}:
        return "Assalomu alaykum! Quyidagi tugmalardan birini tanlang."

    return (
        "Bu buyruqni tushunmadim.\n"
        "Iltimos, quyidagi tugmalardan birini tanlang:\n"
        "- Dars jadvali\n"
        "- To'lovlar tarixi\n"
        "- Bugungi mashg'ulot\n"
        "- Qo'llab-quvvatlash"
    )


async def get_real_student_data_reply(user: dict | None, text: str) -> str | None:
    """Fetches real database records for the student if registered."""
    if not user:
        return None

    normalized = (text or "").strip().lower()

    if "dars jadval" in normalized:
        groups = await get_student_groups(user["id"])
        if not groups:
            return (
                "📅 <b>Dars jadvali</b>\n\n"
                "ℹ️ Siz hali birorta guruhga biriktirilmagansiz.\n"
                "Administrator sizni guruhga biriktirishi bilan dars vaqtlari bu yerda avtomatik ko'rinadi."
            )
        msg = f"📅 <b>{user['full_name']} — Sizning dars jadvalingiz:</b>\n\n"
        for idx, g in enumerate(groups, 1):
            schedule = g["schedule"] if g["schedule"] else "Vaqti belgilanmagan"
            room = f" ({g['room']}-xona)" if g["room"] else ""
            teacher = f", Ustoz: {g['teacher_name']}" if g["teacher_name"] else ""
            msg += f"<b>{idx}. {g['name']}</b> ({g['subject']})\n   ⏰ {schedule}{room}{teacher}\n\n"
        return msg

    if "to'lov" in normalized or "tarixi" in normalized:
        payments = await get_student_payments(user["id"])
        if not payments:
            return (
                "💳 <b>To'lovlar tarixi</b>\n\n"
                "ℹ️ Sizda hali to'lovlar mavjud emas.\n"
                "To'lov amalga oshirilgach, kvitansiyalar shu yerda saqlanadi."
            )
        total_paid = sum(p["amount"] for p in payments)
        msg = f"💳 <b>{user['full_name']} — To'lovlar tarixi:</b>\n\n"
        for idx, p in enumerate(payments, 1):
            note = f" ({p['note']})" if p["note"] else ""
            msg += (
                f"<b>{idx}. {p['month_for']}</b> — {p['amount']:,.0f} so'm\n"
                f"   📚 Guruh: {p['group_name']}\n"
                f"   💳 Usul: {p['payment_type'].capitalize()}{note}\n"
                f"   📅 Sana: {p['created_at'][:10]}\n\n"
            )
        msg += f"💵 <b>Jami to'langan summa:</b> {total_paid:,.0f} so'm"
        return msg

    if "bugungi" in normalized or "mashg'ulot" in normalized:
        groups = await get_student_groups(user["id"])
        if not groups:
            return "🧑‍🏫 <b>Bugungi mashg'ulot:</b>\n\nSiz hali guruhga biriktirilmagansiz."
        msg = "🧑‍🏫 <b>Bugungi mashg'ulotlaringiz:</b>\n\n"
        for g in groups:
            schedule = g["schedule"] if g["schedule"] else "Vaqti ko'rsatilmagan"
            msg += f"🔹 <b>{g['name']}</b> ({g['subject']})\n   ⏰ {schedule}\n\n"
        msg += "<i>Vazifalaringizni vaqtida bajaring va darsga kechikmang!</i>"
        return msg

    if "davomat" in normalized:
        att = await get_student_attendance(user["id"], limit=10)
        if not att:
            return "✅ <b>Davomat tarixi</b>\n\nℹ️ Sizda hali davomat yozuvlari mavjud emas."
        msg = f"✅ <b>{user['full_name']} — Davomat tarixi:</b>\n\n"
        for a in att:
            icon = "🟢 Keldi" if a["status"] == "keldi" else ("🔴 Kelmadi" if a["status"] == "kelmadi" else "🟡 Sababli")
            msg += f"📅 <b>{a['date']}</b> — {a['group_name']}: {icon}\n"
        return msg

    return None


async def get_real_parent_data_reply(user: dict | None, text: str) -> tuple[str | None, any]:
    """Fetches real database records for parent queries."""
    if not user:
        return None, None

    normalized = (text or "").strip().lower()
    children = await get_parent_students(user["id"])

    if "farzand" in normalized:
        if not children:
            return (
                "ℹ️ <b>Sizga hali birorta farzand biriktirilmagan.</b>\n\n"
                "Farzandingizni profilingizga biriktirish uchun o'quv markaz ma'muriyati bilan bog'laning:\n"
                "📞 Aloqa: +998 90 123 45 67\n"
                "Telegram: @zahro_admin",
                None,
            )
        msg = f"👨‍👩‍👧 <b>Sizning farzandlaringiz ({len(children)} ta):</b>\n\nBatafsil ma'lumot olish uchun quyidagi tugmani bosing:"
        return msg, get_parent_children_keyboard(children)

    if "dars jadval" in normalized:
        if not children:
            return "ℹ️ Sizga hali birorta farzand biriktirilmagan.", None
        msg = "📅 <b>Farzandlaringizning dars jadvali:</b>\n\n"
        for ch in children:
            groups = await get_student_groups(ch["student_id"])
            relation = f" ({ch['relation_type'].capitalize()})" if ch.get("relation_type") else ""
            msg += f"👶 <b>{ch['full_name']}{relation}:</b>\n"
            if not groups:
                msg += "   <i>Guruhlarga biriktirilmagan</i>\n\n"
            else:
                for g in groups:
                    room = f" ({g['room']}-xona)" if g["room"] else ""
                    teacher = f", Ustoz: {g['teacher_name']}" if g["teacher_name"] else ""
                    msg += f"   📚 <b>{g['name']}</b> ({g['subject']})\n      ⏰ {g['schedule'] or 'Belgilanmagan'}{room}{teacher}\n"
                msg += "\n"
        return msg, None

    if "to'lov" in normalized or "tarixi" in normalized:
        if not children:
            return "ℹ️ Sizga hali birorta farzand biriktirilmagan.", None
        msg = "💳 <b>Farzandlaringizning to'lovlar tarixi:</b>\n\n"
        for ch in children:
            payments = await get_student_payments(ch["student_id"])
            msg += f"👶 <b>{ch['full_name']}:</b>\n"
            if not payments:
                msg += "   <i>Hozircha to'lovlar mavjud emas</i>\n\n"
            else:
                for p in payments[:5]:
                    msg += f"   💵 {p['month_for']}: {p['amount']:,.0f} so'm ({p['group_name']}) - {p['payment_type']}\n"
                msg += "\n"
        return msg, None

    if "davomat" in normalized:
        if not children:
            return "ℹ️ Sizga hali birorta farzand biriktirilmagan.", None
        msg = "✅ <b>Farzandlaringizning davomat holati:</b>\n\n"
        for ch in children:
            att = await get_student_attendance(ch["student_id"], limit=5)
            msg += f"👶 <b>{ch['full_name']}:</b>\n"
            if not att:
                msg += "   <i>Davomat yozuvlari mavjud emas</i>\n\n"
            else:
                for a in att:
                    icon = "🟢 Keldi" if a["status"] == "keldi" else ("🔴 Kelmadi" if a["status"] == "kelmadi" else "🟡 Sababli")
                    msg += f"   📅 {a['date']} — {a['group_name']}: {icon}\n"
                msg += "\n"
        return msg, None

    return None, None



@router.message(CommandStart())
async def cmd_start(message: Message):
    telegram_id = message.from_user.id
    user = await get_user(telegram_id)
    effective_role = get_effective_role(telegram_id, user["role"] if user else "parent")

    if not user:
        if effective_role in {"super_admin", "admin"}:
            await add_user(
                telegram_id=telegram_id,
                full_name=message.from_user.full_name,
                phone="",
                role=effective_role,
            )
            webapp_url = await setup_user_webapp_menu(message.bot, telegram_id)
            await message.answer(
                f"Xush kelibsiz, {message.from_user.full_name}!\n\nSiz super admin sifatida tizimga kirdingiz.",
                reply_markup=get_main_keyboard(effective_role, webapp_url=webapp_url),
            )
            return

        await message.answer(
            f"Assalomu alaykum, {message.from_user.full_name}!\n"
            f"Zahro o'quv markazining rasmiy botiga xush kelibsiz.\n\n"
            f"Ro'yxatdan o'tish uchun telefon raqamingizni yuboring:",
            reply_markup=get_phone_keyboard(),
        )
        return

    if effective_role in {"super_admin", "admin"}:
        await add_user(
            telegram_id=telegram_id,
            full_name=user["full_name"],
            phone=user["phone"] or "",
            role=effective_role,
        )

    # Set up Telegram Chat Menu Button on bottom-left
    webapp_url = await setup_user_webapp_menu(message.bot, telegram_id, user)

    if effective_role == "super_admin":
        greeting = "🛡 Siz Super Admin paneliga kirdingiz."
    elif effective_role == "admin":
        greeting = "🛡 Siz Admin paneliga kirdingiz."
    elif effective_role == "teacher":
        greeting = "👨‍🏫 Siz O'qituvchi paneliga kirdingiz."
    elif effective_role == "student":
        greeting = "👨‍🎓 Siz O'quvchi kabinetiga kirdingiz."
    else:
        greeting = "👨‍👩‍👧 Siz Ota-ona kabinetiga kirdingiz."

    menu_hint = ""
    if webapp_url.startswith("https://"):
        menu_hint = "\n\n👉 <i>Ekranning chap pastki burchagidagi <b>Web App</b> tugmasi orqali shaxsiy kabinetingizga kirishingiz mumkin!</i>"

    await message.answer(
        f"Xush kelibsiz, <b>{user['full_name']}</b>!\n\n{greeting}{menu_hint}",
        reply_markup=get_main_keyboard(effective_role, webapp_url=webapp_url),
        parse_mode="HTML",
    )


@router.message(F.contact)
async def process_contact(message: Message):
    phone = message.contact.phone_number
    full_name = message.from_user.full_name
    effective_role = get_effective_role(message.from_user.id, "parent")

    if effective_role in {"super_admin", "admin"}:
        await add_user(
            telegram_id=message.from_user.id,
            full_name=full_name,
            phone=phone,
            role=effective_role,
        )
        webapp_url = await setup_user_webapp_menu(message.bot, message.from_user.id)
        await message.answer(
            f"✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!\nSiz tizimda <b>{effective_role}</b> sifatida qayd etildingiz.",
            reply_markup=get_main_keyboard(effective_role, webapp_url=webapp_url),
            parse_mode="HTML",
        )
        return

    # Normal user registration: register with default 'student', then let user choose
    await add_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        phone=phone,
        role="student",
    )
    user = await get_user(message.from_user.id)
    await setup_user_webapp_menu(message.bot, message.from_user.id, user)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    role_choice_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨‍🎓 O'quvchiman", callback_data="setrole_student"),
                InlineKeyboardButton(text="👨‍👩‍👧 Ota-onaman", callback_data="setrole_parent"),
            ]
        ]
    )

    await message.answer(
        f"✅ Rahmat, <b>{full_name}</b>! Telefon raqamingiz (<code>{phone}</code>) qabul qilindi.\n\n"
        f"Iltimos, o'quv markazimizdagi maqomingizni tanlang:",
        reply_markup=role_choice_kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("setrole_"))
async def handle_role_selection(callback: CallbackQuery):
    selected_role = callback.data.split("_")[1]
    telegram_id = callback.from_user.id
    await update_user_role(telegram_id, selected_role)
    user = await get_user(telegram_id)

    # Configure the persistent Chat Menu Button on bottom left
    webapp_url = await setup_user_webapp_menu(callback.bot, telegram_id, user)
    role_title = "👨‍🎓 O'quvchi" if selected_role == "student" else "👨‍👩‍👧 Ota-ona"

    webapp_notice = (
        "👉 Ekranning <b>chap pastki burchagidagi Web App</b> tugmasi orqali shaxsiy kabinetingizga istalgan vaqtda kirishingiz mumkin!"
        if webapp_url.startswith("https://")
        else f"👉 Shaxsiy kabinetingiz manzili: <a href='{webapp_url}'>{webapp_url}</a>"
    )

    await callback.message.edit_text(
        f"✅ Maqomingiz belgilandi: <b>{role_title}</b>\n\n"
        f"📱 <b>Web App kabinetingiz tayyor:</b>\n"
        f"{webapp_notice}\n\n"
        f"Quyidagi menyu orqali dars jadvali, davomat va to'lovlaringizni kuzatib boring.",
        parse_mode="HTML",
    )
    await callback.message.answer(
        "Asosiy menyu:",
        reply_markup=get_main_keyboard(selected_role, webapp_url=webapp_url),
    )
    await callback.answer()



# ==================== FEEDBACK & PARENT HANDLERS ====================

@router.message(F.text.in_({"💬 Murojaat va taklif", "murojaat va taklif", "murojaat", "/murojaat"}))
async def handle_feedback_start(message: Message):
    telegram_id = message.from_user.id
    user = await get_user(telegram_id)
    if not user:
        await message.answer("Iltimos, avval /start orqali ro'yxatdan o'ting.")
        return

    role = user["role"]
    if role == "parent":
        children = await get_parent_students(user["id"])
        child_id = children[0]["student_id"] if len(children) == 1 else None
        text = (
            "💬 <b>Murojaat va taklif yuborish</b>\n\n"
            "O'quv markazimiz faoliyati yoki ta'lim sifati bo'yicha fikr va takliflaringiz biz uchun juda muhim.\n"
            "Murojaat toifasini tanlang:"
        )
        await message.answer(text, reply_markup=get_feedback_type_keyboard(child_id), parse_mode="HTML")
    else:
        text = (
            "💬 <b>Murojaat va taklif yuborish</b>\n\n"
            "Savol, taklif yoki mulohazalaringiz bo'lsa, toifani tanlang:"
        )
        await message.answer(text, reply_markup=get_feedback_type_keyboard(user["id"]), parse_mode="HTML")


@router.callback_query(F.data.startswith("fbtype_"))
async def process_feedback_type(call: CallbackQuery):
    parts = call.data.split("_")
    student_id_val = int(parts[1]) if parts[1].isdigit() and int(parts[1]) > 0 else None
    fb_type = parts[2]

    FEEDBACK_SESSIONS[call.from_user.id] = {
        "student_id": student_id_val,
        "type": fb_type,
    }

    type_titles = {
        "taklif": "💡 Taklif",
        "shikoyat": "⚠️ Shikoyat",
        "savol": "❓ Savol",
        "boshqa": "📝 Boshqa",
    }
    title = type_titles.get(fb_type, fb_type.capitalize())

    await call.message.edit_text(
        f"✍️ <b>{title} toifasi bo'yicha murojaat matnini yuboring:</b>\n\n"
        f"Fikr-mulohazangizni bitta xabarda yozib yuboring. O'quv markaz ma'muriyati albatta ko'rib chiqadi va javob beradi.\n\n"
        f"<i>Bekor qilish uchun 'cancel' deb yozing.</i>",
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "fb_cancel")
async def cancel_feedback_flow(call: CallbackQuery):
    FEEDBACK_SESSIONS.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Murojaat bekor qilindi.")
    await call.answer()


@router.callback_query(F.data.startswith("child_view_"))
async def child_view_details(call: CallbackQuery):
    student_id = int(call.data.replace("child_view_", ""))
    student = await get_user_by_id(student_id)
    if not student:
        await call.answer("O'quvchi topilmadi.", show_alert=True)
        return

    groups = await get_student_groups(student_id)
    text = (
        f"👶 <b>Farzand: {student['full_name']}</b>\n"
        f"📞 Telefon: {student['phone'] or 'Kiritilmagan'}\n"
        f"📚 Guruhlar soni: {len(groups)} ta\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    await call.message.edit_text(text, reply_markup=get_child_details_keyboard(student_id), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("ch_sch_"))
async def child_schedule_detail(call: CallbackQuery):
    student_id = int(call.data.replace("ch_sch_", ""))
    student = await get_user_by_id(student_id)
    groups = await get_student_groups(student_id)

    msg = f"📅 <b>{student['full_name']} — Dars jadvali:</b>\n\n"
    if not groups:
        msg += "<i>Ushbu o'quvchi hali birorta guruhga biriktirilmagan.</i>"
    else:
        for g in groups:
            room = f" ({g['room']}-xona)" if g["room"] else ""
            teacher = f", Ustoz: {g['teacher_name']}" if g["teacher_name"] else ""
            msg += f"🔹 <b>{g['name']}</b> ({g['subject']})\n   ⏰ {g['schedule'] or 'Belgilanmagan'}{room}{teacher}\n\n"

    await call.message.answer(msg, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("ch_att_"))
async def child_attendance_detail(call: CallbackQuery):
    student_id = int(call.data.replace("ch_att_", ""))
    student = await get_user_by_id(student_id)
    att = await get_student_attendance(student_id, limit=10)

    msg = f"✅ <b>{student['full_name']} — Davomat tarixi:</b>\n\n"
    if not att:
        msg += "<i>Davomat ma'lumotlari hali mavjud emas.</i>"
    else:
        for a in att:
            icon = "🟢 Keldi" if a["status"] == "keldi" else ("🔴 Kelmadi" if a["status"] == "kelmadi" else "🟡 Sababli")
            msg += f"📅 {a['date']} — <b>{a['group_name']}</b>: {icon}\n"

    await call.message.answer(msg, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("ch_pay_"))
async def child_payment_detail(call: CallbackQuery):
    student_id = int(call.data.replace("ch_pay_", ""))
    student = await get_user_by_id(student_id)
    payments = await get_student_payments(student_id)

    msg = f"💳 <b>{student['full_name']} — To'lovlar tarixi:</b>\n\n"
    if not payments:
        msg += "<i>To'lovlar tarixi mavjud emas.</i>"
    else:
        for p in payments[:10]:
            msg += f"💵 <b>{p['month_for']}</b>: {p['amount']:,.0f} so'm ({p['group_name']}) - {p['payment_type'].capitalize()}\n"

    await call.message.answer(msg, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("ch_fb_"))
async def child_feedback_start(call: CallbackQuery):
    student_id = int(call.data.replace("ch_fb_", ""))
    await call.message.answer(
        "💬 <b>Ushbu farzandingiz bo'yicha murojaat toifasini tanlang:</b>",
        reply_markup=get_feedback_type_keyboard(student_id),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "child_back")
async def child_back_to_list(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.answer()
        return
    children = await get_parent_students(user["id"])
    await call.message.edit_text(
        f"👨‍👩‍👧 <b>Sizning farzandlaringiz ({len(children)} ta):</b>",
        reply_markup=get_parent_children_keyboard(children),
        parse_mode="HTML",
    )
    await call.answer()


# ==================== TEXT MESSAGE ROUTER ====================

@router.message(F.text)
async def process_text(message: Message):
    text = message.text or ""
    if not text:
        return

    normalized = text.strip().lower()
    user_id = message.from_user.id

    # Check admin reply session first
    if await handle_admin_reply_step(message):
        return

    # Check broadcast message session
    if await handle_broadcast_message(message):
        return

    # Check feedback submission session
    if user_id in FEEDBACK_SESSIONS:
        if normalized in {"cancel", "bekor", "/cancel"}:
            FEEDBACK_SESSIONS.pop(user_id, None)
            await message.answer("❌ Murojaat bekor qilindi.")
            return

        session = FEEDBACK_SESSIONS.pop(user_id)
        user = await get_user(user_id)
        role = get_effective_role(user_id, user["role"] if user else "parent")
        fb_id = await create_feedback(
            user_id=user["id"] if user else 1,
            message=text,
            feedback_type=session["type"],
            student_id=session["student_id"],
        )
        await notify_new_feedback(fb_id)
        await message.answer(
            "✅ <b>Murojaatingiz ma'muriyatga muvaffaqiyatli yuborildi!</b>\n\n"
            "Tez orada mas'ul xodimlar tomonidan ko'rib chiqilib, ushbu bot orqali javob qaytariladi.",
            reply_markup=get_main_keyboard(role),
            parse_mode="HTML",
        )
        return

    if normalized in {"qayta ishga tushirish", "/restart", "restart"}:
        if user_id in CREATION_SESSIONS:
            CREATION_SESSIONS.pop(user_id, None)
        await cmd_start(message)
        return

    if user_id in CREATION_SESSIONS and should_cancel_creation_session(text):
        CREATION_SESSIONS.pop(user_id, None)

    if user_id in CREATION_SESSIONS:
        await _handle_creation_step(message)
        return

    if is_admin_creation_cmd(text):
        await start_creation_wizard(message, role="admin", label="Admin")
        return

    if is_teacher_creation_cmd(text):
        await start_creation_wizard(message, role="teacher", label="Ustoz")
        return

    user = await get_user(user_id)
    role = get_effective_role(user_id, user["role"] if user else "parent")

    # Personal WebApp cabinet (direct popup button without raw text link)
    if normalized in {"crm web app", "📊 crm web app", "crm", "web app", "📱 shaxsiy kabinet", "shaxsiy kabinet", "kabinet"}:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

        if role in {"super_admin", "admin"}:
            url = get_webapp_url("/admin")
            title = "⚡️ Admin Portali"
        elif role == "teacher" and user:
            url = get_webapp_url(f"/teacher/{user['id']}")
            title = "👨‍🏫 Ustoz Portali"
        elif user:
            if role == "parent":
                children = await get_parent_students(user["id"])
                target_id = children[0]["student_id"] if children else user["id"]
                title = "👨‍👩‍👧 Ota-ona Portali"
                url = get_webapp_url(f"/parent/{target_id}")
            else:
                target_id = user["id"]
                title = "👨‍🎓 O'quvchi Portali"
                url = get_webapp_url(f"/student/{target_id}")
        else:
            url = get_webapp_url("/")
            title = "🌐 EduCenter Web App"

        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{title}ni ochish", web_app=WebAppInfo(url=url))]
            ]
        )
        await message.answer(
            f"📱 <b>{title}:</b>\nPastdagi tugmani bosing, to'g'ridan-to'g'ri ochiladi:",
            reply_markup=inline_kb,
            parse_mode="HTML",
        )
        return

    # Check for parent-specific queries if role is parent
    if role == "parent" and user:
        parent_text, parent_kb = await get_real_parent_data_reply(user, text)
        if parent_text:
            reply_kb = parent_kb if parent_kb else get_main_keyboard(role)
            await message.answer(parent_text, reply_markup=reply_kb, parse_mode="HTML")
            return

    # Check for student real data
    real_reply = await get_real_student_data_reply(user, text)
    if real_reply:
        await message.answer(real_reply, reply_markup=get_main_keyboard(role), parse_mode="HTML")
        return

    reply = build_student_reply(text)
    await message.answer(reply, reply_markup=get_main_keyboard(role))