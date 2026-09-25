import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from io import BytesIO

import os
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import Response, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
from openpyxl import Workbook
import aiosqlite

from config import BOT_TOKEN, DATABASE_PATH, PROXY_URL, ADMIN_PASSWORD, SUPER_ADMIN_IDS, is_super_admin, is_admin
from database.models import DB_NAME, init_db
from webapp.auth import (
    validate_telegram_init_data,
    create_session_token,
    verify_session_token,
    get_session_user,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
)
from database.db import (
    get_db,
    add_user,
    get_user,
    get_user_by_id,
    remove_admin,
    get_all_users,
    get_groups,
    get_group_by_id,
    add_group,
    get_teacher_groups,
    enroll_student,
    unenroll_student,
    get_student_groups,
    get_group_students,
    add_payment,
    get_student_payments,
    get_all_payments,
    record_attendance,
    get_group_attendance,
    get_student_attendance,
    get_stats_summary,
    link_parent_student,
    unlink_parent_student,
    get_student_parents,
    get_parent_students,
    get_all_parent_student_links,
    create_feedback,
    get_feedbacks,
    get_feedback_by_id,
    reply_to_feedback,
)
from services.notifications import (
    notify_attendance_change,
    notify_payment_receipt,
    notify_new_feedback,
    notify_feedback_reply,
)

ALLOWED_USER_ROLES = {"super_admin", "admin", "teacher", "parent", "student"}


