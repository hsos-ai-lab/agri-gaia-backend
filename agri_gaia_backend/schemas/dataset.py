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

import datetime

from typing import Optional, List
from pydantic import BaseModel



class DatasetBase(BaseModel):
    name: str
    public: Optional[bool]
    annotator: Optional[str]
    annotation_date: Optional[datetime.datetime]
    annotation_task_id: Optional[int]
    annotation_labels: Optional[List[str]]
    owner: str
    filecount: int
    total_filesize: int
    last_modified: datetime.datetime
    metadata_uri: Optional[str]
    bucket_name: str
    minio_location: str
    dataset_type: str


class Dataset(DatasetBase):
    id: int

    class Config:
        orm_mode = True
