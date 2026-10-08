from fastapi import FastAPI
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middleware
from app.routers.auth import router as auth_router
from app.routers.calendar import router as calendar_router
from app.routers.categories import router as categories_router
from app.routers.dashboard import router as dashboard_router
from app.routers.reminders import router as reminders_router
from app.routers.schedules import router as schedules_router
from app.routers.tasks import router as tasks_router

openapi_tags = [
    {
        "name": "Health",
        "description": "System health check and service status monitoring.",
    },
    {
        "name": "Auth",
        "description": "User authentication, registration, login, and user profile management.",
    },
    {
        "name": "Categories",
        "description": "Category CRUD operations for organizing tasks and schedules.",
    },
    {
        "name": "Tasks",
        "description": "Task lifecycle, priority, bulk operations, and task statistics.",
    },
    {
        "name": "Schedules",
        "description": "Event schedules, recurring schedule rules, and occurrence generation.",
    },
    {
        "name": "Reminders",
        "description": "Scheduled reminders with notification tracking and due alerts.",
    },
    {
        "name": "Calendar",
        "description": "Multi-entity calendar aggregation for day, range, and month views.",
    },
    {
        "name": "Dashboard",
        "description": "Aggregated user productivity metrics and quick stats.",
    },
]

app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    version="1.0.0",
    description="Comprehensive backend API for Taskora V1: Schedule, Task, Calendar, and Reminder Management.",
    openapi_tags=openapi_tags,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Taskora Team",
        "email": "support@taskora.app",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

setup_middleware(app)
setup_exception_handlers(app)

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(tasks_router)
app.include_router(schedules_router)
app.include_router(reminders_router)
app.include_router(calendar_router)
app.include_router(dashboard_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.PROJECT_NAME}
