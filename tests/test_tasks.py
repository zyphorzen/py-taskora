import uuid
from datetime import datetime, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestTaskCRUD:
    """Comprehensive test suite for Task CRUD API with user isolation and category validation."""

    async def test_create_task_minimal(self, client: AsyncClient, user_and_token):
        user, _, headers = user_and_token
        payload = {"title": "Buy groceries"}
        response = await client.post("/tasks", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy groceries"
        assert data["user_id"] == str(user.id)
        assert data["status"] == "todo"
        assert data["priority"] == "medium"
        assert data["category_id"] is None
        assert data["completed_at"] is None
        assert uuid.UUID(data["id"])

    async def test_create_task_with_category(self, client: AsyncClient, auth_headers):
        cat_res = await client.post(
            "/categories",
            json={"name": f"Home_{uuid.uuid4().hex[:6]}"},
            headers=auth_headers,
        )
        assert cat_res.status_code == 201
        cat_id = cat_res.json()["id"]

        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "title": "Clean kitchen",
            "description": "Clean counters and sink",
            "category_id": cat_id,
            "status": "in_progress",
            "priority": "high",
            "due_date": now_iso,
        }
        task_res = await client.post("/tasks", json=payload, headers=auth_headers)
        assert task_res.status_code == 201
        data = task_res.json()
        assert data["title"] == payload["title"]
        assert data["category_id"] == cat_id
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"

    async def test_create_task_with_foreign_category(
        self, client: AsyncClient, create_user
    ):
        user_a = await create_user()
        user_b = await create_user()

        headers_a = {
            "Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"
        }
        headers_b = {
            "Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"
        }

        cat_res = await client.post(
            "/categories",
            json={"name": f"A_Cat_{uuid.uuid4().hex[:6]}"},
            headers=headers_a,
        )
        cat_id_a = cat_res.json()["id"]

        payload = {"title": "Intruder task", "category_id": cat_id_a}
        res = await client.post("/tasks", json=payload, headers=headers_b)
        assert res.status_code == 400
        assert "Category not found or does not belong to user" in res.json()["detail"]

    async def test_create_task_validation(self, client: AsyncClient, auth_headers):
        res_empty = await client.post(
            "/tasks", json={"title": ""}, headers=auth_headers
        )
        assert res_empty.status_code == 422

        res_invalid_status = await client.post(
            "/tasks",
            json={"title": "Test", "status": "unknown_status"},
            headers=auth_headers,
        )
        assert res_invalid_status.status_code == 422

        res_no_auth = await client.post("/tasks", json={"title": "No Auth"})
        assert res_no_auth.status_code in (401, 403)

    async def test_list_tasks_and_user_isolation(
        self, client: AsyncClient, create_user
    ):
        user_1 = await create_user()
        user_2 = await create_user()

        headers_1 = {
            "Authorization": f"Bearer {create_access_token(subject=str(user_1.id))}"
        }
        headers_2 = {
            "Authorization": f"Bearer {create_access_token(subject=str(user_2.id))}"
        }

        suffix = uuid.uuid4().hex[:6]
        await client.post(
            "/tasks", json={"title": f"T1_User1_{suffix}"}, headers=headers_1
        )
        await client.post(
            "/tasks", json={"title": f"T2_User1_{suffix}"}, headers=headers_1
        )
        await client.post(
            "/tasks", json={"title": f"T1_User2_{suffix}"}, headers=headers_2
        )

        res_1 = await client.get("/tasks", headers=headers_1)
        assert res_1.status_code == 200
        titles_1 = [t["title"] for t in res_1.json()]
        assert f"T1_User1_{suffix}" in titles_1
        assert f"T2_User1_{suffix}" in titles_1
        assert f"T1_User2_{suffix}" not in titles_1

        res_2 = await client.get("/tasks", headers=headers_2)
        assert res_2.status_code == 200
        titles_2 = [t["title"] for t in res_2.json()]
        assert f"T1_User2_{suffix}" in titles_2
        assert f"T1_User1_{suffix}" not in titles_2

    async def test_list_tasks_filters_and_search(
        self, client: AsyncClient, auth_headers
    ):
        key = uuid.uuid4().hex[:6]
        await client.post(
            "/tasks",
            json={"title": f"Report alpha {key}", "status": "todo", "priority": "low"},
            headers=auth_headers,
        )
        await client.post(
            "/tasks",
            json={
                "title": f"Report beta {key}",
                "status": "completed",
                "priority": "urgent",
            },
            headers=auth_headers,
        )

        res_search = await client.get(f"/tasks?q=alpha {key}", headers=auth_headers)
        assert res_search.status_code == 200
        assert len(res_search.json()) == 1
        assert f"Report alpha {key}" == res_search.json()[0]["title"]

        res_status = await client.get("/tasks?status=completed", headers=auth_headers)
        assert res_status.status_code == 200
        for task in res_status.json():
            assert task["status"] == "completed"

        res_priority = await client.get("/tasks?priority=urgent", headers=auth_headers)
        assert res_priority.status_code == 200
        for task in res_priority.json():
            assert task["priority"] == "urgent"

    async def test_get_task_by_id(self, client: AsyncClient, create_user):
        owner = await create_user()
        other = await create_user()

        h_owner = {
            "Authorization": f"Bearer {create_access_token(subject=str(owner.id))}"
        }
        h_other = {
            "Authorization": f"Bearer {create_access_token(subject=str(other.id))}"
        }

        res = await client.post(
            "/tasks", json={"title": "Private task"}, headers=h_owner
        )
        task_id = res.json()["id"]

        get_ok = await client.get(f"/tasks/{task_id}", headers=h_owner)
        assert get_ok.status_code == 200
        assert get_ok.json()["id"] == task_id

        get_forbidden = await client.get(f"/tasks/{task_id}", headers=h_other)
        assert get_forbidden.status_code == 404

        get_nonexistent = await client.get(f"/tasks/{uuid.uuid4()}", headers=h_owner)
        assert get_nonexistent.status_code == 404

    async def test_update_task_status_auto_completed_at(
        self, client: AsyncClient, auth_headers
    ):
        create_res = await client.post(
            "/tasks",
            json={"title": "Complete me", "status": "todo"},
            headers=auth_headers,
        )
        task_id = create_res.json()["id"]
        assert create_res.json()["completed_at"] is None

        patch_completed = await client.patch(
            f"/tasks/{task_id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert patch_completed.status_code == 200
        assert patch_completed.json()["completed_at"] is not None

        patch_reopen = await client.patch(
            f"/tasks/{task_id}",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert patch_reopen.status_code == 200
        assert patch_reopen.json()["completed_at"] is None

    async def test_delete_task(self, client: AsyncClient, create_user):
        owner = await create_user()
        stranger = await create_user()

        h_owner = {
            "Authorization": f"Bearer {create_access_token(subject=str(owner.id))}"
        }
        h_stranger = {
            "Authorization": f"Bearer {create_access_token(subject=str(stranger.id))}"
        }

        task_res = await client.post(
            "/tasks", json={"title": "Task to delete"}, headers=h_owner
        )
        task_id = task_res.json()["id"]

        del_foreign = await client.delete(f"/tasks/{task_id}", headers=h_stranger)
        assert del_foreign.status_code == 404

        del_ok = await client.delete(f"/tasks/{task_id}", headers=h_owner)
        assert del_ok.status_code == 204

        get_del = await client.get(f"/tasks/{task_id}", headers=h_owner)
        assert get_del.status_code == 404
