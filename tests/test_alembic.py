import os
from pathlib import Path
from alembic.config import Config
from app.core.config import settings


def test_alembic_config_load():
    alembic_cfg = Config("alembic.ini")
    script_location = alembic_cfg.get_main_option("script_location")
    assert script_location.endswith("app/db/migrations")


def test_alembic_files_exist():
    assert Path("alembic.ini").exists()
    assert Path("app/db/migrations/env.py").exists()
    assert Path("app/db/migrations/script.py.mako").exists()
    env_content = Path("app/db/migrations/env.py").read_text()
    assert "target_metadata = Base.metadata" in env_content
    assert "settings.SQLALCHEMY_DATABASE_URI" in env_content
