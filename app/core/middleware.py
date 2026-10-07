import logging
import time
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("taskora.middleware")


class ProcessTimeAndRequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "Unhandled server exception on %s %s: %s",
                request.method,
                request.url,
                exc,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        duration = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{duration:.6f}"
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ],
    )
    app.add_middleware(ProcessTimeAndRequestIdMiddleware)
