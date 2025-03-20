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

import json
import copy
from typing import Optional, Set
from agri_gaia_backend.services.licensing.license import License


class Dependency:
    def __init__(
        self,
        name: str,
        version: Set[str],
        url: Optional[str] = None,
        license: Optional[str] = None,
    ):
        self.name = name
        self.version = version
        self.url = url
        self.license = License(name=license) if license is not None else None

    def __iter__(self):
        yield "name", self.name
        yield "version", list(self.version)
        yield "url", self.url
        yield "license", self.license

    def __str__(self) -> str:
        obj = copy.deepcopy(self)
        obj.version = list(obj.version)
        return json.dumps(vars(obj), indent=4, default=str)
