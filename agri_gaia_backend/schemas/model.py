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
    format: Optional[ModelFormat] = None


class ModelPatch(ModelBase):
    input_name: Optional[str] = None
    input_datatype: Optional[TensorDatatype] = None
    input_shape: Optional[List[int]] = None
    input_semantics: Optional[InputTensorShapeSemantics] = None
    output_name: Optional[str] = None
    output_datatype: Optional[TensorDatatype] = None
    output_shape: Optional[List[int]] = None
    output_labels: Optional[List[str]] = None


class Model(ModelBase):
    id: int
    owner: str
    public: Optional[bool] = None
    last_modified: datetime.datetime
    bucket_name: str
    metadata_uri: Optional[str] = None
    file_size: Optional[int] = None
    file_name: Optional[str] = None
    input_name: Optional[str] = None
    input_datatype: Optional[TensorDatatype] = None
    input_shape: Optional[List[int]] = None
    input_semantics: Optional[InputTensorShapeSemantics] = None
    output_name: Optional[str] = None
    output_datatype: Optional[TensorDatatype] = None
    output_shape: Optional[List[int]] = None
    output_labels: Optional[List[str]] = None

    class Config:
        from_attributes = True
