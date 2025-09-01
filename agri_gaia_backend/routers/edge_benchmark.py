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

from io import BytesIO
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse
from agri_gaia_backend.services import minio_api
from typing import List, Any, Optional, Dict, Annotated
from agri_gaia_backend.db import model_api as sql_model_api
from agri_gaia_backend.db import dataset_api as sql_dataset_api
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from edge_benchmarking_client.client import EdgeBenchmarkingClient
from agri_gaia_backend.db import edge_benchmark_api as sql_benchmark_api
from edge_benchmarking_types.edge_device.models import (
    DeviceHeader as TDeviceHeader,
    BenchmarkJob as TBenchmarkJob,
)
from edge_benchmarking_types.sensors.models import (
    SensorInfo as TSensorInfo,
    SensorConfig as TSensorConfig,
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
    create_single_file_response,
    create_zip_file_response,
)

load_dotenv()

ROOT_PATH = "/edge-benchmark"

EDGE_BENCHMARK_PATH = os.path.abspath("./edge-benchmark")
EDGE_BENCHMARK_FORMS_PATH = os.path.join(EDGE_BENCHMARK_PATH, "forms")

EdgeBenchmarkingClientDep = Annotated[
    EdgeBenchmarkingClient,
    Depends(
        lambda: EdgeBenchmarkingClient(
            protocol="https",
            host=os.getenv("EDGE_BENCHMARKING_URL"),
            username=os.getenv("EDGE_BENCHMARKING_USER"),
            password=os.getenv("EDGE_BENCHMARKING_PASSWORD"),
        )
    ),
]

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


