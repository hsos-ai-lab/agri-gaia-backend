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


def get_inference_result(db: Session, inference_id: int) -> Optional[models.Inference]:
    return (
        db.query(models.Inference).filter(models.Inference.id == inference_id).first()
    )


def get_inferences_by_owner(
    db: Session, owner: str, skip: int = 0, limit: int = 100
) -> List[models.Inference]:
    return (
        db.query(models.Inference)
        .filter(models.Inference.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_inferences_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> List[models.Inference]:
    return (
        db.query(models.Inference)
        .filter(models.Inference.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_inference_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> models.Inference:
    return (
        db.query(models.Inference)
        .filter(models.Inference.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_inferences_by_metadata_uri(
    db: Session, skip: int = 0, limit: int = 100, uris: Array = []
) -> List[models.Inference]:
    return (
        db.query(models.Inference)
        .filter(models.Inference.metadata_uri.in_(uris))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_inferences(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Inference]:
    return db.query(models.Inference).offset(skip).limit(limit).all()


def create_inference(
    db: Session,
    name: str,
    owner: str,
    last_modified: datetime.datetime,
    bucket_name: str,
) -> models.Inference:
    db_inference = models.Inference(
        name=name,
        owner=owner,
        last_modified=last_modified,
        bucket_name=bucket_name,
    )
    db.add(db_inference)
    db.commit()
    db.refresh(db_inference)
    return db_inference


def update_inference(db: Session, inference: models.Inference) -> models.Inference:
    db.add(inference)
    db.commit()
    db.refresh(inference)
    return inference


def delete_inference(db: Session, inference: models.Inference) -> bool:
    db.delete(inference)
    db.commit()
    return True
