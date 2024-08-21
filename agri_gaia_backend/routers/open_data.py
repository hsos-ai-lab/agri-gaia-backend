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

import json
import logging

from typing import List
from fastapi import APIRouter
from agri_gaia_backend.services.postgis.postgis_api import postgis
from agri_gaia_backend.schemas.fieldborder import Fieldborder

logger = logging.getLogger("api-logger")
router = APIRouter(prefix="/open-data")


@router.get("/geo/fieldborders", response_model=List[Fieldborder])
async def fieldborders(nwlat: float, nwlng: float, selat: float, selng: float):
    fieldborders = postgis.get_fieldborders(
        north_west_lat_lng_bounds=(nwlat, nwlng),
        south_east_lat_lng_bounds=(selat, selng),
    )

    # GeoJson from PostGIS is already in json format
    # FastAPI will re-encode it, resulting in double encoded json
    # Workaround: deserialize here before serializing whole respone model
    for f in fieldborders:
        f.polygon = json.loads(f.polygon)

    return fieldborders
