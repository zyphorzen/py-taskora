import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token


class TestTaskStatusAndPriority:
    async def test_update_status_endpoint(self, client: AsyncClient, auth_headers):
        create_res = await client.post(
            "/tasks",
            json={"title": "Test status endpoint", "status": "todo"},
            headers=auth_headers,
        )
        task_id = create_res.json()["id"]

        patch_res = await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "in_progress"
        assert patch_res.json()["completed_at"] is None

        complete_res = await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert complete_res.status_code == 200
        assert complete_res.json()["status"] == "completed"
        assert complete_res.json()["completed_at"] is not None

        todo_res = await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": "todo"},
            headers=auth_headers,
        )
        assert todo_res.status_code == 200
        assert todo_res.json()["status"] == "todo"
        assert todo_res.json()["completed_at"] is None

    async def test_update_priority_endpoint(self, client: AsyncClient, auth_headers):
        create_res = await client.post(
            "/tasks",
            json={"title": "Test priority endpoint", "priority": "low"},
            headers=auth_headers,
        )
        task_id = create_res.json()["id"]

        patch_res = await client.patch(
            f"/tasks/{task_id}/priority",
            json={"priority": "urgent"},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["priority"] == "urgent"

    async def test_complete_and_reopen_shortcuts(
        self, client: AsyncClient, auth_headers
    ):
        create_res = await client.post(
            "/tasks",
            json={"title": "Shortcut task", "status": "todo"},
            headers=auth_headers,
        )
        task_id = create_res.json()["id"]

        comp_res = await client.post(
            f"/tasks/{task_id}/complete",
            headers=auth_headers,
        )
        assert comp_res.status_code == 200
        assert comp_res.json()["status"] == "completed"
        assert comp_res.json()["completed_at"] is not None

        reopen_res = await client.post(
            f"/tasks/{task_id}/reopen",
            headers=auth_headers,
        )
        assert reopen_res.status_code == 200
        assert reopen_res.json()["status"] == "todo"
        assert reopen_res.json()["completed_at"] is None

    async def test_bulk_status_update(self, client: AsyncClient, create_user):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        t1_a = (
            await client.post("/tasks", json={"title": "Task 1 A"}, headers=h_a)
        ).json()["id"]
        t2_a = (
            await client.post("/tasks", json={"title": "Task 2 A"}, headers=h_a)
        ).json()["id"]
        t1_b = (
            await client.post("/tasks", json={"title": "Task 1 B"}, headers=h_b)
        ).json()["id"]

        bulk_res = await client.post(
            "/tasks/bulk/status",
            json={
                "task_ids": [t1_a, t2_a, t1_b],
                "status": "completed",
            },
            headers=h_a,
        )
        assert bulk_res.status_code == 200
        bulk_data = bulk_res.json()
        assert bulk_data["affected_count"] == 2
        assert t1_a in bulk_data["task_ids"]
        assert t2_a in bulk_data["task_ids"]
        assert t1_b not in bulk_data["task_ids"]

        check_b = await client.get(f"/tasks/{t1_b}", headers=h_b)
        assert check_b.json()["status"] == "todo"

    async def test_bulk_delete(self, client: AsyncClient, create_user):
        user_a = await create_user()
        user_b = await create_user()

        h_a = {"Authorization": f"Bearer {create_access_token(subject=str(user_a.id))}"}
        h_b = {"Authorization": f"Bearer {create_access_token(subject=str(user_b.id))}"}

        t1 = (
            await client.post("/tasks", json={"title": "Delete 1"}, headers=h_a)
        ).json()["id"]
        t2 = (
            await client.post("/tasks", json={"title": "Delete 2"}, headers=h_a)
        ).json()["id"]
        t_other = (
            await client.post("/tasks", json={"title": "Keep me"}, headers=h_b)
        ).json()["id"]

        del_res = await client.post(
            "/tasks/bulk/delete",
            json={"task_ids": [t1, t2, t_other]},
            headers=h_a,
        )
        assert del_res.status_code == 200
        assert del_res.json()["affected_count"] == 2

        get_t1 = await client.get(f"/tasks/{t1}", headers=h_a)
        assert get_t1.status_code == 404

        get_other = await client.get(f"/tasks/{t_other}", headers=h_b)
        assert get_other.status_code == 200

    async def test_task_statistics(self, client: AsyncClient, create_user):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        future_due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

        await client.post(
            "/tasks",
            json={
                "title": "Overdue task",
                "status": "todo",
                "priority": "urgent",
                "due_date": past_due,
            },
            headers=headers,
        )
        await client.post(
            "/tasks",
            json={
                "title": "Future in progress",
                "status": "in_progress",
                "priority": "high",
                "due_date": future_due,
            },
            headers=headers,
        )
        await client.post(
            "/tasks",
            json={
                "title": "Finished past",
                "status": "completed",
                "priority": "medium",
                "due_date": past_due,
            },
            headers=headers,
        )

        stats_res = await client.get("/tasks/statistics", headers=headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()

        assert stats["total"] == 3
        assert stats["completed_count"] == 1
        assert stats["pending_count"] == 2
        assert stats["overdue_count"] == 1
        assert stats["by_status"]["todo"] == 1
        assert stats["by_status"]["in_progress"] == 1
        assert stats["by_status"]["completed"] == 1
        assert stats["by_priority"]["urgent"] == 1
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["medium"] == 1
