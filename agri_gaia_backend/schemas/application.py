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

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ApplicationBase(BaseModel):
    name: str
    yaml: str


class ApplicationCreate(ApplicationBase):
    group_ids: List[int]


class ApplicationUpdate(BaseModel):
    group_ids: List[int]
    yaml: str


class Application(ApplicationBase):
    id: int
    last_modified: datetime
    portainer_edge_stack_id: int
    portainer_edge_group_ids: List[int]
    status: Optional[object] = None

    class Config:
        from_attributes = True
