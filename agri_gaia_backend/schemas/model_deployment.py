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

from typing import Optional
import datetime
from pydantic import BaseModel

from agri_gaia_backend.db.models import ModelDeploymentStatus, DeploymentType


class ModelDeploymentBase(BaseModel):
    type: DeploymentType
    model_id: int
    edge_device_id: Optional[int] = None
    status: ModelDeploymentStatus

    class Config:
        protected_namespaces = ()


class ModelDeploymentCreate(ModelDeploymentBase):
    pass


class ModelDeployment(ModelDeploymentBase):
    id: int
    creation_date: datetime.datetime

    class Config:
        from_attributes = True
        protected_namespaces = ()
