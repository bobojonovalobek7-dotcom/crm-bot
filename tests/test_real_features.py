import pytest
from config import get_webapp_url
from database.models import init_db
from database.db import (
    add_user,
    get_user,
    add_group,
    get_groups,
    get_teacher_groups,
    enroll_student,
    get_student_groups,
    get_group_students,
    unenroll_student,
    add_payment,
    get_student_payments,
    record_attendance,
    get_group_attendance,
    get_stats_summary,
)
from bot.handlers.student import get_real_student_data_reply


@pytest.mark.anyio
async def test_database_crud_and_real_flows():
    await init_db()

    # 1. Add teacher and student
    await add_user(telegram_id=999001, full_name="Test O'qituvchi", phone="+998901112233", role="teacher")
    await add_user(telegram_id=999002, full_name="Test O'quvchi", phone="+998904445566", role="student")

    teacher = await get_user(999001)
    student = await get_user(999002)

    assert teacher is not None
    assert teacher["full_name"] == "Test O'qituvchi"
    assert student is not None
    assert student["full_name"] == "Test O'quvchi"

    # 2. Add group
    group_id = await add_group(
        name="Test Matematika-101",
        subject="Matematika",
        monthly_fee=400000.0,
        teacher_id=teacher["id"],
        schedule="Dush-Chor-Jum 15:00",
        room="5-xona",
    )
    assert group_id is not None

    teacher_groups = await get_teacher_groups(teacher["id"])
    assert any(g["name"] == "Test Matematika-101" for g in teacher_groups)

    # 3. Enroll student
    await enroll_student(student["id"], group_id)
    student_groups = await get_student_groups(student["id"])
    assert any(g["id"] == group_id for g in student_groups)

    roster = await get_group_students(group_id)
    assert any(s["id"] == student["id"] for s in roster)

    # 4. Add payment
    payment_id = await add_payment(
        student_id=student["id"],
        group_id=group_id,
        amount=400000.0,
        payment_type="karta",
        month_for="2026-09",
        note="Test to'lov",
    )
    assert payment_id is not None

    payments = await get_student_payments(student["id"])
    assert len(payments) >= 1
    assert payments[0]["amount"] == 400000.0

    # 5. Record attendance
    await record_attendance(group_id, student["id"], "2026-09-22", "keldi")
    attendance = await get_group_attendance(group_id, "2026-09-22")
    assert any(a["student_id"] == student["id"] and a["status"] == "keldi" for a in attendance)

    # 6. Check stats summary
    stats = await get_stats_summary()
    assert stats["groups"] >= 1
    assert stats["total_revenue"] >= 400000.0

    # 7. Real student bot reply
    schedule_reply = await get_real_student_data_reply(dict(student), "Dars jadvalim")
    assert schedule_reply is not None
    assert "Test Matematika-101" in schedule_reply
    assert "15:00" in schedule_reply

    payment_reply = await get_real_student_data_reply(dict(student), "To'lovlar tarixi")
    assert payment_reply is not None
    assert "400,000" in payment_reply or "400 000" in payment_reply

    # 8. Unenroll student
    await unenroll_student(student["id"], group_id)
    updated_groups = await get_student_groups(student["id"])
    assert not any(g["id"] == group_id for g in updated_groups)


def test_webapp_url_generator():
    assert get_webapp_url("/admin").endswith("/admin")
    assert get_webapp_url("teacher/1").endswith("/teacher/1")
    assert get_webapp_url("").startswith("http")
