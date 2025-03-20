#!/usr/bin/env python

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

# -*- coding: utf-8 -*-
import datetime

from typing import Optional
from pydantic import BaseModel
from agri_gaia_backend.schemas.dataset import Dataset


class TrainContainer(BaseModel):
    id: Optional[int]
    container_id: Optional[str]
    status: Optional[str]
    last_modified: Optional[datetime.datetime]
    image_id: str
    repository: str
    tag: str
    owner: str

    provider: str
    architecture: str
    dataset_id: int
    dataset: Dataset
    model_filepath: str
    score_regexp: str
    score_name: str
    score: Optional[float]

    class Config:
        orm_mode = True
