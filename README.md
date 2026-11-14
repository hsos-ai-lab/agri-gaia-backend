<!--
SPDX-FileCopyrightText: 2024 Osnabrück University of Applied Sciences
SPDX-FileContributor: Andreas Schliebitz
SPDX-FileContributor: Henri Graf
SPDX-FileContributor: Jonas Tüpker
SPDX-FileContributor: Lukas Hesse
SPDX-FileContributor: Maik Fruhner
SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
SPDX-FileContributor: Tobias Wamhof

SPDX-License-Identifier: MIT
-->

<div align="center">

<img src="https://raw.githubusercontent.com/hsos-ai-lab/agri-gaia-platform/main/services/keycloak/themes/agrigaia/login/resources/img/raw/agri-gaia-fulllogo.png" alt="Agri-Gaia logo" width="360">

# Agri-Gaia Backend

**The web server backend of the Agri-Gaia platform, powered by FastAPI.**

[![Release](https://img.shields.io/badge/release-1.0.0-2e7d32)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[API Overview](#-api-overview) ·
[Configuration](#-configuration) ·
[Development](#-development) ·
[Database Migrations](#database-migrations) ·
[Testing](#-testing)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Tech Stack](#-tech-stack)
- [API Overview](#-api-overview)
- [Integrations](#-integrations)
- [Configuration](#-configuration)
- [Development](#-development)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Related Repositories](#-related-repositories)
- [Changelog](#-changelog)
- [License](#-license)

## 🌱 Overview

The backend is the central REST API of the [Agri-Gaia platform](https://github.com/hsos-ai-lab/agri-gaia-platform). It authenticates users through Keycloak and coordinates all other platform services. Its responsibilities include:

- managing datasets, models and their semantic metadata;
- building and running model training containers;
- building inference images and deploying them to edge devices;
- connecting the platform to data spaces through the Eclipse Dataspace Connector.

> [!NOTE]
> This repository is included as a git submodule at `services/backend` of the [agri-gaia-platform](https://github.com/hsos-ai-lab/agri-gaia-platform) repository. The backend depends on many platform services (Keycloak, PostgreSQL, MinIO, Fuseki, Portainer, and others) and is **not intended to run on its own**. Start it as part of the platform's Docker Compose stack.

## 🧰 Tech Stack

| Area | Technologies |
|------|--------------|
| Language & runtime | Python 3.12, Uvicorn |
| Web framework | FastAPI ~0.110, Pydantic v1 |
| Persistence | SQLAlchemy 1.4, Alembic, PostgreSQL 14, PostGIS (GeoAlchemy2) |
| Authentication | Keycloak / OpenID Connect via `python-keycloak` |
| Object storage | MinIO Python SDK, with per-user STS credentials |
| Containers | Docker SDK, `python-on-whales`, BuildKit / Buildx, `nuctl` |
| Semantic web | `rdflib`, SPARQL against Apache Jena Fuseki |
| Machine learning | `tritonclient`, ONNX, FiftyOne, `pycocotools` |
| Observability | `prometheus-fastapi-instrumentator` |

## 🧭 API Overview

The application entry point is [`agri_gaia_backend/main.py`](agri_gaia_backend/main.py), which registers the following routers:

| Prefix | Purpose |
|--------|---------|
| `/users` | Information about the authenticated user |
| `/datasets` | Dataset management in MinIO with semantic metadata, search, download, label-format conversion (CVAT, COCO, YOLO), CVAT annotation and Nuclio-based auto-annotation |
| `/cvat` | CVAT task creation and CVAT user/session handling |
| `/models` | Model upload, management, search, download and publication |
| `/train` | Training providers and architectures, training configurations, template upload and train container lifecycle (run, stop, logs, score, model) |
| `/triton` | Batch inference of models on datasets with NVIDIA Triton |
| `/inference-container-templates` | Installation of inference container templates from ZIP archives or Git repositories |
| `/container-images` | Registry images; building inference images from a model and a template |
| `/container-deployments` | Deployment of container images to edge devices |
| `/model-deployments` | Deployment of models to edge devices |
| `/edge-devices`, `/edge-groups`, `/tags` | Edge device and group management via Portainer Edge |
| `/applications` | Edge applications deployed as Portainer edge stacks |
| `/integrated-services` | Integration of external services through their OpenAPI specifications |
| `/network` | Eclipse Dataspace Connector: connectors, catalogs, contract negotiations and transfers |
| `/agrovoc`, `/geonames` | AGROVOC keyword and ontology lookups, GeoNames locations |
| `/open-data` | Geographic open data (field borders from PostGIS) |
| `/licenses` | Third-party license report |
| `/tasks` | Status of long-running background tasks |
| `/urls` | Pre-authenticated URLs for platform tools |
| `/service` | Internal hooks for Keycloak user (de)registration and Docker registry events |

The interactive OpenAPI documentation is served at `https://api.<PROJECT_BASE_URL>/docs`. It is reachable without a bearer token only when `DEBUG` is enabled. Prometheus metrics are exposed at `/metrics`.

## 🔌 Integrations

| Service | Usage |
|---------|-------|
| **Keycloak** | Validates JWT bearer tokens (signature, audience and expiry) on every request |
| **PostgreSQL** | Primary relational database (`postgres_backend`) |
| **PostGIS** | Geographic data such as field borders (`postgis_backend`) |
| **MinIO** | Per-user buckets for datasets and models, accessed with STS `AssumeRoleWithWebIdentity` credentials |
| **Apache Jena Fuseki** | Semantic metadata, ontologies, AGROVOC and GeoNames via SPARQL |
| **BuildKit / Docker registry** | Builds training and inference images in the remote build container and pushes them to `registry.<PROJECT_BASE_URL>` |
| **Portainer** | Edge devices, edge groups, edge stacks and tags |
| **CVAT / Nuclio** | Annotation tasks and serverless auto-annotation functions deployed with `nuctl` |
| **NVIDIA Triton** | Model inference via `tritonclient` |
| **Eclipse Dataspace Connector** | Publishing assets and negotiating contracts in data spaces |
| **GitHub API** | Optional, for the license report (`GITHUB_TOKEN`) |

## 🔧 Configuration

The backend reads its configuration from environment variables. They are provided by the platform's `docker-compose.yml` and supplemented by the [`.env`](.env) file in this repository. Values from `.env` never override variables that are already set.

| Group | Variables |
|-------|-----------|
| General | `PROJECT_BASE_URL`, `PROJECT_NAME`, `DEBUG`, `MIGRATE_DB`, `BACKEND_VERIFY_SSL` |
| Keycloak | `KEYCLOAK_INTERNAL_URL`, `KEYCLOAK_REALM_NAME`, `BACKEND_OPENID_CLIENT_ID`, `BACKEND_OPENID_CLIENT_SECRET`, `REALM_SERVICE_ACCOUNT_USERNAME`, `REALM_SERVICE_ACCOUNT_PASSWORD` |
| Databases | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGIS_DB`, `POSTGIS_USER`, `POSTGIS_PASSWORD` |
| MinIO | `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` |
| Fuseki | `FUSEKI_ENDPOINT`, `FUSEKI_ADMIN_USER`, `FUSEKI_ADMIN_PASSWORD` |
| Registry | `REGISTRY_URL`, `REGISTRY_TOKEN` |
| CVAT / Nuclio | `CVAT_SUPERUSER`, `CVAT_SUPERUSER_PASSWORD`, `NUCLIO_CVAT_PROJECT_NAME` |
| Portainer | `PORTAINER_VERSION`, `PORTAINER_OPENID_CLIENT_ID`, `PORTAINER_OPENID_CLIENT_SECRET`, `PORTAINER_ADMIN_USERNAME`, `PORTAINER_ADMIN_PASSWORD`, `PORTAINER_EDGE_PORT` |
| EDC | `CONNECTOR_PASSWORD`, `PROVIDER_DATA_ENDPOINT` |
| Other | `GPUS`, `GITHUB_TOKEN` |

Docker build arguments: `DOCKER_VERSION`, `NUCLIO_VERSION`, `KEYCLOAK_REALM_NAME`, and the optional `NVIDIA_NGC_API_KEY`, which configures access to `nvcr.io`.

## 💻 Development

### Running in development mode

Start the backend as part of the platform (see the [platform README](https://github.com/hsos-ai-lab/agri-gaia-platform#-getting-started)). In development mode, the platform's `docker-compose.override.yml`:

- builds the image from [`Dockerfile-dev`](Dockerfile-dev);
- bind-mounts this directory into the container at `/code`;
- runs Uvicorn with `--reload`, so code changes are applied immediately.

The server listens on port `8000` and is routed by Traefik to `https://api.<PROJECT_BASE_URL>`. The process runs under [debugpy](https://github.com/microsoft/debugpy), which listens on port `5678` inside the container. Publish this port in a local Compose override to attach a remote debugger.

### Working on the data model

The backend server uses **SQLAlchemy** as its ORM framework and **PostgreSQL** as its DBMS. The models are defined in [`agri_gaia_backend/db/models.py`](agri_gaia_backend/db/models.py). Changes to the database schema are managed with **Alembic** migrations in [`alembic/versions`](alembic/versions).

### Database migrations

The database migrations are applied automatically when the backend server starts, provided the `MIGRATE_DB` environment variable is set:

| `MIGRATE_DB` | Behavior at startup |
|--------------|---------------------|
| `true` | Runs `alembic upgrade head` |
| unset / `false` | Creates missing tables directly from the SQLAlchemy models (`create_all`), without Alembic |

When the data model changes, a migration file can be autogenerated with:

```bash
alembic revision --autogenerate -m "message"
```

The database host `postgres_backend` resolves only inside the Compose network, so run the command inside the running container from the platform root:

```bash
docker compose exec backend alembic revision --autogenerate -m "message"
```

With the development bind mount in place, the new revision is written directly to your working tree. Review the generated file before committing it.

### Model training templates

The [`model-training`](model-training) directory contains the shared training infrastructure (`common/`, `datasets/`, `export/`, `validation/`) and the bundled training templates:

| Provider | Category | Architectures |
|----------|----------|---------------|
| Torchvision | Classification | EfficientNet |
| Torchvision | Instance Segmentation | Mask R-CNN |
| Ultralytics | Object Detection | YOLOv5, YOLOv11 |

Users can add templates through the UI. See the [train container template](https://github.com/hsos-ai-lab/agri-gaia-train-container-template) for the template format.

Inference container templates are not bundled. They are installed at runtime from ZIP archives or Git repositories and stored in the `model-inference` volume. See the [inference container template](https://github.com/hsos-ai-lab/agri-gaia-inference-container-template).

## 🧪 Testing

The test suite in [`tests`](tests) uses [pytest](https://docs.pytest.org/) with FastAPI's `TestClient`. The tests are **integration tests**: they require the running platform, including Keycloak, PostgreSQL, MinIO, CVAT and Portainer.

Run them from the platform root:

```bash
./run_tests.sh   # equivalent to: docker compose exec backend pytest .
```

Key concepts of the suite (see [`tests/README.md`](tests/README.md) for details):

- **Fixtures instead of setup/teardown**: a session-scoped fixture creates and deletes a test user for the whole session.
- **Isolation per test**: every test gets a fresh backend app, database session and test client.
- **Three test clients**: unauthenticated, authenticated as the test user, and one that automatically deletes resources created through `POST` requests.
- **Cleanup warnings**: errors during cleanup are reported as `UserWarning`s starting with `CleanupError`. Disable them per test with `@pytest.mark.filterwarnings("ignore:CleanupError")`.

## 📁 Project Structure

```text
agri-gaia-backend/
├── agri_gaia_backend/
│   ├── main.py          # FastAPI application, middleware and router registration
│   ├── routers/         # API endpoints, one module per resource
│   ├── db/              # SQLAlchemy models, engine and CRUD modules
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Clients for CVAT, Docker, EDC, Fuseki, MinIO, Portainer, ...
│   └── util/            # Authentication, environment helpers, logging, training utilities
├── alembic/             # Database migrations
├── config/              # Docker client configuration
├── fuseki/              # Fuseki dataset assembler template
├── model-training/      # Shared training infrastructure and bundled templates
├── model-inference/     # Installation target for inference templates
├── tests/               # pytest integration tests
├── Dockerfile           # Container image
├── Dockerfile-dev       # Development image
└── requirements.txt
```

## 🔗 Related Repositories

| Repository | Description |
|------------|-------------|
| [agri-gaia-platform](https://github.com/hsos-ai-lab/agri-gaia-platform) | Docker Compose platform definition |
| [agri-gaia-backend](https://github.com/hsos-ai-lab/agri-gaia-backend) | FastAPI backend (this repository) |
| [agri-gaia-frontend](https://github.com/hsos-ai-lab/agri-gaia-frontend) | React frontend |
| [agri-gaia-platform-deployment](https://github.com/hsos-ai-lab/agri-gaia-platform-deployment) | Scripts for automated production deployments |
| [agri-gaia-train-container-template](https://github.com/hsos-ai-lab/agri-gaia-train-container-template) | Template for custom model training containers |
| [agri-gaia-inference-container-template](https://github.com/hsos-ai-lab/agri-gaia-inference-container-template) | Template for custom inference containers |

## 📝 Changelog

All notable changes are documented in [CHANGELOG.md](CHANGELOG.md).

## 📄 License

This project is licensed under the [MIT License](LICENSE).

Copyright © 2024 Osnabrück University of Applied Sciences.

**Contributors:** Andreas Schliebitz, Henri Graf, Jonas Tüpker, Lukas Hesse, Maik Fruhner, Prof. Dr.-Ing. Heiko Tapken, Tobias Wamhof
