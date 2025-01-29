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

from io import BytesIO
import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from fastapi.testclient import TestClient
from agri_gaia_backend import schemas


class TestCreateApplication:
    def test_create_application(
        self, authenticated_client: TestClient, test_edge_group, test_application
    ):
        data = {
            "name": "Test-Application-2",
            "group_ids": [test_edge_group["id"]],
            "yaml": "version: '3'\n\nservices:  \n  my-service:\n    # enter your application details...\n\nvolumes:\n",
        }
        applications = authenticated_client.get("/applications")
        len_applications_before = len(applications.json())

        response = authenticated_client.post("/applications", json=data)

        applications = authenticated_client.get("/applications")
        len_applications_after = len(applications.json())

        assert response.status_code == HTTP_201_CREATED, "Could not create application"
        response_application = schemas.Application(**response.json())

        assert response_application.name == "Test-Application-2"
        assert len(response_application.portainer_edge_group_ids) == 1
        assert response_application.portainer_edge_group_ids[0] == test_edge_group["id"]

        assert len_applications_after == len_applications_before + 1

    def test_create_application_with_already_existing_name(
        self, authenticated_client: TestClient, test_edge_group, test_application
    ):
        data = {
            "name": "Test-Application",
            "group_ids": [test_edge_group["id"]],
            "yaml": "version: '3'\n\nservices:  \n  my-service:\n    # enter your application details...\n\nvolumes:\n",
        }
        applications = authenticated_client.get("/applications")
        len_applications_before = len(applications.json())

        response = authenticated_client.post("/applications", json=data)

        applications = authenticated_client.get("/applications")
        len_applications_after = len(applications.json())

        assert (
            response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        ), "Should not create application"

        assert len_applications_after == len_applications_before


class TestGetApplication:
    def test_get_all_applications(
        self, authenticated_client: TestClient, test_application
    ):

        response = authenticated_client.get("/applications")

        assert response.status_code == HTTP_200_OK, "Could not get applications"

        applications = response.json()

        assert len(applications) == 1
        assert applications[0]["id"] == test_application.id
        assert applications[0]["name"] == test_application.name

    def test_get_application_by_id(
        self, authenticated_client: TestClient, test_application
    ):

        response = authenticated_client.get(f"/applications/{test_application.id}")

        assert response.status_code == HTTP_200_OK, "Could not get application"

        application = response.json()

        assert application["id"] == test_application.id
        assert application["name"] == test_application.name

    def test_get_application_by_wrong_id(
        self, authenticated_client: TestClient, test_application
    ):
        response = authenticated_client.get("/applications/-10")

        assert response.status_code == HTTP_404_NOT_FOUND, "Should not get application"


class TestUpdateApplication:
    def test_update_application(
        self, authenticated_client: TestClient, test_application, test_edge_group
    ):

        data = {
            "name": "Test-Application-3",
            "group_ids": [test_edge_group["id"]],
            "yaml": "Updated content",
        }

        response = authenticated_client.put(
            f"/applications/{test_application.id}", json=data
        )

        assert response.status_code == HTTP_200_OK, "Could not update application"

        application = response.json()

        assert application["id"] == test_application.id
        assert application["yaml"] == "Updated content"
        assert (
            application["name"] == "Test-Application"
        ), "Should not be able to change application name"

    def test_update_application_wrong_application_id(
        self, authenticated_client: TestClient, test_application, test_edge_group
    ):

        data = {
            "name": "Test-Application-3",
            "group_ids": [test_edge_group["id"]],
            "yaml": "Updated content",
        }

        response = authenticated_client.put("/applications/-10", json=data)

        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Should not update application"

    def test_update_application_wrong_edge_group_id(
        self, authenticated_client: TestClient, test_application, test_edge_group
    ):

        data = {
            "name": "Test-Application-3",
            "group_ids": [test_edge_group["id"] + 1],
            "yaml": "Updated content",
        }

        response = authenticated_client.put(
            f"/applications/{test_application.id}", json=data
        )

        assert (
            response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        ), "Should not update application"


class TestDeleteApplication:
    def test_delete_application(
        self, authenticated_client: TestClient, test_application
    ):
        applications = authenticated_client.get("/applications")
        len_applications_before = len(applications.json())

        response = authenticated_client.delete(f"/applications/{test_application.id}")

        applications = authenticated_client.get("/applications")
        len_applications_after = len(applications.json())

        assert (
            response.status_code == HTTP_204_NO_CONTENT
        ), "Could not delete application"
        assert len_applications_before - 1 == len_applications_after

    def test_delete_application_wrong_id(
        self, authenticated_client: TestClient, test_application
    ):
        applications = authenticated_client.get("/applications")
        len_applications_before = len(applications.json())

        response = authenticated_client.delete(f"/applications/-10")

        applications = authenticated_client.get("/applications")
        len_applications_after = len(applications.json())

        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Should not delete application"
        assert len_applications_before == len_applications_after
