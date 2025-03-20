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

import os


def bool_from_env(var_name: str) -> bool:
    return os.getenv(var_name, "False").lower() in ("true", "1", "t")


DEBUG_MODE = bool_from_env("DEBUG")

PROJECT_BASE_URL = os.environ.get("PROJECT_BASE_URL")
KEYCLOAK_REALM_NAME = os.environ.get("KEYCLOAK_REALM_NAME")

REALM_SERVICE_ACCOUNT_USERNAME = os.environ.get("REALM_SERVICE_ACCOUNT_USERNAME")
REALM_SERVICE_ACCOUNT_PASSWORD = os.environ.get("REALM_SERVICE_ACCOUNT_PASSWORD")

KEYCLOAK_ADMIN_USERNAME = os.environ.get("KEYCLOAK_ADMIN_USERNAME")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")

S3_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD")

NUCLIO_CVAT_PROJECT_NAME = os.environ.get("NUCLIO_CVAT_PROJECT_NAME")

FUSEKI_ADMIN_USER = os.environ.get("FUSEKI_ADMIN_USER")
FUSEKI_ADMIN_PASSWORD = os.environ.get("FUSEKI_ADMIN_PASSWORD")

REGISTRY_URL = os.environ.get("REGISTRY_URL")
