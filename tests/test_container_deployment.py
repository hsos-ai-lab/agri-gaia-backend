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

import logging
import pytest
import time
import requests
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_202_ACCEPTED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from agri_gaia_backend import schemas

from agri_gaia_backend.db import container_deployment_api, container_api, tasks_api
from agri_gaia_backend.db.models import TaskStatus
from agri_gaia_backend.services.portainer.portainer_api import portainer

from . import mock


class TestCreateContainerDeployment:
    def test_create_invalid_container_deployment(
        self, testclient: TestClient, db: Session
    ):
        data = {
            "name": "Test-Container",
        }
        num_containers_before = len(
            container_deployment_api.get_container_deployments(db)
        )
        response = testclient.post("/container-deployments", json=data)

        print(response.text)
        assert (
            response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
        ), "Creating an invalid container deployment shouldn't be allowed"

        assert (
            len(container_deployment_api.get_container_deployments(db))
            == num_containers_before
        ), "Container Deployment was created"

    def test_given_unregistered_edge_device_when_create_container_deployment_then_return_error(
        self,
        testclient: TestClient,
        db: Session,
        test_edge_device,
        test_container_image,
    ):
        payload = {
            "name": "Test-Container-Deployment",
            "edge_device_id": test_edge_device.id,
            "container_image_id": test_container_image.id,
            "port_bindings": [
                {"host_port": 8000, "container_port": 80, "protocol": "tcp"}
            ],
        }
        num_containers_before = len(
            container_deployment_api.get_container_deployments(db)
        )

        response = testclient.post("/container-deployments", json=payload)

        assert (
            not response.is_success
        ), "Container deployment was created when it shouldn't be"
        assert (
            response.status_code == HTTP_409_CONFLICT
        ), "Wrong response code for invalid container deployment creation"
        assert (
            len(container_deployment_api.get_container_deployments(db))
            == num_containers_before
        ), "Container Deployment was created"

    def test_given_nonexistent_container_id_when_create_container_deployment_then_return_404(
        self,
        testclient: TestClient,
        db: Session,
        monkeypatch,
        registered_test_edge_device,
    ):
        non_existing_container_id = 9999999
        assert (
            container_api.get_container_image(db, non_existing_container_id) is None
        ), "Precondition failed: container exists"
        payload = {
            "name": "Test-Container-Deployment",
            "edge_device_id": registered_test_edge_device.id,
            "container_image_id": non_existing_container_id,
            "port_bindings": [
                {"host_port": 8000, "container_port": 80, "protocol": "tcp"}
            ],
        }

        num_containers_before = len(
            container_deployment_api.get_container_deployments(db)
        )

        with monkeypatch.context() as m:
            mock_method = mock.common.MockRequestsMethod()
            mock_method.add_response(
                ".*/docker/containers/json",
                mock.portainer.DockerContainersMockResponse([]),
            )
            m.setattr(requests, "get", mock_method)
            response = testclient.post("/container-deployments", json=payload)

        assert response.status_code == HTTP_404_NOT_FOUND, "Wrong response code"
        assert (
            len(container_deployment_api.get_container_deployments(db))
            == num_containers_before
        ), "Container Deployment was created"

    def test_given_container_deployment_with_same_name_exists_when_create_then_return_error(
        self,
        testclient: TestClient,
        db: Session,
        monkeypatch,
        registered_test_edge_device,
        test_container_image,
    ):
        payload = {
            "name": mock.portainer.DockerContainersMockResponse.DUMMY_CONTAINER["Name"],
            "edge_device_id": registered_test_edge_device.id,
            "container_image_id": test_container_image.id,
            "port_bindings": [
                {"host_port": 8000, "container_port": 80, "protocol": "tcp"}
            ],
        }

        num_containers_before = len(
            container_deployment_api.get_container_deployments(db)
        )

        with monkeypatch.context() as m:
            mock_method = mock.common.MockRequestsMethod()
            mock_method.add_response(
                ".*/docker/containers/json",
                mock.portainer.DockerContainersMockResponse(),
            )
            m.setattr(requests, "get", mock_method)
            response = testclient.post("/container-deployments", json=payload)

        print(response.status_code)
        assert response.status_code == HTTP_409_CONFLICT, "Container was created"
        assert (
            len(container_deployment_api.get_container_deployments(db))
            == num_containers_before
        ), "Container Deployment was created"

    # the container deployment is cleaned up automatically but could not figure out when
    @pytest.mark.filterwarnings("ignore:CleanupError")
    def test_create_valid_container_deployment(
        self,
        testclient: TestClient,
        db: Session,
        monkeypatch,
        registered_test_edge_device,
        test_container_image,
    ):
        payload = {
            "name": "Test-Container-Deployment",
            "edge_device_id": int(registered_test_edge_device.id),
            "container_image_id": int(test_container_image.id),
            "port_bindings": [
                {"host_port": 8000, "container_port": 80, "protocol": "tcp"}
            ],
        }

        logging.info("========================================")
        logging.info(payload)

        num_containers_before = len(
            container_deployment_api.get_container_deployments(db)
        )

        with monkeypatch.context() as m:
            mock_method = mock.common.MockRequestsMethod()
            mock_method.add_response(
                ".*/docker/containers/json",
                mock.portainer.DockerContainersMockResponse([]),
            )
            m.setattr(requests, "get", mock_method)
            response = testclient.post("/container-deployments", json=payload)

        assert (
            response.status_code == HTTP_201_CREATED
        ), "Error creating container deployment"
        assert (
            len(container_deployment_api.get_container_deployments(db))
            == num_containers_before + 1
        ), "Container Deployment was not created"


