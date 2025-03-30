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

import re
import json
import yaml
import requests
import mistletoe
import validators

from io import StringIO
from pathlib import Path
from itertools import chain
from urllib.parse import urlparse
from mistletoe.ast_renderer import ASTRenderer
from typing import List, Optional, Dict

from agri_gaia_backend.services.licensing.dependency import Dependency
from agri_gaia_backend.services.licensing.util.regexp import URL_REGEXP
from agri_gaia_backend.services.licensing.dependency_source import DependencySource
from agri_gaia_backend.services.licensing.util.github import (
    get_github_repo_from_github_url,
    get_license_from_github,
    get_license_from_github_search,
)


class DockerImages(DependencySource):
    def __init__(
        self,
        project_root: Path,
        filename: str,
        extensions: List[str],
        recursive: bool = False,
    ):
        super().__init__(project_root, filename, extensions, recursive)

    def parse_dependencies(self, filepath: Path) -> List[Dependency]:
        def _replace_from_env(env_var_str: str) -> str:
            if "${" in env_var_str:
                env_var = re.search(r"\$[\{](\w*)[\}]", env_var_str).group(1)
                env_var_str = env_var_str.replace(
                    "${" + env_var + "}", self.env[env_var]
                )
            return env_var_str

        def _create_dependency_from_image(image: str) -> Dependency:
            def _test_docker_hub_url(url: str) -> bool:
                response = requests.get(url, allow_redirects=False)
                return response.status_code == 200

            def _create_image_url(image_name: str) -> str:
                docker_hub_url = "https://hub.docker.com"
                dependency_url = f"https://{image_name}"
                if not validators.url(dependency_url):
                    url = f"{docker_hub_url}/r/{image_name}"
                    if not _test_docker_hub_url(url):
                        url = f"{docker_hub_url}/_/{image_name}"
                else:
                    url = dependency_url
                return url

            image_name, tag = map(
                _replace_from_env,
                image.split(":") if ":" in image else (image, "latest"),
            )
            return Dependency(
                name=image_name, version={tag}, url=_create_image_url(image_name)
            )

        def _create_dependency_from_github_url(github_url: str) -> Dependency:
            if github_url.endswith(".git"):
                github_url = github_url.strip(".git")

            if github_url.startswith("git@"):
                github_url = f"https://{github_url.strip('git@').replace(':', '/')}"

            parsed_github_url = urlparse(github_url)

            release_donwload_subpath = "/releases/download/"
            if release_donwload_subpath in parsed_github_url.path:
                path_parts = parsed_github_url.path.split(release_donwload_subpath)
                name = path_parts[0].strip("/")
                version = path_parts[1].split("/")[0]
                url = f"{parsed_github_url.scheme}://{parsed_github_url.netloc}{path_parts[0]}"
            else:
                name = parsed_github_url.path.strip("/")
                version = "latest"
                url = github_url

            owner_repo = get_github_repo_from_github_url(url)
            if owner_repo is not None:
                _, repo = owner_repo
                name = repo

            return Dependency(
                name=name,
                version={version},
                url=url,
            )

        def _create_dependencies_from_dockerfile(
            dockerfile_path: str,
        ) -> List[Dependency]:
            with open(dockerfile_path) as fh:
                lines = fh.read().splitlines()
            dockerfile_dependencies = []
            for line in lines:
                if "github.com" in line:
                    line = _replace_from_env(line)
                    github_urls = re.findall(URL_REGEXP, line)
                    github_dependencies = [
                        _create_dependency_from_github_url(github_url)
                        for github_url in github_urls
                    ]
                    dockerfile_dependencies.extend(github_dependencies)
            return dockerfile_dependencies

        def _get_images_from_dockerfile(dockerfile_path: str) -> List[str]:
            with open(dockerfile_path, "r") as fh:
                from_statements = filter(
                    lambda line: line.strip().startswith("FROM"),
                    fh.read().splitlines(),
                )
                return [
                    from_statement.split(" ")[1] for from_statement in from_statements
                ]

        def _get_images_from_docker_compose_file(
            docker_compose_filepath: str,
        ) -> List[str]:
            images = []
            with open(docker_compose_filepath, "r") as fh:
                compose_services = yaml.safe_load(fh)["services"]
                for service in compose_services.values():
                    if "image" in service:
                        images.append(service["image"])
                    else:
                        dockerfile_path = (
                            self.project_root.joinpath(
                                service["build"]["context"],
                                service["build"]["dockerfile"],
                            )
                            if "dockerfile" in service["build"]
                            else self.project_root.joinpath(
                                service["build"]["context"], "Dockerfile"
                            )
                        )
                        images += _get_images_from_dockerfile(dockerfile_path)
            return images

        images = _get_images_from_docker_compose_file(filepath)
        image_depedencies = [_create_dependency_from_image(image) for image in images]

        dockerfile_filepaths = self.project_root.rglob("Dockerfile")
        dockerfile_dependencies = list(
            chain.from_iterable(
                [
                    _create_dependencies_from_dockerfile(dockerfile_filepath)
                    for dockerfile_filepath in dockerfile_filepaths
                ]
            )
        )

        return image_depedencies + dockerfile_dependencies

    def add_license(self, dependencies: List[Dependency]) -> List[Dependency]:
        def _get_markdown_urls(node: Dict, urls: List) -> None:
            if node["type"] == "Link":
                urls.append(node["target"])
            if node["type"] == "RawText":
                urls.extend(re.findall(URL_REGEXP, node["content"]))

            children = node["children"] if "children" in node else []
            for child in children:
                _get_markdown_urls(child, urls)

        def _get_github_url(urls: List[str]) -> Optional[str]:
            github_urls = list(filter(lambda url: "github.com" in url, urls))

            if not github_urls:
                return None

            github_license_urls = list(
                filter(
                    lambda github_url: "LICENSE" in github_url
                    or "license" in github_url,
                    github_urls,
                )
            )

            return github_urls[0] if not github_license_urls else github_license_urls[0]

        def _get_github_url_from_docker_hub(dependency: Dependency) -> Optional[str]:
            library = "library/" if "/_/" in dependency.url else ""
            docker_hub_url = (
                f"https://hub.docker.com/v2/repositories/{library}{dependency.name}"
            )
            response = requests.get(docker_hub_url)
            print(docker_hub_url, response.status_code)
            if response.status_code != 200:
                return None
            description_markdown = response.json()["full_description"]

            with StringIO(description_markdown) as sh:
                description_dict = json.loads(mistletoe.markdown(sh, ASTRenderer))

            md_urls = []
            _get_markdown_urls(description_dict, md_urls)

            return _get_github_url(md_urls)

        for dependency in dependencies:
            if "hub.docker.com" in dependency.url:
                github_url = _get_github_url_from_docker_hub(dependency)
                if github_url is not None:
                    owner_repo = get_github_repo_from_github_url(github_url)
                    if owner_repo is not None:
                        dependency.license = get_license_from_github(*owner_repo)
            elif "github.com" in dependency.url:
                owner_repo = get_github_repo_from_github_url(dependency.url)
                if owner_repo is not None:
                    dependency.license = get_license_from_github(*owner_repo)

            if dependency.license is None:
                dependency.license = get_license_from_github_search(dependency)

            if dependency.license is None:
                print(f"Unable to find license for image {dependency.name}.")
        return dependencies
