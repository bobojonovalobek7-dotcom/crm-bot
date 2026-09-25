import aiosqlite
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import BOT_TOKEN, SUPER_ADMIN_IDS, is_admin, is_super_admin, get_webapp_url
from database.db import (
    add_user,
    get_user,
    get_user_by_id,
    get_stats_summary,
    get_all_users,
    get_users_by_role,
    add_payment,
    get_groups,
    get_group_by_id,
    get_group_students,
    get_feedbacks,
    get_feedback_by_id,
    reply_to_feedback,
    remove_admin,
    remove_admin_by_telegram_id,
)
from database.models import DB_NAME
from bot.keyboards.inline import (
    get_admin_broadcast_keyboard,
    get_admin_feedback_action_keyboard,
    get_admins_management_keyboard,
    get_confirm_delete_admin_keyboard,
)
from services.notifications import notify_payment_receipt, notify_feedback_reply

router = Router()
CREATION_SESSIONS: dict[int, dict[str, str]] = {}
BROADCAST_SESSIONS: dict[int, dict[str, str]] = {}
ADMIN_REPLY_SESSIONS: dict[int, int] = {}
PAYMENT_WIZARD_SESSIONS: dict[int, dict] = {}
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
    if not value:
        return False
    stripped = value.strip()
    if stripped.isdigit():
        return False

    norm = stripped.lower()
    clean = "".join(ch for ch in norm if ch.isalnum() or ch.isspace() or ch in "'-/")
    clean = " ".join(clean.split())

    cancel_keywords = {
        "cancel", "bekor", "bekor qilish", "otmen", "to'xtat", "chiqish", "/cancel",
        "qayta ishga tushirish", "qayta", "restart", "/restart", "/start", "start",
        "yangi admin", "yangi ustoz", "yangi oqituvchi", "yangi teacher", "yangi to'lov", "yangi tolov",
        "to'lov", "tolov", "adminlar", "hisobotlar", "murojaatlar", "/feedbacks", "/murojaatlar",
        "/admins", "/adminlar", "xabar yuborish", "crm web app", "web app", "crm", "kabinet",
    }
    if clean in cancel_keywords or norm in cancel_keywords:
        return True

    if any(k in clean for k in ["qayta ishga tushirish", "restart", "yangi admin", "yangi ustoz", "yangi tolov", "yangi to'lov", "xabar yuborish"]):
        return True

    return False


async def _is_real_telegram_user(telegram_id: int, bot: Bot | None = None) -> bool:
    # Always allow valid structural telegram IDs. Telegram get_chat() returns 'Chat not found'
    # if the person hasn't started the bot yet, which would prevent admins from adding new teachers/admins.
    return True


async def _is_admin_user(user_id: int | None) -> bool:
    if not user_id:
        return False
    if is_super_admin(user_id) or is_admin(user_id):
        return True
    user = await get_user(user_id)
    return bool(user and user.get("role") in {"super_admin", "admin"})


def is_admin_creation_cmd(text: str) -> bool:
    if not text:
        return False
    norm = text.strip().lower()
    if any(norm.startswith(cmd) for cmd in ["/create_admin", "/add_admin", "/addadmin", "/new_admin"]):
        return True
    clean = "".join(ch for ch in norm if ch.isalnum() or ch.isspace() or ch in "'-")
    if "admin" in clean and any(k in clean for k in ["qo'sh", "qosh", "yarat", "yangi"]):
        return True
    if clean.strip() in {"yangi admin", "admin qoshish", "admin qo'shish", "admin"}:
        return True
    return False


def is_teacher_creation_cmd(text: str) -> bool:
    if not text:
        return False
    norm = text.strip().lower()
    if any(norm.startswith(cmd) for cmd in ["/create_teacher", "/add_teacher", "/addteacher", "/new_teacher"]):
        return True
    clean = "".join(ch for ch in norm if ch.isalnum() or ch.isspace() or ch in "'-")
    if any(t in clean for t in ["ustoz", "o'qituvchi", "oqituvchi", "teacher"]) and any(k in clean for k in ["qo'sh", "qosh", "yarat", "yangi"]):
        return True
    if clean.strip() in {"yangi ustoz", "ustoz qoshish", "ustoz qo'shish"}:
        return True
    return False


