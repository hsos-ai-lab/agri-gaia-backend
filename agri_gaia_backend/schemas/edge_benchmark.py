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
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from agri_gaia_backend.schemas.dataset import Dataset
from agri_gaia_backend.schemas.model import Model
from edge_benchmarking_types.edge_device.models import BenchmarkJob as TBenchmarkJob
from edge_benchmarking_types.edge_farm.enums import (
    OptimizationFactor,
    LatencyPercentile,
)
from edge_benchmarking_types.edge_farm.models import (
    BenchmarkConfig as TBenchmarkConfig,
    DeviceRecommendation as TDeviceRecommendation,
)


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


class AutoSearchRequest(BaseModel):
    """Request payload for an auto-search ("recommend best device") run.

    ``benchmark_config`` carries the inference-client template and cpu_only flag;
    its ``edge_device`` host is overridden per candidate during the search.
    """

    model_id: int
    dataset_id: int
    chunk_size: int
    candidate_hostnames: List[str]
    factor: OptimizationFactor
    latency_metric: LatencyPercentile = LatencyPercentile.P95
    latency_threshold_ms: float
    min_accuracy: Optional[float] = None
    accuracy_metric: str = "accuracy"
    benchmark_config: TBenchmarkConfig
    created_at: datetime


class AutoSearchRun(BaseModel):
    """Persisted artifact of an auto-search run (stored as JSON in MinIO)."""

    model_id: int
    dataset_id: int
    request: AutoSearchRequest
    recommendation: TDeviceRecommendation
    created_at: datetime
