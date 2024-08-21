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

"""Adding score and score_name to TrainContainer.

Revision ID: c502af8cbbc1
Revises: f61279c37563
Create Date: 2022-08-13 23:30:32.071800

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c502af8cbbc1'
down_revision = 'f61279c37563'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('train_containers', sa.Column('score_name', sa.String(), nullable=True))
    op.add_column('train_containers', sa.Column('score', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('train_containers', 'score')
    op.drop_column('train_containers', 'score_name')
    # ### end Alembic commands ###