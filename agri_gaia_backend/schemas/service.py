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

import datetime

from typing import Optional
from pydantic import BaseModel


class ServiceBase(BaseModel):
    name: str
    public: Optional[bool]
    owner: str
    last_modified: datetime.datetime
    metadata_uri: Optional[str]
    bucket_name: str


class Service(ServiceBase):
    id: int

    class Config:
        orm_mode = True
