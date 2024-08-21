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

from agri_gaia_backend.db import models
from agri_gaia_backend.schemas import model_deployment as schemas
import datetime


def get_model_deployment(db: Session, model_deployment_id: int):
    return (
        db.query(models.ModelDeployment)
        .filter(models.ModelDeployment.id == model_deployment_id)
        .first()
    )


def get_model_deployments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ModelDeployment).offset(skip).limit(limit).all()


def create_model_deployment(
    db: Session,
    model_deployment_create: schemas.ModelDeploymentCreate,
    creation_date: datetime.datetime,
    status: models.ModelDeploymentStatus = models.ModelDeploymentStatus.created,
):
    db_model_deployment = models.ModelDeployment(
        **model_deployment_create.dict(), status=status, creation_date=creation_date
    )
    db.add(db_model_deployment)
    db.commit()
    db.refresh(db_model_deployment)
    return db_model_deployment


def update_model_deployment(db: Session, model_deployment: models.ModelDeployment):
    db.add(model_deployment)
    db.commit()
    db.refresh(model_deployment)
    return model_deployment


def delete_model_deployment(db: Session, model_deployment: models.ModelDeployment):
    db.delete(model_deployment)
    db.commit()
    return True
