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

from docker.errors import APIError

from agri_gaia_backend.util import env
from agri_gaia_backend.services.docker.client import host_client as client
from agri_gaia_backend.services.docker.client import registry_client

import logging

logger = logging.getLogger("api-logger")

config_dir = ".platform"


def create_named_volume(name):
    client.volumes.create(name)


def delete_named_volume(name):
    client.volumes.get(name).remove()


def download_image_into_platform_registry(
    external_repository: str,
    external_tag: str,
    os_arch: str,
    platform_repository: str,
    platform_tag: str,
):
    image_id = f"{external_repository}:{external_tag}"
    platform_repository_url = f"{env.REGISTRY_URL}/{platform_repository}"
    try:
        # pull the image from the remote registry
        pull_output = registry_client.pull(
            external_repository, external_tag, platform=os_arch
        )
        logger.debug(f"pulled image: {pull_output}")

        # tag the image with the new name to point at the platform registry
        registry_client.tag(image_id, platform_repository_url, platform_tag)

        # push the tagged image to the platform registry
        registry_client.push(platform_repository_url, platform_tag)

        # remove the images from the local machine
        registry_client.remove_image(f"{platform_repository_url}:{platform_tag}")
        registry_client.remove_image(image_id)

        return platform_repository, platform_tag
    except APIError as e:
        logger.error("Error processing the image:")
        logger.error(e)

    return None, None
