"""PostGIS region boundaries + spatial index. PostgreSQL/PostGIS only - this migration
is a no-op (raises a clear error) on SQLite, since Spatialite setup differs by platform
and is out of scope for the prototype's default local run.

Run only when DATABASE_URL points at Postgres with the postgis extension available:
  alembic upgrade head
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError(
            "0002_postgis_regions requires PostgreSQL + PostGIS. "
            "Skip this migration on SQLite (stay on revision 0001)."
        )
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "regions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("province", sa.String(64), nullable=False),
        sa.Column("boundary", sa.Text, nullable=True),  # WKT until geoalchemy2 is added
        sa.Column("centroid_lat", sa.Float, nullable=False),
        sa.Column("centroid_lon", sa.Float, nullable=False),
    )
    op.execute(
        "ALTER TABLE regions ADD COLUMN geom geometry(MultiPolygon, 4326)"
    )
    op.execute("CREATE INDEX ix_regions_geom ON regions USING GIST (geom)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("0002_postgis_regions requires PostgreSQL + PostGIS.")
    op.drop_table("regions")
