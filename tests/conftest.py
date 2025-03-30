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

from dataclasses import dataclass
from io import BytesIO
import requests
import json
import os
import glob
import logging

from fastapi import FastAPI
import pytest
import warnings
import datetime
from fastapi.testclient import TestClient
from agri_gaia_backend.db import tasks_api
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_409_CONFLICT,
)
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from minio import Minio

from agri_gaia_backend import main
from agri_gaia_backend.util.env import (
    KEYCLOAK_REALM_NAME,
    KEYCLOAK_ADMIN_USERNAME,
    KEYCLOAK_ADMIN_PASSWORD,
    MINIO_ROOT_USER,
    MINIO_ROOT_PASSWORD,
    S3_ENDPOINT,
    bool_from_env,
)
from agri_gaia_backend.services import minio_api
from agri_gaia_backend.services.cvat import cvat_api
from agri_gaia_backend.services.cvat.cvat_client import CvatClient, CvatAuth

from agri_gaia_backend import schemas
from agri_gaia_backend.db import container_api

from agri_gaia_backend.routers import cvat as cvat_router

from agri_gaia_backend.services.portainer.portainer_api import portainer

from . import mock

POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres_backend:5432/{POSTGRES_DB}"

OIDC_ENDPOINT = (
    f"http://keycloak:8080/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/token"
)
USERS_ENDPOINT = f"http://keycloak:8080/admin/realms/{KEYCLOAK_REALM_NAME}/users"

PROJECT_BASE_URL = os.environ.get("PROJECT_BASE_URL")
VERIFY_SSL = bool_from_env("BACKEND_VERIFY_SSL")

cvatClient = CvatClient(
    protocol="https", host=f"cvat.{PROJECT_BASE_URL}", port=None, verify_ssl=VERIFY_SSL
)


def get_admin_client():
    _admin_client = Minio(
        endpoint=S3_ENDPOINT,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=False,
    )
    return _admin_client


