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

import sys
import torch
import subprocess

from pathlib import Path
from util import read_custom_config
from export import _read_export_config, EXPORT_CONFIG_FILENAME

if __name__ == "__main__":
    train_args = sys.argv[1:]
    train_cmd = ["python", "yolo_train.py"] + train_args
    try:
        subprocess.run(train_cmd, stdout=sys.stdout, stderr=sys.stderr, check=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        raise e

    if Path(EXPORT_CONFIG_FILENAME).exists():
        export_config = _read_export_config()
        if export_config:
            custom_config = read_custom_config()
            model_filepath = custom_config["model_filepath"]

            batch_size, _, height, width = export_config["input_shapes"][0]
            device = torch.cuda.current_device() if torch.cuda.is_available() else "cpu"
            opset = export_config["opset_version"]
            verbose = export_config["verbose"]

            export_cmd = [
                "python",
                "yolo_export.py",
                "--weights",
                model_filepath,
                "--include",
                "onnx",
                "--opset",
                opset,
                "--batch-size",
                batch_size,
                "--imgsz",
                height,
                width,
                "--device",
                device,
            ]

            export_cmd = list(map(str, export_cmd))
            print(f"Exporting model '{model_filepath}' to ONNX:", " ".join(export_cmd))
            try:
                subprocess.run(
                    export_cmd, stdout=sys.stdout, stderr=sys.stderr, check=True
                )
            except subprocess.CalledProcessError as e:
                print(e.stderr)
                raise e
