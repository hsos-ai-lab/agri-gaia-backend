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

import io
import json
import os
import pathlib
import tarfile
from typing import Dict

from agri_gaia_backend.db.models import Model, ModelFormat
from agri_gaia_backend.services import minio_api

import logging

logger = logging.getLogger("api-logger")


def get_build_context_from_project_files(paths: Dict[str, str]) -> Dict[str, Dict]:
    """This function

    Args:
        paths: A dictionary that maps from the source paths of the files from the filesystem to the destination paths of the files in the build context.
    Returns:
        A dictionary that maps from the paths in the build context to a dictionary that contains the file content and the file permissions
    """
    build_context = {}

    for src_path, dest_path in paths.items():
        stat_info = os.stat(src_path)
        with open(src_path, "rb") as file:
            file_content = file.read()
        build_context[dest_path] = dict(content=file_content, stat_info=stat_info)

    return build_context


def pack_to_tar(build_context: Dict[str, Dict]) -> bytes:
    memoryfile = io.BytesIO()
    with tarfile.open(fileobj=memoryfile, mode="w:gz") as tar:
        for path, file_dict in build_context.items():
            info = tarfile.TarInfo(path)
            info.size = len(file_dict["content"])
            if file_dict["stat_info"] is not None:
                info.mode = file_dict["stat_info"].st_mode
            tar.addfile(info, io.BytesIO(file_dict["content"]))
    memoryfile.seek(0)
    return memoryfile.read()


def get_model_blob(model: Model):
    bucket = model.bucket_name
    object_name = f"models/{model.id}/{model.file_name}"
    return minio_api.get_admin_client().get_object(bucket, object_name).read()


def get_metadata_for_image_build(model: Model) -> Dict:
    return {
        "name": model.name,
        "format": model.format.value if model.format else None,
        "input_name": model.input_name,
        "input_datatype": model.input_datatype.value if model.input_datatype else None,
        "input_shape": model.input_shape,
        "input_semantics": (
            model.input_semantics.value if model.input_semantics else None
        ),
        "output_name": model.output_name,
        "output_datatype": (
            model.output_datatype.value if model.output_datatype else None
        ),
        "output_shape": model.output_shape,
        "output_labels": model.output_labels,
    }


def _get_project_files(template_directory: pathlib.Path) -> Dict[str, str]:
    paths = [str(path) for path in template_directory.glob("**/*")]
    paths = {
        path: os.path.relpath(path, template_directory)
        for path in paths
        if os.path.isfile(path)
    }
    return paths


def _get_model_file_extension_from_format(model: Model) -> str:
    mapping = {
        ModelFormat.onnx: "onnx",
        ModelFormat.pytorch: "pt",
        ModelFormat.tensorrt: "trt",
    }
    extension = mapping.get(model.format, None)
    if extension is None:
        logger.warning(
            f"Couldn't infer file extension for model '{model.name}' with format '{model.format}'. Using extension of model file"
        )
        extension = pathlib.Path(model.file_name).suffix.replace(".", "")
    return extension


def create_tar_build_context(template_directory: pathlib.Path, model: Model) -> bytes:
    paths = _get_project_files(template_directory)
    build_context = get_build_context_from_project_files(paths)

    model_blob = get_model_blob(model)
    model_file_extension = _get_model_file_extension_from_format(model)
    model_file_path = f"models/model.{model_file_extension}"
    build_context[model_file_path] = dict(content=model_blob, stat_info=None)

    model_metadata = json.dumps(get_metadata_for_image_build(model), indent=4)
    build_context["models/model.json"] = dict(
        content=model_metadata.encode("utf-8"), stat_info=None
    )
    return pack_to_tar(build_context)
