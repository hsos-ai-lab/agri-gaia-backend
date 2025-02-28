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

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from agri_gaia_backend.db.models import Application
from agri_gaia_backend.schemas import application as schemas


def get_application(db: Session, application_id: int) -> Application:
    return db.query(Application).filter(Application.id == application_id).first()


def get_applications(db: Session, skip: int = 0, limit: int = 100) -> List[Application]:
    return db.query(Application).offset(skip).limit(limit).all()


def create_application(
    db: Session,
    application_create: schemas.ApplicationCreate,
    edge_stack_id: int,
    last_modified: datetime,
) -> Application:
    db_application = Application(
        name=application_create.name,
        yaml=application_create.yaml,
        last_modified=last_modified,
        portainer_edge_stack_id=edge_stack_id,
        portainer_edge_group_ids=application_create.group_ids,
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


def update_application(db: Session, application: Application) -> Application:
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def delete_application(db: Session, application: Application) -> bool:
    db.delete(application)
    db.commit()
    return True
