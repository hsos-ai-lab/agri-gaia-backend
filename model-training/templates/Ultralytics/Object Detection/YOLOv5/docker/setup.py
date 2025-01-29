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

import yaml

from pathlib import Path
from typing import Dict, List
from config import finalize_config
from dataset import DATA_DIRS

from cvat_dataset import (
    get_cvat_dataset,
    as_yolo,
    create_directory_structure,
    create_train_images,
    create_test_images,
    create_train_labels,
    create_test_labels,
)

DATASET_YAML_FILEPATH = "./dataset.yaml"


def _create_labels(
    labels_path: Path,
    label_names: List[str],
    files_with_annotations: Dict[Path, Dict],
) -> None:
    labels = as_yolo(label_names, files_with_annotations)
    for filepath, annotation_entries in labels.items():
        annotation_entries = list(map(lambda s: f"{s}\n", annotation_entries))
        with open(labels_path.joinpath(f"{filepath.stem}.txt"), "w") as fh:
            fh.writelines(annotation_entries)


def _create_dataset_yaml(label_names: List[str]) -> None:
    dataset_config = {
        "train": str(DATA_DIRS["images_train"]),
        "val": str(DATA_DIRS["images_val"]),
        "nc": len(label_names),
        "names": label_names,
    }
    with open(DATASET_YAML_FILEPATH, "w") as fh:
        yaml.dump(dataset_config, fh, allow_unicode=True)


if __name__ == "__main__":
    config, label_names, train_data, val_data = get_cvat_dataset()

    create_directory_structure()

    create_train_labels(_create_labels, train_data, label_names)
    create_test_labels(_create_labels, val_data, label_names)

    create_train_images(train_data)
    create_test_images(val_data)

    _create_dataset_yaml(label_names)

    finalize_config(config)
