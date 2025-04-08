#!/usr/bin/env python

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

# -*- coding: utf-8 -*-

import io
import os
import re
import glob
import json
import logging
import tempfile
import zipfile
from datetime import datetime
from distutils.dir_util import copy_tree
from operator import itemgetter
from shutil import copy
from typing import Dict, List, Optional
from itertools import chain

from agri_gaia_backend.db import dataset_api as dataset_sql_api
from agri_gaia_backend.db import train_api as sql_api
from agri_gaia_backend.db.models import Dataset
from agri_gaia_backend.schemas.model import Model
from agri_gaia_backend.routers.common import (
    TaskCreator,
    check_exists,
    create_single_file_response,
    get_db,
    get_task_creator,
)
from agri_gaia_backend.util.common import gpu_available
from agri_gaia_backend.routers.datasets import update_annotations_from_cvat
from agri_gaia_backend.routers.models import persist_model, persist_model_artifact
from agri_gaia_backend.schemas.keycloak_user import KeycloakUser
from agri_gaia_backend.schemas.train_container import TrainContainer
from agri_gaia_backend.services.docker import image_builder
from agri_gaia_backend.services.docker.client import host_client as docker_host_client
from agri_gaia_backend.util.train import (
    get_config_filepath,
    get_config_filepaths,
    get_container,
    get_container_status,
    get_dockerfile_filepath,
    jsonfile2dict,
    remove_container,
    remove_image,
    is_float,
    infer_model_format,
    validate_template,
    install_template,
    uninstall_template,
    get_onnx_model_filepath,
    read_from_container,
    get_config_with_schema,
    get_export_schema_filepath,
    update_train_container_config,
    update_train_container_dataset,
    read_train_container_config,
)
from docker.types import DeviceRequest, Ulimit
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from sqlalchemy.orm import Session
from jsonschema import validate

ROOT_PATH = "/train"

MODEL_TRAINING_PATH = os.path.abspath("./model-training")
TEMPLATES_PATH = os.path.join(MODEL_TRAINING_PATH, "templates")
EXPORT_PATH = os.path.join(MODEL_TRAINING_PATH, "export")
COMMON_PATH = os.path.join(MODEL_TRAINING_PATH, "common")
DATASETS_PATH = os.path.join(MODEL_TRAINING_PATH, "datasets")

VERIFY_SSL = False

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


