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

from typing import List, Optional
from pathlib import Path
from itertools import chain
from dotenv import dotenv_values
from abc import ABC, abstractmethod

from agri_gaia_backend.services.licensing.dependency import Dependency


class DependencySource(ABC):
    def __init__(
        self,
        project_root: Optional[Path],
        filename: str,
        extensions: List[str],
        recursive: bool = False,
    ):
        self.project_root = project_root
        self.filename = filename
        self.extensions = extensions

        if project_root is not None:
            self.env = dotenv_values(self.project_root.joinpath(".env"))
            if recursive:
                self.filepaths = list(
                    chain.from_iterable(
                        self.project_root.rglob(f"{filename}{ext}")
                        for ext in extensions
                    )
                )
            else:
                self.filepaths = [
                    self.project_root.joinpath(f"{filename}{ext}") for ext in extensions
                ]

    def deduplicate_dependencies(
        self, dependencies: List[Dependency]
    ) -> List[Dependency]:
        unique_dependencies = {}
        for dependency in dependencies:
            if dependency.name not in unique_dependencies:
                unique_dependencies[dependency.name] = dependency
            else:
                unique_dependencies[dependency.name].version = unique_dependencies[
                    dependency.name
                ].version.union(dependency.version)

        return list(unique_dependencies.values())

    @abstractmethod
    def parse_dependencies(self, filepath: Path) -> List[Dependency]:
        pass

    @abstractmethod
    def add_license(self, dependencies: List[Dependency]) -> List[Dependency]:
        pass

    def analyze(
        self, dependencies: Optional[List[Dependency]] = None
    ) -> List[Dependency]:
        if dependencies is None:
            dependencies = []
            for filepath in self.filepaths:
                dependencies += self.parse_dependencies(filepath)
        else:
            dependencies = self.deduplicate_dependencies(dependencies)
        return self.add_license(dependencies)
