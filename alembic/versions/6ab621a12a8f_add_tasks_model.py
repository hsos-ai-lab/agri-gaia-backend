# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Add tasks model

Revision ID: 6ab621a12a8f
Revises: 4aa84b223571
Create Date: 2022-07-07 11:03:42.465207

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6ab621a12a8f"
down_revision = "4aa84b223571"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiator", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("creation_date", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("created", "inprogress", "completed", "failed", name="taskstatus"),
            nullable=True,
        ),
        sa.Column("completion_percentage", sa.Float(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_id"), "tasks", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_tasks_id"), table_name="tasks")
    op.drop_table("tasks")
    # ### end Alembic commands ###