def is_payment_cmd(text: str) -> bool:
    if not text:
        return False
    norm = text.strip().lower()
    if any(norm.startswith(cmd) for cmd in ["/add_payment", "/addpayment", "/pay"]):
        return True
    clean = "".join(ch for ch in norm if ch.isalnum() or ch.isspace() or ch in "'-")
    if any(p in clean for p in ["tolov", "to'lov", "tulov"]):
        if any(k in clean for k in ["yangi", "qabul", "qilish", "qo'sh", "qosh"]):
            return True
        if clean.strip() in {"tolov", "to'lov", "yangi to'lov", "yangi tolov"}:
            return True
    return False


async def start_creation_wizard(message: Message, role: str, label: str, target_user_id: int | None = None):
    caller_id = target_user_id or (message.from_user.id if message.from_user else None)
    if not await _is_admin_user(caller_id):
        await message.answer("❌ Bu buyruq faqat admin va super admin uchun.")
        return

    CREATION_SESSIONS[caller_id] = {
        "role": role,
        "label": label,
        "step": "full_name",
    }
    await message.answer(
        f"🧩 <b>Yangi {label} qo'shish</b> (1/3 bosqich):\n\n"
        f"Iltimos, {label.lower()}ning <b>ism va familiyasi</b>ni kiriting.\n"
        f"<i>(Masalan: Sardor Rahimov)</i>\n\n"
        "Bekor qilish uchun: <code>cancel</code>",
        parse_mode="HTML"
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

    if should_cancel_creation_session(text):
        CREATION_SESSIONS.pop(user_id, None)
        await message.answer("❌ Jarayon bekor qilindi.")
        return

    if step == "full_name":
        if len(text) < 2:
            await message.answer("❗ Ism va familiyangizni to'liq kiriting.")
            return
        session["full_name"] = text
        session["step"] = "phone"
        await message.answer(
            f"📞 <b>{label} qo'shish</b> (2/3 bosqich):\n\n"
            "Telefon raqamini kiriting <i>(masalan: +998901234567)</i>:\n\n"
            "Bekor qilish uchun: <code>cancel</code>",
            parse_mode="HTML"
        )
        return

    if step == "phone":
        if len(text) < 5:
            await message.answer("❗ Telefon raqamni to'g'ri kiriting.")
            return
        session["phone"] = text
        session["step"] = "telegram_id"
        await message.answer(
            f"🆔 <b>{label} qo'shish</b> (3/3 bosqich):\n\n"
            "Foydalanuvchining <b>Telegram ID</b> raqamini kiriting:\n"
            "<i>(Telegram ID raqamini @userinfobot orqali bilish mumkin)</i>\n\n"
            "Bekor qilish uchun: <code>cancel</code>",
            parse_mode="HTML"
        )
        return

    if step == "telegram_id":
        if not text.isdigit():
            CREATION_SESSIONS.pop(user_id, None)
            from bot.keyboards.default import get_main_keyboard
            caller_user = await get_user(user_id)
            caller_role = caller_user["role"] if caller_user else "admin"
            await message.answer(
                "⚠️ Jarayon bekor qilindi (Telegram ID kiritilmadi).\n"
                "Qaytadan boshlash uchun kerakli tugmani bosing.",
                reply_markup=get_main_keyboard(caller_role),
                parse_mode="HTML"
            )
            return

        ok, telegram_id, error = validate_telegram_id(text)
        if not ok:
            await message.answer(f"❗ {error}\n\nBekor qilish uchun: <code>cancel</code>", parse_mode="HTML")
            return

        full_name = session.get("full_name", "")
        phone = session.get("phone", "")
        await add_user(telegram_id=telegram_id, full_name=full_name, phone=phone, role=role)
        CREATION_SESSIONS.pop(user_id, None)

        from bot.keyboards.default import get_main_keyboard
        caller_user = await get_user(user_id)
        caller_role = caller_user["role"] if caller_user else "admin"
        await message.answer(
            f"✅ <b>{label} muvaffaqiyatli qo'shildi!</b>\n\n"
            f"👤 <b>Ism:</b> {full_name}\n"
            f"📞 <b>Telefon:</b> {phone}\n"
            f"🆔 <b>Telegram ID:</b> {telegram_id}\n"
            f"🏷 <b>Roli:</b> {role.upper()}",
            reply_markup=get_main_keyboard(caller_role),
            parse_mode="HTML"
        )


async def _create_user_via_bot(message: Message, role: str, command_name: str):
    if not await _is_admin_user(message.from_user.id):
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

    await add_user(telegram_id=telegram_id, full_name=full_name, phone=phone, role=role)
    await message.answer(f"✅ {role.upper()} muvaffaqiyatli yaratildi: {full_name}")


async def start_payment_wizard(message: Message, target_user_id: int | None = None):
    caller_id = target_user_id or (message.from_user.id if message.from_user else None)
    if not await _is_admin_user(caller_id):
        await message.answer("❌ Bu buyruq faqat adminlar uchun.")
        return

    groups = await get_groups()
    if not groups:
        await message.answer(
            "ℹ️ Hozircha tizimda guruhlar mavjud emas.\n"
            f"Avval guruh yaratishingiz lozim: {get_webapp_url('/admin')}"
        )
        return

    PAYMENT_WIZARD_SESSIONS[caller_id] = {
        "step": "choose_group"
    }

    buttons = []
    for g in groups[:8]:
        fee = g.get("monthly_fee", 0)
        fee_str = f" ({fee:,.0f} so'm)" if fee else ""
        buttons.append([
            InlineKeyboardButton(text=f"📚 {g['name']}{fee_str}", callback_data=f"pw_g_{g['id']}")
        ])

    webapp_url = get_webapp_url("/admin")
    if webapp_url.startswith("https://"):
        buttons.append([InlineKeyboardButton(text="📱 Web App orqali to'lov", web_app=WebAppInfo(url=webapp_url))])
    else:
        buttons.append([InlineKeyboardButton(text="🌐 CRM da to'lov qilish", url=webapp_url)])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "💰 <b>Yangi to'lov qabul qilish</b> (1/4 bosqich):\n\n"
        "Qaysi <b>guruh</b> uchun to'lov qilinmoqda? Guruhni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )


async def _handle_payment_wizard_text(message: Message) -> bool:
    user_id = message.from_user.id
    session = PAYMENT_WIZARD_SESSIONS.get(user_id)
    if not session:
        return False

    text = (message.text or "").strip()
    if text.lower() in {"cancel", "bekor", "bekor qilish", "/cancel"}:
        PAYMENT_WIZARD_SESSIONS.pop(user_id, None)
        await message.answer("❌ To'lov qabul qilish bekor qilindi.")
        return True

    step = session.get("step")

    if step == "input_student_manual":
        if text.isdigit():
            std_id = int(text)
            std = await get_user_by_id(std_id)
            student_name = std["full_name"] if std else f"O'quvchi #{std_id}"
            session["student_id"] = std_id
            session["student_name"] = student_name
        else:
            all_stds = await get_users_by_role("student")
            match = next((s for s in all_stds if text.lower() in s["full_name"].lower()), None)
            if match:
                session["student_id"] = match["id"]
                session["student_name"] = match["full_name"]
            else:
                await add_user(telegram_id=None, full_name=text, role="student")
                from database.db import get_db
                async with get_db() as db:
                    async with db.execute("SELECT id FROM users WHERE full_name = ? ORDER BY id DESC LIMIT 1", (text,)) as cur:
                        row = await cur.fetchone()
                        session["student_id"] = row[0] if row else 1
                session["student_name"] = text

        session["step"] = "choose_amount"
        monthly_fee = float(session.get("monthly_fee", 400000))
        half_fee = monthly_fee / 2.0

        buttons = [
            [InlineKeyboardButton(text=f"💵 {monthly_fee:,.0f} so'm (To'liq oy)", callback_data=f"pw_amt_{int(monthly_fee)}")],
            [InlineKeyboardButton(text=f"💵 {half_fee:,.0f} so'm (Yarim oy)", callback_data=f"pw_amt_{int(half_fee)}")],
            [InlineKeyboardButton(text="✍️ Boshqa summa kiritish", callback_data="pw_amt_manual")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            f"💵 <b>To'lov summasi</b> (3/4 bosqich):\n\n"
            f"👤 <b>O'quvchi:</b> {session['student_name']}\n"
            f"📚 <b>Guruh:</b> {session['group_name']}\n\n"
            f"To'lov summasini tanlang yoki raqam yozing:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return True

    if step == "input_amount_manual":
        clean_num = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        try:
            val = float(clean_num)
            if val <= 0:
                await message.answer("❗ Summa musbat son bo'lishi kerak. Qayta kiriting:")
                return True
        except ValueError:
            await message.answer("❗ Summani raqamda kiriting (masalan: 350000):")
            return True

        session["amount"] = val
        session["step"] = "choose_type"
        buttons = [
            [InlineKeyboardButton(text="💵 Naqd pul", callback_data="pw_type_naqd")],
            [InlineKeyboardButton(text="💳 Plastik karta", callback_data="pw_type_karta")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            f"💳 <b>To'lov usuli</b> (4/4 bosqich):\n\n"
            f"👤 <b>O'quvchi:</b> {session['student_name']}\n"
            f"📚 <b>Guruh:</b> {session['group_name']}\n"
            f"💵 <b>Summa:</b> {val:,.0f} so'm\n\n"
            f"To'lov qaysi usulda amalga oshirilmoqda?",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return True

    return False


async def _create_payment_via_bot(message: Message):
    if not await _is_admin_user(message.from_user.id):
        await message.answer("❌ To'lov qabul qilish faqat adminlar uchun.")
        return

    text = (message.text or "").strip()
    if "|" not in text:
        await start_payment_wizard(message)
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


# ==================== SESSION MESSAGE INTERCEPTORS ====================

@router.message(lambda msg: msg.from_user and msg.from_user.id in PAYMENT_WIZARD_SESSIONS and not should_cancel_creation_session(msg.text or ""))
async def process_payment_wizard_session(message: Message):
    await _handle_payment_wizard_text(message)


@router.message(lambda msg: msg.from_user and msg.from_user.id in CREATION_SESSIONS and not should_cancel_creation_session(msg.text or ""))
async def process_creation_session(message: Message):
    await _handle_creation_step(message)


@router.message(lambda msg: msg.from_user and msg.from_user.id in ADMIN_REPLY_SESSIONS)
async def process_admin_reply_session(message: Message):
    await handle_admin_reply_step(message)


@router.message(lambda msg: msg.from_user and msg.from_user.id in BROADCAST_SESSIONS)
async def process_broadcast_session(message: Message):
    await handle_broadcast_message(message)


# ==================== COMMAND & BUTTON HANDLERS ====================

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


@router.message(lambda msg: is_admin_creation_cmd(msg.text or ""))
async def create_admin_command(message: Message):
    text = (message.text or "").strip()
    if "|" in text:
        await _create_user_via_bot(message, role="admin", command_name="create_admin")
    else:
        await start_creation_wizard(message, role="admin", label="Admin")


@router.message(lambda msg: is_teacher_creation_cmd(msg.text or ""))
async def create_teacher_command(message: Message):
    text = (message.text or "").strip()
    if "|" in text:
        await _create_user_via_bot(message, role="teacher", command_name="create_teacher")
    else:
        await start_creation_wizard(message, role="teacher", label="Ustoz")


@router.message(lambda msg: is_payment_cmd(msg.text or ""))
async def add_payment_button(message: Message):
    await _create_payment_via_bot(message)


# ==================== PAYMENT WIZARD CALLBACKS ====================

@router.callback_query(F.data == "pw_cancel")
async def process_payment_cancel(call: CallbackQuery):
    PAYMENT_WIZARD_SESSIONS.pop(call.from_user.id, None)
    await call.message.edit_text("❌ To'lov qabul qilish bekor qilindi.")
    await call.answer()


@router.callback_query(F.data.startswith("pw_g_"))
async def process_payment_group_choice(call: CallbackQuery):
    user_id = call.from_user.id
    group_id = int(call.data.replace("pw_g_", ""))
    group = await get_group_by_id(group_id)
    if not group:
        await call.answer("Guruh topilmadi.")
        return

    session = PAYMENT_WIZARD_SESSIONS.get(user_id, {})
    session["group_id"] = group_id
    session["group_name"] = group["name"]
    session["monthly_fee"] = group["monthly_fee"]
    session["step"] = "choose_student"
    PAYMENT_WIZARD_SESSIONS[user_id] = session

    students = await get_group_students(group_id)
    if not students:
        students = await get_users_by_role("student")

    if not students:
        session["step"] = "input_student_manual"
        PAYMENT_WIZARD_SESSIONS[user_id] = session
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")]
        ])
        await call.message.edit_text(
            f"👤 <b>Yangi to'lov qabul qilish</b> (2/4 bosqich):\n\n"
            f"📚 <b>Tanlangan guruh:</b> {group['name']}\n\n"
            f"Ushbu guruhda hali o'quvchilar ro'yxati shakllanmagan.\n"
            f"To'lov qabul qilinayotgan o'quvchining <b>Ism va familiyasi</b>ni yozib yuboring:\n"
            f"<i>(Masalan: Jasur Olimov)</i>\n\n"
            f"Bekor qilish uchun: <code>cancel</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await call.answer()
        return

    buttons = []
    for s in students[:10]:
        phone_str = f" ({s['phone']})" if s.get("phone") else ""
        buttons.append([
            InlineKeyboardButton(text=f"👤 {s['full_name']}{phone_str}", callback_data=f"pw_s_{s['id']}")
        ])

    buttons.append([
        InlineKeyboardButton(text="✍️ Yangi o'quvchi ismini yozish", callback_data="pw_s_manual")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(
        f"👤 <b>Yangi to'lov qabul qilish</b> (2/4 bosqich):\n\n"
        f"📚 <b>Tanlangan guruh:</b> {group['name']}\n\n"
        f"O'quvchini tanlang yoki yangi ism kiriting:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "pw_s_manual")
async def process_payment_student_manual(call: CallbackQuery):
    user_id = call.from_user.id
    session = PAYMENT_WIZARD_SESSIONS.get(user_id)
    if not session:
        await call.answer("Sessiya topilmadi. Qayta boshlang.")
        return

    session["step"] = "input_student_manual"
    await call.message.edit_text(
        f"✍️ <b>O'quvchi ma'lumotini kiriting:</b>\n\n"
        f"O'quvchining <b>Ism va familiyasi</b>ni yozib yuboring:\n"
        f"<i>(Masalan: Jasur Olimov)</i>\n\n"
        "Bekor qilish uchun: <code>cancel</code>",
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("pw_s_"))
async def process_payment_student_choice(call: CallbackQuery):
    user_id = call.from_user.id
    student_id = int(call.data.replace("pw_s_", ""))
    student = await get_user_by_id(student_id)
    session = PAYMENT_WIZARD_SESSIONS.get(user_id)
    if not session:
        await call.answer("Sessiya topilmadi.")
        return

    student_name = student["full_name"] if student else f"O'quvchi #{student_id}"
    session["student_id"] = student_id
    session["student_name"] = student_name
    session["step"] = "choose_amount"

    monthly_fee = float(session.get("monthly_fee", 400000))
    half_fee = monthly_fee / 2.0

    buttons = [
        [InlineKeyboardButton(text=f"💵 {monthly_fee:,.0f} so'm (To'liq oy)", callback_data=f"pw_amt_{int(monthly_fee)}")],
        [InlineKeyboardButton(text=f"💵 {half_fee:,.0f} so'm (Yarim oy)", callback_data=f"pw_amt_{int(half_fee)}")],
        [InlineKeyboardButton(text="✍️ Boshqa summa kiritish", callback_data="pw_amt_manual")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await call.message.edit_text(
        f"💵 <b>Yangi to'lov qabul qilish</b> (3/4 bosqich):\n\n"
        f"👤 <b>O'quvchi:</b> {student_name}\n"
        f"📚 <b>Guruh:</b> {session['group_name']}\n\n"
        f"To'lov summasini tanlang yoki o'zingiz yozing:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "pw_amt_manual")
async def process_payment_amount_manual(call: CallbackQuery):
    user_id = call.from_user.id
    session = PAYMENT_WIZARD_SESSIONS.get(user_id)
    if not session:
        await call.answer("Sessiya topilmadi.")
        return

    session["step"] = "input_amount_manual"
    await call.message.edit_text(
        f"✍️ <b>To'lov summasini kiriting:</b>\n\n"
        f"Kerakli summani faqat raqam bilan yozing (masalan: <code>350000</code>):\n\n"
        f"Bekor qilish uchun: <code>cancel</code>",
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("pw_amt_"))
async def process_payment_amount_choice(call: CallbackQuery):
    user_id = call.from_user.id
    amount = float(call.data.replace("pw_amt_", ""))
    session = PAYMENT_WIZARD_SESSIONS.get(user_id)
    if not session:
        await call.answer("Sessiya topilmadi.")
        return

    session["amount"] = amount
    session["step"] = "choose_type"

    buttons = [
        [InlineKeyboardButton(text="💵 Naqd pul", callback_data="pw_type_naqd")],
        [InlineKeyboardButton(text="💳 Plastik karta", callback_data="pw_type_karta")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pw_cancel")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await call.message.edit_text(
        f"💳 <b>Yangi to'lov qabul qilish</b> (4/4 bosqich):\n\n"
        f"👤 <b>O'quvchi:</b> {session['student_name']}\n"
        f"📚 <b>Guruh:</b> {session['group_name']}\n"
        f"💵 <b>Summa:</b> {amount:,.0f} so'm\n\n"
        f"To'lov qaysi usulda amalga oshirilmoqda?",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("pw_type_"))
async def process_payment_final(call: CallbackQuery):
    user_id = call.from_user.id
    payment_type = call.data.replace("pw_type_", "")
    session = PAYMENT_WIZARD_SESSIONS.pop(user_id, None)
    if not session:
        await call.answer("Sessiya eskirgan.")
        return

    student_id = session.get("student_id", 1)
    group_id = session.get("group_id", 1)
    amount = session.get("amount", 0.0)
    student_name = session.get("student_name", "O'quvchi")
    group_name = session.get("group_name", "Guruh")
    from datetime import datetime
    month_for = datetime.now().strftime("%Y-%m")

    await add_payment(
        student_id=student_id,
        group_id=group_id,
        amount=amount,
        payment_type=payment_type,
        month_for=month_for,
        note="Bot orqali qabul qilindi",
    )

    await notify_payment_receipt(
        student_id=student_id,
        group_id=group_id,
        amount=amount,
        payment_type=payment_type,
        month_for=month_for,
        note="Bot orqali qabul qilindi",
    )

    await call.message.edit_text(
        f"✅ <b>To'lov muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"👤 <b>O'quvchi:</b> {student_name}\n"
        f"📚 <b>Guruh:</b> {group_name}\n"
        f"💵 <b>Summa:</b> {amount:,.0f} so'm\n"
        f"💳 <b>To'lov usuli:</b> {payment_type.capitalize()}\n"
        f"📅 <b>Oy uchun:</b> {month_for}\n\n"
        f"🧾 Kvitansiya o'quvchi va ota-onaga avtomatik jo'natildi!",
        parse_mode="HTML"
    )
    await call.answer("To'lov saqlandi!")


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


# ==================== SUPER ADMIN: MANAGE ADMINS ====================

@router.message(F.text.in_({"👥 Adminlar", "adminlar", "/admins", "/adminlar"}))
async def list_admins_command(message: Message):
    if not is_super_admin(message.from_user.id):
        await message.answer("❌ Bu bo'lim faqat Super Admin uchun ochiq.")
        return

    admins = await get_users_by_role("admin")
    super_admins = await get_users_by_role("super_admin")

    # Combine ensuring unique
    seen_ids = set()
    all_admins = []
    for u in super_admins + admins:
        if u["id"] not in seen_ids:
            seen_ids.add(u["id"])
            all_admins.append(u)

    if not all_admins:
        # Fallback to current user
        all_admins = [await get_user(message.from_user.id)]

    text = (
        "👑 <b>Adminlar va Boshqaruvchilar Ro'yxati:</b>\n\n"
        f"Jami adminlar soni: <b>{len(all_admins)}</b> ta\n\n"
    )

    for idx, adm in enumerate(all_admins, 1):
        role_badge = "👑 Super Admin" if (adm.get("telegram_id") in SUPER_ADMIN_IDS or adm.get("role") == "super_admin") else "🛡 Admin"
        phone = adm.get("phone") or "Telefon yo'q"
        tid = adm.get("telegram_id") or "Kiritilmagan"
        text += (
            f"<b>{idx}. {adm['full_name']}</b> ({role_badge})\n"
            f"   📞 {phone} | 🆔 <code>{tid}</code>\n\n"
        )

    text += "Adminni o'chirish yoki yangi admin qo'shish uchun quyidagi tugmalardan foydalaning:"
    kb = get_admins_management_keyboard(all_admins, SUPER_ADMIN_IDS)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("del_adm_"))
async def prompt_delete_admin(call: CallbackQuery):
    if not is_super_admin(call.from_user.id):
        await call.answer("Faqat Super Admin uchun!", show_alert=True)
        return

    admin_id = int(call.data.replace("del_adm_", ""))
    target = await get_user_by_id(admin_id)
    if not target:
        await call.answer("Admin topilmadi.", show_alert=True)
        return

    if target.get("telegram_id") in SUPER_ADMIN_IDS:
        await call.answer("Super Adminni o'chirib bo'lmaydi!", show_alert=True)
        return

    text = (
        f"⚠️ <b>Haqiqatan ham {target['full_name']} adminlik huquqini bekor qilmoqchimisiz?</b>\n\n"
        f"Telefon: {target['phone'] or 'Yo\'q'}\n"
        f"Telegram ID: {target['telegram_id'] or 'Yo\'q'}\n\n"
        f"O'chirilgach, u bot va CRM admin boshqaruvidan mahrum bo'ladi."
    )
    await call.message.edit_text(text, reply_markup=get_confirm_delete_admin_keyboard(admin_id), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("confirm_del_adm_"))
async def confirm_delete_admin(call: CallbackQuery):
    if not is_super_admin(call.from_user.id):
        await call.answer("Faqat Super Admin uchun!", show_alert=True)
        return

    admin_id = int(call.data.replace("confirm_del_adm_", ""))
    target = await get_user_by_id(admin_id)
    if not target:
        await call.answer("Admin topilmadi.", show_alert=True)
        return

    if target.get("telegram_id") in SUPER_ADMIN_IDS:
        await call.answer("Super Adminni o'chirib bo'lmaydi!", show_alert=True)
        return

    await remove_admin(admin_id)
    await call.message.edit_text(
        f"✅ <b>{target['full_name']}</b> adminlikdan muvaffaqiyatli o'chirildi!\n\n"
        "Adminlar ro'yxatiga qaytish uchun: /admins",
        parse_mode="HTML"
    )
    await call.answer("Admin o'chirildi!")


@router.callback_query(F.data == "cancel_del_adm")
async def cancel_delete_admin(call: CallbackQuery):
    await call.message.edit_text("❌ Adminni o'chirish bekor qilindi.")
    await call.answer()


@router.callback_query(F.data == "adm_add_new")
async def callback_add_new_admin(call: CallbackQuery):
    if not is_super_admin(call.from_user.id):
        await call.answer("Faqat Super Admin uchun!", show_alert=True)
        return

    await call.answer()
    await start_creation_wizard(call.message, role="admin", label="Admin", target_user_id=call.from_user.id)


@router.message(F.text.startswith("/delete_admin") | F.text.startswith("/remove_admin"))
async def delete_admin_text_command(message: Message):
    if not is_super_admin(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat Super Admin uchun.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("❗ Format: <code>/delete_admin &lt;admin_id yoki telegram_id&gt;</code>", parse_mode="HTML")
        return

    raw_id = parts[1].strip()
    try:
        parsed_id = int(raw_id)
    except ValueError:
        await message.answer("❗ ID raqam bo'lishi kerak.")
        return

    if parsed_id in SUPER_ADMIN_IDS:
        await message.answer("❌ Super Adminni o'chirib bo'lmaydi!")
        return

    # Try by user_id first, then telegram_id
    target = await get_user_by_id(parsed_id)
    if target and target.get("role") == "admin":
        await remove_admin(target["id"])
        await message.answer(f"✅ Admin <b>{target['full_name']}</b> muvaffaqiyatli o'chirildi!", parse_mode="HTML")
        return

    target_tg = await get_user(parsed_id)
    if target_tg and target_tg.get("role") == "admin":
        await remove_admin(target_tg["id"])
        await message.answer(f"✅ Admin <b>{target_tg['full_name']}</b> muvaffaqiyatli o'chirildi!", parse_mode="HTML")
        return

    await message.answer(f"❗ ID={parsed_id} bo'yicha admin topilmadi.")

