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

import time
import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_202_ACCEPTED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from agri_gaia_backend.db import tasks_api
from agri_gaia_backend.db.models import TaskStatus
from agri_gaia_backend import schemas


class TestGetContainerImage:
    # TODO container hinzufügen
    def test_get_container_images(self, testclient: TestClient, db: Session):
        response = testclient.get("/container-images")
        assert response.status_code == HTTP_200_OK, "Error getting containers"

    def test_get_container_image_wrong_repository_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.get("/container-images/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"

    def test_get_container_image_wrong_second_repository_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.get("/container-images/-10/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"


class TestContainerImageDelete:
    def test_delete_cont2ainer_image_wrong_repository_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.delete("/container-images/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"

    def test_delete_container_image_wrong_second_repository_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.delete("/container-images/-10/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"

    def test_delete_container_image_wrong_second_repository_id_and_wrong_image_tag(
        self,
        testclient: TestClient,
    ):
        response = testclient.delete("/container-images/-10/-10:-10")
        assert (
            response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        ), "Container with wrong ID was found"


class TestContainerImageDownload:
    def test_download_container_image_wrong_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.post("/container-images/download/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"

    def test_download_container_image_invalid_tag(
        self,
        testclient: TestClient,
    ):
        response = testclient.post("/container-images/download/-10/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"


"""
    def test_download_container_invalid_arch(
        self, request, authenticated_client: TestClient, db
    ):
        response = authenticated_client.post("/containers/download/-10/-10/-10")
        task_url = response.headers["Location"]
        task_response = authenticated_client.get(task_url)
        task = schemas.Task(**task_response.json())

        def delete_task():
            tasks_api.delete_task(db, tasks_api.get_task(db, task.id))

        request.addfinalizer(delete_task)

        start = time.time()
        while (task := tasks_api.get_task(db, task.id)).status in [
            TaskStatus.created,
            TaskStatus.inprogress,
        ]:
            # TODO @Henri: was ist hier die Zeitspanne? war 1 sec...
            assert (
                time.time() - start < 5.0
            ), "Time condition not fulfilled, maybe increase the time limit"

        assert (
            response.status_code == HTTP_202_ACCEPTED
        ), "Error starting container download"
        assert task.status == TaskStatus.failed, "Task should've thrown an error"
"""


class TestContainerImageBuild:
    def test_build_container_image_wrong_parameters(
        self,
        testclient: TestClient,
    ):
        data = {
            "repository_name": "-10",
            "tag": "-10",
        }
        response = testclient.post("/containter-images/build", json=data)
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container with wrong ID was found"
