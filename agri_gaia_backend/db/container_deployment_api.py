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

from sqlalchemy.orm import Session

from agri_gaia_backend.db.models import (
    ContainerDeployment,
    ContainerDeploymentStatus,
    PortBinding,
)
from agri_gaia_backend.schemas.container_deployment import ContainerDeploymentCreate
from agri_gaia_backend.schemas.container_image import ContainerImage

import datetime


def get_container_deployment(db: Session, container_deployment_id: int):
    return (
        db.query(ContainerDeployment)
        .filter(ContainerDeployment.id == container_deployment_id)
        .first()
    )


def get_container_deployments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(ContainerDeployment).offset(skip).limit(limit).all()


def get_container_deployments_for_container_image(
    db: Session, container_image: ContainerImage
):
    return (
        db.query(ContainerDeployment)
        .filter(ContainerDeployment.container_image_id == container_image.id)
        .all()
    )


def create_container_deployment(
    db: Session,
    container_deployment_create: ContainerDeploymentCreate,
    creation_date: datetime.datetime,
    status: ContainerDeploymentStatus = ContainerDeploymentStatus.created,
):
    cd_create_dict = container_deployment_create.dict()
    # ports bindings is a list of dicts so we need to convert each dict to a PortBinding object
    port_bindings = [PortBinding(**pm) for pm in cd_create_dict.pop("port_bindings")]
    db_container_deployment = ContainerDeployment(
        **cd_create_dict,
        port_bindings=port_bindings,
        status=status,
        creation_date=creation_date
    )

    db.add(db_container_deployment)
    for pm in db_container_deployment.port_bindings:
        db.add(pm)

    db.commit()
    db.refresh(db_container_deployment)
    return db_container_deployment


def update_container_deployment(db: Session, container_deployment: ContainerDeployment):
    db.add(container_deployment)
    db.commit()
    db.refresh(container_deployment)
    return container_deployment


def delete_container_deployment(db: Session, container_deployment: ContainerDeployment):
    db.delete(container_deployment)
    db.commit()
    return True
