#!/usr/bin/env python

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

# -*- coding: utf-8 -*-
import datetime

from typing import Optional
from pydantic import BaseModel
from agri_gaia_backend.schemas.dataset import Dataset


class TrainContainer(BaseModel):
    id: Optional[int] = None
    container_id: Optional[str] = None
    status: Optional[str] = None
    last_modified: Optional[datetime.datetime] = None
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
    score: Optional[float] = None

    class Config:
        from_attributes = True
        protected_namespaces = ()
