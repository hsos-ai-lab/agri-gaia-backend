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

import re
import io
import logging
import os
import tarfile
import tempfile
from typing import Callable, Dict, List, Union

import python_on_whales


from agri_gaia_backend.db.models import EdgeDevice, InferenceContainerTemplate, Model
from agri_gaia_backend.services.container_template.definitions import (
    INFERENCE_CONTAINER_TEMPLATES_DIR,
)
from agri_gaia_backend.services.docker.client import build_container_client as docker
from agri_gaia_backend.services.docker import image_util
from agri_gaia_backend.services.minio_api.client import (
    MINIO_HOST,
    MINIO_IP_ADDRESS,
)

logger = logging.getLogger("api-logger")

REGISTRY_URL = os.environ.get("REGISTRY_URL")


class MissingInputDataException(Exception):
    def __init__(
        self, model_properties: List[str] = [], device_properties: List[str] = []
    ):
        self.model_properties = model_properties
        self.device_properties = device_properties


def _get_device_metadata(edge_info: Union[EdgeDevice, Dict]):
    if isinstance(edge_info, Dict):
        device_metadata = edge_info
    else:
        device_metadata = {"device_type": "generic", "architecture": edge_info.arch}

    return device_metadata


def _validate_device_metadata(edge_info: Union[EdgeDevice, Dict]) -> List[str]:
    if not edge_info["architecture"]:
        return ["architecture"]
    return []


def _validate_model_properties(model: Model) -> List[str]:
    required_properties = [
        "input_shape",
        "input_datatype",
        "input_semantics",
        "output_datatype",
        "output_shape",
        "format",
    ]
    empty_required_properties = [
        propertyname
        for propertyname, propertyvalue in model.__dict__.items()
        if propertyname in required_properties and propertyvalue is None
    ]
    return empty_required_properties


def _create_fs_build_context(build_context: bytes, directory: str):
    memoryfile = io.BytesIO(build_context)
    with tarfile.open(fileobj=memoryfile, mode="r:gz") as tar:
        tar.extractall(directory)


def create_repository_url(repository_name: str) -> str:
    return f"{REGISTRY_URL}/{repository_name}"


def validate_generator_input(model: Model, edge_info: Union[EdgeDevice, Dict]) -> None:
    invalid_model_props = _validate_model_properties(model)
    device_metadata = _get_device_metadata(edge_info)
    invalid_device_props = _validate_device_metadata(device_metadata)

    if invalid_model_props or invalid_device_props:
        raise MissingInputDataException(invalid_model_props, invalid_device_props)


def build_and_push_image(
    inference_container_template: InferenceContainerTemplate,
    repository_name: str,
    image_tag: str,
    model: Model,
    edge_info: Union[EdgeDevice, Dict],
    status_callback: Callable[[str, dict], None] = lambda x, y: None,
) -> str:
    """
    Either device metadata or edge_device must be given
    """
    repository_url = create_repository_url(repository_name)
    device_metadata = _get_device_metadata(edge_info)

    invalid_model_props = _validate_model_properties(model)
    invalid_device_props = _validate_device_metadata(device_metadata)

    if invalid_model_props or invalid_device_props:
        raise MissingInputDataException(invalid_model_props, invalid_device_props)

    container_template_dir = (
        INFERENCE_CONTAINER_TEMPLATES_DIR / inference_container_template.dirname
    )

    build_context = image_util.create_tar_build_context(container_template_dir, model)

    with tempfile.TemporaryDirectory() as tempdirname:
        _create_fs_build_context(build_context, tempdirname)
        _build_and_push_image(
            tempdirname,
            repository_url=repository_url,
            image_tag=image_tag,
            platforms=[device_metadata["architecture"]],
            status_callback=status_callback,
            add_hosts={MINIO_HOST: MINIO_IP_ADDRESS},
        )

    return f"{repository_url}:{image_tag}"


def _build_and_push_image(
    context_directory: str,
    repository_url: str,
    image_tag: str,
    status_callback: Callable[[str, dict], None],
    **kwargs,
):
    """Builds an image from the given dockerfile.

    Args:
        context_directory   : the directory in the filesystem or the build context
        repository_url      : the repository url that the image will be tagged with.
        image_tag           : the tag that the image will get (only the part after the colon).
        status_callback     : a callback function for statusupdates during the build
        buildargs           : additional arguments that can be used in build phase
        network             : the network the build container shall connect to. Set this to 'host'
            if the build container needs to connect to the platform services in RUN statements.
            This should only be used for static, non user provided dockerfiles!
    """
    repository_url_with_tag = f"{repository_url}:{image_tag}"
    try:
        logs_generator = docker.buildx.build(
            context_path=context_directory,
            tags=repository_url_with_tag,
            pull=True,
            push=True,
            stream_logs=True,
            **kwargs,
        )

        build_successful = True
        for log in logs_generator:
            status_callback("update", log)

    except python_on_whales.exceptions.DockerException as e:
        status_callback("failed", {"reason": str(e)})
        raise e
