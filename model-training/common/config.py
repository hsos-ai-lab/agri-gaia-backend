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

import json
from typing import Dict

TRAIN_CONFIG_FILEPATH = "./train_config.json"
PRESETS_FILEPATH = "./presets.json"


def load_config() -> Dict:
    with open(TRAIN_CONFIG_FILEPATH, "r") as fh:
        return json.load(fh)


def finalize_config(config: Dict, custom: Dict = {}):
    with open(PRESETS_FILEPATH, "r") as fh:
        presets = json.load(fh)
    config = {**config, **presets, **custom}
    with open(TRAIN_CONFIG_FILEPATH, "w") as fh:
        json.dump(config, fh, indent=4)
