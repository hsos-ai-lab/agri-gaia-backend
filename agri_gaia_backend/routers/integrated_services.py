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

from fastapi import APIRouter, Response, Request, HTTPException, Form, Depends
from datetime import datetime
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.schemas.service import Service
from agri_gaia_backend.db import services_api as sql_api
from agri_gaia_backend.db import models
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.schemas.service_input import ServiceInput
from agri_gaia_backend.routers.common import get_db, check_exists
from agri_gaia_backend.util.common import get_stacktrace
from agri_gaia_backend.routers import common
from agri_gaia_backend.services.graph.sparql_operations import util as sparql_util
from agri_gaia_backend.services.edc.connector import (
    create_catalog_entry_service,
    delete_catalog_entry_service,
)
from agri_gaia_backend.services.graph.sparql_operations import (
    services as sparql_services_api,
)
from agri_gaia_backend.services.minio_api import MINIO_ENDPOINT

import json
import yaml
from datetime import datetime
import requests

from openapi_spec_validator import validate_spec

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from typing import List, Optional
import io
import jsonref
import requests
import logging
import json
import time
import yaml
from urllib.parse import urlparse
from urllib.parse import unquote
from mimetypes import guess_extension

logger = logging.getLogger("api-logger")

ROOT_PATH = "/integrated-services"
router = APIRouter(prefix=ROOT_PATH)


