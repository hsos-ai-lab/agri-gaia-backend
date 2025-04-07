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
import logging
import datetime
import requests

from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from requests.auth import HTTPBasicAuth
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.db import model_api as sql_api
from agri_gaia_backend.db import dataset_api as dataset_sql_api
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from edge_benchmarking_client.client import EdgeBenchmarkingClient
from agri_gaia_backend.db import edge_benchmark_api as sql_benchmark_api
from edge_benchmarking_types.edge_device.models import (
    DeviceHeader as TDeviceHeader,
    BenchmarkJob as TBenchmarkJob,
)
from agri_gaia_backend.schemas.edge_benchmark import BenchmarkJobRun, BenchmarkJob
from edge_benchmarking_types.edge_farm.models import (
    BenchmarkConfig,
    TritonInferenceClient,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
    File,
    UploadFile,
    Form,
)
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
EDGE_FARM_API_URL = f"{EDGE_FARM_API_PROTOCOL}://{EDGE_FARM_API_HOST}"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


@router.get("/jobs", response_model=List[BenchmarkJob])
def get_all_benchmark_jobs(
    skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)
):
    return sql_benchmark_api.get_all_benchmark_jobs(skip=skip, limit=limit, db=db)


@router.get("/device/header", response_model=List[TDeviceHeader])
def get_all_edge_benchmark_device_headers():
    return requests.get(
        f"{EDGE_FARM_API_URL}/device/header", auth=EDGE_FARM_API_BASIC_AUTH
    ).json()


@router.get("/device/{hostname}/info")
def get_edge_benchmark_device_info(hostname: str) -> dict[str, Any]:
    return requests.get(
        f"{EDGE_FARM_API_URL}/device/{hostname}/info", auth=EDGE_FARM_API_BASIC_AUTH
    ).json()


@router.post("/start")
async def edge_benchmark_start(
    request: Request,
    payload: str = Form(...),
    model_metadata: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> None:
    user: KeycloakUser = request.user
    minio_token = user.minio_token
    bucket_name = user.minio_bucket_name

    payload = json.loads(payload)

    dataset_id = payload["dataset_id"]
    model_id = payload["model_id"]
    chunk_size = payload["chunk_size"]

    benchmark_config = BenchmarkConfig(**payload["benchmark_config"])

    model_name, model = load_model(model_id, minio_token, db)
    (dataset_name, dataset), labels = load_dataset(dataset_id, minio_token, db)

    if isinstance(benchmark_config.inference_client, TritonInferenceClient):
        model_filename, _ = model
        benchmark_config.inference_client.model_name = Path(model_filename).stem
        benchmark_config.inference_client.model_version = "1"

    model_metadata = (
        (model_metadata.filename, BytesIO(await model_metadata.read()))
        if model_metadata is not None
        else None
    )

    def _run_benchmark(
        on_error,
        on_progress_change,
        db: Session,
        user: KeycloakUser,
    ) -> None:

        client = EdgeBenchmarkingClient(
            protocol=EDGE_FARM_API_PROTOCOL,
            host=EDGE_FARM_API_HOST,
            username=EDGE_FARM_API_BASIC_AUTH_USERNAME,
            password=EDGE_FARM_API_BASIC_AUTH_PASSWORD,
        )

        benchmark_job: TBenchmarkJob = client.benchmark(
            edge_device=benchmark_config.edge_device.host,
            dataset=dataset,
            model=model,
            inference_client=benchmark_config.inference_client,
            model_metadata=model_metadata,
            labels=labels,
            chunk_size=chunk_size,
            cpu_only=benchmark_config.cpu_only,
            cleanup=True,
        )

        benchmark_job_run = BenchmarkJobRun(
            dataset_id=dataset_id,
            model_id=model_id,
            benchmark_job=benchmark_job,
            benchmark_config=benchmark_config,
        )

        minio_prefix = f"{Path(ROOT_PATH).name}"
        minio_filepath = f"{minio_prefix}/{benchmark_job.id}.json"

        minio_api.upload_data(
            bucket_name,
            prefix=minio_prefix,
            token=minio_token,
            data=benchmark_job_run.model_dump_json().encode("utf-8"),
            objectname=Path(minio_filepath).name,
        )

        timestamp = datetime.datetime.now()
        sql_benchmark_api.create_benchmark_job(
            db,
            owner=user.username,
            bucket_name=user.minio_bucket_name,
            minio_location=minio_filepath,
            timestamp=timestamp,
            last_modified=timestamp,
            run=benchmark_job_run,
        )

    _, task_location_url, _ = task_creator.create_background_task(
        func=_run_benchmark,
        task_title=f"Benchmark job on device '{benchmark_config.edge_device.host}' with dataset '{dataset_name}' and model '{model_name}'.",
        db=db,
        user=user,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


def load_model(model_id: int, minio_token: str, db) -> tuple[str, str, BytesIO]:
    model = check_exists(sql_api.get_model(db, model_id))
    _validate_parameters(bucket=model.bucket_name, token=minio_token)

    model_name = f"models/{model_id}/{model.file_name}"
    model_bytes = minio_api.get_object(
        bucket=model.bucket_name, object_name=model_name, token=minio_token
    ).read()
    return model.name, (model.file_name, BytesIO(model_bytes))


def load_dataset(dataset_id: int, minio_token: str, db):
    dataset = check_exists(dataset_sql_api.get_dataset(db, dataset_id))
    _validate_parameters(dataset.bucket_name, minio_token)

    dataset_prefix = f"datasets/{dataset.id}"

    dataset_files: list[tuple[str, BytesIO]] = []
    for dataset_entry in minio_api.get_all_objects(
        bucket=dataset.bucket_name, prefix=dataset_prefix, token=minio_token
    ):
        if not dataset_entry.is_dir and "annotations" not in dataset_entry.object_name:
            sample_filename = Path(dataset_entry.object_name).name
            sample_bytes = minio_api.download_file(
                bucket=dataset.bucket_name, minio_item=dataset_entry, token=minio_token
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
        label_filename = Path(label_file.object_name).name
        labels = (label_filename, BytesIO(label_bytes))

    return (dataset.name, dataset_files), labels


def _validate_parameters(bucket, token):
    try:
        minio_api.valid_params(bucket, token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
