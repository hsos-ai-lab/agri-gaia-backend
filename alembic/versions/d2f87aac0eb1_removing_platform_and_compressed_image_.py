# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT

"""Removing platform and compressed image size.

Revision ID: d2f87aac0eb1
Revises: a5ab059c815d
Create Date: 2022-09-06 15:08:11.910773

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2f87aac0eb1"
down_revision = "a5ab059c815d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("train_containers", "platform")
    op.drop_column("train_containers", "compressed_image_size")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "train_containers",
        sa.Column(
            "compressed_image_size", sa.BIGINT(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "train_containers",
        sa.Column("platform", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    # ### end Alembic commands ###