# Returns a list of all service names registered in the platform
@router.get("", response_model=List[Service])
def get_all_services(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
    return sql_api.get_services(skip=skip, limit=limit, db=db)


# returns a single file from minIO at the given path
@router.get("/file/{file_path}")
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


# returns a dict of all filenames in the users MinIO, ordered in a tree structure
@router.get("/files")
def get_all_files(request: Request):
    user: KeycloakUser = request.user
    paths = []
    response = minio_api.get_all_objects(
        user.minio_bucket_name,
        prefix="services",
        token=user.minio_token,
    )
    for item in response:
        paths.append(item.object_name)

    out = {"name": user.minio_bucket_name, "path": "", "children": []}
    for item in paths:
        items = item.split("/")
        add_items(out, items, out["path"])

    return out


# helper function for get:files
def add_items(d, items, path):
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
        add_items(d["children"][index], items[1:], d["children"][index]["path"])


# returns the openapi document of a given service. May be altered to include examples from previous calls and only contains information for the given request/operation
@router.get("/{service_name}/{service_path}/{requestType}/inputs")
def get_service_inputs(
    uri: str,
    service_name: str,
    request: Request,
    service_path: int,
    requestType: str,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10000,
):
    # Getting the "Owner" of the Service, aka the bucket name in which the file exists
    service: models.Service = check_exists(
        sql_api.get_service_by_name(db=db, name=service_name)[0]
    )

    # Looking up the correct filename for the service definition, needs to be done to account for Upper/Lowercase Filenames
    user: KeycloakUser = request.user
    name = minio_api.get_all_objects(
        service.bucket_name,
        prefix="services/definitions/" + service_name + "/",
        token=user.minio_token,
    )[0].object_name

    # Loading the actual openapi definition of the chosen api
    response = minio_api.get_object(
        bucket=service.bucket_name, object_name=name, token=user.minio_token
    )
    jsonData = jsonref.loads(response.read().decode())
    service_path = list(jsonData["paths"].keys())[service_path]

    """
    fileEnum = []
    for item in minio_api.get_all_objects(
        user.minio_bucket_name,
        prefix="services/" + service_name.split(".")[0],
        token=user.minio_token,
    ):
        if item.object_name.split("/")[-1] not in {"input.json", "output.json"}:
            fileEnum.append(
                {"name": item.object_name.split("/")[-1], "value": item.object_name}
            )
    """

    # setting new example values if there is a history call given
    if uri != "new":
        template = minio_api.get_object(
            user.minio_bucket_name,
            object_name="services/"
            + service_name.split(".")[0]
            + service_path
            + "/"
            + requestType
            + "/"
            + uri
            + "/input.json",
            token=user.minio_token,
        ).data.decode()
        template = jsonref.loads(template)
        operationData = jsonData["paths"][service_path][requestType]
        if "parameters" in operationData:
            for idx, parameter in enumerate(operationData["parameters"]):
                if parameter["name"] in template:
                    operationData["parameters"][idx]["example"] = template[
                        parameter["name"]
                    ]
                else:
                    if "example" in operationData["parameters"][idx]:
                        del operationData["parameters"][idx]["example"]
                logger.info(operationData["parameters"][idx])
        jsonData["paths"][service_path][requestType] = operationData

    # deleting all other paths from the openapi doc so only the chosen request will be shown
    for path in list(jsonData["paths"]):
        if path != service_path:
            del jsonData["paths"][path]
        else:
            for request in list(jsonData["paths"][path]):
                if request != requestType:
                    del jsonData["paths"][path][request]

    return jsonData


# returns the original openapi doc of a given service
@router.get("/{service_name}/openapi")
def get_service_openapi(
    request: Request, service_name: str, db: Session = Depends(get_db)
):
    # Getting the "Owner" of the Service, aka the bucket name in which the file exists
    service: models.Service = check_exists(
        sql_api.get_service_by_name(db=db, name=service_name)[0]
    )

    user: KeycloakUser = request.user
    name = minio_api.get_all_objects(
        service.bucket_name,
        prefix="services/definitions/" + service_name + "/",
        token=user.minio_token,
    )[0].object_name

    jsonData = jsonref.loads(
        minio_api.get_object(
            bucket=service.bucket_name, object_name=name, token=user.minio_token
        )
        .read()
        .decode("utf-8")
    )

    return jsonData


# handles the response of a service call
@router.post("/{service_name}/{requestType}/response")
async def handle_response(
    request: Request,
    service_name: str,
    requestType: str,
    body: bytes = Form(...),
    contentType: Optional[str] = Form(None),
    requestURL: str = Form(...),
):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # saving all query parameters so they can be written to the input.json file
    url = unquote(requestURL)
    requestInput = {}
    query = urlparse(url).query
    # TODO: handle Path parameters
    path = urlparse(url).path
    if query:
        query = query.split("&")
        logger.info(query)
        for query in query:
            name, value = query.split("=")
            values = value.split(",")
            if len(values) == 1:
                requestInput[name] = values[0]
            else:
                requestInput[name] = values
    logger.info(requestInput)

    # saving all files from the request body to MinIO
    user: KeycloakUser = request.user
    token = user.minio_token
    bucket = user.minio_bucket_name
    try:
        formData = await request.form()
        for item in formData.items():
            # TODO: currently only handling Body as Files
            # logger.info(type(item[1]))
            if not isinstance(item[1], str) or not isinstance(item[1], bytes):
                minio_api.upload_data(
                    bucket,
                    prefix="services/"
                    + service_name
                    + urlparse(url).path
                    + "/"
                    + requestType
                    + "/"
                    + time,
                    token=token,
                    data=item[1].file,
                    objectname=item[1].filename,
                    content_type=item[1].content_type,
                )
                requestInput[item[0]] = item[1].filename
    except Exception as e:
        logger.exception(e)

    # saving input and output of the call to MinIO
    try:
        minio_api.upload_data(
            bucket,
            prefix="services/"
            + service_name
            + urlparse(url).path
            + "/"
            + requestType
            + "/"
            + time,
            token=token,
            data=json.dumps(requestInput).encode("utf-8"),
            objectname="input.json",
        )

        minio_api.upload_data(
            bucket,
            prefix="services/"
            + service_name
            + urlparse(url).path
            + "/"
            + requestType
            + "/"
            + time,
            token=token,
            data=body,
            objectname="output"
            + guess_extension(contentType.partition(";")[0].strip()),
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500, detail="Response Data could not be uploaded to MinIO"
        )

    return (
        "services/"
        + service_name
        + urlparse(requestURL).path
        + "/"
        + requestType
        + "/"
        + time
    )


# returns the general information for a service
@router.get("/{service_name}/info")
def get_service_info(
    request: Request, service_name: str, db: Session = Depends(get_db)
):
    # Getting the "Owner" of the Service, aka the bucket name in which the file exists
    service: models.Service = check_exists(
        sql_api.get_service_by_name(db=db, name=service_name)[0]
    )

    user: KeycloakUser = request.user
    name = minio_api.get_all_objects(
        service.bucket_name,
        prefix="services/definitions/" + service_name + "/",
        token=user.minio_token,
    )[0].object_name

    jsonData = jsonref.loads(
        minio_api.get_object(
            bucket=service.bucket_name, object_name=name, token=user.minio_token
        )
        .read()
        .decode("utf-8")
    )

    response = {}

    helper_operations = []
    helper_paths = []
    paths = list(jsonData["paths"].keys())
    for path in paths:
        operations = list(jsonData["paths"][path].keys())
        for operation in operations:
            helper_operations.append(operation)
            helper_paths.append(path)
    response["paths"] = helper_paths
    response["operations"] = helper_operations

    response["description"] = jsonData["info"]["description"]
    if "contact" in jsonData["info"]:
        for key in jsonData["info"]["contact"].keys():
            response[key] = jsonData["info"]["contact"][key]

    return response


# returns the specific information and call history for an endpoint of a service
@router.get("/{service_name}/{service_path}/{operation}/info")
def get_service_info(
    request: Request,
    service_name: str,
    service_path: int,
    operation: str,
    db: Session = Depends(get_db),
):
    # Getting the "Owner" of the Service, aka the bucket name in which the file exists
    service: models.Service = check_exists(
        sql_api.get_service_by_name(db=db, name=service_name)[0]
    )

    response = {}
    user: KeycloakUser = request.user
    name = minio_api.get_all_objects(
        service.bucket_name,
        prefix="services/definitions/" + service_name + "/",
        token=user.minio_token,
    )[0].object_name

    jsonData = jsonref.loads(
        minio_api.get_object(
            bucket=service.bucket_name, object_name=name, token=user.minio_token
        )
        .read()
        .decode("utf-8")
    )

    helper_operations = []
    helper_paths = []
    paths = list(jsonData["paths"].keys())
    for path in paths:
        operations = list(jsonData["paths"][path].keys())
        for operation in operations:
            helper_operations.append(operation)
            helper_paths.append(path)
    response["paths"] = helper_paths
    response["operations"] = helper_operations

    service_path = list(jsonData["paths"].keys())[service_path]
    response["description"] = jsonData["paths"][service_path][operation]["description"]

    if "contact" in jsonData["info"]:
        for key in jsonData["info"]["contact"].keys():
            response[key] = jsonData["info"]["contact"][key]

    history = []
    for item in minio_api.get_all_objects(
        user.minio_bucket_name,
        prefix="services/"
        + service_name.split(".")[0]
        + service_path
        + "/"
        + operation,
        token=user.minio_token,
    ):
        if item.object_name.split("/")[-1] == "input.json":
            history.append(item.object_name.split("/")[-2])
    history.reverse()

    response["history"] = history

    logger.info(response)
    return response


@router.post("/uploadService")
def upload_service(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
    link: Optional[str] = Form(None),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user: KeycloakUser = request.user
    token = user.minio_token
    bucket = user.minio_bucket_name

    created_service = _create_initial_entry_postgres(
        db=db,
        user=user,
        service_name=name,
    )

    try:
        if link != None:
            response = requests.get(url=link)
            if link.rsplit(".")[-1] == "yaml" or link.rsplit(".")[-1] == "yml":
                jsonData = yaml.safe_load(bytes(response.text, "utf-8"))
            else:
                jsonData = jsonref.loads(bytes(response.text, "utf-8"))
            logger.info(jsonData)
        elif files != None:
            filetype = files[0].filename.rsplit(".")[-1]
            if filetype == "json":
                jsonData = jsonref.loads(files[0].file.read().decode())
                # jsonData = yaml.safe_dump(python_dict)
            else:
                jsonData = yaml.safe_load(files[0].file.read().decode())

            files[0].file.seek(0)
        else:
            raise HTTPException(
                status_code=500, detail=str("Please provide a File or Link")
            )

        validate_spec(jsonData)

        labels = set()
        for path in jsonData["paths"].keys():
            for request in jsonData["paths"][path].keys():
                if "tags" in jsonData["paths"][path][request]:
                    labels.update(jsonData["paths"][path][request]["tags"])

        """
        fuseki_id = _save_service_metadata_to_fuseki(
            service=created_service,
            description=jsonData["info"]["description"],
            db=db,
            url=jsonData["servers"][0]["url"],
            labels=labels,
        )
        """

        #####################################################
        # Autogerenerated from Arka
        fuseki_id = _save_service_metadata_to_fuseki_auto(
            service=created_service, db=db, file_json=jsonData
        )
        #####################################################

        created_service.metadata_uri = fuseki_id
        sql_api.update_service(db=db, service=created_service)
    except Exception as e:
        logger.error(get_stacktrace(e))
        print(get_stacktrace(e))
        sparql_services_api.delete_service_autogenerated(created_service.metadata_uri)
        sql_api.delete_service(db=db, service=created_service)
        raise HTTPException(status_code=500, detail=str(e))

    try:
        minio_api.upload_data(
            bucket,
            prefix=f"services/definitions/{created_service.name}",
            token=token,
            data=bytes(jsonref.dumps(jsonData), "utf-8"),
            objectname=name + ".json",
        )

    except Exception as e:
        logger.exception(e)
        sparql_services_api.delete_service_autogenerated(created_service.metadata_uri)
        sql_api.delete_service(db=db, service=created_service)
        raise HTTPException(
            status_code=500, detail="Response Data could not be Uploaded to MinIO"
        )

    return "Service successfully registered"


def _save_service_metadata_to_fuseki_auto(
    service: Service,
    db: Session,
    file_json,
):
    """Saves Integrated Service metadata to the Fuseki Triple storage.

    First this function creates a temporary Fuseki dataset.
    Then the given metadata will be used, to build a graph representation.
    This representation is sent to the temporary dataset and will be validated using the shacl shapes stored in the shapes dataset.
    If the validation does not fail, tha graph will be also saved in the Fuseki dataset ds.
    After the uploading of the metadata the temporary graph gets deleted.

    Args:
        Integrated Service: The Integrated Service instance, that was put into Postgres.
        labels: A list of labels, which are used to describe the Integrated Service.
        description: The description of the Integrated Service.
        db: Database Session. Only used to delete the Postgres entry, if the uploading to Fuseki fails.

    Returns:
        The URL used as an ID in the Fuseki Storage.

    Raises:
        HTTPException: If uploading metadata to FUseki failes.
    """
    try:
        temporary_fuseki_dataset = "dataset-" + str(service.id)

        sparql_util.createFusekiDataset(temporary_fuseki_dataset)

        graph, fuseki_id = sparql_services_api.create_graph_autogenerated(
            file_json=file_json,
            minio_server=MINIO_ENDPOINT,
            bucket=service.bucket_name,
            service_id=service.id,
        )

        sparql_util.store_graph(graph, temporary_fuseki_dataset)

        shape_information = sparql_util.get_shapes()
        report = sparql_util.shacl_validate(temporary_fuseki_dataset, shape_information)

        if not report["sh:conforms"]:
            raise HTTPException(
                status_code=400,
                detail="Data does not match required data for triple storage.",
            )

        sparql_util.store_graph(graph)
        sparql_util.delete_graph(temporary_fuseki_dataset)

        return fuseki_id
    except Exception as e:
        logger.error(
            "Uploading Metadata to Fuseki failed. Stacktrace:\n" + get_stacktrace(e)
        )
        sql_api.delete_service(db, service)
        raise HTTPException(
            status_code=500,
            detail="Creation of Metdata for Integrated Service failed. Please try again.",
        )


def _save_service_metadata_to_fuseki(
    service: Service,
    description: str,
    db: Session,
    url: str,
    labels: List[str],
):
    """Saves Integrated Service metadata to the Fuseki Triple storage.

    First this function creates a temporary Fuseki dataset.
    Then the given metadata will be used, to build a graph representation.
    This representation is sent to the temporary dataset and will be validated using the shacl shapes stored in the shapes dataset.
    If the validation does not fail, tha graph will be also saved in the Fuseki dataset ds.
    After the uploading of the metadata the temporary graph gets deleted.

    Args:
        Integrated Service: The Integrated Service instance, that was put into Postgres.
        labels: A list of labels, which are used to describe the Integrated Service.
        description: The description of the Integrated Service.
        db: Database Session. Only used to delete the Postgres entry, if the uploading to Fuseki fails.

    Returns:
        The URL used as an ID in the Fuseki Storage.

    Raises:
        HTTPException: If uploading metadata to FUseki failes.
    """
    try:
        temporary_fuseki_dataset = "dataset-" + str(service.id)

        sparql_util.createFusekiDataset(temporary_fuseki_dataset)

        graph, fuseki_id = sparql_services_api.create_graph(
            minio_server=MINIO_ENDPOINT,
            bucket=service.bucket_name,
            service_name=service.name,
            service_id=service.id,
            description=description,
            url=url,
            labels=labels,
        )

        sparql_util.store_graph(graph, temporary_fuseki_dataset)

        shape_information = sparql_util.get_shapes()
        report = sparql_util.shacl_validate(temporary_fuseki_dataset, shape_information)

        if not report["sh:conforms"]:
            raise HTTPException(
                status_code=400,
                detail="Data does not match required data for triple storage.",
            )

        sparql_util.store_graph(graph)
        sparql_util.delete_graph(temporary_fuseki_dataset)

        return fuseki_id
    except Exception as e:
        logger.error(
            "Uploading Metadata to Fuseki failed. Stacktrace:\n" + get_stacktrace(e)
        )
        sql_api.delete_service(db, service)
        raise HTTPException(
            status_code=500,
            detail="Creation of Metdata for Integrated Service failed. Please try again.",
        )


def _create_initial_entry_postgres(
    db: Session,
    user: KeycloakUser,
    service_name: str,
):
    """Created an initial entry for the Integrated Service in the Postgres database.

    Args:
        db: Database Session.
        user: Information on the user, who wants to create the Integrated Service.
        name: The name of the Integrated Service.

    Returns:
        The instance of the created Integrated Service.

    Raises:
        HTTPException: If there are problems during creation of the Integrated Service.
    """
    try:
        # Replace Integrated Service name by name(2), (3)... if name already exist
        if sql_api.get_service_by_name(db=db, name=service_name):
            count = 2
            while sql_api.get_service_by_name(db=db, name=f"{service_name}({count})"):
                count += 1
            service_name = f"{service_name}({count})"

        created_service = sql_api.create_service(
            db,
            name=service_name,
            owner=user.username,
            last_modified=datetime.now(),
            bucket_name=user.minio_bucket_name,
        )

        return created_service
    except Exception as e:
        logger.error("Saving into Postgres failed. Stacktrace:\n" + get_stacktrace(e))
        raise HTTPException(
            status_code=500,
            detail="Initial Creation of Service failed. Please try again.",
        )


@router.patch("/{service_id}/toggle-public")
def update_service_public(
    request: Request, service_id: int, db: Session = Depends(get_db)
):
    service = check_exists(sql_api.get_service(db, service_id))

    service.public = not service.public

    if service.public:
        _create_zip(service, request.user.minio_token)
        _create_catalog_entry(service)
    else:
        _remove_zip(service, request.user.minio_token)
        _remove_catalog_entry(service)

    return sql_api.update_service(db, service)


def _create_zip(service: Service, token):
    downloaded_files = {}
    metadata = sparql_services_api.get_metadata_information_for_service_uri(
        service.metadata_uri
    )
    downloaded_files["metadata.json"] = json.dumps(metadata).encode("utf-8")
    for item in minio_api.get_all_objects(
        service.bucket_name, prefix=f"services/definitions/{service.name}/", token=token
    ):
        if item.is_dir is False:
            downloaded_files[item.object_name] = minio_api.download_file(
                service.bucket_name, token, item
            ).read()
    zip = common.create_zip_file(downloaded_files)
    minio_api.upload_data(
        bucket=service.bucket_name,
        prefix=f"services/{service.name}/edc",
        token=token,
        data=zip.getvalue(),
        objectname=f"{service.name}.zip",
    )


def _remove_zip(service: Service, token):
    minio_api.delete_object(
        bucket=service.bucket_name,
        object_name=f"services/{service.name}/edc/{service.name}.zip",
        token=token,
    )


def _create_catalog_entry(service: Service):
    description = sparql_util.get_description_for_uri(service.metadata_uri)
    metadata = sparql_util.get_metadata_information_for_uri(service.metadata_uri)
    create_catalog_entry_service(service, description, metadata)


def _remove_catalog_entry(service: Service):
    delete_catalog_entry_service(service)


@router.delete("/{service_id}")
def delete_service(
    request: Request,
    service_id: str,
    db: Session = Depends(get_db),
):
    service = check_exists(sql_api.get_service(db, service_id))
    user: KeycloakUser = request.user

    _validate_parameters(service.bucket_name, user.minio_token)

    # Check integrity constraints first, before deleting files from MinIO.
    try:
        sql_api.delete_service(db, service)
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if service.metadata_uri is not None:
        sparql_services_api.delete_service_autogenerated(service.metadata_uri)

    service_prefix = f"services/{service.name}/"
    minio_api.delete_all_objects(
        user.minio_bucket_name, prefix=service_prefix, token=user.minio_token
    )

    minio_api.delete_all_objects(
        user.minio_bucket_name,
        prefix="services/definitions/" + service.name,
        token=user.minio_token,
    )

    return Response(status_code=204)


def _validate_parameters(bucket, token):
    try:
        minio_api.valid_params(bucket, token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
