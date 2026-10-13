"""Runs Alembic upgrade/downgrade against a throwaway SQLite file. Confirms 0001 is
reversible; confirms 0002 fails loudly (by design) on SQLite instead of silently no-oping."""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


def _cfg(db_path: Path) -> Config:
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")
    return cfg


def test_0001_upgrade_and_downgrade(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path / "mig.db")
    command.upgrade(cfg, "0001")
    command.downgrade(cfg, "base")


def test_0002_refuses_on_sqlite(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path / "mig2.db")
    command.upgrade(cfg, "0001")
    with pytest.raises(Exception, match="PostGIS"):
        command.upgrade(cfg, "0002")
