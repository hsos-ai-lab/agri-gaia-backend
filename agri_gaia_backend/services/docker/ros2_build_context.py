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

import pathlib
import os
from typing import Dict

import yaml
from agri_gaia_backend.db.models import Model

from agri_gaia_backend.schemas.container_image import Ros2ContainerConfig
from agri_gaia_backend.services.docker import image_util

RESOURCE_DIR = os.path.abspath("./inference-images/ros2")


def create_tar_build_context(model: Model, ros2config: Ros2ContainerConfig) -> bytes:
    paths = _get_project_files()
    build_context = image_util.get_build_context_from_project_files(paths)

    model_blob = image_util.get_model_blob(model)
    build_context["models/model.onnx"] = dict(content=model_blob, stat_info=None)

    config = _create_node_config(model, ros2config)
    build_context["ros_2_infer/config/config.yaml"] = dict(
        content=yaml.dump(config).encode("utf-8"), stat_info=None
    )

    return image_util.pack_to_tar(build_context)


def _get_project_files() -> Dict[str, str]:
    ros2_dir = os.path.join(RESOURCE_DIR, "ros_2_infer")
    paths = [str(path) for path in pathlib.Path(ros2_dir).glob("**/*")]
    paths = {
        path: os.path.relpath(path, RESOURCE_DIR)
        for path in paths
        if os.path.isfile(path)
    }
    docker_entrypoint_path = os.path.join(RESOURCE_DIR, "docker-entrypoint.sh")
    dockerfile_path = os.path.join(RESOURCE_DIR, "Dockerfile")
    paths[docker_entrypoint_path] = "docker-entrypoint.sh"
    paths[dockerfile_path] = "Dockerfile"
    return paths


def _create_node_config(model: Model, ros2config: Ros2ContainerConfig) -> Dict:
    node_config = {
        "active_rgb": True,
        "rgb_topic_name": ros2config.sub_topic,
        "dect_rgb_topic": ros2config.pub_topic,
    }

    shape_hwc = _input_shape_as_hwc(model)

    inference_config = {
        "input_tensor_shape": shape_hwc,
        "model_path": "/models/model.onnx",
        "class_names": model.output_labels,
    }

    config = {
        "/camera_listener": {
            "ros__parameters": {
                "camera": node_config,
                "inference": inference_config,
            }
        }
    }
    return config


def _input_shape_as_hwc(model: Model):
    shape, semantics = model.input_shape, model.input_semantics
    return [shape[semantics.value.index(channel)] for channel in "HWC"]
