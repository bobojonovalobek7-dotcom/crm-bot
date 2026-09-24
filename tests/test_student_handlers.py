from config import get_effective_role
from bot.handlers.student import build_student_reply
from bot.keyboards.default import get_main_keyboard
from webapp.app import is_valid_user_role, build_payment_message


def test_schedule_reply():
    reply = build_student_reply("Dars jadvalim")
    assert "jadval" in reply.lower()


def test_payment_history_reply():
    reply = build_student_reply("To'lovlar tarixi")
    assert "to'lov" in reply.lower() or "to'lovlar" in reply.lower()


def test_guided_admin_creation_prompt_uses_step_by_step_flow():
    admin_reply = build_student_reply("Yangi admin")
    teacher_reply = build_student_reply("Yangi ustoz")

    assert "ism" in admin_reply.lower()
    assert "telefon" in admin_reply.lower()
    assert "telegram id" in admin_reply.lower()
    assert "/create_admin" not in admin_reply
    assert "ism" in teacher_reply.lower()
    assert "telefon" in teacher_reply.lower()
    assert "telegram id" in teacher_reply.lower()
    assert "/create_teacher" not in teacher_reply


def test_fake_telegram_id_is_rejected():
    from bot.handlers.admin import validate_telegram_id

    ok, _, error = validate_telegram_id("123456789")
    assert ok is False
    assert "haqiqiy" in (error or "").lower()

    ok2, value, error2 = validate_telegram_id("5341602920")
    assert ok2 is True
    assert value == 5341602920
    assert error2 is None


def test_help_reply_lists_creation_commands():
    reply = build_student_reply("Yordam")
    assert "yangi admin" in reply.lower()
    assert "yangi ustoz" in reply.lower()


def test_creation_session_is_cancelled_on_other_action():
    from bot.handlers.admin import should_cancel_creation_session

    assert should_cancel_creation_session("CRM Web App") is True
    assert should_cancel_creation_session("Yangi admin") is True
    assert should_cancel_creation_session("123456789") is False


def test_dashboard_summary_and_excel_export_contract():
    from webapp.app import build_dashboard_summary, build_export_rows

    summary = build_dashboard_summary(
        students=5,
        teachers=2,
        groups=3,
        total_revenue=1500000,
        attendance_rate=92,
        active_parents=4,
    )
    assert summary["students"] == 5
    assert summary["teachers"] == 2
    assert summary["total_revenue"] == 1500000
    assert "attendance_rate" in summary

    rows = build_export_rows("students", [
        {"full_name": "Ali Valiyev", "phone": "+99890", "role": "student"},
    ])
    assert rows[0][0] == "Ali Valiyev"
    assert rows[0][1] == "+99890"


def test_support_reply():
    reply = build_student_reply("Qo'llab-quvvatlash")
    assert "qo'llab" in reply.lower() or "support" in reply.lower()


def test_super_admin_role_priority_over_parent_db_role():
    assert get_effective_role(5341602920, "parent") == "super_admin"
    assert get_effective_role(5341602920, "teacher") == "super_admin"


def test_admin_keyboard_uses_https_safe_button():
    keyboard = get_main_keyboard("admin")
    texts = [button.text for row in keyboard.keyboard for button in row]
    assert not any("CRM Web App".lower() in text.lower() for text in texts)
    assert any("Yangi admin".lower() in text.lower() for text in texts)
    assert any("Yangi ustoz".lower() in text.lower() for text in texts)
    assert any("Yangi to'lov".lower() in text.lower() for text in texts)


def test_supports_admin_and_teacher_roles_for_user_creation():
    assert is_valid_user_role("admin") is True
    assert is_valid_user_role("teacher") is True
    assert is_valid_user_role("super_admin") is True
    assert is_valid_user_role("unknown") is False


def test_build_payment_message_includes_payment_content():
    msg = build_payment_message("Ali Valiyev", "Matematika", 350000, "naqd", "2026-09", "Karta")
    assert "To'lov qabul qilindi" in msg
    assert "Ali Valiyev" in msg
    assert "350" in msg


def test_role_menus_cover_parent_and_teacher_actions():
    parent = [button.text for row in get_main_keyboard("parent").keyboard for button in row]
    teacher = [button.text for row in get_main_keyboard("teacher").keyboard for button in row]
    admin = [button.text for row in get_main_keyboard("admin").keyboard for button in row]

    assert any("Dars jadvali".lower() in text.lower() for text in parent)
    assert any("Bugungi mashg'ulot".lower() in text.lower() for text in parent)
    assert any("Guruhlarim".lower() in text.lower() for text in teacher)
    assert any("Davomat".lower() in text.lower() for text in teacher)
    assert any("Yangi admin".lower() in text.lower() for text in admin)

    super_admin_kb = [button.text for row in get_main_keyboard("super_admin").keyboard for button in row]
    assert any("adminlar".lower() in text.lower() for text in super_admin_kb)
    assert any("yangi admin".lower() in text.lower() for text in super_admin_kb)
