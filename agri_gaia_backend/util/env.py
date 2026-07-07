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

import os


def bool_from_env(var_name: str) -> bool:
    return os.getenv(var_name, "False").lower() in ("true", "1", "t")


def int_from_env(var_name: str, default: int) -> int:
    """Read a positive int from the environment, falling back to ``default`` on
    an unset/empty/invalid value (a misconfiguration must not break startup)."""
    raw = os.getenv(var_name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


DEBUG_MODE = bool_from_env("DEBUG")

# Edge-benchmark concurrency limits (see routers/edge_benchmark.py). Benchmarks
# run on their own bounded executor so they cannot starve other background work,
# and each user is limited to a few active benchmark tasks for fairness.
EDGE_BENCHMARK_MAX_WORKERS = int_from_env("EDGE_BENCHMARK_MAX_WORKERS", 4)
EDGE_BENCHMARK_MAX_ACTIVE_PER_USER = int_from_env(
    "EDGE_BENCHMARK_MAX_ACTIVE_PER_USER", 3
)

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
