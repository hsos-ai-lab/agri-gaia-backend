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

import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from agri_gaia_backend.services.portainer.portainer_api import portainer


class TestCreateEdgeGroup:
    def test_create_edge_group(
        self, authenticated_client: TestClient, test_edge_device, test_edge_group
    ):
        tag_ids = portainer.get_ids_for_tag_names(
            test_edge_device.tags, allow_create=True
        )
        data = {"name": "Test-Edge-Group-2", "tag_ids": tag_ids}
        response = authenticated_client.post("/edge-groups", json=data)

        assert response.status_code == HTTP_200_OK, "Could not create edge group"

        response = authenticated_client.get("/edge-groups")
        edge_groups = response.json()
        assert len(edge_groups) == 2

        assert edge_groups[1]["name"] == "Test-Edge-Group-2"

    def test_create_edge_group_with_existing_name(
        self, authenticated_client: TestClient, test_edge_device, test_edge_group
    ):
        tag_ids = portainer.get_ids_for_tag_names(
            test_edge_device.tags, allow_create=True
        )
        data = {"name": test_edge_group["name"], "tag_ids": tag_ids}
        response = authenticated_client.post("/edge-groups", json=data)

        assert (
            response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        ), "Should not create edge group"


class TestGetEdgeGroups:
    def test_get_all_edge_groups(
        self, authenticated_client: TestClient, test_edge_group
    ):
        response = authenticated_client.get("/edge-groups")
        assert response.status_code == HTTP_200_OK, "Could not get edge groups"

        edge_groups = response.json()
        assert len(edge_groups) == 1
        edge_group = edge_groups[0]

        assert edge_group["id"] == test_edge_group["id"]
        assert edge_group["name"] == test_edge_group["name"]
        assert edge_group["tagIds"] == test_edge_group["tagIds"]
        assert edge_group["deviceCount"] == 1


class TestDeleteEdgeGroup:
    def test_delete_edge_group(self, authenticated_client: TestClient, test_edge_group):
        test_edge_group_id = test_edge_group["id"]
        response = authenticated_client.delete(f"/edge-groups/{test_edge_group_id}")
        assert (
            response.status_code == HTTP_204_NO_CONTENT
        ), "Could not delete edge group"

        response = authenticated_client.get("/edge-groups")
        edge_groups = response.json()
        assert len(edge_groups) == 0

    def test_delete_edge_group_with_wrong_id(
        self, authenticated_client: TestClient, test_edge_group
    ):
        response = authenticated_client.delete("/edge-groups/-10")
        assert (
            response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        ), "Should not delete edge group"
