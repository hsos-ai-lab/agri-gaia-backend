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

from typing import Optional, List
from pydantic import BaseModel


class DatasetBase(BaseModel):
    name: str
    public: Optional[bool] = None
    annotator: Optional[str] = None
    annotation_date: Optional[datetime.datetime] = None
    annotation_task_id: Optional[int] = None
    annotation_labels: Optional[List[str]] = None
    owner: str
    filecount: int
    total_filesize: int
    last_modified: datetime.datetime
    metadata_uri: Optional[str] = None
    bucket_name: str
    minio_location: str
    dataset_type: str


class Dataset(DatasetBase):
    id: int

    class Config:
        from_attributes = True
