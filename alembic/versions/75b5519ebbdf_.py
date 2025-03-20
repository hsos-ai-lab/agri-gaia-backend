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

"""empty message

Revision ID: 75b5519ebbdf
Revises: b4756864b403, 6ab621a12a8f
Create Date: 2022-07-13 15:51:04.152032

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "75b5519ebbdf"
down_revision = ("b4756864b403", "6ab621a12a8f")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
