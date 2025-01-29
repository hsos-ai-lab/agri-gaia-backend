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

from typing import Optional, List
import datetime
from pydantic import BaseModel

from agri_gaia_backend.schemas.container_deployment import ContainerDeployment


class EdgeDeviceBase(BaseModel):
    name: str


class EdgeDeviceCreate(EdgeDeviceBase):
    tags: Optional[List[str]] = None


class EdgeDevice(EdgeDeviceBase):
    id: int
    arch: Optional[str] = None
    portainer_id: Optional[int] = None
    os: Optional[str] = None
    cpu_count: Optional[int] = None
    arch: Optional[str] = None
    memory: Optional[int] = None
    tags: Optional[List[str]] = None
    last_heartbeat: Optional[datetime.datetime] = None
    registered: bool
    edge_key: str
    container_deployments: List[ContainerDeployment]

    class Config:
        from_attributes = True
