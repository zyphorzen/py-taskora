from app.core.config import Settings, settings


def test_settings_load():
    assert settings.PROJECT_NAME == "Taskora"
    assert settings.API_V1_STR == "/api/v1"
    assert "postgresql+asyncpg://" in settings.SQLALCHEMY_DATABASE_URI
    assert settings.ALGORITHM == "HS256"


def test_custom_settings_database_uri():
    custom = Settings(
        POSTGRES_SERVER="db.example.com",
        POSTGRES_PORT=5433,
        POSTGRES_USER="myuser",
        POSTGRES_PASSWORD="mypassword",
        POSTGRES_DB="mydb",
    )
    expected_uri = "postgresql+asyncpg://myuser:mypassword@db.example.com:5433/mydb"
    assert custom.SQLALCHEMY_DATABASE_URI == expected_uri
