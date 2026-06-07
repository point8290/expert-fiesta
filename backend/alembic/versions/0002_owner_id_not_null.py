"""Tighten projects.owner_id to NOT NULL (PR0-4 AC3).

Backfill any orphaned rows before deploying to an environment with existing data;
on a fresh database there is nothing to backfill.

Revision ID: 0002_owner_id_not_null
Revises: 5666ba96e8db
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_owner_id_not_null"
down_revision = "5666ba96e8db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.alter_column("owner_id", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.alter_column("owner_id", existing_type=sa.String(), nullable=True)
