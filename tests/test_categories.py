import uuid
import pytest
from httpx2 import AsyncClient

from app.core.security import create_access_token
from app.models.user import User


class TestCategoryCRUD:
    """Comprehensive test suite for Category CRUD API with user isolation."""

    async def test_create_category_success(self, client: AsyncClient, user_and_token):
        user, _, headers = user_and_token
        payload = {
            "name": f"Work_{uuid.uuid4().hex[:6]}",
            "color": "#3B82F6",
            "icon": "briefcase",
        }
        response = await client.post("/categories", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["color"] == payload["color"]
        assert data["icon"] == payload["icon"]
        assert data["user_id"] == str(user.id)
        assert uuid.UUID(data["id"])

    async def test_create_category_duplicate_name_same_user(
        self, client: AsyncClient, auth_headers
    ):
        cat_name = f"DuplicateCat_{uuid.uuid4().hex[:6]}"
        payload = {"name": cat_name, "color": "#FF0000"}

        res1 = await client.post("/categories", json=payload, headers=auth_headers)
        assert res1.status_code == 201

        res2 = await client.post("/categories", json=payload, headers=auth_headers)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"]

    async def test_create_category_same_name_different_users(
        self, client: AsyncClient, create_user
    ):
        user1 = await create_user()
        user2 = await create_user()

        token1 = create_access_token(subject=str(user1.id))
        token2 = create_access_token(subject=str(user2.id))

        shared_name = f"SharedName_{uuid.uuid4().hex[:6]}"
        payload = {"name": shared_name}

        res1 = await client.post(
            "/categories",
            json=payload,
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res1.status_code == 201

        res2 = await client.post(
            "/categories",
            json=payload,
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert res2.status_code == 201

    async def test_create_category_validation_and_unauthorized(
        self, client: AsyncClient, auth_headers
    ):
        res_empty = await client.post(
            "/categories", json={"name": ""}, headers=auth_headers
        )
        assert res_empty.status_code == 422

        res_no_auth = await client.post("/categories", json={"name": "Valid"})
        assert res_no_auth.status_code in (401, 403)

    async def test_list_categories_and_user_isolation(
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

        suffix = uuid.uuid4().hex[:6]
        await client.post(
            "/categories", json={"name": f"A_Cat1_{suffix}"}, headers=headers_a
        )
        await client.post(
            "/categories", json={"name": f"A_Cat2_{suffix}"}, headers=headers_a
        )
        await client.post(
            "/categories", json={"name": f"B_Cat1_{suffix}"}, headers=headers_b
        )

        list_a = await client.get("/categories", headers=headers_a)
        assert list_a.status_code == 200
        items_a = list_a.json()
        names_a = [item["name"] for item in items_a]
        assert f"A_Cat1_{suffix}" in names_a
        assert f"A_Cat2_{suffix}" in names_a
        assert f"B_Cat1_{suffix}" not in names_a

        list_b = await client.get("/categories", headers=headers_b)
        assert list_b.status_code == 200
        items_b = list_b.json()
        names_b = [item["name"] for item in items_b]
        assert f"B_Cat1_{suffix}" in names_b
        assert f"A_Cat1_{suffix}" not in names_b

    async def test_list_categories_search_filter(
        self, client: AsyncClient, auth_headers
    ):
        unique = uuid.uuid4().hex[:6]
        await client.post(
            "/categories", json={"name": f"Urgent_{unique}"}, headers=auth_headers
        )
        await client.post(
            "/categories", json={"name": f"Routine_{unique}"}, headers=auth_headers
        )

        res = await client.get(f"/categories?q=urgent_{unique}", headers=auth_headers)
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["name"] == f"Urgent_{unique}"

    async def test_get_category_by_id(self, client: AsyncClient, create_user):
        user_owner = await create_user()
        user_stranger = await create_user()

        headers_owner = {
            "Authorization": f"Bearer {create_access_token(subject=str(user_owner.id))}"
        }
        headers_stranger = {
            "Authorization": f"Bearer {create_access_token(subject=str(user_stranger.id))}"
        }

        create_res = await client.post(
            "/categories",
            json={"name": f"Secret_{uuid.uuid4().hex[:6]}"},
            headers=headers_owner,
        )
        cat_id = create_res.json()["id"]

        get_res = await client.get(f"/categories/{cat_id}", headers=headers_owner)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == cat_id

        stranger_res = await client.get(
            f"/categories/{cat_id}", headers=headers_stranger
        )
        assert stranger_res.status_code == 404

        nonexistent_res = await client.get(
            f"/categories/{uuid.uuid4()}", headers=headers_owner
        )
        assert nonexistent_res.status_code == 404

    async def test_update_category_patch_and_put(
        self, client: AsyncClient, create_user
    ):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        initial_name = f"Init_{uuid.uuid4().hex[:6]}"
        create_res = await client.post(
            "/categories",
            json={"name": initial_name, "color": "#000000"},
            headers=headers,
        )
        cat_id = create_res.json()["id"]

        patch_res = await client.patch(
            f"/categories/{cat_id}",
            json={"color": "#FFFFFF", "icon": "star"},
            headers=headers,
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["name"] == initial_name
        assert patch_data["color"] == "#FFFFFF"
        assert patch_data["icon"] == "star"

        new_name = f"Updated_{uuid.uuid4().hex[:6]}"
        put_res = await client.put(
            f"/categories/{cat_id}",
            json={"name": new_name, "color": "#123456", "icon": "heart"},
            headers=headers,
        )
        assert put_res.status_code == 200
        put_data = put_res.json()
        assert put_data["name"] == new_name
        assert put_data["color"] == "#123456"

    async def test_update_category_conflict_and_isolation(
        self, client: AsyncClient, create_user
    ):
        user = await create_user()
        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }

        c1 = await client.post(
            "/categories", json={"name": f"C1_{uuid.uuid4().hex[:6]}"}, headers=headers
        )
        c2 = await client.post(
            "/categories", json={"name": f"C2_{uuid.uuid4().hex[:6]}"}, headers=headers
        )
        c1_name = c1.json()["name"]
        c2_id = c2.json()["id"]

        conflict_res = await client.patch(
            f"/categories/{c2_id}",
            json={"name": c1_name},
            headers=headers,
        )
        assert conflict_res.status_code == 409
        assert "already exists" in conflict_res.json()["detail"]

    async def test_delete_category(self, client: AsyncClient, create_user):
        user = await create_user()
        stranger = await create_user()

        headers = {
            "Authorization": f"Bearer {create_access_token(subject=str(user.id))}"
        }
        headers_stranger = {
            "Authorization": f"Bearer {create_access_token(subject=str(stranger.id))}"
        }

        create_res = await client.post(
            "/categories",
            json={"name": f"ToDelete_{uuid.uuid4().hex[:6]}"},
            headers=headers,
        )
        cat_id = create_res.json()["id"]

        stranger_del = await client.delete(
            f"/categories/{cat_id}", headers=headers_stranger
        )
        assert stranger_del.status_code == 404

        del_res = await client.delete(f"/categories/{cat_id}", headers=headers)
        assert del_res.status_code == 204

        get_res = await client.get(f"/categories/{cat_id}", headers=headers)
        assert get_res.status_code == 404
