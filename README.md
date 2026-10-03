# Taskora Backend (V1)

Taskora is a schedule, task, calendar, and reminder management backend built with Python and FastAPI.

## Tech Stack
- Python 3.14+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x (Async)
- Alembic
- Pydantic v2
- JWT Authentication & Argon2 Password Hashing
- pytest

## Getting Started

### 1. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload
```
