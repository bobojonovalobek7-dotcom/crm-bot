import aiosqlite
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, is_admin, is_super_admin, get_webapp_url
from database.db import (
    add_user,
    get_user,
    get_user_by_id,
    get_stats_summary,
    get_all_users,
    get_users_by_role,
    add_payment,
    get_feedbacks,
    get_feedback_by_id,
    reply_to_feedback,
)
from database.models import DB_NAME
from bot.keyboards.inline import get_admin_broadcast_keyboard, get_admin_feedback_action_keyboard
from services.notifications import notify_payment_receipt, notify_feedback_reply

router = Router()
CREATION_SESSIONS: dict[int, dict[str, str]] = {}
BROADCAST_SESSIONS: dict[int, dict[str, str]] = {}
ADMIN_REPLY_SESSIONS: dict[int, int] = {}
_FAKE_TELEGRAM_IDS = {123456789, 111111111, 999999999, 1234567890, 1000000000}


def validate_telegram_id(raw_value: str) -> tuple[bool, int | None, str | None]:
    value = (raw_value or "").strip()
    if not value:
        return False, None, "Telegram ID kiriting."

    try:
        telegram_id = int(value)
    except ValueError:
        return False, None, "Telegram ID faqat raqam bo'lishi kerak."

    if telegram_id <= 0:
        return False, None, "Telegram ID musbat son bo'lishi kerak."

    if telegram_id < 100000 or telegram_id in _FAKE_TELEGRAM_IDS:
        return False, None, "Telegram ID haqiqiy bo'lishi shart. Tasodifiy yoki placeholder ID kiritmang."

    return True, telegram_id, None


