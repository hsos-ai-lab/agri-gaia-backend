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

"""Adding platform and compressed_image_size to TrainContainer

Revision ID: a5ab059c815d
Revises: 86230dd72507
Create Date: 2022-09-06 09:30:25.353498

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a5ab059c815d"
down_revision = "86230dd72507"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("train_containers", sa.Column("platform", sa.String(), nullable=True))
    op.add_column(
        "train_containers",
        sa.Column("compressed_image_size", sa.BigInteger(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("train_containers", "compressed_image_size")
    op.drop_column("train_containers", "platform")
    # ### end Alembic commands ###