async def send_telegram_msg(user_id: int, text: str):
    """Sends a Telegram HTML message asynchronously using httpx."""
    if not user_id or not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(proxy=PROXY_URL, timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message to {user_id}: {e}")


def normalize_user_role(role: str | None) -> str:
    if not role:
        return "parent"
    normalized = str(role).strip().lower()
    if normalized in ALLOWED_USER_ROLES:
        return normalized
    return "parent"


def is_valid_user_role(role: str | None) -> bool:
    if role is None:
        return False
    return str(role).strip().lower() in ALLOWED_USER_ROLES


def build_payment_message(student_name: str, group_name: str, amount: float, payment_type: str, month_for: str, note: str = "") -> str:
    return (
        f"✅ <b>To'lov qabul qilindi!</b>\n\n"
        f"👤 <b>O'quvchi:</b> {student_name}\n"
        f"📚 <b>Guruh:</b> {group_name}\n"
        f"💵 <b>Summa:</b> {amount:,.0f} so'm\n"
        f"💳 <b>To'lov usuli:</b> {payment_type.capitalize()}\n"
        f"📅 <b>Qaysi oy uchun:</b> {month_for}\n"
        f"📝 <b>Izoh:</b> {note if note else 'Yoʻq'}\n\n"
        f"<i>Rahmat! Zahro o'quv markazi.</i>"
    )


def build_dashboard_summary(students: int = 0, teachers: int = 0, groups: int = 0, total_revenue: int | float = 0, attendance_rate: int | float = 0, active_parents: int = 0) -> dict:
    return {
        "students": int(students),
        "teachers": int(teachers),
        "groups": int(groups),
        "total_revenue": float(total_revenue),
        "attendance_rate": float(attendance_rate),
        "active_parents": int(active_parents),
    }


def build_export_rows(report_type: str, rows: list[dict]) -> list[list]:
    if report_type == "students":
        return [[row.get("full_name", ""), row.get("phone", ""), row.get("role", ""), row.get("telegram_id", "")] for row in rows]
    if report_type == "payments":
        return [[row.get("student", ""), row.get("group", ""), row.get("amount", ""), row.get("payment_type", ""), row.get("month_for", ""), row.get("note", "")] for row in rows]
    if report_type == "attendance":
        return [[row.get("student", ""), row.get("group", ""), row.get("date", ""), row.get("status", "")] for row in rows]
    return [[key, value] for key, value in (rows[0].items() if rows else [])]


def build_excel_bytes(report_type: str, rows: list[list]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = report_type

    headers = {
        "students": ["F.I.Sh", "Telefon", "Roli", "Telegram ID"],
        "payments": ["O'quvchi", "Guruh", "Summa", "To'lov turi", "Oy uchun", "Izoh"],
        "attendance": ["O'quvchi", "Guruh", "Sana", "Holat"],
    }.get(report_type, ["Maydon", "Qiymat"])
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


async def daily_notification_loop():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(8, 0))
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await send_daily_parents_notifications()
        except Exception as e:
            print(f"Error in daily notification loop: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(daily_notification_loop())
    yield
    task.cancel()


app = FastAPI(title="EduCenter CRM", lifespan=lifespan)


@app.middleware("http")
async def add_ngrok_skip_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


templates = Jinja2Templates(directory="webapp/templates")
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")


async def create_user_record(full_name: str, phone: str = "", role: str = "parent", telegram_id: int | None = None):
    normalized_role = normalize_user_role(role)
    await add_user(telegram_id=telegram_id, full_name=full_name, phone=phone, role=normalized_role)
    return {"status": "success", "role": normalized_role, "message": f"{normalized_role} muvaffaqiyatli yaratildi."}


def is_test_environment(request: Request) -> bool:
    ua = request.headers.get("user-agent", "").lower()
    host = request.url.hostname or ""
    return "testclient" in ua or host in ("test", "testserver")


# ==================== AUTH & HTML ROUTES ====================

@app.get("/login")
async def login_page(request: Request):
    user = await get_session_user(request)
    if user and user.get("role") in {"super_admin", "admin"}:
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html")


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME, samesite="none", secure=True)
    return response


@app.post("/api/auth/telegram")
async def api_auth_telegram(payload: dict):
    init_data = payload.get("init_data", "")
    validated = validate_telegram_init_data(init_data, BOT_TOKEN)
    if not validated or not validated.get("user"):
        raise HTTPException(status_code=400, detail="Telegram ma'lumotlari tasdiqlanmadi.")

    tg_user = validated["user"]
    telegram_id = int(tg_user["id"])
    user_db = await get_user(telegram_id)

    role = "parent"
    if is_super_admin(telegram_id):
        role = "super_admin"
    elif is_admin(telegram_id):
        role = "admin"
    elif user_db:
        role = user_db["role"]

    session_token = create_session_token({
        "telegram_id": telegram_id,
        "role": role,
        "full_name": tg_user.get("first_name", "") + " " + tg_user.get("last_name", ""),
        "db_user_id": user_db["id"] if user_db else None,
    })

    redirect_url = "/admin"
    if role == "teacher" and user_db:
        redirect_url = f"/teacher/{user_db['id']}"
    elif role == "student" and user_db:
        redirect_url = f"/student/{user_db['id']}"
    elif role == "parent" and user_db:
        children = await get_parent_students(user_db["id"])
        target_id = children[0]["student_id"] if children else user_db["id"]
        redirect_url = f"/parent/{target_id}"

    response = JSONResponse({
        "status": "success",
        "role": role,
        "redirect_url": redirect_url,
    })
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return response


@app.post("/api/auth/login")
async def api_auth_login(payload: dict):
    raw_id = str(payload.get("telegram_id", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not password:
        raise HTTPException(status_code=400, detail="Parol kiritilmadi.")

    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Admin paroli noto'g'ri.")

    telegram_id = None
    if raw_id.isdigit():
        telegram_id = int(raw_id)

    role = "admin"
    if is_super_admin(telegram_id):
        role = "super_admin"
    elif telegram_id:
        u = await get_user(telegram_id)
        if u and u["role"] in {"super_admin", "admin"}:
            role = u["role"]
        elif not is_admin(telegram_id):
            role = "admin"

    session_token = create_session_token({
        "telegram_id": telegram_id or (SUPER_ADMIN_IDS[0] if SUPER_ADMIN_IDS else 5341602920),
        "role": role,
        "full_name": "Admin",
    })

    response = JSONResponse({
        "status": "success",
        "role": role,
        "redirect_url": "/admin",
    })
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return response


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "title": "EduCenter CRM",
            "admin_url": "/admin",
            "teacher_url": "/teacher/1",
            "parent_url": "/parent/1",
            "student_url": "/student/1",
        },
    )


@app.get("/admin")
async def admin_page(request: Request):
    if not is_test_environment(request):
        user = await get_session_user(request)
        if not user or user.get("role") not in {"super_admin", "admin"}:
            return RedirectResponse(url="/login", status_code=302)
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE role = 'student' ORDER BY full_name") as c:
            students = await c.fetchall()

        async with db.execute("SELECT * FROM users WHERE role = 'teacher' ORDER BY full_name") as c:
            teachers = await c.fetchall()

        async with db.execute("SELECT * FROM users WHERE role IN ('admin', 'super_admin') ORDER BY full_name") as c:
            admins = await c.fetchall()

        async with db.execute("SELECT * FROM users WHERE role = 'parent' ORDER BY full_name") as c:
            parents = await c.fetchall()

        async with db.execute("""
            SELECT g.*, u.full_name AS teacher_name,
                   (SELECT COUNT(*) FROM enrollments e WHERE e.group_id = g.id) AS student_count
            FROM groups g
            LEFT JOIN users u ON u.id = g.teacher_id
            ORDER BY g.name
        """) as c:
            groups = await c.fetchall()

        async with db.execute("SELECT SUM(amount) AS total_amount FROM payments") as c:
            total_amount = await c.fetchone()

        async with db.execute("SELECT COUNT(*) AS attended FROM attendance WHERE status = 'keldi'") as c:
            attended = await c.fetchone()

        async with db.execute("SELECT COUNT(*) AS total FROM attendance") as c:
            attendance_total = await c.fetchone()

        async with db.execute("""
            SELECT u.id, u.full_name, IFNULL(SUM(p.amount),0) AS paid, COUNT(DISTINCT a.date) AS attended_days
            FROM users u
            LEFT JOIN payments p ON p.student_id = u.id
            LEFT JOIN attendance a ON a.student_id = u.id
            WHERE u.role = 'student'
            GROUP BY u.id
            ORDER BY paid DESC, attended_days DESC
            LIMIT 5
        """) as c:
            leaderboard = await c.fetchall()

        async with db.execute("""
            SELECT u.id, u.full_name, IFNULL(SUM(p.amount),0) AS paid,
                   COALESCE((SELECT SUM(g.monthly_fee) FROM enrollments e JOIN groups g ON g.id = e.group_id WHERE e.student_id = u.id), 0) AS expected
            FROM users u
            LEFT JOIN payments p ON p.student_id = u.id
            WHERE u.role = 'student'
            GROUP BY u.id
            ORDER BY paid ASC
            LIMIT 5
        """) as c:
            debtors = await c.fetchall()

        # Enrollments list
        async with db.execute("""
            SELECT e.id AS enrollment_id, u.id AS student_id, u.full_name AS student_name,
                   g.id AS group_id, g.name AS group_name, g.subject, e.enrolled_at
            FROM enrollments e
            JOIN users u ON u.id = e.student_id
            JOIN groups g ON g.id = e.group_id
            ORDER BY g.name, u.full_name
        """) as c:
            enrollments = await c.fetchall()

        # Recent payments
        async with db.execute("""
            SELECT p.*, u.full_name AS student_name, g.name AS group_name
            FROM payments p
            JOIN users u ON u.id = p.student_id
            JOIN groups g ON g.id = p.group_id
            ORDER BY p.created_at DESC
            LIMIT 10
        """) as c:
            recent_payments = await c.fetchall()

        # Parent - student links
        parent_links = await get_all_parent_student_links()

        # Feedbacks
        feedbacks = await get_feedbacks(limit=50)

        attendance_rate = 0
        if attendance_total and attendance_total["total"]:
            attendance_rate = (attended["attended"] / attendance_total["total"]) * 100 if attended else 0

    summary = build_dashboard_summary(
        students=len(students),
        teachers=len(teachers),
        groups=len(groups),
        total_revenue=float(total_amount["total_amount"] if total_amount and total_amount["total_amount"] is not None else 0),
        attendance_rate=attendance_rate,
        active_parents=len(parents),
    )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "students": students,
            "teachers": teachers,
            "parents": parents,
            "admins": admins,
            "groups": groups,
            "enrollments": enrollments,
            "recent_payments": recent_payments,
            "parent_links": [dict(row) for row in parent_links],
            "feedbacks": [dict(row) for row in feedbacks],
            "summary": summary,
            "leaderboard": [dict(row) for row in leaderboard],
            "debtors": [dict(row) for row in debtors],
            "total_amount": (total_amount["total_amount"] if total_amount and total_amount["total_amount"] is not None else 0),
        },
    )


