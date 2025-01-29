#!/usr/bin/env python

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

# -*- coding: utf-8 -*-

import os

from pathlib import Path
from typing import List, Dict

MOUNTED_DATASETS_ROOT_PATH = "/minio/datasets"
DATASETS_ROOT_PATH = "/datasets"

DATA_DIRS: Dict[str, Path] = {}


def get_dataset_path() -> Path:
    dataset_path = os.path.join(
        MOUNTED_DATASETS_ROOT_PATH, os.environ.get("DATASET_ID")
    )
    assert os.path.isdir(dataset_path), f"Dataset directory '{dataset_path}' not found."
    return Path(dataset_path)


def load_dataset_filepaths() -> List[Path]:
    dataset_path = get_dataset_path()
    return list(dataset_path.glob("*.*"))
