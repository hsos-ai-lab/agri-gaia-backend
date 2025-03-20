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

with open("train_config.json", "r") as fh:
    train_config = json.load(fh)

reserved = {"train-split", "test-split"}

args = []
for option, value in train_config.items():
    if value is None or value == "" or option in reserved:
        continue
    if type(value) is bool:
        if value:
            args.append(f"--{option}")
    elif type(value) is list:
        if value:
            args.append(f"--{option} {' '.join(map(str, value))}")
    else:
        args.append(f"--{option} {value}")

print(" ".join(args))
