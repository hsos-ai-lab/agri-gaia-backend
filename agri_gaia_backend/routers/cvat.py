#!/usr/bin/env python

# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-

import os
from typing import Dict
from hashlib import sha256

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.db import dataset_api as sql_api
from agri_gaia_backend.routers.common import check_exists, get_db
from agri_gaia_backend.schemas.dataset import Dataset
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.services.cvat.cvat_api import (
    create_task_for_dataset,
    rest_login,
    rest_logout,
    rest_user_exists,
    rest_user_create,
)
from agri_gaia_backend.schemas.cvat import CvatAuthDataSchema

ROOT_PATH = "/cvat"

router = APIRouter(prefix=ROOT_PATH)


def jwt2password(jwt: str) -> str:
    salt = os.getenv("CVAT_SUPERUSER_PASSWORD")
    return sha256((jwt["sub"] + salt).encode("utf-8")).hexdigest()


@router.post("/tasks/{dataset_id}", status_code=status.HTTP_201_CREATED)
def create_task(
    request: Request,
    auth_data: CvatAuthDataSchema,
    dataset_id: int,
    db: Session = Depends(get_db),
) -> Dict:
    user: KeycloakUser = request.user
    dataset: Dataset = check_exists(sql_api.get_dataset(db, dataset_id))
    return create_task_for_dataset(auth_data.dict(), dataset, user)


@router.post("/auth/login")
def auth_login(request: Request) -> CvatAuthDataSchema:
    user: KeycloakUser = request.user
    auth_data = rest_login(
        username=user.username,
        password=jwt2password(user.jwt_token),
    )
    return CvatAuthDataSchema(**auth_data)


@router.post("/auth/logout")
def auth_logout(auth_data: CvatAuthDataSchema) -> Dict:
    return rest_logout(auth_data.dict())


@router.post("/user/create")
def user_create(request: Request) -> Dict:
    user: KeycloakUser = request.user
    jwt: Dict = user.jwt_token

    return rest_user_create(
        username=user.username,
        email=jwt["email"],
        password=jwt2password(jwt),
        first_name=jwt["given_name"],
        last_name=jwt["family_name"],
    )


@router.get("/user/exists")
def user_exists(request: Request) -> Dict:
    user: KeycloakUser = request.user
    return rest_user_exists(user.username)
