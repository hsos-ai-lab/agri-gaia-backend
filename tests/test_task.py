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

import pytest
import time
import requests
from fastapi.testclient import TestClient
from agri_gaia_backend import schemas
from agri_gaia_backend.db import tasks_api

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_202_ACCEPTED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)


class TestGetTask:
    def test_get_all_tasks(self, testclient: TestClient, test_task):
        response = testclient.get("/tasks")

        tasks = response.json()
        filtered_task = [t for t in tasks if t["id"] == test_task.id]

        assert response.status_code == HTTP_200_OK, "Error getting Task"
        assert (
            len(filtered_task) == 1
        ), "Test_task is not in the returned tasks (or too many with the same id)"
        returned_task = schemas.Task(**filtered_task[0])

        assert (
            returned_task.id == test_task.id
        ), "Returned task does not have same id as test_task"
        assert (
            returned_task.creation_date == test_task.creation_date
        ), "Returned task does not have same creation_date as test_task"
        assert (
            returned_task.initiator == test_task.initiator
        ), "Returned task does not have same initiator as test_task"
        assert (
            returned_task.title == test_task.title
        ), "Returned task does not have same title as test_task"

    def test_get_single_task(self, testclient: TestClient, test_task):
        response = testclient.get(f"/tasks/{test_task.id}")

        task = response.json()

        assert response.status_code == HTTP_200_OK, "Error getting Task"
        task = schemas.Task(**task)

        assert (
            task.id == test_task.id
        ), "Returned task does not have same id as test_task"
        assert (
            task.creation_date == test_task.creation_date
        ), "Returned task does not have same creation_date as test_task"
        assert (
            task.initiator == test_task.initiator
        ), "Returned task does not have same initiator as test_task"
        assert (
            task.title == test_task.title
        ), "Returned task does not have same title as test_task"

    def test_get_single_task_wrong_id(self, testclient: TestClient, test_task):
        response = testclient.get("/tasks/-10")
        assert (
            response.status_code == HTTP_404_NOT_FOUND
        ), "Task shouldn't have been returned"


class TestDeleteTask:
    def test_delete_task(
        self,
        testclient: TestClient,
        test_task,
        db,
    ):
        assert (
            tasks_api.get_task(db, test_task.id) is not None
        ), "Precondition for delete task test failed, task is not in DB"

        response = testclient.delete(f"/tasks/{test_task.id}")
        assert response.status_code == HTTP_204_NO_CONTENT, "Error deleting task"

        assert tasks_api.get_task(db, test_task.id) is None, "Task was not deleted"

    def test_delete_task_wrong_id(
        self,
        testclient: TestClient,
        test_task,
        db,
    ):
        tasks_count = len(tasks_api.get_tasks(db))

        assert tasks_count >= 1, "There should be at least one Task in DB"

        response = testclient.delete(f"/tasks/-10")
        assert response.status_code == HTTP_404_NOT_FOUND, "Wrong ID was found"

        tasks_count_after = len(tasks_api.get_tasks(db))

        assert tasks_count == tasks_count_after, "No Task should have been deleted"
