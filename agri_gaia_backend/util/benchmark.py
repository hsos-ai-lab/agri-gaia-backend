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

import json
import logging
from typing import List, Optional
from fastapi import HTTPException, Request
from fastapi.datastructures import UploadFile
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.services.minio_api import MINIO_ENDPOINT
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser

logger = logging.getLogger("api-logger")


def get_all_datasets(user: KeycloakUser):
    token = user.minio_token
    datasets = []
    metadata_files = {}
    for item in minio_api.get_all_objects(
        user.minio_bucket_name, prefix="benchmark", token=token
    ):
        if item.is_dir is False and "metadata" in item.object_name:
            metadata_files[item.object_name] = json.loads(
                minio_api.download_file(user.minio_bucket_name, token, item)
                .read()
                .decode()
            )
    logger.info(metadata_files)
    for key, value in metadata_files.items():
        datasets.append(str(value["dataset"]))
    logger.info(datasets)
    datasets_singular = list(dict.fromkeys(datasets))
    return datasets_singular


def get_jobs_for_dataset(user: KeycloakUser, dataset_id: str):
    token = user.minio_token
    metadata_files = {}
    for item in minio_api.get_all_objects(
        user.minio_bucket_name, prefix="benchmark", token=token
    ):
        if item.is_dir is False and "metadata" in item.object_name:
            metadata_files[item.object_name] = json.loads(
                minio_api.download_file(user.minio_bucket_name, token, item)
                .read()
                .decode()
            )
    logger.info(metadata_files)
    jobs = []
    for key, value in metadata_files.items():
        if value["dataset"] == dataset_id:
            jobs.append(value["job_id"])
    return jobs


def get_all_devices(user: KeycloakUser):
    token = user.minio_token
    devices = []
    metadata_files = {}
    for item in minio_api.get_all_objects(
        user.minio_bucket_name, prefix="benchmark", token=token
    ):
        if item.is_dir is False and "metadata" in item.object_name:
            metadata_files[item.object_name] = json.loads(
                minio_api.download_file(user.minio_bucket_name, token, item)
                .read()
                .decode()
            )
    logger.info(metadata_files)
    for key, value in metadata_files.items():
        devices.append(value["edge_device"]["device_name"])
    logger.info(devices)
    datasets_singular = list(dict.fromkeys(devices))
    return datasets_singular


def get_jobs_for_device(user: KeycloakUser, device_name: str):
    token = user.minio_token
    metadata_files = {}
    for item in minio_api.get_all_objects(
        user.minio_bucket_name, prefix="benchmark", token=token
    ):
        if item.is_dir is False and "metadata" in item.object_name:
            metadata_files[item.object_name] = json.loads(
                minio_api.download_file(user.minio_bucket_name, token, item)
                .read()
                .decode()
            )
    jobs = []
    for key, value in metadata_files.items():
        if value["edge_device"]["device_name"] == device_name:
            jobs.append(value["job_id"])
    return jobs


def get_data_for_job(user: KeycloakUser, job_id: str):
    token = user.minio_token
    benchmarkData = (
        minio_api.get_object(
            user.minio_bucket_name, f"benchmark/{job_id}/benchmark.json", token=token
        )
        .read()
        .decode()
    )
    logger.info(benchmarkData)
    return benchmarkData