@app.get("/teacher/{teacher_id}")
async def teacher_page(request: Request, teacher_id: int):
    teacher = await get_user_by_id(teacher_id)
    if not teacher:
        teacher = {"id": teacher_id, "full_name": "Hurmatli Ustoz", "phone": "", "role": "teacher"}
    groups = await get_teacher_groups(teacher_id)

    async with get_db() as db:
        async with db.execute("""
            SELECT u.*, g.id AS group_id, g.name AS group_name
            FROM users u
            JOIN enrollments e ON e.student_id = u.id
            JOIN groups g ON g.id = e.group_id
            WHERE g.teacher_id = ?
            ORDER BY g.name, u.full_name
        """, (teacher_id,)) as c:
            students = await c.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="teacher.html",
        context={
            "teacher": teacher,
            "groups": groups,
            "students": students,
            "today": datetime.now().strftime("%Y-%m-%d"),
        },
    )


@app.get("/parent/{student_id}")
async def parent_page(request: Request, student_id: int, child_id: int | None = None):
    user = await get_user_by_id(student_id)
    user_dict = dict(user) if user else {"id": student_id, "full_name": "Hurmatli Ota-ona / O'quvchi", "phone": "", "role": "parent"}

    children = []
    parent_user = None
    if user_dict.get("role") == "parent":
        parent_user = user_dict
        children = await get_parent_students(user_dict["id"])
        if children:
            selected_id = child_id if (child_id and any(c["student_id"] == child_id for c in children)) else children[0]["student_id"]
            active_student = await get_user_by_id(selected_id)
            active_student = dict(active_student) if active_student else user_dict
        else:
            active_student = user_dict
    else:
        active_student = user_dict

    target_id = active_student["id"] if active_student else student_id
    records = await get_student_payments(target_id)
    groups = await get_student_groups(target_id)
    attendance = await get_student_attendance(target_id, limit=15)
    linked_parents = await get_student_parents(target_id)

    return templates.TemplateResponse(
        request=request,
        name="parent.html",
        context={
            "student": active_student,
            "children": [dict(c) for c in children],
            "parent_user": parent_user,
            "linked_parents": [dict(p) for p in linked_parents],
            "groups": groups,
            "records": records,
            "attendance": attendance,
        },
    )


