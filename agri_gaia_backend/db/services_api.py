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

from multiprocessing.dummy import Array
from typing import List, Optional
from sqlalchemy.orm import Session
import datetime

from agri_gaia_backend.db import models


def get_service(db: Session, service_id: int) -> Optional[models.Service]:
    return db.query(models.Service).filter(models.Service.id == service_id).first()


def get_services_by_owner(
    db: Session, owner: str, skip: int = 0, limit: int = 100
) -> List[models.Service]:
    return (
        db.query(models.Service)
        .filter(models.Service.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_published_services(
    db: Session, skip: int = 0, limit: int = 100  
) -> List[models.Service]:
    return(
        db.query(models.Service)
        .filter(models.Service.public == True)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_services_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> List[models.Service]:
    return (
        db.query(models.Service)
        .filter(models.Service.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_service_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> models.Service:
    return (
        db.query(models.Service)
        .filter(models.Service.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_services_by_metadata_uri(
    db: Session, skip: int = 0, limit: int = 100, uris: Array = []
) -> List[models.Service]:
    return (
        db.query(models.Service)
        .filter(models.Service.metadata_uri.in_(uris))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_services(db: Session, skip: int = 0, limit: int = 100) -> List[models.Service]:
    return db.query(models.Service).offset(skip).limit(limit).all()


def create_service(
    db: Session,
    name: str,
    owner: str,
    last_modified: datetime.datetime,
    bucket_name: str,
) -> models.Service:
    db_service = models.Service(
        name=name,
        owner=owner,
        last_modified=last_modified,
        bucket_name=bucket_name,
    )
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


def update_service(db: Session, service: models.Service) -> models.Service:
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service: models.Service) -> bool:
    db.delete(service)
    db.commit()
    return True
