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

import json
from pathlib import Path
from typing import Dict, List

from config import finalize_config
from cvat_dataset import (
    create_directory_structure,
    get_cvat_dataset,
    as_coco,
    create_train_images,
    create_test_images,
    create_train_labels,
    create_test_labels,
)


def _create_labels(
    labels_path: Path,
    label_names: List[str],
    files_with_annotations: Dict[Path, Dict],
) -> None:
    labels = as_coco(label_names, files_with_annotations, dataset_type="classification")
    with open(labels_path.joinpath("labels.json"), "w") as fh:
        json.dump(labels, fh)


if __name__ == "__main__":
    config, label_names, train_data, val_data = get_cvat_dataset()

    create_directory_structure()

    create_train_labels(_create_labels, train_data, label_names)
    create_test_labels(_create_labels, val_data, label_names)

    create_train_images(train_data)
    create_test_images(val_data)

    finalize_config(config)
