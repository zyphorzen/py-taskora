from fastapi import FastAPI
from app.core.config import settings
from app.routers.auth import router as auth_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API for Taskora V1 - Schedule, Task, Calendar, and Reminder Management",
)

app.include_router(auth_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.PROJECT_NAME}
