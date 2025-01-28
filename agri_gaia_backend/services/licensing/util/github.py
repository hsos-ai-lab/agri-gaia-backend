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

import os
import requests

from urllib.parse import urlparse
from typing import Tuple, Optional

from agri_gaia_backend.services.licensing.license import License
from agri_gaia_backend.services.licensing.dependency import Dependency


def github_http_get(url: str) -> requests.Response:
    github_token = os.getenv("GITHUB_TOKEN")
    response = requests.get(
        url,
        headers=(
            {
                "Authorization": f"Bearer {github_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if github_token is not None
            else None
        ),
    )
    print(url, response.status_code)
    return response


def get_github_repo_from_github_url(github_url: str) -> Tuple[str, str]:
    url_path = urlparse(github_url).path
    owner, repo = url_path.split("/")[1:3]
    return owner, repo


def get_license_from_github(owner: str, repo: str) -> Optional[License]:
    github_license_url = f"https://api.github.com/repos/{owner}/{repo}/license"
    response = github_http_get(github_license_url)
    if response.status_code == 200:
        license = response.json()["license"]
        return License(name=license["name"])


def get_license_from_github_search(
    dependency: Dependency,
) -> Optional[License]:
    query = None
    if "/" in dependency.name:
        parts = dependency.name.split("/")
        last = parts[-1]
        for part in parts:
            if part in last:
                query = part
                break
        if query is None:
            query = last
    else:
        query = dependency.name

    response = github_http_get(f"https://api.github.com/search/repositories?q={query}")
    if response.status_code == 200:
        search_results = response.json()["items"]
        if type(search_results) == list and search_results:
            first_result = search_results[0]
            if "license" in first_result:
                return License(name=first_result["license"]["name"])
