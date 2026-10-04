import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestCalendarEvents:
    async def test_calendar_events_empty(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=3)
        end = now - timedelta(days=1)
        res = await client.get(
            "/calendar/events",
            params={"start_date": start.isoformat(), "end_date": end.isoformat()},
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_items"] == 0
        assert data["total_schedules"] == 0
        assert data["total_tasks"] == 0
        assert data["total_reminders"] == 0
        assert data["schedules"] == []
        assert data["tasks"] == []
        assert data["reminders"] == []

    async def test_calendar_events_aggregation(self, client: AsyncClient, auth_headers):
        base_time = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)

        sched_res = await client.post(
            "/schedules",
            json={
                "title": "Quarterly Review",
                "start_time": base_time.isoformat(),
                "end_time": (base_time + timedelta(hours=2)).isoformat(),
            },
            headers=auth_headers,
        )
        assert sched_res.status_code == 201

        rec_res = await client.post(
            "/schedules",
            json={
                "title": "Daily Standup",
                "start_time": (base_time + timedelta(days=1)).isoformat(),
                "end_time": (base_time + timedelta(days=1, hours=1)).isoformat(),
                "is_recurring": True,
                "recurrence_pattern": "daily",
                "recurrence_interval": 1,
            },
            headers=auth_headers,
        )
        assert rec_res.status_code == 201

        task_res = await client.post(
            "/tasks",
            json={
                "title": "Prepare Slide Deck",
                "due_date": (base_time + timedelta(days=2)).isoformat(),
            },
            headers=auth_headers,
        )
        assert task_res.status_code == 201

        rem_res = await client.post(
            "/reminders",
            json={
                "title": "Ping team about deck",
                "remind_at": (base_time + timedelta(days=2, hours=3)).isoformat(),
            },
            headers=auth_headers,
        )
        assert rem_res.status_code == 201

        window_start = base_time - timedelta(days=1)
        window_end = base_time + timedelta(days=4)

        res = await client.get(
            "/calendar/events",
            params={
                "start_date": window_start.isoformat(),
                "end_date": window_end.isoformat(),
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["total_items"] > 0
        assert data["total_tasks"] >= 1
        assert any(t["title"] == "Prepare Slide Deck" for t in data["tasks"])
        assert data["total_reminders"] >= 1
        assert any(r["title"] == "Ping team about deck" for r in data["reminders"])
        assert any(s["title"] == "Quarterly Review" for s in data["schedules"])
        assert any(s["title"] == "Daily Standup" for s in data["schedules"])

    async def test_calendar_events_include_flags(
        self, client: AsyncClient, auth_headers
    ):
        base_time = datetime(2026, 11, 5, 9, 0, 0, tzinfo=timezone.utc)

        await client.post(
            "/schedules",
            json={
                "title": "Included Schedule",
                "start_time": base_time.isoformat(),
                "end_time": (base_time + timedelta(hours=1)).isoformat(),
            },
            headers=auth_headers,
        )
        await client.post(
            "/tasks",
            json={
                "title": "Included Task",
                "due_date": base_time.isoformat(),
            },
            headers=auth_headers,
        )
        await client.post(
            "/reminders",
            json={
                "title": "Included Reminder",
                "remind_at": base_time.isoformat(),
            },
            headers=auth_headers,
        )

        res = await client.get(
            "/calendar/events",
            params={
                "start_date": (base_time - timedelta(hours=1)).isoformat(),
                "end_date": (base_time + timedelta(hours=2)).isoformat(),
                "include_schedules": "true",
                "include_tasks": "false",
                "include_reminders": "false",
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_schedules"] >= 1
        assert data["total_tasks"] == 0
        assert data["total_reminders"] == 0
        assert data["tasks"] == []
        assert data["reminders"] == []

    async def test_calendar_events_validation_error(
        self, client: AsyncClient, auth_headers
    ):
        now = datetime.now(timezone.utc)
        res = await client.get(
            "/calendar/events",
            params={
                "start_date": now.isoformat(),
                "end_date": (now - timedelta(days=1)).isoformat(),
            },
            headers=auth_headers,
        )
        assert res.status_code == 400
        assert (
            "end_date must be greater than or equal to start_date"
            in res.json()["detail"]
        )

    async def test_calendar_user_isolation(self, client: AsyncClient, create_user):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        dt = datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        await client.post(
            "/schedules",
            json={
                "title": "Confidential Event A",
                "start_time": dt.isoformat(),
                "end_time": (dt + timedelta(hours=1)).isoformat(),
            },
            headers=h_a,
        )

        res_b = await client.get(
            "/calendar/events",
            params={
                "start_date": (dt - timedelta(days=1)).isoformat(),
                "end_date": (dt + timedelta(days=1)).isoformat(),
            },
            headers=h_b,
        )
        assert res_b.status_code == 200
        assert not any(
            s["title"] == "Confidential Event A" for s in res_b.json()["schedules"]
        )


class TestCalendarViews:
    async def test_calendar_day_view(self, client: AsyncClient, auth_headers):
        day_date = "2026-10-15"
        base_time = datetime(2026, 10, 15, 14, 0, 0, tzinfo=timezone.utc)

        await client.post(
            "/schedules",
            json={
                "title": "Design Workshop",
                "start_time": base_time.isoformat(),
                "end_time": (base_time + timedelta(hours=3)).isoformat(),
            },
            headers=auth_headers,
        )

        res = await client.get(
            "/calendar/day",
            params={"target_date": day_date},
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert any(s["title"] == "Design Workshop" for s in data["schedules"])

    async def test_calendar_month_summary(self, client: AsyncClient, auth_headers):
        dt1 = datetime(2026, 10, 4, 11, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 10, 18, 16, 0, 0, tzinfo=timezone.utc)

        await client.post(
            "/schedules",
            json={
                "title": "First Sunday Session",
                "start_time": dt1.isoformat(),
                "end_time": (dt1 + timedelta(hours=1)).isoformat(),
            },
            headers=auth_headers,
        )
        await client.post(
            "/tasks",
            json={
                "title": "Mid-Month Deliverable",
                "due_date": dt2.isoformat(),
            },
            headers=auth_headers,
        )

        res = await client.get(
            "/calendar/month-summary",
            params={"year": 2026, "month": 10},
            headers=auth_headers,
        )
        assert res.status_code == 200
        summaries = res.json()
        assert len(summaries) == 31

        day4 = next(s for s in summaries if s["date"] == "2026-10-04")
        assert day4["schedules_count"] >= 1

        day18 = next(s for s in summaries if s["date"] == "2026-10-18")
        assert day18["tasks_count"] >= 1
