import pytest
from fastapi.testclient import TestClient
from webapp.app import app
from database.models import init_db
from database.db import add_user, get_user, remove_admin
from services.menu_service import resolve_menu_button_text, resolve_user_webapp_url

client = TestClient(app)


@pytest.mark.anyio
async def test_all_five_portals_render():
    await init_db()

    # 1. Create a sample user for each role
    await add_user(telegram_id=601, full_name="Super Admin Bobur", phone="+998901111111", role="super_admin")
    await add_user(telegram_id=602, full_name="Admin Sardor", phone="+998902222222", role="admin")
    await add_user(telegram_id=603, full_name="Ustoz Nodir", phone="+998903333333", role="teacher")
    await add_user(telegram_id=604, full_name="Ota Jamshid", phone="+998904444444", role="parent")
    await add_user(telegram_id=605, full_name="Oquvchi Temur", phone="+998905555555", role="student")

    u_teacher = await get_user(603)
    u_parent = await get_user(604)
    u_student = await get_user(605)

    # 2. Test Admin Portal
    res_admin = client.get("/admin")
    assert res_admin.status_code == 200
    assert "EduCenter CRM" in res_admin.text
    assert "tab-superadmin" in res_admin.text
    assert "/admin/backup" in res_admin.text

    # 3. Test Teacher Portal
    res_teacher = client.get(f"/teacher/{u_teacher['id']}")
    assert res_teacher.status_code == 200
    assert "Ustoz Nodir" in res_teacher.text or "O'qituvchi" in res_teacher.text

    # 4. Test Parent Portal
    res_parent = client.get(f"/parent/{u_parent['id']}")
    assert res_parent.status_code == 200

    # 5. Test Student Portal
    res_student = client.get(f"/student/{u_student['id']}")
    assert res_student.status_code == 200
    assert "Oquvchi Temur" in res_student.text
    assert "Mening Darslarim" in res_student.text


@pytest.mark.anyio
async def test_database_backup_download():
    await init_db()
    res = client.get("/admin/backup")
    assert res.status_code == 200
    assert "application/octet-stream" in res.headers.get("content-type", "")
    assert len(res.content) > 0


@pytest.mark.anyio
async def test_delete_admin_workflow():
    await init_db()
    await add_user(telegram_id=699, full_name="Ochiriladigan Admin", phone="+998990000000", role="admin")
    admin_to_del = await get_user(699)
    assert admin_to_del is not None

    res = client.post("/admin/delete-admin", data={"admin_id": admin_to_del["id"]})
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    deleted = await get_user(699)
    assert deleted is None


def test_five_roles_menu_button_titles():
    assert resolve_menu_button_text("super_admin") == "👑 Super Admin Portali"
    assert resolve_menu_button_text("admin") == "🛡 Admin Portali"
    assert resolve_menu_button_text("teacher") == "👨‍🏫 Ustoz Portali"
    assert resolve_menu_button_text("parent") == "👨‍👩‍👧 Ota-ona Portali"
    assert resolve_menu_button_text("student") == "👨‍🎓 O'quvchi Portali"
