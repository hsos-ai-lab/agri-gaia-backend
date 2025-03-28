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

import logging

from typing import Dict
from fastapi import APIRouter, HTTPException
from agri_gaia_backend.util.env import (
    PROJECT_BASE_URL,
    REALM_SERVICE_ACCOUNT_USERNAME,
    REALM_SERVICE_ACCOUNT_PASSWORD,
    FUSEKI_ADMIN_USER,
    FUSEKI_ADMIN_PASSWORD,
)

ROOT_PATH = "/urls"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


def create_basic_auth_url(subdomain: str, username: str, password: str) -> str:
    return f"https://{username}:{password}@{subdomain}.{PROJECT_BASE_URL}"


BASIC_AUTH_URLS = {
    "nuclio": create_basic_auth_url(
        "nuclio", REALM_SERVICE_ACCOUNT_USERNAME, REALM_SERVICE_ACCOUNT_PASSWORD
    ),
    "fuseki": create_basic_auth_url("fuseki", FUSEKI_ADMIN_USER, FUSEKI_ADMIN_PASSWORD),
}


@router.get("/basic-auth")
def get_all_basic_auth_urls() -> Dict[str, str]:
    return BASIC_AUTH_URLS


@router.get("/basic-auth/{subdomain}")
def get_basic_auth_url(subdomain: str) -> Dict[str, str]:
    try:
        return {"url": BASIC_AUTH_URLS[subdomain]}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Basic Auth URL not found for subdomain '{subdomain}'.",
        )
