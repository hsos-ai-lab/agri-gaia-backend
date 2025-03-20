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

FROM ultralytics/yolov5:v6.2

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=Europe/Berlin

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY mount-s3.sh /mount-s3.sh
RUN chmod +x /mount-s3.sh

RUN apt update \
  && apt install -y --no-install-recommends \
  kmod fuse s3fs jq libxml2-utils curl wget tree \
  python3 python-is-python3 python3-pip
RUN sed -i '/user_allow_other/s/^#//g' /etc/fuse.conf

RUN pip install tf2onnx==1.14.0 onnxmltools==1.11.2

WORKDIR /usr/src/app

COPY config_to_args.py config.py dataset.py cvat_dataset.py export.py ./

COPY requirements.txt setup.py train_config.json presets.json export_config.json ./
RUN pip3 install -r requirements.txt

COPY .env ./

ENTRYPOINT ["/bin/bash", "/docker-entrypoint.sh"]
CMD ["$@"]
