# SPDX-FileCopyrightText: 2024 Osnabrück University of Applied Sciences
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT

"""Adding model_filepath to TrainContainer.

Revision ID: f61279c37563
Revises: 568a140ba0d0
Create Date: 2022-08-13 21:55:34.932325

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f61279c37563"
down_revision = "568a140ba0d0"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "train_containers", sa.Column("model_filepath", sa.String(), nullable=True)
    )
    op.add_column(
        "train_containers", sa.Column("score_regexp", sa.String(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("train_containers", "score_regexp")
    op.drop_column("train_containers", "model_filepath")
    # ### end Alembic commands ###
