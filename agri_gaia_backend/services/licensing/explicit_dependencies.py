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

from pathlib import Path
from typing import List

from agri_gaia_backend.services.licensing.dependency_source import DependencySource
from agri_gaia_backend.services.licensing.dependency import Dependency
from agri_gaia_backend.services.licensing.util.github import (
    get_github_repo_from_github_url,
    get_license_from_github,
    get_license_from_github_search,
)

EXPLICIT_DEPENDENCIES = [
    {
        "name": "Java Packages",
        "dependencies": [
            Dependency(
                name="Connector",
                version={"v0.0.1-milestone-6"},
                url="https://github.com/eclipse-edc/Connector",
            ),
            Dependency(
                name="apache-jena-fuseki",
                version={"4.6.0"},
                url="https://github.com/apache/jena",
            ),
            Dependency(
                name="WebVOWL",
                version={"1.1.6"},
                url="https://github.com/VisualDataWeb/WebVOWL",
            ),
        ],
    }
]


class ExplicitDependencies(DependencySource):
    def __init__(
        self,
        project_root=None,
        filename=None,
        extensions=None,
        recursive: bool = False,
    ):
        super().__init__(project_root, filename, extensions, recursive)

    def parse_dependencies(self, filepath: Path) -> List[Dependency]:
        pass

    def add_license(self, dependencies: List[Dependency]) -> List[Dependency]:
        for dependency in dependencies:
            if "github.com" in dependency.url:
                owner_repo = get_github_repo_from_github_url(dependency.url)
                if owner_repo is not None:
                    dependency.license = get_license_from_github(*owner_repo)
            if dependency.license is None:
                dependency.license = get_license_from_github_search(dependency)
        return dependencies
