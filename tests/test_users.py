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

import pytest
from starlette.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED
from fastapi.testclient import TestClient

from .conftest import Testuser


class TestUserAuthentication:
    def test_unauthenticated_returns_unauthorized(self, unauthenticated_client):
        response = unauthenticated_client.get("/users/me")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_me(self, testclient: TestClient, test_user: Testuser):
        response = testclient.get("/users/me")
        assert response.status_code == HTTP_200_OK
        assert response.json()["hello"] == test_user.username
