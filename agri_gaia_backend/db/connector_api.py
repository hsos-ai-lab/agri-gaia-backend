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

from typing import List, Optional
from sqlalchemy.orm import Session

from agri_gaia_backend.db import models


def get_connector(db: Session, connector_id: int) -> Optional[models.Connector]:
    return (
        db.query(models.Connector).filter(models.Connector.id == connector_id).first()
    )


def get_connectors_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> List[models.Connector]:
    return (
        db.query(models.Connector)
        .filter(models.Connector.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_connector_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> models.Connector:
    return (
        db.query(models.Connector)
        .filter(models.Connector.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_connectors(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Connector]:
    return db.query(models.Connector).offset(skip).limit(limit).all()


def create_connector(
    db: Session,
    name: str,
    description: str,
    data_url: str,
    ids_url: str,
    minio_url: str,
    api_key: str,
) -> models.Connector:
    db_connector = models.Connector(
        name=name,
        description=description,
        data_url=data_url,
        ids_url=ids_url,
        minio_url=minio_url,
        api_key=api_key,
    )
    db.add(db_connector)
    db.commit()
    db.refresh(db_connector)
    return db_connector


def update_connector(db: Session, connector: models.Connector) -> models.Connector:
    db.add(connector)
    db.commit()
    db.refresh(connector)
    return connector


def delete_connector(db: Session, connector: models.Connector) -> bool:
    db.delete(connector)
    db.commit()
    return True
