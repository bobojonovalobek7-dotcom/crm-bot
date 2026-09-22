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
    # 1. Without HTTPS URL
    kb_http = get_main_keyboard("admin", webapp_url="http://localhost:8000/admin")
    crm_btn_http = next(
        b for row in kb_http.keyboard for b in row if "CRM Web App" in b.text
    )
    assert crm_btn_http.web_app is None

    # 2. With HTTPS URL
    https_url = "https://crm.educenter.uz/admin"
    kb_https = get_main_keyboard("admin", webapp_url=https_url)
    crm_btn_https = next(
        b for row in kb_https.keyboard for b in row if "CRM Web App" in b.text
    )
    assert crm_btn_https.web_app is not None
    assert crm_btn_https.web_app.url == https_url

    # 3. Verify Shaxsiy kabinet is removed from parent and student keyboards
    kb_parent = get_main_keyboard("parent")
    parent_texts = [b.text for row in kb_parent.keyboard for b in row]
    assert "📱 Shaxsiy kabinet" not in parent_texts

    kb_student = get_main_keyboard("student")
    student_texts = [b.text for row in kb_student.keyboard for b in row]
    assert "📱 Shaxsiy kabinet" not in student_texts

