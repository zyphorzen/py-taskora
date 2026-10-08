# Taskora Backend API (V1)

Taskora is a modern, high-performance backend API designed for task, schedule, calendar, and reminder management. Built with Python 3.14+, FastAPI, PostgreSQL (Supabase asyncpg), and SQLAlchemy 2.x async.

---

## Features

### 1. Authentication & Security
- User registration with unique username and email constraints.
- Argon2id password hashing for robust protection against brute-force attacks.
- JWT (JSON Web Tokens) access token authorization.
- Token decoding and user context validation (`get_current_user`).
- Strict user data isolation across all endpoints.
- OWASP security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`).
- CORS middleware with custom exposed headers.
- Request tracing with `X-Request-ID` and latency calculation with `X-Process-Time`.

### 2. Category Management
- Categorize tasks and schedules with custom names and hex colors.
- Case-insensitive name uniqueness per authenticated user.
- Cascade protection: deleting a category safely decouples associated tasks and schedules (`SET NULL`).

### 3. Task Management
- Full task lifecycle management: `todo`, `in_progress`, `completed`, `cancelled`.
- Priority levels: `low`, `medium`, `high`, `urgent`.
- Filter tasks by status, priority, category, and substring search (`q`).
- Dedicated status management endpoints: `/tasks/{id}/complete`, `/tasks/{id}/reopen`, `/tasks/{id}/status`, `/tasks/{id}/priority`.
- Bulk operations: `/tasks/bulk/status` and `/tasks/bulk/delete`.
- Task analytics: `/tasks/statistics` with completion rate and status/priority breakdown.

### 4. Schedule & Recurrence Engine
- Event scheduling with timezone-aware start and end timestamps, all-day flag, and location.
- Recurrence patterns: `daily`, `weekly`, `monthly`, and `yearly` with customizable recurrence interval and optional end date.
- Dynamic occurrence generator expanding recurring series within specified date windows.
- Recurrence management: `/schedules/{id}/stop-recurrence`.

### 5. Reminder System
- Time-based reminders linked to tasks, schedules, or standalone.
- Multiple notification types: `push`, `email`, `in_app`.
- Due reminder detection: `/reminders/due` for instant polling of unsent overdue alerts.
- Reminder delivery tracking: `/reminders/{id}/mark-sent`.
- Cascade deletion: deleting an associated task or schedule automatically cleans up related reminders.

### 6. Unified Calendar API
- Date range aggregation: `/calendar/events` combining schedules (including expanded recurring events), due tasks, and reminders.
- Single day view: `/calendar/day` for daily planning.
- Month activity summary: `/calendar/month-summary` providing per-day event counts for calendar heatmaps and dot badges.

### 7. Dashboard & Productivity Analytics
- Comprehensive dashboard: `/dashboard` aggregating task completion metrics, schedule counts, upcoming items, urgent priorities, and category distribution.
- Fast widget telemetry: `/dashboard/quick-stats` providing instant count summaries for mobile and web dashboards.

### 8. Global Error Handling
- Standardized error response format across all endpoints.
- Custom application exceptions: `NotFoundError` (404), `BadRequestError` (400), `UnauthorizedError` (401), `ForbiddenError` (403), `ConflictError` (409).
- Pydantic v2 validation handler with `422 Unprocessable Content`.
- Safe unhandled exception fallback returning `500 Internal Server Error` without leaking internal traces.

---

## Tech Stack

- **Runtime:** Python 3.14+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Database:** PostgreSQL (Supabase asyncpg)
- **ORM:** SQLAlchemy 2.x (Async Engine, AsyncSession, Mapped columns)
- **Migrations:** Alembic (Async migration runner)
- **Validation & Serialization:** Pydantic v2
- **Authentication:** PyJWT, Argon2-cffi
- **Testing:** Pytest, pytest-asyncio, HTTPX

---

## Project Structure

```text
py-taskora/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   ├── middleware.py
│   │   └── security.py
│   ├── db/
│   │   └── migrations/
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   ├── dependencies/
│   │   └── auth.py
│   ├── models/
│   │   ├── category.py
│   │   ├── reminder.py
│   │   ├── schedule.py
│   │   ├── task.py
│   │   └── user.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── calendar.py
│   │   ├── categories.py
│   │   ├── dashboard.py
│   │   ├── reminders.py
│   │   ├── schedules.py
│   │   └── tasks.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── calendar.py
│   │   ├── category.py
│   │   ├── dashboard.py
│   │   ├── reminder.py
│   │   ├── schedule.py
│   │   ├── task.py
│   │   └── user.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_calendar.py
│   ├── test_categories.py
│   ├── test_dashboard.py
│   ├── test_error_handling.py
│   ├── test_integration_workflow.py
│   ├── test_recurring_schedules.py
│   ├── test_reminders.py
│   ├── test_schedules.py
│   ├── test_security.py
│   ├── test_task_status_priority.py
│   └── test_tasks.py
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- Python 3.14 or higher
- PostgreSQL database instance

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
PROJECT_NAME=Taskora
APP_ENV=development
API_V1_STR=/api/v1
PORT=8000

POSTGRES_SERVER=aws-0-ap-northeast-1.pooler.supabase.com
POSTGRES_PORT=5432
POSTGRES_USER=postgres.your_project_id
POSTGRES_PASSWORD=your_database_password
POSTGRES_DB=postgres

SECRET_KEY=your-secure-random-secret-key-at-least-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 3. Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Database Migration
Apply all database migrations up to head:
```bash
alembic upgrade head
```

### 5. Running the Application
Start the ASGI server:
```bash
uvicorn app.main:app --reload --port 8000
```

---

## API Documentation

When the application is running, interactive API documentation is available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Testing

Run the full automated test suite:
```bash
pytest
```

Run test suite with verbose output:
```bash
pytest -v
```

---

## License

This project is licensed under the MIT License.