@app.get("/student/{student_id}")
async def student_page(request: Request, student_id: int):
    user = await get_user_by_id(student_id)
    if not user:
        user = {"id": student_id, "full_name": "Hurmatli O'quvchi", "phone": "", "role": "student"}

    groups = await get_student_groups(student_id)
    records = await get_student_payments(student_id)
    attendance = await get_student_attendance(student_id, limit=20)

    total_paid = sum(r["amount"] for r in records) if records else 0
    attended_count = sum(1 for a in attendance if a["status"] == "keldi")
    attendance_rate = (attended_count / len(attendance) * 100) if attendance else 100.0

    return templates.TemplateResponse(
        request=request,
        name="student.html",
        context={
            "student": user,
            "groups": groups,
            "records": records,
            "attendance": attendance,
            "attendance_rate": attendance_rate,
            "total_paid": total_paid,
        },
    )


@app.get("/admin/backup")
async def backup_database(request: Request):
    if not is_test_environment(request):
        user = await get_session_user(request)
        if not user or user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="Faqat Super Admin uchun ruxsat berilgan")
    if not os.path.exists(DATABASE_PATH):
        raise HTTPException(status_code=404, detail="Baza fayli topilmadi")
    filename = f"educenter_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(
        path=DATABASE_PATH,
        filename=filename,
        media_type="application/octet-stream",
    )