class TestGetContainerDeployment:
    def test_get_container_deployment_incorrect_id(
        self, testclient: TestClient, db: Session
    ):
        response = testclient.get(f"/container-deployments/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container Deployment shouldn't have been returned"

    @pytest.mark.filterwarnings(
        "ignore:CleanupError"
    )  # cascade-deleted when testcontainer is deleted
    def test_get_all_container_deployments(
        self,
        test_user,
        testclient: TestClient,
        test_container_deployment,
        db,
    ):
        num_containers = len(container_deployment_api.get_container_deployments(db))
        response = testclient.get("/container-deployments")

        container_deployments = response.json()

        filtered_container_deployments = [
            d for d in container_deployments if d["id"] == test_container_deployment.id
        ]

        assert (
            len(filtered_container_deployments) == 1
        ), "TestContainerDeployment is not in the returned container_deployments (or too many with the same id)"

        assert (
            response.status_code == HTTP_200_OK
        ), "Error getting Container Deployments"

        assert (
            len(container_deployments) == num_containers
        ), "Response contains the wrong amount of containers"

        assert (
            filtered_container_deployments[0]["edge_device_id"]
            == test_container_deployment.edge_device_id
        ), "Filtered Container Deployment contains wrong Edge Device ID"

        assert (
            filtered_container_deployments[0]["container_image"]["owner"]
            == test_user.username
        ), "Filtered Container Deployment contains wrong Edge Device ID"

    @pytest.mark.filterwarnings(
        "ignore:CleanupError"
    )  # cascade-deleted when testcontainer is deleted
    def test_get_single_container_deployment(
        self,
        testclient: TestClient,
        monkeypatch,
        test_container_deployment,
        test_container_image,
    ):
        with monkeypatch.context() as m:
            mock_method = mock.common.MockRequestsMethod()
            mock_method.add_response(
                ".*/docker/containers/json",
                mock.portainer.DockerContainersMockResponse([]),
            )
            m.setattr(requests, "get", mock_method)
            response = testclient.get(
                f"/container-deployments/{test_container_deployment.id}"
            )

        container_deployment = schemas.ContainerDeployment(**response.json())

        assert response.status_code == HTTP_200_OK, "Error getting container deployment"

        assert (
            container_deployment.id == test_container_deployment.id
        ), "Container deployment is not the test container deployment"
        assert (
            container_deployment.container_image == test_container_image
        ), "Container deployment is in wrong container"


class TestContainerDeploymentDelete:
    def test_delete_container_deployment_wrong_id(
        self,
        testclient: TestClient,
        db: Session,
    ):
        num_containers_before = len(
            container_deployment_api.get_container_deployments(db)
        )

        response = testclient.delete("/container-deployments/-10")

        num_containers_after = len(
            container_deployment_api.get_container_deployments(db)
        )

        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Error deleting container deployment"

        assert (
            num_containers_before == num_containers_after
        ), "Numbers of container Deployments shouldn't change"

    @pytest.mark.filterwarnings("ignore:CleanupError")
    def test_given_container_deployment_in_created_state_when_delete_then_okay(
        self, testclient: TestClient, db: Session, test_container_deployment
    ):
        response = testclient.delete(
            f"/container-deployments/{test_container_deployment.id}"
        )
        assert (
            container_deployment_api.get_container_deployment(
                db, test_container_deployment.id
            )
            is None
        ), "Container deployment was not deleted"
        assert (
            response.status_code == HTTP_204_NO_CONTENT
        ), "Error deleting container deployment"


"""TEST LATER Doesn't work with Monkeypatch
class TestContainerDeploymentDeploy:
    # check portainer repsonse, check if container is on deployed status
    # check if name is not already on edge device
    def test_deploy_container_deployment(
        self,
        testclient: TestClient,
        test_container_deployment,
        monkeypatch,
        db,
    ):

        with monkeypatch.context() as m:
            mock_method = mock.common.MockRequestsMethod()
            mock_method.add_response(
                ".*\/docker\/images\/create.*",
                mock.portainer.DockerImageCreateMockResponse([]),
            )
            m.setattr(requests, "post", mock_method)
            response = testclient.put(
                f"/container-deployments/{test_container_deployment.id}/deploy"
            )

        task_url = response.headers["Location"]
        task_response = testclient.get(task_url)
        task = schemas.Task(**task_response.json())

        start = time.time()
        while (task := tasks_api.get_task(db, task.id)).status in [
            TaskStatus.created,
            TaskStatus.inprogress,
        ]:
            assert (
                time.time() - start < 3.0
            ), "Time condition not fulfilled, maybe increase the time limit"

        assert (
            response.status_code == HTTP_202_ACCEPTED
        ), "Error deploying Container Deployment"

        assert task.status == TaskStatus.completed

    def test_deploy_container_deployment_wrong_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.put("/container-deployments/-10/deploy")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container deployment with wrong ID was still found"


class TestContainerDeploymentUndeploy:
    def test_undeploy_container_deployment_wrong_id(
        self,
        testclient: TestClient,
    ):
        response = testclient.put("/container-deployments/-10/undeploy")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Container deployment with wrong ID was still found"
"""
