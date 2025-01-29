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

import datetime
from enum import Enum
import json
import logging
import os
import copy
from io import BytesIO
from typing import List
from agri_gaia_backend.schemas.benchmark_device import BenchmarkDevice
from dotenv import load_dotenv, dotenv_values
from agri_gaia_backend.services import minio_api
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
import requests
from agri_gaia_backend.routers.common import (
    TaskCreator,
    check_exists,
    get_db,
    get_task_creator,
)
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.db import model_api as sql_api
from agri_gaia_backend.db import dataset_api as dataset_sql_api
from agri_gaia_backend.db import tasks_api
from agri_gaia_backend.db import benchmark_api as sql_benchmark_api
from agri_gaia_backend.util.benchmark import get_all_datasets

from edge_benchmarking_client.client import EdgeBenchmarkingClient
from edge_benchmarking_types.edge_farm.models import TritonInferenceClientConfig
from tritonclient.grpc import model_config_pb2
from google.protobuf import json_format
from agri_gaia_backend.util.common import get_stacktrace
from agri_gaia_backend.schemas.benchmark import Benchmark


ROOT_PATH = "/edge-benchmark"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)
load_dotenv()


class Datatypes(Enum):
    float16 = "TYPE_FP16"
    float32 = "TYPE_FP32"
    float64 = "TYPE_FP64"
    int8 = "TYPE_INT8"
    int16 = "TYPE_INT16"
    int32 = "TYPE_INT32"
    int64 = "TYPE_INT64"
    uint8 = "TYPE_UINT8"
    uint16 = "TYPE_UINT16"
    uint32 = "TYPE_UINT32"
    uint64 = "TYPE_UINT64"
    bool = "TYPE_BOOL"
    string = "TYPE_STRING"


@router.get("", response_model=List[Benchmark])
def get_all_benchmarks(
    skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)
):
    return sql_benchmark_api.get_benchmarks(skip=skip, limit=limit, db=db)


@router.get("/devices", response_model=List[BenchmarkDevice])
def get_all_devices():
    """
    Fetches all Benchmarking Devices from the edge farm manager

    Returns:
        A list of all devices, which are stored by the edge farm.
    """

    json = requests.get(
        f"https://{os.getenv("EDGE_BENCHMARKING_URL")}/device/header",
        auth=(os.getenv("EDGE_BENCHMARKING_USER"), os.getenv("EDGE_BENCHMARKING_PASSWORD")),
    ).json()
    return json


