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

import os
import json
import time
import logging
import datetime
import requests
import traceback

from io import BytesIO
from typing import List, Any
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from requests.auth import HTTPBasicAuth
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.db import model_api as sql_api
from agri_gaia_backend.schemas.benchmark import Benchmark
from agri_gaia_backend.db import dataset_api as dataset_sql_api
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from edge_benchmarking_client.client import EdgeBenchmarkingClient
from agri_gaia_backend.db import benchmark_api as sql_benchmark_api
from agri_gaia_backend.schemas.benchmark_device import BenchmarkDevice
from edge_benchmarking_types.edge_farm.models import TritonDenseNetClient
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from agri_gaia_backend.routers.common import (
    TaskCreator,
    check_exists,
    get_db,
    get_task_creator,
)

load_dotenv()

ROOT_PATH = "/edge-benchmark"

EDGE_FARM_API_BASIC_AUTH_USERNAME = os.getenv("EDGE_BENCHMARKING_USER")
EDGE_FARM_API_BASIC_AUTH_PASSWORD = os.getenv("EDGE_BENCHMARKING_PASSWORD")
EDGE_FARM_API_BASIC_AUTH = HTTPBasicAuth(
    EDGE_FARM_API_BASIC_AUTH_USERNAME, EDGE_FARM_API_BASIC_AUTH_PASSWORD
)

EDGE_FARM_API_PROTOCOL = "https"
EDGE_FARM_API_HOST = os.getenv("EDGE_BENCHMARKING_URL")

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


@router.get("", response_model=List[Benchmark])
def get_all_benchmark_jobs(
    skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)
):
    return sql_benchmark_api.get_benchmarks(skip=skip, limit=limit, db=db)


@router.get("/device/header", response_model=List[BenchmarkDevice])
def get_all_edge_benchmark_device_headers():
    return requests.get(
        f"https://{os.getenv("EDGE_BENCHMARKING_URL")}/device/header",
        auth=EDGE_FARM_API_BASIC_AUTH,
    ).json()


@router.get("/device/{hostname}/info")
def get_edge_benchmark_device_info(hostname: str) -> dict[str, Any]:
    return requests.get(
        f"https://{os.getenv("EDGE_BENCHMARKING_URL")}/device/{hostname}/info",
        auth=EDGE_FARM_API_BASIC_AUTH,
    ).json()


