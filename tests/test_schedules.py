import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestScheduleCRUD:
    async def test_create_schedule_success(self, client: AsyncClient, user_and_token):
        user, _, headers = user_and_token
        now = datetime.now(timezone.utc)
        payload = {
            "title": "Team Sprint Planning",
            "description": "Weekly planning meeting",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "is_all_day": False,
            "location": "Room 301",
            "status": "scheduled",
        }
        res = await client.post("/schedules", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == payload["title"]
        assert data["user_id"] == str(user.id)
        assert data["category_id"] is None
        assert data["location"] == "Room 301"
        assert uuid.UUID(data["id"])

    async def test_create_schedule_with_category(
        self, client: AsyncClient, auth_headers
    ):
        cat_res = await client.post(
            "/categories",
            json={"name": f"Work_{uuid.uuid4().hex[:6]}"},
            headers=auth_headers,
        )
        assert cat_res.status_code == 201
        cat_id = cat_res.json()["id"]

        now = datetime.now(timezone.utc)
        payload = {
            "title": "Product Demo",
            "category_id": cat_id,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
        }
        res = await client.post("/schedules", json=payload, headers=auth_headers)
        assert res.status_code == 201
        assert res.json()["category_id"] == cat_id

    async def test_create_schedule_with_foreign_category(
        self, client: AsyncClient, create_user
    ):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        cat_res = await client.post(
            "/categories",
            json={"name": f"A_Cat_{uuid.uuid4().hex[:6]}"},
            headers=h_a,
        )
        cat_id_a = cat_res.json()["id"]

        now = datetime.now(timezone.utc)
        payload = {
            "title": "Invader meeting",
            "category_id": cat_id_a,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }
        res = await client.post("/schedules", json=payload, headers=h_b)
        assert res.status_code == 400
        assert "Category not found or does not belong to user" in res.json()["detail"]

    async def test_create_schedule_invalid_time_range(
        self, client: AsyncClient, auth_headers
    ):
        now = datetime.now(timezone.utc)
        payload = {
            "title": "Backwards Time Meeting",
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(hours=1)).isoformat(),
        }
        res = await client.post("/schedules", json=payload, headers=auth_headers)
        assert res.status_code == 422

    async def test_create_schedule_validation_and_unauthorized(
        self, client: AsyncClient, auth_headers
    ):
        res_empty = await client.post(
            "/schedules", json={"title": ""}, headers=auth_headers
        )
        assert res_empty.status_code == 422

        res_no_auth = await client.post("/schedules", json={"title": "No Auth"})
        assert res_no_auth.status_code in (401, 403)

    async def test_list_schedules_and_user_isolation(
        self, client: AsyncClient, create_user
    ):
        user_1 = await create_user()
        user_2 = await create_user()

        h_1 = {"Authorization": f"Bearer {create_access_token(subject=str(user_1.id))}"}
        h_2 = {"Authorization": f"Bearer {create_access_token(subject=str(user_2.id))}"}

        now = datetime.now(timezone.utc)
        suffix = uuid.uuid4().hex[:6]
        await client.post(
            "/schedules",
            json={
                "title": f"S1_U1_{suffix}",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_1,
        )
        await client.post(
            "/schedules",
            json={
                "title": f"S1_U2_{suffix}",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_2,
        )

        res_1 = await client.get("/schedules", headers=h_1)
        assert res_1.status_code == 200
        titles_1 = [s["title"] for s in res_1.json()]
        assert f"S1_U1_{suffix}" in titles_1
        assert f"S1_U2_{suffix}" not in titles_1

        res_2 = await client.get("/schedules", headers=h_2)
        assert res_2.status_code == 200
        titles_2 = [s["title"] for s in res_2.json()]
        assert f"S1_U2_{suffix}" in titles_2
        assert f"S1_U1_{suffix}" not in titles_2

    async def test_list_schedules_filters(self, client: AsyncClient, auth_headers):
        now = datetime.now(timezone.utc)
        key = uuid.uuid4().hex[:6]
        await client.post(
            "/schedules",
            json={
                "title": f"Dentist {key}",
                "location": "Downtown Clinic",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "end_time": (now + timedelta(days=1, hours=1)).isoformat(),
            },
            headers=auth_headers,
        )
        await client.post(
            "/schedules",
            json={
                "title": f"Flight {key}",
                "location": "Airport",
                "start_time": (now + timedelta(days=10)).isoformat(),
                "end_time": (now + timedelta(days=10, hours=4)).isoformat(),
            },
            headers=auth_headers,
        )

        res_q = await client.get(f"/schedules?q=clinic", headers=auth_headers)
        assert res_q.status_code == 200
        assert len(res_q.json()) == 1
        assert f"Dentist {key}" in res_q.json()[0]["title"]

        filter_start = (now + timedelta(days=5)).isoformat()
        res_date = await client.get(
            "/schedules", params={"start_date": filter_start}, headers=auth_headers
        )
        assert res_date.status_code == 200
        titles = [s["title"] for s in res_date.json()]
        assert f"Flight {key}" in titles

        assert f"Dentist {key}" not in titles

    async def test_get_schedule_by_id(self, client: AsyncClient, create_user):
        owner = await create_user()
        other = await create_user()

        h_owner = {
            "Authorization": f"Bearer {create_access_token(subject=str(owner.id))}"
        }
        h_other = {
            "Authorization": f"Bearer {create_access_token(subject=str(other.id))}"
        }

        now = datetime.now(timezone.utc)
        res = await client.post(
            "/schedules",
            json={
                "title": "Private Consultation",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_owner,
        )
        sch_id = res.json()["id"]

        get_ok = await client.get(f"/schedules/{sch_id}", headers=h_owner)
        assert get_ok.status_code == 200
        assert get_ok.json()["id"] == sch_id

        get_other = await client.get(f"/schedules/{sch_id}", headers=h_other)
        assert get_other.status_code == 404

        get_nonexistent = await client.get(
            f"/schedules/{uuid.uuid4()}", headers=h_owner
        )
        assert get_nonexistent.status_code == 404

    async def test_update_schedule_patch_and_put(
        self, client: AsyncClient, auth_headers
    ):
        now = datetime.now(timezone.utc)
        create_res = await client.post(
            "/schedules",
            json={
                "title": "Initial Meeting",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
                "location": "Old Office",
            },
            headers=auth_headers,
        )
        sch_id = create_res.json()["id"]

        patch_res = await client.patch(
            f"/schedules/{sch_id}",
            json={"location": "New Office", "is_all_day": True},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["location"] == "New Office"
        assert patch_res.json()["is_all_day"] is True

        patch_invalid_time = await client.patch(
            f"/schedules/{sch_id}",
            json={"end_time": (now - timedelta(hours=5)).isoformat()},
            headers=auth_headers,
        )
        assert patch_invalid_time.status_code == 422

        new_start = now + timedelta(days=1)
        new_end = new_start + timedelta(hours=3)
        put_res = await client.put(
            f"/schedules/{sch_id}",
            json={
                "title": "Updated Meeting Title",
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
                "location": "Conference Room",
            },
            headers=auth_headers,
        )
        assert put_res.status_code == 200
        assert put_res.json()["title"] == "Updated Meeting Title"
        assert put_res.json()["location"] == "Conference Room"

    async def test_delete_schedule(self, client: AsyncClient, create_user):
        owner = await create_user()
        other = await create_user()

        h_owner = {
            "Authorization": f"Bearer {create_access_token(subject=str(owner.id))}"
        }
        h_other = {
            "Authorization": f"Bearer {create_access_token(subject=str(other.id))}"
        }

        now = datetime.now(timezone.utc)
        sch_res = await client.post(
            "/schedules",
            json={
                "title": "Schedule to delete",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
            headers=h_owner,
        )
        sch_id = sch_res.json()["id"]

        del_other = await client.delete(f"/schedules/{sch_id}", headers=h_other)
        assert del_other.status_code == 404

        del_ok = await client.delete(f"/schedules/{sch_id}", headers=h_owner)
        assert del_ok.status_code == 204

        get_gone = await client.get(f"/schedules/{sch_id}", headers=h_owner)
        assert get_gone.status_code == 404
