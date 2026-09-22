from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from config import get_webapp_url
from database.db import (
    get_user,
    get_teacher_groups,
    get_group_by_id,
    get_group_students,
    get_group_attendance,
    record_attendance,
)
from bot.keyboards.inline import get_teacher_groups_keyboard, get_attendance_marking_keyboard
from services.notifications import notify_attendance_change

router = Router()


@router.message(F.text.in_({"👨‍🏫 Web panel", "/teacher"}))
async def teacher_web_panel(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Siz ro'yxatdan o'tmagansiz. Iltimos /start bosing.")
        return

    url = get_webapp_url(f"/teacher/{user['id']}")
    await message.answer(
        f"👨‍🏫 <b>O'qituvchi boshqaruv paneli</b>\n\n"
        f"Guruhlar va o'quvchilar ro'yxati, davomat monitoringi:\n"
        f"👉 <a href='{url}'>{url}</a>",
        parse_mode="HTML",
    )


@router.message(F.text == "👥 Guruhlarim")
async def teacher_groups(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Siz ro'yxatdan o'tmagansiz. Iltimos /start bosing.")
        return

    groups = await get_teacher_groups(user["id"])
    if not groups:
        await message.answer("ℹ️ Sizga hali birorta guruh biriktirilmagan. Administrator bilan bog'laning.")
        return

    text = "📚 <b>Sizning guruhlaringiz:</b>\n\n"
    for idx, g in enumerate(groups, 1):
        schedule = g["schedule"] if g["schedule"] else "Jadval belgilanmagan"
        room = f", Xona: {g['room']}" if g["room"] else ""
        text += (
            f"<b>{idx}. {g['name']}</b> ({g['subject']})\n"
            f"   👥 O'quvchilar: {g['student_count']} ta\n"
            f"   ⏰ Vaqti: {schedule}{room}\n"
            f"   💰 Oylik to'lov: {g['monthly_fee']:,.0f} so'm\n\n"
        )

    text += "Guruh o'quvchilari yoki davomatni ko'rish uchun quyidagi tugmalardan birini tanlang:"
    await message.answer(text, reply_markup=get_teacher_groups_keyboard(groups), parse_mode="HTML")


@router.message(F.text == "📅 Dars jadvali")
async def teacher_schedule(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Iltimos, avval /start bosing.")
        return

    groups = await get_teacher_groups(user["id"])
    if not groups:
        await message.answer("Sizga hali guruhlar biriktirilmagan.")
        return

    text = "📅 <b>Sizning dars jadvalingiz:</b>\n\n"
    for idx, g in enumerate(groups, 1):
        schedule = g["schedule"] if g["schedule"] else "Belgilanmagan"
        room = f" ({g['room']}-xona)" if g["room"] else ""
        text += f"🔹 <b>{g['name']}</b> ({g['subject']})\n   ⏰ {schedule}{room}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "✅ Davomat")
async def teacher_attendance_start(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Iltimos, avval /start bosing.")
        return

    groups = await get_teacher_groups(user["id"])
    if not groups:
        await message.answer("Davomat qilish uchun avval sizga guruh biriktirilgan bo'lishi kerak.")
        return

    await message.answer(
        "📝 <b>Qaysi guruhga davomat qilmoqchisiz?</b>\nKerakli guruhni tanlang:",
        reply_markup=get_teacher_groups_keyboard(groups),
        parse_mode="HTML",
    )


@router.message(F.text == "📚 Materiallar")
async def teacher_materials(message: Message):
    await message.answer(
        "📚 <b>O'qituvchilar uchun materiallar bo'limi</b>\n\n"
        "- Dars ishlanmalari va rejalari\n"
        "- Test sinovlari va nazorat savollari\n"
        "- O'quv metodik qo'llanmalar\n\n"
        "Fayllarni yuklash yoki yangilash uchun o'quv markaz metodistiga murojaat qiling.",
        parse_mode="HTML",
    )


@router.message(F.text == "💬 Murojaat")
async def teacher_support(message: Message):
    await message.answer(
        "💬 <b>Ma'muriyat bilan bog'lanish:</b>\n\n"
        "Savol yoki takliflaringiz bo'lsa, quyidagi kontaktlarga murojaat qilishingiz mumkin:\n"
        "📞 Telefon: +998 90 123 45 67\n"
        "Telegram: @zahro_admin\n"
        "Ish vaqti: 09:00 - 19:00",
        parse_mode="HTML",
    )


# ==================== CALLBACK QUERY HANDLERS ====================

@router.callback_query(F.data.startswith("t_grp_"))
async def show_group_roster(call: CallbackQuery):
    group_id = int(call.data.replace("t_grp_", ""))
    group = await get_group_by_id(group_id)
    students = await get_group_students(group_id)

    if not group:
        await call.answer("Guruh topilmadi.")
        return

    text = f"📚 <b>Guruh:</b> {group['name']} ({group['subject']})\n"
    text += f"⏰ <b>Jadval:</b> {group['schedule'] or 'Belgilanmagan'}\n"
    text += f"👥 <b>O'quvchilar ro'yxati ({len(students)} ta):</b>\n\n"

    if not students:
        text += "<i>Ushbu guruhga hali o'quvchilar qo'shilmagan.</i>"
    else:
        for idx, s in enumerate(students, 1):
            phone = s["phone"] if s["phone"] else "Tel yo'q"
            text += f"{idx}. <b>{s['full_name']}</b> ({phone})\n"

    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("t_att_"))
async def start_attendance_marking(call: CallbackQuery):
    group_id = int(call.data.replace("t_att_", ""))
    group = await get_group_by_id(group_id)
    students = await get_group_students(group_id)

    if not students:
        await call.answer("Bu guruhda o'quvchilar yo'q.", show_alert=True)
        return

    today = datetime.now().strftime("%Y-%m-%d")
    existing_attendance = await get_group_attendance(group_id, today)
    status_map = {row["student_id"]: row["status"] for row in existing_attendance}

    # If not recorded yet, default to "keldi"
    for s in students:
        if s["id"] not in status_map:
            status_map[s["id"]] = "keldi"
            await record_attendance(group_id, s["id"], today, "keldi")

    text = (
        f"📝 <b>Davomat kiritish: {group['name']}</b>\n"
        f"📅 Sana: <b>{today}</b>\n\n"
        "O'quvchi holatini o'zgartirish uchun ismini bosing:\n"
        "✅ Keldi | ❌ Kelmadi | ⚠️ Sababli"
    )

    kb = get_attendance_marking_keyboard(students, group_id, status_map)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("att_toggle_"))
async def toggle_student_attendance(call: CallbackQuery):
    # format: att_toggle_{group_id}_{student_id}_{current_status}
    parts = call.data.split("_")
    group_id = int(parts[2])
    student_id = int(parts[3])
    current_status = parts[4]

    next_status_map = {
        "keldi": "kelmadi",
        "kelmadi": "sababli",
        "sababli": "keldi",
    }
    new_status = next_status_map.get(current_status, "keldi")

    today = datetime.now().strftime("%Y-%m-%d")
    await record_attendance(group_id, student_id, today, new_status)

    students = await get_group_students(group_id)
    existing_attendance = await get_group_attendance(group_id, today)
    status_map = {row["student_id"]: row["status"] for row in existing_attendance}

    kb = get_attendance_marking_keyboard(students, group_id, status_map)
    try:
        await call.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await call.answer(f"Holat: {new_status.capitalize()}")


@router.callback_query(F.data.startswith("att_done_"))
async def finish_attendance(call: CallbackQuery):
    group_id = int(call.data.replace("att_done_", ""))
    group = await get_group_by_id(group_id)
    today = datetime.now().strftime("%Y-%m-%d")

    records = await get_group_attendance(group_id, today)
    keldi_count = sum(1 for r in records if r["status"] == "keldi")
    kelmadi_count = sum(1 for r in records if r["status"] == "kelmadi")
    sababli_count = sum(1 for r in records if r["status"] == "sababli")

    summary = (
        f"✅ <b>{group['name']} guruhi uchun davomat saqlandi!</b>\n\n"
        f"📅 Sana: {today}\n"
        f"🟢 Keldi: {keldi_count} ta\n"
        f"🔴 Kelmadi: {kelmadi_count} ta\n"
        f"🟡 Sababli: {sababli_count} ta\n\n"
        f"<i>Barcha ma'lumotlar tizimga kiritildi va ota-onalarga xabarnomalar yuborildi.</i>"
    )

    # Dispatch alerts to parents for each student's attendance
    for r in records:
        try:
            await notify_attendance_change(
                student_id=r["student_id"],
                group_id=group_id,
                date=today,
                status=r["status"],
            )
        except Exception as e:
            print(f"Error notifying attendance for student {r['student_id']}: {e}")

    await call.message.edit_text(summary, parse_mode="HTML")
    await call.answer("Davomat muvaffaqiyatli saqlandi!")
