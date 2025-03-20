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

import os
import datetime
import json
from typing import Dict

from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder

from agri_gaia_backend.schemas.user_events import (
    UserRegistrationEvent,
    UserDeregistrationEvent,
)

from sqlalchemy.orm import Session

from agri_gaia_backend.services.user_provisioning import user_registration
from agri_gaia_backend.services.docker import util as docker_util
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.util.auth import service_account
from agri_gaia_backend.db import container_api
from agri_gaia_backend.routers.common import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service")


@router.post("/user-registration", tags=["service"])
async def on_user_registration(
    request: Request, registration_event: UserRegistrationEvent
):
    user: KeycloakUser = request.user
    if user.username != service_account.BACKEND_SERVICE_ACCOUNT_USERNAME:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED)

    user_registration.setup_user_infrastructure(registration_event.username)
    return JSONResponse(content=jsonable_encoder({"result": "success"}))


@router.post("/user-deregistration", tags=["service"])
async def on_user_registration(
    request: Request, deregistration_event: UserDeregistrationEvent
):
    user: KeycloakUser = request.user
    if user.username != service_account.BACKEND_SERVICE_ACCOUNT_USERNAME:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED)

    logger.debug("Deregistration Event received: " + deregistration_event.username)
    user_registration.teardown_user_infrastructure(deregistration_event.username)
    return JSONResponse(content=jsonable_encoder({"result": "success"}))


@router.post("/registry-event", tags=["service"])
async def on_registry_event(
    request: Request,
    db: Session = Depends(get_db),
):
    data = await request.json()
    filter_condition = (
        lambda e: e["action"] == "push"
        and "manifests" in e["target"]["url"]
        and "tag" in e["target"]
    )
    manifest_pe = list(filter(filter_condition, data["events"]))

    if len(manifest_pe) == 0:
        return Response()

    for pe in manifest_pe:
        try:
            repository = pe["target"]["repository"]
            tag = pe["target"]["tag"]
            owner = pe["actor"]["name"]

            manifest_or_index = docker_util.get_manifest(repository, tag)
            image_meta = dict(repository=repository, tag=tag, owner=owner)
            if docker_util.is_image_manifest(pe["target"]["mediaType"]):
                handle_new_image(db, manifest_or_index, image_meta)
            elif docker_util.is_image_index(pe["target"]["mediaType"]):
                manifests = docker_util.get_manifests_from_index(
                    repository, manifest_or_index
                )
                current_images = (
                    container_api.get_container_images_by_repository_and_tag(
                        db, repository, tag
                    )
                )
                for single_manifest in manifests:
                    created_or_updated_image = handle_new_image(
                        db, single_manifest, image_meta
                    )
                    current_images = [
                        i
                        for i in current_images
                        if i["platform"] != created_or_updated_image["platform"]
                    ]

            else:
                logger.warning(
                    f"Got push event from registry with unhandled media type '{pe['target']['mediaType']}'. Can't extract all metainformation."
                )
        except Exception as e:
            logger.exception(e)

    return Response()


def handle_new_image(db: Session, manifest: Dict, image_meta: Dict):
    more_image_metadata = docker_util.get_image_metadata(
        image_meta["repository"], manifest
    )
    image_meta.update(more_image_metadata)

    container = container_api.get_container_image_by_repository_and_tag_and_platform(
        db, image_meta["repository"], image_meta["tag"], image_meta["platform"]
    )

    if container is not None:
        for attribute, value in image_meta.items():
            setattr(container, attribute, value)
        container.last_modified = datetime.datetime.now()
        container = container_api.update_container_image(db, container)
    else:
        container = container_api.create_container_image(
            db, **image_meta, last_modified=datetime.datetime.now()
        )
    return container


@router.get("/portainer-version", tags=["service"])
async def get_portainer_version(request: Request):
    data = {"version": os.environ.get("PORTAINER_VERSION")}
    return Response(content=data)
