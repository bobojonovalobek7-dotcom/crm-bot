import pytest
from fastapi.testclient import TestClient
from database.models import init_db
from database.db import (
    add_user,
    get_user,
    link_parent_student,
    unlink_parent_student,
    get_parent_students,
    get_student_parents,
    get_all_parent_student_links,
    create_feedback,
    get_feedbacks,
    get_feedback_by_id,
    reply_to_feedback,
    add_group,
    enroll_student,
)
from bot.handlers.student import get_real_parent_data_reply, get_real_student_data_reply
from webapp.app import app
from services.notifications import (
    notify_attendance_change,
    notify_payment_receipt,
    notify_new_feedback,
    notify_feedback_reply,
)


@pytest.mark.anyio
async def test_parent_student_linking_and_unlinking():
    await init_db()

    # Create a parent and a student
    await add_user(telegram_id=888001, full_name="Muzaffar Ota", phone="+998901230001", role="parent")
    await add_user(telegram_id=888002, full_name="Jasur O'quvchi", phone="+998901230002", role="student")

    parent = await get_user(888001)
    student = await get_user(888002)

    assert parent is not None
    assert student is not None

    # Link parent to student
    await link_parent_student(parent["id"], student["id"], relation_type="ota")

    # Verify parent has student
    children = await get_parent_students(parent["id"])
    assert len(children) >= 1
    assert any(c["student_id"] == student["id"] and c["relation_type"] == "ota" for c in children)

    # Verify student has parent
    parents = await get_student_parents(student["id"])
    assert len(parents) >= 1
    assert any(p["parent_id"] == parent["id"] for p in parents)

    # Verify all links
    links = await get_all_parent_student_links()
    assert any(l["parent_id"] == parent["id"] and l["student_id"] == student["id"] for l in links)

    # Test parent bot queries (dars jadvali, to'lovlar, farzandlarim)
    reply, kb = await get_real_parent_data_reply(dict(parent), "Farzandlarim")
    assert reply is not None
    assert "Jasur O'quvchi" in str(kb) or "farzandlaringiz" in reply.lower()

    # Unlink parent and student
    await unlink_parent_student(parent["id"], student["id"])
    children_after = await get_parent_students(parent["id"])
    assert not any(c["student_id"] == student["id"] for c in children_after)


@pytest.mark.anyio
async def test_feedback_lifecycle_and_reply():
    await init_db()

    await add_user(telegram_id=888003, full_name="Gulnora Ona", phone="+998901230003", role="parent")
    await add_user(telegram_id=888004, full_name="Anvarbek", phone="+998901230004", role="student")

    parent = await get_user(888003)
    student = await get_user(888004)

    # Create feedback
    fb_id = await create_feedback(
        user_id=parent["id"],
        message="Darslar sifatidan juda mamnunmiz, rahmat!",
        feedback_type="taklif",
        student_id=student["id"],
    )
    assert fb_id is not None

    # Retrieve feedback
    feedbacks = await get_feedbacks()
    fb = await get_feedback_by_id(fb_id)
    assert fb is not None
    assert fb["status"] == "yangi"
    assert fb["feedback_type"] == "taklif"
    assert "mamnunmiz" in fb["message"]

    # Reply to feedback
    await reply_to_feedback(
        feedback_id=fb_id,
        reply_text="Tashakkur! Sizning fikringiz biz uchun qadrli.",
        admin_id=1,
    )

    fb_updated = await get_feedback_by_id(fb_id)
    assert fb_updated["status"] == "javob_berildi"
    assert "Tashakkur" in fb_updated["admin_reply"]


@pytest.mark.anyio
async def test_notifications_execute_without_error():
    await init_db()

    # Test that notification calls execute safely without crashing even if Telegram API is unreachable or mocked
    await notify_attendance_change(student_id=999999, group_id=999999, date="2026-09-22", status="kelmadi")
    await notify_payment_receipt(student_id=999999, group_id=999999, amount=350000, payment_type="karta", month_for="2026-09")
    await notify_new_feedback(feedback_id=999999)
    await notify_feedback_reply(feedback_id=999999)


def test_webapp_endpoints_parent_and_feedback():
    client = TestClient(app)

    # 1. Test parent page loading
    resp = client.get("/parent/1")
    assert resp.status_code == 200
    assert "Kabinet" in resp.text or "O'quvchi" in resp.text

    # 2. Test feedback submission endpoint
    fb_resp = client.post(
        "/feedback/create",
        data={
            "user_id": "1",
            "message": "Web orqali yuborilgan taklif",
            "feedback_type": "taklif",
        },
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["status"] == "success"

    # 3. Test link parent endpoint
    link_resp = client.post(
        "/admin/link-parent",
        data={
            "parent_id": "1",
            "student_id": "1",
            "relation_type": "ota",
        },
    )
    assert link_resp.status_code == 200
    assert link_resp.json()["status"] == "success"

    # 4. Test unlink parent endpoint
    unlink_resp = client.post(
        "/admin/unlink-parent",
        data={
            "parent_id": "1",
            "student_id": "1",
        },
    )
    assert unlink_resp.status_code == 200
    assert unlink_resp.json()["status"] == "success"
