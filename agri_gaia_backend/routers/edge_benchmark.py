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
import uuid
import logging

from io import BytesIO
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.util import env
from agri_gaia_backend.util.datasets import (
    ANNOTATIONS_FILENAME,
    find_annotation_file_object,
    dataset_has_annotation_file,
)
from typing import Generator, List, Any, Optional, Dict, Annotated
from agri_gaia_backend.db.models import Dataset
from agri_gaia_backend.db import model_api as sql_model_api
from agri_gaia_backend.db import tasks_api
from agri_gaia_backend.db import dataset_api as sql_dataset_api
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from edge_benchmarking_client.client import EdgeBenchmarkingClient
from agri_gaia_backend.db import edge_benchmark_api as sql_benchmark_api
from edge_benchmarking_types.edge_device.models import (
    DeviceHeader as TDeviceHeader,
    DeviceInfo as TDeviceInfo,
    BenchmarkJob as TBenchmarkJob,
)
from edge_benchmarking_types.sensors.models import (
    SensorInfo as TSensorInfo,
    SensorConfig as TSensorConfig,
)
from agri_gaia_backend.schemas.edge_benchmark import (
    BenchmarkJobRun,
    BenchmarkJob,
    AutoSearchRequest,
    AutoSearchRun,
)
from edge_benchmarking_client.ranking import CandidateInput, rank_candidates
from edge_benchmarking_types.edge_farm.models import (
    BenchmarkConfig,
    TritonInferenceClient,
    DeviceCatalogEntry as TDeviceCatalogEntry,
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

# Upper bound on candidate devices per auto-search. A single request fans out to
# one (sequential) benchmark per device, so an unbounded list would tie up edge
# devices and background-task threads. Sized comfortably above the real fleet
# (edge-03..edge-21).
MAX_AUTO_SEARCH_CANDIDATES = 64

# Dedicated executor for benchmark/auto-search tasks. Keeping benchmarks off the
# shared TaskCreator pool means a flood of (long-running) benchmark jobs cannot
# starve other background work (training, dataset processing, image builds, ...).
BENCHMARK_EXECUTOR = ThreadPoolExecutor(
    max_workers=env.EDGE_BENCHMARK_MAX_WORKERS,
    thread_name_prefix="edge-benchmark",
)

# Titles created by the benchmark endpoints below; used to scope the per-user
# active-task limit to this feature without a task-category column.
BENCHMARK_TASK_TITLE_PREFIXES = ("Benchmark job", "Auto-search")


def _enforce_active_benchmark_task_limit(db: Session, username: str) -> None:
    """Reject (429) if the user already has the max active benchmark tasks.

    Bounds per-user fan-out so one user cannot monopolize the bounded benchmark
    executor or grow its queue without limit.
    """
    active = tasks_api.count_active_tasks_by_initiator(
        db, initiator=username, title_prefixes=BENCHMARK_TASK_TITLE_PREFIXES
    )
    if active >= env.EDGE_BENCHMARK_MAX_ACTIVE_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You already have {active} active benchmark task(s); "
                f"maximum is {env.EDGE_BENCHMARK_MAX_ACTIVE_PER_USER}. "
                "Wait for one to finish and try again."
            ),
            headers={"Retry-After": "30"},
        )


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


