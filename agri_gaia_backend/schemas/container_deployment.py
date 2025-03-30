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
import datetime
from pydantic import BaseModel, Field

from agri_gaia_backend.db.models import ContainerDeploymentStatus, PortBindingProtocol
from agri_gaia_backend.schemas.container_image import ContainerImage


class PortBinding(BaseModel):
    host_port: int
    container_port: int
    protocol: PortBindingProtocol

    class Config:
        from_attributes = True
        populate_by_name = True


class ContainerDeploymentBase(BaseModel):
    edge_device_id: int
    container_image_id: int
    port_bindings: List[PortBinding] = None
    name: str
    # network
    # env


class ContainerDeploymentCreate(ContainerDeploymentBase):
    pass


class ContainerDeployment(ContainerDeploymentBase):
    id: int
    creation_date: datetime.datetime
    status: ContainerDeploymentStatus
    container_image: ContainerImage
    # the id docker gives the started container
    # we need this to manage it later (e. g. stop)
    docker_container_id: Optional[str] = None

    class Config:
        from_attributes = True
