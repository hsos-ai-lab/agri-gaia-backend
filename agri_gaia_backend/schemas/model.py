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

from typing import List, Optional
import datetime
from pydantic import BaseModel
from agri_gaia_backend.db.models import (
    InputTensorShapeSemantics,
    ModelFormat,
    TensorDatatype,
)


class ModelBase(BaseModel):
    name: str
    format: Optional[ModelFormat]


class ModelPatch(ModelBase):
    input_name: Optional[str]
    input_datatype: Optional[TensorDatatype]
    input_shape: Optional[List[int]]
    input_semantics: Optional[InputTensorShapeSemantics]
    output_name: Optional[str]
    output_datatype: Optional[TensorDatatype]
    output_shape: Optional[List[int]]
    output_labels: Optional[List[str]]


class Model(ModelBase):
    id: int
    owner: str
    public: Optional[bool]
    last_modified: datetime.datetime
    bucket_name: str
    metadata_uri: Optional[str]
    file_size: Optional[int]
    file_name: Optional[str]
    input_name: Optional[str]
    input_datatype: Optional[TensorDatatype]
    input_shape: Optional[List[int]]
    input_semantics: Optional[InputTensorShapeSemantics]
    output_name: Optional[str]
    output_datatype: Optional[TensorDatatype]
    output_shape: Optional[List[int]]
    output_labels: Optional[List[str]]

    class Config:
        orm_mode = True
