import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestReminderCRUD:
    async def test_create_reminder_standalone_success(
        self, client: AsyncClient, user_and_token
    ):
        user, _, headers = user_and_token
        remind_time = datetime.now(timezone.utc) + timedelta(hours=2)
        payload = {
            "title": "Drink water",
            "remind_at": remind_time.isoformat(),
            "notification_type": "push",
        }
        res = await client.post("/reminders", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Drink water"
        assert data["user_id"] == str(user.id)
        assert data["task_id"] is None
        assert data["schedule_id"] is None
        assert data["notification_type"] == "push"
        assert data["is_sent"] is False
        assert data["sent_at"] is None
        assert uuid.UUID(data["id"])

    async def test_create_reminder_with_task_success(
        self, client: AsyncClient, auth_headers
    ):
        task_res = await client.post(
            "/tasks",
            json={"title": "Submit Quarterly Report", "priority": "high"},
            headers=auth_headers,
        )
        assert task_res.status_code == 201
        task_id = task_res.json()["id"]

        remind_time = datetime.now(timezone.utc) + timedelta(days=1)
        payload = {
            "title": "Reminder for task report",
            "task_id": task_id,
            "remind_at": remind_time.isoformat(),
            "notification_type": "email",
        }
        res = await client.post("/reminders", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["task_id"] == task_id
        assert data["schedule_id"] is None
        assert data["notification_type"] == "email"

    async def test_create_reminder_with_schedule_success(
        self, client: AsyncClient, auth_headers
    ):
        now = datetime.now(timezone.utc)
        sched_res = await client.post(
            "/schedules",
            json={
                "title": "Client Sync",
                "start_time": (now + timedelta(hours=3)).isoformat(),
                "end_time": (now + timedelta(hours=4)).isoformat(),
            },
            headers=auth_headers,
        )
        assert sched_res.status_code == 201
        sched_id = sched_res.json()["id"]

        remind_time = now + timedelta(hours=2, minutes=45)
        payload = {
            "title": "Sync starting in 15 mins",
            "schedule_id": sched_id,
            "remind_at": remind_time.isoformat(),
            "notification_type": "in_app",
        }
        res = await client.post("/reminders", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["schedule_id"] == sched_id
        assert data["task_id"] is None
        assert data["notification_type"] == "in_app"

    async def test_create_reminder_with_foreign_task_fails(
        self, client: AsyncClient, create_user
    ):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        task_res = await client.post(
            "/tasks",
            json={"title": "Private Task A"},
            headers=h_a,
        )
        assert task_res.status_code == 201
        task_id = task_res.json()["id"]

        now = datetime.now(timezone.utc)
        res = await client.post(
            "/reminders",
            json={
                "title": "Intrusion Attempt",
                "task_id": task_id,
                "remind_at": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_b,
        )
        assert res.status_code == 400
        assert "Task not found" in res.json()["detail"]

    async def test_create_reminder_with_foreign_schedule_fails(
        self, client: AsyncClient, create_user
    ):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        now = datetime.now(timezone.utc)
        sched_res = await client.post(
            "/schedules",
            json={
                "title": "Private Schedule A",
                "start_time": (now + timedelta(hours=2)).isoformat(),
                "end_time": (now + timedelta(hours=3)).isoformat(),
            },
            headers=h_a,
        )
        assert sched_res.status_code == 201
        sched_id = sched_res.json()["id"]

        res = await client.post(
            "/reminders",
            json={
                "title": "Intrusion Reminder",
                "schedule_id": sched_id,
                "remind_at": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_b,
        )
        assert res.status_code == 400
        assert "Schedule not found" in res.json()["detail"]

    async def test_create_reminder_validation_error(
        self, client: AsyncClient, auth_headers
    ):
        res = await client.post(
            "/reminders",
            json={"title": "", "remind_at": "invalid-datetime"},
            headers=auth_headers,
        )
        assert res.status_code == 422


class TestReminderQueriesAndFilters:
    async def test_get_due_reminders(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(minutes=15)
        future_time = now + timedelta(hours=2)

        res_due = await client.post(
            "/reminders",
            json={
                "title": "Due Reminder",
                "remind_at": past_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert res_due.status_code == 201
        due_id = res_due.json()["id"]

        res_future = await client.post(
            "/reminders",
            json={
                "title": "Future Reminder",
                "remind_at": future_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert res_future.status_code == 201
        future_id = res_future.json()["id"]

        res_already_sent = await client.post(
            "/reminders",
            json={
                "title": "Sent Past Reminder",
                "remind_at": past_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert res_already_sent.status_code == 201
        sent_id = res_already_sent.json()["id"]
        await client.post(f"/reminders/{sent_id}/mark-sent", headers=auth_headers)

        res = await client.get("/reminders/due", headers=auth_headers)
        assert res.status_code == 200
        due_list = res.json()
        due_ids = [r["id"] for r in due_list]

        assert due_id in due_ids
        assert future_id not in due_ids
        assert sent_id not in due_ids

    async def test_get_reminders_filters(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/reminders",
            json={
                "title": "Upcoming Reminder 1",
                "remind_at": (now + timedelta(hours=10)).isoformat(),
            },
            headers=auth_headers,
        )
        assert r1.status_code == 201
        r1_id = r1.json()["id"]

        r2 = await client.post(
            "/reminders",
            json={
                "title": "Past Reminder 2",
                "remind_at": (now - timedelta(hours=5)).isoformat(),
            },
            headers=auth_headers,
        )
        assert r2.status_code == 201
        r2_id = r2.json()["id"]
        await client.post(f"/reminders/{r2_id}/mark-sent", headers=auth_headers)

        res_all = await client.get("/reminders", headers=auth_headers)
        assert res_all.status_code == 200
        all_ids = [r["id"] for r in res_all.json()]
        assert r1_id in all_ids
        assert r2_id in all_ids

        res_sent = await client.get("/reminders?is_sent=true", headers=auth_headers)
        assert res_sent.status_code == 200
        sent_ids = [r["id"] for r in res_sent.json()]
        assert r2_id in sent_ids
        assert r1_id not in sent_ids

        res_unsent = await client.get("/reminders?is_sent=false", headers=auth_headers)
        assert res_unsent.status_code == 200
        unsent_ids = [r["id"] for r in res_unsent.json()]
        assert r1_id in unsent_ids
        assert r2_id not in unsent_ids

        res_upcoming = await client.get(
            "/reminders?upcoming=true", headers=auth_headers
        )
        assert res_upcoming.status_code == 200
        upcoming_ids = [r["id"] for r in res_upcoming.json()]
        assert r1_id in upcoming_ids
        assert r2_id not in upcoming_ids


class TestReminderDetailsAndUpdates:
    async def test_get_reminder_by_id_and_isolation(
        self, client: AsyncClient, create_user
    ):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        now = datetime.now(timezone.utc)
        res_create = await client.post(
            "/reminders",
            json={
                "title": "Personal secret reminder",
                "remind_at": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_a,
        )
        assert res_create.status_code == 201
        reminder_id = res_create.json()["id"]

        res_get_a = await client.get(f"/reminders/{reminder_id}", headers=h_a)
        assert res_get_a.status_code == 200
        assert res_get_a.json()["id"] == reminder_id

        res_get_b = await client.get(f"/reminders/{reminder_id}", headers=h_b)
        assert res_get_b.status_code == 404

    async def test_update_reminder(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        res_create = await client.post(
            "/reminders",
            json={
                "title": "Initial reminder title",
                "remind_at": (now + timedelta(hours=1)).isoformat(),
                "notification_type": "push",
            },
            headers=auth_headers,
        )
        assert res_create.status_code == 201
        reminder_id = res_create.json()["id"]

        new_time = now + timedelta(hours=5)
        update_payload = {
            "title": "Updated reminder title",
            "remind_at": new_time.isoformat(),
            "notification_type": "email",
        }
        res_patch = await client.patch(
            f"/reminders/{reminder_id}",
            json=update_payload,
            headers=auth_headers,
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["title"] == "Updated reminder title"
        assert data["notification_type"] == "email"

    async def test_mark_reminder_sent(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        res_create = await client.post(
            "/reminders",
            json={
                "title": "Doctor Appointment reminder",
                "remind_at": (now + timedelta(minutes=30)).isoformat(),
            },
            headers=auth_headers,
        )
        assert res_create.status_code == 201
        reminder_id = res_create.json()["id"]
        assert res_create.json()["is_sent"] is False
        assert res_create.json()["sent_at"] is None

        res_sent = await client.post(
            f"/reminders/{reminder_id}/mark-sent",
            headers=auth_headers,
        )
        assert res_sent.status_code == 200
        data = res_sent.json()
        assert data["is_sent"] is True
        assert data["sent_at"] is not None

    async def test_delete_reminder_and_cascade_from_task(
        self, client: AsyncClient, auth_headers
    ):
        task_res = await client.post(
            "/tasks",
            json={"title": "Task with cascading reminder"},
            headers=auth_headers,
        )
        assert task_res.status_code == 201
        task_id = task_res.json()["id"]

        now = datetime.now(timezone.utc)
        rem_res = await client.post(
            "/reminders",
            json={
                "title": "Will be deleted on cascade",
                "task_id": task_id,
                "remind_at": (now + timedelta(hours=1)).isoformat(),
            },
            headers=auth_headers,
        )
        assert rem_res.status_code == 201
        rem_id = rem_res.json()["id"]

        del_task = await client.delete(f"/tasks/{task_id}", headers=auth_headers)
        assert del_task.status_code == 204

        check_rem = await client.get(f"/reminders/{rem_id}", headers=auth_headers)
        assert check_rem.status_code == 404

    async def test_delete_reminder_direct(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        rem_res = await client.post(
            "/reminders",
            json={
                "title": "Direct delete reminder",
                "remind_at": (now + timedelta(hours=1)).isoformat(),
            },
            headers=auth_headers,
        )
        assert rem_res.status_code == 201
        rem_id = rem_res.json()["id"]

        del_res = await client.delete(f"/reminders/{rem_id}", headers=auth_headers)
        assert del_res.status_code == 204

        check_res = await client.get(f"/reminders/{rem_id}", headers=auth_headers)
        assert check_res.status_code == 404
