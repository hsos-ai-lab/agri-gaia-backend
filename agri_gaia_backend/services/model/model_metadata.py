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

from typing import IO, Any, Dict, List, Tuple
import onnx
from agri_gaia_backend.db.models import (
    Model,
    ModelFormat,
    TensorDatatype,
    InputTensorShapeSemantics,
)

import logging

logger = logging.getLogger("api-logger")

ONNX_DATATYPE_MAPPING = {
    1: TensorDatatype.float32,
    2: TensorDatatype.uint8,
    3: TensorDatatype.int8,
    4: TensorDatatype.uint16,
    5: TensorDatatype.int16,
    6: TensorDatatype.int32,
    7: TensorDatatype.int64,
    8: TensorDatatype.string,
    9: TensorDatatype.bool,
    10: TensorDatatype.float16,
    11: TensorDatatype.float64,
    12: TensorDatatype.uint32,
    13: TensorDatatype.uint64,
}


def get_onnx_input_output_metadata(modelfile: IO[bytes]) -> Tuple[Dict, Dict]:
    inputs, outputs = {}, {}

    model = onnx.load(modelfile)
    modelinput = model.graph.input[0]
    dims = modelinput.type.tensor_type.shape.dim
    shape, semantics = _onnx_get_shape_semantics(dims)

    inputs = {
        "input_name": modelinput.name,
        "input_datatype": ONNX_DATATYPE_MAPPING[modelinput.type.tensor_type.elem_type],
        "input_shape": shape,
        "input_semantics": semantics,
    }

    modeloutput = model.graph.output[0]
    dims = modeloutput.type.tensor_type.shape.dim
    output_shape = [dim.dim_value for dim in dims]

    outputs = {
        "output_name": modeloutput.name,
        "output_datatype": ONNX_DATATYPE_MAPPING[
            modeloutput.type.tensor_type.elem_type
        ],
        "output_shape": output_shape,
    }

    return inputs, outputs


def set_onnx_input_output_metadata(model: Model, modelfile: IO[bytes]) -> None:
    inputs, outputs = get_onnx_input_output_metadata(modelfile)
    model.input_name = inputs["input_name"]
    model.input_datatype = inputs["input_datatype"]
    model.input_shape = inputs["input_shape"]
    model.input_semantics = inputs["input_semantics"]

    model.output_shape = outputs["output_shape"]
    model.output_datatype = outputs["output_datatype"]
    model.output_name = outputs["output_name"]


def _onnx_get_shape_semantics(dims: Any) -> Tuple[List[int], InputTensorShapeSemantics]:
    shape = [dim.dim_value for dim in dims]
    semantics = []
    for dim in dims:
        if dim.denotation == "DATA_BATCH":
            semantics.append("N")
        if dim.denotation == "DATA_CHANNEL":
            semantics.append("C")
        if dim.denotation == "DATA_FEATURE":
            if semantics[-1] == "H":
                semantics.append("W")
            else:
                semantics.append("H")

    # if not all denotations were set use the convention
    if len(shape) != len(semantics):
        semantics = ["H", "W"]
        single_input_dims = shape if len(shape) == 3 else shape[1:]
        channel_index = single_input_dims.index(min(single_input_dims))
        semantics.insert(channel_index, "C")
        if len(shape) == 4:
            semantics.insert(0, "N")

    semantics = "".join(semantics)
    return shape, InputTensorShapeSemantics(semantics)
