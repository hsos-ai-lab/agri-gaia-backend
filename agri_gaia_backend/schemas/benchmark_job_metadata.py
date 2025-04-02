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

from pydantic import BaseModel
from edge_benchmarking_types.edge_farm.models import BenchmarkConfig
from edge_benchmarking_types.edge_device.models import BenchmarkJob


class BenchmarkJobMetadata(BaseModel):
    model_id: int
    dataset_id: int
    benchmark_config: BenchmarkConfig
    benchmark_job: BenchmarkJob
