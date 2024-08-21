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

from typing import List
from pydantic import BaseModel

class ConnectorBase(BaseModel):
    name: str
    description: str
    data_url: str
    ids_url: str
    minio_url: str
    api_key: str

class Connector(ConnectorBase):
    id: int

    class Config:
        orm_mode = True
