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

from pydantic import BaseModel
from typing import Dict, Optional


class Fieldborder(BaseModel):
    gid: int
    polygon: Dict[str, object]
    schlagnr: Optional[int]
    flik: Optional[str]
    nrle: Optional[int]
    flek: Optional[str]
    akt_fl: Optional[float]
    antjahr: Optional[int]
    kc_festg: Optional[str]
    tsbez: Optional[str]
    typ_le: Optional[str]

    class Config:
        orm_mode = True
