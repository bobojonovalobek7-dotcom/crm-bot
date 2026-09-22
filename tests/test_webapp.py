import pytest
from httpx import AsyncClient, ASGITransport
from webapp.app import app
from database.models import init_db


@pytest.mark.anyio
async def test_webapp_routes_and_apis():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Home page
        res = await client.get("/")
        assert res.status_code == 200
        assert "EduCenter" in res.text

        # 2. Admin page
        res = await client.get("/admin")
        assert res.status_code == 200
        assert "CRM" in res.text

        # 3. Create group via web
        res = await client.post(
            "/admin/create-group",
            data={
                "name": "Web Django-01",
                "subject": "Python Django",
                "monthly_fee": 450000.0,
                "teacher_id": 1,
                "schedule": "Dush-Chor-Jum 18:00",
                "room": "1-xona",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # 4. Teacher page
        res = await client.get("/teacher/1")
        assert res.status_code == 200

        # 5. Parent page
        res = await client.get("/parent/1")
        assert res.status_code == 200

        # 6. Export Excel
        res = await client.get("/admin/export/students")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