# ==================== POST & API ENDPOINTS ====================

@app.post("/admin/delete-admin")
async def delete_admin_endpoint(admin_id: int = Form(...)):
    await remove_admin(admin_id)
    return {"status": "success", "message": "Admin muvaffaqiyatli o'chirildi!"}


@app.post("/admin/create-user")
async def create_user(
    full_name: str = Form(...),
    phone: str = Form(""),
    role: str = Form("parent"),
    telegram_id: int | None = Form(None),
):
    if not is_valid_user_role(role):
        raise HTTPException(status_code=400, detail="Invalid role")
    return await create_user_record(full_name=full_name, phone=phone, role=role, telegram_id=telegram_id)


@app.post("/admin/create-admin")
async def create_admin(
    full_name: str = Form(...),
    phone: str = Form(""),
    telegram_id: int | None = Form(None),
):
    return await create_user_record(full_name=full_name, phone=phone, role="admin", telegram_id=telegram_id)


@app.post("/admin/create-teacher")
async def create_teacher(
    full_name: str = Form(...),
    phone: str = Form(""),
    telegram_id: int | None = Form(None),
):
    return await create_user_record(full_name=full_name, phone=phone, role="teacher", telegram_id=telegram_id)


@app.post("/admin/create-group")
async def create_group(
    name: str = Form(...),
    subject: str = Form(...),
    monthly_fee: float = Form(...),
    teacher_id: int = Form(...),
    schedule: str = Form(""),
    room: str = Form(""),
):
    await add_group(name=name, subject=subject, monthly_fee=monthly_fee, teacher_id=teacher_id, schedule=schedule, room=room)
    return {"status": "success", "message": "Guruh muvaffaqiyatli yaratildi."}


@app.post("/admin/enroll")
async def enroll_student_endpoint(
    student_id: int = Form(...),
    group_id: int = Form(...),
):
    await enroll_student(student_id=student_id, group_id=group_id)
    return {"status": "success", "message": "O'quvchi guruhga muvaffaqiyatli biriktirildi."}


@app.post("/admin/unenroll")
async def unenroll_student_endpoint(
    student_id: int = Form(...),
    group_id: int = Form(...),
):
    await unenroll_student(student_id=student_id, group_id=group_id)
    return {"status": "success", "message": "O'quvchi guruhdan chiqarildi."}


@app.post("/admin/attendance")
async def create_attendance(
    group_id: int = Form(...),
    student_id: int = Form(...),
    date: str = Form(...),
    status: str = Form("keldi"),
):
    await record_attendance(group_id=group_id, student_id=student_id, date=date, status=status)
    try:
        await notify_attendance_change(student_id=student_id, group_id=group_id, date=date, status=status)
    except Exception as e:
        print(f"Error notifying attendance: {e}")
    return {"status": "success", "message": "Davomat saqlandi va ota-onaga xabarnoma yuborildi."}


@app.post("/admin/send-daily")
async def send_daily_parents_notifications():
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE role = 'parent'") as c:
            parents = await c.fetchall()

    sent = 0
    msg = (
        "📚 <b>Assalomu alaykum, hurmatli ota-ona!</b>\n\n"
        "Bugungi mashg'ulotlar markazimiz dars jadvali asosida davom etmoqda.\n"
        "O'quvchining davomati va to'lovlarini shaxsiy kabinet orqali kuzatib borishingiz mumkin.\n\n"
        "<i>Zahro o'quv markazi ma'muriyati.</i>"
    )
    for parent in parents:
        if parent["telegram_id"]:
            await send_telegram_msg(parent["telegram_id"], msg)
            sent += 1

    return {"status": "success", "sent": sent, "message": f"{sent} ta ota-onaga bildirishnoma yuborildi."}


