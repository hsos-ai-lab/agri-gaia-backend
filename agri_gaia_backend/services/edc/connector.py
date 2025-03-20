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

from multiprocessing.dummy import Array
import os
from tokenize import String

from agri_gaia_backend.db.models import Dataset, Model, Service

import logging
import requests
import random

CATALOG_ENDPOINT = os.environ.get("PROVIDER_DATA_ENDPOINT")
PROJECT_BASE_URL = os.environ.get("PROJECT_BASE_URL")
CONNECTOR_PASSWORD = os.environ.get("CONNECTOR_PASSWORD")

logger = logging.getLogger("api-logger")


def own_connector_information():
    requests.get(
        CATALOG_ENDPOINT + "/api/v1/data/assets",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )

    dict = {
        "connector_data_url": "https://edc-provider."
        + PROJECT_BASE_URL
        + "/api/v1/data",
        "connector_ids_url": "https://edc-provider-ids."
        + PROJECT_BASE_URL.replace("edc-provider", "edc-provider-ids")
        + "/api/v1/ids/data",
        "minio_url": "https://minio."
        + PROJECT_BASE_URL.replace("edc-provider", "minio"),
        "password": CONNECTOR_PASSWORD,
        "available": True,
    }
    return dict


def create_catalog_entry_dataset(
    dataset: Dataset,
    labels: Array,
    description: String,
    metadata: Array,
    locations: Array,
):
    if len(locations) == 0:
        location = "unkown location"
    else:
        location = locations[0]

    minio_location = dataset.minio_location + "/edc/" + dataset.name + ".zip"
    id = dataset.minio_location.replace("/", "")

    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/assets",
        json=_create_asset_entry(
            id=id,
            minio_location=minio_location,
            name=dataset.name,
            bucket=dataset.bucket_name,
            labels=labels,
            description=description,
            metadata=metadata,
            content="Datensatz",
            location=location,
        ),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/policydefinitions",
        json=_create_policy_entry(target_id=id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/contractdefinitions",
        json=_create_contract_offer(asset_id=id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )


def delete_catalog_entry_dataset(dataset: Dataset):
    id = dataset.minio_location.replace("/", "")
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/contractdefinitions/contract" + id,
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/policydefinitions/policy" + id,
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/assets/" + id,
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )


def create_catalog_entry_service(
    service: Service, description: String, metadata: Array
):
    minio_location = "services/" + service.name + "/edc/" + service.name + ".zip"
    id = f"services{service.name}"

    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/assets",
        json=_create_asset_entry(
            id=id,
            minio_location=minio_location,
            name=service.name,
            bucket=service.bucket_name,
            labels=[],
            description=description,
            metadata=metadata,
            content="KI-Service",
            location="",
        ),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/policydefinitions",
        json=_create_policy_entry(target_id=id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/contractdefinitions",
        json=_create_contract_offer(asset_id=id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )


def delete_catalog_entry_service(service: Service):
    id = f"services{service.name}"
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/contractdefinitions/contract" + id,
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/policydefinitions/policy" + id,
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/assets/" + id,
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )


def create_catalog_entry_model(
    model: Model, labels: Array, description: String, metadata: Array
):
    minio_location = "models/" + str(model.id) + "/edc/" + model.name + ".zip"
    id = "models" + str(model.id)
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/assets",
        json=_create_asset_entry(
            id=id,
            minio_location=minio_location,
            name=model.name,
            bucket=model.bucket_name,
            labels=labels,
            description=description,
            metadata=metadata,
            content="KI-Modell",
            location="",
        ),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/policydefinitions",
        json=_create_policy_entry(target_id=id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )
    requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/contractdefinitions",
        json=_create_contract_offer(asset_id=id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    )


