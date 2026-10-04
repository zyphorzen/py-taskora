import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestDashboard:
    async def test_get_dashboard_empty(self, client: AsyncClient, auth_headers):
        res = await client.get("/dashboard", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()

        assert data["tasks"]["total"] == 0
        assert data["tasks"]["completed"] == 0
        assert data["tasks"]["pending"] == 0
        assert data["tasks"]["overdue"] == 0
        assert data["tasks"]["completion_rate"] == 0.0
        assert data["tasks"]["by_status"]["todo"] == 0

        assert data["schedules"]["total"] == 0
        assert data["schedules"]["today_count"] == 0
        assert data["schedules"]["upcoming_count"] == 0

        assert data["reminders"]["total"] == 0
        assert data["reminders"]["pending_count"] == 0
        assert data["reminders"]["due_count"] == 0

        assert data["categories"] == []
        assert data["recent_urgent_tasks"] == []
        assert data["upcoming_schedules"] == []
        assert data["due_reminders"] == []

    async def test_get_dashboard_populated(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)

        cat_res = await client.post(
            "/categories",
            json={"name": f"Project_{uuid.uuid4().hex[:6]}", "color": "blue"},
            headers=auth_headers,
        )
        assert cat_res.status_code == 201
        cat_id = cat_res.json()["id"]

        t1_res = await client.post(
            "/tasks",
            json={
                "title": "Urgent Launch Task",
                "priority": "urgent",
                "status": "in_progress",
                "category_id": cat_id,
                "due_date": (now + timedelta(hours=2)).isoformat(),
            },
            headers=auth_headers,
        )
        assert t1_res.status_code == 201

        t2_res = await client.post(
            "/tasks",
            json={
                "title": "Completed Task",
                "priority": "medium",
                "status": "todo",
                "category_id": cat_id,
            },
            headers=auth_headers,
        )
        assert t2_res.status_code == 201
        t2_id = t2_res.json()["id"]
        await client.post(f"/tasks/{t2_id}/complete", headers=auth_headers)

        t3_res = await client.post(
            "/tasks",
            json={
                "title": "Overdue Task",
                "priority": "high",
                "status": "todo",
                "due_date": (now - timedelta(days=2)).isoformat(),
            },
            headers=auth_headers,
        )
        assert t3_res.status_code == 201

        s1_res = await client.post(
            "/schedules",
            json={
                "title": "Today Standup",
                "category_id": cat_id,
                "start_time": (now + timedelta(minutes=10)).isoformat(),
                "end_time": (now + timedelta(minutes=40)).isoformat(),
            },
            headers=auth_headers,
        )
        assert s1_res.status_code == 201

        r1_res = await client.post(
            "/reminders",
            json={
                "title": "Due Reminder Notice",
                "remind_at": (now - timedelta(minutes=5)).isoformat(),
            },
            headers=auth_headers,
        )
        assert r1_res.status_code == 201

        res = await client.get("/dashboard", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()

        assert data["tasks"]["total"] >= 3
        assert data["tasks"]["completed"] >= 1
        assert data["tasks"]["pending"] >= 2
        assert data["tasks"]["overdue"] >= 1
        assert data["tasks"]["completion_rate"] > 0

        assert data["schedules"]["total"] >= 1
        assert data["schedules"]["today_count"] >= 1
        assert data["schedules"]["upcoming_count"] >= 1

        assert data["reminders"]["total"] >= 1
        assert data["reminders"]["due_count"] >= 1

        matching_cat = next(c for c in data["categories"] if c["id"] == cat_id)
        assert matching_cat["task_count"] >= 2
        assert matching_cat["schedule_count"] >= 1

        assert any(
            t["title"] == "Urgent Launch Task" for t in data["recent_urgent_tasks"]
        )
        assert any(s["title"] == "Today Standup" for s in data["upcoming_schedules"])
        assert any(r["title"] == "Due Reminder Notice" for r in data["due_reminders"])

    async def test_get_quick_stats(self, client: AsyncClient, auth_headers):
        res = await client.get("/dashboard/quick-stats", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "pending_tasks" in data
        assert "overdue_tasks" in data
        assert "total_schedules" in data
        assert "upcoming_schedules" in data
        assert "today_schedules" in data
        assert "pending_reminders" in data
        assert "due_reminders" in data

    async def test_dashboard_user_isolation(self, client: AsyncClient, create_user):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        await client.post(
            "/tasks",
            json={"title": "User A Private Task"},
            headers=h_a,
        )

        res_b = await client.get("/dashboard", headers=h_b)
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["tasks"]["total"] == 0
        assert data_b["recent_urgent_tasks"] == []
