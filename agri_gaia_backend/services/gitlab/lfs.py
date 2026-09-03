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

import base64
import hashlib
from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import quote

import requests


def _checked(response: requests.Response) -> requests.Response:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise RuntimeError(f"{error}: {response.text}") from error
    return response


def push_file_as_lfs_object(
    gitlab_api_url: str,
    project_id: str,
    branch: Optional[str],
    gitlab_token: str,
    filename: str,
    data: bytes,
) -> None:
    """Uploads ``data`` as a Git LFS-tracked file at the repository root of ``branch``.

    Mirrors the classic Git LFS batch-API upload flow: the object is uploaded
    to GitLab's LFS storage, a pointer file is committed, ``.gitattributes``
    is updated to track the target path via LFS, and the pointer is finally
    moved to its real path.

    If ``branch`` is not given (e.g. it wasn't recorded for a dataset imported
    before this was tracked), the project's default branch is used instead.
    """
    gitlab_host = gitlab_api_url.rsplit("/api/v4", 1)[0]
    api_headers = {"PRIVATE-TOKEN": gitlab_token}

    project = _checked(
        requests.get(f"{gitlab_api_url}/projects/{project_id}", headers=api_headers)
    ).json()
    project_path = project["path_with_namespace"]
    branch = branch or project["default_branch"]

    remote_path = filename.lstrip("/")

    oid = hashlib.sha256(data).hexdigest()
    size = len(data)

    batch = _checked(
        requests.post(
            f"{gitlab_host}/{project_path}.git/info/lfs/objects/batch",
            auth=("oauth2", gitlab_token),
            headers={
                "Accept": "application/vnd.git-lfs+json",
                "Content-Type": "application/vnd.git-lfs+json",
            },
            json={
                "operation": "upload",
                "transfers": ["basic"],
                "objects": [{"oid": oid, "size": size}],
                "ref": {"name": f"refs/heads/{branch}"},
            },
        )
    ).json()

    lfs_object = batch["objects"][0]
    if "error" in lfs_object:
        raise RuntimeError(f"LFS error: {lfs_object['error']}")

    upload = lfs_object.get("actions", {}).get("upload")
    if upload:
        upload_headers = {
            key: value
            for key, value in upload.get("header", {}).items()
            if key.lower() != "transfer-encoding"
        }
        upload_auth = (
            None
            if any(key.lower() == "authorization" for key in upload_headers)
            else ("oauth2", gitlab_token)
        )
        _checked(
            requests.put(
                upload["href"], data=data, headers=upload_headers, auth=upload_auth
            )
        )

    pointer = (
        "version https://git-lfs.github.com/spec/v1\n"
        f"oid sha256:{oid}\n"
        f"size {size}\n"
    )

    def commit(message: str, actions: list) -> None:
        _checked(
            requests.post(
                f"{gitlab_api_url}/projects/{project_id}/repository/commits",
                headers=api_headers,
                json={
                    "branch": branch,
                    "commit_message": message,
                    "actions": actions,
                },
            )
        )

    # Store the pointer temporarily before marking its final path as LFS-managed.
    parent = PurePosixPath(remote_path).parent
    temporary_path = oid if str(parent) == "." else str(parent / oid)

    commit(
        f"Add LFS pointer for {remote_path}",
        [{"action": "create", "file_path": temporary_path, "content": pointer}],
    )

    # Add the target path to .gitattributes.
    attributes_url = (
        f"{gitlab_api_url}/projects/{project_id}/repository/files/"
        f"{quote('.gitattributes', safe='')}"
    )
    response = requests.get(attributes_url, headers=api_headers, params={"ref": branch})

    attribute = f"{remote_path} filter=lfs diff=lfs merge=lfs -text"

    if response.status_code == 404:
        existing_attributes = ""
        attribute_action = "create"
    else:
        _checked(response)
        existing_attributes = base64.b64decode(response.json()["content"]).decode(
            "utf-8"
        )
        attribute_action = "update"

    if attribute not in existing_attributes.splitlines():
        new_attributes = existing_attributes.rstrip()
        if new_attributes:
            new_attributes += "\n"
        new_attributes += attribute + "\n"

        commit(
            "Update .gitattributes",
            [
                {
                    "action": attribute_action,
                    "file_path": ".gitattributes",
                    "content": new_attributes,
                }
            ],
        )

    # Move the pointer to its final path.
    commit(
        f"Add LFS file {remote_path}",
        [{"action": "move", "previous_path": temporary_path, "file_path": remote_path}],
    )