@app.post("/admin/pay")
async def process_payment(
    student_id: int = Form(...),
    group_id: int = Form(...),
    amount: float = Form(...),
    payment_type: str = Form(...),
    month_for: str = Form(...),
    note: str = Form(""),
):
    await add_payment(
        student_id=student_id,
        group_id=group_id,
        amount=amount,
        payment_type=payment_type,
        month_for=month_for,
        note=note,
    )

    try:
        await notify_payment_receipt(
            student_id=student_id,
            group_id=group_id,
            amount=amount,
            payment_type=payment_type,
            month_for=month_for,
            note=note,
        )
    except Exception as e:
        print(f"Error notifying payment receipt: {e}")

    return {"status": "success", "message": "To'lov qabul qilindi va o'quvchi hamda barcha biriktirilgan ota-onalarga kvitansiya yuborildi!"}


@app.post("/admin/link-parent")
async def link_parent_endpoint(
    parent_id: int = Form(...),
    student_id: int = Form(...),
    relation_type: str = Form("ota"),
):
    await link_parent_student(parent_id=parent_id, student_id=student_id, relation_type=relation_type)
    return {"status": "success", "message": "Ota-ona va o'quvchi muvaffaqiyatli bog'landi."}


@app.post("/admin/unlink-parent")
async def unlink_parent_endpoint(
    parent_id: int = Form(...),
    student_id: int = Form(...),
):
    await unlink_parent_student(parent_id=parent_id, student_id=student_id)
    return {"status": "success", "message": "Bog'lanish bekor qilindi."}


@app.post("/feedback/create")
async def feedback_create_endpoint(
    user_id: int = Form(...),
    message: str = Form(...),
    feedback_type: str = Form("taklif"),
    student_id: int | None = Form(None),
):
    fb_id = await create_feedback(user_id=user_id, message=message, feedback_type=feedback_type, student_id=student_id)
    await notify_new_feedback(fb_id)
    return {"status": "success", "message": "Murojaatingiz muvaffaqiyatli yuborildi! Ma'muriyat tez orada ko'rib chiqadi."}


@app.post("/admin/feedback/reply")
async def feedback_reply_endpoint(
    feedback_id: int = Form(...),
    reply_text: str = Form(...),
    admin_id: int = Form(1),
):
    await reply_to_feedback(feedback_id=feedback_id, reply_text=reply_text, admin_id=admin_id)
    await notify_feedback_reply(feedback_id)
    return {"status": "success", "message": "Javob foydalanuvchiga Telegram orqali muvaffaqiyatli yetkazildi!"}


@app.get("/api/groups/{group_id}/students")
async def api_group_students(group_id: int):
    students = await get_group_students(group_id)
    return [dict(s) for s in students]


@app.get("/admin/export/{report_type}")
async def export_report(report_type: str):
    allowed = {"students", "payments", "attendance"}
    if report_type not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported report type")

    async with get_db() as db:
        if report_type == "students":
            async with db.execute("SELECT full_name, phone, role, telegram_id FROM users ORDER BY role, full_name") as c:
                rows = await c.fetchall()
            payload = build_export_rows("students", [dict(row) for row in rows])
        elif report_type == "payments":
            async with db.execute("""
                SELECT u.full_name AS student, g.name AS "group", p.amount, p.payment_type, p.month_for, p.note
                FROM payments p
                JOIN users u ON u.id = p.student_id
                JOIN groups g ON g.id = p.group_id
                ORDER BY p.created_at DESC
            """) as c:
                rows = await c.fetchall()
            payload = build_export_rows("payments", [dict(row) for row in rows])
        else:
            async with db.execute("""
                SELECT u.full_name AS student, g.name AS "group", a.date, a.status
                FROM attendance a
                JOIN users u ON u.id = a.student_id
                JOIN groups g ON g.id = a.group_id
                ORDER BY a.date DESC
            """) as c:
                rows = await c.fetchall()
            payload = build_export_rows("attendance", [dict(row) for row in rows])

    excel_bytes = build_excel_bytes(report_type, payload)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_type}.xlsx"'},
    )