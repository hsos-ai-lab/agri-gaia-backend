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

import logging
from typing import Set

from agri_gaia_backend.services.graph.sparql_operations import util as sparql_util
from fastapi import APIRouter

ROOT_PATH = "/geonames"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


@router.get("/locations")
def get_geonames_locations() -> Set[str]:
    return sorted(sparql_util.get_possible_locations())


@router.get("/locations/{location}/check")
def check_location(location: str):
    uri = sparql_util.check_location(location)
    return {"name": location, "concept": uri}
