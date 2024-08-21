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

from fastapi import APIRouter

import logging

logger = logging.getLogger("api-logger")

from agri_gaia_backend.services.portainer.portainer_api import portainer

ROOT_PATH = "/tags"
router = APIRouter(prefix=ROOT_PATH)


@router.get("")
def get_all_tags():
    tags = portainer.get_tags()

    return [{"id": t["ID"], "name": t["Name"]} for t in tags]
