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

import json
from typing import Dict, List
import dxf
from agri_gaia_backend.util.auth import service_account
from agri_gaia_backend.util import env
import io

import logging

logger = logging.getLogger(__name__)

MEDIATYPE_IMAGE_MANIFEST_DOCKER = "application/vnd.docker.distribution.manifest.v2+json"
MEDIATYPE_IMAGE_INDEX_DOCKER = (
    "application/vnd.docker.distribution.manifest.list.v2+json"
)
MEDIATYPE_IMAGE_MANIFEST_OCI = "application/vnd.oci.image.manifest.v1+json"
MEDIATYPE_IMAGE_INDEX_OCI = "application/vnd.oci.image.index.v1+json"


def is_image_manifest(mediaType: str) -> bool:
    return mediaType in [MEDIATYPE_IMAGE_MANIFEST_DOCKER, MEDIATYPE_IMAGE_MANIFEST_OCI]


def is_image_index(mediaType: str) -> bool:
    return mediaType in [MEDIATYPE_IMAGE_INDEX_DOCKER, MEDIATYPE_IMAGE_INDEX_OCI]


def get_platform(manifest_descriptor: Dict) -> str:
    os = manifest_descriptor["os"]
    arch = manifest_descriptor["architecture"]

    platform = os + "/" + arch
    if "variant" in manifest_descriptor and arch != "arm64":
        platform += "/" + manifest_descriptor["variant"]
    return platform


def get_compressed_image_size(image_manifest: Dict) -> int:
    return sum(layer["size"] for layer in image_manifest["layers"])


def docker_registry_auth(dxf_base, response):
    username = service_account.REALM_SERVICE_ACCOUNT_USERNAME
    password = service_account.REALM_SERVICE_ACCOUNT_PASSWORD
    dxf_base.authenticate(username, password, response=response)


"""
    === TODO ===
    Use proper certificates from "config/traefik/certs/{self-signed,issued,lets-encrypt}"
    If we deploy the platform with "issued" or "lets-encrypt" certificates, this backend
    component can verify TLS connections via:

    VERIFY_SSL = bool_from_env("BACKEND_VERIFY_SSL")
"""


def get_dxf_repo(repository_name: str) -> dxf.DXF:
    return dxf.DXF(
        host=env.REGISTRY_URL,
        repo=repository_name,
        auth=docker_registry_auth,
        tlsverify=False,
    )


# def get_manifest(
#     repository_name: str, tag_or_digest: str
# ) -> Union[Dict, Dict[str, Dict]]:
#     repository = get_dxf_repo(repository_name)
#     manifest_or_dict = repository.get_manifest(tag_or_digest)
#     if isinstance(manifest_or_dict, dict):
#         return {
#             platform: json.loads(manifest)
#             for platform, manifest in manifest_or_dict.items()
#         }
#     return json.loads(manifest_or_dict)


def get_manifest(repository_name: str, tag_or_digest: str) -> Dict:
    repository = get_dxf_repo(repository_name)
    manifest, _ = repository.get_manifest_and_response(tag_or_digest)
    return json.loads(manifest)


def get_manifests_from_index(repository_name: str, image_index: Dict) -> List[Dict]:
    repository = get_dxf_repo(repository_name)
    tags_or_digests = []
    for manifest_descriptor in image_index["manifests"]:
        annotations = image_index.get("annotations", None)
        if (
            annotations
            and annotations.get("vnd.docker.reference.type", None)
            == "attestation-manifest"
        ):
            continue
        platform = manifest_descriptor["platform"]
        if platform["architecture"] == "unknown" or platform["os"] == "unknown":
            continue
        tags_or_digests.append(manifest_descriptor["digest"])
    return [json.loads(repository.get_manifest(alias)) for alias in tags_or_digests]


def get_image_metadata(repository_name, manifest: Dict) -> Dict:
    config_digest = manifest["config"]["digest"]
    config: bytes = get_blob(repository_name, config_digest)
    config: Dict = json.loads(config.decode("utf-8"))

    platform = get_platform(config)
    exposed_ports = [*config["config"].get("ExposedPorts", [])]
    compressed_image_size = sum(layer["size"] for layer in manifest["layers"])

    return {
        "platform": platform,
        "exposed_ports": exposed_ports,
        "compressed_image_size": compressed_image_size,
    }


def get_blob(repository_name: str, digest: str) -> bytes:
    repository = get_dxf_repo(repository_name)
    buffer = io.BytesIO()
    content_iter = iter(repository.pull_blob(digest))
    for chunk in content_iter:
        buffer.write(chunk)

    buffer.seek(0)
    return buffer.read()


def delete_image_alias(repository_name: str, image_tag: str) -> None:
    repository = get_dxf_repo(repository_name)
    repository.del_alias(alias=image_tag)