def should_cancel_creation_session(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {
        "crm web app",
        "web app",
        "crm",
        "yangi admin",
        "yangi ustoz",
        "yangi oqituvchi",
        "yangi teacher",
        "hisobotlar",
        "📈 hisobotlar",
        "murojaatlar",
        "💬 murojaatlar",
        "/feedbacks",
        "/murojaatlar",
        "xabar yuborish",
        "📣 xabar yuborish",
        "qayta ishga tushirish",
        "restart",
        "/restart",
        "/start",
        "start",
    }


async def _is_real_telegram_user(telegram_id: int, bot: Bot | None = None) -> bool:
    close_needed = False
    if bot is None:
        bot = Bot(token=BOT_TOKEN)
        close_needed = True

    try:
        await bot.get_chat(chat_id=telegram_id)
        return True
    except Exception:
        return False
    finally:
        if close_needed:
            await bot.close()


def _is_admin_user(user_id: int | None) -> bool:
    return bool(is_super_admin(user_id) or is_admin(user_id))


async def start_creation_wizard(message: Message, role: str, label: str):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat admin va super admin uchun.")
        return

    CREATION_SESSIONS[message.from_user.id] = {
        "role": role,
        "label": label,
        "step": "full_name",
    }
    await message.answer(
        f"🧩 {label} yaratish uchun 1/3 bosqich:\n\n"
        "Ism va familiyangizni kiriting.\n\n"
        "Bekor qilish uchun: cancel"
    )


async def _handle_creation_step(message: Message):
    user_id = message.from_user.id
    session = CREATION_SESSIONS.get(user_id)
    if not session:
        return

    role = session["role"]
    label = session["label"]
    step = session["step"]
    text = (message.text or "").strip()

    normalized = text.strip().lower()
    if normalized in {"cancel", "bekor qilish", "otmen", "cancelled"}:
        CREATION_SESSIONS.pop(user_id, None)
        await message.answer("❌ Yaratish bekor qilindi.")
        return

    if step == "full_name":
        if len(text) < 2:
            await message.answer("❗ Ism va familiyangizni to'liq kiriting.")
            return
        session["full_name"] = text
        session["step"] = "phone"
        await message.answer("2/3 bosqich: Telefon raqamingizni kiriting.\n\nBekor qilish uchun: cancel")
        return

    if step == "phone":
        if len(text) < 5:
            await message.answer("❗ Telefon raqamni to'g'ri kiriting.")
            return
        session["phone"] = text
        session["step"] = "telegram_id"
        await message.answer("3/3 bosqich: Telegram ID ni kiriting.\n\nBekor qilish uchun: cancel")
        return

    if step == "telegram_id":
        ok, telegram_id, error = validate_telegram_id(text)
        if not ok:
            await message.answer(f"❗ {error}")
            return

        existing = await get_user(telegram_id)
        if existing:
            await message.answer("❗ Bu Telegram ID allaqachon ro'yxatdan o'tgan.")
            return

        if not await _is_real_telegram_user(telegram_id, message.bot):
            await message.answer("❗ Bu Telegram ID haqiqiy foydalanuvchi hisobiga tegishli emas. Qayta kiriting.")
            return

        full_name = session.get("full_name", "")
        phone = session.get("phone", "")
        await add_user(telegram_id=telegram_id, full_name=full_name, phone=phone, role=role)
        await message.answer(f"✅ {label} muvaffaqiyatli yaratildi: {full_name}")
        CREATION_SESSIONS.pop(user_id, None)


async def _create_user_via_bot(message: Message, role: str, command_name: str):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat admin va super admin uchun.")
        return

    text = (message.text or "").strip()
    if text.lower() in {f"/{command_name}", f"/{command_name} "}:
        await start_creation_wizard(message, role=role, label=role.capitalize())
        return

    parts = [part.strip() for part in text.replace(f"/{command_name}", "", 1).split("|") if part.strip()]
    if len(parts) < 3:
        await message.answer(
            f"❗ Noto'g'ri format. Qayta kiriting:\n/{command_name} <Ism Familiya> | <Telefon> | <Telegram ID>"
        )
        return

    full_name = parts[0]
    phone = parts[1]
    ok, telegram_id, error = validate_telegram_id(parts[2])
    if not ok:
        await message.answer(f"❗ {error}")
        return

    existing = await get_user(telegram_id)
    if existing:
        await message.answer("❗ Bu Telegram ID allaqachon ro'yxatdan o'tgan.")
        return

    if not await _is_real_telegram_user(telegram_id, message.bot):
        await message.answer("❗ Bu Telegram ID haqiqiy foydalanuvchi hisobiga tegishli emas. Qayta kiriting.")
        return

    await add_user(telegram_id=telegram_id, full_name=full_name, phone=phone, role=role)
    await message.answer(f"✅ {role.upper()} muvaffaqiyatli yaratildi: {full_name}")


async def _create_payment_via_bot(message: Message):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ To'lov qabul qilish faqat adminlar uchun.")
        return

    text = (message.text or "").strip()
    if text.lower() in {"/add_payment", "/add_payment ", "yangi to'lov", "💰 yangi to'lov"}:
        await message.answer(
            "💳 <b>To'lovni qabul qilish formati:</b>\n\n"
            "<code>/add_payment student_id | group_id | amount | payment_type | month_for | note</code>\n\n"
            "Misol:\n"
            "<code>/add_payment 1 | 1 | 350000 | naqd | 2026-09 | Sentyabr oyi uchun</code>\n\n"
            "<i>Yoki WebApp CRM orqali qulayroq qabul qilishingiz mumkin:</i>\n"
            f"👉 {get_webapp_url('/admin')}",
            parse_mode="HTML",
        )
        return

    parts = [part.strip() for part in text.replace("/add_payment", "", 1).split("|") if part.strip()]
    if len(parts) < 5:
        await message.answer("❗ Format xato. Qayta kiriting: /add_payment student_id | group_id | amount | payment_type | month_for | note")
        return

    try:
        student_id = int(parts[0])
        group_id = int(parts[1])
        amount = float(parts[2])
        payment_type = parts[3]
        month_for = parts[4]
        note = parts[5] if len(parts) > 5 else ""
    except ValueError:
        await message.answer("❗ Ma'lumotlar turida xatolik. Raqamlarni to'g'ri kiriting.")
        return

    await add_payment(
        student_id=student_id,
        group_id=group_id,
        amount=amount,
        payment_type=payment_type,
        month_for=month_for,
        note=note,
    )

    await notify_payment_receipt(
        student_id=student_id,
        group_id=group_id,
        amount=amount,
        payment_type=payment_type,
        month_for=month_for,
        note=note,
    )

    await message.answer("✅ To'lov saqlandi va o'quvchi hamda unga biriktirilgan barcha ota-onalarga kvitansiya jo'natildi!")


@router.message(F.text == "/admin")
async def admin_command(message: Message):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return
    url = get_webapp_url("/admin")
    await message.answer(
        f"🛠 <b>Zahro CRM Boshqaruv Paneli:</b>\n\n"
        f"Guruhlar, to'lovlar, o'quvchilar va hisobotlar:\n"
        f"👉 <a href='{url}'>{url}</a>",
        parse_mode="HTML",
    )


@router.message(F.text.in_({"📈 Hisobotlar", "hisobotlar", "/stats"}))
async def admin_stats_command(message: Message):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ Bu ma'lumot faqat adminlar uchun.")
        return

    stats = await get_stats_summary()
    url = get_webapp_url("/admin")

    text = (
        "📊 <b>Zahro o'quv markazi — Umumiy Hisobot</b>\n\n"
        f"👨‍🎓 <b>Jami o'quvchilar:</b> {stats['students']} ta\n"
        f"👩‍🏫 <b>O'qituvchilar:</b> {stats['teachers']} ta\n"
        f"📚 <b>Faol guruhlar:</b> {stats['groups']} ta\n"
        f"💰 <b>Umumiy tushum:</b> {stats['total_revenue']:,.0f} so'm\n"
        f"📈 <b>O'rtacha davomat:</b> {stats['attendance_rate']:.1f}%\n\n"
        f"Batafsil CRM orqali ko'rish:\n👉 <a href='{url}'>{url}</a>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_({"📣 Xabar yuborish", "xabar yuborish"}))
async def admin_broadcast_prompt(message: Message):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ Faqat adminlar uchun.")
        return

    await message.answer(
        "📣 <b>Kimlarga xabar yubormoqchisiz?</b>\nKerakli auditoriyani tanlang:",
        reply_markup=get_admin_broadcast_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("bc_"))
async def process_broadcast_choice(call: CallbackQuery):
    choice = call.data.replace("bc_", "")
    if choice == "cancel":
        await call.message.edit_text("❌ Xabar yuborish bekor qilindi.")
        await call.answer()
        return

    BROADCAST_SESSIONS[call.from_user.id] = {"target": choice}
    target_names = {
        "parents": "barcha o'quvchi va ota-onalarga",
        "teachers": "barcha o'qituvchilarga",
        "all": "barcha foydalanuvchilarga",
    }
    target_name = target_names.get(choice, "foydalanuvchilarga")

    await call.message.edit_text(
        f"✍️ <b>{target_name.capitalize()} yuboriladigan xabar matnini kiriting:</b>\n\n"
        f"<i>Xabarni bekor qilish uchun 'cancel' deb yozing.</i>",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(F.text.startswith("/create_admin"))
async def create_admin_command(message: Message):
    await _create_user_via_bot(message, role="admin", command_name="create_admin")


@router.message(F.text.startswith("/create_teacher"))
async def create_teacher_command(message: Message):
    await _create_user_via_bot(message, role="teacher", command_name="create_teacher")


@router.message(F.text.startswith("/add_payment"))
async def add_payment_command(message: Message):
    await _create_payment_via_bot(message)


@router.message(F.text.in_({"💰 Yangi to'lov", "yangi to'lov"}))
async def add_payment_button(message: Message):
    await _create_payment_via_bot(message)


# ==================== FEEDBACKS & BROADCAST PROCESSING ====================

@router.message(F.text.in_({"💬 Murojaatlar", "murojaatlar", "/feedbacks", "/murojaatlar"}))
async def admin_feedbacks_command(message: Message):
    if not _is_admin_user(message.from_user.id):
        await message.answer("❌ Bu bo'lim faqat adminlar uchun.")
        return

    feedbacks = await get_feedbacks(limit=10)
    if not feedbacks:
        await message.answer("ℹ️ Hozircha murojaat va takliflar mavjud emas.")
        return

    await message.answer("📬 <b>So'nggi murojaat va takliflar:</b>", parse_mode="HTML")
    for fb in feedbacks:
        status_icon = "🟢 Yangi" if fb["status"] == "yangi" else ("🟡 Ko'rildi" if fb["status"] == "korildi" else "✅ Javob berilgan")
        student_info = f"\n👶 O'quvchi: <b>{fb['student_name']}</b>" if fb["student_name"] else ""
        reply_info = f"\n\n💬 <b>Javob ({fb['admin_name'] or 'Admin'}):</b>\n{fb['admin_reply']}" if fb["admin_reply"] else ""

        text = (
            f"📌 <b>Murojaat #{fb['id']} — {fb['feedback_type'].upper()}</b> ({status_icon})\n"
            f"👤 <b>Kimdan:</b> {fb['user_name']} ({fb['user_role']})\n"
            f"📞 <b>Telefon:</b> {fb['user_phone'] or 'Ko\'rsatilmagan'}{student_info}\n"
            f"📅 <b>Sana:</b> {fb['created_at'][:16] if fb['created_at'] else ''}\n\n"
            f"📝 <b>Xabar:</b>\n«{fb['message']}»{reply_info}"
        )
        kb = get_admin_feedback_action_keyboard(fb["id"]) if fb["status"] != "javob_berildi" else None
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admfb_reply_"))
async def prompt_admin_feedback_reply(call: CallbackQuery):
    if not _is_admin_user(call.from_user.id):
        await call.answer("Faqat adminlar uchun.", show_alert=True)
        return

    feedback_id = int(call.data.replace("admfb_reply_", ""))
    ADMIN_REPLY_SESSIONS[call.from_user.id] = feedback_id

    await call.message.answer(
        f"✍️ <b>#{feedback_id}-sonli murojaat uchun javobingizni yuboring:</b>\n\n"
        f"<i>Bekor qilish uchun 'cancel' deb yozing.</i>",
        parse_mode="HTML",
    )
    await call.answer()


async def handle_admin_reply_step(message: Message) -> bool:
    user_id = message.from_user.id
    if user_id not in ADMIN_REPLY_SESSIONS:
        return False

    feedback_id = ADMIN_REPLY_SESSIONS.pop(user_id)
    text = (message.text or "").strip()

    if text.lower() in {"cancel", "bekor"}:
        await message.answer("❌ Murojaatga javob berish bekor qilindi.")
        return True

    admin_user = await get_user(user_id)
    admin_id = admin_user["id"] if admin_user else 1

    await reply_to_feedback(feedback_id=feedback_id, reply_text=text, admin_id=admin_id)
    await notify_feedback_reply(feedback_id)
    await message.answer(f"✅ #{feedback_id}-sonli murojaatga javob muvaffaqiyatli yetkazildi!")
    return True


async def handle_broadcast_message(message: Message) -> bool:
    user_id = message.from_user.id
    if user_id not in BROADCAST_SESSIONS:
        return False

    session = BROADCAST_SESSIONS.pop(user_id)
    text = (message.text or "").strip()

    if text.lower() in {"cancel", "bekor"}:
        await message.answer("❌ Xabar yuborish bekor qilindi.")
        return True

    target = session["target"]
    if target == "parents":
        parents = await get_users_by_role("parent")
        students = await get_users_by_role("student")
        target_users = parents + students
    elif target == "teachers":
        target_users = await get_users_by_role("teacher")
    else:
        target_users = await get_all_users()

    sent = 0
    formatted_msg = (
        f"📢 <b>O'quv markaz ma'muriyatidan e'lon:</b>\n\n"
        f"{text}\n\n"
        f"<i>Zahro o'quv markazi</i>"
    )

    for u in target_users:
        if u["telegram_id"]:
            try:
                await message.bot.send_message(chat_id=u["telegram_id"], text=formatted_msg, parse_mode="HTML")
                sent += 1
            except Exception:
                pass

    await message.answer(f"✅ Xabar muvaffaqiyatli tarqatildi!\nJami qabul qilganlar: {sent} ta foydalanuvchi.")
    return True

