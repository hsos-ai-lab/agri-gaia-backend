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

FROM alpine as backend_binaries

ARG DOCKER_VERSION
ARG NUCLIO_VERSION

RUN wget https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz && tar xzf docker-${DOCKER_VERSION}.tgz

RUN wget https://github.com/nuclio/nuclio/releases/download/${NUCLIO_VERSION}/nuctl-${NUCLIO_VERSION}-linux-amd64
RUN chmod +x nuctl-${NUCLIO_VERSION}-linux-amd64 && mv nuctl-${NUCLIO_VERSION}-linux-amd64 nuctl

FROM alpine as docker_config_stage

RUN apk update && apk add jq moreutils

ARG NVIDIA_NGC_API_KEY

WORKDIR /root
COPY ./config/docker-client/config.json ./config/docker-client/add-nvidia-key.sh ./
RUN ./add-nvidia-key.sh config.json "$NVIDIA_NGC_API_KEY"

FROM python:3.11.3

WORKDIR /code
RUN apt update && apt install -y dnsutils

COPY --from=backend_binaries docker/docker /usr/local/bin
COPY --from=docker/buildx-bin:latest /buildx /usr/local/lib/docker/cli-plugins/docker-buildx

COPY --from=backend_binaries nuctl /usr/local/bin

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

RUN mkdir -p /root/.docker
COPY --from=docker_config_stage /root/config.json /root/.docker/config.json

CMD ["uvicorn", "agri_gaia_backend.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
