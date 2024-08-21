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


import re
import json
import requests

from typing import List
from pathlib import Path

from agri_gaia_backend.services.licensing.license import License
from agri_gaia_backend.services.licensing.dependency import Dependency
from agri_gaia_backend.services.licensing.dependency_source import DependencySource


class NodePackages(DependencySource):
    def __init__(
        self,
        project_root: Path,
        filename: str,
        extensions: List[str],
        recursive: bool = False,
    ):
        super().__init__(project_root, filename, extensions, recursive)

    def parse_dependencies(self, filepath: Path) -> List[Dependency]:
        with open(filepath, "r") as fh:
            node_packages = json.load(fh)
            return [
                Dependency(name=name, version={version})
                for name, version in {
                    **node_packages["dependencies"],
                    **node_packages["devDependencies"],
                }.items()
            ]

    def add_license(self, dependencies: List[Dependency]) -> List[Dependency]:
        def _create_registry_url(dependency: Dependency) -> str:
            version = re.sub(r"[^0-9.]", "", list(dependency.version)[0])
            if len(version) != 5:
                version = "latest"
            return f"https://registry.npmjs.com/{dependency.name}/{version}"

        for dependency in dependencies:
            try:
                # See: https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md
                registry_url = _create_registry_url(dependency)
                response = requests.get(registry_url)
                print(registry_url, response.status_code)
                response.raise_for_status()
                dependency_meta = response.json()
                dependency.license = License(name=dependency_meta["license"])
                dependency.url = f"https://www.npmjs.com/package/{dependency.name}/"
            except requests.HTTPError:
                continue
        return dependencies
