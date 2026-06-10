"""Add jobs.target_id (CB-3 — async keyframe/character-ref generation).

Revision ID: 0003_job_target_id
Revises: 0002_owner_id_not_null
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_job_target_id"
down_revision = "0002_owner_id_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("target_id", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("target_id")
