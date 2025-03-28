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


import requests
import requirements as PythonRequirementsParser

from pathlib import Path
from typing import List, Optional, Dict

from agri_gaia_backend.services.licensing.license import License
from agri_gaia_backend.services.licensing.dependency import Dependency
from agri_gaia_backend.services.licensing.dependency_source import DependencySource


class PythonLibraries(DependencySource):
    def __init__(
        self,
        project_root: Path,
        filename: str,
        extensions: List[str],
        recursive: bool = True,
    ):
        super().__init__(project_root, filename, extensions, recursive)

    def parse_dependencies(self, filepath: Path) -> List[Dependency]:
        with open(filepath, "r") as fh:
            return list(
                Dependency(
                    name=req.name.lower(),
                    version={",".join("".join(spec) for spec in req.specs)},
                )
                for req in PythonRequirementsParser.parse(fh)
            )

    def add_license(self, dependencies: List[Dependency]) -> List[Dependency]:
        def _get_license(dependency_meta: Dict) -> Optional[str]:
            license_classifier = list(
                filter(
                    lambda classifier: classifier.startswith("License"),
                    dependency_meta["info"]["classifiers"],
                )
            )
            license_name = None
            if license_classifier:
                license_name = license_classifier[0].split(" :: ")[-1]
            if not license_name:
                license_name = dependency_meta["info"]["license"]
            return License(name=license_name)

        for dependency in dependencies:
            try:
                pypi_url = f"https://pypi.org/pypi/{dependency.name}/json"
                response = requests.get(pypi_url)
                print(pypi_url, response.status_code)
                response.raise_for_status()
                dependency_meta = response.json()
                dependency.license = _get_license(dependency_meta)
                dependency.url = f"https://pypi.org/project/{dependency.name}/"
            except requests.HTTPError:
                continue
        return dependencies
