import uuid
import pytest
from httpx2 import AsyncClient

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.main import app


@app.get("/_test/custom-not-found")
async def _endpoint_not_found():
    raise NotFoundError("Test resource was not found")


@app.get("/_test/custom-conflict")
async def _endpoint_conflict():
    raise ConflictError("Test resource conflict detected")


@app.get("/_test/custom-forbidden")
async def _endpoint_forbidden():
    raise ForbiddenError("Test forbidden action")


@app.get("/_test/custom-unauthorized")
async def _endpoint_unauthorized():
    raise UnauthorizedError("Test unauthorized action")


@app.get("/_test/custom-bad-request")
async def _endpoint_bad_request():
    raise BadRequestError("Test bad request message")


@app.get("/_test/unhandled-server-error")
async def _endpoint_server_error():
    raise RuntimeError("Simulated unexpected crash")


class TestErrorHandlingAndMiddleware:
    async def test_middleware_request_id_and_process_time(self, client: AsyncClient):
        res = await client.get("/health")
        assert res.status_code == 200
        assert "x-request-id" in res.headers
        assert "x-process-time" in res.headers
        assert float(res.headers["x-process-time"]) >= 0.0

    async def test_middleware_custom_request_id_preserved(self, client: AsyncClient):
        custom_id = "custom-req-id-98765"
        res = await client.get("/health", headers={"X-Request-ID": custom_id})
        assert res.status_code == 200
        assert res.headers["x-request-id"] == custom_id

    async def test_cors_headers(self, client: AsyncClient):
        origin = "http://localhost:5173"
        res = await client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin

    async def test_standard_404_not_found(self, client: AsyncClient):
        res = await client.get("/completely-unknown-route-endpoint")
        assert res.status_code == 404
        data = res.json()
        assert "detail" in data
        assert data["detail"] == "Not Found"

    async def test_validation_error_422(self, client: AsyncClient, auth_headers):
        res = await client.post("/categories", json={}, headers=auth_headers)
        assert res.status_code == 422
        data = res.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    async def test_custom_taskora_exceptions(self, client: AsyncClient):
        res_nf = await client.get("/_test/custom-not-found")
        assert res_nf.status_code == 404
        assert res_nf.json()["detail"] == "Test resource was not found"

        res_cf = await client.get("/_test/custom-conflict")
        assert res_cf.status_code == 409
        assert res_cf.json()["detail"] == "Test resource conflict detected"

        res_fb = await client.get("/_test/custom-forbidden")
        assert res_fb.status_code == 403
        assert res_fb.json()["detail"] == "Test forbidden action"

        res_un = await client.get("/_test/custom-unauthorized")
        assert res_un.status_code == 401
        assert res_un.json()["detail"] == "Test unauthorized action"

        res_br = await client.get("/_test/custom-bad-request")
        assert res_br.status_code == 400
        assert res_br.json()["detail"] == "Test bad request message"

    async def test_unhandled_exception_returns_500(self, client: AsyncClient):
        res = await client.get("/_test/unhandled-server-error")
        assert res.status_code == 500
        assert res.json() == {"detail": "Internal server error"}
