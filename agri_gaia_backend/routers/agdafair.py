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

import base64
import datetime
import io
import json
import logging
import os
from typing import Any

import gitlab
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from minio import Minio
from sqlalchemy.orm import Session

from agri_gaia_backend.db import dataset_api as sql_api
from agri_gaia_backend.routers.common import get_db
from agri_gaia_backend.services.graph.sparql_operations import util as sparql_util

ROOT_PATH = "/agdafair"
LFS_RESOLVER_URL = "https://lfs-resolver.nfdi4plants.org/presigned-url/"
GITLAB_API_PREFIX = "https://gitdev.nfdi4plants.org/api/v4/projects/"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)

minio_endpoint = os.environ.get("MINIO_ENDPOINT")
minio_user = os.environ.get("MINIO_ROOT_USER")
minio_pass = os.environ.get("MINIO_ROOT_PASSWORD")


def _get_minio_client() -> Minio:
    """Create and return a MinIO client using environment credentials."""
    return Minio(
        minio_endpoint,
        access_key=minio_user,
        secret_key=minio_pass,
        secure=False,
    )


def _parse_ro_crate_metadata(content: dict[str, Any]) -> str:
    """Parse an RO-Crate metadata JSON, register it in Fuseki, and return the dataset name.

    Iterates over the ``@graph`` array looking for the root dataset descriptor
    (``@id == "./"``). When found, creates a Fuseki dataset named after the
    ``identifier`` field and stores the full JSON-LD metadata under the
    ``name`` field.

    Args:
        content: Parsed RO-Crate JSON-LD metadata dictionary.

    Returns:
        The sanitised dataset identifier (spaces removed) used as the Fuseki
        dataset name.

    Raises:
        ValueError: If no root dataset descriptor is found in the graph.
    """
    for node in content["@graph"]:
        if node["@id"] == "./":
            name = node["identifier"].replace(" ", "")
            sparql_util.createFusekiDataset(name)
            sparql_util.store_json(content, node["name"].replace(" ", ""))
            return name

    raise ValueError("RO-Crate metadata does not contain a root dataset descriptor (@id='./')).")


def _download_files(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Download all LFS-tracked files referenced in the RO-Crate graph.

    Files are identified by the presence of a ``sha256`` field. Each file is
    resolved via the NFDI4Plants LFS resolver and its binary content is
    downloaded.

    Args:
        content: Parsed RO-Crate JSON-LD metadata dictionary.

    Returns:
        A list of dicts, each containing ``name``, ``content`` (bytes), and
        ``content_type`` of a downloaded file.
    """
    files = []
    for node in content["@graph"]:
        oid = node.get("sha256")
        if not oid:
            continue

        logger.debug("Resolving LFS object: oid=%s, name=%s", oid, node.get("name"))
        response = requests.get(f"{LFS_RESOLVER_URL}?oid={oid}", allow_redirects=True)
        response.raise_for_status()

        files.append({
            "name": node["name"],
            "content": response.content,
            "content_type": response.headers.get("Content-Type", "application/octet-stream"),
        })

    return files


def _upload_files_to_minio(
    bucket: str,
    dataset_id: str,
    files: list[dict[str, Any]],
) -> None:
    """Upload downloaded files to a MinIO bucket under the dataset path.

    Args:
        bucket: Target MinIO bucket name.
        dataset_id: Dataset identifier used to build the object path.
        files: List of file dicts as returned by :func:`_download_files`.
    """
    client = _get_minio_client()
    for file in files:
        data = io.BytesIO(file["content"])
        client.put_object(
            bucket,
            f"dataset/{dataset_id}/{file['name']}",
            data,
            length=len(file["content"]),
            content_type=file["content_type"],
        )


def _import_ro_crate(
    db: Session,
    content: dict[str, Any],
    owner: str,
    bucket: str,
    dataset_type: str,
) -> dict[str, str]:
    """Shared import logic for both ``/import`` and ``/importCrate`` endpoints.

    Parses the RO-Crate metadata, downloads referenced files, persists a
    dataset record in the database, and uploads the files to MinIO. On failure
    during upload, the partially created dataset is cleaned up.

    Args:
        db: Active SQLAlchemy database session.
        content: Parsed RO-Crate JSON-LD metadata dictionary.
        owner: Username that owns the imported dataset.
        bucket: MinIO bucket to upload files into.
        dataset_type: Classification of the dataset (e.g. ``"AgriImageDataResource"``).

    Returns:
        A dict with a success message.

    Raises:
        HTTPException: If the RO-Crate metadata is invalid or file download fails.
    """
    try:
        name = _parse_ro_crate_metadata(content)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    files = _download_files(content)

    dataset = sql_api.create_dataset(
        db,
        name=name,
        owner=owner,
        filecount=len(files),
        total_filesize=sum(len(f["content"]) for f in files),
        last_modified=datetime.datetime.now(),
        bucket_name=bucket,
        dataset_type=dataset_type,
        annotation_labels=None,
    )

    try:
        _upload_files_to_minio(bucket, dataset.id, files)
        dataset.minio_location = f"datasets/{dataset.id}"
        dataset.metadata_uri = name
        sql_api.update_dataset(db, dataset)
    except Exception:
        logger.exception("Upload failed for dataset %s — rolling back", dataset.id)
        sql_api.delete_dataset(db, dataset)
        raise HTTPException(status_code=500, detail="Failed to upload files to storage.")

    return {"message": "Data imported!"}


@router.get("/test")
def heartbeat():
    """Health-check endpoint."""
    return {"message": "Service alive!"}


@router.post("/import")
async def import_arc(request: Request, db: Session = Depends(get_db)):
    """Import a dataset from a GitLab-hosted ARC repository.

    Expects a JSON body with:
        - ``package_endpoint``: GitLab instance URL.
        - ``gitlab_token``: Personal access token for the GitLab API.
        - ``project_id``: Numeric GitLab project ID.
        - ``ro_crate_url``: Full API URL to the RO-Crate metadata file.
        - ``username``: Owner of the imported dataset.
        - ``datasetType``: Classification of the dataset.
    """
    body = json.loads(await request.body())

    gl = gitlab.Gitlab(body["package_endpoint"], private_token=body["gitlab_token"])
    project = gl.projects.get(body["project_id"])
    logger.info("Importing ARC from project: %s", project.name)

    # Strip the GitLab API prefix to get the repository-relative file path
    file_path = body["ro_crate_url"].removeprefix(GITLAB_API_PREFIX).split("/", 1)[1]
    logger.info("RO-Crate file path: %s", file_path)

    raw = project.files.get(file_path=file_path, ref="main")
    content = json.loads(base64.b64decode(raw.content).decode("utf-8"))

    return _import_ro_crate(
        db,
        content,
        owner=body["username"],
        bucket=body["username"],
        dataset_type=body["datasetType"],
    )


@router.post("/importCrate")
async def import_crate(request: Request, db: Session = Depends(get_db)):
    """Import a dataset from a directly submitted RO-Crate JSON-LD payload.

    Expects the raw request body to be a valid RO-Crate ``metadata.json``
    document. Uses ``"towamhof"`` as both owner and bucket name, and defaults the
    dataset type to ``"AgriImageDataResource"``.
    """
    content = json.loads(await request.body())

    return _import_ro_crate(
        db,
        content,
        owner="towamhof",
        bucket="towamhof",
        dataset_type="AgriImageDataResource",
    )
