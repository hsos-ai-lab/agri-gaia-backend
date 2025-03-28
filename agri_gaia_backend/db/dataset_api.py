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

from multiprocessing.dummy import Array
from typing import List, Optional
from sqlalchemy.orm import Session
import datetime

from agri_gaia_backend.db import models


def get_dataset(db: Session, dataset_id: int) -> Optional[models.Dataset]:
    return db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()


def get_datasets_by_owner(
    db: Session, owner: str, skip: int = 0, limit: int = 100
) -> List[models.Dataset]:
    return (
        db.query(models.Dataset)
        .filter(models.Dataset.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_published_datasets(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Dataset]:
    return (
        db.query(models.Dataset)
        .filter(models.Dataset.public == True)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_datasets_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> List[models.Dataset]:
    return (
        db.query(models.Dataset)
        .filter(models.Dataset.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_dataset_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> models.Dataset:
    return (
        db.query(models.Dataset)
        .filter(models.Dataset.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_datasets_by_metadata_uri(
    db: Session, skip: int = 0, limit: int = 100, uris: Array = []
) -> List[models.Dataset]:
    return (
        db.query(models.Dataset)
        .filter(models.Dataset.metadata_uri.in_(uris))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_datasets(db: Session, skip: int = 0, limit: int = 100) -> List[models.Dataset]:
    return db.query(models.Dataset).offset(skip).limit(limit).all()


def create_dataset(
    db: Session,
    name: str,
    owner: str,
    filecount: int,
    total_filesize: int,
    last_modified: datetime.datetime,
    bucket_name: str,
    annotation_labels: List[str],
    dataset_type: str,
) -> models.Dataset:
    db_dataset = models.Dataset(
        name=name,
        owner=owner,
        filecount=filecount,
        total_filesize=total_filesize,
        last_modified=last_modified,
        bucket_name=bucket_name,
        annotation_labels=annotation_labels,
        dataset_type=dataset_type,
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    return db_dataset


def update_dataset(db: Session, dataset: models.Dataset) -> models.Dataset:
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, dataset: models.Dataset) -> bool:
    db.delete(dataset)
    db.commit()
    return True
