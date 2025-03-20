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

import datetime
from typing import Optional
from pydantic import BaseModel
from agri_gaia_backend.db.models import TaskStatus


class Task(BaseModel):
    id: int
    initiator: str
    title: Optional[str] = None
    creation_date: datetime.datetime
    status: TaskStatus
    completion_percentage: float
    message: Optional[str] = None

    class Config:
        from_attributes = True
