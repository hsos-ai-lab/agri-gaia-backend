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

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder

from agri_gaia_backend.schemas.keycloak_user import KeycloakUser

import logging

logger = logging.getLogger("api-logger")

router = APIRouter(prefix="/users")


@router.get("/me", tags=["users"])
async def me(request: Request):
    user: KeycloakUser = request.user
    return JSONResponse(
        content=jsonable_encoder({"hello": user.username, "token": user.access_token})
    )


# respond to pings from a user to check login token validity
@router.get("/ping", tags=["users"])
async def me(request: Request):
    return Response()