@router.get("/forms/create")
async def get_benchmark_job_create_form() -> Dict:
    create_form_schema_filepath = os.path.join(
        EDGE_BENCHMARK_FORMS_PATH, "create.jsonschema"
    )
    with open(create_form_schema_filepath, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/forms/sensors")
async def get_benchmark_sensors_form() -> Dict:
    sensors_form_schema_filepath = os.path.join(
        EDGE_BENCHMARK_FORMS_PATH, "sensors.jsonschema"
    )
    with open(sensors_form_schema_filepath, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/jobs", response_model=List[BenchmarkJob])
async def get_all_benchmark_jobs(
    skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)
):
    return sql_benchmark_api.get_all_benchmark_jobs(skip=skip, limit=limit, db=db)


@router.delete("/jobs/{job_id}")
async def delete_benchmark_job(
    request: Request, job_id: int, db: Session = Depends(get_db)
) -> Response:
    user: KeycloakUser = request.user
    minio_token = user.minio_token

    benchmark_job: BenchmarkJob = check_exists(
        sql_benchmark_api.get_benchmark_job_by_id(db=db, job_id=job_id)
    )
    sql_benchmark_api.delete_benchmark_job(db=db, benchmark_job=benchmark_job)

    if minio_api.exists(
        bucket=benchmark_job.bucket_name,
        object_name=benchmark_job.minio_location,
        token=minio_token,
    ):
        minio_api.delete_object(
            bucket=benchmark_job.bucket_name,
            object_name=benchmark_job.minio_location,
            token=minio_token,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/results/{job_id}")
async def get_benchmark_job_results(
    request: Request, job_id: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
    _, results = _get_benchmark_job_result(job_id=job_id, request=request, db=db)
    return results


@router.get("/results/{job_id}/download")
async def download_benchmark_job_result(
    request: Request, job_id: int, db: Session = Depends(get_db)
) -> FileResponse:
    job, results = _get_benchmark_job_result(job_id=job_id, request=request, db=db)
    return create_single_file_response(
        file=json.dumps(results).encode("utf-8"),
        filename=Path(job.minio_location).name,
        content_type="application/json",
    )


@router.post("/results/download")
async def download_benchmark_job_results(
    request: Request,
    job_ids: list[int],
    db: Session = Depends(get_db),
) -> FileResponse:
    return create_zip_file_response(
        {
            Path(job.minio_location).name: json.dumps(result).encode("utf-8")
            for (job, result) in [
                _get_benchmark_job_result(job_id=job_id, request=request, db=db)
                for job_id in job_ids
            ]
        },
        filename="results.zip",
    )


@router.get("/device/header", response_model=List[TDeviceHeader])
async def get_device_headers(edge_benchmarking_client: EdgeBenchmarkingClientDep):
    return edge_benchmarking_client.get_device_headers()


@router.get("/device/{hostname}/info")
async def get_device_info(
    hostname: str, edge_benchmarking_client: EdgeBenchmarkingClientDep
) -> dict[str, Any]:
    return edge_benchmarking_client.get_device_info(hostname=hostname)


@router.get("/sensor", response_model=List[TSensorInfo])
async def get_sensors(edge_benchmarking_client: EdgeBenchmarkingClientDep):
    return edge_benchmarking_client.get_sensors()


@router.post("/sensor/{hostname}/capture")
async def capture_dataset(
    hostname: str,
    sensor_config: TSensorConfig,
    edge_benchmarking_client: EdgeBenchmarkingClientDep,
    background_tasks: BackgroundTasks,
) -> Response:
    dataset: List[Path] = edge_benchmarking_client.capture_dataset(
        root_dir="/tmp", hostname=hostname, sensor_config=sensor_config
    )
    if len(dataset) != 1:
        raise ValueError(f"Error capturing dataset using sensor '{hostname}'.")

    zip_dataset_filepath = dataset[0]
    background_tasks.add_task(zip_dataset_filepath.unlink, missing_ok=True)

    with open(zip_dataset_filepath, mode="rb") as fh:
        return create_single_file_response(
            file=fh.read(),
            filename=zip_dataset_filepath.name,
            content_type="application/x-zip-compressed",
        )


@router.post("/start")
async def edge_benchmark_start(
    request: Request,
    edge_benchmarking_client: EdgeBenchmarkingClientDep,
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
    created_at = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))

    benchmark_config = BenchmarkConfig(**payload["benchmark_config"])

    model_name, model = _load_model(model_id, minio_token, db)
    (dataset_name, dataset), labels = _load_dataset(dataset_id, minio_token, db)

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
        edge_benchmarking_client: EdgeBenchmarkingClientDep,
        db: Session,
        user: KeycloakUser,
    ) -> None:
        benchmark_job: TBenchmarkJob = edge_benchmarking_client.benchmark(
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
            created_at=created_at,
        )

        minio_prefix = f"{Path(ROOT_PATH).name}"
        minio_filepath = f"{minio_prefix}/{benchmark_job.id}.json"

        minio_api.upload_data(
            bucket=bucket_name,
            prefix=minio_prefix,
            token=minio_token,
            data=benchmark_job_run.model_dump_json().encode("utf-8"),
            objectname=Path(minio_filepath).name,
        )

        sql_benchmark_api.create_benchmark_job(
            db,
            owner=user.username,
            bucket_name=user.minio_bucket_name,
            minio_location=minio_filepath,
            timestamp=created_at,
            last_modified=created_at,
            run=benchmark_job_run,
        )

    _, task_location_url, _ = task_creator.create_background_task(
        func=_run_benchmark,
        edge_benchmarking_client=edge_benchmarking_client,
        task_title=f"Benchmark job on device '{benchmark_config.edge_device.host}' with dataset '{dataset_name}' and model '{model_name}'.",
        db=db,
        user=user,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


def _load_model(model_id: int, minio_token: str, db) -> tuple[str, str, BytesIO]:
    model = check_exists(sql_model_api.get_model(db, model_id))
    _validate_parameters(bucket=model.bucket_name, token=minio_token)

    model_name = f"models/{model_id}/{model.file_name}"
    model_bytes = minio_api.get_object(
        bucket=model.bucket_name, object_name=model_name, token=minio_token
    ).read()
    return model.name, (model.file_name, BytesIO(model_bytes))


def _load_dataset(dataset_id: int, minio_token: str, db):
    dataset = check_exists(sql_dataset_api.get_dataset(db, dataset_id))
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


def _get_benchmark_job_result(
    request: Request, db: Session, job_id: int
) -> tuple[BenchmarkJob, dict]:
    user: KeycloakUser = request.user
    minio_token = user.minio_token

    benchmark_job: BenchmarkJob = check_exists(
        sql_benchmark_api.get_benchmark_job_by_id(db=db, job_id=job_id)
    )
    return benchmark_job, json.loads(
        minio_api.get_object(
            bucket=benchmark_job.bucket_name,
            object_name=benchmark_job.minio_location,
            token=minio_token,
        )
        .read()
        .decode()
    )


def _validate_parameters(bucket, token):
    try:
        minio_api.valid_params(bucket, token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
