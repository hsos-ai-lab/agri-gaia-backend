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

import datetime

from typing import Optional
from pydantic import BaseModel


class BenchmarkBase(BaseModel):
    name: str
    owner: str
    last_modified: datetime.datetime
    metadata_uri: Optional[str] = None
    bucket_name: str
    minio_location: str


class Benchmark(BenchmarkBase):
    id: int
    timestamp: datetime.datetime
    dataset_id: int
    job_id: str
    device_ip: str
    device_name: str

    class Config:
        from_attributes = True
