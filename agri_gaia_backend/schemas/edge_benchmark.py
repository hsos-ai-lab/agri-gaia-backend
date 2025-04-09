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

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from agri_gaia_backend.schemas.dataset import Dataset
from agri_gaia_backend.schemas.model import Model
from edge_benchmarking_types.edge_device.models import BenchmarkJob as TBenchmarkJob
from edge_benchmarking_types.edge_farm.models import BenchmarkConfig as TBenchmarkConfig


class InferenceClient(str, Enum):
    TRITON_DENSE_NET_CLIENT = "TritonDenseNetClient"
    TRITON_YOLO_CLIENT = "TritonYoloClient"


class BenchmarkJob(BaseModel):
    id: int
    owner: str
    bucket_name: str
    minio_location: Optional[str]
    timestamp: datetime
    last_modified: datetime
    dataset: Dataset
    model: Model
    cpu_only: bool
    edge_device: str
    inference_client: InferenceClient

    class Config:
        from_attributes = True


class BenchmarkJobRun(BaseModel):
    model_id: int
    dataset_id: int
    benchmark_config: TBenchmarkConfig
    benchmark_job: TBenchmarkJob
    created_at: datetime
