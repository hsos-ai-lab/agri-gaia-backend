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

"""Refactor Container to ContainerImage

Revision ID: cfe722aefa59
Revises: f6f8f4c3a2f4
Create Date: 2023-04-24 14:59:52.115574

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "cfe722aefa59"
down_revision = "f6f8f4c3a2f4"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.rename_table("containers", "container_images")
    op.execute("ALTER SEQUENCE containers_id_seq RENAME TO container_images_id_seq")
    op.execute("ALTER INDEX containers_pkey RENAME TO container_images_pkey")
    op.execute("ALTER INDEX ix_containers_id RENAME TO ix_container_images_id")
    op.execute(
        "ALTER TABLE container_images RENAME CONSTRAINT containers_model_id_fkey TO container_images_model_id_fkey"
    )

    op.execute(
        "ALTER TABLE container_deployments RENAME COLUMN container_id TO container_image_id"
    )
    op.execute(
        "ALTER TABLE container_deployments RENAME CONSTRAINT container_deployments_container_id_fkey TO container_images_deployments_container_id_fkey"
    )

    # op.drop_constraint('container_deployments_container_id_fkey', 'container_deployments', type_='foreignkey')
    # op.create_foreign_key(None, 'container_deployments', 'container_images', ['container_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_constraint(None, 'container_deployments', type_='foreignkey')
    # op.create_foreign_key('container_deployments_container_id_fkey', 'container_deployments', 'containers', ['container_id'], ['id'])

    op.execute(
        "ALTER TABLE container_deployments RENAME CONSTRAINT container_images_deployments_container_id_fkey TO container_deployments_container_id_fkey"
    )
    op.execute(
        "ALTER TABLE container_deployments RENAME COLUMN container_image_id TO container_id"
    )

    op.execute(
        "ALTER TABLE container_images RENAME CONSTRAINT container_images_model_id_fkey TO containers_model_id_fkey"
    )
    op.execute("ALTER INDEX ix_container_images_id RENAME TO ix_containers_id")
    op.execute("ALTER INDEX container_images_pkey RENAME TO containers_pkey")
    op.execute("ALTER SEQUENCE container_images_id_seq RENAME TO containers_id_seq")
    op.rename_table("container_images", "containers")

    # ### end Alembic commands ###
