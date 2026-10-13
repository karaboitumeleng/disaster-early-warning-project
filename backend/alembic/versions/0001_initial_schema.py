"""Initial schema: users, readings, alerts, audit_log.

Uses plain columns everywhere so this runs unmodified on SQLite (the prototype default).
On PostgreSQL, run 0002 afterwards to add PostGIS geometry columns and spatial indexes.
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "readings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("payload_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("region_id", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_readings_region_id", "readings", ["region_id"])
    op.create_index("ix_readings_observed_at", "readings", ["observed_at"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("reading_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("region_id", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("disaster_type", sa.String(32), nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("degraded", sa.Boolean, nullable=False),
        sa.Column("novel", sa.Boolean, nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("explanation", sa.JSON, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("handled_by", sa.String(64), nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_region_id", "alerts", ["region_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("detail", sa.JSON, nullable=False),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("alerts")
    op.drop_table("readings")
    op.drop_table("users")
