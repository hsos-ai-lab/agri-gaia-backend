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

from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)

from agri_gaia_backend.routers.common import (
    check_exists,
    get_db,
)
from agri_gaia_backend.db import tasks_api
from agri_gaia_backend import schemas
from agri_gaia_backend.routers.paths import TASKS_ROOT_PATH
from sqlalchemy.orm import Session

import logging

logger = logging.getLogger("api-logger")

router = APIRouter(prefix=TASKS_ROOT_PATH)


@router.get("", response_model=List[schemas.Task])
async def get_tasks(
    initiator: str = None,
    skip: int = 0,
    limit: int = 100,
    id: Optional[List[int]] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Fetches database for background tasks of the backend.

    Args:
        skip: How many task entries shall be skipped. Defaults to 0.
        limit: What is the maximum number of tasks to be fetched? defaults to 100.
        db: Database Session. Created automatically.

    Returns:
        A list of tasks
    """
    if initiator:
        return tasks_api.get_tasks_by_initiator(db, initiator, skip, limit)
    return tasks_api.get_tasks(db, skip, limit, id)


@router.get("/{task_id}", response_model=schemas.Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    Fetches the database for the task with the given task_id

    Args:
        task_id: the id of the task that shall be fetched
        db: Database Session: Created automatically

    Returns:
        The task with the given id
    """
    return check_exists(tasks_api.get_task(db, task_id))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Deletes the Task in the database

    Args:
        task_id: the id of the task that shall be deleted
        db: Database Session: Created automatically

    Returns:
        204 if success, 500 otherwise
    """
    task = check_exists(tasks_api.get_task(db, task_id))
    success = tasks_api.delete_task(db, task)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting task",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
