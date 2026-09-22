import httpx
from config import BOT_TOKEN
from database.db import (
    get_user_by_id,
    get_group_by_id,
    get_student_parents,
    get_users_by_role,
    get_feedback_by_id,
)


async def send_telegram_notification(chat_id: int | None, text: str) -> bool:
    """Sends a Telegram HTML message asynchronously using httpx."""
    if not chat_id or not BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram notification to {chat_id}: {e}")
        return False


async def notify_attendance_change(student_id: int, group_id: int, date: str, status: str):
    """
    Sends real-time attendance alert to linked parent(s) and student.
    Particularly alerts parents when child is marked 'kelmadi' (absent).
    """
    student = await get_user_by_id(student_id)
    group = await get_group_by_id(group_id)
    if not student or not group:
        return

    student_name = student["full_name"]
    group_name = group["name"]
    subject = group["subject"]

    parents = await get_student_parents(student_id)

    if status == "kelmadi":
        parent_msg = (
            f"🚨 <b>DIQQAT: Farzandingiz darsga kelmadi!</b>\n\n"
            f"Hurmatli ota-ona!\n"
            f"Farzandingiz <b>{student_name}</b> bugun (<b>{date}</b>) "
            f"<b>{group_name}</b> ({subject}) darsiga qatnashmadi.\n\n"
            f"Iltimos, sababini o'qituvchiga yoki markaz ma'muriyatiga ma'lum qiling.\n"
            f"📞 Aloqa: +998 90 123 45 67\n"
            f"<i>Zahro o'quv markazi</i>"
        )
    elif status == "keldi":
        parent_msg = (
            f"🟢 <b>Davomat xabarnomasi</b>\n\n"
            f"Hurmatli ota-ona!\n"
            f"Farzandingiz <b>{student_name}</b> bugun (<b>{date}</b>) "
            f"<b>{group_name}</b> ({subject}) darsiga o'z vaqtida yetib keldi va darsda qatnashmoqda.\n\n"
            f"<i>Zahro o'quv markazi</i>"
        )
    else:  # sababli
        parent_msg = (
            f"🟡 <b>Davomat xabarnomasi</b>\n\n"
            f"Farzandingiz <b>{student_name}</b> bugun (<b>{date}</b>) "
            f"<b>{group_name}</b> ({subject}) darsida <b>Sababli qatnashmadi</b> deb qayd etildi.\n\n"
            f"<i>Zahro o'quv markazi</i>"
        )

    # Notify all linked parents
    for parent in parents:
        if parent["telegram_id"]:
            await send_telegram_notification(parent["telegram_id"], parent_msg)

    # Also notify student if they have telegram
    if student["telegram_id"]:
        student_msg = (
            f"📋 <b>Davomatingiz qayd etildi:</b>\n\n"
            f"📚 Guruh: <b>{group_name}</b>\n"
            f"📅 Sana: <b>{date}</b>\n"
            f"Holat: <b>{status.capitalize()}</b>"
        )
        await send_telegram_notification(student["telegram_id"], student_msg)


async def notify_payment_receipt(
    student_id: int,
    group_id: int,
    amount: float,
    payment_type: str,
    month_for: str,
    note: str = "",
):
    """
    Sends official payment receipt to both the student and all linked parents.
    """
    student = await get_user_by_id(student_id)
    group = await get_group_by_id(group_id)
    if not student:
        return

    student_name = student["full_name"]
    group_name = group["name"] if group else "Guruh"

    receipt_msg = (
        f"✅ <b>To'lov qabul qilindi! (Rasmiy kvitansiya)</b>\n\n"
        f"👤 <b>O'quvchi:</b> {student_name}\n"
        f"📚 <b>Guruh:</b> {group_name}\n"
        f"💵 <b>To'langan summa:</b> {amount:,.0f} so'm\n"
        f"💳 <b>To'lov turi:</b> {payment_type.capitalize()}\n"
        f"📅 <b>Qaysi oy uchun:</b> {month_for}\n"
        f"📝 <b>Izoh:</b> {note if note else 'Yoʻq'}\n\n"
        f"<i>Farzandingiz ta'limiga befarq bo'lmaganingiz uchun tashakkur!\n"
        f"Zahro o'quv markazi.</i>"
    )

    # Send to student
    if student["telegram_id"]:
        await send_telegram_notification(student["telegram_id"], receipt_msg)

    # Send to all linked parents
    parents = await get_student_parents(student_id)
    for parent in parents:
        if parent["telegram_id"]:
            await send_telegram_notification(parent["telegram_id"], receipt_msg)


async def notify_new_feedback(feedback_id: int):
    """
    Notifies all admins and super_admins when a new feedback/ticket is submitted.
    """
    fb = await get_feedback_by_id(feedback_id)
    if not fb:
        return

    author_name = fb["user_name"]
    author_phone = fb["user_phone"] or "Ko'rsatilmagan"
    role = fb["user_role"]
    student_info = f"\n👶 <b>O'quvchi:</b> {fb['student_name']}" if fb["student_name"] else ""
    feedback_type = fb["feedback_type"].upper()
    message_text = fb["message"]

    alert_msg = (
        f"💬 <b>Yangi murojaat qabul qilindi! (ID: #{fb['id']})</b>\n\n"
        f"👤 <b>Kimdan:</b> {author_name} ({role})\n"
        f"📞 <b>Telefon:</b> {author_phone}{student_info}\n"
        f"📌 <b>Turi:</b> {feedback_type}\n"
        f"📝 <b>Xabar:</b>\n{message_text}\n\n"
        f"<i>Admin panel orqali javob berishingiz mumkin.</i>"
    )

    # Collect admin telegram IDs
    admins = await get_users_by_role("admin")
    super_admins = await get_users_by_role("super_admin")
    all_admin_ids = {u["telegram_id"] for u in admins + super_admins if u["telegram_id"]}

    for tid in all_admin_ids:
        await send_telegram_notification(tid, alert_msg)


async def notify_feedback_reply(feedback_id: int):
    """
    Sends the administrator's reply back to the user who created the feedback.
    """
    fb = await get_feedback_by_id(feedback_id)
    if not fb or not fb["user_telegram_id"]:
        return

    user_name = fb["user_name"]
    original_msg = fb["message"]
    admin_reply = fb["admin_reply"] or ""
    admin_name = fb["admin_name"] or "Ma'muriyat"

    reply_msg = (
        f"📩 <b>Murojaatingizga javob keldi!</b>\n\n"
        f"Hurmatli <b>{user_name}</b>, sizning murojaatingiz ko'rib chiqildi:\n\n"
        f"📝 <b>Sizning murojaatingiz:</b>\n<i>«{original_msg}»</i>\n\n"
        f"💬 <b>Javob ({admin_name}):</b>\n<b>{admin_reply}</b>\n\n"
        f"<i>Savollaringiz bo'lsa yana murojaat qilishingiz mumkin.\n"
        f"Zahro o'quv markazi.</i>"
    )

    await send_telegram_notification(fb["user_telegram_id"], reply_msg)
