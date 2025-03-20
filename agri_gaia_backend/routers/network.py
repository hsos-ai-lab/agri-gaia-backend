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
from typing import List
import json
import os
import io

from agri_gaia_backend.db import connector_api as sql_api
from agri_gaia_backend.routers.common import check_exists, get_db, extract_zip
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.schemas.connector import Connector
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.schemas.dataset import Dataset
from agri_gaia_backend.util.common import get_stacktrace
from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    Response,
    status,
)
from agri_gaia_backend.routers.datasets import _import_dataset_from_zip
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agri_gaia_backend.services.edc.connector import (
    create_contract_negotiation,
    initiate_file_transfer,
    query_contract_negotiation,
    query_filetransfer,
    own_connector_information,
)

PROJECT_BASE_URL = os.environ.get("PROJECT_BASE_URL")

ROOT_PATH = "/network"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


@router.get("", response_model=List[Connector])
def get_all_connectors(
    skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)
):
    """Fetches all Connectors from the postgres database

    Args:
        skip: How many connector entries shall be skipped. Defaults to 0.
        limit: What is the maximum number of connectors to be fetched? defaults to 100.
        db: Database Session. Created automatically.

    Returns:
        A list of all connectors, which are stored by the plattform.
    """
    return sql_api.get_connectors(db, skip=skip, limit=limit)


@router.get("/info")
def get_own_connector_information():
    """Fetches all Connectors from the postgres database

    Args:
        skip: How many connector entries shall be skipped. Defaults to 0.
        limit: What is the maximum number of connectors to be fetched? defaults to 100.
        db: Database Session. Created automatically.

    Returns:
        A list of all connectors, which are stored by the plattform.
    """

    return own_connector_information()


@router.get("/{connector_id}", response_model=Connector)
def get_connector(connector_id: int, db: Session = Depends(get_db)):
    """Fetches the Conenctor matching the given ID

    Args:
        connector_id: The ID of the searched connector
        db: Database Session. Created automatically.

    Returns:
        One Connector object that is identified by the passed ID.

    Raises:
        HTTPException: No connector is found for the given ID.
    """
    return check_exists(sql_api.get_connector(db, connector_id))


@router.get("/contractNegotiation/{negotiation_id}")
def query_negotiation(
    request: Request,
    negotiation_id: str,
    db: Session = Depends(get_db),
):
    print(negotiation_id)
    print(PROJECT_BASE_URL)
    response = query_contract_negotiation(negotiation_id=negotiation_id)
    print(response)
    result = json.loads(response.decode("utf8").replace("'", '"'))
    print(result)
    return result


@router.get("/transferprocess/{transfer_id}")
def query_transfer_Process(
    request: Request,
    transfer_id: str,
    db: Session = Depends(get_db),
):
    print(transfer_id)
    print(PROJECT_BASE_URL)
    response = query_filetransfer(transfer_id=transfer_id)
    print(response)
    result = json.loads(response.decode("utf8").replace("'", '"'))
    return result


@router.post(
    "/transferprocess/{connector_id}/{agreement_id}/{asset_id}", response_model=str
)
def initiate_transfer(
    request: Request,
    connector_id: str,
    agreement_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
):
    print(connector_id)
    user: KeycloakUser = request.user

    connector = sql_api.get_connector(connector_id=connector_id, db=db)
    response = initiate_file_transfer(
        asset_id=asset_id,
        contract_agreement_id=agreement_id,
        bucket=user.username,
        minio_endpoint="https://minio." + PROJECT_BASE_URL,
        asset_name=agreement_id + ".zip",
        connector_address=connector.ids_url,
    )

    result = json.loads(response.decode("utf8").replace("'", '"'))
    return result["id"]


@router.post(
    "/contractNegotiation/{connector_id}/{offer_id}/{asset_id}", response_model=str
)
def initiate_negotiation(
    request: Request,
    connector_id: str,
    offer_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
):
    print(connector_id)
    connector = sql_api.get_connector(connector_id=connector_id, db=db)
    response = create_contract_negotiation(
        offer_id=offer_id, asset_id=asset_id, connector_ids_address=connector.ids_url
    )
    result = json.loads(response.decode("utf8").replace("'", '"'))
    return result["id"]


