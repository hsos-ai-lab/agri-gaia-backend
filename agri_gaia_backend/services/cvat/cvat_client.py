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

import logging
import os
from typing import Dict, Union

import requests
from agri_gaia_backend.util.common import is_json_response

logger = logging.getLogger("api-logger")


class CvatAuth:
    def __init__(self, key: str, csrftoken: str, sessionid: str, **kwargs):
        self.key = key
        self.csrftoken = csrftoken
        self.sessionid = sessionid

    def create_headers(self) -> Dict:
        return {"X-CSRFToken": self.csrftoken, "Authorization": f"Token {self.key}"}

    def create_cookies(self) -> Dict:
        return {"sessionid": self.sessionid}

    def __iter__(self):
        yield "key", self.key
        yield "csrftoken", self.csrftoken
        yield "sessionid", self.sessionid


class CvatClient:
    def __init__(
        self, protocol: str, host: str, port: int = None, verify_ssl: bool = True
    ) -> None:
        self.cvat_server_url = (
            f"{protocol}://{host}:{port}"
            if port is not None
            else f"{protocol}://{host}"
        )
        self.cvat_api_url = f"{self.cvat_server_url}/api"
        self.verify_ssl = verify_ssl
        self.csrftoken = None

    def login_superuser(self) -> CvatAuth:
        return self.login(
            username=os.getenv("CVAT_SUPERUSER"),
            password=os.getenv("CVAT_SUPERUSER_PASSWORD"),
        )

    def login(self, username: str, password: str) -> CvatAuth:
        logger.debug(
            f"[CvatClient::login] Logging in to CVAT at '{self.cvat_server_url}' as user '{username}'."
        )
        response = requests.post(
            url=f"{self.cvat_api_url}/auth/login",
            json={
                "username": username,
                "password": password,
            },
            verify=self.verify_ssl,
        )
        response.raise_for_status()

        logger.debug(f"[CvatClient::login] Logged in to CVAT as user '{username}'.")
        return CvatAuth(
            key=response.json()["key"],
            csrftoken=response.cookies["csrftoken"],
            sessionid=response.cookies["sessionid"],
        )

    def logout(self, auth_data: Dict) -> CvatAuth:
        auth = CvatAuth(**auth_data)
        response = requests.post(
            url=f"{self.cvat_api_url}/auth/logout",
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return auth

    def sign(self, url: str) -> Dict:
        auth = self.login_superuser()
        response = requests.post(
            url=f"{self.cvat_api_url}/auth/signing",
            json={"url": url},
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        self.logout(dict(auth))
        response.raise_for_status()
        return response.json()

    def get_users(self) -> Dict:
        auth = self.login_superuser()
        response = requests.get(
            url=f"{self.cvat_api_url}/users",
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        self.logout(dict(auth))
        return response.json()

    def create_task(self, task: Dict, auth_data: Dict) -> Dict:
        auth = CvatAuth(**auth_data)
        response = requests.post(
            url=f"{self.cvat_api_url}/tasks",
            json=task,
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def update_task(self, task_id: int, new_task: Dict, auth_data: Dict) -> Dict:
        auth = CvatAuth(**auth_data)
        response = requests.patch(
            url=f"{self.cvat_api_url}/tasks/{task_id}",
            json=new_task,
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def add_data_to_task(self, task_id: int, data: Dict, auth_data: Dict) -> Dict:
        auth = CvatAuth(**auth_data)
        response = requests.post(
            url=f"{self.cvat_api_url}/tasks/{task_id}/data",
            json=data,
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def add_task_annotations(
        self,
        task_id: int,
        auth_data: Dict,
        format: str = None,
        filename: str = None,
        annotations: Dict = None,
        extra_headers: Dict = {},
    ) -> Union[Dict, requests.Response]:
        auth = CvatAuth(**auth_data)

        url = f"{self.cvat_api_url}/tasks/{task_id}/annotations"
        if format is not None and filename is not None:
            url += f"?format={format}&filename={filename}"
        elif annotations is None:
            url += "/"

        response = requests.post(
            url=url,
            json=annotations,
            headers={**auth.create_headers(), **extra_headers},
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        if is_json_response(response):
            return response.json()
        return response

    def update_task_annotations_from_file(
        self,
        task_id: int,
        file_id: str,
        annotations: str,
        auth_data: Dict,
        extra_headers={},
    ) -> Union[Dict, requests.Response]:
        auth = CvatAuth(**auth_data)
        response = requests.patch(
            url=f"{self.cvat_api_url}/tasks/{task_id}/annotations/{file_id}",
            data=annotations,
            headers={**auth.create_headers(), **extra_headers},
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        if is_json_response(response):
            return response.json()
        return response

    def update_task_annotations(
        self,
        task_id: int,
        auth_data: Dict,
        format: str = None,
        filename: str = None,
        annotations: Dict = None,
    ) -> Union[Dict, requests.Response]:
        auth = CvatAuth(**auth_data)

        url = f"{self.cvat_api_url}/tasks/{task_id}/annotations"
        if format is not None and filename is not None:
            url += f"?format={format}&filename={filename}"

        response = requests.put(
            url=url,
            json=annotations,
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response

    def delete_task(self, task_id: int, auth_data: Dict) -> None:
        auth = CvatAuth(**auth_data)
        response = requests.delete(
            url=f"{self.cvat_api_url}/tasks/{task_id}",
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()

    def get_task(self, task_id: int, auth_data: Dict) -> Dict:
        auth = CvatAuth(**auth_data)
        response = requests.get(
            url=f"{self.cvat_api_url}/tasks/{task_id}",
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def get_task_status(self, task_id: int, auth_data: Dict) -> Dict:
        auth = CvatAuth(**auth_data)
        response = requests.get(
            url=f"{self.cvat_api_url}/tasks/{task_id}/status?id={task_id}",
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    # /api/tasks/task_id/annotations?org=&format=CVAT+for+images+1.1&filename=annotations.zip
    def get_task_annotations(
        self,
        task_id: int,
        filename: str,
        format: str,
        action: str = None,
    ) -> requests.Response:
        auth = self.login_superuser()

        url = f"{self.cvat_api_url}/tasks/{task_id}/annotations?filename={filename}&format={format}"
        if action is not None:
            url += f"&action={action}"

        response = requests.get(
            url=url,
            headers=auth.create_headers(),
            cookies=auth.create_cookies(),
            verify=self.verify_ssl,
        )
        self.logout(dict(auth))
        response.raise_for_status()
        return response
