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
import subprocess
from minio import Minio
from minio.credentials import WebIdentityProvider


MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_HOST = MINIO_ENDPOINT.split(":")[0]
MINIO_IP_ADDRESS = subprocess.run(
    ["dig", "+short", MINIO_HOST], stdout=subprocess.PIPE
).stdout.decode("utf-8")

_admin_client = None


def get_admin_client():
    global _admin_client
    if _admin_client is None:
        _admin_client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=False,
        )
    return _admin_client


class MinIOOpenID(Minio):
    def __init__(
        self,
        endpoint,
        secure=True,
        http_client=None,
        token=None,
    ):

        access_key = None
        secret_key = None
        region = None
        session_token = None

        self._endpoint = endpoint

        self._endpoint_url = ("https://" if secure else "http://") + endpoint

        t = Token(token)

        self._credentials = self._get_credentials_provider(
            self._endpoint_url, t.get_token, secure=secure
        )

        super().__init__(
            self._endpoint,
            access_key,
            secret_key,
            session_token,
            secure=secure,
            region=region,
            http_client=http_client,
            credentials=self._credentials,
        )

    def _get_credentials_provider(
        self,
        s3_endpoint_url,
        credentials_func=None,
        secure=True,
    ):
        assert credentials_func
        return WebIdentityProvider(credentials_func, s3_endpoint_url, secure)


class Token:
    token = {}

    def __init__(self, access_token) -> None:
        self.token = access_token

    def get_token(self):
        return self.token