def build_train_image(
    on_error,
    on_progress_change,
    db: Session,
    provider: str,
    category: str,
    architecture: str,
    dataset_id: int,
    train_config: Dict,
    export_config: Optional[Dict],
    train_configs_path: str,
    owner: str,
) -> None:
    try:
        dataset = check_exists(
            dataset_sql_api.get_dataset(db, dataset_id),
            detail=f"Dataset with id '{dataset_id}' does not exist.",
        )

        with tempfile.TemporaryDirectory() as context_directory:
            copy_tree(COMMON_PATH, context_directory)
            copy_tree(DATASETS_PATH, context_directory)

            dockerfile_filepath = get_dockerfile_filepath(
                TEMPLATES_PATH, provider, architecture
            )
            copy_tree(os.path.dirname(dockerfile_filepath), context_directory)
            copy(os.path.join(train_configs_path, "presets.json"), context_directory)
            copy(os.path.join(EXPORT_PATH, "export.py"), context_directory)

            with open(
                os.path.join(context_directory, "train_config.json"),
                "w",
                encoding="utf-8",
            ) as fh:
                json.dump(train_config, fh)

            with open(
                os.path.join(context_directory, "export_config.json"),
                "w",
                encoding="utf-8",
            ) as fh:
                if not export_config:
                    export_config = {}
                json.dump(export_config, fh)

            image_name = f"{provider}-{architecture.replace(' ', '_')}".lower()
            repository_url = (
                image_builder.create_repository_url(owner) + f"/{image_name}"
            )
            image_tag = datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + "-train"

            image_builder._build_and_push_image(
                context_directory=context_directory,
                repository_url=repository_url,
                image_tag=image_tag,
                platforms=["linux/amd64"],
                status_callback=lambda type, info: logger.info(
                    f"{type}: {json.dumps(info)}"
                ),
            )

        image_id = f"{repository_url}:{image_tag}"

        custom_config_filepath = os.path.join(train_configs_path, "custom.json")
        with open(custom_config_filepath, "r", encoding="utf-8") as fh:
            model_filepath, score_name, score_regexp = itemgetter(
                "model_filepath", "score_name", "score_regexp"
            )(json.load(fh))

        sql_api.create_train_container(
            db,
            owner=owner,
            image_id=image_id,
            repository=f"{owner}/{image_name}",
            tag=image_tag,
            last_modified=datetime.now(),
            provider=provider,
            category=category,
            architecture=architecture,
            dataset_id=dataset_id,
            dataset=dataset,
            model_filepath=model_filepath,
            score_name=score_name,
            score_regexp=score_regexp,
        )
    except HTTPException as e:
        error_msg = str(e.detail)
        logger.error(error_msg)
        on_error(error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        on_error(error_msg)


@router.post("/containers/{train_container_id}/run")
async def run_train_container(
    request: Request,
    train_container_id: int,
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> Response:
    user: KeycloakUser = request.user

    def _run_train_container(
        on_error,
        on_progress_change,
        db: Session,
        user: KeycloakUser,
        train_container_id: int,
    ) -> None:
        try:
            train_container: TrainContainer = check_exists(
                sql_api.get_train_container(db, train_container_id)
            )

            dataset: Dataset = check_exists(
                dataset_sql_api.get_dataset(db, train_container.dataset_id)
            )

            if train_container.container_id is not None:
                get_container(train_container.container_id).start()
            else:
                run_parameters = {
                    "image": train_container.image_id,
                    "environment": {
                        "OID_ACCESS_TOKEN": user.access_token,
                        "S3_HOST": "http://minio:9000",
                        "S3_BUCKET_NAME": train_container.dataset.bucket_name,
                        "DATASET_ID": dataset.id,
                    },
                    "network": f"{os.environ.get('PROJECT_NAME')}_network",
                    "privileged": True,
                    "cap_add": ["SYS_ADMIN"],
                    "devices": ["/dev/fuse:/dev/fuse"],
                    "detach": True,
                    "remove": False,
                    "ipc_mode": "host",
                    "ulimits": [
                        Ulimit(name="memlock", soft=-1, hard=-1),
                        Ulimit(name="stack", soft=67108864, hard=67108864),
                    ],
                }

                if gpu_available():
                    # See: https://github.com/docker/docker-py/blob/82cf559b5a641f53e9035b44b91f829f3b4cca80/docker/types/containers.py
                    gpu_device_ids = os.getenv("GPUS")
                    gpu_device_request = (
                        DeviceRequest(
                            name="nvidia",
                            device_ids=[gpu_device_ids],
                            capabilities=[["gpu"]],
                        )
                        if (
                            gpu_device_ids
                            and gpu_device_ids != "all"
                            and all(
                                map(lambda x: x.isdigit(), gpu_device_ids.split(","))
                            )
                        )
                        else DeviceRequest(
                            name="nvidia", count=-1, capabilities=[["gpu"]]
                        )
                    )

                    run_parameters["device_requests"] = [gpu_device_request]
                    run_parameters["environment"]["NVIDIA_VISIBLE_DEVICES"] = "all"

                container = docker_host_client.containers.run(**run_parameters)
                train_container.container_id = container.id

            train_container.score = None
            sql_api.update_train_container(db, train_container)

            if dataset.annotation_task_id is not None:
                update_annotations_from_cvat(dataset, user.minio_token)
        except Exception as e:
            on_error(str(e))

    _, task_location_url, _ = task_creator.create_background_task(
        _run_train_container,
        task_title=f"Run Train Container #{train_container_id}.",
        db=db,
        user=user,
        train_container_id=train_container_id,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


@router.patch("/containers/{train_container_id}/score")
def update_train_container_score(
    train_container_id: int, db: Session = Depends(get_db)
):
    train_container = check_exists(sql_api.get_train_container(db, train_container_id))
    train_container_status = get_container_status(train_container.container_id)
    if train_container_status != "exited":
        raise HTTPException(
            status_code=400,
            detail=f"Train Container #{train_container_id} has not exited.",
        )

    if train_container.score is not None:
        return train_container

    logs = get_container(train_container.container_id).logs(tail=50).decode("utf-8")

    score_regexp = re.compile(train_container.score_regexp)
    score_matches = re.findall(score_regexp, logs)

    if not score_matches:
        raise HTTPException(
            status_code=404,
            detail=f"No score for Train Container #{train_container_id} found in logs.",
        )

    try:
        if not isinstance(score_matches[0], str):
            score_matches = chain.from_iterable(score_matches)

        score = round(
            float(
                list(
                    filter(
                        is_float,
                        map(lambda s: s.strip(), score_matches),
                    )
                )[-1]
            ),
            3,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to extract score for Train Container #{train_container_id}: {str(e)}",
        ) from e

    train_container.score = score
    sql_api.update_train_container(db, train_container)
    return train_container


@router.post("/containers/{train_container_id}/stop")
def stop_train_container(
    train_container_id: int,
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> Response:
    def _stop_train_container(
        on_error,
        on_progress_change,
        db: Session,
        train_container_id: int,
    ) -> None:
        try:
            train_container: TrainContainer = check_exists(
                sql_api.get_train_container(db, train_container_id)
            )
            get_container(train_container.container_id).stop()
        except Exception as e:
            on_error(str(e))

    _, task_location_url, _ = task_creator.create_background_task(
        _stop_train_container,
        task_title=f"Stop Train Container #{train_container_id}.",
        db=db,
        train_container_id=train_container_id,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


@router.get("/containers", response_model=List[TrainContainer])
def get_train_containers(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    train_containers = sql_api.get_train_containers(db, skip=skip, limit=limit)
    for train_container in train_containers[:]:
        try:
            train_container.status = get_container_status(train_container.container_id)
            sql_api.update_train_container(db, train_container)
        # if get_container_status raises a "not found" exception, the container was removed from the host
        # consequently, it needs to be deleted from the database because it cannot be started again.
        except HTTPException:
            sql_api.delete_train_container(db, train_container)
            train_containers.remove(train_container)

    return train_containers


@router.get("/containers/{train_container_id}")
def get_train_container(train_container_id: int, db: Session = Depends(get_db)) -> Dict:
    return check_exists(sql_api.get_train_container(db, train_container_id))


@router.get("/containers/{train_container_id}/model")
async def get_train_container_model(
    request: Request, train_container_id: int, db: Session = Depends(get_db)
) -> Model:
    try:
        user: KeycloakUser = request.user

        train_container = check_exists(
            sql_api.get_train_container(db, train_container_id)
        )
        dataset = check_exists(
            dataset_sql_api.get_dataset(db, train_container.dataset_id),
        )

        generic_model_filepath = train_container.model_filepath
        onnx_model_filepath = get_onnx_model_filepath(generic_model_filepath)

        trained_models = {
            candidate_model_filepath: read_from_container(
                train_container.container_id, candidate_model_filepath
            )
            for candidate_model_filepath in (
                onnx_model_filepath,
                generic_model_filepath,
            )
        }

        if not any(trained_models.values()):
            raise HTTPException(
                status_code=404,
                detail=f"Trained model file not found in Train Container at {' or '.join(trained_models.keys())}.",
            )

        trained_model_data, trained_model_filepath = (
            (trained_models[onnx_model_filepath], onnx_model_filepath)
            if trained_models[onnx_model_filepath] is not None
            else (trained_models[generic_model_filepath], generic_model_filepath)
        )

        trained_model_filename = os.path.basename(trained_model_filepath)
        train_container_logs = get_container(train_container.container_id).logs()

        model: Model = persist_model(
            db=db,
            user=user,
            name=f"{train_container.architecture} ({train_container.provider}) [{dataset.name}, {train_container.score} {train_container.score_name}]",
            filename=trained_model_filename,
            model_file=io.BytesIO(trained_model_data),
            format=infer_model_format(trained_model_filename),
        )

        persist_model_artifact(
            user=user,
            model=model,
            filename="train.log",
            data=train_container_logs,
        )

        return model
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/containers/{train_container_id}/status")
def get_train_container_status(
    train_container_id: int, db: Session = Depends(get_db)
) -> Dict:
    train_container = check_exists(sql_api.get_train_container(db, train_container_id))
    return {
        "status": get_container_status(train_container.container_id),
        "score": train_container.score,
    }


@router.delete("/containers/{train_container_id}")
def delete_train_container(
    train_container_id: int, db: Session = Depends(get_db)
) -> Response:
    train_container = check_exists(sql_api.get_train_container(db, train_container_id))
    if train_container.container_id is not None:
        remove_container(train_container.container_id, force=True)
    # Do not force remove images as they could be used by multiple containers
    remove_image(train_container.image_id, force=False)
    sql_api.delete_train_container(db, train_container)
    return Response(status_code=204)


@router.patch("/containers/{train_container_id}", response_model=TrainContainer)
def update_train_container(
    train_container_id: int,
    train_container_update: TrainContainer,
    db: Session = Depends(get_db),
) -> TrainContainer:
    stored_train_container = check_exists(
        sql_api.get_train_container(db, train_container_id)
    )
    update_data = train_container_update.dict(exclude_unset=True)
    updated_train_container = stored_train_container.copy(update=update_data)
    sql_api.update_train_container(db, updated_train_container)

    return updated_train_container


@router.get("/containers/{train_container_id}/logs")
def get_train_container_logs(
    train_container_id: int,
    tail: int = None,
    max_length: int = 20000,
    db: Session = Depends(get_db),
) -> Dict:
    train_container = check_exists(sql_api.get_train_container(db, train_container_id))

    if train_container.container_id is None:
        raise HTTPException(status_code=404, detail="No logs found.")

    train_container = get_container(train_container.container_id)
    logs = (
        train_container.logs()
        if (tail is None or tail < 0)
        else train_container.logs(tail=tail)
    ).decode("utf-8")

    if tail is not None and len(logs) > max_length:
        logs = logs[-max_length:]

    return {"logs": logs}


@router.get("/containers/{train_container_id}/config")
def get_train_container_config(
    train_container_id: int,
    db: Session = Depends(get_db),
) -> Dict:
    train_container = check_exists(sql_api.get_train_container(db, train_container_id))

    if train_container.container_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"No Train Container '{train_container.container_id}' found.",
        )

    config_obj = {}
    for config_filename, config_key in [
        ("train_config.json", "train"),
        ("export_config.json", "export"),
    ]:
        config_json = read_train_container_config(
            config_filename=config_filename,
            train_container=train_container,
            templates_path=TEMPLATES_PATH,
        )

        if config_key == "train":
            schema_with_values = get_train_config_for_architecture(
                train_container.provider, train_container.architecture
            )
        elif config_key == "export":
            schema_with_values = get_export_config()
        else:
            raise KeyError(f"Unsupported configuration schema type '{config_key}'.")

        schema, config = itemgetter("schema", "values")(schema_with_values)

        config_obj[config_key] = {
            "schema": schema,
            "values": {k: v for k, v in config_json.items() if k in config},
            "empty": not config_json,
        }

    return {
        "container_id": train_container_id,
        "config": config_obj,
        "provider": train_container.provider,
        "architecture": {
            "category": train_container.category,
            "name": train_container.architecture,
        },
        "dataset_id": train_container.dataset_id,
    }


@router.get("/providers")
def get_providers() -> List[str]:
    return [
        os.path.basename(os.path.dirname(d))
        for d in glob.glob(os.path.join(TEMPLATES_PATH, "*", ""))
    ]


@router.get("/architectures/{provider}")
def get_architectures(provider: str) -> List[Dict]:
    config_filepaths = get_config_filepaths(TEMPLATES_PATH, provider, provider)
    return [
        {
            "category": config_filepath.parent.parent.parent.name,
            "name": config_filepath.parent.parent.name,
        }
        for config_filepath in config_filepaths
    ]


@router.post("/config")
async def process_train_config(
    request: Request,
    db: Session = Depends(get_db),
    task_creator: TaskCreator = Depends(get_task_creator),
) -> Response:
    user: KeycloakUser = request.user

    data = await request.json()

    (
        provider,
        category,
        architecture,
        dataset_id,
        train_config,
        export_config,
    ) = itemgetter(
        "provider",
        "category",
        "architecture",
        "dataset_id",
        "train_config",
        "export_config",
    )(
        data
    )

    config_filepath, _ = get_config_filepath(TEMPLATES_PATH, provider, architecture)
    train_configs_path = os.path.dirname(config_filepath)

    _, task_location_url, _ = task_creator.create_background_task(
        build_train_image,
        task_title=f"Train Container Buildjob: {architecture} ({provider})",
        db=db,
        provider=provider,
        category=category,
        architecture=architecture,
        dataset_id=dataset_id,
        train_config=train_config,
        export_config=export_config,
        train_configs_path=train_configs_path,
        owner=user.username,
    )

    headers = {"Location": task_location_url}
    return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)


@router.put("/config")
async def update_train_config(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict:
    data = await request.json()

    (
        train_config,
        export_config,
        dataset_id,
        train_container_id,
    ) = itemgetter(
        "train_config", "export_config", "dataset_id", "container_id"
    )(data)

    train_container = check_exists(sql_api.get_train_container(db, train_container_id))

    if train_container.container_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"No Train Container '{train_container.container_id}' found.",
        )

    for config, config_filename in [
        (train_config, "train_config.json"),
        (export_config, "export_config.json"),
    ]:
        update_train_container_config(
            config=config,
            config_filename=config_filename,
            train_container=train_container,
            templates_path=TEMPLATES_PATH,
        )

    update_train_container_dataset(
        db=db,
        dataset_id=dataset_id,
        train_container=train_container,
        templates_path=TEMPLATES_PATH,
    )

    return {
        "train_config": train_config,
        "export_config": export_config,
        "container": train_container,
    }


@router.get("/config/{provider}/{architecture}")
def get_train_config_for_architecture(provider: str, architecture: str) -> Dict:
    config_filepath, _ = get_config_filepath(TEMPLATES_PATH, provider, architecture)
    train_json_schema, train_config_values = get_config_with_schema(config_filepath)

    return {
        "schema": train_json_schema,
        "values": train_config_values,
    }


@router.post("/config/download")
async def download_train_config(request: Request):
    data = await request.json()

    provider, architecture, train_config = itemgetter(
        "provider", "architecture", "train_config"
    )(data)

    _, ext = get_config_filepath(TEMPLATES_PATH, provider, architecture)

    train_config = json.dumps(train_config, indent=4)

    if ext == ".jsonschema":
        ext = ".json"

    now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    return create_single_file_response(
        bytes(train_config, "utf-8"),
        filename=f"{provider.lower()}-{architecture.lower()}_{now}-train{ext}",
        content_type="application/json",
    )


@router.post("/config/upload")
def upload_train_config(
    provider: str = Form(...),
    architecture: str = Form(...),
    config_file: UploadFile = File(...),
) -> Dict:
    try:
        config_filepath, ext = get_config_filepath(
            TEMPLATES_PATH, provider, architecture
        )
        if ext != ".jsonschema":
            raise RuntimeError
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Unable to verify schema of configuration file.",
        ) from e

    try:
        train_config_values = json.loads(config_file.file.read().decode("utf-8"))
        train_config_schema = jsonfile2dict(config_filepath)
        validate(train_config_values, train_config_schema)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return train_config_values


@router.get("/config/export")
def get_export_config() -> Dict:
    export_schema_filepath = get_export_schema_filepath(EXPORT_PATH)
    export_json_schema, export_config_values = get_config_with_schema(
        export_schema_filepath
    )

    return {
        "schema": export_json_schema,
        "values": export_config_values,
    }


@router.post("/template/upload", status_code=status.HTTP_201_CREATED)
def upload_train_container_template(
    template_zip: UploadFile = File(...),
) -> Dict:
    try:
        with tempfile.TemporaryDirectory() as template_directory:
            zip_bytes = template_zip.file.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(template_directory)

            template_directory_entries = os.listdir(template_directory)
            if len(template_directory_entries) != 1 or not os.path.isdir(
                os.path.join(template_directory, template_directory_entries[0])
            ):
                raise RuntimeError("Archive did not extract as a single directory.")

            template_dirname = template_directory_entries[0]
            template_root_dir = os.path.join(template_directory, template_dirname)
            provider, category, architecture = validate_template(
                MODEL_TRAINING_PATH, template_root_dir
            )
            install_template(
                TEMPLATES_PATH, template_root_dir, provider, category, architecture
            )
            return {
                "provider": provider,
                "architecture": {"category": category, "name": architecture},
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/template")
async def delete_train_container_template(request: Request) -> Response:
    data = await request.json()
    provider, architecture = itemgetter("provider", "architecture")(data)
    uninstall_template(TEMPLATES_PATH, provider, architecture)
    return Response(status_code=204)
