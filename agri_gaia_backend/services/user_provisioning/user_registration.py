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

import os
from agri_gaia_backend.services.minio_api.client import get_admin_client
from agri_gaia_backend.services.docker import docker_api
from agri_gaia_backend.services.graph.sparql_operations import util as sparql_util
from agri_gaia_backend.services.graph.sparql_operations import users as sparql_users

import logging

logger = logging.getLogger("api-logger")


def setup_user_infrastructure(username: str):
    _setup_minio_bucket(username)
    _create_user_volume(username)
    _create_fuseki_entry(username)


def _setup_minio_bucket(username):
    minio_client = get_admin_client()
    minio_client.make_bucket(username)


def _create_user_volume(username):
    docker_api.create_named_volume(
        f"{os.environ.get('PROJECT_NAME')}_user_data_{username}"
    )


def _create_fuseki_entry(username):
    graph = sparql_users.get_default_graph(username)
    sparql_util.store_graph(graph)


def teardown_user_infrastructure(username: str):
    _delete_minio_bucket(username)
    _delete_user_volume(username)
    _delete_fuseki_entry(username)


def _delete_minio_bucket(username: str):
    minio_client = get_admin_client()
    try:
        minio_client.remove_bucket(username)
    except Exception as e:
        logger.warn(f"Error removing bucket on user '{username}' deregistration: {e}")


def _delete_user_volume(username: str):
    try:
        docker_api.delete_named_volume(
            f"{os.environ.get('PROJECT_NAME')}_user_data_{username}"
        )
    except Exception as e:
        logger.warn(f"Error removing volume on user '{username}' deregistration: {e}")


def _delete_fuseki_entry(username: str):
    sparql_users.delete_user(username)
