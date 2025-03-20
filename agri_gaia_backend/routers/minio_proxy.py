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

from typing import Dict
import logging

from fastapi import APIRouter, Request
from urllib.parse import unquote

from agri_gaia_backend.schemas.keycloak_user import KeycloakUser

from agri_gaia_backend.services import minio_api

logger = logging.getLogger("api-logger")
router = APIRouter(prefix="/minio-proxy")


@router.get("/files")
def get_filetree(request: Request, prefix: str = "") -> Dict:
    user: KeycloakUser = request.user
    paths = []
    response = minio_api.get_all_objects(
        user.minio_bucket_name,
        prefix=prefix,
        token=user.minio_token,
    )
    for item in response:
        paths.append(item.object_name)

    out = {"name": user.minio_bucket_name, "path": "", "children": []}
    for item in paths:
        items = item.split("/")
        _add_items(out, items, out["path"])

    return out


# helper function
def _add_items(d, items, path):
    if len(items) == 1:
        if items[0] in d:
            return
        else:
            item = {"name": items[0], "path": path + items[0]}
            d["children"].append(item)
    else:
        index = next(
            (i for i, obj in enumerate(d["children"]) if obj["name"] == items[0]), -1
        )
        if index == -1:
            item = {"name": items[0], "path": path + items[0] + "/", "children": []}
            d["children"].append(item)
        _add_items(d["children"][index], items[1:], d["children"][index]["path"])


# returns a single file from minIO at the given path
@router.get("/file/{file_path:path}")
def get_file(request: Request, file_path: str):
    user: KeycloakUser = request.user
    response = minio_api.get_object(
        user.minio_bucket_name,
        object_name=unquote(file_path),
        token=user.minio_token,
    ).read()

    logger.info(type(response))
    logger.info(response)

    return response
