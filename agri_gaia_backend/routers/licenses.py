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
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-

import os
import logging

from typing import Dict, List
from pathlib import Path
from fastapi import APIRouter, HTTPException
from agri_gaia_backend.services.licensing.licenses import analyze, read_licenses

ROOT_PATH = "/licenses"
PROJECT_ROOT = "/platform"
OUTPUT_PATH = Path(__file__).parent.parent.absolute().joinpath("services/licensing")

router = APIRouter(prefix=ROOT_PATH)
logger = logging.getLogger("api-logger")


@router.get("/")
def get_licenses(github_token: str = None, return_cached: bool = True) -> List:
    try:
        logger.debug(
            f"[get_licenses] github_token: '{github_token}', return_cached: '{return_cached}'"
        )
        if return_cached:
            return read_licenses(OUTPUT_PATH)
        if github_token:
            os.environ["GITHUB_TOKEN"] = github_token
        return analyze(project_root=PROJECT_ROOT, output_path=OUTPUT_PATH)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))