def get_oidc_access_token(
    username: str, password: str, client_id: str, endpoint: str = OIDC_ENDPOINT
) -> str:
    payload = {
        "client_id": client_id,
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(endpoint, headers=headers, data=payload)
    assert (
        response.status_code == HTTP_200_OK
    ), f"Login of user '{username}' failed. Response: {response.text}"

    response_body = response.json()
    return response_body["access_token"]


@dataclass
class Testuser:
    __test__ = False
    username: str
    password: str
    email: str
    firstname: str
    lastname: str


@pytest.fixture(scope="session")
def test_user():
    info = Testuser(
        username="testuser",
        password="password",
        email="testuser@example.com",
        firstname="Testfirstname",
        lastname="Testlastname",
    )
    return info


@pytest.fixture(scope="session", autouse=True)
def register_testuser(test_user: Testuser):
    admin_accesstoken = get_oidc_access_token(
        KEYCLOAK_ADMIN_USERNAME,
        KEYCLOAK_ADMIN_PASSWORD,
        client_id="admin-cli",
        endpoint="http://keycloak:8080/realms/master/protocol/openid-connect/token",
    )

    auth_header = {
        "Authorization": f"Bearer {admin_accesstoken}",
    }

    payload = {
        "firstName": test_user.firstname,
        "lastName": test_user.lastname,
        "email": test_user.email,
        "enabled": "true",
        "username": test_user.username,
        "credentials": [
            {
                "type": "password",
                "value": test_user.password,
                "temporary": False,
            }
        ],
    }

    response = requests.post(USERS_ENDPOINT, headers=auth_header, json=payload)
    if response.status_code != HTTP_409_CONFLICT:
        assert (
            response.status_code == HTTP_201_CREATED
        ), f"Registration of testuser failed. Response text: {response.text}"

    _admin_client = get_admin_client()

    if not _admin_client.bucket_exists(test_user.username):
        _admin_client.make_bucket(test_user.username)

    yield

    # cleanup
    get_user_response = requests.get(
        USERS_ENDPOINT + f"?username={test_user.username}",
        headers=auth_header,
    )
    assert (
        get_user_response.status_code == HTTP_200_OK
    ), f"Error getting user {test_user.username}"

    reponse_body = get_user_response.json()
    testuser_id = reponse_body[0]["id"]

    delete_user_response = requests.delete(
        USERS_ENDPOINT + f"/{testuser_id}", headers=auth_header
    )
    assert (
        delete_user_response.status_code == HTTP_204_NO_CONTENT
    ), f"Error deleting user {test_user.username} with ID {testuser_id}"

    if _admin_client.bucket_exists(test_user.username):
        _admin_client.remove_bucket(test_user.username)


@pytest.fixture(scope="session")
def testuser_auth_token(register_testuser, test_user: Testuser):
    return get_oidc_access_token(
        test_user.username, test_user.password, client_id="frontend"
    )


# https://stackoverflow.com/questions/58660378/how-use-pytest-to-unit-test-sqlalchemy-orm-classes
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    """returns a SQLAlchemy scoped session factory"""
    return scoped_session(sessionmaker(bind=db_engine))


@pytest.fixture(scope="session")
def db(db_session_factory):
    """yields a SQLAlchemy connection which is rollbacked after the test"""
    session = db_session_factory()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def minio_client():
    return minio_api.get_admin_client()


@pytest.fixture(scope="session")
def app(db) -> FastAPI:
    def get_test_session():
        return db

    # main.app.dependency_overrides[get_db] = get_test_session
    return main.app


@pytest.fixture(scope="session")
def unauthenticated_client(app) -> TestClient:
    """
    Fixture providing the basic unauthenticated client with possible modifications regarding headers etc.
    """
    return TestClient(app)


@pytest.fixture(scope="session")
def authenticated_client(app, testuser_auth_token: str) -> TestClient:
    """
    Fixture providing a client based on the unauthenticated client and using the identity of the test user for authentication.
    """
    client = TestClient(app)
    client.headers = {
        "Authorization": f"Bearer {testuser_auth_token}",
    }
    return client


@pytest.fixture
def testclient(app, testuser_auth_token: str) -> TestClient:
    """
    Fixture providing the client that shall be used in tests in general.
    This client has additional modifications such that resources created with this client are deleted automatically after finishing the test.
    """
    client = TestClient(app)
    client.headers = {
        "Authorization": f"Bearer {testuser_auth_token}",
    }

    created_resources = []
    orig_post = client.post

    def post_patched(*args, **kwargs):
        response = orig_post(*args, **kwargs)
        if response.is_success:
            body = response.json()
            url = args[0] if len(args) > 0 else kwargs["url"]
            created_resources.append({"endpoint": url, "id": body["id"]})
        return response

    client.post = post_patched
    yield client

    for created_resource in created_resources:
        delete_url = f"{created_resource['endpoint']}/{created_resource['id']}"
        response = client.delete(delete_url)
        if not response.is_success:
            warning = UserWarning(
                f"CleanupError: Error deleting resource for test cleanup: '{delete_url}'\nResponse code: {response.status_code}\nResponse text: {response.text}"
            )
            warnings.warn(warning)
            logging.warning(warning)


@pytest.fixture
def test_dataset(
    authenticated_client: TestClient, cvat_authentication_data
) -> schemas.Dataset:
    data = {
        "semantic_labels": [
            "http://aims.fao.org/aos/agrovoc/c_13551",
        ],
        "name": "Test-Dataset",
        "description": "This is a test dataset with a single file.",
        "includes_annotation_file": False,
        "is_classification_dataset": False,
        "dataset_type": "AgriImageDataResource",
        "metadata": "{}",
    }
    files = {
        "files": ("testfile.txt", BytesIO("This is a test file.".encode("utf-8"))),
    }

    response = authenticated_client.post("/datasets", data=data, files=files)

    assert response.status_code == HTTP_201_CREATED, "Error creating testdataset"
    testdataset = schemas.Dataset(**response.json())

    yield testdataset

    dataset_url = f"/datasets/{testdataset.id}"
    response = authenticated_client.request(
        "DELETE", dataset_url, json=cvat_authentication_data
    )

    # response = authenticated_client.delete(dataset_url, body=cvat_authentication_data)
    if not response.is_success:
        warning = UserWarning(
            f"CleanupError: Error deleting dataset: '{dataset_url}'\nResponse code: {response.status_code}\nResponse text: {response.text}"
        )
        warnings.warn(warning)
        logging.warning(warning)


@pytest.fixture
def test_model(testclient: TestClient) -> schemas.Model:
    data = {
        "name": "Test-Model",
        "description": "This is a test model with a single file.",
        "labels": ["Potato"],
        "format": "pytorch",
        "includes_annotation_file": False,
    }
    files = {
        "modelfile": (
            "test_model.txt",
            BytesIO("This is a test file.".encode("utf-8")),
        ),
    }

    response = testclient.post("/models", data=data, files=files)

    assert response.status_code == HTTP_201_CREATED, "Error creating model"

    assert response.headers["Content-Type"] == "application/json"

    testmodel = schemas.Model(**response.json())

    return testmodel


@pytest.fixture
def test_edge_device(testclient: TestClient) -> schemas.EdgeDevice:
    data = {"name": "Test-Edge-Device3", "tags": ["Test"]}
    response = testclient.post("/edge-devices", json=data)
    assert response.status_code == HTTP_201_CREATED, "Error creating edge device"
    assert response.headers["Content-Type"] == "application/json"
    testedgedevice = schemas.EdgeDevice(**response.json())
    testedgedevice.tags = [
        "Test"
    ]  # workaround tags attribute usually being filled by portainer

    return testedgedevice


@pytest.fixture
def registered_test_edge_device(
    testclient: TestClient, monkeypatch
) -> schemas.EdgeDevice:
    data = {"name": "Test-Edge-Device4", "tags": []}
    response = testclient.post("/edge-devices", json=data)
    assert response.status_code == HTTP_201_CREATED, "Error creating edge device"
    assert response.headers["Content-Type"] == "application/json"

    testedgedevice = schemas.EdgeDevice(**response.json())

    with monkeypatch.context() as m:
        mock_method = mock.common.MockRequestsMethod()
        mock_method.add_response(
            ".*/docker/info", mock.portainer.DockerInfoMockResponse()
        )
        mock_method.add_response(
            ".*/endpoints$",
            mock.portainer.get_endpoints_response_method(testedgedevice.portainer_id),
        )
        m.setattr(requests, "get", mock_method)
        edge_response = testclient.get(f"/edge-devices/{testedgedevice.id}")

    # should be registered now
    testedgedevice = schemas.EdgeDevice(**edge_response.json())

    return testedgedevice


@pytest.fixture
def test_container_deployment(
    testclient: TestClient,
    registered_test_edge_device: schemas.EdgeDevice,
    test_container_image,
    monkeypatch,
) -> schemas.ContainerDeployment:
    # port = gültiger port
    data = {
        "name": "Test-Container-Deployment2232",
        "edge_device_id": registered_test_edge_device.id,
        "container_image_id": test_container_image.id,
        "port_bindings": [
            {"host_port": "2000", "container_port": "2000", "protocol": "udp"}
        ],
    }

    with monkeypatch.context() as m:
        mock_method = mock.common.MockRequestsMethod()
        mock_method.add_response(
            ".*/docker/containers/json", mock.portainer.DockerContainersMockResponse([])
        )
        m.setattr(requests, "get", mock_method)
        response = testclient.post("/container-deployments", json=data)

    assert (
        response.status_code == HTTP_201_CREATED
    ), "Error creating container deployment"

    assert response.headers["Content-Type"] == "application/json"

    test_container_deployment = schemas.ContainerDeployment(**response.json())

    return test_container_deployment


@pytest.fixture(scope="session", autouse=True)
def register_cvat_user(authenticated_client: TestClient, test_user):
    def delete_user():
        users = cvatClient.get_users()["results"]
        cvat_user = [user for user in users if user["username"] == test_user.username]
        if not cvat_user:
            warnings.warn(
                UserWarning(
                    f"TestUser was not found in CVAT. Should be here at this point."
                )
            )

        su_auth = cvatClient.login_superuser()
        response = requests.delete(
            url=cvat_user[0]["url"],
            headers=su_auth.create_headers(),
            cookies=su_auth.create_cookies(),
            verify=cvatClient.verify_ssl,
        )

        if not response.ok:
            warnings.warn(
                UserWarning(
                    f"TestUser was not deleted in CVAT. Response text: {response.text}"
                )
            )

    response = authenticated_client.get("/cvat/user/exists")
    user_exists = response.json()["exists"]
    if user_exists:
        delete_user()

    response = authenticated_client.post("/cvat/user/create")
    assert response.is_success, "Error creating cvat user"
    username = response.json()["username"]
    assert username == test_user.username, "Response has different username"

    yield

    delete_user()


@pytest.fixture
def cvat_authentication_data(
    register_cvat_user, authenticated_client: TestClient, test_user
):
    """
    First checks if current User exists in CVAT, if not a new User is created.
    User is then logged in and authentication tokens are returned.
    After the yield, the CVAT User is deleted.
    """
    response = authenticated_client.get("/cvat/user/exists")

    assert (
        response.status_code == HTTP_200_OK
    ), "Error checking if cvat user already exists"

    username = response.json()["username"]
    user_exists = response.json()["exists"]
    assert user_exists, "CVAT user does not exist"
    assert username == test_user.username, "Response has different username"

    login_response = authenticated_client.post("/cvat/auth/login")

    assert login_response.is_success, "CVAT login for testuser was not okay"
    auth_data = login_response.json()
    return auth_data


@pytest.fixture
def test_container_image(db, test_user):
    container_image = container_api.create_container_image(
        db,
        test_user.username,
        f"{test_user.username}/testrepo",
        "testversion",
        "linux/arm64",
        [8000],
        datetime.datetime.now(),
    )

    yield schemas.ContainerImage.from_orm(container_image)

    container_api.delete_container_image(db, container_image)


@pytest.fixture
def test_edge_group(
    authenticated_client: TestClient, test_edge_device
) -> schemas.EdgeGroup:
    tag_ids = portainer.get_ids_for_tag_names(test_edge_device.tags, allow_create=True)
    data = {"name": "Test-Edge-Group", "tag_ids": tag_ids}
    response = authenticated_client.post("/edge-groups", json=data)

    print(response.text)
    assert (
        response.status_code == HTTP_200_OK
    ), "Could not create edge group for test_edge_group Fixture"

    response = authenticated_client.get("/edge-groups")
    edge_groups = response.json()

    assert (
        len(edge_groups) == 1
    ), f"Number of Edge Groups is not as expected. Length of Edge-Group is {len(edge_groups)} but expected is 1."

    yield edge_groups[0]

    print("================================")
    response = authenticated_client.get("/edge-groups")
    edge_groups = response.json()
    for edge_group in edge_groups:
        edge_group_id = edge_group["id"]
        response = authenticated_client.delete(f"/edge-groups/{edge_group_id}")


@pytest.fixture
def test_application(
    authenticated_client: TestClient, test_edge_group
) -> schemas.Application:
    data = {
        "name": "Test-Application",
        "group_ids": [test_edge_group["id"]],
        "yaml": "version: '3'\n\nservices:  \n  my-service:\n    # enter your application details...\n\nvolumes:\n",
    }

    response = authenticated_client.post("/applications", json=data)

    assert (
        response.status_code == HTTP_201_CREATED
    ), "Could not create edge group for Application"
    response_application = schemas.Application(**response.json())

    assert response_application.name == "Test-Application"
    assert len(response_application.portainer_edge_group_ids) == 1
    assert response_application.portainer_edge_group_ids[0] == test_edge_group["id"]

    yield response_application

    response = authenticated_client.get("/applications")
    applications = response.json()

    for application in applications:
        application_id = application["id"]
        response = authenticated_client.delete(f"/applications/{application_id}")


@pytest.fixture
def test_task(db) -> schemas.Task:
    task = tasks_api.create_task(db, initiator="Test-Initiatior", title="Test-Task")
    yield task
    if tasks_api.get_task(db, task.id) is not None:
        tasks_api.delete_task(db, task)