def delete_catalog_entry_model(model: Model):
    requests.delete(
        CATALOG_ENDPOINT
        + "/api/v1/data/contractdefinitions/contractmodels"
        + str(model.id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )
    requests.delete(
        CATALOG_ENDPOINT
        + "/api/v1/data/policydefinitions/policymodels"
        + str(model.id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )
    requests.delete(
        CATALOG_ENDPOINT + "/api/v1/data/assets/models" + str(model.id),
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    )


def create_contract_negotiation(
    connector_ids_address: str, offer_id: str, asset_id: str
):
    return requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/contractnegotiations",
        json=_create_contract_negotiation(
            connector_ids_address=connector_ids_address,
            offer_id=offer_id,
            asset_id=asset_id,
        ),
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    ).content


def query_contract_negotiation(negotiation_id: str):
    negotiation = requests.get(
        CATALOG_ENDPOINT + f"/api/v1/data/contractnegotiations/{negotiation_id}",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    ).content
    return negotiation


def query_filetransfer(transfer_id: str):
    transfer = requests.get(
        CATALOG_ENDPOINT + f"/api/v1/data/transferprocess/{transfer_id}",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    ).content
    return transfer


def initiate_file_transfer(
    asset_id: str,
    contract_agreement_id: str,
    bucket: str,
    minio_endpoint: str,
    asset_name: str,
    connector_address: str,
):
    transfer = _create_file_transfer(
        asset_id=asset_id,
        asset_name=asset_name,
        contract_agreement_id=contract_agreement_id,
        bucket=bucket,
        minio_endpoint=minio_endpoint,
        connector_address=connector_address,
    )
    return requests.post(
        CATALOG_ENDPOINT + "/api/v1/data/transferprocess",
        json=transfer,
        headers={"X-Api-Key": CONNECTOR_PASSWORD, "Content-Type": "application/json"},
    ).content


def get_catalouge_information():
    assets = requests.get(
        CATALOG_ENDPOINT + "/api/v1/data/assets",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    ).content
    policies = requests.get(
        CATALOG_ENDPOINT + "/api/v1/data/policydefinitions",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    ).content
    definitions = requests.get(
        CATALOG_ENDPOINT + "/api/v1/data/contractdefinitions",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    ).content
    negotiations = requests.get(
        CATALOG_ENDPOINT + "/api/v1/data/contractnegotiations",
        headers={"X-Api-Key": CONNECTOR_PASSWORD},
    ).content

    # print(json.dumps(json.loads(assets), indent=4))
    # print(json.dumps(json.loads(policies), indent=4))
    # print(json.dumps(json.loads(definitions), indent=4))
    # print(json.dumps(json.loads(negotiations), indent=4))
    return {
        "assets": assets,
        "definitions": definitions,
        "policies": policies,
        "negotiations": negotiations,
    }


def _create_file_transfer(
    asset_id: str,
    contract_agreement_id: str,
    bucket: str,
    minio_endpoint: str,
    asset_name: str,
    connector_address: str,
):
    dict = {
        "assetId": asset_id,
        "contractId": contract_agreement_id,
        "connectorId": "consumer",
        "dataDestination": {
            "properties": {
                "bucketName": bucket,
                "endpoint": minio_endpoint,
                "assetName": asset_name,
                "type": "AmazonS3",
                "region": "us-east-1",
            }
        },
        "managedResources": "true",
        "transferType": {"isFinite": "true"},
        "connectorAddress": connector_address,
        "protocol": "ids-multipart",
    }
    print(dict)
    return dict


def _create_contract_negotiation(
    connector_ids_address: str, offer_id: str, asset_id: str
):
    dict = {
        "connectorAddress": connector_ids_address,
        "connectorId": "connector-id",
        "offer": {
            "offerId": offer_id,
            "assetId": asset_id,
            "policy": {
                "permissions": [
                    {
                        "edctype": "dataspaceconnector:permission",
                        "uid": None,
                        "target": asset_id,
                        "action": {
                            "type": "USE",
                            "includedIn": None,
                            "constraint": None,
                        },
                        "assignee": None,
                        "assigner": None,
                        "constraints": [],
                        "duties": [],
                    }
                ],
                "prohibitions": [],
                "obligations": [],
                "extensibleProperties": {},
                "inheritsFrom": None,
                "assigner": None,
                "assignee": None,
                "target": "",
                "type": {"type": "set"},
            },
            "connectorId": "connector-id",
            "protocol": "ids-multipart",
        },
    }
    print(dict)

    return dict


def _create_policy_entry(target_id: String):
    dict = {
        "uid": "use-eu",
        "id": "policy" + target_id,
        "policy": {
            "permissions": [
                {
                    "edctype": "dataspaceconnector:permission",
                    "uid": None,
                    "target": target_id,
                    "action": {"type": "USE", "includedIn": None, "constraint": None},
                    "assignee": None,
                    "assigner": None,
                    "constraints": [],
                    "duties": [],
                }
            ],
            "prohibitions": [],
            "obligations": [],
            "extensibleProperties": {},
            "inheritsFrom": None,
            "assigner": None,
            "assignee": None,
            "target": "",
            "type": {"type": "set"},
        },
    }
    return dict


def _create_asset_entry(
    id: String,
    minio_location: String,
    name: String,
    bucket: String,
    labels: Array,
    description: String,
    metadata: Array,
    content: String,
    location: String,
):
    dict = {
        "asset": {
            "id": id,
            "properties": {
                "asset:prop:id": id,
                "asset:prop:name": name,
                "asset:prop:description": description,
                "asset:prop:version": "1.0",
                "asset:prop:contenttype": content,
                "theme": labels,
                "asset:prop:byteSize": None,
                "spatial": location,
                "temporal": "",
                "price": random.randint(1000, 9999),
                "metadata": metadata,
            },
        },
        "dataAddress": {
            "properties": {
                "type": "AmazonS3",
                "region": "us-east-1",
                "bucketName": bucket,
                "assetName": minio_location,
                "keyName": minio_location,
            }
        },
    }
    return dict


def _create_contract_offer(asset_id: String):
    dict = {
        "accessPolicyId": "policy" + asset_id,
        "contractPolicyId": "policy" + asset_id,
        "id": "contract" + asset_id,
        "criteria": [
            {"operandLeft": "asset:prop:id", "operator": "=", "operandRight": asset_id}
        ],
    }
    return dict
