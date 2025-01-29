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

"""add applications entity

Revision ID: 86230dd72507
Revises: c502af8cbbc1
Create Date: 2022-08-16 13:47:57.513639

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "86230dd72507"
down_revision = "c502af8cbbc1"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("yaml", sa.String(), nullable=True),
        sa.Column("last_modified", sa.DateTime(), nullable=True),
        sa.Column("portainer_edge_stack_id", sa.Integer(), nullable=True),
        sa.Column("portainer_edge_group_ids", sa.ARRAY(sa.Integer()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applications_id"), "applications", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_applications_id"), table_name="applications")
    op.drop_table("applications")
    # ### end Alembic commands ###
