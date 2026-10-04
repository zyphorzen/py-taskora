import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestRecurringSchedules:
    async def test_create_recurring_schedule_daily(
        self, client: AsyncClient, auth_headers
    ):
        now = datetime.now(timezone.utc)
        payload = {
            "title": "Daily Standup",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(minutes=30)).isoformat(),
            "is_recurring": True,
            "recurrence_pattern": "daily",
            "recurrence_interval": 1,
            "recurrence_end_date": (now + timedelta(days=30)).isoformat(),
        }
        res = await client.post("/schedules", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["is_recurring"] is True
        assert data["recurrence_pattern"] == "daily"
        assert data["recurrence_interval"] == 1
        assert data["recurrence_end_date"] is not None

    async def test_create_recurring_validation(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        res_missing_pattern = await client.post(
            "/schedules",
            json={
                "title": "Invalid Recurring",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
                "is_recurring": True,
            },
            headers=auth_headers,
        )
        assert res_missing_pattern.status_code == 422

        res_invalid_end = await client.post(
            "/schedules",
            json={
                "title": "Invalid End Limit",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
                "is_recurring": True,
                "recurrence_pattern": "daily",
                "recurrence_end_date": (now - timedelta(days=1)).isoformat(),
            },
            headers=auth_headers,
        )
        assert res_invalid_end.status_code == 422

    async def test_occurrences_daily_expansion(self, client: AsyncClient, create_user):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        start_base = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
        payload = {
            "title": "Morning Routine",
            "start_time": start_base.isoformat(),
            "end_time": (start_base + timedelta(minutes=45)).isoformat(),
            "is_recurring": True,
            "recurrence_pattern": "daily",
            "recurrence_interval": 1,
        }
        create_res = await client.post("/schedules", json=payload, headers=headers)
        assert create_res.status_code == 201
        sch_id = create_res.json()["id"]

        window_start = start_base
        window_end = start_base + timedelta(days=6, hours=23)

        res = await client.get(
            "/schedules/occurrences",
            params={
                "start_date": window_start.isoformat(),
                "end_date": window_end.isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 200
        occurrences = res.json()
        assert len(occurrences) == 7
        for i, occ in enumerate(occurrences):
            assert occ["schedule_id"] == sch_id
            assert occ["is_recurring"] is True
            assert occ["recurrence_pattern"] == "daily"
            expected_start = start_base + timedelta(days=i)
            assert datetime.fromisoformat(occ["start_time"]) == expected_start

    async def test_occurrences_weekly_expansion(self, client: AsyncClient, create_user):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        start_base = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
        payload = {
            "title": "Weekly Team Sync",
            "start_time": start_base.isoformat(),
            "end_time": (start_base + timedelta(hours=1)).isoformat(),
            "is_recurring": True,
            "recurrence_pattern": "weekly",
            "recurrence_interval": 1,
        }
        await client.post("/schedules", json=payload, headers=headers)

        window_start = start_base
        window_end = start_base + timedelta(days=27, hours=23)

        res = await client.get(
            "/schedules/occurrences",
            params={
                "start_date": window_start.isoformat(),
                "end_date": window_end.isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 200
        assert len(res.json()) == 4

    async def test_occurrences_monthly_expansion(
        self, client: AsyncClient, create_user
    ):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        start_base = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)
        payload = {
            "title": "Monthly Billing Review",
            "start_time": start_base.isoformat(),
            "end_time": (start_base + timedelta(hours=2)).isoformat(),
            "is_recurring": True,
            "recurrence_pattern": "monthly",
            "recurrence_interval": 1,
        }
        await client.post("/schedules", json=payload, headers=headers)

        window_start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        window_end = datetime(2026, 11, 1, tzinfo=timezone.utc)

        res = await client.get(
            "/schedules/occurrences",
            params={
                "start_date": window_start.isoformat(),
                "end_date": window_end.isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 200
        assert len(res.json()) == 3

    async def test_occurrences_respect_end_date_limit(
        self, client: AsyncClient, create_user
    ):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        start_base = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
        end_limit = start_base + timedelta(days=2)
        payload = {
            "title": "Short workshop series",
            "start_time": start_base.isoformat(),
            "end_time": (start_base + timedelta(hours=1)).isoformat(),
            "is_recurring": True,
            "recurrence_pattern": "daily",
            "recurrence_interval": 1,
            "recurrence_end_date": end_limit.isoformat(),
        }
        await client.post("/schedules", json=payload, headers=headers)

        res = await client.get(
            "/schedules/occurrences",
            params={
                "start_date": start_base.isoformat(),
                "end_date": (start_base + timedelta(days=10)).isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 200
        assert len(res.json()) == 3

    async def test_stop_recurrence_endpoint(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        create_res = await client.post(
            "/schedules",
            json={
                "title": "Will be cancelled recurring",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
                "is_recurring": True,
                "recurrence_pattern": "weekly",
            },
            headers=auth_headers,
        )
        sch_id = create_res.json()["id"]

        stop_res = await client.post(
            f"/schedules/{sch_id}/stop-recurrence",
            headers=auth_headers,
        )
        assert stop_res.status_code == 200
        data = stop_res.json()
        assert data["is_recurring"] is False
        assert data["recurrence_end_date"] is not None

    async def test_occurrences_user_isolation(self, client: AsyncClient, create_user):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        start_time = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
        await client.post(
            "/schedules",
            json={
                "title": "User A Recurring",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(hours=1)).isoformat(),
                "is_recurring": True,
                "recurrence_pattern": "daily",
            },
            headers=h_a,
        )
        await client.post(
            "/schedules",
            json={
                "title": "User B Recurring",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(hours=1)).isoformat(),
                "is_recurring": True,
                "recurrence_pattern": "daily",
            },
            headers=h_b,
        )

        params = {
            "start_date": start_time.isoformat(),
            "end_date": (start_time + timedelta(days=2)).isoformat(),
        }

        res_a = await client.get("/schedules/occurrences", params=params, headers=h_a)
        assert res_a.status_code == 200
        titles_a = [occ["title"] for occ in res_a.json()]
        assert "User A Recurring" in titles_a
        assert "User B Recurring" not in titles_a

        res_b = await client.get("/schedules/occurrences", params=params, headers=h_b)
        assert res_b.status_code == 200
        titles_b = [occ["title"] for occ in res_b.json()]
        assert "User B Recurring" in titles_b
        assert "User A Recurring" not in titles_b
