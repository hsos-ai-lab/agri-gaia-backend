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

from typing import List

from sqlalchemy.orm import Session

from agri_gaia_backend.db import models
import datetime


def get_model(db: Session, model_id: int):
    return db.query(models.Model).filter(models.Model.id == model_id).first()


def get_models_by_owner(db: Session, owner: str, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Model)
        .filter(models.Model.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_model_by_name(db: Session, name: str, skip: int = 0, limit: int = 1):
    return (
        db.query(models.Model)
        .filter(models.Model.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_published_models(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Model]:
    return (
        db.query(models.Model)
        .filter(models.Model.public == True)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_models_by_metadata_uri(
    db: Session, skip: int = 0, limit: int = 100, uris: Array = []
):
    return (
        db.query(models.Model)
        .filter(models.Model.metadata_uri.in_(uris))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_models(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Model).offset(skip).limit(limit).all()


def create_model(
    db: Session,
    name: str,
    format: str,
    owner: str,
    last_modified: datetime.datetime,
    bucket_name: str,
    file_size: int,
    file_name: str,
):
    db_model = models.Model(
        name=name,
        format=format,
        owner=owner,
        last_modified=last_modified,
        bucket_name=bucket_name,
        file_size=file_size,
        file_name=file_name,
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


def update_model(db: Session, model: models.Model):
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def delete_model(db: Session, model: models.Model):
    db.delete(model)
    db.commit()
    return True
