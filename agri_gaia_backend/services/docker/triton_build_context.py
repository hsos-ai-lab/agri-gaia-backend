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
import pathlib
import re
import json
from typing import Dict
from agri_gaia_backend.db.models import Model
from agri_gaia_backend.services.docker import image_util

RESOURCE_DIR = os.path.abspath("./inference-images/triton")


def create_tar_build_context(model: Model) -> bytes:
    paths = _get_project_files()
    build_context = image_util.get_build_context_from_project_files(paths)

    model_blob = image_util.get_model_blob(model)
    build_context["models/model.onnx"] = dict(content=model_blob, stat_info=None)

    model_metadata = json.dumps(
        image_util.get_metadata_for_image_build(model), indent=4
    )
    build_context["models/model.json"] = dict(
        content=model_metadata.encode("utf-8"), stat_info=None
    )
    return image_util.pack_to_tar(build_context)


def _get_project_files() -> Dict[str, str]:
    paths = [str(path) for path in pathlib.Path(RESOURCE_DIR).glob("**/*")]
    paths = {
        path: os.path.relpath(path, RESOURCE_DIR)
        for path in paths
        if os.path.isfile(path)
    }
    return paths
