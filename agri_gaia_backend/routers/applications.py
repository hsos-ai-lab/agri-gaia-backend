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

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Response, status

from sqlalchemy.orm import Session
from agri_gaia_backend.schemas.application import (
    Application,
    ApplicationCreate,
    ApplicationUpdate,
)

from agri_gaia_backend.routers.common import check_exists, get_db
from agri_gaia_backend.db import (
    models,
    application_api as sql_api,
)
from agri_gaia_backend.routers.common import check_exists
from agri_gaia_backend.services.portainer.portainer_api import portainer

import logging

logger = logging.getLogger("api-logger")


ROOT_PATH = "/applications"
router = APIRouter(prefix=ROOT_PATH)


@router.get("", response_model=List[Application])
def get_all_applications(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    portainer_edge_stacks = portainer.get_all_edge_stacks()
    applications = sql_api.get_applications(db, skip=skip, limit=limit)
    # add errors / logs.
    for app in applications:
        stack = next(
            (
                s
                for s in portainer_edge_stacks
                if s["Id"] == app.portainer_edge_stack_id
            ),
            None,
        )
        if stack:
            app.status = stack["Status"]
            # for k in status.keys():
            #    status[k]["Type"]
            #    status[k]["Error"]
            #    status[k]["EndpointID"]

    return applications


@router.get("/{application_id}", response_model=Application)
def get_application(application_id: int, db: Session = Depends(get_db)):
    return check_exists(sql_api.get_application(db, application_id))


@router.post("", response_model=Application, status_code=status.HTTP_201_CREATED)
def create_application(
    application_create: ApplicationCreate, db: Session = Depends(get_db)
):

    edge_stack = portainer.deploy_edge_stack(
        name=application_create.name,
        edge_group_ids=application_create.group_ids,
        yaml=application_create.yaml,
    )
    edge_stack_id = edge_stack["Id"]
    return sql_api.create_application(
        db,
        application_create,
        edge_stack_id,
        last_modified=datetime.now(),
    )


@router.put("/{application_id}", response_model=Application)
def edit_application(
    application_id: int,
    application_update: ApplicationUpdate,
    db: Session = Depends(get_db),
):

    application: models.Application = check_exists(
        sql_api.get_application(db, application_id)
    )

    portainer.edit_edge_stack(
        application.portainer_edge_stack_id,
        application_update.group_ids,
        application_update.yaml,
    )

    application.yaml = application_update.yaml
    application.portainer_edge_group_ids = application_update.group_ids

    logger.debug(application.portainer_edge_group_ids)

    return sql_api.update_application(db, application)


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):

    application: models.Application = check_exists(
        sql_api.get_application(db, application_id)
    )

    portainer.delete_edge_stack(application.portainer_edge_stack_id)

    sql_api.delete_application(db, application)
    return Response(status_code=204)
