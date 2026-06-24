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
    """A single agricultural field parcel with its geometry and LPIS/InVeKoS metadata.

    Attributes:
        gid: Unique geometry/feature ID (e.g. the PostGIS row identifier).
        polygon: The parcel boundary geometry, as a GeoJSON-like mapping.
        schlagnr: Schlagnummer — the field/parcel number.
        flik: Feldblock-Identifikator (FLIK) — the LPIS field-block identifier.
        nrle: Nummer des Landschaftselements — number/ID of the landscape
            element (Landschaftselement) within or adjacent to the parcel.
        flek: Identifier of the landscape element (the LE counterpart to FLIK).
        akt_fl: Aktuelle Fläche — the parcel's current area, typically in hectares.
        antjahr: Antragsjahr — the subsidy application year this record belongs to.
        kc_festg: Festgestellter Kulturcode — the determined/verified crop ("culture") code.
        tsbez: Teilschlagbezeichnung — label/designation of the sub-parcel (Teilschlag).
        typ_le: Typ des Landschaftselements — the type/category of the landscape element.
    """
    
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
