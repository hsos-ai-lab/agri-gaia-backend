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

FROM python:3.12-slim AS build_stage
WORKDIR /work

RUN pip install jinja2~=3.0.3
COPY model_config_template.pbtxt .
COPY create_triton_model_repository.py .

COPY models /work/models
RUN python3 create_triton_model_repository.py

FROM nvcr.io/nvidia/tritonserver:22.03-py3

COPY --from=build_stage /work/model_repository /model_repository

CMD ["tritonserver", "--model-repository=/model_repository"]
