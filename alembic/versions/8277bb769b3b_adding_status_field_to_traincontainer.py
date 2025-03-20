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

"""Adding status field to TrainContainer.

Revision ID: 8277bb769b3b
Revises: 75b5519ebbdf
Create Date: 2022-07-14 10:44:03.387844

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8277bb769b3b"
down_revision = "75b5519ebbdf"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("train_containers", sa.Column("status", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("train_containers", "status")
    # ### end Alembic commands ###