@router.get("/forms/job-create")
async def get_benchmark_job_create_form() -> Dict:
    create_form_schema_filepath = os.path.join(
        EDGE_BENCHMARK_FORMS_PATH, "job_create.jsonschema"
    )
    with open(create_form_schema_filepath, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/forms/sensor-add")
async def get_benchmark_sensor_add_form() -> Dict:
    create_form_schema_filepath = os.path.join(
        EDGE_BENCHMARK_FORMS_PATH, "sensor_info.jsonschema"
    )
    with open(create_form_schema_filepath, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/forms/sensor-config")
async def get_benchmark_sensor_config_form() -> Dict:
    schema_filepath = os.path.join(
        EDGE_BENCHMARK_FORMS_PATH, "sensor_config.jsonschema"
    )
    with open(schema_filepath, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/forms/sensor-info")
async def get_benchmark_sensor_info_form() -> Dict:
    schema_filepath = os.path.join(EDGE_BENCHMARK_FORMS_PATH, "sensor_info.jsonschema")
    with open(schema_filepath, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/jobs", response_model=List[BenchmarkJob])
async def get_all_benchmark_jobs(
    skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)
):
    return sql_benchmark_api.get_all_benchmark_jobs(skip=skip, limit=limit, db=db)


@router.get("/datasets/{dataset_id}/ground-truth")
async def get_dataset_ground_truth(
    request: Request, dataset_id: int, db: Session = Depends(get_db)
) -> Dict[str, bool]:
    """Whether a dataset has CVAT ground truth (annotations.xml) for accuracy.

    The benchmark create / auto-search UIs call this to warn that accuracy will
    be N/A before a run, steering the user to add annotations in the Datasets tab.
    """
    user: KeycloakUser = request.user
    dataset = check_exists(sql_dataset_api.get_dataset(db, dataset_id))
    return {"has_ground_truth": dataset_has_annotation_file(dataset, user.minio_token)}


def _delete_benchmark_job_record(
    db: Session, benchmark_job: BenchmarkJob, minio_token: str
) -> None:
    """Delete a benchmark job's DB row and its MinIO result object (if present)."""
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


@router.delete("/jobs/{job_id}")
async def delete_benchmark_job(
    request: Request, job_id: int, db: Session = Depends(get_db)
) -> Response:
    user: KeycloakUser = request.user
    minio_token = user.minio_token

    benchmark_job: BenchmarkJob = check_exists(
        sql_benchmark_api.get_benchmark_job_by_id(db=db, job_id=job_id)
    )
    _delete_benchmark_job_record(
        db=db, benchmark_job=benchmark_job, minio_token=minio_token
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
async def get_device_headers(
    edge_benchmarking_client: EdgeBenchmarkingClientDep,
) -> Any:
    return edge_benchmarking_client.get_device_headers()


@router.get("/device/{hostname}/info")
async def get_device_info(
    hostname: str, edge_benchmarking_client: EdgeBenchmarkingClientDep
) -> TDeviceInfo:
    return edge_benchmarking_client.get_device_info(hostname=hostname)


@router.get("/catalog", response_model=List[TDeviceCatalogEntry])
async def get_device_catalog(
    edge_benchmarking_client: EdgeBenchmarkingClientDep,
) -> Any:
    return edge_benchmarking_client.get_device_catalog()


@router.get("/sensor", response_model=List[TSensorInfo])
async def get_sensors(edge_benchmarking_client: EdgeBenchmarkingClientDep) -> Any:
    return edge_benchmarking_client.get_sensors()


@router.post("/sensor")
async def create_sensor(
    sensor_info: TSensorInfo, edge_benchmarking_client: EdgeBenchmarkingClientDep
) -> TSensorInfo:
    return edge_benchmarking_client.create_sensor(sensor_info=sensor_info)


@router.put("/sensor/{hostname}")
async def replace_sensor(
    hostname: str,
    sensor_info: TSensorInfo,
    edge_benchmarking_client: EdgeBenchmarkingClientDep,
) -> TSensorInfo:
    return edge_benchmarking_client.replace_sensor(
        hostname=hostname, sensor_info=sensor_info
    )


@router.delete("/sensor/{hostname}")
async def delete_sensor(
    hostname: str, edge_benchmarking_client: EdgeBenchmarkingClientDep
) -> Response:
    return edge_benchmarking_client.remove_sensor(hostname=hostname)


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

    _enforce_active_benchmark_task_limit(db, user.username)

    payload = json.loads(payload)

    dataset_id = payload["dataset_id"]
    model_id = payload["model_id"]
    chunk_size = payload["chunk_size"]
    created_at = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))

    benchmark_config = BenchmarkConfig(**payload["benchmark_config"])

    model_name, model = _load_model(model_id, minio_token, db)
    dataset = check_exists(sql_dataset_api.get_dataset(db, dataset_id))

    if isinstance(benchmark_config.inference_client, TritonInferenceClient):
        model_filename, _ = model
        benchmark_config.inference_client.model_name = Path(model_filename).stem
        benchmark_config.inference_client.model_version = "1"
        benchmark_config.inference_client.num_classes = 1

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
        dataset: Dataset = dataset,
    ) -> None:
        dataset_files, labels, annotation = _load_dataset(
            minio_token, dataset, chunk_size
        )

        benchmark_job: TBenchmarkJob = edge_benchmarking_client.benchmark(
            edge_device=benchmark_config.edge_device.host,
            dataset=dataset_files,
            model=model,
            inference_client=benchmark_config.inference_client,
            model_metadata=model_metadata,
            labels=labels,
            annotation=annotation,
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
        task_title=f"Benchmark job on device '{benchmark_config.edge_device.host}' with dataset '{dataset.name}' and model '{model_name}'.",
        executor=BENCHMARK_EXECUTOR,
        db=db,
        user=user,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


AUTO_SEARCH_PREFIX = f"{Path(ROOT_PATH).name}/auto-search"


@router.post("/auto-search")
async def edge_benchmark_auto_search(
    request: Request,
    edge_benchmarking_client: EdgeBenchmarkingClientDep,
    payload: str = Form(...),
    model_metadata: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> Response:
    """Benchmark a model across candidate devices and recommend the best one.

    Thin wrapper over the edge-benchmarking client's recommender building blocks:
    it benchmarks each candidate device (reusing the same per-device path as
    ``/start``, persisting each run as a normal benchmark job), then ranks the
    survivors of the latency constraint by the chosen factor via the client's
    ``rank_candidates``. Runs as a single background task; returns 202 + Location.
    """
    user: KeycloakUser = request.user
    minio_token = user.minio_token
    bucket_name = user.minio_bucket_name

    _enforce_active_benchmark_task_limit(db, user.username)

    auto_search_request = AutoSearchRequest(**json.loads(payload))
    created_at = auto_search_request.created_at

    # Dedupe (preserving order) and cap the candidate list before fanning out.
    candidate_hostnames = list(dict.fromkeys(auto_search_request.candidate_hostnames))
    if not candidate_hostnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one candidate device is required.",
        )
    if len(candidate_hostnames) > MAX_AUTO_SEARCH_CANDIDATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Too many candidate devices ({len(candidate_hostnames)}); "
                f"maximum is {MAX_AUTO_SEARCH_CANDIDATES}."
            ),
        )
    auto_search_request.candidate_hostnames = candidate_hostnames

    model_name, model = _load_model(auto_search_request.model_id, minio_token, db)
    dataset = check_exists(
        sql_dataset_api.get_dataset(db, auto_search_request.dataset_id)
    )

    benchmark_config = auto_search_request.benchmark_config
    if isinstance(benchmark_config.inference_client, TritonInferenceClient):
        model_filename, _ = model
        benchmark_config.inference_client.model_name = Path(model_filename).stem
        benchmark_config.inference_client.model_version = "1"
        benchmark_config.inference_client.num_classes = 1

    model_metadata = (
        (model_metadata.filename, BytesIO(await model_metadata.read()))
        if model_metadata is not None
        else None
    )

    def _run_auto_search(
        on_error,
        on_progress_change,
        edge_benchmarking_client: EdgeBenchmarkingClientDep,
        db: Session,
        user: KeycloakUser,
        dataset: Dataset = dataset,
    ) -> None:
        # Cost/tier metadata is optional: if the catalog is unreachable, energy
        # and latency searches still work; cost searches then exclude devices
        # with a clear reason instead of failing the whole run.
        try:
            catalog = edge_benchmarking_client.get_device_catalog()
        except Exception as e:
            logger.warning("Could not fetch device catalog: %s", e)
            catalog = []

        hostnames = auto_search_request.candidate_hostnames
        candidates: List[CandidateInput] = []

        for index, hostname in enumerate(hostnames):
            catalog_entry = edge_benchmarking_client.resolve_catalog_entry(
                hostname, catalog
            )

            # Per-device copy of the config: the inference client and edge device
            # must target this candidate's host.
            device_config = benchmark_config.model_copy(deep=True)
            device_config.edge_device.host = hostname
            device_config.inference_client.host = hostname

            try:
                # The dataset is a one-shot generator, so rebuild it per device.
                dataset_files, labels, annotation = _load_dataset(
                    minio_token, dataset, auto_search_request.chunk_size
                )

                benchmark_job: TBenchmarkJob = edge_benchmarking_client.benchmark(
                    edge_device=hostname,
                    dataset=dataset_files,
                    model=model,
                    inference_client=device_config.inference_client,
                    model_metadata=model_metadata,
                    labels=labels,
                    annotation=annotation,
                    chunk_size=auto_search_request.chunk_size,
                    cpu_only=device_config.cpu_only,
                    cleanup=True,
                )

                # Persist each per-device run as a normal benchmark job so it
                # shows up in the Jobs view and its charts can be drilled into.
                benchmark_job_run = BenchmarkJobRun(
                    dataset_id=auto_search_request.dataset_id,
                    model_id=auto_search_request.model_id,
                    benchmark_job=benchmark_job,
                    benchmark_config=device_config,
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
                db_job = sql_benchmark_api.create_benchmark_job(
                    db,
                    owner=user.username,
                    bucket_name=bucket_name,
                    minio_location=minio_filepath,
                    timestamp=created_at,
                    last_modified=created_at,
                    run=benchmark_job_run,
                )

                candidates.append(
                    CandidateInput(
                        hostname=hostname,
                        benchmark_job=benchmark_job,
                        benchmark_job_id=str(db_job.id),
                        catalog_entry=catalog_entry,
                    )
                )
            except Exception as e:
                logger.exception("Auto-search benchmark on '%s' failed.", hostname)
                candidates.append(
                    CandidateInput(
                        hostname=hostname,
                        catalog_entry=catalog_entry,
                        error=f"benchmark failed: {e}",
                    )
                )

            on_progress_change((index + 1) / len(hostnames))

        recommendation = rank_candidates(
            candidates,
            factor=auto_search_request.factor,
            latency_metric=auto_search_request.latency_metric,
            latency_threshold_ms=auto_search_request.latency_threshold_ms,
            min_accuracy=auto_search_request.min_accuracy,
            accuracy_metric=auto_search_request.accuracy_metric,
        )

        auto_search_run = AutoSearchRun(
            model_id=auto_search_request.model_id,
            dataset_id=auto_search_request.dataset_id,
            request=auto_search_request,
            recommendation=recommendation,
            created_at=created_at,
        )

        search_id = uuid.uuid4().hex
        minio_filepath = f"{AUTO_SEARCH_PREFIX}/{search_id}.json"
        minio_api.upload_data(
            bucket=bucket_name,
            prefix=AUTO_SEARCH_PREFIX,
            token=minio_token,
            data=auto_search_run.model_dump_json().encode("utf-8"),
            objectname=Path(minio_filepath).name,
        )

    _, task_location_url, _ = task_creator.create_background_task(
        func=_run_auto_search,
        edge_benchmarking_client=edge_benchmarking_client,
        task_title=(
            f"Auto-search ({auto_search_request.factor.value}) for model "
            f"'{model_name}' across {len(auto_search_request.candidate_hostnames)} "
            f"device(s) under {auto_search_request.latency_metric.value} latency "
            f"<= {auto_search_request.latency_threshold_ms} ms."
        ),
        executor=BENCHMARK_EXECUTOR,
        db=db,
        user=user,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


@router.get("/auto-search")
async def get_all_auto_searches(request: Request) -> List[dict]:
    user: KeycloakUser = request.user
    minio_token = user.minio_token
    bucket_name = user.minio_bucket_name

    runs: List[dict] = []
    for file_object in minio_api.get_all_objects(
        bucket=bucket_name, prefix=AUTO_SEARCH_PREFIX, token=minio_token
    ):
        if file_object.is_dir or not file_object.object_name.endswith(".json"):
            continue
        # Skip (don't fail the whole listing on) any object we can't read/parse.
        try:
            run = json.loads(
                minio_api.get_object(
                    bucket=bucket_name,
                    object_name=file_object.object_name,
                    token=minio_token,
                )
                .read()
                .decode()
            )
            # The run id lives only in the filename; expose it so the frontend
            # can open/delete a specific run.
            run["id"] = Path(file_object.object_name).stem
            runs.append(run)
        except (ValueError, OSError) as e:
            logger.warning(
                "Skipping unreadable auto-search result '%s': %s",
                file_object.object_name,
                e,
            )
    return runs


@router.get("/auto-search/results/{search_id}")
async def get_auto_search_result(request: Request, search_id: str) -> dict:
    user: KeycloakUser = request.user
    minio_token = user.minio_token
    bucket_name = user.minio_bucket_name

    object_name = f"{AUTO_SEARCH_PREFIX}/{search_id}.json"
    if not minio_api.exists(
        bucket=bucket_name, object_name=object_name, token=minio_token
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auto-search result '{search_id}' not found.",
        )
    return json.loads(
        minio_api.get_object(
            bucket=bucket_name, object_name=object_name, token=minio_token
        )
        .read()
        .decode()
    )


@router.delete("/auto-search/{search_id}")
async def delete_auto_search(
    request: Request, search_id: str, db: Session = Depends(get_db)
) -> Response:
    """Delete an auto-search run and cascade-delete the benchmark jobs it created."""
    user: KeycloakUser = request.user
    minio_token = user.minio_token
    bucket_name = user.minio_bucket_name

    object_name = f"{AUTO_SEARCH_PREFIX}/{search_id}.json"
    if not minio_api.exists(
        bucket=bucket_name, object_name=object_name, token=minio_token
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auto-search result '{search_id}' not found.",
        )

    run = json.loads(
        minio_api.get_object(
            bucket=bucket_name, object_name=object_name, token=minio_token
        )
        .read()
        .decode()
    )

    # Cascade-delete the benchmark jobs this run created. Skip candidates with no
    # job id (excluded/failed) and jobs that are already gone (e.g. deleted
    # manually from the Jobs view), so a partially-cleaned run still deletes.
    candidates = (run.get("recommendation") or {}).get("candidates") or []
    for candidate in candidates:
        raw_id = candidate.get("benchmark_job_id")
        if raw_id is None:
            continue
        try:
            job_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        benchmark_job = sql_benchmark_api.get_benchmark_job_by_id(db=db, job_id=job_id)
        if benchmark_job is None:
            continue
        _delete_benchmark_job_record(
            db=db, benchmark_job=benchmark_job, minio_token=minio_token
        )

    # Delete the run JSON last so a mid-cascade failure leaves it retryable.
    minio_api.delete_object(
        bucket=bucket_name, object_name=object_name, token=minio_token
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _load_model(model_id: int, minio_token: str, db) -> tuple[str, str, BytesIO]:
    model = check_exists(sql_model_api.get_model(db, model_id))
    _validate_parameters(bucket=model.bucket_name, token=minio_token)

    model_name = f"models/{model_id}/{model.file_name}"
    model_bytes = minio_api.get_object(
        bucket=model.bucket_name, object_name=model_name, token=minio_token
    ).read()
    return model.name, (model.file_name, BytesIO(model_bytes))


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def _is_image_sample(object_name: str) -> bool:
    return Path(object_name).suffix.lower() in IMAGE_EXTENSIONS


def _load_dataset(minio_token: str, dataset, chunk_size: int):
    _validate_parameters(dataset.bucket_name, minio_token)

    dataset_prefix = f"datasets/{dataset.id}"

    def dataset_generator() -> Generator[list[str, BytesIO], None, None]:
        all_objects = minio_api.get_all_objects(
            bucket=dataset.bucket_name, prefix=dataset_prefix, token=minio_token
        )
        # Only image files are valid benchmark samples. Exclude directories,
        # annotations and any non-image sidecars (e.g. EDC metadata folders)
        # that would otherwise be sent to the device and crash image decoding.
        all_objects_filtered = [
            file_object
            for file_object in all_objects
            if not file_object.is_dir and _is_image_sample(file_object.object_name)
        ]
        for i in range(0, len(all_objects_filtered), chunk_size):
            dataset_chunk = []
            for current_file in all_objects_filtered[i : i + chunk_size]:
                sample_filename = Path(current_file.object_name).name
                sample_bytes = minio_api.download_file(
                    bucket=dataset.bucket_name,
                    minio_item=current_file,
                    token=minio_token,
                ).read()
                dataset_chunk.append((sample_filename, BytesIO(sample_bytes)))
            yield dataset_chunk

    dataset_files: Generator[list[str, BytesIO], None, None] = dataset_generator()

    annotation_objects = list(
        minio_api.get_all_objects(
            dataset.bucket_name, f"{dataset_prefix}/annotations", minio_token
        )
    )

    label_files = [
        label_file
        for label_file in annotation_objects
        if Path(label_file.object_name).name != "annotations.xml"
    ]

    labels = None
    if len(label_files) == 1:
        label_file = label_files[0]
        label_bytes = minio_api.download_file(
            dataset.bucket_name, minio_token, label_file
        ).read()
        label_filename = Path(label_file.object_name).name
        labels = (label_filename, BytesIO(label_bytes))

    # CVAT ground-truth annotation (annotations.xml). When present, it is forwarded
    # to the Edge Farm API, which uses it to compute accuracy for the benchmark job.
    annotation = None
    annotation_object = find_annotation_file_object(dataset, minio_token)
    if annotation_object is not None:
        annotation_bytes = minio_api.download_file(
            dataset.bucket_name, minio_token, annotation_object
        ).read()
        annotation = (ANNOTATIONS_FILENAME, BytesIO(annotation_bytes))

    return dataset_files, labels, annotation


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
