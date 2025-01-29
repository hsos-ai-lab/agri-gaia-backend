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

import docker
import os
import json

from tenacity import after_log, retry, stop_after_attempt, wait_fixed
from python_on_whales.docker_client import DockerClient
from agri_gaia_backend.util.auth import service_account

import logging

logger = logging.getLogger("api-logger")

REGISTRY_URL = os.environ.get("REGISTRY_URL")

DOCKER_SOCKET_URL = "build-container:2376"
DOCKER_CLIENT_CERT = "/certs/docker-build/client/cert.pem"
DOCKER_CLIENT_KEY = "/certs/docker-build/client/key.pem"
DOCKER_CLIENT_CA = "/certs/docker-build/client/ca.pem"


def _create_whales_client() -> DockerClient:
    try:

        @retry(
            wait=wait_fixed(5),
            stop=stop_after_attempt(60),
            after=after_log(logger, logging.INFO),
            reraise=True,
        )
        def _try():
            client = DockerClient(
                host=DOCKER_SOCKET_URL,
                tlscacert=DOCKER_CLIENT_CA,
                tlscert=DOCKER_CLIENT_CERT,
                tlskey=DOCKER_CLIENT_KEY,
                tls=True,
            )

            client.login(
                server=REGISTRY_URL,
                username=service_account.REALM_SERVICE_ACCOUNT_USERNAME,
                password=service_account.REALM_SERVICE_ACCOUNT_PASSWORD,
            )
            return client

        client = _try()
    except Exception as ex:
        logger.error(
            f"""Error creating docker whales client or logging into docker registry. Infos:
            docker socket url: {DOCKER_SOCKET_URL}
            registry url: {REGISTRY_URL}
            username: {service_account.REALM_SERVICE_ACCOUNT_USERNAME}
            """
        )
        raise ex
    return client


def _create_api_client():
    response = None
    try:

        @retry(
            wait=wait_fixed(5),
            stop=stop_after_attempt(60),
            after=after_log(logger, logging.INFO),
            reraise=True,
        )
        def _try():
            docker_tls_config = docker.tls.TLSConfig(
                client_cert=(DOCKER_CLIENT_CERT, DOCKER_CLIENT_KEY),
                verify=DOCKER_CLIENT_CA,
            )
            client = docker.APIClient(base_url=DOCKER_SOCKET_URL, tls=docker_tls_config)
            response = client.login(
                registry=REGISTRY_URL,
                username=service_account.REALM_SERVICE_ACCOUNT_USERNAME,
                password=service_account.REALM_SERVICE_ACCOUNT_PASSWORD,
            )
            return client, response

        client, response = _try()

    except Exception as ex:
        logger.error(
            f"""Error creating docker client or logging into docker registry. Infos:
        docker socket url: {DOCKER_SOCKET_URL}
        registry url: {REGISTRY_URL}
        username: {service_account.REALM_SERVICE_ACCOUNT_USERNAME}
        login response: {json.dumps(response)}
        """
        )
        raise ex
    return client


build_container_client = _create_whales_client()

registry_client = _create_api_client()

host_client = docker.from_env()
