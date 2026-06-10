"""Add jobs.gpu_seconds (CB-5 — GPU-second metering).

Revision ID: 0004_job_gpu_seconds
Revises: 0003_job_target_id
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_job_gpu_seconds"
down_revision = "0003_job_target_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(
            sa.Column("gpu_seconds", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("gpu_seconds")
