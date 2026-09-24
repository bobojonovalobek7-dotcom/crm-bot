import pytest
from config import get_webapp_url
from services.menu_service import resolve_user_webapp_url
from bot.keyboards.default import get_main_keyboard
from database.models import init_db
from database.db import add_user, get_user, update_user_role, link_parent_student


@pytest.mark.anyio
async def test_resolve_user_webapp_urls():
    await init_db()

    # 1. Admin
    admin_url = await resolve_user_webapp_url(5341602920)
    assert admin_url.endswith("/admin")

    # 2. Teacher
    teacher_user = {"id": 12, "telegram_id": 999111, "role": "teacher", "full_name": "Ustoz"}
    teacher_url = await resolve_user_webapp_url(999111, teacher_user)
    assert teacher_url.endswith("/teacher/12")

    # 3. Student
    student_user = {"id": 44, "telegram_id": 999222, "role": "student", "full_name": "Oquvchi"}
    student_url = await resolve_user_webapp_url(999222, student_user)
    assert student_url.endswith("/student/44")


@pytest.mark.anyio
async def test_parent_resolves_to_first_child_url():
    await init_db()

    # Create parent and student
    await add_user(telegram_id=888001, full_name="Ota Test", phone="+998901112233", role="parent")
    await add_user(telegram_id=888002, full_name="Farzand Test", phone="+998901112244", role="student")

    parent = await get_user(888001)
    child = await get_user(888002)

    await link_parent_student(student_id=child["id"], parent_id=parent["id"], relation_type="ota")

    parent_url = await resolve_user_webapp_url(888001, parent)
    assert parent_url.endswith(f"/parent/{child['id']}")


@pytest.mark.anyio
async def test_update_user_role_in_db():
    await init_db()

    await add_user(telegram_id=777111, full_name="Yangilash Test", phone="+998931112233", role="student")
    user_before = await get_user(777111)
    assert user_before["role"] == "student"

    await update_user_role(777111, "parent")
    user_after = await get_user(777111)
    assert user_after["role"] == "parent"


def test_main_keyboard_webapp_attachment():
    # Verify CRM Web App is removed from reply keyboard to avoid clutter (dedicated blue chat menu button used)
    kb_admin = get_main_keyboard("admin")
    admin_texts = [b.text for row in kb_admin.keyboard for b in row]
    assert "📊 CRM Web App" not in admin_texts
    assert "👤 Yangi admin" in admin_texts

    # Verify Shaxsiy kabinet & CRM Web App are not cluttering parent and student keyboards
    kb_parent = get_main_keyboard("parent")
    parent_texts = [b.text for row in kb_parent.keyboard for b in row]
    assert "📱 Shaxsiy kabinet" not in parent_texts
    assert "📊 CRM Web App" not in parent_texts

    kb_student = get_main_keyboard("student")
    student_texts = [b.text for row in kb_student.keyboard for b in row]
    assert "📱 Shaxsiy kabinet" not in student_texts
    assert "📊 CRM Web App" not in student_texts

