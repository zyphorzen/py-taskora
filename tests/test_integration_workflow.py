import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient


class TestEndToEndWorkflow:
    async def test_full_user_lifecycle_workflow(self, client: AsyncClient):
        suffix = uuid.uuid4().hex[:8]
        username = f"e2e_user_{suffix}"
        email = f"e2e_{suffix}@example.com"
        password = "SecureE2EPass123!"

        reg_res = await client.post(
            "/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
            },
        )
        assert reg_res.status_code == 201
        user_data = reg_res.json()
        assert user_data["username"] == username
        assert user_data["email"] == email

        login_res = await client.post(
            "/auth/login",
            json={
                "username": username,
                "password": password,
            },
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_res = await client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["id"] == user_data["id"]

        cat_work_res = await client.post(
            "/categories",
            json={"name": f"Work_{suffix}", "color": "blue"},
            headers=headers,
        )
        assert cat_work_res.status_code == 201
        work_cat_id = cat_work_res.json()["id"]

        cat_pers_res = await client.post(
            "/categories",
            json={"name": f"Personal_{suffix}", "color": "green"},
            headers=headers,
        )
        assert cat_pers_res.status_code == 201
        pers_cat_id = cat_pers_res.json()["id"]

        now = datetime.now(timezone.utc)
        task_due = now + timedelta(days=2)
        task_res = await client.post(
            "/tasks",
            json={
                "title": "Complete Sprint Deliverable",
                "category_id": work_cat_id,
                "priority": "high",
                "due_date": task_due.isoformat(),
            },
            headers=headers,
        )
        assert task_res.status_code == 201
        task_id = task_res.json()["id"]

        sched_start = now + timedelta(days=1, hours=2)
        sched_res = await client.post(
            "/schedules",
            json={
                "title": "Sprint Review Sync",
                "category_id": work_cat_id,
                "start_time": sched_start.isoformat(),
                "end_time": (sched_start + timedelta(hours=1)).isoformat(),
                "is_recurring": True,
                "recurrence_pattern": "weekly",
                "recurrence_interval": 1,
            },
            headers=headers,
        )
        assert sched_res.status_code == 201
        sched_id = sched_res.json()["id"]

        rem_task_res = await client.post(
            "/reminders",
            json={
                "title": "Reminder: Sprint deliverable due tomorrow",
                "task_id": task_id,
                "remind_at": (task_due - timedelta(days=1)).isoformat(),
                "notification_type": "email",
            },
            headers=headers,
        )
        assert rem_task_res.status_code == 201
        rem_task_id = rem_task_res.json()["id"]

        rem_sched_res = await client.post(
            "/reminders",
            json={
                "title": "Reminder: Sprint review starts in 10 mins",
                "schedule_id": sched_id,
                "remind_at": (sched_start - timedelta(minutes=10)).isoformat(),
                "notification_type": "push",
            },
            headers=headers,
        )
        assert rem_sched_res.status_code == 201
        rem_sched_id = rem_sched_res.json()["id"]

        patch_status_res = await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert patch_status_res.status_code == 200
        assert patch_status_res.json()["status"] == "in_progress"

        complete_res = await client.post(
            f"/tasks/{task_id}/complete",
            headers=headers,
        )
        assert complete_res.status_code == 200
        assert complete_res.json()["status"] == "completed"
        assert complete_res.json()["completed_at"] is not None

        occ_res = await client.get(
            "/schedules/occurrences",
            params={
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=21)).isoformat(),
            },
            headers=headers,
        )
        assert occ_res.status_code == 200
        occurrences = occ_res.json()
        assert len(occurrences) >= 3

        cal_res = await client.get(
            "/calendar/events",
            params={
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=7)).isoformat(),
            },
            headers=headers,
        )
        assert cal_res.status_code == 200
        cal_data = cal_res.json()
        assert cal_data["total_tasks"] >= 1
        assert cal_data["total_schedules"] >= 1
        assert cal_data["total_reminders"] >= 1

        day_res = await client.get(
            "/calendar/day",
            params={"target_date": sched_start.date().isoformat()},
            headers=headers,
        )
        assert day_res.status_code == 200
        day_data = day_res.json()
        assert any(s["title"] == "Sprint Review Sync" for s in day_data["schedules"])

        month_sum_res = await client.get(
            "/calendar/month-summary",
            params={"year": now.year, "month": now.month},
            headers=headers,
        )
        assert month_sum_res.status_code == 200
        assert len(month_sum_res.json()) >= 28

        dash_res = await client.get("/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data["tasks"]["completed"] >= 1
        assert dash_data["tasks"]["completion_rate"] == 100.0
        assert dash_data["schedules"]["total"] >= 1
        assert dash_data["reminders"]["total"] >= 2
        assert len(dash_data["categories"]) >= 2

        stats_res = await client.get("/dashboard/quick-stats", headers=headers)
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert stats_data["completed_tasks"] >= 1
        assert stats_data["total_schedules"] >= 1

        mark_res = await client.post(
            f"/reminders/{rem_task_id}/mark-sent",
            headers=headers,
        )
        assert mark_res.status_code == 200
        assert mark_res.json()["is_sent"] is True

        del_cat_res = await client.delete(
            f"/categories/{work_cat_id}",
            headers=headers,
        )
        assert del_cat_res.status_code == 204

        check_task_res = await client.get(f"/tasks/{task_id}", headers=headers)
        assert check_task_res.status_code == 200
        assert check_task_res.json()["category_id"] is None

        check_sched_res = await client.get(f"/schedules/{sched_id}", headers=headers)
        assert check_sched_res.status_code == 200
        assert check_sched_res.json()["category_id"] is None

    async def test_multi_user_isolation_e2e(self, client: AsyncClient):
        suffix_a = uuid.uuid4().hex[:8]
        suffix_b = uuid.uuid4().hex[:8]

        reg_a = await client.post(
            "/auth/register",
            json={
                "username": f"user_a_{suffix_a}",
                "email": f"usera_{suffix_a}@example.com",
                "password": "Password123!",
            },
        )
        assert reg_a.status_code == 201

        reg_b = await client.post(
            "/auth/register",
            json={
                "username": f"user_b_{suffix_b}",
                "email": f"userb_{suffix_b}@example.com",
                "password": "Password123!",
            },
        )
        assert reg_b.status_code == 201

        login_a = await client.post(
            "/auth/login",
            json={"username": f"user_a_{suffix_a}", "password": "Password123!"},
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        login_b = await client.post(
            "/auth/login",
            json={"username": f"user_b_{suffix_b}", "password": "Password123!"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        now = datetime.now(timezone.utc)
        task_a_res = await client.post(
            "/tasks",
            json={
                "title": "Secret Task A",
                "due_date": (now + timedelta(days=1)).isoformat(),
            },
            headers=headers_a,
        )
        assert task_a_res.status_code == 201
        task_a_id = task_a_res.json()["id"]

        sched_a_res = await client.post(
            "/schedules",
            json={
                "title": "Secret Meeting A",
                "start_time": (now + timedelta(hours=1)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat(),
            },
            headers=headers_a,
        )
        assert sched_a_res.status_code == 201
        sched_a_id = sched_a_res.json()["id"]

        rem_a_res = await client.post(
            "/reminders",
            json={
                "title": "Secret Reminder A",
                "remind_at": (now + timedelta(minutes=30)).isoformat(),
            },
            headers=headers_a,
        )
        assert rem_a_res.status_code == 201
        rem_a_id = rem_a_res.json()["id"]

        get_task_b = await client.get(f"/tasks/{task_a_id}", headers=headers_b)
        assert get_task_b.status_code == 404

        get_sched_b = await client.get(f"/schedules/{sched_a_id}", headers=headers_b)
        assert get_sched_b.status_code == 404

        get_rem_b = await client.get(f"/reminders/{rem_a_id}", headers=headers_b)
        assert get_rem_b.status_code == 404

        patch_task_b = await client.patch(
            f"/tasks/{task_a_id}",
            json={"title": "Hacked Title"},
            headers=headers_b,
        )
        assert patch_task_b.status_code == 404

        del_sched_b = await client.delete(f"/schedules/{sched_a_id}", headers=headers_b)
        assert del_sched_b.status_code == 404

        b_tasks = await client.get("/tasks", headers=headers_b)
        assert b_tasks.status_code == 200
        assert b_tasks.json() == []

        b_scheds = await client.get("/schedules", headers=headers_b)
        assert b_scheds.status_code == 200
        assert b_scheds.json() == []

        b_rems = await client.get("/reminders", headers=headers_b)
        assert b_rems.status_code == 200
        assert b_rems.json() == []

        b_dash = await client.get("/dashboard", headers=headers_b)
        assert b_dash.status_code == 200
        assert b_dash.json()["tasks"]["total"] == 0
        assert b_dash.json()["schedules"]["total"] == 0
        assert b_dash.json()["reminders"]["total"] == 0