@router.post("/start")
# TODO: Create pydantic model for edge_device
# TODO: Create pydantic model for benchmark_config
def edge_benchmark_start(
    request: Request,
    edge_device: dict,
    dataset_id: int,
    model_id: int,
    benchmark_config: dict,
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> None:
    user: KeycloakUser = request.user

    minio_token = user.minio_token
    bucket_name = user.minio_bucket_name

    model = load_model(model_id, minio_token, db)
    dataset, labels = load_dataset(dataset_id, minio_token, db)

    def _run_benchmark(
        on_error,
        on_progress_change,
        db: Session,
        user: KeycloakUser,
        model,
        dataset,
    ) -> None:

        client = EdgeBenchmarkingClient(
            protocol=EDGE_FARM_API_PROTOCOL,
            host=EDGE_FARM_API_HOST,
            username=EDGE_FARM_API_BASIC_AUTH_USERNAME,
            password=EDGE_FARM_API_BASIC_AUTH_PASSWORD,
        )

        # TODO: Map benchmark_config onto inference_client
        inference_client = TritonDenseNetClient(
            host=edge_device.hostname,
            model_name="densenet_onnx",
            num_classes=1,
            scaling="inception",
        )

        # TODO: Map benchmark_config onto benchmark_job
        benchmark_job = client.benchmark(
            edge_device=edge_device.hostname,
            dataset=dataset,
            model=model,
            inference_client=inference_client,
            model_metadata=None,
            labels=labels,
            cleanup=True,
        )

        minio_api.upload_data(
            bucket_name,
            prefix=f"benchmark/{benchmark_job.id}",
            token=minio_token,
            data=json.dumps(benchmark_job.benchmark_results).encode("utf-8"),
            objectname="benchmark.json",
        )

        minio_api.upload_data(
            bucket_name,
            prefix=f"benchmark/{benchmark_job.id}",
            token=minio_token,
            data=json.dumps(benchmark_job.inference_results).encode("utf-8"),
            objectname="inference.json",
        )

        # TODO: Create pydantic model for metadata
        metadata = {
            "time": time.time(),
            "dataset": dataset_id,
            "edge_device": {
                "device_ip": edge_device["ip"],
                "device_name": edge_device["hostname"],
            },
            "job_id": benchmark_job.id,
        }

        minio_api.upload_data(
            bucket_name,
            prefix=f"benchmark/{benchmark_job.id}",
            token=minio_token,
            data=json.dumps(metadata).encode("utf-8"),
            objectname="metadata.json",
        )

        _create_initial_entry_postgres(
            db=db,
            user=user,
            benchmark_name=f"{benchmark_job.id}",
            dataset_id=dataset_id,
            job_id=benchmark_job.id,
            device_ip=edge_device["ip"],
            device_name=edge_device["hostname"],
        )

    _, task_location_url, _ = task_creator.create_background_task(
        func=_run_benchmark,
        task_title=f"Started benchmark job on device '{edge_device["hostname"]}' with dataset '{dataset.name}' and model '{model.name}'.",
        db=db,
        user=user,
        model=model,
        dataset=dataset,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


def load_model(model_id: int, token: str, db) -> tuple[str, BytesIO]:
    model = check_exists(sql_api.get_model(db, model_id))
    _validate_parameters(model.bucket_name, token)

    minio_item = f"models/{model_id}/{model.name}"
    model_bytes = minio_api.download_file(model.bucket_name, token, minio_item).read()

    return model.name, BytesIO(model_bytes)


def load_dataset(dataset_id: int, minio_token: str, db):
    dataset = check_exists(dataset_sql_api.get_dataset(db, dataset_id))
    _validate_parameters(dataset.bucket_name, minio_token)

    dataset_prefix = f"datasets/{dataset.id}"

    dataset_files: list[tuple[str, BytesIO]] = []
    for dataset_entry in minio_api.get_all_objects(
        dataset.bucket_name, prefix=dataset_prefix, token=minio_token
    ):
        if not dataset_entry.is_dir and "annotations" not in dataset_entry.object_name:
            sample_filename = os.path.basename(dataset_entry.object_name)
            sample_bytes = minio_api.download_file(
                dataset.bucket_name, minio_token, dataset_entry
            ).read()

            dataset_files.append((sample_filename, BytesIO(sample_bytes)))

    label_files = minio_api.get_all_objects(
        dataset.bucket_name, f"{dataset_prefix}/annotations", minio_token
    )

    labels = None
    if len(label_files) == 1:
        label_file = label_files[0]
        label_bytes = minio_api.download_file(
            dataset.bucket_name, minio_token, label_file
        ).read()
        labels = ("labels.txt", BytesIO(label_bytes))

    return dataset_files, labels


def _validate_parameters(bucket, token):
    try:
        minio_api.valid_params(bucket, token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _create_initial_entry_postgres(
    db: Session,
    user: KeycloakUser,
    benchmark_name: str,
    dataset_id: int,
    job_id: int,
    device_ip: str,
    device_name: str,
):
    try:
        if sql_benchmark_api.get_benchmark_by_name(db=db, name=benchmark_name):
            count = 2
            while sql_benchmark_api.get_benchmark_by_name(
                db=db, name=f"{benchmark_name}({count})"
            ):
                count += 1
            inference_name = f"{inference_name}({count})"

        created_inference = sql_benchmark_api.create_benchmark(
            db,
            name=benchmark_name,
            owner=user.username,
            last_modified=datetime.datetime.now(),
            bucket_name=user.minio_bucket_name,
            minio_location=f"benchmark/{job_id}",
            timestamp=datetime.datetime.now(),
            dataset_id=dataset_id,
            job_id=job_id,
            device_ip=device_ip,
            device_name=device_name,
        )

        return created_inference
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Initial creation of benchmark job entry failed. Please try again.",
        ) from e
