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

import io
import minio

from typing import Optional, Union
from agri_gaia_backend.services.minio_api.client import *

import logging

logger = logging.getLogger("api-logger")


# Creates a connection to a minio instance
#
# token:        has to be a valid token and must be passed as a dict object
def get_access(token):
    minio_endpoint = os.environ.get("MINIO_ENDPOINT")

    http_client = None

    mclient = MinIOOpenID(
        endpoint=minio_endpoint,
        token=token,
        secure=False,
        http_client=http_client,
    )

    return mclient


def valid_params(bucket, token):
    """
    Validates the Parameters, which can be used to connect to a minio instance.

    Args:
        bucket: The bucket, which should be accessed.
        token: the authentication token used to connect.
    """
    minio_client = get_access(token)
    minio_client.bucket_exists(bucket)


def upload_file(bucket, prefix, token, file, objectname: Optional[str] = None):
    """
    Uploads a single file to the defined MinIO location

    bucket: specifies the bucket, which shall be used to upload or download files
    prefix: defines the prefix, where to upload the file. If there is no trailing '/' at the end, a '/' will be added
    token: has to be a valid token and must be passed as a dict object
    file: the file to be uploaded
    objectname: name of the object. Will be prefixed with 'prefix'. If not given the filename of the file will be used.
    """

    minio_client = get_access(token)
    objectname = objectname or file.filename
    prefix = prefix.rstrip("/") + "/"

    minio_client.put_object(
        bucket_name=bucket,
        object_name=prefix + objectname,
        data=file.file._file,
        length=-1,
        part_size=50 * 1024 * 1024,
    )


def upload_data(
    bucket: str,
    prefix: str,
    token: str,
    data: Union[bytes, io.BytesIO],
    objectname: str,
    content_type="application/octet-stream",
):
    """
    Uploads data to the defined MinIO location

    Args:
        bucket: specifies the bucket, which shall be used to upload or download files
        prefix: defines the prefix, where to upload the file. If there is no trailing '/' at the end, a '/' will be added
        token: has to be a valid token and must be passed as a dict object
        data: data to be uploaded
        objectname: name of the object. Will be prefixed with 'prefix'.
        content_type: content type of data. Defaults to "application/octet-stream".
    """
    minio_client = get_access(token)
    prefix = prefix.rstrip("/") + "/"

    if type(data) is bytes:
        data = io.BytesIO(data)

    minio_client.put_object(
        bucket_name=bucket,
        object_name=prefix + objectname,
        data=data,
        length=-1,
        part_size=50 * 1024 * 1024,
        content_type=content_type,
    )


def download_file(bucket, token, minio_item):
    """
    Downloads a single file from the defined MinIO location.

    Args:
        bucket: specifies the bucket, which shall be used to upload or download files
        token: has to be a valid token to access the MinIO storage and must be passed as a dict object
        minio_item: The object name of the file, whicch should be retrieved.

    Returns:
        The MinIO Response object.
    """
    return get_object(bucket, minio_item.object_name, token)


def delete_all_objects(bucket, prefix, token):
    """
    Delete all files starting with given dataset as prefix from minio

    bucket:                 specifies the bucket, which shall be used
    prefix:                 defines the prefix, which shall be deleted. If there is no trailing '/' at the end, a '/' will be added
    token:                  has to be a valid token and must be passed as a dict object
    """
    minio_client = get_access(token)
    prefix = prefix.rstrip("/") + "/"

    for item in minio_client.list_objects(bucket, prefix=prefix, recursive=True):
        minio_client.remove_object(bucket, item.object_name)


def delete_object(bucket, object_name, token):
    """
    deletes the object for the given bucket and object name

    bucket:             bucket the object is in
    object_name:        the name of the object in the bucket
    token:              has to be a valid token and must be passed as a dict object
    """
    minio_client = get_access(token)
    minio_client.remove_object(bucket, object_name)


def get_all_objects(bucket, prefix, token):
    """
    Returns a list of all objects contained in a dataset of an defined MinIO bucket

    bucket:               specifies the bucket, which shall be used to upload or download files
    prefix:               defines the prefix, where to upload the file. If there is no trailing '/' at the end, a '/' will be added
    token:                has to be a valid token and must be passed as a dict object
    """
    minio_client = get_access(token)
    prefix = prefix.rstrip("/") + "/"

    return list(minio_client.list_objects(bucket, prefix=prefix, recursive=True))


def get_object(bucket, object_name, token):
    """
    Returns the object for the given bucket and object name

    bucket:             bucket the object is in
    object_name:        the name of the object in the bucket
    token:              has to be a valid token and must be passed as a dict object

    return:             The object as urllib3.response.HTTPResponse object
    """
    minio_client = get_access(token)
    return minio_client.get_object(bucket, object_name)


def stat_object(bucket: str, object_name: str, token: str) -> minio.datatypes.Object:
    minio_client = get_access(token)
    return minio_client.stat_object(bucket_name=bucket, object_name=object_name)


def exists(bucket: str, object_name: str, token: str) -> bool:
    minio_client = get_access(token)
    try:
        minio_client.stat_object(bucket_name=bucket, object_name=object_name)
    except minio.S3Error as e:
        if e.code == "NoSuchKey":
            return False
    return True
