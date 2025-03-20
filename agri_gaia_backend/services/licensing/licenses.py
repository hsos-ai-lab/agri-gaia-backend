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

import os
import json
import argparse

from pathlib import Path
from typing import List, Dict, Optional

from agri_gaia_backend.services.licensing.license import License
from agri_gaia_backend.services.licensing.util.github import github_http_get
from agri_gaia_backend.services.licensing.dependency import Dependency
from agri_gaia_backend.services.licensing.node_packages import NodePackages
from agri_gaia_backend.services.licensing.docker_images import DockerImages
from agri_gaia_backend.services.licensing.python_libraries import PythonLibraries
from agri_gaia_backend.services.licensing.explicit_dependencies import (
    ExplicitDependencies,
)
from agri_gaia_backend.services.licensing.util.licenses import LICENSES
from agri_gaia_backend.services.licensing.explicit_dependencies import (
    EXPLICIT_DEPENDENCIES,
)

LICENSES_FILENAME = "licenses.json"


GITHUB_LICENSES = {}


def get_args():
    parser = argparse.ArgumentParser(
        description="Automatically collect licenses of Python, Node and Compose dependecies."
    )
    parser.add_argument(
        "--project-root",
        type=str,
        required=True,
        help="Project root path",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="./",
        help="Output path to write 'licenses.json' to.",
    )
    return parser.parse_args()


def write_licenses(licenses: Dict[str, List[Dependency]], output_path: str) -> None:
    with open(Path(output_path).joinpath(LICENSES_FILENAME), "w") as fh:
        json.dump(licenses, fh, indent=4, default=dict)


def read_licenses(licenses_path: str) -> Dict:
    with open(Path(licenses_path).joinpath(LICENSES_FILENAME)) as fh:
        return json.load(fh)


def finalize_licenses(dependencies: List[Dependency]) -> List[Dependency]:
    def _get_license_from_github(dependency: Dependency) -> Optional[Dict]:
        for license_names, license_key in LICENSES.items():
            if (
                dependency.license is not None
                and dependency.license.name in license_names
            ):
                if license_key not in GITHUB_LICENSES:
                    response = github_http_get(
                        f"https://api.github.com/licenses/{license_key}"
                    )
                    if response.status_code == 200:
                        GITHUB_LICENSES[license_key] = response.json()

                if license_key in GITHUB_LICENSES:
                    return GITHUB_LICENSES[license_key]
                break
        return None

    for dependency in dependencies:
        github_license = _get_license_from_github(dependency)
        if github_license is not None:
            dependency.license = License(
                name=github_license["name"],
                key=github_license["key"],
                html_url=github_license["html_url"],
            )

    return dependencies


def analyze(project_root: str, output_path: str) -> Dict:
    if not os.environ.get("GITHUB_TOKEN"):
        raise RuntimeError(
            "No GitHub personal access (GITHUB_TOKEN) found in environment. Licenses cannot be refreshed due to the GitHub API's rate limiting."
        )

    project_root = Path(project_root)
    output_path = Path(output_path)

    python_libraries = PythonLibraries(
        project_root=project_root,
        filename="requirements",
        extensions=[".txt"],
        recursive=True,
    )
    python_libraries: List[Dependency] = python_libraries.analyze()
    python_libraries = finalize_licenses(python_libraries)

    node_packages = NodePackages(
        project_root=project_root.joinpath("services/frontend"),
        filename="package",
        extensions=[".json"],
        recursive=False,
    )
    node_packages: List[Dependency] = node_packages.analyze()
    node_packages = finalize_licenses(node_packages)

    docker_images = DockerImages(
        project_root=project_root,
        filename="docker-compose",
        extensions=[".yml"],
        recursive=False,
    )
    docker_images: List[Dependency] = docker_images.analyze()
    docker_images = finalize_licenses(docker_images)

    licenses = [
        {
            "name": dependency_category,
            "dependencies": dependencies,
        }
        for dependency_category, dependencies in (
            ("Python Libraries", python_libraries),
            ("Node Packages", node_packages),
            ("Docker Images", docker_images),
        )
    ]

    for category in EXPLICIT_DEPENDENCIES:
        category_name = category["name"]
        explicit_dependencies = ExplicitDependencies()
        explicit_dependencies: List[Dependency] = explicit_dependencies.analyze(
            category["dependencies"]
        )
        explicit_dependencies = finalize_licenses(explicit_dependencies)
        licenses.append({"name": category_name, "dependencies": explicit_dependencies})

    write_licenses(licenses=licenses, output_path=output_path)

    return licenses


if __name__ == "__main__":
    ARGS = get_args()
    analyze(project_root=ARGS.project_root, output_path=ARGS.output_path)
