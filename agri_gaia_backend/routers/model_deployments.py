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

from typing import List
import datetime

from fastapi import APIRouter, Request, Depends, Response

from sqlalchemy.orm import Session

from agri_gaia_backend.db.models import ModelDeploymentStatus, DeploymentType

from agri_gaia_backend.schemas.model_deployment import (
    ModelDeploymentCreate,
    ModelDeployment,
)

from agri_gaia_backend.services.model_deployment import deployment_service
from agri_gaia_backend.routers.common import check_exists, get_db

from agri_gaia_backend.db import (
    model_deployment_api as sql_api,
    model_api as model_api,
    edge_device_api as edge_device_api,
)

import logging

logger = logging.getLogger("api-logger")


ROOT_PATH = "/model-deployments"
router = APIRouter(prefix=ROOT_PATH)


@router.get("", response_model=List[ModelDeployment])
def get_all_model_deployments(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return sql_api.get_model_deployments(db, skip=skip, limit=limit)


@router.get("/{model_deployment_id}", response_model=ModelDeployment)
def get_model_deployment(model_deployment_id: int, db: Session = Depends(get_db)):
    return check_exists(sql_api.get_model_deployment(db, model_deployment_id))


@router.post("", response_model=ModelDeployment)
def create_model_deployment(
    model_deployment_create: ModelDeploymentCreate, db: Session = Depends(get_db)
):
    return sql_api.create_model_deployment(
        db, model_deployment_create, creation_date=datetime.datetime.now()
    )


@router.put("/{model_deployment_id}/deploy", response_model=ModelDeployment)
def deploy_model(model_deployment_id: int, db: Session = Depends(get_db)):
    model_deployment = sql_api.get_model_deployment(db, model_deployment_id)

    if model_deployment.status == ModelDeploymentStatus.running:
        return model_deployment

    model = model_api.get_model(db, model_deployment.model_id)

    if model_deployment.type == DeploymentType.edge:
        edge_device = edge_device_api.get_edge_device(
            db, model_deployment.edge_device_id
        )
        deployment_status = deployment_service.deploy_model_to_edge(model, edge_device)
    elif model_deployment.type == DeploymentType.cloud:
        raise NotImplementedError("Cloud deployment is not implemented yet")

    model_deployment.status = deployment_status

    return sql_api.update_model_deployment(db, model_deployment)


@router.put("/{model_deployment_id}/undeploy", response_model=ModelDeployment)
def undeploy_model(model_deployment_id: int, db: Session = Depends(get_db)):
    model_deployment = sql_api.get_model_deployment(db, model_deployment_id)

    if model_deployment.status != ModelDeploymentStatus.running:
        return model_deployment

    model = model_api.get_model(db, model_deployment.model_id)

    if model_deployment.type == DeploymentType.edge:
        edge_device = edge_device_api.get_edge_device(
            db, model_deployment.edge_device_id
        )
        deployment_status = deployment_service.undeploy_model_from_edge(
            model, edge_device
        )
    elif model_deployment.type == DeploymentType.cloud:
        raise NotImplementedError("Cloud deployment is not implemented yet")

    model_deployment.status = deployment_status
    return sql_api.update_model_deployment(db, model_deployment)


@router.delete("/{model_deployment_id}")
def delete_model_deployment(
    request: Request, model_deployment_id: int, db: Session = Depends(get_db)
):
    model_deployment = check_exists(
        sql_api.get_model_deployment(db, model_deployment_id)
    )
    if model_deployment.status == ModelDeploymentStatus.running:
        model_deployment = undeploy_model(model_deployment_id)

    sql_api.delete_model_deployment(db, model_deployment)
    return Response(status_code=204)
