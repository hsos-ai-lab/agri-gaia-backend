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

import os
import time

from starlette.authentication import AuthenticationBackend, AuthCredentials
from fastapi import Request

from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakConnectionError

import logging

from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.schemas.registry_user import RegistryUser

logger = logging.getLogger("api-logger")

REGISTRY_TOKEN = os.environ.get("REGISTRY_TOKEN")


class BearerTokenAuthBackend(AuthenticationBackend):
    def __init__(self) -> None:
        super().__init__()

        self.keycloak = KeycloakOpenID(
            server_url=f"{os.environ.get('KEYCLOAK_INTERNAL_URL')}/",
            client_id=os.environ.get("BACKEND_OPENID_CLIENT_ID"),
            realm_name=os.environ.get("KEYCLOAK_REALM_NAME"),
            client_secret_key=os.environ.get("BACKEND_OPENID_CLIENT_SECRET"),
        )

        self.keycloak_public_key = None

        while self.keycloak_public_key is None:
            try:
                self.keycloak_public_key = (
                    "-----BEGIN PUBLIC KEY-----\n"
                    + self.keycloak.public_key()
                    + "\n-----END PUBLIC KEY-----"
                )
            except KeycloakConnectionError:
                logging.warn("Could not connect to Keycloak. Try again in 5 seconds...")
                time.sleep(5)

    async def authenticate(self, request: Request):
        if self.keycloak_public_key is None:
            logger.debug("Auth Backend not initialized!")
            return None

        if "Authorization" not in request.headers:
            # logger.debug("No Auth Header!")
            return None

        access_token = request.headers["Authorization"].split(" ")[-1]

        # Check if it is the Bearer Token of the registry User:
        # TODO: make this not cringy
        if access_token == REGISTRY_TOKEN:
            return AuthCredentials(["authenticated"]), RegistryUser()

        # and if not, log in normal user:
        options = {"verify_signature": True, "verify_aud": True, "verify_exp": True}

        try:
            jwt_token = self.keycloak.decode_token(
                access_token, key=self.keycloak_public_key, options=options
            )
            return AuthCredentials(["authenticated"]), KeycloakUser(
                jwt_token, access_token
            )
        except Exception as e:
            logger.error("Could not decode token")
            logger.error(e)
            return None
