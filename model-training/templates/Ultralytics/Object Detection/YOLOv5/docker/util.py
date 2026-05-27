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
from typing import Dict, List

CUSTOM_CONFIG_FILENAME = "custom.json"


def read_custom_config() -> Dict:
    with open(CUSTOM_CONFIG_FILENAME, "r", encoding="utf-8") as fh:
        return json.load(fh)

def convert_args(argv: List[str]) -> List[str]:
    args = []
    argc = len(argv)
    for i, entry in enumerate(argv):
        if not entry.startswith("--"):
            continue

        if "=" in entry:
            arg = entry[2:]
        else:
            arg = f"{entry[2:]}="

            if i + 1 < argc:
                if argv[i + 1].startswith("--"):
                    value = True
                else:
                    value = argv[i + 1]
            else:
                value = True
            arg += str(value)

        args.append(arg)
    return args
