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
from typing import List, Optional, Tuple
from urllib.parse import quote

import requests


def _checked(response: requests.Response) -> requests.Response:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise RuntimeError(f"{error}: {response.text}") from error
    return response


def push_files_as_lfs_objects(
    gitlab_api_url: str,
    project_id: str,
    branch: Optional[str],
    gitlab_token: str,
    files: List[Tuple[str, bytes]],
) -> None:
    """Uploads ``files`` as Git LFS-tracked files in the repository, in one push.

    ``files`` is a list of ``(remote_path, data)`` pairs. Mirrors the classic
    Git LFS batch-API upload flow: the objects are uploaded to GitLab's LFS
    storage in a single batch call, pointer files are committed,
    ``.gitattributes`` is updated to track the target paths via LFS, and the
    pointers are finally moved to their real paths — each step done as one
    commit covering all files, rather than one commit per file.

    If ``branch`` is not given (e.g. it wasn't recorded for a dataset imported
    before this was tracked), the project's default branch is used instead.
    """
    if not files:
        return

    gitlab_host = gitlab_api_url.rsplit("/api/v4", 1)[0]
    api_headers = {"PRIVATE-TOKEN": gitlab_token}

    project = _checked(
        requests.get(f"{gitlab_api_url}/projects/{project_id}", headers=api_headers)
    ).json()
    project_path = project["path_with_namespace"]
    branch = branch or project["default_branch"]

    entries = [
        {
            "remote_path": remote_path.lstrip("/"),
            "data": data,
            "oid": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        for remote_path, data in files
    ]

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
                "objects": [
                    {"oid": entry["oid"], "size": entry["size"]} for entry in entries
                ],
                "ref": {"name": f"refs/heads/{branch}"},
            },
        )
    ).json()

    lfs_objects_by_oid = {obj.get("oid"): obj for obj in batch["objects"]}

    for entry in entries:
        lfs_object = lfs_objects_by_oid.get(entry["oid"])
        if lfs_object is None:
            raise RuntimeError(f"No LFS batch response for {entry['remote_path']}")
        if "error" in lfs_object:
            raise RuntimeError(
                f"LFS error for {entry['remote_path']}: {lfs_object['error']}"
            )

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
                    upload["href"],
                    data=entry["data"],
                    headers=upload_headers,
                    auth=upload_auth,
                )
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

    # Store the pointers temporarily before marking their final paths as LFS-managed.
    create_actions = []
    for entry in entries:
        pointer = (
            "version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{entry['oid']}\n"
            f"size {entry['size']}\n"
        )
        parent = PurePosixPath(entry["remote_path"]).parent
        entry["temporary_path"] = (
            entry["oid"] if str(parent) == "." else str(parent / entry["oid"])
        )
        create_actions.append(
            {"action": "create", "file_path": entry["temporary_path"], "content": pointer}
        )

    commit(f"Add LFS pointer(s) for {len(entries)} file(s)", create_actions)

    # Add the target paths to .gitattributes.
    attributes_url = (
        f"{gitlab_api_url}/projects/{project_id}/repository/files/"
        f"{quote('.gitattributes', safe='')}"
    )
    response = requests.get(attributes_url, headers=api_headers, params={"ref": branch})

    if response.status_code == 404:
        existing_attributes = ""
        attribute_action = "create"
    else:
        _checked(response)
        existing_attributes = base64.b64decode(response.json()["content"]).decode(
            "utf-8"
        )
        attribute_action = "update"

    existing_lines = existing_attributes.splitlines()
    new_lines = [
        f"{entry['remote_path']} filter=lfs diff=lfs merge=lfs -text"
        for entry in entries
        if f"{entry['remote_path']} filter=lfs diff=lfs merge=lfs -text"
        not in existing_lines
    ]

    if new_lines:
        new_attributes = existing_attributes.rstrip()
        if new_attributes:
            new_attributes += "\n"
        new_attributes += "\n".join(new_lines) + "\n"

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

    # Move the pointers to their final paths.
    move_actions = [
        {
            "action": "move",
            "previous_path": entry["temporary_path"],
            "file_path": entry["remote_path"],
        }
        for entry in entries
    ]
    commit(
        f"Add LFS file(s): {', '.join(entry['remote_path'] for entry in entries)}",
        move_actions,
    )
