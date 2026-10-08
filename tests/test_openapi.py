import pytest
from httpx2 import AsyncClient


class TestDocumentationAndOpenAPI:
    async def test_openapi_json_endpoint(self, client: AsyncClient):
        res = await client.get("/openapi.json")
        assert res.status_code == 200
        data = res.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Taskora API"
        assert data["info"]["version"] == "1.0.0"
        assert "paths" in data

        tag_names = [t["name"] for t in data.get("tags", [])]
        assert "Health" in tag_names
        assert "Auth" in tag_names
        assert "Categories" in tag_names
        assert "Tasks" in tag_names
        assert "Schedules" in tag_names
        assert "Reminders" in tag_names
        assert "Calendar" in tag_names
        assert "Dashboard" in tag_names

    async def test_swagger_docs_endpoint(self, client: AsyncClient):
        res = await client.get("/docs")
        assert res.status_code == 200
        assert "html" in res.headers.get("content-type", "").lower()

    async def test_redoc_endpoint(self, client: AsyncClient):
        res = await client.get("/redoc")
        assert res.status_code == 200
        assert "html" in res.headers.get("content-type", "").lower()
