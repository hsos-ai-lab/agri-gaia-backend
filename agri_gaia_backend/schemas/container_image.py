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

from __future__ import annotations
import datetime

from typing import Optional, List
from pydantic import BaseModel, root_validator
from enum import Enum


class ContainerImage(BaseModel):
    repository: str
    tag: str
    platform: Optional[str]
    exposed_ports: Optional[List[str]]
    id: Optional[int]
    owner: Optional[str]
    last_modified: Optional[datetime.datetime]
    model_id: Optional[int]
    metadata_uri: Optional[str]
    compressed_image_size: Optional[int]

    class Config:
        orm_mode = True


class ContainerImageBuildConfig(BaseModel):
    container_template_id: int
    repository: str
    tag: str
    model_id: int
    architecture: Optional[str] = None
    edge_device_id: Optional[int] = None

    @root_validator
    def check_architecture_or_edge_device_id_set(cls, values):
        architecture = values.get("architecture")
        edge_device_id = values.get("edge_device_id")
        if architecture is None and edge_device_id is None:
            raise ValueError("One of 'architecture' and 'edge_device_id' must be set")
        if architecture is not None and edge_device_id is not None:
            raise ValueError(
                "Only one of 'architecture' and 'edge_device_id' can be set"
            )
        return values
