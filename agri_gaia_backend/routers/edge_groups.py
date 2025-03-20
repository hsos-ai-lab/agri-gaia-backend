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

from fastapi import APIRouter, status, Response
from agri_gaia_backend.schemas.edge_group import EdgeGroupCreate

import logging

logger = logging.getLogger("api-logger")

from agri_gaia_backend.services.portainer.portainer_api import portainer

ROOT_PATH = "/edge-groups"
router = APIRouter(prefix=ROOT_PATH)


@router.get("")
def get_all_edge_groups():
    groups = portainer.get_all_edge_groups()

    return [
        {
            "id": g["Id"],
            "name": g["Name"],
            "tagIds": g["TagIds"],
            "inUse": g["HasEdgeStack"],
            "deviceCount": len(g["Endpoints"]),
        }
        for g in groups
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_edge_group(edge_group_create: EdgeGroupCreate):
    group = portainer.create_edge_group(
        edge_group_create.name, edge_group_create.tag_ids
    )
    return Response()


@router.delete("/{edge_group_id}")
def delete_edge_group(edge_group_id: int):
    portainer.delete_edge_group(edge_group_id)
    return Response(status_code=204)
