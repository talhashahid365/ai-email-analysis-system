"""Guards against model/migration drift: `alembic upgrade head` must produce every table and column the models define."""
import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_alembic_head_matches_models(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'mig.db'}"
    sys.path.insert(0, BACKEND)
    from app.config import settings
    monkeypatch.setattr(settings, "DATABASE_URL", db_url)
    from app.database import Base
    from app import models  # noqa: F401  (registers tables)

    cfg = Config(os.path.join(BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND, "alembic"))
    command.upgrade(cfg, "head")

    insp = inspect(create_engine(db_url))
    problems = []
    for name, table in Base.metadata.tables.items():
        if not insp.has_table(name):
            problems.append(f"missing table {name}")
            continue
        have = {c["name"] for c in insp.get_columns(name)}
        for col in table.columns:
            if col.name not in have:
                problems.append(f"{name}.{col.name} missing from migrations")
    assert not problems, problems
