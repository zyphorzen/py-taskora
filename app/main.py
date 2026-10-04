from fastapi import FastAPI
from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.schedules import router as schedules_router
from app.routers.tasks import router as tasks_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API for Taskora V1 - Schedule, Task, Calendar, and Reminder Management",
)

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(tasks_router)
app.include_router(schedules_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.PROJECT_NAME}
