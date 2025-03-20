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
from typing import Optional


class License:
    def __init__(
        self,
        name: str,
        key: Optional[str] = None,
        html_url: Optional[str] = None,
    ):
        self.name = name
        self.key = key
        self.html_url = html_url

    def __iter__(self):
        yield "name", self.name
        yield "key", self.key
        yield "html_url", self.html_url

    def __str__(self) -> str:
        return json.dumps(vars(self), indent=4, default=str)
