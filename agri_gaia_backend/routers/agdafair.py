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

import logging
import json
from fastapi import (
    APIRouter,
    Request,
)
from agri_gaia_backend.services.graph.sparql_operations import util as sparql_util
import gitlab
import base64


ROOT_PATH = "/agdafair"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)

toBeRemoved= "https://gitdev.nfdi4plants.org/api/v4/projects/"

@router.get("/test")
def heartbeat():
    return {"message":"Service alive!"}

@router.post("/import")
async def homepage(request: Request):
    body_bytes = await request.body()
    body_str = body_bytes.decode()
    logger.info(f"raw_body: {body_str}")

    bodyJson = json.loads(body_str)

    gl = gitlab.Gitlab(bodyJson["package_endpoint"], private_token=bodyJson["gitlab_token"])
    project = gl.projects.get(bodyJson["project_id"])

    logger.info(project.name)

    fileLocation= bodyJson["ro_crate_url"].removeprefix(toBeRemoved).split("/", 1)[1]

    logger.info(fileLocation)

    f = project.files.get(file_path=fileLocation, ref='main')
    #f = project.files.get(file_path='arc-ro-crate-metadata.json', ref='main')
    file_content = base64.b64decode(f.content).decode('utf-8')
    logger.info(file_content)

    content = json.loads(file_content)
    for object in content["@graph"]:
        if object["@id"] == "./":
            sparql_util.createFusekiDataset(object["name"].replace(" ", ""))
            sparql_util.store_json(file_content, object["name"].replace(" ", ""))

    # do some backend stuff
    # eventually return a JSON with a 'follow_me' to a URL that the auth service redirects to.
    # foo is a just an example GET parameter that can be sent, i.e., session ids or other stateful information.
    return {"message": "Data imported!"}
