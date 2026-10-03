from fastapi import FastAPI

app = FastAPI(
    title="Taskora API",
    version="1.0.0",
    description="Backend API for Taskora V1 - Schedule, Task, Calendar, and Reminder Management",
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "Taskora API"}
