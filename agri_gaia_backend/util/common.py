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

import json
import shutil
import colorsys
import traceback
import numpy as np
import requests
import subprocess

from typing import Dict, List, Union, Tuple, Optional
from contextlib import suppress
from matplotlib.colors import rgb2hex
from collections.abc import MutableMapping
from pathlib import Path
from json import JSONDecodeError


def get_stacktrace(exc: Exception) -> str:
    return "".join(
        traceback.format_exception(type(exc), value=exc, tb=exc.__traceback__)
    )


def delete_keys_from_dict(dictionary: Dict, keys: List[str]) -> None:
    for key in keys:
        with suppress(KeyError):
            del dictionary[key]
    for value in dictionary.values():
        if isinstance(value, MutableMapping):
            delete_keys_from_dict(value, keys)


def distinct_colors(num_colors: int) -> List[str]:
    colors = []
    for i in np.arange(0.0, 360.0, 360.0 / num_colors):
        hue = i / 360.0
        lightness = (50 + np.random.rand() * 10) / 100.0
        saturation = (90 + np.random.rand() * 10) / 100.0
        rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
        colors.append(rgb)
    colors = np.asarray(colors)
    return [rgb2hex(colors[i, :]) for i in range(colors.shape[0])]


def is_json_response(response: requests.Response):
    return (
        "Content-Type" in response.headers
        and "application/json" in response.headers.get("Content-Type")
    )


def exists_in_dict(dictionary: Dict, keys: Union[str, List[str]]):
    if not dictionary:
        return False

    if type(keys) is not list:
        keys = [keys]

    keys = list(map(str, keys))
    entry = dictionary
    for key in keys:
        if key not in entry or not entry[key]:
            return False
        entry = entry[key]

    return bool(entry)


def mv(src: str, dst: str) -> None:
    print(f"[mv] Moving '{src}' -> '{dst}'")
    shutil.move(src, dst)


def rm(path: Union[str, Path]) -> None:
    print(f"[rm] Removing '{path}'")
    shutil.rmtree(path, ignore_errors=True)


def mkdir(path: str) -> None:
    print(f"[mkdir] Creating '{path}'")
    Path(path).mkdir(parents=True, exist_ok=True)


def touch(path: str) -> None:
    print(f"[touch] Creating '{path}'")
    Path(path).touch(exist_ok=True)


def gpu_available() -> bool:
    try:
        subprocess.check_output("nvidia-smi")
        return True
    except Exception:
        return False


def is_valid_json(filepath: str) -> Tuple[bool, Optional[str]]:
    try:
        with open(filepath, "r") as fh:
            json.load(fh)
        return True, None
    except JSONDecodeError as e:
        return False, str(e)
