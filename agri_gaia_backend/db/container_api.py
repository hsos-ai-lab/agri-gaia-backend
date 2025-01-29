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

import datetime

from typing import List, Optional
from sqlalchemy.orm import Session

from agri_gaia_backend.db import models


def get_container_image(
    db: Session, container_image_id: int
) -> Optional[models.ContainerImage]:
    return (
        db.query(models.ContainerImage)
        .filter(models.ContainerImage.id == container_image_id)
        .first()
    )


def get_container_images(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.ContainerImage]:
    return db.query(models.ContainerImage).offset(skip).limit(limit).all()


def get_container_images_by_owner(
    db: Session, owner: str, skip: int = 0, limit: int = 100
) -> List[models.ContainerImage]:
    return (
        db.query(models.ContainerImage)
        .filter(models.ContainerImage.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )


@DeprecationWarning
def get_container_image_by_repository_and_tag(
    db: Session, repository: str, tag: str
) -> Optional[models.ContainerImage]:
    return (
        db.query(models.ContainerImage)
        .filter(
            models.ContainerImage.repository == repository,
            models.ContainerImage.tag == tag,
        )
        .first()
    )


# this can return multiple containers, if there are images for multiple platforms
def get_container_images_by_repository_and_tag(
    db: Session, repository: str, tag: str
) -> List[models.ContainerImage]:
    return (
        db.query(models.ContainerImage)
        .filter(
            models.ContainerImage.repository == repository,
            models.ContainerImage.tag == tag,
        )
        .all()
    )


def get_container_image_by_repository_and_tag_and_platform(
    db: Session, repository: str, tag: str, platform: str
) -> Optional[models.ContainerImage]:
    return (
        db.query(models.ContainerImage)
        .filter(
            models.ContainerImage.repository == repository,
            models.ContainerImage.tag == tag,
            models.ContainerImage.platform == platform,
        )
        .first()
    )


def get_container_images_for_model(
    db: Session, model: models.Model
) -> List[models.ContainerImage]:
    return (
        db.query(models.ContainerImage)
        .filter(models.ContainerImage.model_id == model.id)
        .all()
    )


def create_container_image(
    db: Session,
    owner: str,
    repository: str,
    tag: str,
    platform: str,
    exposed_ports: List[int],
    last_modified: datetime.datetime,
    metadata_uri: Optional[str] = None,
    model_id: Optional[int] = None,
    compressed_image_size: Optional[int] = None,
) -> models.ContainerImage:
    db_container_image = models.ContainerImage(
        owner=owner,
        repository=repository,
        tag=tag,
        platform=platform,
        exposed_ports=exposed_ports,
        last_modified=last_modified,
        metadata_uri=metadata_uri,
        model_id=model_id,
        compressed_image_size=compressed_image_size,
    )
    db.add(db_container_image)
    db.commit()
    db.refresh(db_container_image)
    return db_container_image


def update_container_image(
    db: Session, container_image: models.Model
) -> models.ContainerImage:
    db.add(container_image)
    db.commit()
    db.refresh(container_image)
    return container_image


def delete_container_image(db: Session, container_image: models.ContainerImage):
    db.delete(container_image)
    db.commit()
    return True
