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

import json
import logging
import os
from typing import List
from agri_gaia_backend.schemas.benchmark_device import BenchmarkDevice
from dotenv import load_dotenv
from fastapi import APIRouter, Request
import requests
from agri_gaia_backend.util.benchmark import (
    get_all_datasets,
    get_all_devices,
    get_data_for_job,
    get_jobs_for_dataset,
    get_jobs_for_device,
)
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser

ROOT_PATH = "/edge-benchmark-overview"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)
load_dotenv()


@router.get("/devices")
def get_devices(request: Request):
    user: KeycloakUser = request.user
    devices = get_all_devices(user)

    return devices


@router.get("/datasets")
def get_datasets(request: Request):
    user: KeycloakUser = request.user
    datasets = get_all_datasets(user)

    return datasets


@router.get("/jobs/datasets/{dataset_id}")
def get_datasets(request: Request, dataset_id: str):
    user: KeycloakUser = request.user
    jobs = get_jobs_for_dataset(user, int(dataset_id))

    return jobs


@router.get("/jobs/devices/{device}")
def get_datasets(request: Request, device: str):
    user: KeycloakUser = request.user
    jobs = get_jobs_for_device(user, device)

    return jobs


@router.get("/job/{job_id}")
def get_datasets(request: Request, job_id: str):
    user: KeycloakUser = request.user
    job = get_data_for_job(user, job_id)

    return job
