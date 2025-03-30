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
    schlagnr: Optional[int] = None
    flik: Optional[str] = None
    nrle: Optional[int] = None
    flek: Optional[str] = None
    akt_fl: Optional[float] = None
    antjahr: Optional[int] = None
    kc_festg: Optional[str] = None
    tsbez: Optional[str] = None
    typ_le: Optional[str] = None

    class Config:
        from_attributes = True
