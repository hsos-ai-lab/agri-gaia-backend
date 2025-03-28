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
from starlette.authentication import SimpleUser


class KeycloakUser(SimpleUser):
    def __init__(self, jwt_token: dict, access_token: str) -> None:
        super(KeycloakUser, self).__init__(jwt_token["preferred_username"])
        self.jwt_token = jwt_token
        self.access_token = access_token

    @property
    def minio_token(self) -> str:
        return {"access_token": self.access_token}

    @property
    def minio_bucket_name(self) -> str:
        return self.username

    @property
    def volume_name(self) -> str:
        return f"{os.environ.get('PROJECT_NAME')}_user_data_{self.username}"

    @property
    def docker_auth(self) -> dict:
        return {"access_token": self.access_token, "exp": self.jwt_token["exp"]}
