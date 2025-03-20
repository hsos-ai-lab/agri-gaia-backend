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
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from agri_gaia_backend import schemas
from agri_gaia_backend.db import edge_device_api


class TestCreateEdgeDevice:
    def test_create_edge_device(self, testclient: TestClient, db: Session):
        data = {"name": "Test-Edge-Device", "tags": []}  # no tags
        num_edge_devices_before = len(edge_device_api.get_edge_devices(db))
        response = testclient.post("/edge-devices", json=data)

        print(response.text)
        assert response.status_code == HTTP_201_CREATED, "Could not create edge device"

        assert (
            len(edge_device_api.get_edge_devices(db)) == num_edge_devices_before + 1
        ), "Edge device was not created"

    def test_create_edge_device_without_name(self, testclient: TestClient, db: Session):
        data = {}
        num_edge_devices_before = len(edge_device_api.get_edge_devices(db))
        response = testclient.post("/edge-devices", json=data)

        print(response.text)
        assert (
            response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
        ), "Edge device should not be able to be processed"

        assert (
            len(edge_device_api.get_edge_devices(db)) == num_edge_devices_before
        ), "Edge device was created"


class TestEdgeDeviceDeployments:
    def test_get_edge_device_deployments(
        self, testclient: TestClient, test_edge_device: schemas.EdgeDevice
    ):
        response = testclient.get(f"/edge-devices/{test_edge_device.id}/deployments")

        assert (
            response.status_code == HTTP_200_OK
        ), "Error checking Edge Device deployment"


class TestGetEdgeDevices:
    def test_get_all_edge_devices(
        self, testclient: TestClient, test_edge_device: schemas.EdgeDevice
    ):
        response = testclient.get("/edge-devices")
        edge_devices = response.json()
        assert response.status_code == HTTP_200_OK, "Error getting edge devices"
        filtered_edge_devices = [
            d for d in edge_devices if d["id"] == test_edge_device.id
        ]
        assert (
            len(filtered_edge_devices) == 1
        ), "Test Edge Device is not in the returned edge devices (or too many with the same id)"
        returned_edge_device = schemas.EdgeDevice(**filtered_edge_devices[0])

        print(returned_edge_device)
        print(test_edge_device)

        assert (
            returned_edge_device == test_edge_device
        ), "Filtered test device is not test_edge_device"

    def test_get_single_edge_device(
        self, testclient: TestClient, test_edge_device: schemas.EdgeDevice
    ):
        response = testclient.get(f"/edge-devices/{test_edge_device.id}")
        edge_device = schemas.EdgeDevice(**response.json())
        assert response.status_code == HTTP_200_OK, "Error getting edge device"
        assert (
            edge_device.name == test_edge_device.name
        ), "Edge device is not the test edge device"

    def test_get_edge_device_incorrect_id(self, testclient: TestClient, db: Session):
        response = testclient.get(f"/edge-devices/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Edge device shouldn't have been returned"


class TestEdgeDeviceDelete:
    # filter the CleanupError
    @pytest.mark.filterwarnings("ignore:CleanupError")
    def test_delete_edge_device(
        self,
        testclient: TestClient,
        test_edge_device: schemas.EdgeDevice,
        db: Session,
    ):
        assert (
            edge_device_api.get_edge_device(db, test_edge_device.id) is not None
        ), "Precondition for delete edge device test failed, edge device is not in DB"

        response = testclient.delete(f"/edge-devices/{test_edge_device.id}")
        assert response.status_code == HTTP_204_NO_CONTENT, "Error deleting edge device"

        assert (
            edge_device_api.get_edge_device(db, test_edge_device.id) is None
        ), "Error deleting edge device"

    def test_delete_edge_device_incorrect_id(
        self,
        testclient: TestClient,
        test_edge_device: schemas.EdgeDevice,
        db: Session,
    ):
        assert (
            edge_device_api.get_edge_device(db, test_edge_device.id) is not None
        ), "Precondition for delete edge device test failed, edge device is not in DB"

        response = testclient.delete(f"/edge-devices/-10")
        print(response.text)
        # möglicherweise irgendwo den Fehler abfangen?
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Wrong status code when trying to delete wrong edge device"

        assert (
            edge_device_api.get_edge_device(db, test_edge_device.id) is not None
        ), "Edge Device shouldn't have been deleted"