@router.post("/import/{asset_name}", response_model=Dataset)
def initiate_transfer(
    request: Request,
    asset_name: str,
    db: Session = Depends(get_db),
):
    user: KeycloakUser = request.user

    object = minio_api.get_object(
        bucket=user.username, object_name=asset_name, token=user.minio_token
    )

    zip_content = extract_zip(io.BytesIO(object.data))
    return _import_dataset_from_zip(zip_content, db, request)


@router.post("", response_model=Connector, status_code=status.HTTP_201_CREATED)
def create_connector(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    ids_url: str = Form(...),
    db: Session = Depends(get_db),
):
    """Creates a connector instance.

    Initially creates an entry in the Postgres database to retreive the autogenerated ID of the connector.
    Afterwards the metadata will be uploaded to the Fuseki Triple Storage.
    After putting the metadata into the triple storage, all files passed to this function will be uploaded to MinIO.
    Last the database entry in the Postgres database will be updated by information in filesize, ...

    Args:
        request: The request object containing information on the user.
            (like authentication token, his bucket name in MinIO, ...)
        name: The name of the connector to be created.
        db: Database Session. Created automatically.
        description: A short description of the connector and what to find inside.
        data_url: The Data endpoint of the connector to be added.
        ids_URL: The IDS endpoint of the connector to be added.
        minio_url: The MinIO endpoint of the connector to be added.

    Returns:
        The created connector instance saved in the Postgres database.

    Raises:
        HTTPException: If one of the steps failes.
    """
    created_connector = _create_initial_entry_postgres(
        db=db,
        connector_name=name,
        connector_description=description,
        connector_ids_url=ids_url,
    )

    return created_connector


def _create_initial_entry_postgres(
    db: Session,
    connector_name: str,
    connector_description: str,
    connector_ids_url: str,
    connector_data_url: str = "",
    connector_minio_url: str = "",
    connector_api_key: str = "",
):
    """Created an initial entry for the connector in the Postgres database.

    Args:
        db: Database Session.
        user: Information on the user, who wants to create the connector.
        connector_name: The name of the connector.
        connector_description: The dscription of the connector.
        connector_data_url: The data endpoint of the connector.
        connector_ids_url: The ids endpoint of the connector.
        connector_minio_url: The MinIO endpoint of the connector.

    Returns:
        The instance of the created connector.

    Raises:
        HTTPException: If there are problems during creation of the connector.
    """
    try:
        created_connector = sql_api.create_connector(
            db,
            name=connector_name,
            description=connector_description,
            data_url=connector_data_url,
            ids_url=connector_ids_url,
            minio_url=connector_minio_url,
            api_key=connector_api_key,
        )

        return created_connector
    except Exception as e:
        logger.error("Saving into Postgres failed. Stacktrace:\n" + get_stacktrace(e))
        raise HTTPException(
            status_code=500,
            detail="Initial Addition of Connector failed. Please try again.",
        )


@router.delete("/{connector_id}")
def delete_connector(
    request: Request,
    connector_id: int,
    db: Session = Depends(get_db),
):
    """Deletes a connector.

    Deletes the connector entry from the Postgres database, the metadata from Fuseki as well as the uploaded files from MinIO.

    Args:
        request: The request object containing information on the user.
            (like authentication token, his bucket name in MinIO, ...)
        cvat_auth: CVAT authentication data (sessionid, key, csrftoken)
        connector_id: The ID of the connector to be deleted.
        db: Database Session. Created automatically.

    Returns:
        Success status code.
    """
    connector = check_exists(sql_api.get_connector(db, connector_id))

    # Check integrity constraints first, before deleting files from MinIO.
    try:
        sql_api.delete_connector(db, connector)
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return Response(status_code=204)
