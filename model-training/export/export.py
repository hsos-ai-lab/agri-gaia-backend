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
import copy
import pkgutil
import traceback

from enum import Enum
from pathlib import Path
from operator import itemgetter
from onnxmltools.utils import save_model
from onnxmltools import convert_tensorflow, convert_keras
from typing import Dict, Any, Optional, Callable

EXPORT_CONFIG_FILENAME = "export_config.json"


class ModelFormat(str, Enum):
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    KERAS = "keras"


SUPPORTED_MODEL_FORMATS = set(format.value for format in ModelFormat)


def _onnx_model_filepath(model_filepath: str) -> Path:
    model_filepath = Path(model_filepath)
    return Path(model_filepath.parent, model_filepath.stem + ".onnx")


def _read_export_config() -> Dict:
    with open(EXPORT_CONFIG_FILENAME, "r") as fh:
        return json.load(fh)


def _check_installed(package_name: str) -> None:
    if not pkgutil.find_loader(package_name):
        raise RuntimeError(
            f"{package_name} is not installed, please install it before calling this function."
        )


def _create_export_kwargs(export_config: Dict, format: ModelFormat) -> Dict:
    export_kwargs = copy.deepcopy(export_config)

    input_shapes, input_types = itemgetter("input_shapes", "input_types")(export_config)
    input_names = export_config["input_names"] if "input_names" in export_config else []

    assert len(input_types) == len(
        input_shapes
    ), f"Input shapes ({len(input_shapes)}) and input types ({len(input_types)}) differ in size."

    assert len(input_names) <= len(
        input_shapes
    ), f"More input names ({len(input_names)}) than actual input shapes ({len(input_shapes)})."

    input_name_delta = len(input_shapes) - len(input_names)
    for input_number in range(
        len(input_names) + 1, len(input_names) + input_name_delta + 1
    ):
        input_names.append(f"Input {input_number}")

    if format == ModelFormat.PYTORCH:
        # See: https://github.com/pytorch/pytorch/blob/31d635803b8d72433ea275d3c36bf829b158d5ec/torch/onnx/utils.py#L190
        _check_installed("torch")
        import torch

        export_kwargs["args"] = [
            torch.ones(input_shape, dtype=eval(f"torch.{input_type}"))
            for input_shape, input_type in zip(input_shapes, input_types)
        ]
        export_kwargs["input_names"] = input_names

        for key, enum_class in (
            ("training", "TrainingMode"),
            ("operator_export_type", "OperatorExportTypes"),
        ):
            export_kwargs[key] = eval(f"torch.onnx.{enum_class}.{export_config[key]}")
    elif format == ModelFormat.TENSORFLOW:
        # Nothing to do.
        # See: https://github.com/onnx/onnxmltools/blob/79c34e377fe3a24d22eabac010e464de061d7adf/onnxmltools/convert/main.py#L424
        pass
    elif format == ModelFormat.KERAS:
        # See: https://github.com/onnx/onnxmltools/blob/79c34e377fe3a24d22eabac010e464de061d7adf/onnxmltools/convert/main.py#L42
        _check_installed("tensorflow")
        import tensorflow as tf

        export_kwargs["initial_types"] = [
            (
                input_name,
                tf.ones(
                    input_shape, dtype=eval(f"tf.dtype.{input_type}"), name=input_name
                ),
            )
            for input_name, input_type, input_shape in zip(
                input_names, input_types, input_shapes
            )
        ]

    for key in ("input_shapes", "input_types", "model_type"):
        del export_kwargs[key]

    return export_kwargs


def _export_onnx_model(model, format: ModelFormat, model_filepath: str) -> Path:
    def export_pytorch(model, model_filepath: str, export_kwargs: Dict) -> Path:
        import torch

        onnx_model_filepath = _onnx_model_filepath(model_filepath)
        torch.onnx.export(
            model=torch.jit.script(model), f=onnx_model_filepath, **export_kwargs
        )

        return onnx_model_filepath

    if format not in SUPPORTED_MODEL_FORMATS:
        raise RuntimeError(
            f"Unsupported model format '{format}' for ONNX conversion. Supported formats: {SUPPORTED_MODEL_FORMATS}"
        )

    export_config = _read_export_config()
    if not export_config:
        raise Exception(
            f"ONNX export configuration '{EXPORT_CONFIG_FILENAME}' is empty."
        )

    export_kwargs = _create_export_kwargs(export_config=export_config, format=format)

    if format == ModelFormat.PYTORCH:
        return export_pytorch(model, model_filepath, export_kwargs)
    elif format == ModelFormat.TENSORFLOW:
        onnx_model = convert_tensorflow(model, **export_kwargs)
    elif format == ModelFormat.KERAS:
        onnx_model = convert_keras(model, **export_kwargs)

    onnx_model_filepath = _onnx_model_filepath(model_filepath)
    save_model(onnx_model, onnx_model_filepath)

    return onnx_model_filepath


def export_model(
    model: Any,
    model_filepath: str,
    model_format: ModelFormat,
    default_model_export_func: Callable,
    default_model_export_kwargs: Optional[Dict] = None,
) -> None:
    try:
        _export_onnx_model(model, model_format, model_filepath)
    except:
        print("ONNX model export failed.")
        print(traceback.format_exc())

        if default_model_export_kwargs is None:
            default_model_export_kwargs = {}

        print("Falling back to 'default_model_export_func' for model export.")
        default_model_export_func(model, model_filepath, **default_model_export_kwargs)