@router.post("")
def run_benchmark(
    request: Request,
    models: List[int],
    datasets: List[int],
    devices: List[BenchmarkDevice],
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> None:
    user: KeycloakUser = request.user

    def benchmark(
        on_error,
        on_progress_change,
        db: Session,
        user: KeycloakUser,
        models,
        datasets,
    ) -> dict:
        # Connection information
        PROTOCOL = "https"
        HOST = os.getenv("EDGE_BENCHMARKING_URL")

        # Basic API authentication
        BASIC_AUTH_USERNAME = os.getenv("EDGE_BENCHMARKING_USER")
        BASIC_AUTH_PASSWORD = os.getenv("EDGE_BENCHMARKING_PASSWORD")

        token = user.minio_token
        bucket = user.minio_bucket_name

        # loading all model configs and model files into dicts
        model_files, model_configs = load_models(models, token, db, user)

        for dataset_id in datasets:
            dataset_files, annotations = load_dataset(dataset_id, db, user)

            for key in model_files:
                for device in devices:
                    client = EdgeBenchmarkingClient(
                        protocol=PROTOCOL,
                        host=HOST,
                        username=BASIC_AUTH_USERNAME,
                        password=BASIC_AUTH_PASSWORD,
                    )

                    # TODO Client Config not complete
                    inference_client_config = TritonInferenceClientConfig(
                        host=device.hostname,
                        model_name="densenet_onnx",
                        num_classes=1,
                        scaling="inception",
                    )

                    benchmark_job = client.benchmark(
                        edge_device=device.hostname,
                        dataset=dataset_files,
                        model=model_files[key],
                        inference_client_config=inference_client_config,
                        model_metadata=None,
                        labels=annotations,
                        cleanup=True,
                    )

                    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    minio_api.upload_data(
                        bucket,
                        prefix=f"benchmark/{benchmark_job.id}",
                        token=token,
                        data=json.dumps(benchmark_job.benchmark_results).encode(
                            "utf-8"
                        ),
                        objectname="benchmark.json",
                    )

                    minio_api.upload_data(
                        bucket,
                        prefix=f"benchmark/{benchmark_job.id}",
                        token=token,
                        data=json.dumps(benchmark_job.inference_results).encode(
                            "utf-8"
                        ),
                        objectname="inference.json",
                    )

                    metadata = {
                        "time": time,
                        "dataset": dataset_id,
                        "edge_device": {
                            "device_ip": device.ip,
                            "device_name": device.hostname,
                        },
                        "job_id": benchmark_job.id,
                    }

                    minio_api.upload_data(
                        bucket,
                        prefix=f"benchmark/{benchmark_job.id}",
                        token=token,
                        data=json.dumps(metadata).encode("utf-8"),
                        objectname="metadata.json",
                    )

                    created_benchmark = _create_initial_entry_postgres(
                        db=db,
                        user=user,
                        benchmark_name=f"{benchmark_job.id}",
                        dataset_id=dataset_id,
                        job_id=benchmark_job.id,
                        device_ip=device.ip,
                        device_name=device.name,
                    )

        return

    # response = client.upload_benchmark_data()

    _, task_location_url, _ = task_creator.create_background_task(
        func=benchmark,
        task_title=f"Inference for Model(s) {models} and Dataset(s) {datasets}.",
        db=db,
        user=user,
        models=models,
        datasets=datasets,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


@router.get("/{hostname}/info")
def get_benchmarking_info(hostname: str):
    """
    Fetches Benchmarking Info for one Device from the edge farm manager
    """
    json = requests.get(
        f"https://{os.getenv("EDGE_BENCHMARKING_URL")}/device/{hostname}/info",
        auth=(os.getenv("EDGE_BENCHMARKING_USER"), os.getenv("EDGE_BENCHMARKING_PASSWORD")),
    ).json()

    return json


def load_models(models, token, db, user):
    model_files = {}
    model_configs = {}
    for model_id in models:
        model = check_exists(sql_api.get_model(db, model_id))

        bucket_name = model.bucket_name
        token = user.minio_token
        model_prefix = f"models/{model.id}"

        _validate_parameters(bucket_name, token)

        for item in minio_api.get_all_objects(
            bucket_name, prefix=model_prefix, token=token
        ):
            if item.is_dir is False:
                # TODO filenames hardcoded
                model_files[item.object_name] = (
                    "densenet_onnx.onnx",
                    BytesIO(minio_api.download_file(bucket_name, token, item).read()),
                )

                # currently only using Tritons autoconfig feature
                # model_configs[item.object_name] = None

                model_configs[item.object_name] = load_config(model, item.object_name)
    return model_files, model_configs


def load_config(model, name):
    # create the actual config as protobuf
    # TODO: currently only onnx
    # TODO: fix dims when batchsize is given
    config = {
        "platform": "onnxruntime_onnx",
        "name": "densenet_onnx",
        "max_batch_size": 1,
        "input": [
            {
                "name": model.input_name,
                "data_type": Datatypes[model.input_datatype.value].value,
                "dims": model.input_shape[1:],
                "reshape": {"shape": [1, 3, 244, 244]},
                "format": "FORMAT_" + model.input_semantics.value,
            }
        ],
        "output": [
            {
                "name": model.output_name,
                "data_type": Datatypes[model.output_datatype.value].value,
                "dims": [model.output_shape[1]],
                "reshape": {"shape": [1, 1000, 1, 1]},
                "label_filename": "label.txt",
            }
        ],
    }

    logger.info(config)
    cf = model_config_pb2.ModelConfig()
    cf = json_format.ParseDict(config, cf)
    logger.info(str(cf))

    return ("config.pbtxt", BytesIO(str(cf).encode()))


def load_dataset(dataset_id, db, user):
    dataset = check_exists(dataset_sql_api.get_dataset(db, dataset_id))

    bucket_name = dataset.bucket_name
    token = user.minio_token
    dataset_prefix = f"datasets/{dataset.id}"

    _validate_parameters(bucket_name, token)

    dataset_files = []
    for item in minio_api.get_all_objects(
        bucket_name, prefix=dataset_prefix, token=token
    ):
        if item.is_dir is False and "annotations" not in item.object_name:
            dataset_files.append(
                (
                    item.object_name.split("/")[-1],
                    BytesIO(minio_api.download_file(bucket_name, token, item).read()),
                )
            )

    annotation_files = minio_api.get_all_objects(
        bucket_name, f"{dataset_prefix}/annotations", token
    )
    if len(annotation_files) != 1:
        annotations = None
    else:
        annotations = (
            "label.txt",
            BytesIO(
                minio_api.download_file(bucket_name, token, annotation_files[0]).read()
            ),
        )

    return dataset_files, annotations


def _validate_parameters(bucket, token):
    try:
        minio_api.valid_params(bucket, token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _create_initial_entry_postgres(
    db: Session,
    user: KeycloakUser,
    benchmark_name: str,
    dataset_id: int,
    job_id: int,
    device_ip: str,
    device_name: str,
):
    """Created an initial entry for the Inference Result in the Postgres database.

    Args:
        db: Database Session.
        user: Information on the user, who wants to create the Inference Result.
        name: The name of the Inference Result.

    Returns:
        The instance of the created Inference Result.

    Raises:
        HTTPException: If there are problems during creation of the Inference Result.
    """
    try:
        # Replace Inference Result name by name(2), (3)... if name already exist
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
        logger.error("Saving into Postgres failed. Stacktrace:\n" + get_stacktrace(e))
        raise HTTPException(
            status_code=500,
            detail="Initial Creation of Service failed. Please try again.",
        )
