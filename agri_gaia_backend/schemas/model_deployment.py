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

from typing import Optional
import datetime
from pydantic import BaseModel

from agri_gaia_backend.db.models import ModelDeploymentStatus, DeploymentType


class ModelDeploymentBase(BaseModel):
    type: DeploymentType
    model_id: int
    edge_device_id: Optional[int]
    status: ModelDeploymentStatus


class ModelDeploymentCreate(ModelDeploymentBase):
    pass


class ModelDeployment(ModelDeploymentBase):
    id: int
    creation_date: datetime.datetime

    class Config:
        orm_mode = True
